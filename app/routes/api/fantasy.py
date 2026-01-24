"""
Fantasy points API endpoints.

Handles fantasy points management, awards, and data fetching.
"""

from typing import Optional

from flask import jsonify, request

from app import db
from app.enums import AwardType
from app.logger import get_logger
from app.models import FantasyAward, FantasyPointEntry, Player
from app.routes import api_bp
from app.routes.main import get_current_league
from app.scrapers import get_scraper, ScraperType
from app.utils import admin_required, error_response, is_admin, normalize_player_name

logger = get_logger(__name__)


# ==================== FANTASY POINTS CRUD ====================

@api_bp.route('/fantasy/points', methods=['POST'])
@admin_required
def update_fantasy_points():
    """Update fantasy points for a player."""
    data = request.get_json()
    player_id = data.get('player_id')
    points = data.get('points', 0)

    player = Player.query.get(player_id)
    if not player:
        return error_response('Player not found', 404)

    player.fantasy_points = points
    db.session.commit()

    return jsonify({
        'success': True,
        'player_id': player_id,
        'points': points
    })


@api_bp.route('/fantasy/points/add', methods=['POST'])
@admin_required
def add_match_points():
    """Add fantasy points for a specific match."""
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected')

    data = request.get_json()
    player_id = data.get('player_id')
    match_number = data.get('match_number')
    points = data.get('points', 0)

    if not player_id or not match_number:
        return error_response('Player ID and match number required')

    player = Player.query.get(player_id)
    if not player:
        return error_response('Player not found', 404)

    # Check for existing entry
    existing = FantasyPointEntry.query.filter_by(
        player_id=player_id,
        match_number=match_number,
        league_id=current_league.id
    ).first()

    if existing:
        existing.points = points
    else:
        entry = FantasyPointEntry(
            player_id=player_id,
            match_number=match_number,
            points=points,
            league_id=current_league.id
        )
        db.session.add(entry)

    # Update total
    db.session.flush()
    total_points = db.session.query(
        db.func.sum(FantasyPointEntry.points)
    ).filter_by(
        player_id=player_id,
        league_id=current_league.id
    ).scalar() or 0
    player.fantasy_points = total_points

    db.session.commit()

    return jsonify({
        'success': True,
        'player_id': player_id,
        'match_number': match_number,
        'points': points,
        'total_points': total_points
    })


@api_bp.route('/fantasy/points/<int:player_id>', methods=['GET'])
def get_player_match_points(player_id: int):
    """Get all match point entries for a player."""
    current_league = get_current_league()

    player = Player.query.get(player_id)
    if not player:
        return error_response('Player not found', 404)

    query = FantasyPointEntry.query.filter_by(player_id=player_id)
    if current_league:
        query = query.filter_by(league_id=current_league.id)
    entries = query.order_by(FantasyPointEntry.match_number).all()

    return jsonify({
        'success': True,
        'player': {
            'id': player.id,
            'name': player.name,
            'team_name': player.team.name if player.team else None,
            'total_points': player.fantasy_points
        },
        'entries': [{
            'id': e.id,
            'match_number': e.match_number,
            'points': e.points
        } for e in entries]
    })


@api_bp.route('/fantasy/points/delete/<int:entry_id>', methods=['DELETE'])
@admin_required
def delete_match_points(entry_id: int):
    """Delete a specific match point entry."""
    entry = FantasyPointEntry.query.get(entry_id)
    if not entry:
        return error_response('Entry not found', 404)

    player_id = entry.player_id
    league_id = entry.league_id
    db.session.delete(entry)

    db.session.flush()
    total_points = db.session.query(
        db.func.sum(FantasyPointEntry.points)
    ).filter_by(
        player_id=player_id,
        league_id=league_id
    ).scalar() or 0

    player = Player.query.get(player_id)
    player.fantasy_points = total_points

    db.session.commit()

    return jsonify({
        'success': True,
        'total_points': total_points
    })


# ==================== FANTASY AWARDS ====================

@api_bp.route('/fantasy/award', methods=['POST'])
@admin_required
def set_fantasy_award():
    """Set a fantasy award (MVP, Orange Cap, Purple Cap)."""
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected')

    data = request.get_json()
    award_type = data.get('award_type')
    player_id = data.get('player_id')

    # Validate award type using enum
    valid_types = [at.value for at in AwardType]
    if award_type not in valid_types:
        return error_response(f'Invalid award type. Valid: {valid_types}')

    award = FantasyAward.query.filter_by(
        award_type=award_type,
        league_id=current_league.id
    ).first()

    if not award:
        award = FantasyAward(award_type=award_type, league_id=current_league.id)
        db.session.add(award)

    award.player_id = player_id if player_id else None
    db.session.commit()

    player_name = None
    if player_id:
        player = Player.query.get(player_id)
        player_name = player.name if player else None

    return jsonify({
        'success': True,
        'award_type': award_type,
        'player_id': player_id,
        'player_name': player_name
    })


