"""Modelo de dados do Sistema de Gestão de Manutenção do Hospital Rio Grande."""
from datetime import date, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from .constants import ROLES, SENSOR_KINDS, TICKET_STATUSES
from .extensions import db


def iso(value):
    return value.isoformat() if value else None


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


# ---------------------------------------------------------------------------
# Estrutura organizacional
# ---------------------------------------------------------------------------
class Sector(db.Model):
    """Setor do hospital (onde estão os ativos e de onde partem os chamados)."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    building = db.Column(db.String(60))
    floor = db.Column(db.String(30))
    cost_center = db.Column(db.String(30))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "building": self.building,
            "floor": self.floor,
            "cost_center": self.cost_center,
        }


class Team(db.Model):
    """Setor/equipe executante de manutenção (destino dos chamados)."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.String(255))
    color = db.Column(db.String(10), default="#0f6cbd")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description, "color": self.color}


class User(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160))
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), nullable=False, default="solicitante")
    sector_id = db.Column(db.Integer, db.ForeignKey("sector.id"))
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"))
    active = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime)
    # Preparação para AD / Microsoft 365 / Google Workspace
    auth_provider = db.Column(db.String(30), default="local", nullable=False)
    external_id = db.Column(db.String(255), index=True)

    sector = db.relationship("Sector")
    team = db.relationship("Team")
    technician = db.relationship("Technician", back_populates="user", uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return bool(self.password_hash) and check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "role_label": ROLES.get(self.role, self.role),
            "sector_id": self.sector_id,
            "sector": self.sector.name if self.sector else None,
            "team_id": self.team_id,
            "team": self.team.name if self.team else None,
            "technician_id": self.technician.id if self.technician else None,
            "active": self.active,
            "auth_provider": self.auth_provider,
            "last_login_at": iso(self.last_login_at),
        }


# ---------------------------------------------------------------------------
# Fornecedores, contratos e equipe técnica
# ---------------------------------------------------------------------------
class Supplier(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    cnpj = db.Column(db.String(20))
    category = db.Column(db.String(80))
    contact_name = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(160))
    rating = db.Column(db.Float, default=4.0)  # avaliação 0-5
    active = db.Column(db.Boolean, default=True)

    contracts = db.relationship("Contract", back_populates="supplier")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "cnpj": self.cnpj,
            "category": self.category,
            "contact_name": self.contact_name,
            "phone": self.phone,
            "email": self.email,
            "rating": self.rating,
            "active": self.active,
        }


class Contract(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(40), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"))
    scope = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    monthly_value = db.Column(db.Float, default=0)
    sla_response_hours = db.Column(db.Integer, default=4)
    sla_resolution_hours = db.Column(db.Integer, default=24)
    notes = db.Column(db.Text)

    supplier = db.relationship("Supplier", back_populates="contracts")
    team = db.relationship("Team")

    @property
    def status(self):
        today = date.today()
        if self.end_date < today:
            return "Vencido"
        if (self.end_date - today).days <= 60:
            return "A vencer"
        if self.start_date > today:
            return "Futuro"
        return "Vigente"

    def to_dict(self):
        return {
            "id": self.id,
            "number": self.number,
            "supplier_id": self.supplier_id,
            "supplier": self.supplier.name if self.supplier else None,
            "team_id": self.team_id,
            "team": self.team.name if self.team else None,
            "scope": self.scope,
            "start_date": iso(self.start_date),
            "end_date": iso(self.end_date),
            "monthly_value": self.monthly_value,
            "annual_value": round((self.monthly_value or 0) * 12, 2),
            "sla_response_hours": self.sla_response_hours,
            "sla_resolution_hours": self.sla_resolution_hours,
            "status": self.status,
            "days_to_end": (self.end_date - date.today()).days,
            "notes": self.notes,
        }


class Technician(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    specialty = db.Column(db.String(120))
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))  # técnico terceirizado
    registration = db.Column(db.String(30))
    shift = db.Column(db.String(30))
    phone = db.Column(db.String(30))
    hourly_rate = db.Column(db.Float, default=45.0)
    active = db.Column(db.Boolean, default=True)

    team = db.relationship("Team")
    user = db.relationship("User", back_populates="technician")
    supplier = db.relationship("Supplier")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "specialty": self.specialty,
            "team_id": self.team_id,
            "team": self.team.name if self.team else None,
            "user_id": self.user_id,
            "username": self.user.username if self.user else None,
            "supplier_id": self.supplier_id,
            "supplier": self.supplier.name if self.supplier else None,
            "external": self.supplier_id is not None,
            "registration": self.registration,
            "shift": self.shift,
            "phone": self.phone,
            "hourly_rate": self.hourly_rate,
            "active": self.active,
        }


