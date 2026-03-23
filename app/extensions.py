"""
Flask extensions initialization.

Extensions are initialized here and imported by the app factory.
"""

from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect


def _get_client_ip() -> str:
    """Get real client IP, accounting for reverse proxies."""
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return get_remote_address()


# Rate limiter - initialized without app, will be init_app() in create_app()
limiter = Limiter(
    key_func=_get_client_ip,
    default_limits=["60 per minute"],
    storage_uri="memory://",
)

# CSRF protection - protects all POST/PUT/DELETE requests
csrf = CSRFProtect()
