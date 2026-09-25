import io

import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.seed import seed_demo


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    class Cfg(TestConfig):
        UPLOAD_FOLDER = str(tmp_path_factory.mktemp("uploads"))

    app = create_app(Cfg)
    with app.app_context():
        seed_demo()
        yield app
        db.session.remove()


def login(app, username, password="123456"):
    client = app.test_client()
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.get_json()
    return client


def test_login_invalido(app):
    r = app.test_client().post("/api/auth/login", json={"username": "admin", "password": "errada"})
    assert r.status_code == 401


def test_usuarios_demo(app):
    for user in ("admin", "gestor", "operador", "usuario", "estoque", "diretoria"):
        me = login(app, user).get("/api/auth/me").get_json()
        assert me["user"]["username"] == user
        assert me["demo"] is True


def test_dashboard_tem_dados(app):
    data = login(app, "diretoria").get("/api/dashboard?days=180").get_json()
    assert data["kpis"]["total"] >= 20
    assert data["kpis"]["finished"] > 0
    assert sum(x["value"] for x in data["charts"]["by_type"]) == data["kpis"]["total"]
    assert len(data["charts"]["by_sector"]) >= 5
    assert data["productivity"] and data["suppliers"]


def test_solicitante_ve_apenas_os_proprios(app):
    client = login(app, "usuario")
    items = client.get("/api/tickets?per_page=500").get_json()["items"]
    assert items and all(t["requester"] == "Juliana Castro" for t in items)
    assert client.get("/api/dashboard").status_code == 403
    assert client.get("/api/users").status_code == 403


def test_fluxo_completo_do_chamado(app):
    req = login(app, "usuario")
    gestor = login(app, "gestor")
    op = login(app, "operador")
    lk = gestor.get("/api/lookups").get_json()
    team = next(t for t in lk["teams"] if t["name"] == "Engenharia Clínica")
    asset = lk["assets"][0]
    rafael = next(t for t in lk["technicians"] if t["name"] == "Rafael Souza")

    r = req.post("/api/tickets", data={
        "title": "Teste de fluxo", "description": "Equipamento com falha", "maintenance_type": "Corretiva",
        "priority": "Alta", "criticality": "Alta", "team_id": team["id"], "asset_id": asset["id"],
        "files": (io.BytesIO(b"\x89PNG fake"), "foto.png")}, content_type="multipart/form-data")
    assert r.status_code == 201, r.get_json()
    t = r.get_json()
    assert t["status"] == "aberto" and t["requester"] == "Juliana Castro" and t["sla_hours"] == 8
    assert len(t["attachments"]) == 1
    tid = t["id"]

    # operador não pode receber/designar; gestor recebe e designa
    assert op.post(f"/api/tickets/{tid}/actions/receive", json={}).status_code == 403
    t = gestor.post(f"/api/tickets/{tid}/actions/receive", json={}).get_json()
    assert t["status"] == "recebido" and t["receiver"] == "Carlos Menezes"
    gestor.post(f"/api/tickets/{tid}/actions/assign", json={"technician_id": rafael["id"]})

    t = op.post(f"/api/tickets/{tid}/actions/accept", json={}).get_json()
    assert t["status"] == "aceito" and t["operator"] == "Rafael Souza"
    t = op.post(f"/api/tickets/{tid}/actions/start", json={}).get_json()
    assert t["status"] == "em_execucao"

    product = next(p for p in lk["products"] if p["quantity"] >= 2)
    r = op.post(f"/api/tickets/{tid}/materials", json={"product_id": product["id"], "quantity": 2})
    assert r.status_code == 201
    r = op.post(f"/api/tickets/{tid}/worklogs", json={"started_at": "2026-01-10T08:00",
                                                       "ended_at": "2026-01-10T10:30"})
    assert r.get_json()["labor_hours"] == 2.5

    t = op.post(f"/api/tickets/{tid}/actions/wait", json={"waiting_reason": "Material"}).get_json()
    assert t["status"] == "aguardando"
    op.post(f"/api/tickets/{tid}/actions/resume", json={})
    assert op.post(f"/api/tickets/{tid}/actions/finish", json={}).status_code == 400  # sem solução
    t = op.post(f"/api/tickets/{tid}/actions/finish", json={
        "diagnosis": "Placa com defeito", "solution": "Placa substituída", "third_party_cost": 100}).get_json()
    assert t["status"] == "finalizado"
    assert t["material_cost"] == round(2 * product["unit_cost"], 2)
    assert t["total_cost"] == round(t["labor_cost"] + t["material_cost"] + 100, 2)

    t = req.post(f"/api/tickets/{tid}/actions/close", json={"closing_notes": "Ok", "satisfaction": 5}).get_json()
    assert t["status"] == "encerrado"
    actions = [e["action"] for e in t["events"]]
    for expected in ("Chamado aberto", "Chamado recebido", "Técnico designado", "Chamado aceito",
                     "Execução iniciada", "Material utilizado", "Apontamento de horas", "Aguardando material",
                     "Execução retomada", "Serviço finalizado", "Chamado encerrado"):
        assert expected in actions

    costs = gestor.get("/api/costs?days=3650").get_json()["items"]
    assert {"Mão de obra", "Material", "Terceiros"} <= {c["category"] for c in costs if c["ticket_id"] == tid}
    moves = gestor.get(f"/api/stock/movements?product_id={product['id']}").get_json()["items"]
    assert moves[0]["ticket_id"] == tid and moves[0]["kind"] == "saida"


