"""
Auction routes for the WPL Auction application.

Handles the main auction room interface.
"""

from flask import render_template

from app.models import AuctionState, Bid, League, Player, Team
from app.routes import auction_bp
from app.routes.main import get_current_league
from app.utils import is_admin


@auction_bp.route('/')
def auction_room():
    """Main auction interface."""
    current_league = get_current_league()
    all_leagues = League.query.filter_by(is_deleted=False).all()

    if current_league:
        teams = Team.query.filter_by(
            league_id=current_league.id, is_deleted=False
        ).all()
        players = Player.query.filter_by(
            league_id=current_league.id, status='available', is_deleted=False
        ).all()
        unsold_players = Player.query.filter_by(
            league_id=current_league.id, status='unsold', is_deleted=False
        ).all()
    else:
        teams = []
        players = []
        unsold_players = []

    auction_state = AuctionState.query.first()

    # Get highest bid for current player (if auction is active)
    highest_bid = None
    if auction_state and auction_state.is_active and auction_state.current_player_id:
        highest_bid = (
            Bid.query
            .filter_by(player_id=auction_state.current_player_id)
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
        all_leagues=all_leagues
    )
