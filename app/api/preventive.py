from datetime import date, datetime, timedelta

from flask import jsonify, request

from ..auth import current_user, require
from ..extensions import db
from ..models import PreventivePlan, Ticket
from ..services import tickets as svc
from . import bp
from .common import ApiError, apply_fields, get_or_404

PLAN_FIELDS = {
    "name": "str", "asset_id": "int", "team_id": "int", "technician_id": "int", "supplier_id": "int",
    "maintenance_type": "str", "frequency_days": "int", "last_done": "date", "next_due": "date",
    "estimated_hours": "float", "checklist": "str", "active": "bool",
}


@bp.get("/preventive")
@require("preventive.view")
def list_plans():
    q = PreventivePlan.query
    if request.args.get("team_id"):
        q = q.filter_by(team_id=int(request.args["team_id"]))
    plans = [p.to_dict() for p in q.order_by(PreventivePlan.next_due)]
    if request.args.get("situation"):
        plans = [p for p in plans if p["situation"] == request.args["situation"]]
    return jsonify(plans)


@bp.get("/preventive/calendar")
@require("preventive.view")
def calendar():
    """Projeta as ocorrências dos planos ativos no intervalo solicitado."""
    start = date.fromisoformat(request.args.get("start") or date.today().replace(day=1).isoformat())
    end = date.fromisoformat(request.args.get("end") or (start + timedelta(days=41)).isoformat())
    events = []
    for p in PreventivePlan.query.filter_by(active=True).all():
        due = p.next_due
        # ocorrências atrasadas aparecem no dia do vencimento
        while due <= end:
            if due >= start:
                events.append({"plan_id": p.id, "date": due.isoformat(), "title": p.name,
                               "type": p.maintenance_type, "team": p.team.name if p.team else None,
                               "asset": p.asset.tag if p.asset else None,
                               "situation": p.situation if due == p.next_due else "Programada"})
            due += timedelta(days=max(1, p.frequency_days))
    # preventivas já executadas no período
    done = Ticket.query.filter(Ticket.preventive_plan_id.isnot(None), Ticket.finished_at.isnot(None),
                               Ticket.finished_at >= datetime.combine(start, datetime.min.time()),
                               Ticket.finished_at <= datetime.combine(end, datetime.max.time())).all()
    for t in done:
        events.append({"plan_id": t.preventive_plan_id, "ticket_id": t.id, "date": t.finished_at.date().isoformat(),
                       "title": t.title, "type": t.maintenance_type, "team": t.team.name if t.team else None,
                       "asset": t.asset.tag if t.asset else None, "situation": "Executada"})
    return jsonify(sorted(events, key=lambda e: e["date"]))


@bp.post("/preventive")
@require("preventive.edit")
def create_plan():
    data = request.get_json(silent=True) or {}
    plan = apply_fields(PreventivePlan(), data, PLAN_FIELDS, required=("name", "team_id", "frequency_days"))
    if not plan.next_due:
        plan.next_due = (plan.last_done or date.today()) + timedelta(days=plan.frequency_days)
    db.session.add(plan)
    db.session.commit()
    return jsonify(plan.to_dict()), 201


@bp.put("/preventive/<int:plan_id>")
@require("preventive.edit")
def update_plan(plan_id):
    plan = get_or_404(PreventivePlan, plan_id, "Plano")
    apply_fields(plan, request.get_json(silent=True) or {}, PLAN_FIELDS)
    db.session.commit()
    return jsonify(plan.to_dict())


@bp.delete("/preventive/<int:plan_id>")
@require("preventive.edit")
def delete_plan(plan_id):
    plan = get_or_404(PreventivePlan, plan_id, "Plano")
    plan.active = False
    db.session.commit()
    return jsonify({"ok": True})


@bp.post("/preventive/<int:plan_id>/generate")
@require("preventive.edit")
def generate_ticket(plan_id):
    """Gera a ordem de serviço preventiva a partir do plano."""
    plan = get_or_404(PreventivePlan, plan_id, "Plano")
    if plan.to_dict()["open_ticket_id"]:
        raise ApiError("Já existe uma OS em aberto para este plano")
    user = current_user()
    ticket = svc.create_ticket({
        "title": plan.ticket_title,
        "description": (plan.checklist or "Executar plano de manutenção programada.")
        + f"\n\nPeriodicidade: a cada {plan.frequency_days} dias. Previsto para {plan.next_due:%d/%m/%Y}.",
        "maintenance_type": plan.maintenance_type,
        "priority": "Alta" if plan.situation == "Atrasada" else "Média",
        "criticality": plan.asset.criticality if plan.asset else "Média",
        "team_id": plan.team_id,
        "asset_id": plan.asset_id,
        "preventive_plan_id": plan.id,
    }, user)
    if plan.technician_id:
        svc.apply_action(ticket, "assign", user, {"technician_id": plan.technician_id})
    db.session.commit()
    return jsonify(ticket.to_dict()), 201
