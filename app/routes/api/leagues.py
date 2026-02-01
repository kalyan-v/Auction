"""
League management API endpoints.

Handles CRUD operations for leagues with proper input validation.
"""

import re

from flask import jsonify, request

from app import db
from app.models import League
from app.routes import api_bp
from app.routes.main import get_current_league
from app.utils import admin_required, error_response, is_admin, validate_positive_int


# Validation constants
MAX_LEAGUE_NAME_LENGTH = 50
MAX_DISPLAY_NAME_LENGTH = 100
LEAGUE_NAME_PATTERN = re.compile(r'^[\w\s\-]+$')


def validate_league_name(name: str) -> str | None:
    """Validate league name and return error message if invalid."""
    if not name:
        return 'League name is required'
    name = name.strip()
    if len(name) > MAX_LEAGUE_NAME_LENGTH:
        return f'League name must be {MAX_LEAGUE_NAME_LENGTH} characters or less'
    if not LEAGUE_NAME_PATTERN.match(name):
        return 'League name can only contain letters, numbers, spaces, underscores, and hyphens'
    return None


@api_bp.route('/leagues', methods=['GET', 'POST'])
def manage_leagues():
    """Get all leagues or create a new league."""
    if request.method == 'POST':
        if not is_admin():
            return error_response('Admin login required', 403)

        data = request.get_json()
        if not data:
            return error_response('Request body is required')

        # Validate league name
        name = data.get('name', '').strip()
        name_error = validate_league_name(name)
        if name_error:
            return error_response(name_error)

        # Check for duplicate league name
        existing = League.query.filter_by(name=name, is_deleted=False).first()
        if existing:
            return error_response('A league with this name already exists')

        # Validate display_name
        display_name = data.get('display_name', name).strip()
        if len(display_name) > MAX_DISPLAY_NAME_LENGTH:
            return error_response(f'Display name must be {MAX_DISPLAY_NAME_LENGTH} characters or less')

        # Validate numeric fields
        default_purse = data.get('default_purse', 500000000)
        try:
            default_purse = float(default_purse)
            if default_purse <= 0:
                return error_response('Default purse must be positive')
        except (TypeError, ValueError):
            return error_response('Invalid default purse value')

        max_squad, max_error = validate_positive_int(data.get('max_squad_size', 20), 'max_squad_size')
        if max_error:
            return error_response(max_error)

        min_squad, min_error = validate_positive_int(data.get('min_squad_size', 16), 'min_squad_size')
        if min_error:
            return error_response(min_error)

        if min_squad > max_squad:
            return error_response('Minimum squad size cannot be greater than maximum')

        league = League(
            name=name,
            display_name=display_name,
            default_purse=default_purse,
            max_squad_size=max_squad,
            min_squad_size=min_squad
        )
        db.session.add(league)
        db.session.commit()
        return jsonify({'success': True, 'league_id': league.id})

    leagues = League.query.filter_by(is_deleted=False).all()
    return jsonify([{
        'id': l.id,
        'name': l.name,
        'display_name': l.display_name,
        'default_purse': l.default_purse,
        'max_squad_size': l.max_squad_size,
        'min_squad_size': l.min_squad_size
    } for l in leagues])


@api_bp.route('/leagues/<int:league_id>', methods=['PUT', 'DELETE'])
def update_league(league_id: int):
    """Update or soft-delete a league with validation."""
    if not is_admin():
        return error_response('Admin login required', 403)

    league = League.query.get(league_id)
    if not league:
        return error_response('League not found', 404)

    if request.method == 'DELETE':
        # Soft delete
        league.is_deleted = True
        db.session.commit()
        return jsonify({'success': True})

    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    # Validate name if provided
    if 'name' in data:
        name = data['name'].strip()
        name_error = validate_league_name(name)
        if name_error:
            return error_response(name_error)
        # Check for duplicate (excluding current league)
        existing = League.query.filter(
            League.name == name,
            League.is_deleted == False,
            League.id != league_id
        ).first()
        if existing:
            return error_response('A league with this name already exists')
        league.name = name

    # Validate display_name if provided
    if 'display_name' in data:
        display_name = data['display_name'].strip()
        if len(display_name) > MAX_DISPLAY_NAME_LENGTH:
            return error_response(f'Display name must be {MAX_DISPLAY_NAME_LENGTH} characters or less')
        league.display_name = display_name

    # Validate numeric fields if provided
    if 'default_purse' in data:
        try:
            default_purse = float(data['default_purse'])
            if default_purse <= 0:
                return error_response('Default purse must be positive')
            league.default_purse = default_purse
        except (TypeError, ValueError):
            return error_response('Invalid default purse value')

    if 'max_squad_size' in data:
        max_squad, max_error = validate_positive_int(data['max_squad_size'], 'max_squad_size')
        if max_error:
            return error_response(max_error)
        league.max_squad_size = max_squad

    if 'min_squad_size' in data:
        min_squad, min_error = validate_positive_int(data['min_squad_size'], 'min_squad_size')
        if min_error:
            return error_response(min_error)
        league.min_squad_size = min_squad

    # Cross-validate squad sizes
    if league.min_squad_size > league.max_squad_size:
        return error_response('Minimum squad size cannot be greater than maximum')

    db.session.commit()
    return jsonify({'success': True})
