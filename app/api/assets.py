from flask import jsonify, request
from sqlalchemy import or_

from ..auth import require
from ..extensions import db
from ..models import Asset, CostEntry, PreventivePlan, Sensor, Ticket
from . import bp
from .common import ApiError, apply_fields, get_or_404, paginate

ASSET_FIELDS = {
    "tag": "str", "name": "str", "category": "str", "kind": "str", "sector_id": "int", "location": "str",
    "manufacturer": "str", "model": "str", "serial_number": "str", "acquisition_date": "date",
    "acquisition_cost": "float", "useful_life_years": "float", "residual_value": "float",
    "warranty_until": "date", "status": "str", "criticality": "str", "supplier_id": "int", "notes": "str",
}


@bp.get("/assets")
@require("assets.view")
def list_assets():
    a = request.args
    q = Asset.query
    if a.get("q"):
        term = f"%{a['q'].strip()}%"
        q = q.filter(or_(Asset.tag.ilike(term), Asset.name.ilike(term), Asset.manufacturer.ilike(term),
                         Asset.model.ilike(term), Asset.location.ilike(term)))
    for field in ("sector_id",):
        if a.get(field):
            q = q.filter(getattr(Asset, field) == int(a[field]))
    for field in ("category", "status", "kind", "criticality"):
        if a.get(field):
            q = q.filter(getattr(Asset, field) == a[field])
    return jsonify(paginate(q.order_by(Asset.tag), a))


@bp.get("/assets/categories")
@require("assets.view")
def asset_categories():
    rows = db.session.query(Asset.category).distinct().order_by(Asset.category).all()
    return jsonify([r[0] for r in rows])


@bp.get("/assets/<int:asset_id>")
@require("assets.view")
def get_asset(asset_id):
    asset = get_or_404(Asset, asset_id, "Ativo")
    data = asset.to_dict()
    tickets = asset.tickets.order_by(Ticket.created_at.desc()).all()
    costs = CostEntry.query.filter_by(asset_id=asset.id).all()
    data["history"] = [t.to_dict() for t in tickets]
    data["plans"] = [p.to_dict() for p in PreventivePlan.query.filter_by(asset_id=asset.id)]
    data["sensors"] = [s.to_dict() for s in Sensor.query.filter_by(asset_id=asset.id)]
    data["summary"] = {
        "tickets": len(tickets),
        "failures": sum(1 for t in tickets if t.maintenance_type in ("Corretiva", "Emergencial")),
        "maintenance_cost": round(sum(c.amount for c in costs if c.category != "Investimento"), 2),
        "labor_hours": round(sum(t.labor_hours or 0 for t in tickets), 1),
        "last_maintenance": max((t.finished_at.isoformat() for t in tickets if t.finished_at), default=None),
    }
    return jsonify(data)


@bp.post("/assets")
@require("assets.edit")
def create_asset():
    data = request.get_json(silent=True) or {}
    if data.get("tag") and Asset.query.filter_by(tag=data["tag"].strip()).first():
        raise ApiError("Já existe um ativo com este patrimônio")
    asset = apply_fields(Asset(), data, ASSET_FIELDS, required=("tag", "name", "category"))
    db.session.add(asset)
    db.session.commit()
    return jsonify(asset.to_dict()), 201


@bp.put("/assets/<int:asset_id>")
@require("assets.edit")
def update_asset(asset_id):
    asset = get_or_404(Asset, asset_id, "Ativo")
    data = request.get_json(silent=True) or {}
    if data.get("tag") and data["tag"] != asset.tag and Asset.query.filter_by(tag=data["tag"]).first():
        raise ApiError("Já existe um ativo com este patrimônio")
    apply_fields(asset, data, ASSET_FIELDS)
    db.session.commit()
    return jsonify(asset.to_dict())


@bp.delete("/assets/<int:asset_id>")
@require("assets.edit")
def delete_asset(asset_id):
    """Ativos com histórico não são apagados: são desativados (baixa patrimonial)."""
    asset = get_or_404(Asset, asset_id, "Ativo")
    if asset.tickets.count() or CostEntry.query.filter_by(asset_id=asset.id).count():
        asset.status = "Desativado"
        db.session.commit()
        return jsonify({"ok": True, "deactivated": True})
    PreventivePlan.query.filter_by(asset_id=asset.id).delete()
    db.session.delete(asset)
    db.session.commit()
    return jsonify({"ok": True, "deleted": True})
