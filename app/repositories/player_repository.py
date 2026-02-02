"""
Player repository for player data access.

Provides specialized queries for player entities.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app import db
from app.models import Player
from app.repositories.base import BaseRepository


class PlayerRepository(BaseRepository[Player]):
    """Repository for player data access operations."""

    def __init__(self):
        super().__init__(Player)

    def get_by_league(
        self,
        league_id: int,
        include_deleted: bool = False
    ) -> List[Player]:
        """Get all players for a league.

        Args:
            league_id: ID of the league.
            include_deleted: Include soft-deleted players.

        Returns:
            List of Player instances.
        """
        query = select(Player).where(Player.league_id == league_id)
        if not include_deleted:
            query = query.where(Player.is_deleted == False)
        return db.session.execute(query).scalars().all()

    def get_available(
        self,
        league_id: int,
        position: Optional[str] = None,
        include_unsold: bool = False
    ) -> List[Player]:
        """Get available players for auction.

        Args:
            league_id: ID of the league.
            position: Filter by position (optional).
            include_unsold: Include unsold players.

        Returns:
            List of available Player instances.
        """
        statuses = ['available']
        if include_unsold:
            statuses.append('unsold')

        query = select(Player).where(
            Player.league_id == league_id,
            Player.is_deleted == False,
            Player.status.in_(statuses)
        )

        if position:
            query = query.where(Player.position == position)

        return db.session.execute(query).scalars().all()

    def get_sold(self, league_id: int) -> List[Player]:
        """Get sold players with eager-loaded team.

        Args:
            league_id: ID of the league.

        Returns:
            List of sold Player instances with teams loaded.
        """
        return db.session.execute(
            select(Player)
            .options(joinedload(Player.team))
            .where(
                Player.league_id == league_id,
                Player.status == 'sold',
                Player.is_deleted == False
            )
        ).scalars().all()

    def get_by_team(self, team_id: int) -> List[Player]:
        """Get all players for a team.

        Args:
            team_id: ID of the team.

        Returns:
            List of Player instances.
        """
        return self.filter_by(team_id=team_id, is_deleted=False)

    def get_without_images(self, league_id: int) -> List[Player]:
        """Get players without images.

        Args:
            league_id: ID of the league.

        Returns:
            List of Player instances without images.
        """
        return db.session.execute(
            select(Player).where(
                Player.league_id == league_id,
                Player.is_deleted == False,
                (Player.image_url.is_(None) | (Player.image_url == ''))
            )
        ).scalars().all()

    def find_by_name(
        self,
        name: str,
        league_id: int
    ) -> Optional[Player]:
        """Find a player by exact name match.

        Args:
            name: Player name.
            league_id: ID of the league.

        Returns:
            Player instance or None.
        """
        return db.session.execute(
            select(Player).where(
                Player.league_id == league_id,
                Player.is_deleted == False,
                db.func.lower(Player.name) == name.lower()
            )
        ).scalars().first()