@api_bp.route('/fantasy/awards', methods=['GET'])
def get_fantasy_awards():
    """Get all fantasy awards for current league."""
    current_league = get_current_league()
    if not current_league:
        return jsonify({'success': True, 'awards': {}})

    awards = FantasyAward.query.filter_by(league_id=current_league.id).all()
    result = {}
    for award in awards:
        result[award.award_type] = {
            'player_id': award.player_id,
            'player_name': award.player.name if award.player else None
        }
    return jsonify({'success': True, 'awards': result})


@api_bp.route('/fantasy/players', methods=['GET'])
def get_fantasy_players():
    """Get all sold players with fantasy points."""
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


# ==================== PLAYER NAME MATCHING ====================

def find_player_by_name(name: str, league_id: int) -> Optional[Player]:
    """Find a player by name with fuzzy matching."""
    if not name:
        return None

    search_name = name.strip().lower()

    # Get scraper for name mappings
    scraper = get_scraper(ScraperType.WPL)
    mapped_name = scraper.name_mappings.get(search_name, search_name)

    # Try exact match with mapped name
    player = Player.query.filter(
        Player.league_id == league_id,
        Player.is_deleted == False,
        db.func.lower(Player.name) == mapped_name
    ).first()

    if player:
        return player

    # Try exact match with original name
    player = Player.query.filter(
        Player.league_id == league_id,
        Player.is_deleted == False,
        db.func.lower(Player.name) == search_name
    ).first()

    if player:
        return player

    # Fuzzy matching
    normalized_search = normalize_player_name(search_name)
    players = Player.query.filter(
        Player.league_id == league_id,
        Player.is_deleted == False
    ).all()

    for p in players:
        db_name_normalized = normalize_player_name(p.name)
        if db_name_normalized == normalized_search:
            return p
        if db_name_normalized in normalized_search or normalized_search in db_name_normalized:
            return p

    # Try first name matching
    name_parts = search_name.split()
    if len(name_parts) >= 2:
        first_name = name_parts[0]
        for p in players:
            db_name_parts = p.name.lower().split()
            if db_name_parts and db_name_parts[0] == first_name:
                for part in name_parts[1:]:
                    if any(part in db_part or db_part in part for db_part in db_name_parts[1:]):
                        return p

    return None


# ==================== DATA FETCHING ====================

@api_bp.route('/fantasy/fetch-awards', methods=['POST'])
@admin_required
def fetch_and_update_awards():
    """Fetch Orange Cap, Purple Cap, and MVP from WPL and update awards."""
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected')

    results = {
        'orange_cap': None,
        'purple_cap': None,
        'mvp': None,
        'errors': []
    }

    with get_scraper(ScraperType.WPL) as scraper:
        # Fetch Orange Cap
        orange_result = scraper.get_orange_cap()
        if orange_result.success and orange_result.leader:
            player_name = orange_result.leader.player_name
            player = find_player_by_name(player_name, current_league.id)
            if player:
                award = FantasyAward.query.filter_by(
                    award_type=AwardType.ORANGE_CAP.value,
                    league_id=current_league.id
                ).first()
                if not award:
                    award = FantasyAward(
                        award_type=AwardType.ORANGE_CAP.value,
                        league_id=current_league.id
                    )
                    db.session.add(award)
                award.player_id = player.id
                results['orange_cap'] = {
                    'player_name': player.name,
                    'player_id': player.id,
                    'runs': orange_result.leader.stats.get('runs', 0),
                    'wpl_name': player_name
                }
            else:
                results['errors'].append(f"Orange Cap: Player '{player_name}' not found")
        else:
            results['errors'].append(f"Orange Cap fetch failed: {orange_result.error}")

        # Fetch Purple Cap
        purple_result = scraper.get_purple_cap()
        if purple_result.success and purple_result.leader:
            player_name = purple_result.leader.player_name
            player = find_player_by_name(player_name, current_league.id)
            if player:
                award = FantasyAward.query.filter_by(
                    award_type=AwardType.PURPLE_CAP.value,
                    league_id=current_league.id
                ).first()
                if not award:
                    award = FantasyAward(
                        award_type=AwardType.PURPLE_CAP.value,
                        league_id=current_league.id
                    )
                    db.session.add(award)
                award.player_id = player.id
                results['purple_cap'] = {
                    'player_name': player.name,
                    'player_id': player.id,
                    'wickets': purple_result.leader.stats.get('wickets', 0),
                    'wpl_name': player_name
                }
            else:
                results['errors'].append(f"Purple Cap: Player '{player_name}' not found")
        else:
            results['errors'].append(f"Purple Cap fetch failed: {purple_result.error}")

        # Fetch MVP
        mvp_result = scraper.get_mvp()
        if mvp_result.success and mvp_result.leader:
            player_name = mvp_result.leader.player_name
            player = find_player_by_name(player_name, current_league.id)
            if player:
                award = FantasyAward.query.filter_by(
                    award_type=AwardType.MVP.value,
                    league_id=current_league.id
                ).first()
                if not award:
                    award = FantasyAward(
                        award_type=AwardType.MVP.value,
                        league_id=current_league.id
                    )
                    db.session.add(award)
                award.player_id = player.id
                results['mvp'] = {
                    'player_name': player.name,
                    'player_id': player.id,
                    'points': mvp_result.leader.stats.get('points', 0),
                    'wpl_name': player_name
                }
            else:
                results['errors'].append(f"MVP: Player '{player_name}' not found")
        else:
            results['errors'].append(f"MVP fetch failed: {mvp_result.error}")

    db.session.commit()

    return jsonify({
        'success': len(results['errors']) == 0,
        'results': results
    })


