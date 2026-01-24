"""
League management API endpoints.

Handles CRUD operations for leagues.
"""

from flask import jsonify, request

from app import db
from app.models import League
from app.routes import api_bp
from app.routes.main import get_current_league
from app.utils import admin_required, error_response, is_admin


@api_bp.route('/leagues', methods=['GET', 'POST'])
def manage_leagues():
    """Get all leagues or create a new league."""
    if request.method == 'POST':
        if not is_admin():
            return error_response('Admin login required', 403)

        data = request.get_json()
        if not data or 'name' not in data:
            return error_response('League name is required')

        league = League(
            name=data['name'],
            display_name=data.get('display_name', data['name']),
            default_purse=data.get('default_purse', 500000000),
            max_squad_size=data.get('max_squad_size', 20),
            min_squad_size=data.get('min_squad_size', 16)
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
    """Update or soft-delete a league."""
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
    league.name = data.get('name', league.name)
    league.display_name = data.get('display_name', league.display_name)
    league.default_purse = data.get('default_purse', league.default_purse)
    league.max_squad_size = data.get('max_squad_size', league.max_squad_size)
    league.min_squad_size = data.get('min_squad_size', league.min_squad_size)
    db.session.commit()
    return jsonify({'success': True})
