"""Utilitários compartilhados pelas rotas da API."""
from datetime import date, datetime

from flask import jsonify

from ..extensions import db


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def error(message, status=400):
    return jsonify({"error": message}), status


def get_or_404(model, obj_id, label="Registro"):
    obj = db.session.get(model, obj_id)
    if obj is None:
        raise ApiError(f"{label} não encontrado", 404)
    return obj


def _coerce(value, kind):
    if value in (None, ""):
        return None
    if kind == "str":
        return str(value).strip()
    if kind == "int":
        return int(value)
    if kind == "float":
        return float(value)
    if kind == "bool":
        return value if isinstance(value, bool) else str(value).lower() in ("1", "true", "sim", "on")
    if kind == "date":
        return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
    if kind == "datetime":
        return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    raise ValueError(kind)


def apply_fields(obj, data, spec, required=()):
    """Copia ``data`` para ``obj`` convertendo os tipos conforme ``spec``."""
    for name in required:
        if data.get(name) in (None, "") and getattr(obj, name, None) in (None, ""):
            raise ApiError(f"Campo obrigatório: {name}")
    for name, kind in spec.items():
        if name in data:
            try:
                setattr(obj, name, _coerce(data[name], kind))
            except (TypeError, ValueError):
                raise ApiError(f"Valor inválido para {name}")
    return obj


def paginate(query, args, serializer=lambda o: o.to_dict()):
    page = max(1, int(args.get("page", 1) or 1))
    per_page = min(500, max(1, int(args.get("per_page", 50) or 50)))
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"items": [serializer(o) for o in items], "total": total, "page": page, "per_page": per_page,
            "pages": (total + per_page - 1) // per_page}
