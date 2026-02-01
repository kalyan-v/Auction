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

__all__ = [
    'BaseService',
    'ServiceError',
    'NotFoundError',
    'ValidationError',
    'AuthorizationError',
]
