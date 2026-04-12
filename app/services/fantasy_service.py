"""
Fantasy points service for managing fantasy league operations.

Encapsulates all business logic related to:
- Fantasy points management
- Fantasy awards (MVP, Orange Cap, Purple Cap)
- Player name matching
- External data fetching
"""

import json
from typing import Dict, List, Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import joinedload

from app import db
from app.constants import PLAYOFF_MATCH_NUMBERS, TEAM_COLORS
from app.enums import AwardType, PlayerStatus
from app.logger import get_logger
from app.models import FantasyAward, FantasyPointEntry, League, Player, Team
from app.scrapers import get_scraper, ScraperType
from app.services.base import BaseService, NotFoundError, ValidationError
from app.utils import normalize_player_name

logger = get_logger(__name__)


class FantasyService(BaseService):
    """Service for fantasy points and awards operations.

    Handles points management, awards, and data fetching from external sources.
    """

    def _get_scraper_type(self, league_id: int) -> ScraperType:
        """Resolve the scraper type from a league's league_type field.

        Args:
            league_id: ID of the league.

        Returns:
            ScraperType matching the league.

        Raises:
            ValidationError: If league not found or unsupported type.
        """
        league = db.session.get(League, league_id)
        if not league:
            raise NotFoundError(f"League {league_id} not found")
        try:
            return ScraperType(league.league_type)
        except ValueError:
            raise ValidationError(f"Unsupported league type: {league.league_type}")

    # ==================== FANTASY POINTS ====================

    def update_player_points(self, player_id: int, points: float) -> dict:
        """Update total fantasy points for a player.

        Args:
            player_id: ID of the player.
            points: New total points value.

        Returns:
            Dict with success status and updated values.

        Raises:
            NotFoundError: If player not found.
        """
        with self.transaction():
            player = db.session.get(Player, player_id)
            if not player:
                raise NotFoundError("Player not found")

            player.fantasy_points = points

            logger.info(f"Updated fantasy points for {player.name}: {points}")

            return {
                'success': True,
                'player_id': player_id,
                'points': points
            }

    def add_match_points(
        self,
        player_id: int,
        match_number: int,
        points: float,
        league_id: int,
        game_id: Optional[str] = None
    ) -> dict:
        """Add fantasy points for a specific match.

        Args:
            player_id: ID of the player.
            match_number: Match number.
            points: Points earned in the match.
            league_id: ID of the league.
            game_id: Optional unique game identifier.

        Returns:
            Dict with success status and total points.

        Raises:
            NotFoundError: If player not found.
        """
        with self.transaction():
            player = db.session.get(Player, player_id)
            if not player:
                raise NotFoundError("Player not found")

            # Check for existing entry with is_deleted filter
            # Use with_for_update() to prevent TOCTOU race when game_id is None
            # (SQL NULL != NULL bypasses the unique constraint)
            existing = FantasyPointEntry.query.filter_by(
                player_id=player_id,
                match_number=match_number,
                league_id=league_id,
                is_deleted=False
            ).with_for_update().first()

            if existing:
                existing.points = points
            else:
                entry = FantasyPointEntry(
                    player_id=player_id,
                    match_number=match_number,
                    points=points,
                    league_id=league_id,
                    game_id=game_id
                )
                db.session.add(entry)

            # Update total
            self.flush()
            total_points = self._calculate_total_points(player_id, league_id)
            player.fantasy_points = total_points

            return {
                'success': True,
                'player_id': player_id,
                'match_number': match_number,
                'points': points,
                'total_points': total_points
            }

    def delete_match_points(self, entry_id: int, league_id: Optional[int] = None) -> dict:
        """Soft delete a specific match point entry.

        Args:
            entry_id: ID of the entry to delete.
            league_id: Optional league ID for ownership validation.

        Returns:
            Dict with success status and new total.

        Raises:
            NotFoundError: If entry not found.
            ValidationError: If entry doesn't belong to the specified league.
        """
        with self.transaction():
            entry = db.session.get(FantasyPointEntry, entry_id)
            if not entry or entry.is_deleted:
                raise NotFoundError("Entry not found")

            if league_id is not None and entry.league_id != league_id:
                raise ValidationError("Entry does not belong to the current league")

            player_id = entry.player_id
            league_id = entry.league_id
            entry.is_deleted = True

            self.flush()
            total_points = self._calculate_total_points(player_id, league_id)

            player = db.session.get(Player, player_id)
            if player:
                player.fantasy_points = total_points

            return {
                'success': True,
                'total_points': total_points
            }

    def get_player_match_points(
        self,
        player_id: int,
        league_id: Optional[int] = None
    ) -> dict:
        """Get all match point entries for a player.

        Args:
            player_id: ID of the player.
            league_id: Optional league ID filter.

        Returns:
            Dict with player info and match entries.

        Raises:
            NotFoundError: If player not found.
        """
        player = db.session.get(Player, player_id)
        if not player:
            raise NotFoundError("Player not found")

        query = FantasyPointEntry.query.filter_by(player_id=player_id, is_deleted=False)
        if league_id:
            query = query.filter_by(league_id=league_id)
        entries = query.order_by(FantasyPointEntry.match_number).all()

        return {
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
        }

    def _calculate_total_points(self, player_id: int, league_id: int) -> float:
        """Calculate total fantasy points from active entries."""
        return db.session.query(
            db.func.sum(FantasyPointEntry.points)
        ).filter_by(
            player_id=player_id,
            league_id=league_id,
            is_deleted=False
        ).scalar() or 0

    # ==================== FANTASY AWARDS ====================

    def _get_or_create_award(self, award_type: str, league_id: int) -> 'FantasyAward':
        """Get existing award or create a new one (must be called within a transaction)."""
        award = FantasyAward.query.filter_by(
            award_type=award_type,
            league_id=league_id
        ).first()
        if not award:
            award = FantasyAward(award_type=award_type, league_id=league_id)
            db.session.add(award)
        return award

    def set_award(
        self,
        award_type: str,
        league_id: int,
        player_id: Optional[int] = None
    ) -> dict:
        """Set a fantasy award.

        Args:
            award_type: Type of award (mvp, orange_cap, purple_cap).
            league_id: ID of the league.
            player_id: ID of the player (optional, None to clear).

        Returns:
            Dict with success status.

        Raises:
            ValidationError: If award type is invalid.
        """
        valid_types = [at.value for at in AwardType]
        if award_type not in valid_types:
            raise ValidationError(f'Invalid award type. Valid: {valid_types}')

        with self.transaction():
            # Validate player BEFORE mutating the award
            player_name = None
            if player_id:
                player = db.session.get(Player, player_id)
                if not player or player.is_deleted:
                    raise ValidationError('Player not found or has been deleted')
                if player.league_id != league_id:
                    raise ValidationError('Player does not belong to the current league')
                player_name = player.name

            award = self._get_or_create_award(award_type, league_id)
            award.player_id = player_id if player_id else None

            logger.info(f"Set {award_type} award to {player_name}")

            return {
                'success': True,
                'award_type': award_type,
                'player_id': player_id,
                'player_name': player_name
            }

    def get_awards(self, league_id: int) -> dict:
        """Get all fantasy awards for a league.

        Args:
            league_id: ID of the league.

        Returns:
            Dict with awards information.
        """
        awards = FantasyAward.query.filter_by(league_id=league_id).all()
        result = {}
        for award in awards:
            player = award.player
            result[award.award_type] = {
                'player_id': award.player_id,
                'player_name': player.name if player and not player.is_deleted else None
            }
        return {'success': True, 'awards': result}

    def get_sold_players(self, league_id: int) -> list[dict]:
        """Get all sold players with fantasy points for a league.

        Args:
            league_id: ID of the league.

        Returns:
            List of player dictionaries with fantasy info.
        """
        players = Player.query.filter_by(
            league_id=league_id,
            status=PlayerStatus.SOLD,
            is_deleted=False
        ).options(joinedload(Player.team)).all()

        return [{
            'id': p.id,
            'name': p.name,
            'position': p.position,
            'team_id': p.team_id,
            'team_name': p.team.name if p.team else None,
            'fantasy_points': p.fantasy_points
        } for p in players]

    # ==================== CHART DATA ====================

    def get_team_points_by_match(self, league_id: int) -> dict:
        """Get cumulative fantasy points per team per match for charting.

        Args:
            league_id: ID of the league.

        Returns:
            Dict with success flag and list of team data with per-match cumulative points.
        """
        # Reverse map: high match numbers back to display labels
        playoff_labels = {v: k for k, v in PLAYOFF_MATCH_NUMBERS.items()}
        # Deduplicate (qualifier1 and qualifier 1 both map to 101)
        playoff_display = {
            100: 'E',
            101: 'Q1',
            102: 'Q2',
            200: 'F',
        }

        # Query: sum points per team per match_number
        rows = (
            db.session.query(
                Team.id,
                Team.name,
                FantasyPointEntry.match_number,
                sa_func.sum(FantasyPointEntry.points).label('total')
            )
            .join(Player, FantasyPointEntry.player_id == Player.id)
            .join(Team, Player.team_id == Team.id)
            .filter(
                FantasyPointEntry.league_id == league_id,
                FantasyPointEntry.is_deleted.is_(False),
                Player.status == PlayerStatus.SOLD,
                Player.is_deleted.is_(False),
                Team.is_deleted.is_(False),
            )
            .group_by(Team.id, Team.name, FantasyPointEntry.match_number)
            .order_by(Team.name, FantasyPointEntry.match_number)
            .all()
        )

        # Organize by team
        teams_data: Dict[int, dict] = {}
        for team_id, team_name, match_number, total in rows:
            if team_id not in teams_data:
                slug = team_name.lower().replace(' ', '-')
                teams_data[team_id] = {
                    'name': team_name,
                    'color': TEAM_COLORS.get(slug, '#667eea'),
                    'matches': []
                }
            label = playoff_display.get(match_number, f'M{match_number}')
            teams_data[team_id]['matches'].append({
                'match_number': match_number,
                'label': label,
                'points': round(float(total), 1)
            })

        # Compute cumulative totals
        result = []
        for team_id, tdata in teams_data.items():
            cumulative = 0
            data_points = []
            for m in tdata['matches']:
                cumulative += m['points']
                data_points.append({
                    'match': m['match_number'],
                    'label': m['label'],
                    'points': m['points'],
                    'cumulative': round(cumulative, 1)
                })
            result.append({
                'name': tdata['name'],
                'color': tdata['color'],
                'data': data_points
            })

        return {'success': True, 'teams': result}

    # ==================== PLAYER MATCHING ====================

    def find_player_by_name(
        self,
        name: str,
        league_id: int
    ) -> Optional[Player]:
        """Find a player by name with fuzzy matching.

        Uses SQL-level exact matches first (2 queries max),
        then falls back to a single in-memory fuzzy match.

        Args:
            name: Player name to search for.
            league_id: ID of the league.

        Returns:
            Player object or None if not found.
        """
        if not name:
            return None

        search_name = name.strip().lower()

        # Get scraper for name mappings
        try:
            scraper_type = self._get_scraper_type(league_id)
            scraper = get_scraper(scraper_type)
            mapped_name = scraper.name_mappings.get(search_name, search_name)
        except Exception:
            mapped_name = search_name

        # Try exact matches via SQL (mapped name and original name in one query)
        names_to_try = [mapped_name]
        if search_name != mapped_name:
            names_to_try.append(search_name)

        player = Player.query.filter(
            Player.league_id == league_id,
            Player.is_deleted.is_(False),
            db.func.lower(Player.name).in_(names_to_try)
        ).first()

        if player:
            return player

        # Fuzzy matching — single query to load all players once
        normalized_search = normalize_player_name(search_name)
        players = Player.query.filter(
            Player.league_id == league_id,
            Player.is_deleted.is_(False)
        ).all()

        for p in players:
            db_name_normalized = normalize_player_name(p.name)
            if db_name_normalized == normalized_search:
                return p
            # Substring match only when names are similar length
            # to avoid false positives (e.g. "Sharma" matching "Sharmila")
            shorter = min(len(db_name_normalized), len(normalized_search))
            longer = max(len(db_name_normalized), len(normalized_search))
            if longer > 0 and shorter / longer >= 0.8:
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

    def fetch_and_update_awards(self, league_id: int) -> dict:
        """Fetch awards from WPL and update database.

        Args:
            league_id: ID of the league.

        Returns:
            Dict with results for each award type.
        """
        results = {
            'orange_cap': None,
            'purple_cap': None,
            'mvp': None,
            'errors': []
        }

        try:
            scraper_type = self._get_scraper_type(league_id)
            scraper = get_scraper(scraper_type)
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error creating scraper: {e}")
            raise ValidationError(f'Failed to initialize scraper: {str(e)}')

        # Fetch all award data BEFORE opening a transaction
        # to avoid holding DB locks during slow network calls
        with scraper:
            orange_result = self._fetch_award_data(
                scraper, 'get_orange_cap', AwardType.ORANGE_CAP,
                league_id, results, 'runs'
            )
            purple_result = self._fetch_award_data(
                scraper, 'get_purple_cap', AwardType.PURPLE_CAP,
                league_id, results, 'wickets'
            )
            mvp_result = self._fetch_award_data(
                scraper, 'get_mvp', AwardType.MVP,
                league_id, results, 'points'
            )

        # Fallback: if MVP feed unavailable, use player with highest fantasy points
        if not mvp_result:
            mvp_result = self._compute_mvp_from_points(league_id, results)

        # Now write all awards in a single short transaction
        with self.transaction():
            for award_data in [orange_result, purple_result, mvp_result]:
                if award_data:
                    award = self._get_or_create_award(
                        award_data['award_type'], league_id
                    )
                    # Only update player_id when we have a match;
                    # don't clear an existing winner with None.
                    if award_data.get('player_id') is not None:
                        award.player_id = award_data['player_id']
                    if award_data.get('leaderboard'):
                        award.leaderboard_json = json.dumps(
                            award_data['leaderboard'], ensure_ascii=False
                        )

        return {
            'success': len(results['errors']) == 0,
            'results': results
        }

    def _fetch_award_data(
        self,
        scraper,
        method_name: str,
        award_type: AwardType,
        league_id: int,
        results: dict,
        stat_key: str
    ) -> Optional[dict]:
        """Fetch award data from scraper without writing to DB.

        Args:
            scraper: Scraper instance.
            method_name: Scraper method to call.
            award_type: Type of award.
            league_id: League ID for player matching.
            results: Mutable results dict (updated in place).
            stat_key: Key for the stat value.

        Returns:
            Dict with award_type and player_id if found, None otherwise.
        """
        result_key = award_type.value
        try:
            method = getattr(scraper, method_name)
            fetch_result = method()

            if fetch_result.success and fetch_result.leader:
                # Always serialize the top-5 leaderboard from the
                # scraper — this is pure display data from the website.
                top5 = [
                    entry.to_dict()
                    for entry in fetch_result.players[:5]
                ]

                # Try to match the leader to a DB player for the
                # award image. Fall back through the top-5 list.
                matched_player = None
                for entry in fetch_result.players[:5]:
                    p = self.find_player_by_name(
                        entry.player_name, league_id
                    )
                    if p:
                        matched_player = p
                        break

                leader_stat = fetch_result.leader.stats.get(stat_key, 0)
                results[result_key] = {
                    'player_name': (
                        matched_player.name if matched_player
                        else fetch_result.leader.player_name
                    ),
                    stat_key: leader_stat,
                    'wpl_name': fetch_result.leader.player_name
                }
                if matched_player:
                    results[result_key]['player_id'] = matched_player.id

                return {
                    'award_type': award_type.value,
                    'player_id': (
                        matched_player.id if matched_player else None
                    ),
                    'leaderboard': top5
                }
            else:
                results['errors'].append(
                    f"{result_key.replace('_', ' ').title()} fetch failed: "
                    f"{fetch_result.error}"
                )
        except Exception as e:
            logger.error(f"Error fetching {result_key}: {e}")
            results['errors'].append(f"{result_key}: {str(e)}")

        return None

    def _compute_mvp_from_points(
        self,
        league_id: int,
        results: dict
    ) -> Optional[dict]:
        """Compute MVP from the player with the highest fantasy points.

        Used as a fallback when the external MVP feed is unavailable.

        Args:
            league_id: ID of the league.
            results: Mutable results dict (updated in place).

        Returns:
            Dict with award_type and player_id if found, None otherwise.
        """
        top_players = Player.query.filter(
            Player.league_id == league_id,
            Player.is_deleted.is_(False),
            Player.fantasy_points > 0
        ).order_by(Player.fantasy_points.desc()).limit(5).all()

        if top_players:
            top_player = top_players[0]
            # Remove any MVP error from the feed failure since we have a fallback
            results['errors'] = [
                e for e in results['errors']
                if not e.lower().startswith('mvp')
            ]
            results['mvp'] = {
                'player_name': top_player.name,
                'player_id': top_player.id,
                'points': top_player.fantasy_points,
                'source': 'fantasy_points'
            }
            logger.info(
                f"MVP fallback: {top_player.name} "
                f"({top_player.fantasy_points} pts)"
            )
            # Build top-5 leaderboard from DB fantasy points
            leaderboard = [
                {
                    'player_name': p.name,
                    'team_short_name': p.team.name if p.team else '',
                    'points': p.fantasy_points,
                }
                for p in top_players
            ]
            return {
                'award_type': AwardType.MVP.value,
                'player_id': top_player.id,
                'leaderboard': leaderboard
            }

        return None

    def fetch_match_fantasy_points(self, league_id: int) -> dict:
        """Fetch all match scorecards and calculate fantasy points.

        Args:
            league_id: ID of the league.

        Returns:
            Dict with update results.
        """
        try:
            scraper_type = self._get_scraper_type(league_id)
            with get_scraper(scraper_type) as scraper:
                result = scraper.scrape_all_matches()
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error scraping matches: {e}")
            raise ValidationError(f'Failed to fetch match data: {str(e)}')

        if not result.get('success'):
            return result

        all_player_stats = result.get('player_stats', {})
        matches_processed = result.get('matches_processed', [])

        updated_players = []
        not_found_players = []

        with self.transaction():
            for wpl_name, data in all_player_stats.items():
                total_fantasy_points = data.get('total_fantasy_points', 0)
                matches_played = data.get('matches_played', 0)

                player = self.find_player_by_name(wpl_name, league_id)

                if player:
                    # Get existing game_ids (only non-deleted entries)
                    existing_entries = FantasyPointEntry.query.filter_by(
                        player_id=player.id,
                        league_id=league_id,
                        is_deleted=False
                    ).all()
                    existing_game_ids = {e.game_id for e in existing_entries if e.game_id}

                    new_entries_added = 0
                    for match in data.get('matches', []):
                        game_id = match.get('game_id', '')

                        if game_id and game_id in existing_game_ids:
                            continue

                        match_num_str = match.get('match', '')
                        if isinstance(match_num_str, str):
                            match_num_str = match_num_str.replace('Match ', '').strip()

                        # Handle playoff matches with special numbers (from constants)
                        match_number = PLAYOFF_MATCH_NUMBERS.get(match_num_str.lower())
                        if match_number is None:
                            try:
                                match_number = int(match_num_str)
                            except (ValueError, TypeError):
                                logger.warning(
                                    f"Could not parse match number: {match_num_str} "
                                    f"for player {player.name}"
                                )
                                continue

                        points = match.get('fantasy_points', 0)

                        entry = FantasyPointEntry(
                            player_id=player.id,
                            match_number=match_number,
                            game_id=game_id,
                            points=points,
                            league_id=league_id
                        )
                        db.session.add(entry)
                        existing_game_ids.add(game_id)
                        new_entries_added += 1

                    # Recalculate total
                    self.flush()
                    total_from_entries = self._calculate_total_points(player.id, league_id)
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
                    logger.warning(
                        "Player not found in DB: %s (%.1f pts, %d matches)",
                        wpl_name, total_fantasy_points, matches_played
                    )
                    not_found_players.append({
                        'wpl_name': wpl_name,
                        'total_points': total_fantasy_points,
                        'matches': matches_played,
                    })

        return {
            'success': True,
            'matches_scraped': len(matches_processed),
            'players_updated': len(updated_players),
            'players_not_found': len(not_found_players),
            'updated': updated_players,
            'not_found': not_found_players
        }


# Singleton instance for use in routes
fantasy_service = FantasyService()
