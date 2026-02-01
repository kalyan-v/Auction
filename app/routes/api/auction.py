"""
Auction API endpoints.

Handles bidding, auction start/end, and price management.
Includes transaction handling and pessimistic locking to prevent race conditions.
"""

from flask import jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.logger import get_logger
from app.models import AuctionState, Bid, Player, Team
from app.routes import api_bp
from app.utils import admin_required, error_response, is_admin

logger = get_logger(__name__)


@api_bp.route('/bid', methods=['POST'])
def place_bid():
    """Place a bid on the current player.

    Uses pessimistic locking (SELECT FOR UPDATE) to prevent race conditions
    when multiple bids are placed concurrently.
    """
    if not is_admin():
        return error_response('Admin login required', 403)

    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    player_id = data.get('player_id')
    team_id = data.get('team_id')
    amount = data.get('amount')

    if not all([player_id, team_id, amount]):
        return error_response('player_id, team_id, and amount are required')

    # Validate player_id and team_id are valid integers
    try:
        player_id = int(player_id)
        team_id = int(team_id)
    except (TypeError, ValueError):
        return error_response('Invalid player_id or team_id')

    # Validate amount is a positive number
    try:
        amount = float(amount)
        if amount <= 0:
            return error_response('Bid amount must be positive')
    except (TypeError, ValueError):
        return error_response('Invalid bid amount')

    try:
        # SECURITY: Use pessimistic locking to prevent race conditions
        # Lock player and team rows for the duration of the transaction
        player = db.session.execute(
            select(Player).where(Player.id == player_id).with_for_update()
        ).scalar_one_or_none()

        team = db.session.execute(
            select(Team).where(Team.id == team_id).with_for_update()
        ).scalar_one_or_none()

        # Validate bid
        if not player or not team:
            db.session.rollback()
            return error_response('Invalid player or team')

        # Check player is in active auction
        if player.status != 'bidding':
            db.session.rollback()
            return error_response('Player is not up for auction')

        # Check if this is a base price bid (first bid) or a raise
        existing_bids = Bid.query.filter_by(player_id=player_id).count()

        if existing_bids == 0:
            # First bid - allow base price (equal to current price)
            if amount < player.current_price:
                db.session.rollback()
                return error_response('Bid must be at least the base price')
        else:
            # Subsequent bids - must be higher than current
            if amount <= player.current_price:
                db.session.rollback()
                return error_response('Bid must be higher than current price')

        if amount > team.budget:
            db.session.rollback()
            return error_response('Insufficient budget')

        # Record bid
        bid = Bid(player_id=player_id, team_id=team_id, amount=amount)
        player.current_price = amount
        db.session.add(bid)
        db.session.commit()

        return jsonify({'success': True, 'current_price': amount})

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error placing bid: {e}", exc_info=True)
        return error_response('Failed to place bid', 500)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error placing bid: {e}", exc_info=True)
        return error_response('Failed to place bid', 500)


@api_bp.route('/auction/start/<int:player_id>', methods=['POST'])
@admin_required
def start_auction(player_id: int):
    """Start auction for a specific player."""
    player = Player.query.get(player_id)
    if not player:
        return error_response('Player not found', 404)

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

    db.session.commit()

    return jsonify({'success': True})


@api_bp.route('/auction/end', methods=['POST'])
@admin_required
def end_auction():
    """End current auction and assign player to highest bidder.

    Uses pessimistic locking to prevent race conditions when
    modifying team budget.
    """
    try:
        auction_state = AuctionState.query.first()
        if not auction_state or not auction_state.is_active:
            return error_response('No active auction')

        player_id = auction_state.current_player_id

        # Lock player row for update
        player = db.session.execute(
            select(Player).where(Player.id == player_id).with_for_update()
        ).scalar_one_or_none()

        if not player:
            db.session.rollback()
            return error_response('Player not found')

        # Find highest bid
        highest_bid = (
            Bid.query
            .filter_by(player_id=player.id)
            .order_by(Bid.amount.desc())
            .first()
        )

        if highest_bid:
            # Lock team row before modifying budget
            team = db.session.execute(
                select(Team).where(Team.id == highest_bid.team_id).with_for_update()
            ).scalar_one_or_none()

            if not team:
                db.session.rollback()
                return error_response('Team not found')

            # SECURITY: Verify team still has sufficient budget
            if team.budget < highest_bid.amount:
                db.session.rollback()
                return error_response('Team has insufficient budget for this purchase')

            team.budget -= highest_bid.amount
            player.team_id = team.id
            player.status = 'sold'
        else:
            player.status = 'unsold'

        auction_state.is_active = False
        auction_state.current_player_id = None

        db.session.commit()

        return jsonify({'success': True})

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error ending auction: {e}", exc_info=True)
        return error_response('Failed to end auction', 500)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error ending auction: {e}", exc_info=True)
        return error_response('Failed to end auction', 500)


@api_bp.route('/auction/unsold', methods=['POST'])
@admin_required
def mark_unsold():
    """Mark current player as unsold."""
    auction_state = AuctionState.query.first()
    if not auction_state or not auction_state.is_active:
        return error_response('No active auction')

    player = Player.query.get(auction_state.current_player_id)
    if not player:
        return error_response('Player not found', 404)

    player.status = 'unsold'
    player.current_price = 0

    auction_state.is_active = False
    auction_state.current_player_id = None

    db.session.commit()

    return jsonify({'success': True})


@api_bp.route('/auction/reset-price', methods=['POST'])
@admin_required
def reset_price():
    """Reset the current player's price to a specific amount."""
    auction_state = AuctionState.query.first()
    if not auction_state or not auction_state.is_active:
        return error_response('No active auction')

    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    # Validate price is a positive number
    try:
        new_price = float(data.get('price', 0))
        if new_price <= 0:
            return error_response('Price must be positive')
    except (TypeError, ValueError):
        return error_response('Invalid price value')

    player = Player.query.get(auction_state.current_player_id)
    if not player:
        return error_response('Player not found', 404)

    player.current_price = new_price

    # Clear bids for this player above the new price
    Bid.query.filter(
        Bid.player_id == player.id,
        Bid.amount > new_price
    ).delete()

    db.session.commit()

    return jsonify({'success': True, 'new_price': new_price})


@api_bp.route('/teams', methods=['GET', 'POST'])
def manage_teams():
    """Get all teams or create a new team."""
    from app.routes.main import get_current_league

    current_league = get_current_league()

    if request.method == 'POST':
        if not is_admin():
            return error_response('Admin login required', 403)
        if not current_league:
            return error_response('No league selected. Create a league first.')

        data = request.get_json()
        if not data or 'name' not in data:
            return error_response('Team name is required')

        budget = data.get('budget', current_league.default_purse)
        team = Team(
            name=data['name'],
            budget=budget,
            initial_budget=budget,
            league_id=current_league.id
        )
        db.session.add(team)
        db.session.commit()
        return jsonify({'success': True, 'team_id': team.id})

    if current_league:
        teams = Team.query.filter_by(
            league_id=current_league.id, is_deleted=False
        ).all()
    else:
        teams = []

    return jsonify([{
        'id': t.id,
        'name': t.name,
        'budget': t.budget
    } for t in teams])
