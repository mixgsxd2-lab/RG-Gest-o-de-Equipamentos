from flask import Blueprint, jsonify

from ..services.tickets import WorkflowError
from .common import ApiError

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.errorhandler(ApiError)
@bp.errorhandler(WorkflowError)
def handle_api_error(exc):
    return jsonify({"error": exc.message}), exc.status


# As rotas são registradas por módulo (importados após a criação do blueprint)
from . import (assets, costs, dashboard, intelligence, iot, preventive, stock, teams,  # noqa: E402,F401
               tickets, users)