def test_estoque_entrada_custo_medio(app):
    client = login(app, "estoque")
    p = client.post("/api/products", json={"code": "TST-1", "name": "Item teste", "unit_cost": 10,
                                           "quantity": 10, "min_stock": 2}).get_json()
    client.post("/api/stock/movements", json={"product_id": p["id"], "kind": "entrada", "quantity": 10,
                                              "unit_cost": 20})
    prod = next(x for x in client.get("/api/products?q=TST-1").get_json())
    assert prod["quantity"] == 20 and prod["unit_cost"] == 15
    r = client.post("/api/stock/movements", json={"product_id": p["id"], "kind": "saida", "quantity": 50})
    assert r.status_code == 400


def test_preventiva_gera_os(app):
    gestor = login(app, "gestor")
    plans = gestor.get("/api/preventive").get_json()
    plan = next(p for p in plans if not p["open_ticket_id"])
    r = gestor.post(f"/api/preventive/{plan['id']}/generate")
    assert r.status_code == 201
    assert gestor.post(f"/api/preventive/{plan['id']}/generate").status_code == 400
    assert gestor.get("/api/preventive/calendar").status_code == 200


def test_inteligencia_e_exportacao(app):
    client = login(app, "diretoria")
    assert client.get("/api/intelligence/failures?days=365").get_json()["total_failures"] > 0
    assert client.get("/api/intelligence/depreciation").get_json()["totals"]["acquisition"] > 0
    pred = client.get("/api/intelligence/predictive").get_json()
    assert pred["assets"] and "score" in pred["assets"][0]
    r = client.get("/api/intelligence/export/chamados.csv")
    assert r.status_code == 200 and b"code" in r.data


def test_iot_ingestao(app):
    client = app.test_client()
    r = client.post("/api/iot/readings", json={"sensor": "GS-O2-01", "value": 2.1},
                    headers={"X-API-Key": "rg-iot-demo-key"})
    assert r.get_json()["ingested"] == 1
    assert client.post("/api/iot/readings", json={"sensor": "GS-O2-01", "value": 2}).status_code == 401
    sensors = login(app, "gestor").get("/api/iot/sensors").get_json()
    assert next(s for s in sensors if s["code"] == "GS-O2-01")["state"] == "alerta"


def test_admin_usuarios(app):
    admin = login(app, "admin")
    r = admin.post("/api/users", json={"username": "novo", "name": "Novo", "role": "solicitante",
                                       "password": "abcdef"})
    assert r.status_code == 201
    login(app, "novo", "abcdef")
    assert admin.get("/api/integrations").get_json()["identity"]
