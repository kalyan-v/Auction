"""
Player management API endpoints.

Handles CRUD operations for players and player image management.
Includes transaction handling and locking for data integrity.
Uses SQLite-compatible application-level locks.
"""

import os
import random
from typing import Optional

import requests
from flask import current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app import db
from app.db_utils import PlayerLock, get_for_update
from app.constants import (
    DEFAULT_REQUEST_TIMEOUT,
    IMAGE_REQUEST_TIMEOUT,
    MIN_VALID_IMAGE_SIZE,
    WIKI_HEADERS,
    WIKI_REQUEST_TIMEOUT,
    WPL_IMAGE_URL_TEMPLATE,
    WPL_SERIES_ID,
)
from app.logger import get_logger
from app.models import AuctionState, Bid, Player
from app.player_data import WPL_PLAYER_IDS
from app.routes import api_bp
from app.routes.main import get_current_league
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

@api_bp.route('/players', methods=['GET', 'POST'])
def manage_players():
    """Get all players or create a new player."""
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
            if base_price < 0:
                return error_response('Base price cannot be negative')
        except (TypeError, ValueError):
            return error_response('Invalid base price value')

        player = Player(
            name=data['name'],
            position=data.get('position', ''),
            country=data.get('country', 'Indian'),
            base_price=base_price,
            original_team=data.get('original_team', ''),
            league_id=current_league.id
        )
        db.session.add(player)
        db.session.commit()
        return jsonify({'success': True, 'player_id': player.id})

    if current_league:
        players = Player.query.filter_by(
            league_id=current_league.id, is_deleted=False
        ).all()
    else:
        players = []

    return jsonify([{
        'id': p.id,
        'name': p.name,
        'position': p.position,
        'country': p.country,
        'base_price': p.base_price,
        'original_team': p.original_team,
        'status': p.status
    } for p in players])


@api_bp.route('/players/<int:player_id>', methods=['PUT', 'DELETE'])
def update_player(player_id: int):
    """Update or soft-delete a player."""
    if not is_admin():
        return error_response('Admin login required', 403)

    player = Player.query.get(player_id)
    if not player:
        return error_response('Player not found', 404)

    if request.method == 'DELETE':
        # Check if player is in active auction
        auction_state = AuctionState.query.first()
        if auction_state and auction_state.current_player_id == player_id:
            auction_state.current_player_id = None
            auction_state.is_active = False

        # Soft delete
        player.is_deleted = True
        db.session.commit()
        return jsonify({'success': True})

    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    # Validate base_price if provided
    if 'base_price' in data:
        try:
            base_price = float(data['base_price'])
            if base_price < 0:
                return error_response('Base price cannot be negative')
            player.base_price = base_price
        except (TypeError, ValueError):
            return error_response('Invalid base price value')

    player.name = data.get('name', player.name)
    player.position = data.get('position', player.position)
    player.country = data.get('country', player.country)
    player.original_team = data.get('original_team', player.original_team)
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/players/<int:player_id>/release', methods=['POST'])
@admin_required
def release_player(player_id: int):
    """Release a player from their team back to auction pool.

    Uses application-level locking for SQLite compatibility.
    """
    from app.models import Team

    try:
        with PlayerLock():
            player = get_for_update(Player, player_id)

            if not player:
                return error_response('Player not found', 404)

            if player.status != 'sold':
                db.session.rollback()
                return error_response('Player is not currently sold to a team')

            # Get team to refund budget
            if player.team_id:
                team = get_for_update(Team, player.team_id)

                if team:
                    team.budget += player.current_price

        player_name = player.name

        # Reset player to available status
        player.status = 'available'
        player.team_id = None
        player.current_price = player.base_price

        # Delete all bids for this player
        Bid.query.filter_by(player_id=player_id).delete()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{player_name} has been released back to auction'
        })

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error releasing player: {e}", exc_info=True)
        return error_response('Failed to release player', 500)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error releasing player: {e}", exc_info=True)
        return error_response('Failed to release player', 500)


# ==================== PLAYER QUERIES ====================

