"""
Base repository class with common CRUD operations.

Provides a foundation for all repository classes with:
- Common query methods (get, get_all, filter_by)
- Soft delete support
- Row-level locking for concurrent access
"""

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Query

from app import db
from app.db_utils import is_sqlite

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Base repository providing common data access operations.

    Attributes:
        model: The SQLAlchemy model class this repository manages.
    """

    def __init__(self, model: Type[T]):
        """Initialize repository with a model class.

        Args:
            model: SQLAlchemy model class.
        """
        self.model = model

    def get(self, id: int) -> Optional[T]:
        """Get a single entity by ID.

        Args:
            id: Primary key value.

        Returns:
            Entity instance or None if not found.
        """
        return db.session.get(self.model, id)

    def get_for_update(self, id: int) -> Optional[T]:
        """Get entity with row-level locking for updates.

        For PostgreSQL/MySQL, uses SELECT FOR UPDATE.
        For SQLite, relies on application-level locks.

        Args:
            id: Primary key value.

        Returns:
            Entity instance or None if not found.
        """
        query = select(self.model).where(self.model.id == id)

        if not is_sqlite():
            query = query.with_for_update()

        return db.session.execute(query).scalar_one_or_none()

    def get_all(self) -> List[T]:
        """Get all entities.

        Returns:
            List of all entity instances.
        """
        return db.session.execute(select(self.model)).scalars().all()

    def filter_by(self, **kwargs) -> List[T]:
        """Get entities matching filter criteria.

        Args:
            **kwargs: Filter conditions as keyword arguments.

        Returns:
            List of matching entity instances.
        """
        return db.session.execute(
            select(self.model).filter_by(**kwargs)
        ).scalars().all()

    def first_by(self, **kwargs) -> Optional[T]:
        """Get first entity matching filter criteria.

        Args:
            **kwargs: Filter conditions as keyword arguments.

        Returns:
            First matching entity or None.
        """
        return db.session.execute(
            select(self.model).filter_by(**kwargs)
        ).scalars().first()

    def create(self, **kwargs) -> T:
        """Create a new entity.

        Args:
            **kwargs: Entity attributes.

        Returns:
            Created entity instance (not yet committed).
        """
        instance = self.model(**kwargs)
        db.session.add(instance)
        return instance

    def delete(self, instance: T) -> None:
        """Hard delete an entity.

        Args:
            instance: Entity to delete.
        """
        db.session.delete(instance)

    def soft_delete(self, instance: T) -> None:
        """Soft delete an entity by setting is_deleted flag.

        Args:
            instance: Entity to soft delete.
        """
        if hasattr(instance, 'is_deleted'):
            instance.is_deleted = True

    def count(self, **kwargs) -> int:
        """Count entities matching filter criteria.

        Args:
            **kwargs: Filter conditions as keyword arguments.

        Returns:
            Count of matching entities.
        """
        return db.session.query(self.model).filter_by(**kwargs).count()

    def exists(self, **kwargs) -> bool:
        """Check if any entity matches filter criteria.

        Args:
            **kwargs: Filter conditions as keyword arguments.

        Returns:
            True if at least one match exists.
        """
        return self.count(**kwargs) > 0

    def query(self) -> Query:
        """Get a query object for the model.

        Returns:
            SQLAlchemy Query object.
        """
        return self.model.query
