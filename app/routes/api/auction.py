"""
Auction API endpoints.

Handles bidding, auction start/end, and price management.
"""

from flask import jsonify, request

from app import db
from app.models import AuctionState, Bid, Player, Team
from app.routes import api_bp
from app.utils import admin_required, error_response, is_admin


@api_bp.route('/bid', methods=['POST'])
def place_bid():
    """Place a bid on the current player."""
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

    player = Player.query.get(player_id)
    team = Team.query.get(team_id)

    # Validate bid
    if not player or not team:
        return error_response('Invalid player or team')

    # Check player is in active auction
    if player.status != 'bidding':
        return error_response('Player is not up for auction')

    # Check if this is a base price bid (first bid) or a raise
    existing_bids = Bid.query.filter_by(player_id=player_id).count()

    if existing_bids == 0:
        # First bid - allow base price (equal to current price)
        if amount < player.current_price:
            return error_response('Bid must be at least the base price')
    else:
        # Subsequent bids - must be higher than current
        if amount <= player.current_price:
            return error_response('Bid must be higher than current price')

    if amount > team.budget:
        return error_response('Insufficient budget')

    # Record bid
    bid = Bid(player_id=player_id, team_id=team_id, amount=amount)
    player.current_price = amount
    db.session.add(bid)
    db.session.commit()

    return jsonify({'success': True, 'current_price': amount})


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
    """End current auction and assign player to highest bidder."""
    auction_state = AuctionState.query.first()
    if not auction_state or not auction_state.is_active:
        return error_response('No active auction')

    player = Player.query.get(auction_state.current_player_id)
    if not player:
        return error_response('Player not found')

    # Find highest bid
    highest_bid = (
        Bid.query
        .filter_by(player_id=player.id)
        .order_by(Bid.amount.desc())
        .first()
    )

    if highest_bid:
        # Assign player to team
        team = Team.query.get(highest_bid.team_id)
        team.budget -= highest_bid.amount
        player.team_id = team.id
        player.status = 'sold'
    else:
        player.status = 'unsold'

    auction_state.is_active = False
    auction_state.current_player_id = None

    db.session.commit()

    return jsonify({'success': True})


@api_bp.route('/auction/unsold', methods=['POST'])
@admin_required
def mark_unsold():
    """Mark current player as unsold."""
    auction_state = AuctionState.query.first()
    if not auction_state or not auction_state.is_active:
        return error_response('No active auction')

    player = Player.query.get(auction_state.current_player_id)
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
    new_price = data.get('price', 0)

    if new_price <= 0:
        return error_response('Invalid price')

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
