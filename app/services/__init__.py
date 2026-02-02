"""
Service layer for business logic.

This module provides service classes that encapsulate business logic,
separating it from HTTP handling in routes and data access in repositories.
"""

from app.services.base import (
    AuthorizationError,
    BaseService,
    NotFoundError,
    ServiceError,
    ValidationError,
)
from app.services.league_service import LeagueService, league_service

__all__ = [
    'BaseService',
    'ServiceError',
    'NotFoundError',
    'ValidationError',
    'AuthorizationError',
    'LeagueService',
    'league_service',
]
