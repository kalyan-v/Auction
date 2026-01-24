"""
Routes package for the WPL Auction application.

This module registers all blueprints and provides a clean interface
for the application to import routes.
"""

from flask import Blueprint

# Create blueprints
main_bp = Blueprint('main', __name__)
auction_bp = Blueprint('auction', __name__)
api_bp = Blueprint('api', __name__)

# Import route handlers to register them with blueprints
# These imports must come after blueprint creation to avoid circular imports
from app.routes import main, auction
from app.routes.api import players, fantasy, cricket, leagues, auction as auction_api

__all__ = ['main_bp', 'auction_bp', 'api_bp']
