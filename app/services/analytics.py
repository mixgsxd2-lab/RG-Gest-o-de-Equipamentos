"""Cálculo de indicadores (dashboard, BI, análise de falhas e custos)."""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from statistics import mean

from ..constants import (ASSET_STATUSES, COST_CATEGORIES, DONE_STATUSES, IN_PROGRESS_STATUSES,
                         MAINTENANCE_TYPES, OPEN_STATUSES, PRIORITIES, TICKET_STATUSES)
from ..models import (Asset, Contract, CostEntry, PreventivePlan, Product, Sensor, Supplier, Technician,
                      Ticket)

MONTHS_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def parse_filters(args):
    today = date.today()
    try:
        days = int(args.get("days", 180))
    except (TypeError, ValueError):
        days = 180
    start = args.get("start")
    end = args.get("end")
    if start:
        start = date.fromisoformat(start)
    else:
        start = today - timedelta(days=days)
        if days >= 60:  # períodos longos começam no 1º dia do mês (sem mês parcial nos gráficos)
            start = start.replace(day=1)
    end = date.fromisoformat(end) if end else today
    return {
        "start": start,
        "end": end,
        "sector_id": int(args["sector_id"]) if args.get("sector_id") else None,
        "team_id": int(args["team_id"]) if args.get("team_id") else None,
        "maintenance_type": args.get("maintenance_type") or None,
    }


def filtered_tickets(f):
    q = Ticket.query.filter(Ticket.created_at >= datetime.combine(f["start"], datetime.min.time()),
                            Ticket.created_at < datetime.combine(f["end"] + timedelta(days=1), datetime.min.time()))
    if f.get("sector_id"):
        q = q.filter(Ticket.sector_id == f["sector_id"])
    if f.get("team_id"):
        q = q.filter(Ticket.team_id == f["team_id"])
    if f.get("maintenance_type"):
        q = q.filter(Ticket.maintenance_type == f["maintenance_type"])
    return q.all()


def filtered_costs(f):
    q = CostEntry.query.filter(CostEntry.date >= f["start"], CostEntry.date <= f["end"])
    if f.get("sector_id"):
        q = q.filter(CostEntry.sector_id == f["sector_id"])
    if f.get("team_id"):
        q = q.filter(CostEntry.team_id == f["team_id"])
    return q.all()


def _avg(values):
    values = [v for v in values if v is not None]
    return round(mean(values), 1) if values else 0


def _pct(part, total):
    return round(100 * part / total, 1) if total else 0


