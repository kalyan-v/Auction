"""
Fantasy points service for managing fantasy league operations.

Encapsulates all business logic related to:
- Fantasy points management
- Fantasy awards (MVP, Orange Cap, Purple Cap)
- Player name matching
- External data fetching
"""

from typing import Dict, List, Optional

from app import db
from app.enums import AwardType
from app.logger import get_logger
from app.models import FantasyAward, FantasyPointEntry, Player
from app.scrapers import get_scraper, ScraperType
from app.services.base import BaseService, NotFoundError, ValidationError
from app.utils import normalize_player_name

logger = get_logger(__name__)


class FantasyService(BaseService):
    """Service for fantasy points and awards operations.

    Handles points management, awards, and data fetching from external sources.
    """

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

            # Check for existing entry
            existing = FantasyPointEntry.query.filter_by(
                player_id=player_id,
                match_number=match_number,
                league_id=league_id
            ).first()

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

    def delete_match_points(self, entry_id: int) -> dict:
        """Soft delete a specific match point entry.

        Args:
            entry_id: ID of the entry to delete.

        Returns:
            Dict with success status and new total.

        Raises:
            NotFoundError: If entry not found.
        """
        with self.transaction():
            entry = db.session.get(FantasyPointEntry, entry_id)
            if not entry or entry.is_deleted:
                raise NotFoundError("Entry not found")

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
            award = FantasyAward.query.filter_by(
                award_type=award_type,
                league_id=league_id
            ).first()

            if not award:
                award = FantasyAward(award_type=award_type, league_id=league_id)
                db.session.add(award)

            award.player_id = player_id if player_id else None

            player_name = None
            if player_id:
                player = db.session.get(Player, player_id)
                player_name = player.name if player else None

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
            result[award.award_type] = {
                'player_id': award.player_id,
                'player_name': award.player.name if award.player else None
            }
        return {'success': True, 'awards': result}

    # ==================== PLAYER MATCHING ====================

    def find_player_by_name(
        self,
        name: str,
        league_id: int
    ) -> Optional[Player]:
        """Find a player by name with fuzzy matching.

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
            scraper = get_scraper(ScraperType.WPL)
            mapped_name = scraper.name_mappings.get(search_name, search_name)
        except Exception:
            mapped_name = search_name

        # Try exact match with mapped name
        player = Player.query.filter(
            Player.league_id == league_id,
            Player.is_deleted.is_(False),
            db.func.lower(Player.name) == mapped_name
        ).first()

        if player:
            return player

        # Try exact match with original name
        player = Player.query.filter(
            Player.league_id == league_id,
            Player.is_deleted.is_(False),
            db.func.lower(Player.name) == search_name
        ).first()

        if player:
            return player

        # Fuzzy matching
        normalized_search = normalize_player_name(search_name)
        players = Player.query.filter(
            Player.league_id == league_id,
            Player.is_deleted.is_(False)
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
            scraper = get_scraper(ScraperType.WPL)
        except Exception as e:
            logger.error(f"Error creating scraper: {e}")
            raise ValidationError(f'Failed to initialize scraper: {str(e)}')

        with scraper:
            # Fetch Orange Cap
            results = self._fetch_award(
                scraper, 'get_orange_cap', AwardType.ORANGE_CAP,
                league_id, results, 'runs'
            )

            # Fetch Purple Cap
            results = self._fetch_award(
                scraper, 'get_purple_cap', AwardType.PURPLE_CAP,
                league_id, results, 'wickets'
            )

            # Fetch MVP
            results = self._fetch_award(
                scraper, 'get_mvp', AwardType.MVP,
                league_id, results, 'points'
            )

        db.session.commit()

        return {
            'success': len(results['errors']) == 0,
            'results': results
        }

    def _fetch_award(
        self,
        scraper,
        method_name: str,
        award_type: AwardType,
        league_id: int,
        results: dict,
        stat_key: str
    ) -> dict:
        """Helper to fetch and set a single award."""
        result_key = award_type.value
        try:
            method = getattr(scraper, method_name)
            fetch_result = method()

            if fetch_result.success and fetch_result.leader:
                player_name = fetch_result.leader.player_name
                player = self.find_player_by_name(player_name, league_id)

                if player:
                    award = FantasyAward.query.filter_by(
                        award_type=award_type.value,
                        league_id=league_id
                    ).first()

                    if not award:
                        award = FantasyAward(
                            award_type=award_type.value,
                            league_id=league_id
                        )
                        db.session.add(award)

                    award.player_id = player.id
                    results[result_key] = {
                        'player_name': player.name,
                        'player_id': player.id,
                        stat_key: fetch_result.leader.stats.get(stat_key, 0),
                        'wpl_name': player_name
                    }
                else:
                    results['errors'].append(
                        f"{result_key.replace('_', ' ').title()}: "
                        f"Player '{player_name}' not found"
                    )
            else:
                results['errors'].append(
                    f"{result_key.replace('_', ' ').title()} fetch failed: "
                    f"{fetch_result.error}"
                )
        except Exception as e:
            logger.error(f"Error fetching {result_key}: {e}")
            results['errors'].append(f"{result_key}: {str(e)}")

        return results

    def fetch_match_fantasy_points(self, league_id: int) -> dict:
        """Fetch all match scorecards and calculate fantasy points.

        Args:
            league_id: ID of the league.

        Returns:
            Dict with update results.
        """
        try:
            with get_scraper(ScraperType.WPL) as scraper:
                result = scraper.scrape_all_matches()
        except Exception as e:
            logger.error(f"Error scraping matches: {e}")
            raise ValidationError(f'Failed to fetch match data: {str(e)}')

        if not result.get('success'):
            return result

        all_player_stats = result.get('player_stats', {})
        matches_processed = result.get('matches_processed', [])

        updated_players = []
        not_found_players = []

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
                        league_id=league_id
                    )
                    db.session.add(entry)
                    existing_game_ids.add(game_id)
                    new_entries_added += 1

                # Recalculate total
                db.session.flush()
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
                not_found_players.append({
                    'wpl_name': wpl_name,
                    'total_points': total_fantasy_points,
                    'matches': matches_played,
                })

        db.session.commit()

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
