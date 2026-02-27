"""
Bid repository for bid data access.

Provides specialized queries for bid entities.
"""

from typing import Optional

from sqlalchemy import select, update

from app import db
from app.models import Bid
from app.repositories.base import BaseRepository


class BidRepository(BaseRepository[Bid]):
    """Repository for bid data access operations."""

    def __init__(self):
        super().__init__(Bid)

    def get_highest_for_player(self, player_id: int) -> Optional[Bid]:
        """Get the highest active bid for a player.

        Args:
            player_id: ID of the player.

        Returns:
            Highest Bid instance or None.
        """
        return db.session.execute(
            select(Bid)
            .where(
                Bid.player_id == player_id,
                Bid.is_deleted.is_(False)
            )
            .order_by(Bid.amount.desc())
        ).scalars().first()

    def count_for_player(self, player_id: int) -> int:
        """Count active bids for a player.

        Args:
            player_id: ID of the player.

        Returns:
            Number of bids.
        """
        return self.count(player_id=player_id, is_deleted=False)

    def soft_delete_for_player(self, player_id: int) -> int:
        """Soft delete all bids for a player.

        Args:
            player_id: ID of the player.

        Returns:
            Number of soft-deleted bids.
        """
        result = db.session.execute(
            update(Bid)
            .where(Bid.player_id == player_id, Bid.is_deleted.is_(False))
            .values(is_deleted=True)
        )
        return result.rowcount

    def soft_delete_above_price(self, player_id: int, price: float) -> int:
        """Soft delete bids above a certain price.

        Args:
            player_id: ID of the player.
            price: Price threshold.

        Returns:
            Number of soft-deleted bids.
        """
        result = db.session.execute(
            update(Bid)
            .where(
                Bid.player_id == player_id,
                Bid.amount > price,
                Bid.is_deleted.is_(False)
            )
            .values(is_deleted=True)
        )
        return result.rowcount