# ---------------------------------------------------------------------------
# Inventário / ativos
# ---------------------------------------------------------------------------
class Asset(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(40), unique=True, nullable=False, index=True)  # patrimônio
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    kind = db.Column(db.String(40), default="Equipamento")
    sector_id = db.Column(db.Integer, db.ForeignKey("sector.id"))
    location = db.Column(db.String(160))
    manufacturer = db.Column(db.String(120))
    model = db.Column(db.String(120))
    serial_number = db.Column(db.String(80))
    acquisition_date = db.Column(db.Date)
    acquisition_cost = db.Column(db.Float, default=0)
    useful_life_years = db.Column(db.Float, default=10)
    residual_value = db.Column(db.Float, default=0)
    warranty_until = db.Column(db.Date)
    status = db.Column(db.String(30), default="Operacional")
    criticality = db.Column(db.String(20), default="Média")
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    notes = db.Column(db.Text)

    sector = db.relationship("Sector")
    supplier = db.relationship("Supplier")
    tickets = db.relationship("Ticket", back_populates="asset", lazy="dynamic")

    def depreciation(self, on=None):
        """Depreciação linear: (custo - residual) / vida útil."""
        on = on or date.today()
        cost = self.acquisition_cost or 0
        residual = self.residual_value or 0
        life = self.useful_life_years or 0
        if not self.acquisition_date or life <= 0 or cost <= 0:
            return {"annual": 0, "accumulated": 0, "book_value": cost, "percent": 0, "age_years": 0,
                    "remaining_years": life}
        age_years = max(0.0, (on - self.acquisition_date).days / 365.25)
        annual = (cost - residual) / life
        accumulated = min(cost - residual, annual * age_years)
        return {
            "annual": round(annual, 2),
            "accumulated": round(accumulated, 2),
            "book_value": round(cost - accumulated, 2),
            "percent": round(100 * accumulated / cost, 1) if cost else 0,
            "age_years": round(age_years, 1),
            "remaining_years": round(max(0.0, life - age_years), 1),
        }

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "tag": self.tag,
            "name": self.name,
            "category": self.category,
            "kind": self.kind,
            "sector_id": self.sector_id,
            "sector": self.sector.name if self.sector else None,
            "location": self.location,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_number": self.serial_number,
            "acquisition_date": iso(self.acquisition_date),
            "acquisition_cost": self.acquisition_cost,
            "useful_life_years": self.useful_life_years,
            "residual_value": self.residual_value,
            "warranty_until": iso(self.warranty_until),
            "status": self.status,
            "criticality": self.criticality,
            "supplier_id": self.supplier_id,
            "supplier": self.supplier.name if self.supplier else None,
            "notes": self.notes,
            "depreciation": self.depreciation(),
        }
        return data


