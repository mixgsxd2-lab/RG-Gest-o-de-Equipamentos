"""Configurações da aplicação.

Todas as opções podem ser sobrescritas por variáveis de ambiente, o que permite
trocar o SQLite de demonstração por PostgreSQL/SQL Server em produção sem mudar
o código (ex.: DATABASE_URL=postgresql+psycopg://user:senha@host/rg_manutencao).
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "rg-demo-chave-trocar-em-producao")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(INSTANCE_DIR, "rg_manutencao.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(INSTANCE_DIR, "uploads"))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB por requisição
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf", "doc", "docx", "xls", "xlsx", "txt"}

    # Identifica claramente o ambiente como DEMONSTRAÇÃO na interface
    DEMO_MODE = os.environ.get("DEMO_MODE", "1") == "1"

    # Chave usada por gateways IoT (energia, água, gases) para enviar leituras
    IOT_API_KEY = os.environ.get("IOT_API_KEY", "rg-iot-demo-key")

    # Preparação para SSO corporativo (ver app/auth_providers.py)
    AUTH_PROVIDERS = {
        "local": {"enabled": True},
        "active_directory": {
            "enabled": os.environ.get("AD_ENABLED", "0") == "1",
            "server": os.environ.get("AD_SERVER", "ldap://ad.hospitalriogrande.local"),
            "base_dn": os.environ.get("AD_BASE_DN", "DC=hospitalriogrande,DC=local"),
        },
        "microsoft365": {
            "enabled": os.environ.get("M365_ENABLED", "0") == "1",
            "tenant_id": os.environ.get("M365_TENANT_ID", ""),
            "client_id": os.environ.get("M365_CLIENT_ID", ""),
        },
        "google_workspace": {
            "enabled": os.environ.get("GOOGLE_ENABLED", "0") == "1",
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "hosted_domain": os.environ.get("GOOGLE_HOSTED_DOMAIN", ""),
        },
    }

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
