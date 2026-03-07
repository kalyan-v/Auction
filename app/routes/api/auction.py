"""
Auction API endpoints.

Handles bidding, auction start/end, and price management.
Business logic is delegated to AuctionService.
"""

from flask import Response, jsonify, request

from app.extensions import limiter
from app.logger import get_logger
from app.routes import api_bp
from app.routes.main import get_current_league
from app.services.auction_service import auction_service
from app.services.team_service import team_service
from app.utils import (
    admin_required, error_response, get_json_body, is_admin, validate_positive_float
)

logger = get_logger(__name__)


@api_bp.route('/bid', methods=['POST'])
@limiter.limit("30 per minute")
@admin_required
def place_bid() -> tuple[Response, int] | Response:
    """Place a bid on the current player.

    Returns:
        JSON response with bid result.
    """
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

    result = auction_service.place_bid(player_id, team_id, amount)
    return jsonify(result)


@api_bp.route('/auction/start/<int:player_id>', methods=['POST'])
@limiter.limit("10 per minute")
@admin_required
def start_auction(player_id: int) -> tuple[Response, int] | Response:
    """Start auction for a specific player.

    Args:
        player_id: ID of the player to auction.

    Returns:
        JSON response with auction start result.
    """
    current_league = get_current_league()
    league_id = current_league.id if current_league else None
    result = auction_service.start_auction(player_id, league_id=league_id)
    return jsonify(result)


@api_bp.route('/auction/end', methods=['POST'])
@limiter.limit("10 per minute")
@admin_required
def end_auction() -> tuple[Response, int] | Response:
    """End current auction and assign player to highest bidder.

    Returns:
        JSON response with auction end result.
    """
    data = request.get_json(silent=True) or {}
    is_rtm = bool(data.get('is_rtm', False))
    result = auction_service.end_auction(is_rtm=is_rtm)
    return jsonify(result)


@api_bp.route('/auction/unsold', methods=['POST'])
@limiter.limit("10 per minute")
@admin_required
def mark_unsold() -> tuple[Response, int] | Response:
    """Mark current player as unsold.

    Returns:
        JSON response with unsold result.
    """
    result = auction_service.mark_unsold()
    return jsonify(result)


@api_bp.route('/auction/reset-price', methods=['POST'])
@limiter.limit("20 per minute")
@admin_required
def reset_price() -> tuple[Response, int] | Response:
    """Reset the current player's price to a specific amount.

    Returns:
        JSON response with price reset result.
    """
    data, error = get_json_body()
    if error:
        return error

    new_price, price_error = validate_positive_float(data.get('price'), 'price')
    if price_error:
        return error_response(price_error)

    result = auction_service.reset_price(new_price)
    return jsonify(result)


@api_bp.route('/teams', methods=['GET', 'POST'])
def manage_teams() -> tuple[Response, int] | Response:
    """Get all teams or create a new team.

    Returns:
        JSON response with teams list or creation result.
    """
    current_league = get_current_league()

    if request.method == 'POST':
        if not is_admin():
            return error_response('Admin login required', 403)
        if not current_league:
            return error_response('No league selected. Create a league first.')

        data = request.get_json()
        if not data or 'name' not in data:
            return error_response('Team name is required')

        budget = data.get('budget')
        if budget is not None:
            try:
                budget = float(budget)
            except (TypeError, ValueError):
                return error_response('Invalid budget value')
            if budget <= 0:
                return error_response('Budget must be positive')

        result = team_service.create_team(
            name=data['name'],
            league_id=current_league.id,
            budget=budget,
            default_purse=current_league.default_purse
        )
        return jsonify(result)

    # GET request - return all teams
    if current_league:
        teams = team_service.get_teams(current_league.id)
    else:
        teams = []

    return jsonify(teams)
