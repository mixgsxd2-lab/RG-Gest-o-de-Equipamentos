import os
import uuid

from flask import current_app, jsonify, request, send_from_directory
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from ..auth import can, current_user, login_required, require
from ..extensions import db
from ..models import Attachment, Technician, Ticket
from ..services import tickets as svc
from . import bp
from .common import ApiError, get_or_404, paginate


def _visible_ticket(ticket_id):
    ticket = get_or_404(Ticket, ticket_id, "Chamado")
    user = current_user()
    if not can(user, "tickets.view_all") and ticket.requester_id != user.id:
        raise ApiError("Acesso negado a este chamado", 403)
    return ticket


def _detail(ticket):
    data = ticket.to_dict(detail=True)
    data["actions"] = svc.available_actions(ticket, current_user())
    return data


def save_attachment(ticket, file, stage, user):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        raise ApiError(f"Tipo de arquivo não permitido: .{ext}")
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    stored = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(folder, stored)
    file.save(path)
    att = Attachment(ticket=ticket, filename=secure_filename(file.filename) or stored, stored_name=stored,
                     mimetype=file.mimetype, size=os.path.getsize(path), stage=stage, uploaded_by=user)
    db.session.add(att)
    return att


@bp.get("/tickets")
@login_required
def list_tickets():
    user = current_user()
    a = request.args
    q = Ticket.query
    if not can(user, "tickets.view_all"):
        q = q.filter(Ticket.requester_id == user.id)
    if a.get("status"):
        q = q.filter(Ticket.status.in_(a["status"].split(",")))
    for field in ("team_id", "sector_id", "asset_id", "operator_id"):
        if a.get(field):
            q = q.filter(getattr(Ticket, field) == int(a[field]))
    if a.get("maintenance_type"):
        q = q.filter(Ticket.maintenance_type == a["maintenance_type"])
    if a.get("priority"):
        q = q.filter(Ticket.priority == a["priority"])
    if a.get("mine") == "requested":
        q = q.filter(Ticket.requester_id == user.id)
    elif a.get("mine") == "assigned":
        tech = Technician.query.filter_by(user_id=user.id).first()
        q = q.filter(Ticket.operator_id == (tech.id if tech else -1))
    if a.get("q"):
        term = f"%{a['q'].strip()}%"
        q = q.filter(or_(Ticket.code.ilike(term), Ticket.title.ilike(term), Ticket.description.ilike(term),
                         Ticket.location.ilike(term)))
    q = q.order_by(Ticket.created_at.desc())
    if a.get("sla") in ("violado", "em_risco"):
        items = [t for t in q.all() if t.sla_status == a["sla"]]
        return jsonify({"items": [t.to_dict() for t in items], "total": len(items), "page": 1,
                        "per_page": len(items), "pages": 1})
    return jsonify(paginate(q, a))


@bp.post("/tickets")
@require("tickets.create")
def create_ticket():
    user = current_user()
    data = request.form.to_dict() if request.files or request.form else (request.get_json(silent=True) or {})
    ticket = svc.create_ticket(data, user)
    db.session.flush()
    for f in request.files.getlist("files"):
        if f and f.filename:
            save_attachment(ticket, f, "abertura", user)
    db.session.commit()
    return jsonify(_detail(ticket)), 201


@bp.get("/tickets/<int:ticket_id>")
@login_required
def get_ticket(ticket_id):
    return jsonify(_detail(_visible_ticket(ticket_id)))


@bp.post("/tickets/<int:ticket_id>/actions/<action>")
@login_required
def ticket_action(ticket_id, action):
    ticket = _visible_ticket(ticket_id)
    svc.apply_action(ticket, action, current_user(), request.get_json(silent=True) or {})
    db.session.commit()
    return jsonify(_detail(ticket))


@bp.post("/tickets/<int:ticket_id>/worklogs")
@require("tickets.execute")
def add_worklog(ticket_id):
    ticket = _visible_ticket(ticket_id)
    svc.add_worklog(ticket, current_user(), request.get_json(silent=True) or {})
    db.session.commit()
    return jsonify(_detail(ticket)), 201


@bp.post("/tickets/<int:ticket_id>/materials")
@require("tickets.execute")
def add_material(ticket_id):
    ticket = _visible_ticket(ticket_id)
    svc.add_material(ticket, current_user(), request.get_json(silent=True) or {})
    db.session.commit()
    return jsonify(_detail(ticket)), 201


@bp.post("/tickets/<int:ticket_id>/comments")
@login_required
def add_comment(ticket_id):
    ticket = _visible_ticket(ticket_id)
    note = ((request.get_json(silent=True) or {}).get("note") or "").strip()
    if not note:
        raise ApiError("Escreva o comentário")
    svc.log_event(ticket, current_user(), "Comentário", note=note)
    db.session.commit()
    return jsonify(_detail(ticket)), 201


@bp.post("/tickets/<int:ticket_id>/attachments")
@login_required
def upload_attachments(ticket_id):
    ticket = _visible_ticket(ticket_id)
    user = current_user()
    if "attach" not in svc.available_actions(ticket, user):
        raise ApiError("Não é possível anexar arquivos neste chamado", 403)
    files = [f for f in request.files.getlist("files") if f and f.filename]
    if not files:
        raise ApiError("Selecione ao menos um arquivo")
    stage = request.form.get("stage") or ("execucao" if ticket.status in ("aceito", "em_execucao", "aguardando")
                                          else "fechamento" if ticket.status == "finalizado" else "abertura")
    for f in files:
        save_attachment(ticket, f, stage, user)
    svc.log_event(ticket, user, "Anexo adicionado", note=", ".join(f.filename for f in files))
    db.session.commit()
    return jsonify(_detail(ticket)), 201


@bp.get("/attachments/<int:att_id>")
@login_required
def download_attachment(att_id):
    att = get_or_404(Attachment, att_id, "Anexo")
    _visible_ticket(att.ticket_id)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], att.stored_name,
                               mimetype=att.mimetype, download_name=att.filename)
