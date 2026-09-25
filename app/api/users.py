from flask import current_app, jsonify, request

from ..auth import PERMISSIONS, current_user, require
from ..auth_providers import list_providers
from ..constants import ROLES
from ..extensions import db
from ..models import User
from . import bp
from .common import ApiError, apply_fields, get_or_404

USER_FIELDS = {"name": "str", "email": "str", "role": "str", "sector_id": "int", "team_id": "int",
               "active": "bool"}


@bp.get("/users")
@require("users.manage")
def list_users():
    return jsonify([u.to_dict() for u in User.query.order_by(User.name)])


@bp.post("/users")
@require("users.manage")
def create_user():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    if not username or User.query.filter_by(username=username).first():
        raise ApiError("Informe um nome de usuário único")
    if data.get("role") not in ROLES:
        raise ApiError("Perfil inválido")
    if len(data.get("password") or "") < 6:
        raise ApiError("A senha deve ter ao menos 6 caracteres")
    user = apply_fields(User(username=username), data, USER_FIELDS, required=("name", "role"))
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@bp.put("/users/<int:user_id>")
@require("users.manage")
def update_user(user_id):
    user = get_or_404(User, user_id, "Usuário")
    data = request.get_json(silent=True) or {}
    if "role" in data and data["role"] not in ROLES:
        raise ApiError("Perfil inválido")
    if user.id == current_user().id and (data.get("active") is False or data.get("role", "admin") != "admin"):
        raise ApiError("Você não pode desativar ou rebaixar o próprio usuário")
    apply_fields(user, data, USER_FIELDS)
    if data.get("password"):
        if len(data["password"]) < 6:
            raise ApiError("A senha deve ter ao menos 6 caracteres")
        user.set_password(data["password"])
    db.session.commit()
    return jsonify(user.to_dict())


@bp.get("/access/matrix")
@require("users.manage")
def access_matrix():
    return jsonify({"roles": ROLES, "permissions": {k: sorted(v) for k, v in PERMISSIONS.items()}})


@bp.get("/integrations")
@require("users.manage")
def integrations():
    """Situação das integrações de identidade e de dados (preparação futura)."""
    cfg = current_app.config
    return jsonify({
        "identity": list_providers(),
        "iot": {"endpoint": "/api/iot/readings", "auth": "Cabeçalho X-API-Key",
                "protocols": ["HTTP/REST", "MQTT (futuro)", "Modbus TCP (futuro)", "BACnet (futuro)"]},
        "bi": {"endpoint": "/api/intelligence/export/<conjunto>.csv|json",
               "tools": ["Power BI", "Excel", "Metabase", "Apache Superset"]},
        "database": cfg["SQLALCHEMY_DATABASE_URI"].split(":", 1)[0],
    })
