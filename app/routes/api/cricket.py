"""
Cricket data API endpoints.

Handles WPL website scraping for stats, points table, and match data.
Uses the pluggable scraper architecture for league support.
"""

from flask import jsonify, request

from app.routes import api_bp
from app.scrapers import get_scraper, ScraperType
from app.utils import error_response


def _get_current_scraper():
    """
    Get the scraper for the current league context.

    In the future, this could be determined by session/request context
    to support multiple leagues simultaneously.
    """
    # For now, always use WPL. Later this could be:
    # league_type = session.get('league_type', ScraperType.WPL)
    return get_scraper(ScraperType.WPL)


# ==================== WPL STATISTICS ====================

@api_bp.route('/cricket/stats/orange-cap', methods=['GET'])
def get_orange_cap_stats():
    """Fetch Orange Cap (most runs) statistics."""
    try:
        with _get_current_scraper() as scraper:
            result = scraper.get_orange_cap()
            if result.success and result.leader:
                return jsonify({
                    'success': True,
                    'player_name': result.leader.player_name,
                    'player_id': result.leader.player_id,
                    'runs': result.leader.stats.get('runs', 0),
                    'matches': result.leader.matches_played,
                    'average': result.leader.stats.get('average', 0),
                    'strike_rate': result.leader.stats.get('strike_rate', 0),
                    'team': result.leader.team_short_name,
                    'all_players': [p.to_dict() for p in result.players],
                })
            return jsonify(result.to_dict())
    except Exception as e:
        return error_response(str(e), 500)


@api_bp.route('/cricket/stats/purple-cap', methods=['GET'])
def get_purple_cap_stats():
    """Fetch Purple Cap (most wickets) statistics."""
    try:
        with _get_current_scraper() as scraper:
            result = scraper.get_purple_cap()
            if result.success and result.leader:
                return jsonify({
                    'success': True,
                    'player_name': result.leader.player_name,
                    'player_id': result.leader.player_id,
                    'wickets': result.leader.stats.get('wickets', 0),
                    'matches': result.leader.matches_played,
                    'economy': result.leader.stats.get('economy', 0),
                    'average': result.leader.stats.get('average', 0),
                    'team': result.leader.team_short_name,
                    'all_players': [p.to_dict() for p in result.players],
                })
            return jsonify(result.to_dict())
    except Exception as e:
        return error_response(str(e), 500)


@api_bp.route('/cricket/stats/mvp', methods=['GET'])
def get_mvp_stats():
    """Fetch MVP (most valuable player) statistics."""
    try:
        with _get_current_scraper() as scraper:
            result = scraper.get_mvp()
            if result.success and result.leader:
                return jsonify({
                    'success': True,
                    'player_name': result.leader.player_name,
                    'player_id': result.leader.player_id,
                    'points': result.leader.stats.get('points', 0),
                    'matches': result.leader.matches_played,
                    'team': result.leader.team_short_name,
                    'all_players': [p.to_dict() for p in result.players],
                })
            return jsonify(result.to_dict())
    except Exception as e:
        return error_response(str(e), 500)


@api_bp.route('/cricket/stats/<stat_type>', methods=['GET'])
def get_cricket_stats(stat_type: str):
    """
    Fetch cricket statistics from WPL website.

    stat_type can be: most-runs, most-wickets, mvp, most-sixes, most-fours, etc.
    """
    try:
        with _get_current_scraper() as scraper:
            # WPL scraper has a get_stats method for generic stat types
            if hasattr(scraper, 'get_stats'):
                result = scraper.get_stats(stat_type)
                return jsonify(result.to_dict())
            return error_response(f"Stat type '{stat_type}' not supported", 400)
    except Exception as e:
        return error_response(str(e), 500)


# ==================== POINTS TABLE ====================

@api_bp.route('/cricket/points-table', methods=['GET'])
def get_points_table():
    """Fetch league points table."""
    try:
        with _get_current_scraper() as scraper:
            result = scraper.get_points_table()
            return jsonify(result)
    except Exception as e:
        return error_response(str(e), 500)


# ==================== MATCH DATA ====================

@api_bp.route('/cricket/matches', methods=['GET'])
def get_matches():
    """Get all completed match URLs."""
    try:
        with _get_current_scraper() as scraper:
            return jsonify(scraper.get_all_match_urls())
    except Exception as e:
        return error_response(str(e), 500)


@api_bp.route('/cricket/match/scorecard', methods=['POST'])
def get_match_scorecard_data():
    """Get detailed scorecard for a specific match."""
    data = request.get_json()
    match_url = data.get('url') if data else None

    if not match_url:
        return error_response('Match URL required')

    try:
        with _get_current_scraper() as scraper:
            result = scraper.scrape_match_scorecard(match_url)
            return jsonify(result.to_dict())
    except Exception as e:
        return error_response(str(e), 500)
