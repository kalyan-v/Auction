"""
Player management API endpoints.

Handles CRUD operations for players and player image management.
Business logic is delegated to PlayerService.
"""

import csv
import io

from flask import Response, jsonify, request, make_response

from app.logger import get_logger
from app.models import Player
from app.routes import api_bp
from app.routes.main import get_current_league
from app.services.player_service import player_service
from app.utils import (
    admin_required,
    create_safe_filename,
    error_response,
    is_admin,
    to_pacific,
    validate_url,
)

logger = get_logger(__name__)


# ==================== PLAYER CRUD ====================


@api_bp.route('/players/export', methods=['GET'])
def export_players_csv() -> Response:
    """Export all players for the current league as a CSV file.

    CSV columns: Player Name, Role, Original Team.

    Returns:
        CSV file download response.
    """
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected')

    players = Player.query.filter_by(
        league_id=current_league.id, is_deleted=False
    ).order_by(Player.auction_category, Player.original_team).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Player Name', 'Auction Category', 'Original Team'])
    for player in players:
        writer.writerow([
            player.name,
            player.auction_category or '',
            player.original_team or ''
        ])

    response = make_response(output.getvalue())
    safe_name = create_safe_filename(current_league.name)
    filename = f"{safe_name}_players.csv"
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@api_bp.route('/players', methods=['GET', 'POST'])
def manage_players() -> tuple[Response, int] | Response:
    """Get all players or create a new player.

    Returns:
        JSON response with players list or creation result.
    """
    current_league = get_current_league()

    if request.method == 'POST':
        if not is_admin():
            return error_response('Admin login required', 403)
        if not current_league:
            return error_response('No league selected. Create a league first.')

        data = request.get_json()
        if not data or 'name' not in data:
            return error_response('Player name is required')

        # Validate base_price if provided
        base_price = data.get('base_price', 100000)
        try:
            base_price = float(base_price)
        except (TypeError, ValueError):
            return error_response('Invalid base price value')

        result = player_service.create_player(
            name=data['name'],
            league_id=current_league.id,
            position=data.get('position', ''),
            country=data.get('country', 'Indian'),
            base_price=base_price,
            original_team=data.get('original_team', ''),
            auction_category=data.get('auction_category', '')
        )
        return jsonify(result)

    # GET request - return all players
    if current_league:
        players = player_service.get_players(current_league.id)
    else:
        players = []

    return jsonify(players)


@api_bp.route('/players/<int:player_id>', methods=['PUT', 'DELETE'])
def update_player(player_id: int) -> tuple[Response, int] | Response:
    """Update or soft-delete a player.

    Args:
        player_id: ID of the player to update/delete.

    Returns:
        JSON response with success status.
    """
    if not is_admin():
        return error_response('Admin login required', 403)

    # Verify player belongs to the admin's current league
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected. Create a league first.')

    player = Player.query.filter_by(id=player_id, is_deleted=False).first()
    if not player:
        return error_response('Player not found', 404)
    if player.league_id != current_league.id:
        return error_response('Player does not belong to the current league', 403)

    if request.method == 'DELETE':
        result = player_service.delete_player(player_id)
        return jsonify(result)

    # PUT request - update player
    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    # Validate base_price if provided
    base_price = None
    if 'base_price' in data:
        try:
            base_price = float(data['base_price'])
        except (TypeError, ValueError):
            return error_response('Invalid base price value')

    result = player_service.update_player(
        player_id=player_id,
        name=data.get('name'),
        position=data.get('position'),
        country=data.get('country'),
        base_price=base_price,
        original_team=data.get('original_team'),
        auction_category=data.get('auction_category')
    )
    return jsonify(result)


@api_bp.route('/players/<int:player_id>/release', methods=['POST'])
@admin_required
def release_player(player_id: int) -> tuple[Response, int] | Response:
    """Release a player from their team back to auction pool.

    Args:
        player_id: ID of the player to release.

    Returns:
        JSON response with release result.
    """
    result = player_service.release_player(player_id)
    return jsonify(result)


# ==================== PLAYER QUERIES ====================

