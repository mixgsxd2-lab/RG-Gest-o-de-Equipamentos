"""Alertas calculados em tempo real a partir do estado do sistema."""
from datetime import date

from ..models import Asset, Contract, PreventivePlan, Product, Sensor, Ticket

SEVERITY_ORDER = {"critico": 0, "alto": 1, "medio": 2, "info": 3}


def build_alerts(user=None):
    alerts = []
    today = date.today()
    active = Ticket.query.filter(Ticket.status.notin_(["finalizado", "encerrado", "cancelado"])).all()
    for t in active:
        st = t.sla_status
        if st == "violado":
            alerts.append({"type": "sla", "severity": "critico", "title": f"SLA violado — {t.code}",
                           "message": t.title, "link": f"#/chamados/{t.id}"})
        elif st == "em_risco":
            alerts.append({"type": "sla", "severity": "alto", "title": f"SLA em risco — {t.code}",
                           "message": t.title, "link": f"#/chamados/{t.id}"})
    for p in PreventivePlan.query.filter_by(active=True).all():
        days = (p.next_due - today).days
        if days < 0:
            alerts.append({"type": "preventiva", "severity": "alto", "title": "Preventiva atrasada",
                           "message": f"{p.name} (venceu há {-days} dia(s))", "link": "#/preventivas"})
        elif days <= 7:
            alerts.append({"type": "preventiva", "severity": "medio", "title": "Preventiva próxima",
                           "message": f"{p.name} em {days} dia(s)", "link": "#/preventivas"})
    for pr in Product.query.filter_by(active=True).all():
        if pr.below_minimum:
            alerts.append({"type": "estoque", "severity": "medio" if pr.quantity > 0 else "alto",
                           "title": "Estoque abaixo do mínimo",
                           "message": f"{pr.name}: {pr.quantity:g} {pr.unit} (mín. {pr.min_stock:g})",
                           "link": "#/estoque"})
    for s in Sensor.query.filter_by(active=True).all():
        if s.state == "alerta":
            alerts.append({"type": "iot", "severity": "critico" if s.kind == "gases" else "alto",
                           "title": f"Sensor fora da faixa — {s.code}",
                           "message": f"{s.name}: {s.last_value:g} {s.unit or ''} "
                                      f"(faixa {s.min_value:g}–{s.max_value:g})",
                           "link": "#/monitoramento"})
    for c in Contract.query.all():
        days = (c.end_date - today).days
        if 0 <= days <= 60:
            alerts.append({"type": "contrato", "severity": "medio", "title": "Contrato a vencer",
                           "message": f"{c.number} — {c.supplier.name} em {days} dia(s)", "link": "#/fornecedores"})
    for a in Asset.query.filter(Asset.warranty_until.isnot(None)).all():
        days = (a.warranty_until - today).days
        if 0 <= days <= 30:
            alerts.append({"type": "garantia", "severity": "info", "title": "Garantia expirando",
                           "message": f"{a.tag} - {a.name} em {days} dia(s)", "link": f"#/ativos/{a.id}"})
    alerts.sort(key=lambda a: SEVERITY_ORDER[a["severity"]])
    return alerts

