from flask import jsonify, request

from ..auth import current_user, require
from ..constants import COST_CATEGORIES
from ..extensions import db
from ..models import CostEntry
from ..services import analytics
from . import bp
from .common import ApiError, apply_fields, get_or_404

COST_FIELDS = {"category": "str", "description": "str", "amount": "float", "date": "date", "sector_id": "int",
               "team_id": "int", "asset_id": "int", "supplier_id": "int", "contract_id": "int"}


@bp.get("/costs")
@require("costs.view")
def list_costs():
    f = analytics.parse_filters(request.args)
    items = analytics.filtered_costs(f)
    if request.args.get("category"):
        items = [c for c in items if c.category == request.args["category"]]
    items.sort(key=lambda c: (c.date, c.id), reverse=True)
    return jsonify({"items": [c.to_dict() for c in items],
                    "total_amount": round(sum(c.amount for c in items), 2),
                    "analysis": analytics.cost_analysis(f)})


@bp.post("/costs")
@require("costs.edit")
def create_cost():
    data = request.get_json(silent=True) or {}
    if data.get("category") not in COST_CATEGORIES:
        raise ApiError("Categoria de custo inválida")
    entry = apply_fields(CostEntry(created_by_id=current_user().id), data, COST_FIELDS,
                         required=("category", "description", "amount", "date"))
    db.session.add(entry)
    db.session.commit()
    return jsonify(entry.to_dict()), 201


@bp.delete("/costs/<int:cost_id>")
@require("costs.edit")
def delete_cost(cost_id):
    entry = get_or_404(CostEntry, cost_id, "Lançamento")
    if entry.ticket_id:
        raise ApiError("Custos de chamados são lançados automaticamente e não podem ser excluídos aqui")
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"ok": True})
