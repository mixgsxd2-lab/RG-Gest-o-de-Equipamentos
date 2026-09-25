"""Indicadores e inteligência: análise de falhas, custos, depreciação,
manutenção preditiva e exportação de dados para BI / Big Data / ML."""
import csv
import io

from flask import Response, jsonify, request

from ..auth import require
from ..models import Asset, CostEntry, StockMovement, Ticket, WorkLog
from ..services import analytics, predictive
from . import bp
from .common import ApiError


@bp.get("/intelligence/failures")
@require("indicators.view")
def failures():
    return jsonify(analytics.failure_analysis(analytics.parse_filters(request.args)))


@bp.get("/intelligence/costs")
@require("indicators.view")
def costs():
    return jsonify(analytics.cost_analysis(analytics.parse_filters(request.args)))


@bp.get("/intelligence/depreciation")
@require("indicators.view")
def depreciation():
    return jsonify(analytics.depreciation_summary())


@bp.get("/intelligence/predictive")
@require("iot.view")
def predictive_view():
    return jsonify(predictive.predictive_ranking(int(request.args.get("limit", 25))))


def _flat(d):
    return {k: v for k, v in d.items() if not isinstance(v, (dict, list))}


DATASETS = {
    "chamados": lambda: [_flat(t.to_dict(detail=True)) for t in Ticket.query.order_by(Ticket.id)],
    "ativos": lambda: [{**_flat(a.to_dict()), **{f"depreciacao_{k}": v for k, v in a.depreciation().items()}}
                       for a in Asset.query.order_by(Asset.id)],
    "custos": lambda: [c.to_dict() for c in CostEntry.query.order_by(CostEntry.date)],
    "movimentos_estoque": lambda: [m.to_dict() for m in StockMovement.query.order_by(StockMovement.created_at)],
    "apontamentos": lambda: [{"ticket_id": w.ticket_id, **w.to_dict()} for w in WorkLog.query.order_by(WorkLog.id)],
    "ml_features": predictive.feature_dataset,
}


@bp.get("/intelligence/datasets")
@require("indicators.view")
def datasets():
    return jsonify(sorted(DATASETS))


@bp.get("/intelligence/export/<name>.<fmt>")
@require("indicators.view")
def export(name, fmt):
    """Exportação em CSV (Excel/Power BI) ou JSON (Big Data / APIs)."""
    if name not in DATASETS or fmt not in ("csv", "json"):
        raise ApiError("Conjunto de dados ou formato inválido", 404)
    rows = DATASETS[name]()
    if fmt == "json":
        return jsonify(rows)
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return Response("﻿" + buf.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename=rg_{name}.csv"})
