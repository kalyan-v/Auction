"""
Fantasy points API endpoints.

Handles fantasy points management, awards, and data fetching.
Business logic is delegated to FantasyService.
"""

from flask import Response, jsonify, request

from app.logger import get_logger
from app.models import Player
from app.routes import api_bp
from app.routes.main import get_current_league
from app.services.base import NotFoundError, ValidationError
from app.services.fantasy_service import fantasy_service
from app.utils import admin_required, error_response, is_admin

logger = get_logger(__name__)


# ==================== FANTASY POINTS CRUD ====================

@api_bp.route('/fantasy/points', methods=['POST'])
@admin_required
def update_fantasy_points() -> tuple[Response, int] | Response:
    """Update fantasy points for a player.

    Returns:
        JSON response with updated points.
    """
    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    player_id = data.get('player_id')
    points = data.get('points', 0)

    # Validate player_id
    try:
        player_id = int(player_id)
    except (TypeError, ValueError):
        return error_response('Invalid player_id')

    # Validate points
    try:
        points = float(points)
    except (TypeError, ValueError):
        return error_response('Invalid points value')

    try:
        result = fantasy_service.update_player_points(player_id, points)
        return jsonify(result)
    except NotFoundError as e:
        return error_response(e.message, e.status_code)


@api_bp.route('/fantasy/points/add', methods=['POST'])
@admin_required
def add_match_points() -> tuple[Response, int] | Response:
    """Add fantasy points for a specific match.

    Returns:
        JSON response with match points and total.
    """
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected')

    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    player_id = data.get('player_id')
    match_number = data.get('match_number')
    points = data.get('points', 0)

    if not player_id or not match_number:
        return error_response('Player ID and match number required')

    # Validate player_id and match_number
    try:
        player_id = int(player_id)
        match_number = int(match_number)
    except (TypeError, ValueError):
        return error_response('Invalid player_id or match_number')

    # Validate points
    try:
        points = float(points)
    except (TypeError, ValueError):
        return error_response('Invalid points value')

    try:
        result = fantasy_service.add_match_points(
            player_id=player_id,
            match_number=match_number,
            points=points,
            league_id=current_league.id
        )
        return jsonify(result)
    except NotFoundError as e:
        return error_response(e.message, e.status_code)


@api_bp.route('/fantasy/points/<int:player_id>', methods=['GET'])
def get_player_match_points(player_id: int) -> tuple[Response, int] | Response:
    """Get all match point entries for a player.

    Args:
        player_id: ID of the player.

    Returns:
        JSON response with player info and match entries.
    """
    current_league = get_current_league()
    league_id = current_league.id if current_league else None

    try:
        result = fantasy_service.get_player_match_points(player_id, league_id)
        return jsonify(result)
    except NotFoundError as e:
        return error_response(e.message, e.status_code)


@api_bp.route('/fantasy/points/delete/<int:entry_id>', methods=['DELETE'])
@admin_required
def delete_match_points(entry_id: int) -> tuple[Response, int] | Response:
    """Delete a specific match point entry.

    Args:
        entry_id: ID of the entry to delete.

    Returns:
        JSON response with new total points.
    """
    try:
        result = fantasy_service.delete_match_points(entry_id)
        return jsonify(result)
    except NotFoundError as e:
        return error_response(e.message, e.status_code)


# ==================== FANTASY AWARDS ====================

@api_bp.route('/fantasy/award', methods=['POST'])
@admin_required
def set_fantasy_award() -> tuple[Response, int] | Response:
    """Set a fantasy award (MVP, Orange Cap, Purple Cap).

    Returns:
        JSON response with award details.
    """
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected')

    data = request.get_json()
    award_type = data.get('award_type')
    player_id = data.get('player_id')

    try:
        result = fantasy_service.set_award(
            award_type=award_type,
            league_id=current_league.id,
            player_id=player_id
        )
        return jsonify(result)
    except ValidationError as e:
        return error_response(e.message, e.status_code)


@api_bp.route('/fantasy/awards', methods=['GET'])
def get_fantasy_awards() -> tuple[Response, int] | Response:
    """Get all fantasy awards for current league.

    Returns:
        JSON response with awards mapping.
    """
    current_league = get_current_league()
    if not current_league:
        return jsonify({'success': True, 'awards': {}})

    result = fantasy_service.get_awards(current_league.id)
    return jsonify(result)


@api_bp.route('/fantasy/players', methods=['GET'])
def get_fantasy_players() -> tuple[Response, int] | Response:
    """Get all sold players with fantasy points.

    Returns:
        JSON response with list of sold players.
    """
    current_league = get_current_league()
    if not current_league:
        return jsonify({'success': True, 'players': []})

    players = Player.query.filter_by(
        league_id=current_league.id,
        status='sold',
        is_deleted=False
    ).all()

    return jsonify({
        'success': True,
        'players': [{
            'id': p.id,
            'name': p.name,
            'position': p.position,
            'team_id': p.team_id,
            'team_name': p.team.name if p.team else None,
            'fantasy_points': p.fantasy_points
        } for p in players]
    })


# ==================== DATA FETCHING ====================

@api_bp.route('/fantasy/fetch-awards', methods=['POST'])
@admin_required
def fetch_and_update_awards() -> tuple[Response, int] | Response:
    """Fetch Orange Cap, Purple Cap, and MVP from WPL and update awards.

    Returns:
        JSON response with fetch results.
    """
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected')

    try:
        result = fantasy_service.fetch_and_update_awards(current_league.id)
        return jsonify(result)
    except ValidationError as e:
        return error_response(e.message, e.status_code)


@api_bp.route('/fantasy/fetch-match-points', methods=['POST'])
@admin_required
def fetch_match_fantasy_points() -> tuple[Response, int] | Response:
    """Fetch all match scorecards and calculate fantasy points.

    Returns:
        JSON response with update summary.
    """
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected')

    try:
        result = fantasy_service.fetch_match_fantasy_points(current_league.id)
        return jsonify(result)
    except ValidationError as e:
        return error_response(e.message, e.status_code)
