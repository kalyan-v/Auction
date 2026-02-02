"""
Cricket data API endpoints.

Handles WPL website scraping for stats, points table, and match data.
Uses the pluggable scraper architecture for league support.
"""

from urllib.parse import urlparse

from flask import Response, jsonify, request

from app.logger import get_logger
from app.routes import api_bp
from app.scrapers import get_scraper, ScraperType
from app.scrapers.base import BaseScraper
from app.utils import error_response

logger = get_logger(__name__)

# Trusted domains for match URL validation (SSRF prevention)
TRUSTED_MATCH_DOMAINS = {
    'www.wplt20.com',
    'wplt20.com',
}


def _validate_match_url(url: str) -> bool:
    """Validate that a match URL is from a trusted WPL domain.

    SECURITY: Prevents SSRF attacks by only allowing URLs from trusted domains.

    Args:
        url: URL to validate.

    Returns:
        True if URL is from a trusted domain, False otherwise.
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.strip())
        # Must be HTTPS and from trusted domain
        return parsed.scheme == 'https' and parsed.netloc in TRUSTED_MATCH_DOMAINS
    except Exception:
        return False


def _get_current_scraper() -> BaseScraper:
    """Get the scraper for the current league context.

    In the future, this could be determined by session/request context
    to support multiple leagues simultaneously.

    Returns:
        Scraper instance for the current league.
    """
    # For now, always use WPL. Later this could be:
    # league_type = session.get('league_type', ScraperType.WPL)
    return get_scraper(ScraperType.WPL)


# ==================== WPL STATISTICS ====================

@api_bp.route('/cricket/stats/orange-cap', methods=['GET'])
def get_orange_cap_stats() -> tuple[Response, int] | Response:
    """Fetch Orange Cap (most runs) statistics.

    Returns:
        JSON response with Orange Cap leader and all players.
    """
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
        logger.error(f"Error fetching cricket data: {e}", exc_info=True)
        return error_response('Failed to fetch cricket data', 500)


@api_bp.route('/cricket/stats/purple-cap', methods=['GET'])
def get_purple_cap_stats() -> tuple[Response, int] | Response:
    """Fetch Purple Cap (most wickets) statistics.

    Returns:
        JSON response with Purple Cap leader and all players.
    """
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
        logger.error(f"Error fetching cricket data: {e}", exc_info=True)
        return error_response('Failed to fetch cricket data', 500)


@api_bp.route('/cricket/stats/mvp', methods=['GET'])
def get_mvp_stats() -> tuple[Response, int] | Response:
    """Fetch MVP (most valuable player) statistics.

    Returns:
        JSON response with MVP leader and all players.
    """
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
        logger.error(f"Error fetching cricket data: {e}", exc_info=True)
        return error_response('Failed to fetch cricket data', 500)


@api_bp.route('/cricket/stats/<stat_type>', methods=['GET'])
def get_cricket_stats(stat_type: str) -> tuple[Response, int] | Response:
    """Fetch cricket statistics from WPL website.

    Args:
        stat_type: Type of stat (most-runs, most-wickets, mvp, most-sixes, etc.)

    Returns:
        JSON response with requested statistics.
    """
    try:
        with _get_current_scraper() as scraper:
            # WPL scraper has a get_stats method for generic stat types
            if hasattr(scraper, 'get_stats'):
                result = scraper.get_stats(stat_type)
                return jsonify(result.to_dict())
            return error_response(f"Stat type '{stat_type}' not supported", 400)
    except Exception as e:
        logger.error(f"Error fetching cricket data: {e}", exc_info=True)
        return error_response('Failed to fetch cricket data', 500)


# ==================== POINTS TABLE ====================

@api_bp.route('/cricket/points-table', methods=['GET'])
def get_points_table() -> tuple[Response, int] | Response:
    """Fetch league points table.

    Returns:
        JSON response with team standings.
    """
    try:
        with _get_current_scraper() as scraper:
            result = scraper.get_points_table()
            return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching cricket data: {e}", exc_info=True)
        return error_response('Failed to fetch cricket data', 500)


# ==================== MATCH DATA ====================

@api_bp.route('/cricket/matches', methods=['GET'])
def get_matches() -> tuple[Response, int] | Response:
    """Get all completed match URLs.

    Returns:
        JSON response with list of match URLs.
    """
    try:
        with _get_current_scraper() as scraper:
            return jsonify(scraper.get_all_match_urls())
    except Exception as e:
        logger.error(f"Error fetching cricket data: {e}", exc_info=True)
        return error_response('Failed to fetch cricket data', 500)


@api_bp.route('/cricket/match/scorecard', methods=['POST'])
def get_match_scorecard_data() -> tuple[Response, int] | Response:
    """Get detailed scorecard for a specific match.

    Returns:
        JSON response with match scorecard data.
    """
    data = request.get_json()
    match_url = data.get('url') if data else None

    if not match_url:
        return error_response('Match URL required')

    # SECURITY: Validate URL is from trusted WPL domain (SSRF prevention)
    if not _validate_match_url(match_url):
        return error_response('Invalid match URL - must be from wplt20.com')

    try:
        with _get_current_scraper() as scraper:
            result = scraper.scrape_match_scorecard(match_url)
            return jsonify(result.to_dict())
    except Exception as e:
        logger.error(f"Error fetching cricket data: {e}", exc_info=True)
        return error_response('Failed to fetch cricket data', 500)
