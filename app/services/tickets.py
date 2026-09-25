"""Regras de negócio do ciclo de vida do chamado.

Fluxo: Aberto → Recebido → Aceito → Em execução → Aguardando material/terceiro
→ Finalizado → Encerrado. Toda ação gera um ``TicketEvent`` (histórico).
"""
from datetime import datetime, timedelta

from ..auth import can
from ..constants import MAINTENANCE_TYPES, PRIORITIES, CRITICALITIES, SLA_EMERGENCY_HOURS, SLA_HOURS
from ..extensions import db
from ..models import (Asset, CostEntry, Product, StockMovement, Technician, Ticket, TicketEvent,
                      TicketMaterial, WorkLog)


class WorkflowError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


AUTO_COST_CATEGORIES = ("Material", "Mão de obra", "Terceiros")


def br_num(value, decimals=2):
    """Formata número no padrão brasileiro (1.234,56)."""
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def sla_hours_for(priority, maintenance_type):
    if maintenance_type == "Emergencial":
        return SLA_EMERGENCY_HOURS
    return SLA_HOURS.get(priority, 24)


def next_code(at=None):
    year = (at or datetime.now()).year
    prefix = f"CH-{year}-"
    last = (Ticket.query.filter(Ticket.code.like(prefix + "%"))
            .order_by(Ticket.code.desc()).first())
    seq = int(last.code.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{seq:04d}"


def log_event(ticket, user, action, note=None, from_status=None, to_status=None, at=None):
    ev = TicketEvent(ticket=ticket, user=user, action=action, note=note,
                     from_status=from_status, to_status=to_status, created_at=at or datetime.now())
    db.session.add(ev)
    return ev


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except ValueError:
        raise WorkflowError(f"Data/hora inválida: {value}")


def create_ticket(data, user, at=None):
    at = at or datetime.now()
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    mtype = data.get("maintenance_type") or "Corretiva"
    priority = data.get("priority") or "Média"
    criticality = data.get("criticality") or "Média"
    if not title or not description:
        raise WorkflowError("Informe título e descrição do chamado")
    if not data.get("team_id"):
        raise WorkflowError("Selecione o setor de manutenção responsável")
    if mtype not in MAINTENANCE_TYPES:
        raise WorkflowError("Tipo de manutenção inválido")
    if priority not in PRIORITIES or criticality not in CRITICALITIES:
        raise WorkflowError("Prioridade ou criticidade inválida")

    asset = db.session.get(Asset, int(data["asset_id"])) if data.get("asset_id") else None
    sector_id = data.get("sector_id") or (asset.sector_id if asset else None) or user.sector_id
    hours = sla_hours_for(priority, mtype)
    ticket = Ticket(
        code=next_code(at),
        title=title,
        description=description,
        maintenance_type=mtype,
        priority=priority,
        criticality=criticality,
        status="aberto",
        team_id=int(data["team_id"]),
        sector_id=int(sector_id) if sector_id else None,
        location=data.get("location") or (asset.location if asset else None),
        asset=asset,
        preventive_plan_id=data.get("preventive_plan_id"),
        requester=user,
        sla_hours=hours,
        sla_due_at=at + timedelta(hours=hours),
        created_at=at,
        updated_at=at,
    )
    db.session.add(ticket)
    log_event(ticket, user, "Chamado aberto", note=f"{mtype} · Prioridade {priority}", to_status="aberto", at=at)
    return ticket


def _technician_for(user):
    return Technician.query.filter_by(user_id=user.id).first()


def _is_operator(ticket, user):
    return ticket.operator is not None and ticket.operator.user_id == user.id


def _ensure_execute(ticket, user):
    if can(user, "tickets.manage"):
        return
    if not can(user, "tickets.execute") or not _is_operator(ticket, user):
        raise WorkflowError("Somente o operador do chamado ou a gestão pode executar esta ação", 403)


def _set_status(ticket, new_status, user, action, note=None, at=None):
    old = ticket.status
    ticket.status = new_status
    ticket.updated_at = at or datetime.now()
    log_event(ticket, user, action, note=note, from_status=old, to_status=new_status, at=at)


def recalc_costs(ticket):
    ticket.labor_hours = round(sum(w.hours for w in ticket.worklogs), 2)
    ticket.labor_cost = round(sum(w.cost or 0 for w in ticket.worklogs), 2)
    ticket.material_cost = round(sum(m.quantity * (m.unit_cost or 0) for m in ticket.materials), 2)


def post_costs(ticket, when=None):
    """Lança os custos do chamado no livro de custos (idempotente)."""
    CostEntry.query.filter(CostEntry.ticket_id == ticket.id,
                           CostEntry.category.in_(AUTO_COST_CATEGORIES)).delete(synchronize_session=False)
    day = (when or ticket.finished_at or datetime.now()).date()
    base = dict(date=day, sector_id=ticket.sector_id, team_id=ticket.team_id,
                asset_id=ticket.asset_id, ticket_id=ticket.id)
    if ticket.labor_cost:
        db.session.add(CostEntry(category="Mão de obra", amount=ticket.labor_cost,
                                 description=f"Mão de obra {ticket.code} ({ticket.labor_hours} h)", **base))
    if ticket.material_cost:
        db.session.add(CostEntry(category="Material", amount=ticket.material_cost,
                                 description=f"Materiais {ticket.code}", **base))
    if ticket.third_party_cost:
        db.session.add(CostEntry(category="Terceiros", amount=ticket.third_party_cost,
                                 supplier_id=ticket.supplier_id,
                                 description=f"Serviço de terceiro {ticket.code}", **base))


def add_worklog(ticket, user, data, at=None):
    _ensure_execute(ticket, user)
    if ticket.status not in ("aceito", "em_execucao", "aguardando", "finalizado"):
        raise WorkflowError("Apontamentos só podem ser feitos em chamados aceitos ou em execução")
    start = _parse_dt(data.get("started_at"))
    end = _parse_dt(data.get("ended_at"))
    if not start or not end or end <= start:
        raise WorkflowError("Informe início e término válidos (término após o início)")
    tech = None
    if data.get("technician_id"):
        tech = db.session.get(Technician, int(data["technician_id"]))
    tech = tech or ticket.operator or _technician_for(user)
    hours = round((end - start).total_seconds() / 3600, 2)
    rate = tech.hourly_rate if tech else 0
    log = WorkLog(ticket=ticket, technician=tech, started_at=start, ended_at=end, hours=hours,
                  cost=round(hours * (rate or 0), 2), description=data.get("description"))
    db.session.add(log)
    if not ticket.started_at or start < ticket.started_at:
        ticket.started_at = start
    recalc_costs(ticket)
    log_event(ticket, user, "Apontamento de horas",
              note=f"{br_num(hours)} h — {data.get('description') or ''}".strip(" —"), at=at)
    return log


def add_material(ticket, user, data, at=None):
    _ensure_execute(ticket, user)
    if ticket.status not in ("aceito", "em_execucao", "aguardando"):
        raise WorkflowError("Materiais só podem ser lançados durante a execução")
    try:
        qty = float(data.get("quantity") or 0)
    except (TypeError, ValueError):
        raise WorkflowError("Quantidade inválida")
    if qty <= 0:
        raise WorkflowError("Quantidade deve ser maior que zero")
    if data.get("product_id"):
        product = db.session.get(Product, int(data["product_id"]))
        if product is None:
            raise WorkflowError("Produto não encontrado", 404)
        if product.quantity < qty:
            raise WorkflowError(f"Estoque insuficiente de {product.name} (disponível: {br_num(product.quantity, 0)})")
        product.quantity -= qty
        item = TicketMaterial(ticket=ticket, product=product, quantity=qty, unit_cost=product.unit_cost,
                              created_at=at or datetime.now())
        db.session.add(StockMovement(product=product, kind="saida", quantity=qty, unit_cost=product.unit_cost,
                                     ticket=ticket, user=user, note=f"Consumo no chamado {ticket.code}",
                                     created_at=at or datetime.now()))
        label = f"{br_num(qty, 2 if qty % 1 else 0)} {product.unit} de {product.name}"
    else:
        desc = (data.get("description") or "").strip()
        if not desc:
            raise WorkflowError("Selecione um produto do estoque ou descreva o material")
        item = TicketMaterial(ticket=ticket, description=desc, quantity=qty,
                              unit_cost=float(data.get("unit_cost") or 0), created_at=at or datetime.now())
        label = f"{br_num(qty, 2 if qty % 1 else 0)} × {desc} (fora do estoque)"
    db.session.add(item)
    recalc_costs(ticket)
    log_event(ticket, user, "Material utilizado", note=label, at=at)
    return item


def _update_asset_status(ticket, starting):
    asset = ticket.asset
    if asset is None or asset.status == "Desativado":
        return
    if starting:
        if ticket.maintenance_type in ("Corretiva", "Emergencial") or ticket.criticality in ("Alta", "Crítica"):
            asset.status = "Em manutenção"
        return
    others = (Ticket.query.filter(Ticket.asset_id == asset.id, Ticket.id != ticket.id,
                                  Ticket.status.in_(["em_execucao", "aguardando"])).count())
    if others == 0 and asset.status in ("Em manutenção", "Inoperante"):
        asset.status = "Operacional"


ACTIONS = ("receive", "assign", "accept", "start", "wait", "resume", "finish", "close", "reopen", "cancel",
           "update")


def available_actions(ticket, user):
    """Ações que o usuário pode executar no chamado (usado pela interface)."""
    manage = can(user, "tickets.manage")
    execute = can(user, "tickets.execute")
    is_op = _is_operator(ticket, user)
    is_req = ticket.requester_id == user.id
    s = ticket.status
    acts = []
    if s == "aberto" and manage:
        acts.append("receive")
    if s in ("aberto", "recebido", "aceito") and manage:
        acts.append("assign")
    if s in ("aberto", "recebido") and execute and (manage or ticket.operator is None or is_op):
        acts.append("accept")
    if s == "aceito" and (manage or is_op):
        acts.append("start")
    if s == "em_execucao" and (manage or is_op):
        acts += ["wait", "finish"]
    if s == "aguardando" and (manage or is_op):
        acts.append("resume")
    if s in ("aceito", "em_execucao", "aguardando") and (manage or is_op):
        acts += ["worklog", "material"]
    if s == "finalizado" and (manage or is_req):
        acts += ["close", "reopen"]
    if (s in ("aberto", "recebido", "aceito") and manage) or (s == "aberto" and is_req):
        acts.append("cancel")
    if manage and s not in ("encerrado", "cancelado"):
        acts.append("update")
    if s not in ("cancelado",):
        acts.append("attach")
    return acts


def apply_action(ticket, action, user, data, at=None):
    at = at or datetime.now()
    if action not in ACTIONS:
        raise WorkflowError("Ação desconhecida")
    if action not in available_actions(ticket, user):
        raise WorkflowError("Ação não permitida para o status atual ou para o seu perfil", 403)
    note = (data.get("note") or "").strip() or None

    if action == "receive":
        ticket.receiver = user
        ticket.received_at = at
        _set_status(ticket, "recebido", user, "Chamado recebido", note, at)

    elif action == "assign":
        tech = db.session.get(Technician, int(data.get("technician_id") or 0))
        if tech is None:
            raise WorkflowError("Selecione o técnico/operador")
        ticket.operator = tech
        if ticket.receiver is None:
            ticket.receiver = user
            ticket.received_at = at
        if ticket.status == "aberto":
            _set_status(ticket, "recebido", user, "Chamado recebido", None, at)
        log_event(ticket, user, "Técnico designado", note=f"{tech.name}" + (f" — {note}" if note else ""), at=at)

    elif action == "accept":
        tech = ticket.operator if ticket.operator and _is_operator(ticket, user) else _technician_for(user)
        if data.get("technician_id") and can(user, "tickets.manage"):
            tech = db.session.get(Technician, int(data["technician_id"]))
        if tech is None:
            raise WorkflowError("Seu usuário não está vinculado a um técnico. Informe o técnico.")
        ticket.operator = tech
        if ticket.receiver is None:
            ticket.receiver = user
            ticket.received_at = at
        ticket.accepted_at = at
        _set_status(ticket, "aceito", user, "Chamado aceito", note or f"Operador: {tech.name}", at)

    elif action == "start":
        ticket.started_at = _parse_dt(data.get("started_at")) or at
        _update_asset_status(ticket, starting=True)
        _set_status(ticket, "em_execucao", user, "Execução iniciada", note, at)

    elif action == "wait":
        reason = data.get("waiting_reason") or "Material"
        if reason not in ("Material", "Terceiro"):
            raise WorkflowError("Motivo de espera inválido")
        ticket.waiting_reason = reason
        if reason == "Terceiro" and data.get("supplier_id"):
            ticket.supplier_id = int(data["supplier_id"])
        _set_status(ticket, "aguardando", user, f"Aguardando {reason.lower()}", note, at)

    elif action == "resume":
        ticket.waiting_reason = None
        _set_status(ticket, "em_execucao", user, "Execução retomada", note, at)

    elif action == "finish":
        solution = (data.get("solution") or ticket.solution or "").strip()
        if not solution:
            raise WorkflowError("Descreva o que foi feito para finalizar o chamado")
        ticket.solution = solution
        for field in ("diagnosis", "observations", "failure_cause"):
            if data.get(field) is not None:
                setattr(ticket, field, data.get(field))
        if data.get("supplier_id"):
            ticket.supplier_id = int(data["supplier_id"])
        if data.get("third_party_cost") not in (None, ""):
            ticket.third_party_cost = float(data["third_party_cost"])
        finished = _parse_dt(data.get("finished_at")) or at
        # Se não houve apontamento, registra um a partir das horas informadas
        if not ticket.worklogs and data.get("labor_hours"):
            hours = float(data["labor_hours"])
            start = ticket.started_at or finished - timedelta(hours=hours)
            add_worklog(ticket, user, {"started_at": start, "ended_at": start + timedelta(hours=hours),
                                       "description": "Execução do serviço"}, at=at)
        ticket.finished_at = finished
        recalc_costs(ticket)
        _update_asset_status(ticket, starting=False)
        if ticket.preventive_plan is not None:
            plan = ticket.preventive_plan
            plan.last_done = finished.date()
            plan.next_due = plan.last_done + timedelta(days=plan.frequency_days)
        db.session.flush()
        post_costs(ticket)
        _set_status(ticket, "finalizado", user, "Serviço finalizado",
                    note or f"Custo total R$ {br_num(ticket.total_cost)}", at)

    elif action == "close":
        ticket.closing_notes = data.get("closing_notes") or note
        if data.get("satisfaction"):
            ticket.satisfaction = max(1, min(5, int(data["satisfaction"])))
        ticket.closed_at = at
        _set_status(ticket, "encerrado", user, "Chamado encerrado", ticket.closing_notes, at)

    elif action == "reopen":
        if not note:
            raise WorkflowError("Informe o motivo da reabertura")
        ticket.finished_at = None
        _set_status(ticket, "em_execucao", user, "Chamado reaberto", note, at)

    elif action == "cancel":
        if not note:
            raise WorkflowError("Informe o motivo do cancelamento")
        _set_status(ticket, "cancelado", user, "Chamado cancelado", note, at)

    elif action == "update":
        changes = []
        for field in ("priority", "criticality", "maintenance_type", "team_id", "asset_id", "sector_id",
                      "location", "title"):
            if field in data and data[field] not in (None, "") and str(getattr(ticket, field)) != str(data[field]):
                value = data[field]
                if field.endswith("_id"):
                    value = int(value)
                setattr(ticket, field, value)
                changes.append(field)
        if "priority" in changes or "maintenance_type" in changes:
            ticket.sla_hours = sla_hours_for(ticket.priority, ticket.maintenance_type)
            ticket.sla_due_at = ticket.created_at + timedelta(hours=ticket.sla_hours)
        if changes:
            log_event(ticket, user, "Dados atualizados", note=", ".join(changes), at=at)
    return ticket
