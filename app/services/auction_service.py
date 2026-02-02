"""
Auction service for managing bidding and auction operations.

Encapsulates all business logic related to:
- Placing bids
- Starting/ending auctions
- Price management
- Player assignment
"""

from typing import Optional

from app import db
from app.db_utils import AuctionLock, BidLock, get_for_update
from app.logger import get_logger
from app.models import AuctionState, Bid, Player, Team
from app.repositories.bid_repository import BidRepository
from app.services.base import BaseService, NotFoundError, ValidationError

logger = get_logger(__name__)


class AuctionService(BaseService):
    """Service for auction-related operations.

    Handles bidding, auction lifecycle, and price management with proper
    locking and transaction handling.
    """

    def __init__(self, bid_repo: Optional[BidRepository] = None):
        """Initialize service with optional repository injection.

        Args:
            bid_repo: BidRepository instance (defaults to new instance).
        """
        self.bid_repo = bid_repo or BidRepository()

    def place_bid(
        self,
        player_id: int,
        team_id: int,
        amount: float
    ) -> dict:
        """Place a bid on a player.

        Args:
            player_id: ID of the player being bid on.
            team_id: ID of the team placing the bid.
            amount: Bid amount in rupees.

        Returns:
            Dict with success status and current price.

        Raises:
            ValidationError: If bid validation fails.
            NotFoundError: If player or team not found.
        """
        # Validate inputs
        if not player_id or not team_id:
            raise ValidationError("player_id and team_id are required")

        if not amount or amount <= 0:
            raise ValidationError("Bid amount must be positive")

        with BidLock():
            with self.transaction():
                player = get_for_update(Player, player_id)
                team = get_for_update(Team, team_id)

                if not player:
                    raise NotFoundError("Player not found")
                if not team:
                    raise NotFoundError("Team not found")

                # Check player is in active auction
                if player.status != 'bidding':
                    raise ValidationError("Player is not up for auction")

                # Check if this is a base price bid (first bid) or a raise
                existing_bids = self.bid_repo.count_for_player(player_id)

                if existing_bids == 0:
                    # First bid - allow base price (equal to current price)
                    if amount < player.current_price:
                        raise ValidationError("Bid must be at least the base price")
                else:
                    # Subsequent bids - must be higher than current
                    if amount <= player.current_price:
                        raise ValidationError("Bid must be higher than current price")

                # Check team budget
                if amount > team.budget:
                    raise ValidationError("Insufficient budget")

                # Record bid
                bid = Bid(player_id=player_id, team_id=team_id, amount=amount)
                player.current_price = amount
                db.session.add(bid)

                logger.info(
                    f"Bid placed: Team {team.name} bid {amount} on {player.name}"
                )

                return {'success': True, 'current_price': amount}

    def start_auction(self, player_id: int) -> dict:
        """Start auction for a specific player.

        Args:
            player_id: ID of the player to auction.

        Returns:
            Dict with success status.

        Raises:
            NotFoundError: If player not found.
        """
        with self.transaction():
            player = db.session.get(Player, player_id)
            if not player:
                raise NotFoundError("Player not found")

            # Get or create auction state
            auction_state = AuctionState.query.first()
            if not auction_state:
                auction_state = AuctionState()
                db.session.add(auction_state)

            auction_state.current_player_id = player_id
            auction_state.is_active = True
            auction_state.time_remaining = 300

            player.current_price = player.base_price
            player.status = 'bidding'

            logger.info(f"Auction started for player: {player.name}")

            return {'success': True}

    def end_auction(self) -> dict:
        """End current auction and assign player to highest bidder.

        Returns:
            Dict with success status and outcome details.

        Raises:
            ValidationError: If no active auction.
            NotFoundError: If player or team not found.
        """
        with AuctionLock():
            with self.transaction():
                auction_state = AuctionState.query.first()
                if not auction_state or not auction_state.is_active:
                    raise ValidationError("No active auction")

                player_id = auction_state.current_player_id
                player = get_for_update(Player, player_id)

                if not player:
                    raise NotFoundError("Player not found")

                # Find highest active bid
                highest_bid = self.bid_repo.get_highest_for_player(player.id)

                result = {'success': True}

                if highest_bid:
                    team = get_for_update(Team, highest_bid.team_id)

                    if not team:
                        raise NotFoundError("Team not found")

                    # Verify team still has sufficient budget
                    if team.budget < highest_bid.amount:
                        raise ValidationError(
                            "Team has insufficient budget for this purchase"
                        )

                    team.budget -= highest_bid.amount
                    player.team_id = team.id
                    player.status = 'sold'
                    result['sold_to'] = team.name
                    result['amount'] = highest_bid.amount

                    logger.info(
                        f"Player {player.name} sold to {team.name} for {highest_bid.amount}"
                    )
                else:
                    player.status = 'unsold'
                    result['sold_to'] = None
                    logger.info(f"Player {player.name} went unsold")

                auction_state.is_active = False
                auction_state.current_player_id = None

                return result

    def mark_unsold(self) -> dict:
        """Mark current player as unsold without accepting bids.

        Returns:
            Dict with success status.

        Raises:
            ValidationError: If no active auction.
            NotFoundError: If player not found.
        """
        with self.transaction():
            auction_state = AuctionState.query.first()
            if not auction_state or not auction_state.is_active:
                raise ValidationError("No active auction")

            player = db.session.get(Player, auction_state.current_player_id)
            if not player:
                raise NotFoundError("Player not found")

            player.status = 'unsold'
            player.current_price = 0

            auction_state.is_active = False
            auction_state.current_player_id = None

            logger.info(f"Player {player.name} marked as unsold")

            return {'success': True}

    def reset_price(self, new_price: float) -> dict:
        """Reset the current player's price to a specific amount.

        Args:
            new_price: The new price to set.

        Returns:
            Dict with success status and new price.

        Raises:
            ValidationError: If no active auction or invalid price.
            NotFoundError: If player not found.
        """
        if not new_price or new_price <= 0:
            raise ValidationError("Price must be positive")

        with self.transaction():
            auction_state = AuctionState.query.first()
            if not auction_state or not auction_state.is_active:
                raise ValidationError("No active auction")

            player = db.session.get(Player, auction_state.current_player_id)
            if not player:
                raise NotFoundError("Player not found")

            player.current_price = new_price

            # Soft delete bids for this player above the new price
            self.bid_repo.soft_delete_above_price(player.id, new_price)

            logger.info(f"Price reset to {new_price} for player {player.name}")

            return {'success': True, 'new_price': new_price}

    def get_auction_state(self) -> Optional[dict]:
        """Get the current auction state.

        Returns:
            Dict with auction state or None if no auction exists.
        """
        auction_state = AuctionState.query.first()
        if not auction_state:
            return None

        result = {
            'is_active': auction_state.is_active,
            'time_remaining': auction_state.time_remaining,
            'current_player_id': auction_state.current_player_id,
        }

        if auction_state.current_player:
            result['current_player'] = {
                'id': auction_state.current_player.id,
                'name': auction_state.current_player.name,
                'current_price': auction_state.current_player.current_price,
                'base_price': auction_state.current_player.base_price,
            }

        return result


# Singleton instance for use in routes
auction_service = AuctionService()
