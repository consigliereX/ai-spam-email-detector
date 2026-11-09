"""Local-first Flask security settings without ML dependencies."""

import os
import secrets
import warnings

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def _bool_env(name, default=False, environ=None):
    env = os.environ if environ is None else environ
    raw = env.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def secret_key(environ=None):
    """Use a configured high-length secret or a fresh local-session secret."""
    env = os.environ if environ is None else environ
    value = env.get("FLASK_SECRET_KEY")
    if value is None:
        warnings.warn(
            "FLASK_SECRET_KEY is unset: using an ephemeral key. "
            "Sessions will expire on restart; set a persistent random key for deployment.",
            RuntimeWarning,
            stacklevel=2,
        )
        return secrets.token_hex(32)
    if len(value) < 32 or value != value.strip() or "change-me" in value.lower() or "replace-this" in value.lower():
        raise ValueError("FLASK_SECRET_KEY must be a random value of at least 32 characters (not a placeholder)")
    return value


def configure_security(app, environ=None):
    """Configure session cookies and bound the amount of submitted email text."""
    env = os.environ if environ is None else environ
    app.secret_key = secret_key(env)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_bool_env("FLASK_COOKIE_SECURE", environ=env),
        MAX_CONTENT_LENGTH=256 * 1024,
    )


def server_options(environ=None):
    """Options for the built-in *development* server; refuse accidental remote debug."""
    env = os.environ if environ is None else environ
    host = env.get("FLASK_HOST", "127.0.0.1").strip()
    if not host:
        raise ValueError("FLASK_HOST cannot be blank")
    try:
        port = int(env.get("PORT", "5000"))
    except ValueError as exc:
        raise ValueError("PORT must be an integer between 1 and 65535") from exc
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    debug = _bool_env("FLASK_DEBUG", environ=env)
    if host not in _LOOPBACK_HOSTS:
        if debug:
            raise ValueError("Flask debug mode must not be enabled on a non-loopback host")
        if not env.get("FLASK_SECRET_KEY"):
            raise ValueError("External binding requires an explicit FLASK_SECRET_KEY")
    return {"host": host, "port": port, "debug": debug}
