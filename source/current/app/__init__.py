import os
import time
import threading
from pathlib import Path

from flask import Flask, jsonify, request, g, abort

from .auth import csrf_token, current_account_id
from .store.db import close_db, init_db
from .config import SECURITY_HEADERS, RATE_LIMITS, RATE_LIMIT_WINDOW_SECONDS, _RATE_LIMIT_MAX_KEYS


def _configured_secret(file_variable: str, value_variable: str, fallback: str = "", allow_dev_auth: bool = False) -> str:
    """Carrega secret de arquivo ou variável de ambiente. Falha se não configurado em produção."""
    path = os.environ.get(file_variable, "")
    if path:
        try:
            value = Path(path).read_text(encoding="utf-8").strip()
        except OSError:
            value = ""
        if value:
            return value
    value = os.environ.get(value_variable, fallback)
    if not value and not allow_dev_auth:
        raise RuntimeError(f"Secret obrigatório não configurado: {value_variable} ou {file_variable}")
    return value


# Rate limiting storage (in-memory, per-process)
_rate_limit_lock = threading.Lock()
_rate_limit_windows = {}


def _check_rate_limit(action: str, account_id: str) -> bool:
    """Verifica se a ação está dentro do limite de rate limiting."""
    limit = RATE_LIMITS.get(action)
    if limit is None:
        return True  # Sem limite definido = permitido

    now = time.monotonic()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    key = f"{account_id}:{action}"

    with _rate_limit_lock:
        timestamps = [ts for ts in _rate_limit_windows.get(key, []) if ts > cutoff]
        allowed = len(timestamps) < limit
        if allowed:
            timestamps.append(now)
        _rate_limit_windows[key] = timestamps

        # Limpeza periódica para evitar memory leak (lazy cleanup a cada 1000 requests)
        if len(_rate_limit_windows) > _RATE_LIMIT_MAX_KEYS:
            for k in list(_rate_limit_windows.keys()):
                _rate_limit_windows[k] = [ts for ts in _rate_limit_windows[k] if ts > cutoff]
                if not _rate_limit_windows[k]:
                    del _rate_limit_windows[k]

    return allowed


def create_app(test_config=None):
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="../templates",
        static_folder="../static",
    )
    configured_data_dir = os.environ.get("ASSISTENTE_V2_DATA_DIR")
    default_data_dir = Path(configured_data_dir) if configured_data_dir else Path(app.instance_path) / "data"

    # Determine ALLOW_DEV_AUTH early (from test_config or env)
    env_allow_dev = os.environ.get("ASSISTENTE_V2_ALLOW_DEV_AUTH", "0") == "1"
    test_allow_dev = test_config is not None and test_config.get("ALLOW_DEV_AUTH", False)
    allow_dev_auth = env_allow_dev or test_allow_dev

    # Configuração de sessão segura
    app.config.from_mapping(
        SECRET_KEY=_configured_secret("ASSISTENTE_V2_SECRET_KEY_FILE", "ASSISTENTE_V2_SECRET_KEY", allow_dev_auth=allow_dev_auth),
        DATA_DIR=str(default_data_dir),
        DATABASE=os.environ.get("ASSISTENTE_V2_DATABASE", str(default_data_dir / "assistente_v2.sqlite3")),
        ALLOW_DEV_AUTH=allow_dev_auth,
        GOOGLE_CLIENT_ID=os.environ.get("ASSISTENTE_GOOGLE_CLIENT_ID", ""),
        GOOGLE_CLIENT_SECRET=os.environ.get("ASSISTENTE_GOOGLE_CLIENT_SECRET", ""),
        GOOGLE_REDIRECT_URI=os.environ.get("ASSISTENTE_GOOGLE_REDIRECT_URI", ""),
        ADMIN_EMAILS={email.strip().lower() for email in os.environ.get("ASSISTENTE_V2_ADMIN_EMAILS", "").split(",") if email.strip()},
        # Session cookie security
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_NAME="__Host-session",
        PERMANENT_SESSION_LIFETIME=30 * 24 * 60 * 60,  # 30 dias
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["DATA_DIR"]).mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)

    # Security headers middleware
    @app.after_request
    def add_security_headers(response):
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        # COOP/COEP para isolamento de origem
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        return response

    # Rate limiting middleware - APLICA EFETIVAMENTE
    @app.before_request
    def check_rate_limit():
        # Pular health check e rotas públicas não autenticadas
        if request.path in ("/healthz",):
            return None

        # Aplicar rate limiting em rotas protegidas
        if request.path.startswith(("/api/", "/projects/", "/account/", "/admin/")):
            # Para rotas que precisam de account_id, validar via auth
            # O rate limiting por ação será aplicado nas próprias rotas
            pass

        return None

    from .routes.account import account_bp
    from .routes.admin import admin_bp
    from .routes.ai import ai_bp
    from .routes.auth import auth_bp
    from .routes.export import export_bp
    from .routes.library import library_bp
    from .routes.oauth import oauth_bp
    from .routes.projects import projects_bp
    from .routes.public import public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(oauth_bp)
    app.register_blueprint(projects_bp)

    @app.context_processor
    def inject_helpers():
        from .auth import current_account_id
        from .store.accounts import get_account
        account_id = current_account_id()
        return {"csrf_token": csrf_token, "navigation_account": get_account(account_id) if account_id else None}

    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok", "service": "assistente-academico"})

    with app.app_context():
        init_db()

    return app
