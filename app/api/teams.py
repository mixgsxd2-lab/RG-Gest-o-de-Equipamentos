"""Equipes, técnicos, setores, fornecedores e contratos."""
from flask import jsonify, request

from ..auth import require
from ..extensions import db
from ..models import Contract, Sector, Supplier, Team, Technician, Ticket
from ..services import analytics
from . import bp
from .common import ApiError, apply_fields, get_or_404

TECH_FIELDS = {"name": "str", "specialty": "str", "team_id": "int", "user_id": "int", "supplier_id": "int",
               "registration": "str", "shift": "str", "phone": "str", "hourly_rate": "float", "active": "bool"}
SUPPLIER_FIELDS = {"name": "str", "cnpj": "str", "category": "str", "contact_name": "str", "phone": "str",
                   "email": "str", "rating": "float", "active": "bool"}
CONTRACT_FIELDS = {"number": "str", "supplier_id": "int", "team_id": "int", "scope": "str", "start_date": "date",
                   "end_date": "date", "monthly_value": "float", "sla_response_hours": "int",
                   "sla_resolution_hours": "int", "notes": "str"}
TEAM_FIELDS = {"name": "str", "description": "str", "color": "str"}
SECTOR_FIELDS = {"name": "str", "building": "str", "floor": "str", "cost_center": "str"}


def _crud(model, fields, label, required, list_perm, edit_perm, order, prefix):
    """Registra rotas REST padrão (listar, criar, alterar) para um cadastro simples."""

    @bp.get(f"/{prefix}", endpoint=f"list_{prefix}")
    @require(list_perm)
    def _list():
        q = model.query
        if hasattr(model, "active") and request.args.get("all") != "1":
            q = q.filter(model.active.is_(True))
        return jsonify([o.to_dict() for o in q.order_by(order)])

    @bp.post(f"/{prefix}", endpoint=f"create_{prefix}")
    @require(edit_perm)
    def _create():
        obj = apply_fields(model(), request.get_json(silent=True) or {}, fields, required=required)
        db.session.add(obj)
        db.session.commit()
        return jsonify(obj.to_dict()), 201

    @bp.put(f"/{prefix}/<int:obj_id>", endpoint=f"update_{prefix}")
    @require(edit_perm)
    def _update(obj_id):
        obj = get_or_404(model, obj_id, label)
        apply_fields(obj, request.get_json(silent=True) or {}, fields)
        db.session.commit()
        return jsonify(obj.to_dict())


_crud(Technician, TECH_FIELDS, "Técnico", ("name",), "teams.view", "teams.edit", Technician.name, "technicians")
_crud(Supplier, SUPPLIER_FIELDS, "Fornecedor", ("name",), "teams.view", "teams.edit", Supplier.name, "suppliers")
_crud(Contract, CONTRACT_FIELDS, "Contrato", ("number", "supplier_id", "scope", "start_date", "end_date"),
      "teams.view", "teams.edit", Contract.end_date, "contracts")
_crud(Team, TEAM_FIELDS, "Equipe", ("name",), "teams.view", "users.manage", Team.name, "teams")
_crud(Sector, SECTOR_FIELDS, "Setor", ("name",), "assets.view", "users.manage", Sector.name, "sectors")


@bp.get("/technicians/productivity")
@require("teams.view")
def productivity():
    f = analytics.parse_filters(request.args)
    return jsonify(analytics.technician_productivity(analytics.filtered_tickets(f)))


@bp.get("/technicians/workload")
@require("teams.view")
def workload():
    """Distribuição de demandas: chamados ativos por técnico e por equipe."""
    active = Ticket.query.filter(Ticket.status.in_(["recebido", "aceito", "em_execucao", "aguardando"])).all()
    rows = []
    for tech in Technician.query.filter_by(active=True).order_by(Technician.name):
        mine = [t for t in active if t.operator_id == tech.id]
        rows.append({"id": tech.id, "name": tech.name, "team": tech.team.name if tech.team else None,
                     "specialty": tech.specialty, "external": tech.supplier_id is not None,
                     "active_tickets": len(mine),
                     "urgent": sum(1 for t in mine if t.priority in ("Urgente", "Alta")),
                     "tickets": [{"id": t.id, "code": t.code, "title": t.title, "status": t.status,
                                  "priority": t.priority} for t in mine]})
    unassigned = [t.to_dict() for t in Ticket.query.filter(Ticket.status.in_(["aberto", "recebido"]),
                                                           Ticket.operator_id.is_(None))
                  .order_by(Ticket.created_at)]
    return jsonify({"technicians": rows, "unassigned": unassigned})


@bp.get("/suppliers/performance")
@require("teams.view")
def suppliers_performance():
    f = analytics.parse_filters(request.args)
    return jsonify(analytics.supplier_performance(analytics.filtered_tickets(f), analytics.filtered_costs(f)))


@bp.delete("/contracts/<int:obj_id>")
@require("teams.edit")
def delete_contract(obj_id):
    contract = get_or_404(Contract, obj_id, "Contrato")
    if contract.to_dict()["status"] in ("Vigente", "A vencer"):
        raise ApiError("Contratos vigentes não podem ser excluídos")
    db.session.delete(contract)
    db.session.commit()
    return jsonify({"ok": True})
