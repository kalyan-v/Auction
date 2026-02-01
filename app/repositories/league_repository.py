"""
League repository for league data access.

Provides specialized queries for league entities.
"""

from typing import List, Optional

from sqlalchemy import select

from app import db
from app.models import League
from app.repositories.base import BaseRepository


class LeagueRepository(BaseRepository[League]):
    """Repository for league data access operations."""

    def __init__(self):
        super().__init__(League)

    def get_active(self) -> List[League]:
        """Get all active (non-deleted) leagues.

        Returns:
            List of active League instances.
        """
        return self.filter_by(is_deleted=False)

    def get_first_active(self) -> Optional[League]:
        """Get the first active league.

        Returns:
            First active League instance or None.
        """
        return self.first_by(is_deleted=False)

    def find_by_name(self, name: str) -> Optional[League]:
        """Find a league by name.

        Args:
            name: League name.

        Returns:
            League instance or None.
        """
        return self.first_by(name=name, is_deleted=False)

    def get_by_id_if_active(self, league_id: int) -> Optional[League]:
        """Get a league by ID if it's active.

        Args:
            league_id: ID of the league.

        Returns:
            League instance if active, None otherwise.
        """
        return self.first_by(id=league_id, is_deleted=False)
