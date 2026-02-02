"""
Team repository for team data access.

Provides specialized queries for team entities.
"""

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app import db
from app.models import Team
from app.repositories.base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    """Repository for team data access operations."""

    def __init__(self):
        super().__init__(Team)

    def get_by_league(
        self,
        league_id: int,
        include_deleted: bool = False
    ) -> List[Team]:
        """Get all teams for a league.

        Args:
            league_id: ID of the league.
            include_deleted: Include soft-deleted teams.

        Returns:
            List of Team instances.
        """
        query = select(Team).where(Team.league_id == league_id)
        if not include_deleted:
            query = query.where(Team.is_deleted == False)
        return db.session.execute(query).scalars().all()

    def get_with_players(self, team_id: int) -> Team:
        """Get a team with eager-loaded players.

        Args:
            team_id: ID of the team.

        Returns:
            Team instance with players loaded.
        """
        return db.session.execute(
            select(Team)
            .options(joinedload(Team.players))
            .where(Team.id == team_id)
        ).scalars().first()

    def get_all_with_players(self, league_id: int) -> List[Team]:
        """Get all teams with eager-loaded players.

        Args:
            league_id: ID of the league.

        Returns:
            List of Team instances with players loaded.
        """
        return db.session.execute(
            select(Team)
            .options(joinedload(Team.players))
            .where(
                Team.league_id == league_id,
                Team.is_deleted == False
            )
        ).scalars().unique().all()

    def find_by_name(self, name: str, league_id: int) -> Team:
        """Find a team by name in a league.

        Args:
            name: Team name.
            league_id: ID of the league.

        Returns:
            Team instance or None.
        """
        return self.first_by(name=name, league_id=league_id, is_deleted=False)
