"""
Base service class with transaction management.

Provides a foundation for all service classes with:
- Transaction context manager for automatic commit/rollback
- Custom exception hierarchy for consistent error handling
- Logging integration
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.logger import get_logger

logger = get_logger(__name__)


class ServiceError(Exception):
    """Base exception for service layer errors.

    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code for the error response.
    """

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(ServiceError):
    """Exception raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)


class ValidationError(ServiceError):
    """Exception raised when input validation fails."""

    def __init__(self, message: str):
        super().__init__(message, 400)


class AuthorizationError(ServiceError):
    """Exception raised when authorization fails."""

    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, 403)


class BaseService:
    """Base class for all services.

    Provides transaction management and common utilities for service classes.
    Services should inherit from this class to ensure consistent error handling
    and database transaction management.

    Example:
        class AuctionService(BaseService):
            def place_bid(self, player_id: int, team_id: int, amount: float):
                with self.transaction():
                    # Business logic here
                    # Automatically commits on success, rolls back on exception
                    pass
    """

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Context manager for database transactions.

        Automatically commits on successful completion and rolls back on any
        exception. Re-raises ServiceError subclasses as-is, wraps other
        exceptions in a generic ServiceError.

        Yields:
            None

        Raises:
            ServiceError: On database errors or unexpected exceptions.
        """
        try:
            yield
            db.session.commit()
        except ServiceError:
            db.session.rollback()
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise ServiceError("Database operation failed", 500)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise ServiceError("An unexpected error occurred", 500)

    def flush(self) -> None:
        """Flush pending changes to the database without committing.

        Useful when you need generated IDs before the transaction completes.
        """
        db.session.flush()
