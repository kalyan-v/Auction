"""
League management API endpoints.

Handles CRUD operations for leagues by delegating to LeagueService.
"""

from flask import Response, jsonify, request

from app.routes import api_bp
from app.services.base import NotFoundError, ValidationError
from app.services.league_service import league_service
from app.utils import error_response, is_admin, validate_positive_int


@api_bp.route('/leagues', methods=['GET', 'POST'])
def manage_leagues() -> tuple[Response, int] | Response:
    """Get all leagues or create a new league.

    Returns:
        JSON response with leagues list or creation result.
    """
    if request.method == 'POST':
        if not is_admin():
            return error_response('Admin login required', 403)

        data = request.get_json()
        if not data:
            return error_response('Request body is required')

        # Parse and validate numeric fields before passing to service
        default_purse = data.get('default_purse', 500000000)
        try:
            default_purse = float(default_purse)
        except (TypeError, ValueError):
            return error_response('Invalid default purse value')

        max_squad, max_error = validate_positive_int(
            data.get('max_squad_size', 20), 'max_squad_size'
        )
        if max_error:
            return error_response(max_error)

        min_squad, min_error = validate_positive_int(
            data.get('min_squad_size', 16), 'min_squad_size'
        )
        if min_error:
            return error_response(min_error)

        try:
            result = league_service.create_league(
                name=data.get('name', ''),
                display_name=data.get('display_name'),
                default_purse=default_purse,
                max_squad_size=max_squad,
                min_squad_size=min_squad
            )
            return jsonify(result)
        except ValidationError as e:
            return error_response(e.message, e.status_code)

    # GET request - return all leagues
    leagues = league_service.get_leagues()
    return jsonify(leagues)


@api_bp.route('/leagues/<int:league_id>', methods=['PUT', 'DELETE'])
def update_league(league_id: int) -> tuple[Response, int] | Response:
    """Update or soft-delete a league.

    Args:
        league_id: ID of the league to update/delete.

    Returns:
        JSON response with success status.
    """
    if not is_admin():
        return error_response('Admin login required', 403)

    if request.method == 'DELETE':
        try:
            result = league_service.delete_league(league_id)
            return jsonify(result)
        except NotFoundError as e:
            return error_response(e.message, e.status_code)

    # PUT request - update league
    data = request.get_json()
    if not data:
        return error_response('Request body is required')

    # Parse optional numeric fields
    default_purse = None
    if 'default_purse' in data:
        try:
            default_purse = float(data['default_purse'])
        except (TypeError, ValueError):
            return error_response('Invalid default purse value')

    max_squad_size = None
    if 'max_squad_size' in data:
        max_squad_size, max_error = validate_positive_int(
            data['max_squad_size'], 'max_squad_size'
        )
        if max_error:
            return error_response(max_error)

    min_squad_size = None
    if 'min_squad_size' in data:
        min_squad_size, min_error = validate_positive_int(
            data['min_squad_size'], 'min_squad_size'
        )
        if min_error:
            return error_response(min_error)

    try:
        result = league_service.update_league(
            league_id=league_id,
            name=data.get('name'),
            display_name=data.get('display_name'),
            default_purse=default_purse,
            max_squad_size=max_squad_size,
            min_squad_size=min_squad_size
        )
        return jsonify(result)
    except (ValidationError, NotFoundError) as e:
        return error_response(e.message, e.status_code)
