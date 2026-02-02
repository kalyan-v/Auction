"""
Database utility functions for SQLite-compatible concurrency handling.

SQLite does not support row-level locking (SELECT FOR UPDATE).
This module provides alternative strategies:
1. Application-level locking using threading locks
2. Database-agnostic query helpers

For production with high concurrency, consider migrating to PostgreSQL
which supports true row-level locking.
"""

import threading
from functools import wraps
from typing import Any, Callable, Type, TypeVar

from sqlalchemy import select

from app import db

# Application-level locks for critical sections
# These work for single-process deployments (e.g., PythonAnywhere)
_bid_lock = threading.Lock()
_auction_lock = threading.Lock()
_player_lock = threading.Lock()

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


def is_sqlite() -> bool:
    """Check if the current database is SQLite."""
    return 'sqlite' in str(db.engine.url)


def get_for_update(model: Type[T], id_value: int) -> T | None:
    """
    Get a model instance with optional row-level locking.

    For SQLite: Returns regular query (relies on application-level locks)
    For PostgreSQL/MySQL: Uses with_for_update() for row-level locking

    Args:
        model: The SQLAlchemy model class
        id_value: The primary key value

    Returns:
        The model instance or None if not found
    """
    query = select(model).where(model.id == id_value)

    # Only use FOR UPDATE on databases that support row-level locking
    if not is_sqlite():
        query = query.with_for_update()

    return db.session.execute(query).scalar_one_or_none()


class BidLock:
    """
    Context manager for bidding operations.

    Provides thread-safe access to bidding operations.
    For SQLite, uses application-level locking.
    """

    def __enter__(self) -> 'BidLock':
        if is_sqlite():
            _bid_lock.acquire()
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: Any
    ) -> None:
        if is_sqlite():
            _bid_lock.release()


class AuctionLock:
    """
    Context manager for auction state changes.

    Provides thread-safe access to auction operations.
    """

    def __enter__(self) -> 'AuctionLock':
        if is_sqlite():
            _auction_lock.acquire()
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: Any
    ) -> None:
        if is_sqlite():
            _auction_lock.release()


class PlayerLock:
    """
    Context manager for player modification operations.

    Provides thread-safe access to player operations like release.
    """

    def __enter__(self) -> 'PlayerLock':
        if is_sqlite():
            _player_lock.acquire()
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: Any
    ) -> None:
        if is_sqlite():
            _player_lock.release()


def with_lock(lock_class: Type[BidLock | AuctionLock | PlayerLock]) -> Callable[[F], F]:
    """
    Decorator to wrap a function with a lock context manager.

    Args:
        lock_class: The lock class to use (BidLock, AuctionLock, or PlayerLock)

    Returns:
        Decorated function with lock protection
    """
    def decorator(f: F) -> F:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with lock_class():
                return f(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator
