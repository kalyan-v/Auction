"""
Service layer for business logic.

This module provides service classes that encapsulate business logic,
separating it from HTTP handling in routes and data access in repositories.
"""

from app.services.base import (
    NotFoundError,
    ServiceError,
    ValidationError,
)

__all__ = [
    'NotFoundError',
    'ServiceError',
    'ValidationError',
]
