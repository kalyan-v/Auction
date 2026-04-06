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
from app.constants import DEFAULT_AUCTION_TIMER
from app.db_utils import AuctionLock, BidLock, get_for_update
from app.enums import PlayerStatus
from app.logger import get_logger
from app.models import AuctionState, Bid, League, Player, Team
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
        if player_id is None or team_id is None:
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

                # Validate player and team belong to the same league
                if player.league_id != team.league_id:
                    raise ValidationError("Player and team must belong to the same league")

                league_id = player.league_id

                # Check player is in active auction
                if player.status != PlayerStatus.BIDDING:
                    raise ValidationError("Player is not up for auction")

                # Check if this is a base price bid (first bid) or a raise
                existing_bids = self.bid_repo.count_for_player(player_id, league_id)

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

                # Record bid with league_id
                bid = Bid(
                    player_id=player_id,
                    team_id=team_id,
                    league_id=league_id,
                    amount=amount
                )
                player.current_price = amount
                db.session.add(bid)

                logger.info(
                    f"Bid placed: Team {team.name} bid {amount} on {player.name}"
                )

                return {'success': True, 'current_price': amount}

    def start_auction(self, player_id: int, league_id: Optional[int] = None) -> dict:
        """Start auction for a specific player.

        Args:
            player_id: ID of the player to auction.
            league_id: ID of the current league context (for cross-league validation).

        Returns:
            Dict with success status.

        Raises:
            NotFoundError: If player not found.
            ValidationError: If player doesn't belong to the current league.
        """
        if league_id is None:
            raise ValidationError("league_id is required to start an auction")

        with AuctionLock():
            with self.transaction():
                player = get_for_update(Player, player_id)
                if not player or player.is_deleted:
                    raise NotFoundError("Player not found")

                # Validate player belongs to the current league
                if player.league_id != league_id:
                    raise ValidationError("Player does not belong to the current league")

                # Get or create league-scoped auction state
                auction_state = AuctionState.query.filter_by(league_id=league_id).first()
                if not auction_state:
                    auction_state = AuctionState(league_id=league_id)
                    db.session.add(auction_state)

                # Clean up any previously active auction to avoid orphaned 'bidding' players
                if auction_state.is_active and auction_state.current_player_id:
                    prev_player = db.session.get(Player, auction_state.current_player_id)
                    if prev_player and prev_player.status == PlayerStatus.BIDDING:
                        prev_player.status = PlayerStatus.AVAILABLE
                        prev_player.current_price = prev_player.base_price
                        logger.warning(
                            f"Cleaned up stale auction for {prev_player.name} "
                            f"before starting auction for player_id={player_id}"
                        )

                auction_state.current_player_id = player_id
                auction_state.is_active = True
                auction_state.time_remaining = DEFAULT_AUCTION_TIMER

                player.current_price = player.base_price
                player.status = PlayerStatus.BIDDING

                # Soft-delete any old bids for this player (from previous auction rounds)
                self.bid_repo.soft_delete_for_player(player_id, league_id)

                logger.info(f"Auction started for player: {player.name}")

                return {'success': True}

    def end_auction(self, league_id: int, is_rtm: bool = False) -> dict:
        """End current auction and assign player to highest bidder.

        Args:
            league_id: ID of the league whose auction to end.
            is_rtm: Whether this sale uses a Right to Match (RTM).

        Returns:
            Dict with success status and outcome details.

        Raises:
            ValidationError: If no active auction or RTM limit exceeded.
            NotFoundError: If player or team not found.
        """
        with AuctionLock():
            with self.transaction():
                auction_state = AuctionState.query.filter_by(
                    league_id=league_id
                ).first()
                if not auction_state or not auction_state.is_active:
                    raise ValidationError("No active auction")

                player_id = auction_state.current_player_id
                player = get_for_update(Player, player_id)

                if not player:
                    raise NotFoundError("Player not found")

                # Find highest active bid
                highest_bid = self.bid_repo.get_highest_for_player(player.id, league_id)

                result = {'success': True}

                if highest_bid:
                    team = get_for_update(Team, highest_bid.team_id)

                    if not team:
                        raise NotFoundError("Team not found")

                    # Validate RTM limit if RTM is being used
                    if is_rtm:
                        league = db.session.get(League, league_id)
                        if league:
                            max_rtm = league.max_rtm or 0
                            if max_rtm <= 0:
                                raise ValidationError(
                                    "RTM is not enabled for this league"
                                )
                            # Count existing RTMs used by this team in this league
                            rtm_used = Player.query.filter_by(
                                team_id=team.id,
                                league_id=league_id,
                                is_rtm=True,
                                status=PlayerStatus.SOLD,
                                is_deleted=False
                            ).count()
                            if rtm_used >= max_rtm:
                                raise ValidationError(
                                    f"{team.name} has already used all {max_rtm} RTMs allowed"
                                )

                    # Verify team still has sufficient budget
                    if team.budget < highest_bid.amount:
                        raise ValidationError(
                            "Team has insufficient budget for this purchase"
                        )

                    team.budget -= highest_bid.amount
                    player.team_id = team.id
                    player.status = PlayerStatus.SOLD
                    player.is_rtm = is_rtm
                    result['sold_to'] = team.name
                    result['amount'] = highest_bid.amount
                    result['is_rtm'] = is_rtm

                    logger.info(
                        f"Player {player.name} sold to {team.name} for {highest_bid.amount}"
                        f"{' (RTM)' if is_rtm else ''}"
                    )
                else:
                    player.status = PlayerStatus.UNSOLD
                    result['sold_to'] = None
                    logger.info(f"Player {player.name} went unsold")

                auction_state.is_active = False
                auction_state.current_player_id = None

                return result

    def mark_unsold(self, league_id: int) -> dict:
        """Mark current player as unsold without accepting bids.

        Args:
            league_id: ID of the league whose auction to mark unsold.

        Returns:
            Dict with success status.

        Raises:
            ValidationError: If no active auction.
            NotFoundError: If player not found.
        """
        with AuctionLock():
            with self.transaction():
                auction_state = AuctionState.query.filter_by(
                    league_id=league_id
                ).first()
                if not auction_state or not auction_state.is_active:
                    raise ValidationError("No active auction")

                player = db.session.get(Player, auction_state.current_player_id)
                if not player:
                    raise NotFoundError("Player not found")

                player.status = PlayerStatus.UNSOLD
                player.current_price = 0

                # Soft delete any bids from this auction round
                self.bid_repo.soft_delete_for_player(player.id, league_id)

                auction_state.is_active = False
                auction_state.current_player_id = None

                logger.info(f"Player {player.name} marked as unsold")

                return {'success': True}

    def reset_price(self, league_id: int, new_price: float) -> dict:
        """Reset the current player's price to a specific amount.

        Args:
            league_id: ID of the league.
            new_price: The new price to set.

        Returns:
            Dict with success status and new price.

        Raises:
            ValidationError: If no active auction or invalid price.
            NotFoundError: If player not found.
        """
        if not new_price or new_price <= 0:
            raise ValidationError("Price must be positive")

        with AuctionLock():
            with self.transaction():
                auction_state = AuctionState.query.filter_by(
                    league_id=league_id
                ).first()
                if not auction_state or not auction_state.is_active:
                    raise ValidationError("No active auction")

                player = db.session.get(Player, auction_state.current_player_id)
                if not player:
                    raise NotFoundError("Player not found")

                player.current_price = new_price

                # Soft delete ALL bids for this player so the next bid is
                # treated as a first bid (allowed at the reset price).
                self.bid_repo.soft_delete_for_player(player.id, league_id)

                logger.info(f"Price reset to {new_price} for player {player.name}")

                return {'success': True, 'new_price': new_price}


# Singleton instance for use in routes
auction_service = AuctionService()
