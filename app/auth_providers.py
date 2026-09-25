"""Provedores de autenticação.

Hoje apenas o provedor ``local`` (usuário/senha no banco) está ativo. Os demais
estão estruturados para futura integração corporativa:

* Active Directory (LDAP)      -> implementar ``ActiveDirectoryProvider.authenticate``
                                  usando, por exemplo, a biblioteca ``ldap3``.
* Microsoft 365 / Entra ID     -> fluxo OAuth2/OIDC (biblioteca ``msal``).
* Google Workspace             -> fluxo OAuth2/OIDC (``google-auth``/``authlib``).

Ao autenticar por um provedor externo, o usuário é localizado (ou criado) pelo
par ``auth_provider`` + ``external_id`` e o perfil (role) pode ser mapeado a
partir de grupos do diretório (ver ``GROUP_ROLE_MAP``).
"""
from flask import current_app

from .extensions import db
from .models import User

# Exemplo de mapeamento de grupos do diretório para perfis do sistema
GROUP_ROLE_MAP = {
    "GG-Manutencao-Admin": "admin",
    "GG-Manutencao-Gestores": "gestor",
    "GG-Manutencao-Tecnicos": "operador",
    "GG-Almoxarifado": "estoque",
    "GG-Diretoria": "diretoria",
}


class AuthProvider:
    key = "base"
    label = "Base"

    @property
    def settings(self):
        return current_app.config["AUTH_PROVIDERS"].get(self.key, {})

    @property
    def enabled(self):
        return bool(self.settings.get("enabled"))

    def authenticate(self, data):  # pragma: no cover - interface
        raise NotImplementedError

    def sync_user(self, external_id, username, name, email, groups=()):
        """Cria/atualiza o usuário local a partir dos dados do diretório."""
        user = User.query.filter_by(auth_provider=self.key, external_id=external_id).first()
        role = next((GROUP_ROLE_MAP[g] for g in groups if g in GROUP_ROLE_MAP), "solicitante")
        if user is None:
            user = User(username=username, auth_provider=self.key, external_id=external_id, role=role)
            db.session.add(user)
        user.name, user.email = name, email
        db.session.commit()
        return user


class LocalProvider(AuthProvider):
    key = "local"
    label = "Usuário e senha"

    def authenticate(self, data):
        username = (data.get("username") or "").strip().lower()
        user = User.query.filter_by(username=username, auth_provider="local").first()
        if user and user.active and user.check_password(data.get("password") or ""):
            return user
        return None


class ActiveDirectoryProvider(AuthProvider):
    key = "active_directory"
    label = "Active Directory"

    def authenticate(self, data):
        # Ponto de integração: bind LDAP com as credenciais do usuário,
        # leitura de displayName/mail/memberOf e chamada a self.sync_user(...)
        return None


class Microsoft365Provider(AuthProvider):
    key = "microsoft365"
    label = "Microsoft 365"

    def authenticate(self, data):
        # Ponto de integração: validar o id_token OIDC recebido do Entra ID
        return None


class GoogleWorkspaceProvider(AuthProvider):
    key = "google_workspace"
    label = "Google Workspace"

    def authenticate(self, data):
        # Ponto de integração: validar o id_token do Google e o domínio (hd)
        return None


PROVIDERS = {p.key: p for p in (LocalProvider(), ActiveDirectoryProvider(),
                                  Microsoft365Provider(), GoogleWorkspaceProvider())}


def get_provider(key):
    return PROVIDERS.get(key)


def list_providers():
    return [{"key": p.key, "label": p.label, "enabled": p.enabled} for p in PROVIDERS.values()]
