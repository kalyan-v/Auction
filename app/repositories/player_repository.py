"""
Player repository for player data access.

Provides league-scoped queries for player entities.
"""

from typing import List, Optional

from app import db
from app.enums import PlayerStatus
from app.models import Player
from app.repositories.base import BaseRepository


class PlayerRepository(BaseRepository[Player]):
    """Repository for player data access operations.

    All queries are league-scoped to ensure proper data isolation.
    """

    def __init__(self):
        super().__init__(Player)

    def get_by_league(self, league_id: int) -> List[Player]:
        """Get all active players for a league.

        Args:
            league_id: ID of the league.

        Returns:
            List of Player instances.
        """
        return self.filter_by(league_id=league_id)

    def get_available(
        self,
        league_id: int,
        position: Optional[str] = None,
        include_unsold: bool = False,
        auction_category: Optional[str] = None
    ) -> List[Player]:
        """Get available players for auction.

        Args:
            league_id: ID of the league.
            position: Filter by position (optional).
            include_unsold: Include unsold players.
            auction_category: Filter by auction category (optional).

        Returns:
            List of available Player instances.
        """
        if include_unsold:
            query = Player.query.filter(
                Player.league_id == league_id,
                Player.is_deleted.is_(False),
                Player.status.in_([PlayerStatus.AVAILABLE, PlayerStatus.UNSOLD])
            )
        else:
            query = Player.query.filter_by(
                league_id=league_id,
                is_deleted=False,
                status=PlayerStatus.AVAILABLE
            )

        if position:
            query = query.filter_by(position=position)

        if auction_category:
            query = query.filter_by(auction_category=auction_category)

        return query.all()

    def get_random(
        self,
        league_id: int,
        position: Optional[str] = None,
        include_unsold: bool = False,
        auction_category: Optional[str] = None
    ) -> Optional[Player]:
        """Get a random available player using SQL-level randomization.

        Args:
            league_id: ID of the league.
            position: Filter by position (optional).
            include_unsold: Include unsold players.
            auction_category: Filter by auction category (optional).

        Returns:
            Random Player instance or None.
        """
        if include_unsold:
            query = Player.query.filter(
                Player.league_id == league_id,
                Player.is_deleted.is_(False),
                Player.status.in_([PlayerStatus.AVAILABLE, PlayerStatus.UNSOLD])
            )
        else:
            query = Player.query.filter_by(
                league_id=league_id,
                is_deleted=False,
                status=PlayerStatus.AVAILABLE
            )

        if position:
            query = query.filter_by(position=position)

        if auction_category:
            query = query.filter_by(auction_category=auction_category)

        return query.order_by(db.func.random()).first()

    def get_sold(self, league_id: int) -> List[Player]:
        """Get all sold players for a league.

        Args:
            league_id: ID of the league.

        Returns:
            List of sold Player instances.
        """
        return self.filter_by(league_id=league_id, status=PlayerStatus.SOLD)

    def find_by_name(self, name: str, league_id: int) -> Optional[Player]:
        """Find a player by exact name (case-insensitive) in a league.

        Args:
            name: Player name to search.
            league_id: ID of the league.

        Returns:
            Player instance or None.
        """
        return Player.query.filter(
            Player.league_id == league_id,
            Player.is_deleted.is_(False),
            db.func.lower(Player.name) == name.lower()
        ).first()
