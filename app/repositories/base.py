"""
Base repository class with common CRUD operations.

Provides a foundation for all repository classes with:
- Common query methods (get, get_all, filter_by)
- Soft delete support (automatically filters is_deleted=False)
- Row-level locking for concurrent access
"""

from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select

from app import db

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Base repository providing common data access operations.

    All query methods automatically filter out soft-deleted records
    for models that have an `is_deleted` column.

    Attributes:
        model: The SQLAlchemy model class this repository manages.
    """

    def __init__(self, model: Type[T]):
        """Initialize repository with a model class.

        Args:
            model: SQLAlchemy model class.
        """
        self.model = model

    @property
    def _has_soft_delete(self) -> bool:
        """Check if model supports soft delete."""
        return hasattr(self.model, 'is_deleted')

    def _apply_soft_delete_filter(self, query):
        """Apply is_deleted=False filter if model supports soft delete.

        Args:
            query: SQLAlchemy query to filter.

        Returns:
            Filtered query.
        """
        if self._has_soft_delete:
            query = query.where(self.model.is_deleted.is_(False))
        return query

    def get(self, id: int) -> Optional[T]:
        """Get a single entity by ID (excludes soft-deleted).

        Args:
            id: Primary key value.

        Returns:
            Entity instance or None if not found or soft-deleted.
        """
        query = select(self.model).where(self.model.id == id)
        query = self._apply_soft_delete_filter(query)
        return db.session.execute(query).scalars().first()

    def get_for_update(self, id: int) -> Optional[T]:
        """Get entity with row-level locking for updates.

        For PostgreSQL/MySQL, uses SELECT FOR UPDATE.
        For SQLite, relies on application-level locks.

        Args:
            id: Primary key value.

        Returns:
            Entity instance or None if not found.
        """
        from app.db_utils import get_for_update
        return get_for_update(self.model, id)

    def get_all(self) -> List[T]:
        """Get all non-deleted entities.

        Returns:
            List of all active entity instances.
        """
        query = select(self.model)
        query = self._apply_soft_delete_filter(query)
        return db.session.execute(query).scalars().all()

    def filter_by(self, **kwargs) -> List[T]:
        """Get entities matching filter criteria (auto-excludes soft-deleted).

        Args:
            **kwargs: Filter conditions as keyword arguments.

        Returns:
            List of matching entity instances.
        """
        query = select(self.model).filter_by(**kwargs)
        # Only add soft-delete filter if not explicitly provided
        if self._has_soft_delete and 'is_deleted' not in kwargs:
            query = query.where(self.model.is_deleted.is_(False))
        return db.session.execute(query).scalars().all()

    def first_by(self, **kwargs) -> Optional[T]:
        """Get first entity matching filter criteria (auto-excludes soft-deleted).

        Args:
            **kwargs: Filter conditions as keyword arguments.

        Returns:
            First matching entity or None.
        """
        query = select(self.model).filter_by(**kwargs)
        if self._has_soft_delete and 'is_deleted' not in kwargs:
            query = query.where(self.model.is_deleted.is_(False))
        return db.session.execute(query).scalars().first()

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
        """Count entities matching filter criteria (auto-excludes soft-deleted).

        Args:
            **kwargs: Filter conditions as keyword arguments.

        Returns:
            Count of matching entities.
        """
        if self._has_soft_delete and 'is_deleted' not in kwargs:
            kwargs['is_deleted'] = False
        return db.session.query(self.model).filter_by(**kwargs).count()

    def exists(self, **kwargs) -> bool:
        """Check if any entity matches filter criteria (auto-excludes soft-deleted).

        Args:
            **kwargs: Filter conditions as keyword arguments.

        Returns:
            True if at least one match exists.
        """
        return self.count(**kwargs) > 0