# ---------------------------------------------------------------------------
# Estoque
# ---------------------------------------------------------------------------
class Product(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(80))
    unit = db.Column(db.String(10), default="un")
    quantity = db.Column(db.Float, default=0, nullable=False)
    min_stock = db.Column(db.Float, default=0)
    unit_cost = db.Column(db.Float, default=0)  # custo médio
    storage_location = db.Column(db.String(80))
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    active = db.Column(db.Boolean, default=True)

    supplier = db.relationship("Supplier")

    @property
    def below_minimum(self):
        return (self.quantity or 0) <= (self.min_stock or 0)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "category": self.category,
            "unit": self.unit,
            "quantity": self.quantity,
            "min_stock": self.min_stock,
            "unit_cost": round(self.unit_cost or 0, 2),
            "total_value": round((self.quantity or 0) * (self.unit_cost or 0), 2),
            "storage_location": self.storage_location,
            "supplier_id": self.supplier_id,
            "supplier": self.supplier.name if self.supplier else None,
            "below_minimum": self.below_minimum,
            "active": self.active,
        }


class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    kind = db.Column(db.String(10), nullable=False)  # entrada | saida | ajuste
    quantity = db.Column(db.Float, nullable=False)
    unit_cost = db.Column(db.Float, default=0)
    ticket_id = db.Column(db.Integer, db.ForeignKey("ticket.id"))
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    document = db.Column(db.String(60))  # NF, requisição etc.
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    product = db.relationship("Product")
    ticket = db.relationship("Ticket")
    supplier = db.relationship("Supplier")
    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product": self.product.name if self.product else None,
            "product_code": self.product.code if self.product else None,
            "unit": self.product.unit if self.product else None,
            "kind": self.kind,
            "quantity": self.quantity,
            "unit_cost": self.unit_cost,
            "total": round((self.quantity or 0) * (self.unit_cost or 0), 2),
            "ticket_id": self.ticket_id,
            "ticket_code": self.ticket.code if self.ticket else None,
            "supplier": self.supplier.name if self.supplier else None,
            "user": self.user.name if self.user else None,
            "document": self.document,
            "note": self.note,
            "created_at": iso(self.created_at),
        }


