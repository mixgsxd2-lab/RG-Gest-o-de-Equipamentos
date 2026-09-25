"""Autenticação por sessão e controle de acesso por perfil (RBAC)."""
from datetime import datetime
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request, session

from .auth_providers import get_provider, list_providers
from .constants import ROLES
from .extensions import db
from .models import User

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

ALL = set(ROLES)

# Matriz de permissões: capacidade -> perfis autorizados
PERMISSIONS = {
    "dashboard.view": {"admin", "gestor", "operador", "estoque", "diretoria"},
    "tickets.create": ALL,
    "tickets.view_all": {"admin", "gestor", "operador", "estoque", "diretoria"},
    "tickets.manage": {"admin", "gestor"},
    "tickets.execute": {"admin", "gestor", "operador"},
    "assets.view": ALL,
    "assets.edit": {"admin", "gestor"},
    "preventive.view": {"admin", "gestor", "operador", "diretoria"},
    "preventive.edit": {"admin", "gestor"},
    "teams.view": {"admin", "gestor", "operador", "diretoria", "estoque"},
    "teams.edit": {"admin", "gestor"},
    "stock.view": {"admin", "gestor", "operador", "estoque", "diretoria"},
    "stock.edit": {"admin", "gestor", "estoque"},
    "costs.view": {"admin", "gestor", "estoque", "diretoria"},
    "costs.edit": {"admin", "gestor"},
    "iot.view": {"admin", "gestor", "operador", "diretoria"},
    "iot.edit": {"admin", "gestor"},
    "indicators.view": {"admin", "gestor", "diretoria"},
    "users.manage": {"admin"},
}


def can(user, permission):
    return user is not None and user.role in PERMISSIONS.get(permission, set())


def current_user():
    uid = session.get("user_id")
    cached = g.get("_rg_user")
    if cached is None or cached[0] != uid:
        user = db.session.get(User, uid) if uid else None
        if user is not None and not user.active:
            user = None
        g._rg_user = cached = (uid, user)
    return cached[1]


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return jsonify({"error": "Não autenticado"}), 401
        return fn(*args, **kwargs)

    return wrapper


def require(permission):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if user is None:
                return jsonify({"error": "Não autenticado"}), 401
            if not can(user, permission):
                return jsonify({"error": "Acesso negado para o seu perfil"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def user_payload(user):
    data = user.to_dict()
    data["permissions"] = sorted(p for p in PERMISSIONS if can(user, p))
    return data


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    provider = get_provider(data.get("provider", "local"))
    if provider is None or not provider.enabled:
        return jsonify({"error": "Provedor de autenticação indisponível"}), 400
    user = provider.authenticate(data)
    if user is None:
        return jsonify({"error": "Usuário ou senha inválidos"}), 401
    session.clear()
    session["user_id"] = user.id
    session.permanent = True
    user.last_login_at = datetime.now()
    db.session.commit()
    return jsonify({"user": user_payload(user)})


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@bp.get("/me")
@login_required
def me():
    return jsonify({"user": user_payload(current_user()), "demo": current_app.config["DEMO_MODE"]})


@bp.get("/providers")
def providers():
    return jsonify(list_providers())


@bp.post("/change-password")
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    user = current_user()
    if user.auth_provider != "local":
        return jsonify({"error": "Senha gerenciada pelo provedor corporativo"}), 400
    if not user.check_password(data.get("current", "")):
        return jsonify({"error": "Senha atual incorreta"}), 400
    new = data.get("new", "")
    if len(new) < 6:
        return jsonify({"error": "A nova senha deve ter ao menos 6 caracteres"}), 400
    user.set_password(new)
    db.session.commit()
    return jsonify({"ok": True})
