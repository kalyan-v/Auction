"""
Main routes for the WPL Auction application.

Handles:
- Home page
- Login/logout
- Setup page
- Squads page
- Fantasy page
- League switching
- Health check
"""

from datetime import datetime, timezone
from typing import Optional, Union
from urllib.parse import urlparse
import json

from flask import (
    Response, current_app, jsonify, redirect, render_template, request, session, url_for
)
from werkzeug.wrappers import Response as WerkzeugResponse
from sqlalchemy import text

from sqlalchemy.orm import joinedload

from app import db
from app.enums import AwardType, PlayerStatus
from app.extensions import limiter
from app.models import FantasyAward, League, Player, Team
from app.logger import get_logger
from app.routes import main_bp
from app.auth import verify_password
from app.utils import is_admin

logger = get_logger(__name__)


def get_current_league() -> Optional[League]:
    """Get the currently selected league.

    For admins: uses session-based league selection.
    For non-admins: always returns the admin-selected active league.

    Returns:
        The current League instance, or None if no leagues exist.
    """
    if is_admin():
        # Admins can freely switch between leagues via session
        league_id = session.get('current_league_id')
        if league_id:
            league = League.query.filter_by(id=league_id, is_deleted=False).first()
            if league:
                return league
        # No session preference — default to the globally active league
        league = League.query.filter_by(is_active=True, is_deleted=False).first()
        if not league:
            league = League.query.filter_by(is_deleted=False).first()
        if league:
            session['current_league_id'] = league.id
        return league
    else:
        # Non-admins always see the admin-selected active league
        league = League.query.filter_by(is_active=True, is_deleted=False).first()
        if league:
            return league
        # Fallback to first league if none marked active
        return League.query.filter_by(is_deleted=False).first()


@main_bp.route('/')
def index() -> WerkzeugResponse:
    """Home page - redirects to Fantasy."""
    return redirect(url_for('main.fantasy'))


def is_safe_redirect_url(url: str) -> bool:
    """Check if a redirect URL is safe (same origin).

    Prevents open redirect vulnerabilities by validating the URL
    points to the same host.
    """
    if not url:
        return False
    parsed = urlparse(url)
    # Allow relative URLs (no netloc) or same-host URLs
    return parsed.netloc == '' or parsed.netloc == request.host


@main_bp.route('/switch-league/<int:league_id>')
def switch_league(league_id: int) -> WerkzeugResponse:
    """Switch to a different league.

    For admins: also sets this league as the globally active league
    so non-admin users will see it across all tabs.
    """
    league = League.query.filter_by(id=league_id, is_deleted=False).first()
    if league:
        session['current_league_id'] = league.id
        if is_admin():
            try:
                # Set this league as the globally active one for non-admin users
                League.query.filter_by(is_active=True, is_deleted=False).update({'is_active': False})
                league.is_active = True
                db.session.commit()
            except Exception:
                db.session.rollback()
                logger.error("Failed to switch active league to %s", league_id, exc_info=True)

    # SECURITY: Validate referrer to prevent open redirect
    referrer = request.referrer
    if referrer and is_safe_redirect_url(referrer):
        return redirect(referrer)
    return redirect(url_for('main.fantasy'))