# ---------------------------------------------------------------------------
# Chamados (ordens de serviço)
# ---------------------------------------------------------------------------
class Ticket(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    maintenance_type = db.Column(db.String(20), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="Média")
    criticality = db.Column(db.String(20), nullable=False, default="Média")
    status = db.Column(db.String(20), nullable=False, default="aberto", index=True)
    waiting_reason = db.Column(db.String(20))  # Material | Terceiro

    team_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=False)  # setor destino
    sector_id = db.Column(db.Integer, db.ForeignKey("sector.id"))  # local do problema
    location = db.Column(db.String(160))
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"))
    preventive_plan_id = db.Column(db.Integer, db.ForeignKey("preventive_plan.id"))
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))  # terceiro acionado

    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)  # quem abriu
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # quem recebeu (responsável)
    operator_id = db.Column(db.Integer, db.ForeignKey("technician.id"))  # quem aceitou/executou

    sla_hours = db.Column(db.Float)
    sla_due_at = db.Column(db.DateTime)
    received_at = db.Column(db.DateTime)
    accepted_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)

    diagnosis = db.Column(db.Text)
    solution = db.Column(db.Text)  # o que foi feito
    observations = db.Column(db.Text)
    closing_notes = db.Column(db.Text)
    failure_cause = db.Column(db.String(80))
    satisfaction = db.Column(db.Integer)  # 1-5

    labor_hours = db.Column(db.Float, default=0)
    labor_cost = db.Column(db.Float, default=0)
    material_cost = db.Column(db.Float, default=0)
    third_party_cost = db.Column(db.Float, default=0)

    team = db.relationship("Team")
    sector = db.relationship("Sector")
    asset = db.relationship("Asset", back_populates="tickets")
    supplier = db.relationship("Supplier")
    preventive_plan = db.relationship("PreventivePlan")
    requester = db.relationship("User", foreign_keys=[requester_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])
    operator = db.relationship("Technician")
    events = db.relationship("TicketEvent", back_populates="ticket", order_by="TicketEvent.created_at",
                             cascade="all, delete-orphan")
    worklogs = db.relationship("WorkLog", back_populates="ticket", order_by="WorkLog.started_at",
                               cascade="all, delete-orphan")
    materials = db.relationship("TicketMaterial", back_populates="ticket", cascade="all, delete-orphan")
    attachments = db.relationship("Attachment", back_populates="ticket", cascade="all, delete-orphan")

    @property
    def total_cost(self):
        return round((self.labor_cost or 0) + (self.material_cost or 0) + (self.third_party_cost or 0), 2)

    @property
    def sla_status(self):
        """no_prazo | em_risco | violado | cumprido."""
        if not self.sla_due_at or self.status == "cancelado":
            return None
        end = self.finished_at
        if end:
            return "cumprido" if end <= self.sla_due_at else "violado"
        now = datetime.now()
        if now > self.sla_due_at:
            return "violado"
        remaining = (self.sla_due_at - now).total_seconds() / 3600
        if self.sla_hours and remaining <= self.sla_hours * 0.25:
            return "em_risco"
        return "no_prazo"

    @property
    def resolution_hours(self):
        if self.finished_at:
            return round((self.finished_at - self.created_at).total_seconds() / 3600, 2)
        return None

    @property
    def response_hours(self):
        if self.accepted_at:
            return round((self.accepted_at - self.created_at).total_seconds() / 3600, 2)
        return None

    def to_dict(self, detail=False):
        data = {
            "id": self.id,
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "maintenance_type": self.maintenance_type,
            "priority": self.priority,
            "criticality": self.criticality,
            "status": self.status,
            "status_label": TICKET_STATUSES.get(self.status, self.status),
            "waiting_reason": self.waiting_reason,
            "team_id": self.team_id,
            "team": self.team.name if self.team else None,
            "sector_id": self.sector_id,
            "sector": self.sector.name if self.sector else None,
            "location": self.location,
            "asset_id": self.asset_id,
            "asset": f"{self.asset.tag} - {self.asset.name}" if self.asset else None,
            "supplier_id": self.supplier_id,
            "supplier": self.supplier.name if self.supplier else None,
            "preventive_plan_id": self.preventive_plan_id,
            "requester_id": self.requester_id,
            "requester": self.requester.name if self.requester else None,
            "receiver_id": self.receiver_id,
            "receiver": self.receiver.name if self.receiver else None,
            "operator_id": self.operator_id,
            "operator": self.operator.name if self.operator else None,
            "operator_user_id": self.operator.user_id if self.operator else None,
            "sla_hours": self.sla_hours,
            "sla_due_at": iso(self.sla_due_at),
            "sla_status": self.sla_status,
            "created_at": iso(self.created_at),
            "received_at": iso(self.received_at),
            "accepted_at": iso(self.accepted_at),
            "started_at": iso(self.started_at),
            "finished_at": iso(self.finished_at),
            "closed_at": iso(self.closed_at),
            "resolution_hours": self.resolution_hours,
            "response_hours": self.response_hours,
            "labor_hours": self.labor_hours,
            "labor_cost": self.labor_cost,
            "material_cost": self.material_cost,
            "third_party_cost": self.third_party_cost,
            "total_cost": self.total_cost,
            "satisfaction": self.satisfaction,
        }
        if detail:
            data.update(
                {
                    "diagnosis": self.diagnosis,
                    "solution": self.solution,
                    "observations": self.observations,
                    "closing_notes": self.closing_notes,
                    "failure_cause": self.failure_cause,
                    "events": [e.to_dict() for e in self.events],
                    "worklogs": [w.to_dict() for w in self.worklogs],
                    "materials": [m.to_dict() for m in self.materials],
                    "attachments": [a.to_dict() for a in self.attachments],
                }
            )
        return data


