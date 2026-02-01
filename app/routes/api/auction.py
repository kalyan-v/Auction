"""
Auction API endpoints.

Handles bidding, auction start/end, and price management.
Business logic is delegated to AuctionService.
"""

from flask import jsonify, request

from app import db
from app.logger import get_logger
from app.models import Team
from app.routes import api_bp
from app.services import ServiceError
from app.services.auction_service import auction_service
from app.utils import admin_required, error_response, is_admin

logger = get_logger(__name__)


@api_bp.route('/bid', methods=['POST'])
def place_bid():
    """Place a bid on the current player."""
    if not is_admin():
        return error_response('Admin login required', 403)

    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    # Validate inputs
    try:
        player_id = int(data.get('player_id'))
        team_id = int(data.get('team_id'))
        amount = float(data.get('amount'))
    except (TypeError, ValueError):
        return error_response('Invalid player_id, team_id, or amount')

    try:
        result = auction_service.place_bid(player_id, team_id, amount)
        return jsonify(result)
    except ServiceError as e:
        return error_response(e.message, e.status_code)


@api_bp.route('/auction/start/<int:player_id>', methods=['POST'])
@admin_required
def start_auction(player_id: int):
    """Start auction for a specific player."""
    try:
        result = auction_service.start_auction(player_id)
        return jsonify(result)
    except ServiceError as e:
        return error_response(e.message, e.status_code)


@api_bp.route('/auction/end', methods=['POST'])
@admin_required
def end_auction():
    """End current auction and assign player to highest bidder."""
    try:
        result = auction_service.end_auction()
        return jsonify(result)
    except ServiceError as e:
        return error_response(e.message, e.status_code)


@api_bp.route('/auction/unsold', methods=['POST'])
@admin_required
def mark_unsold():
    """Mark current player as unsold."""
    try:
        result = auction_service.mark_unsold()
        return jsonify(result)
    except ServiceError as e:
        return error_response(e.message, e.status_code)


@api_bp.route('/auction/reset-price', methods=['POST'])
@admin_required
def reset_price():
    """Reset the current player's price to a specific amount."""
    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    try:
        new_price = float(data.get('price', 0))
    except (TypeError, ValueError):
        return error_response('Invalid price value')

    try:
        result = auction_service.reset_price(new_price)
        return jsonify(result)
    except ServiceError as e:
        return error_response(e.message, e.status_code)


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
