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
from typing import Any, Type, TypeVar

from sqlalchemy import select

from app import db

# Application-level locks for critical sections
# These work for single-process deployments (e.g., PythonAnywhere)
# WARNING: These do NOT protect across multiple gunicorn workers or processes.
# For multi-worker production deployments, migrate to PostgreSQL with
# row-level locking (with_for_update) or use Redis-based distributed locks.
# RLock allows the same thread to re-enter the lock without deadlocking
_bid_lock = threading.RLock()
_auction_lock = threading.RLock()
_player_lock = threading.RLock()

T = TypeVar('T')


def is_sqlite() -> bool:
    """Check if the current database is SQLite."""
    return 'sqlite' in str(db.engine.url)


def get_for_update(model: Type[T], id_value: int) -> T | None:
    """
    Get a model instance with optional row-level locking.

    For SQLite: Returns regular query (relies on application-level locks).
                IMPORTANT: Callers MUST wrap usage in BidLock()/AuctionLock()/PlayerLock()
                to ensure thread safety. These locks only protect within a single process.
    For PostgreSQL/MySQL: Uses with_for_update() for row-level locking.

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


class _SQLiteLock:
    """Context manager that acquires a threading lock only on SQLite.

    For PostgreSQL/MySQL, these operations use row-level locking instead.
    For SQLite (single-process deployments), uses application-level locks.
    """

    def __init__(self, lock: threading.RLock) -> None:
        self._lock = lock

    def __enter__(self) -> '_SQLiteLock':
        if is_sqlite():
            self._lock.acquire()
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: Any
    ) -> None:
        if is_sqlite():
            self._lock.release()


def BidLock() -> _SQLiteLock:
    """Lock for bidding operations."""
    return _SQLiteLock(_bid_lock)


def AuctionLock() -> _SQLiteLock:
    """Lock for auction state changes."""
    return _SQLiteLock(_auction_lock)


def PlayerLock() -> _SQLiteLock:
    """Lock for player modification operations."""
    return _SQLiteLock(_player_lock)