def month_keys(start, end):
    keys, cur = [], date(start.year, start.month, 1)
    while cur <= end:
        keys.append(cur.strftime("%Y-%m"))
        cur = date(cur.year + (cur.month // 12), cur.month % 12 + 1, 1)
    return keys


def month_label(key):
    y, m = key.split("-")
    return f"{MONTHS_PT[int(m) - 1]}/{y[2:]}"


def sla_stats(tickets):
    finished = [t for t in tickets if t.finished_at and t.sla_due_at]
    met = sum(1 for t in finished if t.finished_at <= t.sla_due_at)
    return {"evaluated": len(finished), "met": met, "compliance": _pct(met, len(finished))}


def technician_productivity(tickets):
    rows = {}
    for tech in Technician.query.filter_by(active=True).all():
        rows[tech.id] = {"id": tech.id, "name": tech.name, "team": tech.team.name if tech.team else None,
                         "specialty": tech.specialty, "external": tech.supplier_id is not None,
                         "assigned": 0, "finished": 0, "in_progress": 0, "hours": 0.0,
                         "_res": [], "_sla": []}
    for t in tickets:
        if t.operator_id not in rows:
            continue
        r = rows[t.operator_id]
        r["assigned"] += 1
        if t.status in DONE_STATUSES:
            r["finished"] += 1
            r["_res"].append(t.resolution_hours)
            if t.sla_due_at and t.finished_at:
                r["_sla"].append(t.finished_at <= t.sla_due_at)
        elif t.status in IN_PROGRESS_STATUSES:
            r["in_progress"] += 1
        r["hours"] += t.labor_hours or 0
    out = []
    for r in rows.values():
        r["avg_resolution_hours"] = _avg(r.pop("_res"))
        sla = r.pop("_sla")
        r["sla_compliance"] = _pct(sum(sla), len(sla))
        r["hours"] = round(r["hours"], 1)
        out.append(r)
    return sorted(out, key=lambda r: (-r["finished"], -r["hours"]))


def supplier_performance(tickets, costs):
    rows = {}
    for s in Supplier.query.filter_by(active=True).all():
        contracts = [c for c in s.contracts if c.status in ("Vigente", "A vencer")]
        rows[s.id] = {"id": s.id, "name": s.name, "category": s.category, "rating": s.rating,
                      "tickets": 0, "finished": 0, "_res": [], "_sla": [], "cost": 0.0,
                      "active_contracts": len(contracts),
                      "contract_monthly": round(sum(c.monthly_value or 0 for c in contracts), 2)}
    for t in tickets:
        if t.supplier_id in rows:
            r = rows[t.supplier_id]
            r["tickets"] += 1
            if t.finished_at:
                r["finished"] += 1
                r["_res"].append(t.resolution_hours)
                if t.sla_due_at:
                    r["_sla"].append(t.finished_at <= t.sla_due_at)
    for c in costs:
        if c.supplier_id in rows and c.category in ("Terceiros", "Contrato"):
            rows[c.supplier_id]["cost"] += c.amount
    out = []
    for r in rows.values():
        r["avg_resolution_hours"] = _avg(r.pop("_res"))
        sla = r.pop("_sla")
        r["sla_compliance"] = _pct(sum(sla), len(sla)) if sla else None
        r["cost"] = round(r["cost"], 2)
        # Índice de desempenho (0-100): SLA 50% + avaliação 30% + conclusão 20%
        sla_score = r["sla_compliance"] if r["sla_compliance"] is not None else 80
        done_score = _pct(r["finished"], r["tickets"]) if r["tickets"] else 80
        r["score"] = round(0.5 * sla_score + 0.3 * (r["rating"] or 0) * 20 + 0.2 * done_score, 1)
        out.append(r)
    return sorted(out, key=lambda r: -r["score"])


def preventive_summary():
    plans = PreventivePlan.query.filter_by(active=True).all()
    today = date.today()
    overdue = [p for p in plans if p.next_due < today]
    next7 = [p for p in plans if today <= p.next_due <= today + timedelta(days=7)]
    next30 = [p for p in plans if today <= p.next_due <= today + timedelta(days=30)]
    prev = Ticket.query.filter(Ticket.preventive_plan_id.isnot(None)).all()
    done = [t for t in prev if t.finished_at]
    on_time = sum(1 for t in done if t.sla_due_at and t.finished_at <= t.sla_due_at)
    return {
        "total_plans": len(plans),
        "overdue": len(overdue),
        "next_7_days": len(next7),
        "next_30_days": len(next30),
        "up_to_date": len(plans) - len(overdue),
        "compliance": _pct(len(plans) - len(overdue), len(plans)),
        "executed": len(done),
        "executed_on_time": _pct(on_time, len(done)),
        "upcoming": [p.to_dict() for p in sorted(overdue + next7, key=lambda p: p.next_due)[:8]],
    }


def stock_summary():
    products = Product.query.filter_by(active=True).all()
    below = [p for p in products if p.below_minimum]
    return {
        "items": len(products),
        "total_value": round(sum((p.quantity or 0) * (p.unit_cost or 0) for p in products), 2),
        "below_minimum": len(below),
        "below_list": [p.to_dict() for p in sorted(below, key=lambda p: (p.quantity or 0) - (p.min_stock or 0))[:8]],
    }


def dashboard(f):
    tickets = filtered_tickets(f)
    costs = filtered_costs(f)
    status_counts = Counter(t.status for t in tickets)
    sla = sla_stats(tickets)
    active = [t for t in tickets if t.status not in DONE_STATUSES + ["cancelado"]]

    months = month_keys(f["start"], f["end"])
    opened_m = Counter(t.created_at.strftime("%Y-%m") for t in tickets)
    finished_m = Counter(t.finished_at.strftime("%Y-%m") for t in tickets if t.finished_at)
    cost_month_cat = defaultdict(lambda: defaultdict(float))
    for c in costs:
        cost_month_cat[c.date.strftime("%Y-%m")][c.category] += c.amount
    sla_month = defaultdict(list)
    for t in tickets:
        if t.finished_at and t.sla_due_at:
            sla_month[t.finished_at.strftime("%Y-%m")].append(t.finished_at <= t.sla_due_at)

    by_sector = Counter(t.sector.name if t.sector else "Não informado" for t in tickets).most_common(12)
    by_team = Counter(t.team.name if t.team else "—" for t in tickets).most_common()
    cost_by_cat = defaultdict(float)
    for c in costs:
        cost_by_cat[c.category] += c.amount
    cost_by_sector = defaultdict(float)
    for c in costs:
        cost_by_sector[c.sector.name if c.sector else "Geral / Contratos"] += c.amount

    assets = Asset.query.all()
    asset_status = Counter(a.status for a in assets)
    sensors = Sensor.query.filter_by(active=True).all()

    total_cost = round(sum(c.amount for c in costs), 2)
    return {
        "filters": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in f.items()},
        "kpis": {
            "total": len(tickets),
            "open": sum(status_counts[s] for s in OPEN_STATUSES),
            "in_progress": sum(status_counts[s] for s in IN_PROGRESS_STATUSES),
            "waiting": status_counts["aguardando"],
            "finished": sum(status_counts[s] for s in DONE_STATUSES),
            "cancelled": status_counts["cancelado"],
            "sla_compliance": sla["compliance"],
            "sla_evaluated": sla["evaluated"],
            "sla_violated_open": sum(1 for t in active if t.sla_status == "violado"),
            "sla_at_risk": sum(1 for t in active if t.sla_status == "em_risco"),
            "avg_resolution_hours": _avg([t.resolution_hours for t in tickets]),
            "avg_response_hours": _avg([t.response_hours for t in tickets]),
            "total_cost": total_cost,
            "avg_cost_per_ticket": round(total_cost / len([t for t in tickets if t.finished_at]), 2)
            if any(t.finished_at for t in tickets) else 0,
            "labor_hours": round(sum(t.labor_hours or 0 for t in tickets), 1),
            "satisfaction": _avg([t.satisfaction for t in tickets]),
            "assets_total": len(assets),
            "assets_operational": asset_status["Operacional"],
            "assets_down": asset_status["Inoperante"] + asset_status["Em manutenção"],
            "availability": _pct(asset_status["Operacional"] + asset_status["Reserva"],
                                 len([a for a in assets if a.status != "Desativado"])),
            "sensors_alert": sum(1 for s in sensors if s.state == "alerta"),
        },
        "charts": {
            "by_status": [{"key": k, "label": v, "value": status_counts[k]} for k, v in TICKET_STATUSES.items()],
            "by_type": [{"label": t, "value": sum(1 for x in tickets if x.maintenance_type == t)}
                        for t in MAINTENANCE_TYPES],
            "by_priority": [{"label": p, "value": sum(1 for x in tickets if x.priority == p)} for p in PRIORITIES],
            "by_sector": [{"label": k, "value": v} for k, v in by_sector],
            "by_team": [{"label": k, "value": v} for k, v in by_team],
            "monthly": {
                "labels": [month_label(m) for m in months],
                "opened": [opened_m[m] for m in months],
                "finished": [finished_m[m] for m in months],
                "sla": [_pct(sum(sla_month[m]), len(sla_month[m])) if sla_month[m] else None for m in months],
            },
            "costs_by_category": [{"label": c, "value": round(cost_by_cat[c], 2)} for c in COST_CATEGORIES],
            "costs_by_sector": [{"label": k, "value": round(v, 2)}
                                for k, v in sorted(cost_by_sector.items(), key=lambda x: -x[1])[:10]],
            "costs_monthly": {
                "labels": [month_label(m) for m in months],
                "series": [{"label": c, "data": [round(cost_month_cat[m][c], 2) for m in months]}
                           for c in COST_CATEGORIES],
            },
            "assets_by_status": [{"label": s, "value": asset_status[s]} for s in ASSET_STATUSES],
        },
        "productivity": technician_productivity(tickets),
        "suppliers": supplier_performance(tickets, costs),
        "preventive": preventive_summary(),
        "stock": stock_summary(),
        "recent": [t.to_dict() for t in sorted(active, key=lambda t: t.created_at, reverse=True)[:8]],
    }


# ---------------------------------------------------------------------------
# Inteligência: análise de falhas, depreciação, custos
# ---------------------------------------------------------------------------
FAILURE_TYPES = ("Corretiva", "Emergencial")


def failure_analysis(f):
    tickets = [t for t in filtered_tickets(f) if t.maintenance_type in FAILURE_TYPES]
    period_hours = max(1, ((f["end"] - f["start"]).days + 1) * 24)
    per_asset = defaultdict(list)
    for t in tickets:
        if t.asset_id:
            per_asset[t.asset_id].append(t)
    assets = []
    for asset_id, items in per_asset.items():
        asset = items[0].asset
        repair = [t.resolution_hours for t in items if t.resolution_hours is not None]
        downtime = sum(repair)
        n = len(items)
        mttr = round(downtime / len(repair), 1) if repair else None
        mtbf = round((period_hours - downtime) / n, 1) if n else None
        assets.append({
            "asset_id": asset_id,
            "tag": asset.tag,
            "name": asset.name,
            "category": asset.category,
            "sector": asset.sector.name if asset.sector else None,
            "failures": n,
            "mttr_hours": mttr,
            "mtbf_hours": mtbf,
            "availability": round(100 * (period_hours - downtime) / period_hours, 2),
            "cost": round(sum(t.total_cost for t in items), 2),
        })
    assets.sort(key=lambda a: (-a["failures"], -a["cost"]))
    causes = Counter(t.failure_cause or "Não classificada" for t in tickets if t.finished_at)
    by_category = Counter(t.asset.category for t in tickets if t.asset)
    total = sum(causes.values())
    pareto, acc = [], 0
    for cause, count in causes.most_common():
        acc += count
        pareto.append({"label": cause, "value": count, "cumulative": _pct(acc, total)})
    return {
        "total_failures": len(tickets),
        "assets": assets[:20],
        "pareto_causes": pareto,
        "by_category": [{"label": k, "value": v} for k, v in by_category.most_common(10)],
    }


def depreciation_summary():
    by_cat = defaultdict(lambda: {"assets": 0, "acquisition": 0.0, "book_value": 0.0, "accumulated": 0.0,
                                  "annual": 0.0})
    near_end = []
    for a in Asset.query.filter(Asset.status != "Desativado").all():
        d = a.depreciation()
        r = by_cat[a.category]
        r["assets"] += 1
        r["acquisition"] += a.acquisition_cost or 0
        r["book_value"] += d["book_value"]
        r["accumulated"] += d["accumulated"]
        r["annual"] += d["annual"]
        if d["remaining_years"] <= 1.5 and (a.acquisition_cost or 0) > 0:
            near_end.append({**a.to_dict(), "depreciation": d})
    rows = [{"category": k, **{kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}}
            for k, v in by_cat.items()]
    rows.sort(key=lambda r: -r["acquisition"])
    totals = {k: round(sum(r[k] for r in rows), 2) for k in ("acquisition", "book_value", "accumulated", "annual")}
    return {"by_category": rows, "totals": totals,
            "end_of_life": sorted(near_end, key=lambda a: a["depreciation"]["remaining_years"])[:15]}


def cost_analysis(f):
    tickets = filtered_tickets(f)
    costs = filtered_costs(f)
    by_type = defaultdict(float)
    for t in tickets:
        by_type[t.maintenance_type] += t.total_cost
    by_asset = defaultdict(float)
    for c in costs:
        if c.asset:
            by_asset[f"{c.asset.tag} - {c.asset.name}"] += c.amount
    by_supplier = defaultdict(float)
    for c in costs:
        if c.supplier:
            by_supplier[c.supplier.name] += c.amount
    contracts = Contract.query.all()
    return {
        "total": round(sum(c.amount for c in costs), 2),
        "by_category": [{"label": k, "value": round(sum(c.amount for c in costs if c.category == k), 2)}
                        for k in COST_CATEGORIES],
        "by_maintenance_type": [{"label": k, "value": round(by_type[k], 2)} for k in MAINTENANCE_TYPES],
        "top_assets": [{"label": k, "value": round(v, 2)}
                       for k, v in sorted(by_asset.items(), key=lambda x: -x[1])[:10]],
        "by_supplier": [{"label": k, "value": round(v, 2)}
                        for k, v in sorted(by_supplier.items(), key=lambda x: -x[1])[:10]],
        "contracts_monthly_total": round(sum(c.monthly_value or 0 for c in contracts
                                             if c.status in ("Vigente", "A vencer")), 2),
        "preventive_vs_corrective": {
            "preventive": round(sum(t.total_cost for t in tickets
                                    if t.maintenance_type in ("Preventiva", "Preditiva", "Inspeção", "Calibração")), 2),
            "corrective": round(sum(t.total_cost for t in tickets if t.maintenance_type in FAILURE_TYPES), 2),
        },
    }