class TicketEvent(db.Model):
    """Histórico completo (trilha de auditoria) de todas as ações do chamado."""

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("ticket.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(60), nullable=False)
    from_status = db.Column(db.String(20))
    to_status = db.Column(db.String(20))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    ticket = db.relationship("Ticket", back_populates="events")
    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "action": self.action,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "from_label": TICKET_STATUSES.get(self.from_status) if self.from_status else None,
            "to_label": TICKET_STATUSES.get(self.to_status) if self.to_status else None,
            "note": self.note,
            "user": self.user.name if self.user else "Sistema",
            "created_at": iso(self.created_at),
        }


class WorkLog(db.Model):
    """Apontamento de execução: início, término, horas e atividade."""

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("ticket.id"), nullable=False, index=True)
    technician_id = db.Column(db.Integer, db.ForeignKey("technician.id"))
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, default=0)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    ticket = db.relationship("Ticket", back_populates="worklogs")
    technician = db.relationship("Technician")

    def to_dict(self):
        return {
            "id": self.id,
            "technician_id": self.technician_id,
            "technician": self.technician.name if self.technician else None,
            "started_at": iso(self.started_at),
            "ended_at": iso(self.ended_at),
            "hours": self.hours,
            "cost": self.cost,
            "description": self.description,
        }


class TicketMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("ticket.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    description = db.Column(db.String(160))  # material avulso (sem cadastro)
    quantity = db.Column(db.Float, nullable=False)
    unit_cost = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)

    ticket = db.relationship("Ticket", back_populates="materials")
    product = db.relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "name": self.product.name if self.product else self.description,
            "code": self.product.code if self.product else None,
            "unit": self.product.unit if self.product else "un",
            "quantity": self.quantity,
            "unit_cost": self.unit_cost,
            "total": round(self.quantity * (self.unit_cost or 0), 2),
        }


class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("ticket.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    mimetype = db.Column(db.String(100))
    size = db.Column(db.Integer)
    stage = db.Column(db.String(20), default="abertura")  # abertura | execucao | fechamento
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.now)

    ticket = db.relationship("Ticket", back_populates="attachments")
    uploaded_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "mimetype": self.mimetype,
            "size": self.size,
            "stage": self.stage,
            "is_image": (self.mimetype or "").startswith("image/"),
            "url": f"/api/attachments/{self.id}",
            "uploaded_by": self.uploaded_by.name if self.uploaded_by else None,
            "created_at": iso(self.created_at),
        }


# ---------------------------------------------------------------------------
# Manutenção preventiva
# ---------------------------------------------------------------------------
class PreventivePlan(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"))
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey("technician.id"))
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    maintenance_type = db.Column(db.String(20), default="Preventiva")
    frequency_days = db.Column(db.Integer, nullable=False, default=30)
    last_done = db.Column(db.Date)
    next_due = db.Column(db.Date, nullable=False)
    estimated_hours = db.Column(db.Float, default=1)
    checklist = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)

    asset = db.relationship("Asset")
    team = db.relationship("Team")
    technician = db.relationship("Technician")
    supplier = db.relationship("Supplier")

    @property
    def ticket_title(self):
        """Título da OS gerada (evita repetir o tipo quando já consta no nome do plano)."""
        if self.maintenance_type.lower() in self.name.lower():
            return self.name
        return f"{self.maintenance_type}: {self.name}"

    @property
    def situation(self):
        days = (self.next_due - date.today()).days
        if days < 0:
            return "Atrasada"
        if days <= 7:
            return "Próxima"
        return "Programada"

    def to_dict(self):
        open_ticket = (
            Ticket.query.filter(Ticket.preventive_plan_id == self.id,
                                Ticket.status.notin_(["finalizado", "encerrado", "cancelado"]))
            .order_by(Ticket.id.desc())
            .first()
        )
        return {
            "id": self.id,
            "name": self.name,
            "asset_id": self.asset_id,
            "asset": f"{self.asset.tag} - {self.asset.name}" if self.asset else None,
            "sector": self.asset.sector.name if self.asset and self.asset.sector else None,
            "team_id": self.team_id,
            "team": self.team.name if self.team else None,
            "technician_id": self.technician_id,
            "technician": self.technician.name if self.technician else None,
            "supplier_id": self.supplier_id,
            "supplier": self.supplier.name if self.supplier else None,
            "maintenance_type": self.maintenance_type,
            "frequency_days": self.frequency_days,
            "last_done": iso(self.last_done),
            "next_due": iso(self.next_due),
            "days_to_due": (self.next_due - date.today()).days,
            "estimated_hours": self.estimated_hours,
            "checklist": self.checklist,
            "active": self.active,
            "situation": self.situation,
            "open_ticket_id": open_ticket.id if open_ticket else None,
            "open_ticket_code": open_ticket.code if open_ticket else None,
        }


