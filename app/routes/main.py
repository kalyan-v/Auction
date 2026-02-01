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

from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from flask import (
    current_app, jsonify, redirect, render_template, request, session, url_for
)
from sqlalchemy import text

from sqlalchemy.orm import joinedload

from app import db
from app.enums import AwardType
from app.models import FantasyAward, League, Player, Team
from app.routes import main_bp
from app.utils import is_admin


def get_current_league() -> Optional[League]:
    """Get the currently selected league from session."""
    league_id = session.get('current_league_id')
    if league_id:
        league = League.query.filter_by(id=league_id, is_deleted=False).first()
        if league:
            return league
    # Default to first non-deleted league
    league = League.query.filter_by(is_deleted=False).first()
    if league:
        session['current_league_id'] = league.id
    return league


@main_bp.route('/')
def index():
    """Home page - redirects to Fantasy Points."""
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
def switch_league(league_id: int):
    """Switch to a different league."""
    league = League.query.filter_by(id=league_id, is_deleted=False).first()
    if league:
        session['current_league_id'] = league.id

    # SECURITY: Validate referrer to prevent open redirect
    referrer = request.referrer
    if referrer and is_safe_redirect_url(referrer):
        return redirect(referrer)
    return redirect(url_for('main.fantasy'))


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page with rate limiting protection."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if (username == current_app.config['ADMIN_USERNAME'] and
                password == current_app.config['ADMIN_PASSWORD']):
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
def logout():
    """Logout admin and redirect safely."""
    session.pop('is_admin', None)
    session.pop('current_league_id', None)

    # SECURITY: Validate referrer for redirect
    referrer = request.referrer
    if referrer and is_safe_redirect_url(referrer):
        return redirect(referrer)
    return redirect(url_for('main.index'))


@main_bp.route('/health')
def health_check():
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
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 503


@main_bp.route('/setup')
def setup():
    """Setup page for adding teams and players - view only if not admin."""
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
def squads():
    """View all team squads with players and budgets."""
    current_league = get_current_league()
    all_leagues = League.query.filter_by(is_deleted=False).all()

    if current_league:
        teams = Team.query.filter_by(
            league_id=current_league.id, is_deleted=False
        ).all()
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
def fantasy():
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
            league_id=current_league.id, status='sold', is_deleted=False
        ).all()

        # Get fantasy awards for this league (with eager loading for player)
        mvp = FantasyAward.query.options(
            joinedload(FantasyAward.player)
        ).filter_by(
            award_type=AwardType.MVP.value, league_id=current_league.id
        ).first()

        orange_cap = FantasyAward.query.options(
            joinedload(FantasyAward.player)
        ).filter_by(
            award_type=AwardType.ORANGE_CAP.value, league_id=current_league.id
        ).first()

        purple_cap = FantasyAward.query.options(
            joinedload(FantasyAward.player)
        ).filter_by(
            award_type=AwardType.PURPLE_CAP.value, league_id=current_league.id
        ).first()
    else:
        teams = []
        all_players = []
        mvp = orange_cap = purple_cap = None

    return render_template(
        'fantasy.html',
        teams=teams,
        all_players=all_players,
        mvp=mvp,
        orange_cap=orange_cap,
        purple_cap=purple_cap,
        admin_mode=is_admin(),
        current_league=current_league,
        all_leagues=all_leagues
    )
