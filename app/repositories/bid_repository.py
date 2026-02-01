"""
Bid repository for bid data access.

Provides specialized queries for bid entities.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app import db
from app.models import Bid
from app.repositories.base import BaseRepository


class BidRepository(BaseRepository[Bid]):
    """Repository for bid data access operations."""

    def __init__(self):
        super().__init__(Bid)

    def get_for_player(
        self,
        player_id: int,
        with_team: bool = False
    ) -> List[Bid]:
        """Get all bids for a player.

        Args:
            player_id: ID of the player.
            with_team: Eager load team relationship.

        Returns:
            List of Bid instances ordered by amount descending.
        """
        query = select(Bid).where(Bid.player_id == player_id)
        if with_team:
            query = query.options(joinedload(Bid.team))
        query = query.order_by(Bid.amount.desc())
        return db.session.execute(query).scalars().all()

    def get_highest_for_player(self, player_id: int) -> Optional[Bid]:
        """Get the highest bid for a player.

        Args:
            player_id: ID of the player.

        Returns:
            Highest Bid instance or None.
        """
        return db.session.execute(
            select(Bid)
            .where(Bid.player_id == player_id)
            .order_by(Bid.amount.desc())
        ).scalars().first()

    def count_for_player(self, player_id: int) -> int:
        """Count bids for a player.

        Args:
            player_id: ID of the player.

        Returns:
            Number of bids.
        """
        return self.count(player_id=player_id)

    def delete_for_player(self, player_id: int) -> int:
        """Delete all bids for a player.

        Args:
            player_id: ID of the player.

        Returns:
            Number of deleted bids.
        """
        return Bid.query.filter_by(player_id=player_id).delete()

    def delete_above_price(self, player_id: int, price: float) -> int:
        """Delete bids above a certain price.

        Args:
            player_id: ID of the player.
            price: Price threshold.

        Returns:
            Number of deleted bids.
        """
        return Bid.query.filter(
            Bid.player_id == player_id,
            Bid.amount > price
        ).delete()

    def get_by_team(self, team_id: int) -> List[Bid]:
        """Get all bids by a team.

        Args:
            team_id: ID of the team.

        Returns:
            List of Bid instances.
        """
        return self.filter_by(team_id=team_id)