# ---------------------------------------------------------------------------
# Custos (livro-razão único de custos da manutenção)
# ---------------------------------------------------------------------------
class CostEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(30), nullable=False)  # ver COST_CATEGORIES
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    sector_id = db.Column(db.Integer, db.ForeignKey("sector.id"))
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"))
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"))
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"))
    ticket_id = db.Column(db.Integer, db.ForeignKey("ticket.id"))
    contract_id = db.Column(db.Integer, db.ForeignKey("contract.id"))
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.now)

    sector = db.relationship("Sector")
    team = db.relationship("Team")
    asset = db.relationship("Asset")
    supplier = db.relationship("Supplier")
    ticket = db.relationship("Ticket")
    contract = db.relationship("Contract")

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "amount": round(self.amount, 2),
            "date": iso(self.date),
            "sector_id": self.sector_id,
            "sector": self.sector.name if self.sector else None,
            "team": self.team.name if self.team else None,
            "asset_id": self.asset_id,
            "asset": self.asset.tag if self.asset else None,
            "supplier": self.supplier.name if self.supplier else None,
            "ticket_id": self.ticket_id,
            "ticket_code": self.ticket.code if self.ticket else None,
            "contract": self.contract.number if self.contract else None,
        }


# ---------------------------------------------------------------------------
# Monitoramento / IoT (energia, água, gases, condição de equipamentos)
# ---------------------------------------------------------------------------
class Sensor(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    kind = db.Column(db.String(20), nullable=False)  # ver SENSOR_KINDS
    unit = db.Column(db.String(20))
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"))
    sector_id = db.Column(db.Integer, db.ForeignKey("sector.id"))
    min_value = db.Column(db.Float)
    max_value = db.Column(db.Float)
    protocol = db.Column(db.String(30), default="MQTT")  # MQTT, Modbus, HTTP, BACnet...
    active = db.Column(db.Boolean, default=True)
    last_value = db.Column(db.Float)
    last_reading_at = db.Column(db.DateTime)

    asset = db.relationship("Asset")
    sector = db.relationship("Sector")

    @property
    def state(self):
        if self.last_value is None:
            return "sem_dados"
        if self.min_value is not None and self.last_value < self.min_value:
            return "alerta"
        if self.max_value is not None and self.last_value > self.max_value:
            return "alerta"
        return "normal"

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "kind": self.kind,
            "kind_label": SENSOR_KINDS.get(self.kind, self.kind),
            "unit": self.unit,
            "asset_id": self.asset_id,
            "asset": f"{self.asset.tag} - {self.asset.name}" if self.asset else None,
            "sector": self.sector.name if self.sector else None,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "protocol": self.protocol,
            "active": self.active,
            "last_value": self.last_value,
            "last_reading_at": iso(self.last_reading_at),
            "state": self.state,
        }


class SensorReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey("sensor.id"), nullable=False, index=True)
    value = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)

    def to_dict(self):
        return {"value": self.value, "recorded_at": iso(self.recorded_at)}