@api_bp.route('/fantasy/fetch-match-points', methods=['POST'])
@admin_required
def fetch_match_fantasy_points():
    """Fetch all match scorecards and calculate fantasy points."""
    current_league = get_current_league()
    if not current_league:
        return error_response('No league selected')

    with get_scraper(ScraperType.WPL) as scraper:
        result = scraper.scrape_all_matches()

    if not result.get('success'):
        return jsonify(result)

    all_player_stats = result.get('player_stats', {})
    matches_processed = result.get('matches_processed', [])

    updated_players = []
    not_found_players = []

    for wpl_name, data in all_player_stats.items():
        total_fantasy_points = data.get('total_fantasy_points', 0)
        matches_played = data.get('matches_played', 0)

        player = find_player_by_name(wpl_name, current_league.id)

        if player:
            # Get existing game_ids to avoid duplicates (game_id is the reliable unique key)
            existing_entries = FantasyPointEntry.query.filter_by(
                player_id=player.id,
                league_id=current_league.id
            ).all()
            existing_game_ids = {e.game_id for e in existing_entries if e.game_id}

            new_entries_added = 0
            for match in data.get('matches', []):
                game_id = match.get('game_id', '')

                # Skip if we already have this match (by game_id)
                if game_id and game_id in existing_game_ids:
                    continue

                match_num_str = match.get('match', '')
                if isinstance(match_num_str, str):
                    match_num_str = match_num_str.replace('Match ', '').strip()
                try:
                    match_number = int(match_num_str)
                except (ValueError, TypeError):
                    continue

                points = match.get('fantasy_points', 0)

                entry = FantasyPointEntry(
                    player_id=player.id,
                    match_number=match_number,
                    game_id=game_id,
                    points=points,
                    league_id=current_league.id
                )
                db.session.add(entry)
                existing_game_ids.add(game_id)  # Track newly added game_ids
                new_entries_added += 1

            # Recalculate total
            db.session.flush()
            total_from_entries = db.session.query(
                db.func.sum(FantasyPointEntry.points)
            ).filter_by(
                player_id=player.id,
                league_id=current_league.id
            ).scalar() or 0
            player.fantasy_points = total_from_entries

            updated_players.append({
                'name': player.name,
                'wpl_name': wpl_name,
                'total_points': total_from_entries,
                'matches': matches_played,
                'new_matches_added': new_entries_added,
                'total_runs': data.get('total_runs', 0),
                'total_wickets': data.get('total_wickets', 0),
            })
        else:
            not_found_players.append({
                'wpl_name': wpl_name,
                'total_points': total_fantasy_points,
                'matches': matches_played,
            })

    db.session.commit()

    return jsonify({
        'success': True,
        'matches_scraped': len(matches_processed),
        'players_updated': len(updated_players),
        'players_not_found': len(not_found_players),
        'updated': updated_players,
        'not_found': not_found_players
    })
