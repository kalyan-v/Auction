"""
Auction routes for the WPL Auction application.

Handles the main auction room interface.
"""

from flask import render_template
from sqlalchemy.orm import joinedload

from app.constants import DEFAULT_BID_INCREMENT
from app.enums import PlayerStatus
from app.models import AuctionCategory, AuctionState, Bid, League, Player, Team
from app.routes import auction_bp
from app.routes.main import get_current_league
from app.utils import is_admin


@auction_bp.route('/')
def auction_room() -> str:
    """Main auction interface."""
    current_league = get_current_league()
    all_leagues = League.query.filter_by(is_deleted=False).all()

    if current_league:
        teams = Team.query.filter_by(
            league_id=current_league.id, is_deleted=False
        ).all()
        # Single query for both available and unsold players
        all_pool = Player.query.filter(
            Player.league_id == current_league.id,
            Player.is_deleted.is_(False),
            Player.status.in_([PlayerStatus.AVAILABLE, PlayerStatus.UNSOLD])
        ).all()

        # Build category sort order lookup from AuctionCategory
        category_order = {}
        for cat in AuctionCategory.query.filter_by(
            league_id=current_league.id, is_deleted=False
        ).all():
            category_order[cat.name] = cat.sort_order

        def player_sort_key(p: Player) -> tuple:
            cat_ord = category_order.get(p.auction_category, 999)
            return (cat_ord, p.original_team or '', p.name)

        players = sorted(
            [p for p in all_pool if p.status == PlayerStatus.AVAILABLE],
            key=player_sort_key
        )
        unsold_players = [p for p in all_pool if p.status == PlayerStatus.UNSOLD]
    else:
        teams = []
        players = []
        unsold_players = []

    auction_state = AuctionState.query.filter_by(
        league_id=current_league.id
    ).first() if current_league else None

    # Get highest bid for current player (if auction is active)
    highest_bid = None
    if auction_state and auction_state.is_active and auction_state.current_player_id:
        highest_bid = (
            Bid.query
            .filter_by(player_id=auction_state.current_player_id, is_deleted=False)
            .options(joinedload(Bid.team))
            .order_by(Bid.amount.desc())
            .first()
        )

    return render_template(
        'auction.html',
        teams=teams,
        players=players,
        unsold_players=unsold_players,
        auction_state=auction_state,
        highest_bid=highest_bid,
        admin_mode=is_admin(),
        current_league=current_league,
        all_leagues=all_leagues,
        bid_increment_tiers=current_league.bid_increment_tiers_parsed if current_league else [{'threshold': 0, 'increment': DEFAULT_BID_INCREMENT}],
        auction_categories=(
            [c for c in current_league.auction_categories if not c.is_deleted]
            if current_league else []
        )
    )
