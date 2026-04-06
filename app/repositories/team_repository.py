"""
Team repository for team data access.

Provides league-scoped queries for team entities.
"""

from typing import List, Optional

from app.models import Team
from app.repositories.base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    """Repository for team data access operations.

    All queries are league-scoped to ensure proper data isolation.
    """

    def __init__(self):
        super().__init__(Team)

    def get_by_league(self, league_id: int) -> List[Team]:
        """Get all active teams for a league.

        Args:
            league_id: ID of the league.

        Returns:
            List of Team instances.
        """
        return self.filter_by(league_id=league_id)

    def find_by_name(self, name: str, league_id: int) -> Optional[Team]:
        """Find a team by name in a league.

        Args:
            name: Team name.
            league_id: ID of the league.

        Returns:
            Team instance or None.
        """
        return self.first_by(name=name, league_id=league_id)
