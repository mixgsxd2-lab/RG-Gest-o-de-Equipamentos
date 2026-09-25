"""Inicia o servidor de desenvolvimento.

    python run.py            -> http://localhost:5000

Na primeira execução o banco SQLite é criado em ``instance/`` e populado com
dados fictícios de DEMONSTRAÇÃO (desative com DEMO_MODE=0).
"""
import os

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

with app.app_context():
    if app.config["DEMO_MODE"] and User.query.count() == 0:
        from app.seed import seed_demo

        seed_demo()
        print("Dados de DEMONSTRAÇÃO criados. Acesse com admin / 123456")
    db.session.remove()

if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG", "0") == "1")
