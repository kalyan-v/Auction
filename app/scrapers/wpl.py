"""
WPL (Women's Premier League) scraper implementation.

Scrapes data from wplt20.com for the Women's Premier League.
"""

import json
import re
from typing import Any, Dict, Optional, Set

from app.constants import (
    TEAM_CODE_TO_SLUG,
    WPL_BASE_URL,
    WPL_SERIES_ID,
    WPL_STATS_URL_PATTERNS,
    WPL_TEAM_IDS,
)
from app.dataclasses import (
    LeaderboardEntry,
    MatchInfo,
    PlayerStats,
    PointsTableEntry,
    ScorecardResult,
    StatsResult,
)
from app.enums import LeagueType
from app.logger import get_logger
from app.player_data import KNOWN_BOWLERS, NAME_MAPPINGS
from app.scrapers.base import BaseScraper
from app.utils import safe_float, safe_int

logger = get_logger(__name__)

# Fielders to ignore in dismissal strings (substitutes, etc.)
IGNORED_FIELDERS: frozenset = frozenset({"sub", "substitute"})


class WPLScraper(BaseScraper):
    """
    Scraper for Women's Premier League (WPL) data from wplt20.com.

    Handles scraping of:
    - Statistics (Orange Cap, Purple Cap, MVP, etc.)
    - Points table
    - Match scorecards
    - Player fantasy points calculation
    """

    def __init__(self, series_id: Optional[str] = None) -> None:
        """
        Initialize WPL scraper.

        Args:
            series_id: Optional series ID override (defaults to current season)
        """
        super().__init__()
        self._series_id = series_id or WPL_SERIES_ID

    # ==================== Abstract Property Implementations ====================

    @property
    def league_type(self) -> LeagueType:
        return LeagueType.WPL

    @property
    def base_url(self) -> str:
        return WPL_BASE_URL

    @property
    def series_id(self) -> str:
        return self._series_id

    @property
    def known_bowlers(self) -> Set[str]:
        return KNOWN_BOWLERS

    @property
    def name_mappings(self) -> Dict[str, str]:
        return NAME_MAPPINGS

    @property
    def team_mappings(self) -> Dict[str, str]:
        return WPL_TEAM_IDS

    # ==================== Stats Scraping ====================

    def _extract_leaderboard_json(self, html: str) -> Optional[list]:
        """Extract leaderboard JSON data from HTML."""
        pattern = r'"leaderboard"\s*:\s*(\[[^\]]+\])'
        matches = re.findall(pattern, html)
        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error in leaderboard: {e}")
        return None

    def _scrape_stats(self, stat_type: str) -> StatsResult:
        """
        Scrape statistics from WPL website.

        Args:
            stat_type: Type of stats (most-runs, most-wickets, mvp, etc.)

        Returns:
            StatsResult with leaderboard data
        """
        url_pattern = WPL_STATS_URL_PATTERNS.get(stat_type)
        if not url_pattern:
            return StatsResult(
                success=False,
                error=f"Unknown stat type: {stat_type}"
            )

        url = self.base_url + url_pattern.format(series_id=self.series_id)
        response = self._make_request(url)

        if not response:
            return StatsResult(success=False, error="Request failed")

        leaderboard = self._extract_leaderboard_json(response.text)
        if not leaderboard:
            return StatsResult(success=False, error="No leaderboard data found")

        players = []
        for player in leaderboard:
            stats: Dict[str, Any] = {}

            # Add stat-specific fields
            if stat_type == "most-runs":
                stats = {
                    "runs": safe_int(player.get("runs_scored", 0)),
                    "average": safe_float(player.get("average", 0)),
                    "strike_rate": safe_float(player.get("batting_strike_rate", 0)),
                    "highest_score": player.get("highest_score", ""),
                    "fifties": safe_int(player.get("fifties", 0)),
                    "hundreds": safe_int(player.get("hundred", 0)),
                    "fours": safe_int(player.get("fours", 0)),
                    "sixes": safe_int(player.get("sixes", 0)),
                }
            elif stat_type == "most-wickets":
                stats = {
                    "wickets": safe_int(player.get("wickets", 0)),
                    "economy": safe_float(player.get("economy", 0)),
                    "average": safe_float(player.get("average", 0)),
                    "best_bowling": player.get("best_bowling", ""),
                }
            elif stat_type == "mvp":
                stats = {
                    "points": safe_float(player.get("points", 0)),
                    "wickets": safe_int(player.get("wickets", 0)),
                    "catches": safe_int(player.get("catches", 0)),
                    "run_outs": safe_int(player.get("run_outs", 0)),
                    "stumpings": safe_int(player.get("stumpings", 0)),
                }

            players.append(LeaderboardEntry(
                player_id=str(player.get("player_id", "")),
                player_name=player.get("player_name", ""),
                team_name=player.get("team_name", ""),
                team_short_name=player.get("team_short_name", ""),
                matches_played=safe_int(player.get("matches_played", 0)),
                stats=stats,
            ))

        return StatsResult(
            success=True,
            stat_type=stat_type,
            players=players,
            source="wpl_website",
        )

    def get_orange_cap(self) -> StatsResult:
        """Get Orange Cap (most runs) leader."""
        return self._scrape_stats("most-runs")

    def get_purple_cap(self) -> StatsResult:
        """Get Purple Cap (most wickets) leader."""
        return self._scrape_stats("most-wickets")

    def get_mvp(self) -> StatsResult:
        """Get MVP (most valuable player)."""
        return self._scrape_stats("mvp")

    def get_stats(self, stat_type: str) -> StatsResult:
        """
        Get any type of statistics.

        Args:
            stat_type: One of the supported stat types

        Returns:
            StatsResult with leaderboard data
        """
        return self._scrape_stats(stat_type)

    # ==================== Points Table ====================

    def get_points_table(self) -> Dict[str, Any]:
        """Get WPL points table."""
        url = f"{self.base_url}/points-table-standings"
        response = self._make_request(url)

        if not response:
            return {"success": False, "error": "Request failed"}

        pattern = r'"pointsTableList"\s*:\s*(\[[^\]]+\])'
        matches = re.findall(pattern, response.text)

        if not matches:
            return {"success": False, "error": "Points table data not found"}

        try:
            teams_data = json.loads(matches[0])
            teams = [
                PointsTableEntry(
                    team_name=team.get("team_name", ""),
                    team_short_name=team.get("team_short_name", ""),
                    played=safe_int(team.get("played", 0)),
                    won=safe_int(team.get("won", 0)),
                    lost=safe_int(team.get("lost", 0)),
                    tied=safe_int(team.get("tied", 0)),
                    no_result=safe_int(team.get("no_result", 0)),
                    points=safe_int(team.get("points", 0)),
                    nrr=safe_float(team.get("net_run_rate", 0)),
                ).to_dict()
                for team in teams_data
            ]
            return {"success": True, "teams": teams}
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in points table: {e}")
            return {"success": False, "error": "Could not parse points table"}

    # ==================== Match URLs ====================

    def get_all_match_urls(self) -> Dict[str, Any]:
        """Get URLs for all completed WPL matches."""
        url = f"{self.base_url}/schedule-fixtures-results"
        response = self._make_request(url)

        if not response:
            return {"success": False, "error": "Request failed"}

        pattern = r'window\.fixtures_07_1\s*=\s*(\{[\s\S]*?\});'
        matches = re.findall(pattern, response.text)

        if not matches:
            return {"success": False, "error": "Fixtures data not found"}

        try:
            data = json.loads(matches[0])
            matches_list = data.get("matches", [])

            match_urls = []
            for match in matches_list:
                # Only include completed matches
                if match.get("event_state") != "R":
                    continue

                game_id = match.get("game_id", "")
                if not game_id:
                    continue

                url_path = self._construct_match_url(game_id)
                if url_path:
                    match_urls.append({
                        "url": url_path,
                        "game_id": game_id,
                        "match_name": match.get("event_name", ""),
                        "date": match.get("start_date", ""),
                    })

            return {
                "success": True,
                "match_urls": [m["url"] for m in match_urls],
                "matches": match_urls,
                "count": len(match_urls),
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in fixtures: {e}")
            return {"success": False, "error": "Could not parse fixtures"}

    def _construct_match_url(self, game_id: str) -> Optional[str]:
        """Construct match URL from game ID."""
        if len(game_id) < 6:
            return None

        home_code = game_id[:3]
        away_code = game_id[3:6]

        home_slug = TEAM_CODE_TO_SLUG.get(home_code)
        away_slug = TEAM_CODE_TO_SLUG.get(away_code)

        if not home_slug or not away_slug:
            return None

        return f"/schedule-fixtures-results/{home_slug}-vs-{away_slug}-{game_id}"

    # ==================== Match Scorecard ====================

    def _is_absolute_url(self, url: str) -> bool:
        """Check if URL is absolute (has protocol)."""
        return url.startswith("http://") or url.startswith("https://")

    def _extract_game_id(self, url: str) -> str:
        """Extract game_id from match URL."""
        # URL format: /schedule-fixtures-results/team1-vs-team2-GAMEID
        # Example: /schedule-fixtures-results/mumbai-indians-vs-royal-challengers-bengaluru-minblr01092026267686
        match = re.search(r'-([a-z]{6}\d+)(?:\?|$)', url)
        if match:
            return match.group(1)
        # Fallback: extract last segment after the last hyphen
        parts = url.rstrip('/').split('-')
        if parts:
            return parts[-1]
        return ""

    def scrape_match_scorecard(self, match_url: str) -> ScorecardResult:
        """Scrape detailed scorecard from a WPL match page."""
        if not self._is_absolute_url(match_url):
            match_url = self.base_url + match_url

        response = self._make_request(match_url)
        if not response:
            return ScorecardResult(success=False, error="Request failed")

        pattern = r'window\.cricketscorecard_04_1\s*=\s*(\{[\s\S]*?\});'
        matches = re.findall(pattern, response.text)

        if not matches:
            return ScorecardResult(success=False, error="Scorecard data not found")

        try:
            data = json.loads(matches[0])
            game_data = data.get("gameData", {})
            match_detail = game_data.get("Matchdetail", {})
            innings_list = game_data.get("Innings", [])

            match_info = MatchInfo(
                match_number=match_detail.get("Match", {}).get("Number", "Unknown"),
                home_team=self.team_mappings.get(
                    str(match_detail.get("Team_Home", "")), "T1"
                ),
                away_team=self.team_mappings.get(
                    str(match_detail.get("Team_Away", "")), "T2"
                ),
                date=match_detail.get("Match", {}).get("Date", ""),
                url=match_url,
                game_id=self._extract_game_id(match_url),
            )

            player_stats: Dict[str, PlayerStats] = {}

            # First pass: Extract batting and bowling stats
            for innings in innings_list:
                self._extract_batting_stats(innings, player_stats)
                self._extract_bowling_stats(innings, player_stats)

            # Second pass: Extract fielding stats
            for innings in innings_list:
                self._extract_fielding_stats(innings, player_stats)

            return ScorecardResult(
                success=True,
                match_info=match_info,
                player_stats=player_stats,
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in scorecard: {e}")
            return ScorecardResult(success=False, error=f"JSON parse error: {e}")

    def _extract_batting_stats(
        self,
        innings: Dict[str, Any],
        player_stats: Dict[str, PlayerStats]
    ) -> None:
        """Extract batting stats from innings data."""
        for batsman in innings.get("Batsmen", []):
            name = batsman.get("Name_Full", "")
            if not name:
                continue

            if name not in player_stats:
                player_stats[name] = self.create_empty_player_stats(name)

            stats = player_stats[name]
            stats.runs = safe_int(batsman.get("Runs", 0))
            stats.balls_faced = safe_int(batsman.get("Balls", 0))
            stats.fours = safe_int(batsman.get("Fours", 0))
            stats.sixes = safe_int(batsman.get("Sixes", 0))

            # Determine if out
            howout = batsman.get("Howout", "")
            is_not_out = (
                not howout or
                "not out" in howout.lower() or
                howout.lower() == "batting"
            )
            stats.is_out = not is_not_out

            # Check for LBW/Bowled (for bowler bonus)
            howout_lower = howout.lower()
            is_lbw_bowled = "lbw" in howout_lower or howout_lower.startswith("b ")

            if is_lbw_bowled:
                bowler_id = batsman.get("Bowler")
                for bowler in innings.get("Bowlers", []):
                    if str(bowler.get("Bowler", "")) == str(bowler_id):
                        bowler_name = bowler.get("Name_Full", "")
                        if bowler_name:
                            if bowler_name not in player_stats:
                                player_stats[bowler_name] = self.create_empty_player_stats(bowler_name)
                            player_stats[bowler_name].lbw_bowled += 1
                        break

    def _extract_bowling_stats(
        self,
        innings: Dict[str, Any],
        player_stats: Dict[str, PlayerStats]
    ) -> None:
        """Extract bowling stats from innings data."""
        for bowler in innings.get("Bowlers", []):
            name = bowler.get("Name_Full", "")
            if not name:
                continue

            if name not in player_stats:
                player_stats[name] = self.create_empty_player_stats(name)

            stats = player_stats[name]
            stats.wickets = safe_int(bowler.get("Wickets", 0))
            stats.overs = safe_float(bowler.get("Overs", 0))
            stats.runs_conceded = safe_int(bowler.get("Runs", 0))
            stats.maidens = safe_int(bowler.get("Maidens", 0))
            stats.dot_balls = safe_int(bowler.get("Dots", 0))

    def _is_valid_fielder(self, fielder_name: str) -> bool:
        """Check if fielder name is valid (not a substitute placeholder)."""
        if not fielder_name:
            return False
        return fielder_name.lower() not in IGNORED_FIELDERS

    def _credit_fielding_action(
        self,
        fielder: str,
        player_stats: Dict[str, PlayerStats],
        action: str
    ) -> None:
        """Credit a fielding action to a player if valid."""
        fielder = fielder.strip()
        if not self._is_valid_fielder(fielder):
            return

        if fielder not in player_stats:
            player_stats[fielder] = self.create_empty_player_stats(fielder)

        if action == "catch":
            player_stats[fielder].catches += 1
        elif action == "stumping":
            player_stats[fielder].stumpings += 1
        elif action == "run_out_direct":
            player_stats[fielder].run_outs_direct += 1
        elif action == "run_out_indirect":
            player_stats[fielder].run_outs_indirect += 1

    def _extract_fielding_stats(
        self,
        innings: Dict[str, Any],
        player_stats: Dict[str, PlayerStats]
    ) -> None:
        """Extract fielding stats from dismissal strings."""
        for batsman in innings.get("Batsmen", []):
            howout = batsman.get("Howout", "")
            if not howout:
                continue

            # Caught & bowled
            cb_match = re.match(r'c\s*&\s*b\s+(.+)', howout)
            if cb_match:
                self._credit_fielding_action(
                    cb_match.group(1), player_stats, "catch"
                )
            else:
                # Regular catch
                catch_match = re.match(r'c\s+(.+?)\s+b\s+', howout)
                if catch_match:
                    self._credit_fielding_action(
                        catch_match.group(1), player_stats, "catch"
                    )

            # Stumping
            st_match = re.match(r'st\s+(.+?)\s+b\s+', howout)
            if st_match:
                self._credit_fielding_action(
                    st_match.group(1), player_stats, "stumping"
                )

            # Run out
            ro_match = re.search(r'run out.*?\(([^)]+)\)', howout)
            if ro_match:
                fielders = ro_match.group(1).split("/")
                if len(fielders) == 1:
                    self._credit_fielding_action(
                        fielders[0], player_stats, "run_out_direct"
                    )
                else:
                    for f in fielders:
                        self._credit_fielding_action(
                            f, player_stats, "run_out_indirect"
                        )