@main_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def login() -> Union[str, WerkzeugResponse]:
    """Admin login page with rate limiting protection."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Check username
        if username != current_app.config['ADMIN_USERNAME']:
            return render_template('login.html', error='Invalid credentials')

        # Verify password - supports both hashed (production) and plaintext (dev)
        password_hash = current_app.config.get('ADMIN_PASSWORD_HASH')
        plaintext_password = current_app.config.get('ADMIN_PASSWORD')

        password_valid = False
        if password_hash:
            # Production: Use bcrypt verification
            password_valid = verify_password(password, password_hash)
        elif plaintext_password:
            # Development fallback: Direct comparison (not recommended for production)
            password_valid = (password == plaintext_password)

        if password_valid:
            session['is_admin'] = True
            session.permanent = True  # Use PERMANENT_SESSION_LIFETIME

            # SECURITY: Validate next URL to prevent open redirect
            next_url = request.args.get('next')
            if next_url and is_safe_redirect_url(next_url):
                return redirect(next_url)
            return redirect(url_for('main.setup'))
        else:
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')


@main_bp.route('/logout')
def logout() -> WerkzeugResponse:
    """Logout admin and redirect safely."""
    session.pop('is_admin', None)
    session.pop('current_league_id', None)

    # SECURITY: Validate referrer for redirect
    referrer = request.referrer
    if referrer and is_safe_redirect_url(referrer):
        return redirect(referrer)
    return redirect(url_for('main.index'))


@main_bp.route('/health')
def health_check() -> tuple[Response, int] | Response:
    """Health check endpoint for load balancers and orchestration.

    Returns:
        JSON with health status and database connectivity
    """
    try:
        # Test database connectivity
        db.session.execute(text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error("Health check failed: %s", e, exc_info=True)
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
        }), 503


@main_bp.route('/setup')
def setup() -> Union[str, WerkzeugResponse]:
    """Setup page for adding teams and players - admin only."""
    if not is_admin():
        return redirect(url_for('main.fantasy'))
    current_league = get_current_league()
    all_leagues = League.query.filter_by(is_deleted=False).all()

    if current_league:
        teams = Team.query.filter_by(
            league_id=current_league.id, is_deleted=False
        ).all()
        players = Player.query.filter_by(
            league_id=current_league.id, is_deleted=False
        ).all()
    else:
        teams = []
        players = []

    return render_template(
        'setup.html',
        teams=teams,
        players=players,
        admin_mode=is_admin(),
        current_league=current_league,
        all_leagues=all_leagues
    )


@main_bp.route('/squads')
def squads() -> str:
    """View all team squads with players and budgets."""
    current_league = get_current_league()
    all_leagues = League.query.filter_by(is_deleted=False).all()

    if current_league:
        teams = Team.query.filter_by(
            league_id=current_league.id, is_deleted=False
        ).options(joinedload(Team.players)).all()
    else:
        teams = []

    return render_template(
        'squads.html',
        teams=teams,
        admin_mode=is_admin(),
        current_league=current_league,
        all_leagues=all_leagues
    )


@main_bp.route('/fantasy')
def fantasy() -> str:
    """Fantasy points page for viewing and managing player points.

    Uses eager loading to prevent N+1 queries when iterating over teams.
    """
    current_league = get_current_league()
    all_leagues = League.query.filter_by(is_deleted=False).all()

    if current_league:
        # Use eager loading to fetch teams with their players in a single query
        # This prevents N+1 queries when the template iterates over team.players
        teams = Team.query.options(
            joinedload(Team.players)
        ).filter_by(
            league_id=current_league.id, is_deleted=False
        ).all()

        all_players = Player.query.filter_by(
            league_id=current_league.id, status=PlayerStatus.SOLD, is_deleted=False
        ).all()

        # Get fantasy awards for this league in a single query
        awards = FantasyAward.query.options(
            joinedload(FantasyAward.player)
        ).filter_by(
            league_id=current_league.id
        ).all()

        # Organize awards by type
        awards_by_type = {a.award_type: a for a in awards}
        mvp = awards_by_type.get(AwardType.MVP.value)
        orange_cap = awards_by_type.get(AwardType.ORANGE_CAP.value)
        purple_cap = awards_by_type.get(AwardType.PURPLE_CAP.value)

        # Parse leaderboard JSON for each award (top-5 from scraper)
        def _parse_leaderboard(award):
            if award and award.leaderboard_json:
                try:
                    return json.loads(award.leaderboard_json)
                except (json.JSONDecodeError, TypeError):
                    pass
            return []

        mvp_leaderboard = _parse_leaderboard(mvp)
        orange_leaderboard = _parse_leaderboard(orange_cap)
        purple_leaderboard = _parse_leaderboard(purple_cap)

        # Sort teams by total fantasy points (descending) for the leaderboard
        teams.sort(
            key=lambda t: sum(
                p.fantasy_points for p in t.players if p.status == PlayerStatus.SOLD
            ),
            reverse=True
        )
    else:
        teams = []
        all_players = []
        mvp = orange_cap = purple_cap = None
        mvp_leaderboard = orange_leaderboard = purple_leaderboard = []

    return render_template(
        'fantasy.html',
        teams=teams,
        all_players=all_players,
        total_sold_count=len(all_players) if all_players else 0,
        mvp=mvp,
        orange_cap=orange_cap,
        purple_cap=purple_cap,
        mvp_leaderboard=mvp_leaderboard,
        orange_leaderboard=orange_leaderboard,
        purple_leaderboard=purple_leaderboard,
        admin_mode=is_admin(),
        current_league=current_league,
        all_leagues=all_leagues
    )