@api_bp.route('/players/random', methods=['GET'])
def get_random_player() -> tuple[Response, int] | Response:
    """Get a random available player, optionally filtered by position.

    Returns:
        JSON response with random player data.
    """
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected')

    position = request.args.get('position', '')
    include_unsold = request.args.get('include_unsold', 'false') == 'true'
    auction_category = request.args.get('auction_category', '')

    player = player_service.get_random_player(
        league_id=current_league.id,
        position=position or None,
        include_unsold=include_unsold,
        auction_category=auction_category or None
    )

    if not player:
        position_text = f" for position '{position}'" if position else ""
        category_text = f" in category '{auction_category}'" if auction_category else ""
        return error_response(f'No available players{position_text}{category_text}')

    return jsonify({
        'success': True,
        'player': {
            'id': player.id,
            'name': player.name,
            'position': player.position,
            'base_price': player.base_price
        }
    })


@api_bp.route('/players/available', methods=['GET'])
def get_available_players() -> tuple[Response, int] | Response:
    """Get all available players for animation, optionally filtered by position.

    Returns:
        JSON response with list of available players.
    """
    current_league = get_current_league()
    if not current_league:
        return jsonify({'success': False, 'error': 'No league selected', 'players': []})

    position = request.args.get('position', '')
    include_unsold = request.args.get('include_unsold', 'false') == 'true'
    auction_category = request.args.get('auction_category', '')

    available_players = player_service.get_available_players(
        league_id=current_league.id,
        position=position or None,
        include_unsold=include_unsold,
        auction_category=auction_category or None
    )

    if not available_players:
        position_text = f" for position '{position}'" if position else ""
        category_text = f" in category '{auction_category}'" if auction_category else ""
        return jsonify({
            'success': False,
            'error': f'No available players{position_text}{category_text}',
            'players': []
        })

    return jsonify({
        'success': True,
        'players': [{
            'id': p.id,
            'name': p.name,
            'position': p.position,
            'base_price': p.base_price
        } for p in available_players]
    })


@api_bp.route('/players/<int:player_id>/bids', methods=['GET'])
def get_player_bids(player_id: int) -> tuple[Response, int] | Response:
    """Get bid history for a specific player.

    Args:
        player_id: ID of the player.

    Returns:
        JSON response with player info and bid history.
    """
    result = player_service.get_player_bids(player_id)

    # Format timestamps for display
    for bid in result['bids']:
        pacific_time = to_pacific(bid['timestamp'])
        bid['timestamp'] = pacific_time.strftime('%I:%M:%S %p') if pacific_time else 'N/A'

    return jsonify({'success': True, **result})


# ==================== PLAYER IMAGES ====================

@api_bp.route('/players/<int:player_id>/fetch-image', methods=['POST'])
@admin_required
def fetch_player_image(player_id: int) -> tuple[Response, int] | Response:
    """Fetch, download and save player image locally.

    Args:
        player_id: ID of the player.

    Returns:
        JSON response with image URL or error.
    """
    result = player_service.fetch_player_image(player_id)
    return jsonify(result)


@api_bp.route('/players/<int:player_id>/image', methods=['PUT'])
@admin_required
def update_player_image(player_id: int) -> tuple[Response, int] | Response:
    """Manually update player image URL.

    Args:
        player_id: ID of the player.

    Returns:
        JSON response with updated image URL.
    """
    data = request.get_json()
    image_url = data.get('image_url', '').strip() if data else ''

    # Validate URL (allow local paths and HTTP URLs)
    if image_url and not validate_url(image_url):
        return error_response('Invalid URL format. Use http://, https://, or /path')

    result = player_service.update_player_image(player_id, image_url)
    return jsonify(result)


@api_bp.route('/players/fetch-all-images', methods=['POST'])
@admin_required
def fetch_all_player_images() -> tuple[Response, int] | Response:
    """Fetch images for all players without images.

    Returns:
        JSON response with summary of images found/not found.
    """
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected')

    result = player_service.fetch_all_images(current_league.id)
    return jsonify(result)
