from flask import current_app, jsonify, request

from ..auth import current_user, login_required, require
from ..constants import (ASSET_KINDS, ASSET_STATUSES, COST_CATEGORIES, CRITICALITIES, MAINTENANCE_TYPES,
                         PRIORITIES, ROLES, SENSOR_KINDS, SLA_EMERGENCY_HOURS, SLA_HOURS, TICKET_STATUSES)
from ..models import Asset, Product, Sector, Supplier, Team, Technician
from ..services import analytics
from ..services.alerts import build_alerts
from . import bp


@bp.get("/lookups")
@login_required
def lookups():
    """Listas usadas em formulários e filtros da interface."""
    return jsonify({
        "demo": current_app.config["DEMO_MODE"],
        "sectors": [s.to_dict() for s in Sector.query.order_by(Sector.name)],
        "teams": [t.to_dict() for t in Team.query.order_by(Team.name)],
        "technicians": [{"id": t.id, "name": t.name, "team_id": t.team_id, "specialty": t.specialty,
                         "external": t.supplier_id is not None}
                        for t in Technician.query.filter_by(active=True).order_by(Technician.name)],
        "suppliers": [{"id": s.id, "name": s.name, "category": s.category}
                      for s in Supplier.query.filter_by(active=True).order_by(Supplier.name)],
        "assets": [{"id": a.id, "tag": a.tag, "name": a.name, "sector_id": a.sector_id, "location": a.location}
                   for a in Asset.query.filter(Asset.status != "Desativado").order_by(Asset.tag)],
        "products": [{"id": p.id, "code": p.code, "name": p.name, "unit": p.unit, "quantity": p.quantity,
                      "unit_cost": p.unit_cost}
                     for p in Product.query.filter_by(active=True).order_by(Product.name)],
        "maintenance_types": MAINTENANCE_TYPES,
        "priorities": PRIORITIES,
        "criticalities": CRITICALITIES,
        "statuses": TICKET_STATUSES,
        "asset_statuses": ASSET_STATUSES,
        "asset_kinds": ASSET_KINDS,
        "cost_categories": COST_CATEGORIES,
        "sensor_kinds": SENSOR_KINDS,
        "roles": ROLES,
        "sla_hours": {**SLA_HOURS, "Emergencial": SLA_EMERGENCY_HOURS},
    })


@bp.get("/dashboard")
@require("dashboard.view")
def dashboard():
    return jsonify(analytics.dashboard(analytics.parse_filters(request.args)))


@bp.get("/alerts")
@login_required
def alerts():
    user = current_user()
    items = build_alerts(user)
    if user.role == "solicitante":
        items = []
    elif user.role == "estoque":
        items = [a for a in items if a["type"] == "estoque"]
    return jsonify({"items": items, "total": len(items)})
