"""
Flask extensions initialization.

Extensions are initialized here and imported by the app factory.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

# Rate limiter - initialized without app, will be init_app() in create_app()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per minute"],
    storage_uri="memory://",
)

# CSRF protection - protects all POST/PUT/DELETE requests
csrf = CSRFProtect()