@api_bp.route('/players/random', methods=['GET'])
def get_random_player():
    """Get a random available player, optionally filtered by position."""
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected')

    position = request.args.get('position', '')
    include_unsold = request.args.get('include_unsold', 'false') == 'true'

    if include_unsold:
        query = Player.query.filter(
            Player.league_id == current_league.id,
            Player.is_deleted.is_(False),
            Player.status.in_(['available', 'unsold'])
        )
    else:
        query = Player.query.filter_by(
            league_id=current_league.id,
            is_deleted=False,
            status='available'
        )

    if position:
        query = query.filter_by(position=position)

    available_players = query.all()

    if not available_players:
        position_text = f" for position '{position}'" if position else ""
        return error_response(f'No available players{position_text}')

    player = random.choice(available_players)
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
def get_available_players():
    """Get all available players for animation, optionally filtered by position."""
    current_league = get_current_league()
    if not current_league:
        return jsonify({'success': False, 'error': 'No league selected', 'players': []})

    position = request.args.get('position', '')
    include_unsold = request.args.get('include_unsold', 'false') == 'true'

    if include_unsold:
        query = Player.query.filter(
            Player.league_id == current_league.id,
            Player.is_deleted.is_(False),
            Player.status.in_(['available', 'unsold'])
        )
    else:
        query = Player.query.filter_by(
            league_id=current_league.id,
            is_deleted=False,
            status='available'
        )

    if position:
        query = query.filter_by(position=position)

    available_players = query.all()

    if not available_players:
        position_text = f" for position '{position}'" if position else ""
        return jsonify({
            'success': False,
            'error': f'No available players{position_text}',
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
def get_player_bids(player_id: int):
    """Get bid history for a specific player."""
    player = Player.query.get(player_id)
    if not player:
        return error_response('Player not found', 404)

    bids = (
        Bid.query
        .filter_by(player_id=player_id)
        .options(joinedload(Bid.team))
        .order_by(Bid.amount.desc())
        .all()
    )

    def format_bid_timestamp(bid):
        """Safely format bid timestamp."""
        pacific_time = to_pacific(bid.timestamp)
        return pacific_time.strftime('%I:%M:%S %p') if pacific_time else 'N/A'

    return jsonify({
        'success': True,
        'player': {
            'id': player.id,
            'name': player.name,
            'position': player.position,
            'status': player.status,
            'final_price': player.current_price
        },
        'bids': [{
            'team_name': bid.team.name,
            'amount': bid.amount,
            'timestamp': format_bid_timestamp(bid)
        } for bid in bids]
    })


# ==================== PLAYER IMAGES ====================

def get_player_image_path() -> str:
    """Get the path to store player images."""
    return os.path.join(current_app.root_path, 'static', 'images', 'players')


def download_and_save_image(
    image_url: str,
    player_id: int,
    player_name: str
) -> Optional[str]:
    """Download image from URL and save locally with path traversal protection."""
    try:
        response = requests.get(
            image_url,
            headers=WIKI_HEADERS,
            timeout=IMAGE_REQUEST_TIMEOUT
        )
        if response.status_code != 200:
            return None

        # Validate content type is an image
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            logger.warning(f"Invalid content type for {player_name}: {content_type}")
            return None

        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024
        if len(response.content) > max_size:
            logger.warning(f"Image too large for {player_name}: {len(response.content)} bytes")
            return None

        # Ensure directory exists
        image_dir = get_player_image_path()
        os.makedirs(image_dir, exist_ok=True)

        # Create safe filename from player name
        safe_name = create_safe_filename(player_name)
        filename = f"{player_id}_{safe_name}.jpg"
        filepath = os.path.join(image_dir, filename)

        # SECURITY: Validate path stays within image directory (prevent path traversal)
        real_filepath = os.path.realpath(filepath)
        real_image_dir = os.path.realpath(image_dir)
        if not real_filepath.startswith(real_image_dir + os.sep):
            logger.error(f"Path traversal attempt detected: {filepath}")
            return None

        # Save image
        with open(filepath, 'wb') as f:
            f.write(response.content)

        # Return the URL path for the static file
        return f"/static/images/players/{filename}"

    except requests.RequestException as e:
        logger.error(f"Network error downloading image for {player_name}: {e}")
        return None
    except IOError as e:
        logger.error(f"File error saving image for {player_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading image for {player_name}: {e}", exc_info=True)
        return None


def search_and_download_player_image(
    player_id: int,
    player_name: str
) -> Optional[str]:
    """Search for player image and download it locally - tries WPL first.

    Includes path traversal protection and proper error handling.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    # Try WPL first (official source with high-quality headshots)
    wpl_player_id = WPL_PLAYER_IDS.get(player_name.strip())
    if wpl_player_id:
        try:
            image_url = WPL_IMAGE_URL_TEMPLATE.format(
                series_id=WPL_SERIES_ID,
                player_id=wpl_player_id
            )
            response = requests.get(
                image_url,
                headers=headers,
                timeout=IMAGE_REQUEST_TIMEOUT
            )
            if (response.status_code == 200 and
                    len(response.content) > MIN_VALID_IMAGE_SIZE):
                # Validate file size (max 5MB)
                max_size = 5 * 1024 * 1024
                if len(response.content) > max_size:
                    logger.warning(f"WPL image too large for {player_name}")
                    # Continue to Wikipedia fallback
                else:
                    # Ensure directory exists
                    image_dir = get_player_image_path()
                    os.makedirs(image_dir, exist_ok=True)

                    # Create safe filename
                    safe_name = create_safe_filename(player_name)
                    filename = f"{player_id}_{safe_name}.png"
                    filepath = os.path.join(image_dir, filename)

                    # SECURITY: Validate path stays within image directory
                    real_filepath = os.path.realpath(filepath)
                    real_image_dir = os.path.realpath(image_dir)
                    if not real_filepath.startswith(real_image_dir + os.sep):
                        logger.error(f"Path traversal attempt detected: {filepath}")
                        return None

                    with open(filepath, 'wb') as f:
                        f.write(response.content)

                    return f"/static/images/players/{filename}"

        except requests.RequestException as e:
            logger.error(f"WPL network error for {player_name}: {e}")
        except IOError as e:
            logger.error(f"WPL file error for {player_name}: {e}")
        except Exception as e:
            logger.error(f"WPL unexpected error for {player_name}: {e}", exc_info=True)

    # Fallback to Wikipedia for players not in WPL
    try:
        wiki_url = 'https://en.wikipedia.org/w/api.php'
        params = {
            'action': 'query',
            'titles': player_name,
            'prop': 'pageimages',
            'format': 'json',
            'pithumbsize': 200
        }
        response = requests.get(
            wiki_url,
            params=params,
            headers=WIKI_HEADERS,
            timeout=WIKI_REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            data = response.json()
            pages = data.get('query', {}).get('pages', {})
            for page_id, page_data in pages.items():
                if page_id != '-1':
                    thumbnail = page_data.get('thumbnail', {})
                    if thumbnail.get('source'):
                        local_path = download_and_save_image(
                            thumbnail['source'], player_id, player_name
                        )
                        if local_path:
                            return local_path

    except requests.RequestException as e:
        logger.error(f"Wikipedia network error for {player_name}: {e}")
    except Exception as e:
        logger.error(f"Wikipedia unexpected error for {player_name}: {e}", exc_info=True)

    return None


@api_bp.route('/players/<int:player_id>/fetch-image', methods=['POST'])
@admin_required
def fetch_player_image(player_id: int):
    """Fetch, download and save player image locally."""
    player = Player.query.get(player_id)
    if not player:
        return error_response('Player not found', 404)

    # Search and download image
    local_image_path = search_and_download_player_image(player.id, player.name)

    if local_image_path:
        player.image_url = local_image_path
        db.session.commit()
        return jsonify({
            'success': True,
            'image_url': local_image_path,
            'message': f'Image downloaded for {player.name}'
        })
    else:
        return error_response(
            f'No image found for {player.name}. Try setting manually.'
        )


@api_bp.route('/players/<int:player_id>/image', methods=['PUT'])
@admin_required
def update_player_image(player_id: int):
    """Manually update player image URL."""
    player = Player.query.get(player_id)
    if not player:
        return error_response('Player not found', 404)

    data = request.get_json()
    image_url = data.get('image_url', '').strip()

    # Validate URL (allow local paths and HTTP URLs)
    if image_url and not validate_url(image_url):
        return error_response('Invalid URL format. Use http://, https://, or /path')

    player.image_url = image_url if image_url else None
    db.session.commit()

    return jsonify({
        'success': True,
        'image_url': player.image_url,
        'message': 'Image URL updated'
    })


@api_bp.route('/players/fetch-all-images', methods=['POST'])
@admin_required
def fetch_all_player_images():
    """Fetch images for all players without images."""
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected')

    # Get players without images
    players = Player.query.filter(
        Player.league_id == current_league.id,
        Player.is_deleted.is_(False),
        Player.image_url.is_(None) | (Player.image_url == '')
    ).all()

    results = {'found': 0, 'not_found': 0, 'players': []}

    for player in players:
        local_image_path = search_and_download_player_image(player.id, player.name)

        if local_image_path:
            player.image_url = local_image_path
            results['found'] += 1
            results['players'].append({
                'name': player.name,
                'status': 'found',
                'image_url': local_image_path
            })
        else:
            results['not_found'] += 1
            results['players'].append({
                'name': player.name,
                'status': 'not_found'
            })

    db.session.commit()

    return jsonify({
        'success': True,
        'message': (
            f"Downloaded images for {results['found']} players, "
            f"{results['not_found']} not found"
        ),
        'results': results
    })
