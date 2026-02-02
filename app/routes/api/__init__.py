"""
API routes package for the WPL Auction application.

Contains all API endpoints organized by functionality.
"""

# Import submodules to register routes
from app.routes.api import players, fantasy, cricket, leagues, auction

__all__ = ['players', 'fantasy', 'cricket', 'leagues', 'auction']
