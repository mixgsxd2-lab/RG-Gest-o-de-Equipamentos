"""Sistema de Gestão de Manutenção — Hospital Rio Grande (RG)."""
import os

import click
from flask import Flask, jsonify, render_template, request

from .config import INSTANCE_DIR, Config
from .extensions import db


def create_app(config_class=Config):
    app = Flask(__name__, instance_path=INSTANCE_DIR)
    app.config.from_object(config_class)
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    from . import models  # noqa: F401  (registra os modelos)
    from .api import bp as api_bp
    from .auth import bp as auth_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    @app.get("/")
    def index():
        return render_template("index.html", demo=app.config["DEMO_MODE"])

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(_):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Recurso não encontrado"}), 404
        return render_template("index.html", demo=app.config["DEMO_MODE"]), 200

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({"error": "Arquivo muito grande (máx. 16 MB)"}), 413

    @app.cli.command("init-db")
    @click.option("--demo/--no-demo", default=True, help="Carrega dados fictícios de demonstração")
    @click.option("--reset", is_flag=True, help="Apaga e recria todas as tabelas")
    def init_db(demo, reset):
        """Cria o banco de dados (e opcionalmente os dados de demonstração)."""
        if reset:
            db.drop_all()
        db.create_all()
        if demo:
            from .seed import seed_demo
            seed_demo()
            click.echo("Banco criado com dados de DEMONSTRAÇÃO.")
        else:
            click.echo("Banco criado.")

    with app.app_context():
        db.create_all()

    return app
