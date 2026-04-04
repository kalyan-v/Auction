"""
IPL (Indian Premier League) scraper implementation.

Scrapes data from iplt20.com and scores.iplt20.com JSONP feeds
for the Indian Premier League.
"""

import json
import re
from typing import Any, Dict, List, Optional, Set

from app.constants import (
    CRICBUZZ_BASE_MATCH_ID,
    CRICBUZZ_IPL_SERIES_ID,
    CRICBUZZ_MATCH_ID_STEP,
    CRICBUZZ_MIN_SCORECARD_SIZE,
    CRICBUZZ_SCORECARD_URL,
    IPL_BASE_URL,
    IPL_COMPETITION_ID,
    IPL_FEED_URL,
    IPL_TEAM_IDS,
)
from app.dataclasses import (
    AggregatedPlayerStats,
    LeaderboardEntry,
    MatchInfo,
    PlayerStats,
    PointsTableEntry,
    ScorecardResult,
    StatsResult,
)
from app.enums import LeagueType
from app.logger import get_logger
from app.player_data import IPL_KNOWN_BOWLERS, IPL_NAME_MAPPINGS
from app.scrapers.base import BaseScraper
from app.utils import cricket_overs_to_decimal, normalize_player_name, safe_float, safe_int

logger = get_logger(__name__)

# Fielders to ignore in dismissal strings (substitutes, etc.)
IGNORED_FIELDERS: frozenset = frozenset({"sub", "substitute"})


class IPLScraper(BaseScraper):
    """
    Scraper for Indian Premier League (IPL) data from iplt20.com.

    Uses JSONP feeds from scores.iplt20.com for:
    - Match scorecards (innings feeds)
    - Match schedule (competition schedule feed)
    - Statistics (top run scorers, most wickets)
    - Points table (group standings feed)

    Example:
        scraper = IPLScraper()
        scorecard = scraper.scrape_match_scorecard("/match/2026/2417")
    """

    def __init__(self, competition_id: Optional[str] = None) -> None:
        """
        Initialize IPL scraper.

        Args:
            competition_id: Optional competition ID override (defaults to current season)
        """
        super().__init__()
        self._competition_id = competition_id or IPL_COMPETITION_ID
        self._cricbuzz_id_cache: Dict[str, str] = {}  # match_number -> cb_id

    # ==================== Abstract Property Implementations ====================

    @property
    def league_type(self) -> LeagueType:
        """Return the league type this scraper handles."""
        return LeagueType.IPL

    @property
    def base_url(self) -> str:
        """Return the base URL for the IPL website."""
        return IPL_BASE_URL

    @property
    def series_id(self) -> str:
        """Return the current competition ID."""
        return self._competition_id

    @property
    def known_bowlers(self) -> Set[str]:
        """Return set of known IPL bowler names (lowercase)."""
        return IPL_KNOWN_BOWLERS

    @property
    def name_mappings(self) -> Dict[str, str]:
        """Return IPL name mappings for player name normalization."""
        return IPL_NAME_MAPPINGS

    @property
    def team_mappings(self) -> Dict[str, str]:
        """Return IPL team ID to abbreviation mappings."""
        return IPL_TEAM_IDS

    @property
    def feed_url(self) -> str:
        """Return the base feed URL for JSONP data."""
        return IPL_FEED_URL

    # ==================== JSONP Helpers ====================

    def _fetch_jsonp(self, url: str, callback_name: str) -> Optional[Any]:
        """
        Fetch a JSONP endpoint and extract the JSON data.

        Args:
            url: Full URL to the JSONP endpoint
            callback_name: Expected JSONP callback function name

        Returns:
            Parsed JSON data, or None on failure
        """
        response = self._make_request(url)
        if not response:
            return None

        pattern = rf'{callback_name}\((\{{.*\}})\)'
        match = re.search(pattern, response.text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error in JSONP response: {e}")
        return None

    # ==================== Stats Scraping ====================

    def _scrape_stats(self, stat_type: str) -> StatsResult:
        """
        Scrape statistics from IPL JSONP feeds.

        Args:
            stat_type: Type of stats (most-runs, most-wickets)

        Returns:
            StatsResult with leaderboard data
        """
        feed_map = {
            "most-runs": ("toprunsscorers", "ontoprunsscorers"),
            "most-wickets": ("mostwickets", "onmostwickets"),
        }

        feed_info = feed_map.get(stat_type)
        if not feed_info:
            return StatsResult(
                success=False,
                error=f"Unsupported stat type for IPL: {stat_type}"
            )

        feed_name, callback = feed_info
        url = f"{self.feed_url}/stats/{self._competition_id}-{feed_name}.js"
        data = self._fetch_jsonp(url, callback)

        if not data:
            return StatsResult(success=False, error="Feed request failed")

        entries = data.get(feed_name, [])
        if not entries:
            return StatsResult(success=False, error=f"No {stat_type} data found")

        players: List[LeaderboardEntry] = []
        for player in entries:
            stats: Dict[str, Any] = {}

            if stat_type == "most-runs":
                stats = {
                    "runs": safe_int(player.get("TotalRuns", 0)),
                    "average": safe_float(player.get("BattingAverage", 0)),
                    "strike_rate": safe_float(player.get("StrikeRate", 0)),
                    "highest_score": player.get("HighestScore", ""),
                    "fifties": safe_int(player.get("FiftyPlusRuns", 0)),
                    "hundreds": safe_int(player.get("Centuries", 0)),
                    "fours": safe_int(player.get("Fours", 0)),
                    "sixes": safe_int(player.get("Sixes", 0)),
                }
                player_name = player.get("StrikerName", "")
            elif stat_type == "most-wickets":
                stats = {
                    "wickets": safe_int(player.get("Wickets", 0)),
                    "economy": safe_float(player.get("EconomyRate", 0)),
                    "average": safe_float(player.get("BowlingAverage", 0)),
                    "best_bowling": player.get("BBIW", ""),
                }
                player_name = player.get("BowlerName", "")
            else:
                player_name = ""

            players.append(LeaderboardEntry(
                player_id=str(player.get("ClientPlayerID", "")),
                player_name=player_name,
                team_name=player.get("TeamName", ""),
                team_short_name=player.get("TeamCode", ""),
                matches_played=safe_int(player.get("Matches", 0)),
                stats=stats,
            ))

        return StatsResult(
            success=True,
            stat_type=stat_type,
            players=players,
            source="ipl_feeds",
        )

    def get_orange_cap(self) -> StatsResult:
        """Get Orange Cap (most runs) leader."""
        return self._scrape_stats("most-runs")

    def get_purple_cap(self) -> StatsResult:
        """Get Purple Cap (most wickets) leader."""
        return self._scrape_stats("most-wickets")

    def get_mvp(self) -> StatsResult:
        """
        Get MVP (most valuable player).

        Note: IPL MVP feed may not be available early in the season.
        """
        url = f"{self.feed_url}/stats/{self._competition_id}-mvpPlayersList.js"
        data = self._fetch_jsonp(url, "onmvpplayerslist")

        if not data:
            return StatsResult(
                success=False,
                error="MVP data not available"
            )

        entries = data.get("mvpplayerslist", [])
        players = []
        for player in entries:
            players.append(LeaderboardEntry(
                player_id=str(player.get("ClientPlayerID", "")),
                player_name=player.get("PlayerName", ""),
                team_name=player.get("TeamName", ""),
                team_short_name=player.get("TeamCode", ""),
                matches_played=safe_int(player.get("Matches", 0)),
                stats={"points": safe_float(player.get("Points", 0))},
            ))

        return StatsResult(
            success=True,
            stat_type="mvp",
            players=players,
            source="ipl_feeds",
        )

    def get_stats(self, stat_type: str) -> StatsResult:
        """
        Get any type of statistics.

        Args:
            stat_type: One of the supported stat types

        Returns:
            StatsResult with leaderboard data
        """
        if stat_type == "mvp":
            return self.get_mvp()
        return self._scrape_stats(stat_type)

    # ==================== Points Table ====================

    def get_points_table(self) -> Dict[str, Any]:
        """Get IPL points table from standings feed."""
        url = f"{self.feed_url}/stats/{self._competition_id}-groupstandings.js"
        data = self._fetch_jsonp(url, "ongroupstandings")

        if not data:
            return {"success": False, "error": "Points table feed request failed"}

        standings = data.get("points", [])
        if not standings:
            return {"success": False, "error": "Points table data not found"}

        teams = [
            PointsTableEntry(
                team_name=team.get("TeamName", ""),
                team_short_name=team.get("TeamCode", ""),
                played=safe_int(team.get("Matches", 0)),
                won=safe_int(team.get("Wins", 0)),
                lost=safe_int(team.get("Loss", 0)),
                tied=safe_int(team.get("Tied", 0)),
                no_result=safe_int(team.get("NoResult", 0)),
                points=safe_int(team.get("Points", 0)),
                nrr=safe_float(team.get("NetRunRate", 0)),
            ).to_dict()
            for team in standings
        ]
        return {"success": True, "teams": teams}

    # ==================== Match URLs ====================

    def get_all_match_urls(self) -> Dict[str, Any]:
        """Get URLs for all completed IPL matches from the schedule feed."""
        url = f"{self.feed_url}/{self._competition_id}-matchschedule.js"
        data = self._fetch_jsonp(url, "MatchSchedule")

        if not data:
            return {"success": False, "error": "Schedule feed request failed"}

        matches_list = data.get("Matchsummary", [])
        if not matches_list:
            return {"success": False, "error": "No matches data found"}

        match_urls = []
        for match in matches_list:
            # Only include completed matches
            if match.get("MatchStatus") != "Post":
                continue

            match_id = match.get("MatchID")
            if not match_id:
                continue

            match_year = match.get("MatchDate", "")[:4] or "2026"
            url_path = f"/match/{match_year}/{match_id}"

            # Extract match number from "Match 1" format
            match_order = match.get("MatchOrder", "")

            match_urls.append({
                "url": url_path,
                "game_id": str(match_id),
                "match_name": match.get("MatchName", ""),
                "match_order": match_order,
                "date": match.get("MatchDateNew", ""),
            })

        return {
            "success": True,
            "match_urls": [m["url"] for m in match_urls],
            "matches": match_urls,
            "count": len(match_urls),
        }

    # ==================== Match Scorecard ====================

    def _extract_match_id(self, url: str) -> Optional[str]:
        """
        Extract match ID from an IPL match URL.

        Args:
            url: Match URL like /match/2026/2417

        Returns:
            Match ID string, or None if not found
        """
        match = re.search(r'/match/\d{4}/(\d+)', url)
        if match:
            return match.group(1)
        # Fallback: last numeric segment
        match = re.search(r'(\d+)\s*$', url)
        if match:
            return match.group(1)
        return None

    def scrape_match_scorecard(
        self, match_url: str, match_number: Optional[str] = None
    ) -> ScorecardResult:
        """
        Scrape detailed scorecard from an IPL match using JSONP feeds.

        Args:
            match_url: URL of the match page (e.g., /match/2026/2417)
            match_number: Optional match number for Cricbuzz run out lookup.

        Returns:
            ScorecardResult with player stats
        """
        match_id = self._extract_match_id(match_url)
        if not match_id:
            return ScorecardResult(success=False, error="Could not extract match ID")

        # Fetch match summary for match info
        summary_url = f"{self.feed_url}/{match_id}-matchsummary.js"
        summary_data = self._fetch_jsonp(summary_url, "onScoringMatchsummary")

        if not summary_data:
            return ScorecardResult(success=False, error="Match summary feed failed")

        summary_list = summary_data.get("MatchSummary", [])
        if not summary_list:
            return ScorecardResult(success=False, error="No match summary data")

        summary = summary_list[0] if isinstance(summary_list, list) else summary_list

        match_info = MatchInfo(
            match_number=match_number or str(
                summary.get("MatchOrder", "Unknown")
            ),
            home_team=summary.get("HomeTeamCode", "T1"),
            away_team=summary.get("AwayTeamCode", "T2"),
            date=summary.get("MatchDate", ""),
            url=match_url,
            game_id=match_id,
        )

        player_stats: Dict[str, PlayerStats] = {}

        # Determine number of innings (2 for normal, 4 for super over)
        is_super_over = summary.get("IsSuperOver", 0)
        max_innings = 4 if is_super_over else 2

        # Collect all batting cards first to check for run outs
        all_batting_cards: List[List[Dict[str, Any]]] = []
        all_bowling_cards: List[List[Dict[str, Any]]] = []

        # Fetch each innings
        for inn_no in range(1, max_innings + 1):
            innings_url = f"{self.feed_url}/{match_id}-Innings{inn_no}.js"
            innings_data = self._fetch_jsonp(innings_url, "onScoring")

            if not innings_data:
                if inn_no <= 2:
                    logger.warning(f"Missing innings {inn_no} for match {match_id}")
                continue

            innings = innings_data.get(f"Innings{inn_no}", {})
            if not innings:
                continue

            batting_card = innings.get("BattingCard", [])
            bowling_card = innings.get("BowlingCard", [])
            all_batting_cards.append(batting_card)
            all_bowling_cards.append(bowling_card)

        # Check if any run outs have only 1 fielder in the IPL feed
        has_single_fielder_runout = False
        for bc in all_batting_cards:
            for b in bc:
                ro_match = re.search(
                    r'run\s*out\s*\((.+?)\)',
                    b.get("OutDesc", ""),
                    re.IGNORECASE,
                )
                if ro_match and len(ro_match.group(1).split("/")) == 1:
                    has_single_fielder_runout = True
                    break
            if has_single_fielder_runout:
                break

        # Fetch Cricbuzz run out details only when needed
        cricbuzz_runouts: Optional[Dict[str, List[str]]] = None
        if has_single_fielder_runout:
            cricbuzz_runouts = self._fetch_cricbuzz_runout_details(
                match_info.home_team,
                match_info.away_team,
                match_info.match_number,
            )

        # Now extract all stats
        for batting_card, bowling_card in zip(
            all_batting_cards, all_bowling_cards
        ):
            self._extract_batting_stats(batting_card, player_stats)
            self._extract_bowling_stats(bowling_card, player_stats)
            self._extract_fielding_stats(
                batting_card, player_stats, cricbuzz_runouts
            )

        return ScorecardResult(
            success=True,
            match_info=match_info,
            player_stats=player_stats,
        )

    def _extract_batting_stats(
        self,
        batting_card: List[Dict[str, Any]],
        player_stats: Dict[str, PlayerStats]
    ) -> None:
        """Extract batting stats from IPL BattingCard data."""
        for batsman in batting_card:
            raw_name = batsman.get("PlayerName", "")
            if not raw_name:
                continue

            # Clean player name: remove role markers like "(RP)", "(C)", "(WK)"
            name = re.sub(r'\s*\([^)]*\)', '', raw_name).strip()
            if not name:
                continue

            if name not in player_stats:
                player_stats[name] = self.create_empty_player_stats(name)

            stats = player_stats[name]
            stats.runs += safe_int(batsman.get("Runs", 0))
            stats.balls_faced += safe_int(batsman.get("Balls", 0))
            stats.fours += safe_int(batsman.get("Fours", 0))
            stats.sixes += safe_int(batsman.get("Sixes", 0))

            # Determine if out
            out_desc = batsman.get("OutDesc", "")
            is_not_out = (
                not out_desc or
                "not out" in out_desc.lower() or
                out_desc.lower() == "batting"
            )
            if not is_not_out:
                stats.is_out = True

                # Check for LBW/Bowled (for bowler bonus)
                out_lower = out_desc.lower()
                is_lbw_bowled = "lbw" in out_lower or out_lower.startswith("b ")

                if is_lbw_bowled:
                    bowler_name_raw = batsman.get("BowlerName", "")
                    bowler_name = re.sub(
                        r'\s*\([^)]*\)', '', bowler_name_raw
                    ).strip()
                    if bowler_name:
                        if bowler_name not in player_stats:
                            player_stats[bowler_name] = (
                                self.create_empty_player_stats(bowler_name)
                            )
                        player_stats[bowler_name].lbw_bowled += 1

    def _extract_bowling_stats(
        self,
        bowling_card: List[Dict[str, Any]],
        player_stats: Dict[str, PlayerStats]
    ) -> None:
        """Extract bowling stats from IPL BowlingCard data."""
        for bowler in bowling_card:
            raw_name = bowler.get("PlayerShortName", "") or bowler.get("PlayerName", "")
            if not raw_name:
                continue

            name = re.sub(r'\s*\([^)]*\)', '', raw_name).strip()
            if not name:
                continue

            if name not in player_stats:
                player_stats[name] = self.create_empty_player_stats(name)

            stats = player_stats[name]
            stats.wickets += safe_int(bowler.get("Wickets", 0))
            stats.overs += cricket_overs_to_decimal(
                safe_float(bowler.get("Overs", 0))
            )
            stats.runs_conceded += safe_int(bowler.get("Runs", 0))
            stats.maidens += safe_int(bowler.get("Maidens", 0))
            stats.dot_balls += safe_int(bowler.get("DotBalls", 0))

    @staticmethod
    def _is_valid_fielder(fielder_name: str) -> bool:
        """Check if fielder name is valid (not a substitute placeholder)."""
        return bool(fielder_name) and fielder_name.lower() not in IGNORED_FIELDERS

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

    def _find_cricbuzz_match_id(
        self, home_team: str, away_team: str, match_number: str
    ) -> Optional[str]:
        """Find the Cricbuzz match ID for a given IPL match.

        Uses a two-step approach:
        1. Try the Cricbuzz series page for recent matches.
        2. If not found, predict the ID from a known base and verify
           by checking page size (valid scorecards are >400KB).

        Args:
            home_team: Home team code (e.g., 'CSK')
            away_team: Away team code (e.g., 'PBKS')
            match_number: Match number string (e.g., '7')

        Returns:
            Cricbuzz match ID string, or None if not found.
        """
        t1 = home_team.lower()
        t2 = away_team.lower()

        try:
            num = int(match_number)
        except (ValueError, TypeError):
            return None

        # Check cache first
        if match_number in self._cricbuzz_id_cache:
            return self._cricbuzz_id_cache[match_number]

        # Step 1: Check the series page for recent matches
        series_url = (
            f"https://www.cricbuzz.com/cricket-series/"
            f"{CRICBUZZ_IPL_SERIES_ID}/indian-premier-league-2026/matches"
        )
        response = self._make_request(series_url)
        if response:
            for ta, tb in [(t1, t2), (t2, t1)]:
                pattern = (
                    rf'/live-cricket-scores/(\d+)/'
                    rf'{ta}-vs-{tb}-{match_number}\w*-match'
                )
                match = re.search(pattern, response.text)
                if match:
                    self._cricbuzz_id_cache[match_number] = match.group(1)
                    return match.group(1)

        # Step 2: Predict ID and scan nearby range to find it
        predicted_id = CRICBUZZ_BASE_MATCH_ID + (num - 1) * CRICBUZZ_MATCH_ID_STEP

        slug = self._build_cricbuzz_slug(t1, t2, match_number)
        # Try predicted ID first, then scan ±10 around it
        candidates = [predicted_id]
        for offset in range(1, 11):
            candidates.append(predicted_id - offset)
            candidates.append(predicted_id + offset)

        for cb_id in candidates:
            url = f"{CRICBUZZ_SCORECARD_URL}/{cb_id}/{slug}"
            resp = self._make_request(url)
            if resp and len(resp.text) > CRICBUZZ_MIN_SCORECARD_SIZE:
                self._cricbuzz_id_cache[match_number] = str(cb_id)
                return str(cb_id)

        return None

    @staticmethod
    def _build_cricbuzz_slug(
        t1: str, t2: str, match_number: str
    ) -> str:
        """Build a Cricbuzz URL slug from team codes and match number.

        Args:
            t1: First team code lowercase (e.g., 'csk')
            t2: Second team code lowercase (e.g., 'pbks')
            match_number: Match number string (e.g., '7')

        Returns:
            URL slug string.
        """
        try:
            n = int(match_number)
        except (ValueError, TypeError):
            return f"{t1}-vs-{t2}-match-indian-premier-league-2026"

        if n % 10 == 1 and n % 100 != 11:
            suffix = "st"
        elif n % 10 == 2 and n % 100 != 12:
            suffix = "nd"
        elif n % 10 == 3 and n % 100 != 13:
            suffix = "rd"
        else:
            suffix = "th"

        return (
            f"{t1}-vs-{t2}-{n}{suffix}-match-"
            f"indian-premier-league-2026"
        )

    def _fetch_cricbuzz_runout_details(
        self, home_team: str, away_team: str, match_number: str
    ) -> Dict[str, List[str]]:
        """Fetch detailed run out fielder info from Cricbuzz scorecard.

        The IPL feed often only lists one fielder per run out even when
        multiple fielders were involved. Cricbuzz provides the full list
        (e.g., 'run out (Sarfaraz Khan/Ruturaj Gaikwad)').

        Only called when the current IPL feed data shows a run out.

        Args:
            home_team: Home team code (e.g., 'CSK')
            away_team: Away team code (e.g., 'PBKS')
            match_number: Match number string (e.g., '7')

        Returns:
            Dict mapping batter name (lowercase) to list of fielder names.
            Empty dict if fetch fails.
        """
        cb_id = self._find_cricbuzz_match_id(
            home_team, away_team, match_number
        )
        if not cb_id:
            logger.warning(
                f"Could not find Cricbuzz match ID for "
                f"{home_team} vs {away_team} Match {match_number}"
            )
            return {}

        t1 = home_team.lower()
        t2 = away_team.lower()
        slug = self._build_cricbuzz_slug(t1, t2, match_number)
        url = f"{CRICBUZZ_SCORECARD_URL}/{cb_id}/{slug}"
        response = self._make_request(url)
        if not response:
            return {}

        # Extract all "run out (fielder1/fielder2)" patterns with
        # the batter name from embedded JSON in the page
        result: Dict[str, List[str]] = {}
        for match in re.finditer(
            r'"batName"\s*:\s*"([^"]+)".*?'
            r'"outDesc"\s*:\s*"run out \(([^)]+)\)"',
            response.text,
        ):
            batter_name = match.group(1).strip()
            fielders = [f.strip() for f in match.group(2).split("/")]
            if len(fielders) >= 2:
                result[batter_name.lower()] = fielders

        # Fallback: extract from rendered HTML if JSON parsing missed any.
        # Note: HTML doesn't pair batter with fielders, so keys here are
        # fielder strings — only the secondary fielder-name lookup in
        # _extract_fielding_stats will match these entries.
        if not result:
            for match in re.finditer(
                r'run out \(([^)]+)\)', response.text
            ):
                fielders_str = match.group(1).strip()
                fielders = [f.strip() for f in fielders_str.split("/")]
                if len(fielders) >= 2:
                    result[fielders_str.lower()] = fielders

        if result:
            logger.info(
                f"Cricbuzz run out details for Match {match_number}: "
                f"{result}"
            )

        return result

    def _extract_fielding_stats(
        self,
        batting_card: List[Dict[str, Any]],
        player_stats: Dict[str, PlayerStats],
        cricbuzz_runouts: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        """Extract fielding stats from IPL dismissal descriptions.

        Args:
            batting_card: List of batting card entries from the feed.
            player_stats: Mutable dict of player stats to update.
            cricbuzz_runouts: Optional dict mapping batter name (lowercase)
                to full fielder list from Cricbuzz, used to supplement
                single-fielder run outs from the IPL feed.
        """
        for batsman in batting_card:
            out_desc = batsman.get("OutDesc", "")
            if not out_desc:
                continue

            # Caught & bowled
            cb_match = re.match(r'c\s*&\s*b\s+(.+)', out_desc)
            if cb_match:
                self._credit_fielding_action(
                    cb_match.group(1), player_stats, "catch"
                )
            else:
                # Regular catch
                catch_match = re.match(r'c\s+(.+?)\s+b\s+', out_desc)
                if catch_match:
                    self._credit_fielding_action(
                        catch_match.group(1), player_stats, "catch"
                    )

            # Stumping
            st_match = re.match(r'st\s+(.+?)\s+b\s+', out_desc)
            if st_match:
                self._credit_fielding_action(
                    st_match.group(1), player_stats, "stumping"
                )

            # Run out
            ro_match = re.search(r'run\s*out\s*\((.+?)\)', out_desc, re.IGNORECASE)
            if ro_match:
                fielders_str = ro_match.group(1)
                fielders = [f.strip() for f in fielders_str.split("/")]

                # If only 1 fielder from IPL feed, check Cricbuzz for
                # the full fielder list (IPL feed often drops 2nd fielder)
                if len(fielders) == 1 and cricbuzz_runouts:
                    batter_raw = batsman.get("PlayerName", "")
                    batter_clean = re.sub(
                        r'\s*\([^)]*\)', '', batter_raw
                    ).strip().lower()

                    # Try lookup by batter name first (normalize to
                    # handle name differences between feeds, e.g.,
                    # IPL "K L Rahul" vs Cricbuzz "KL Rahul")
                    batter_normalized = normalize_player_name(batter_clean)
                    cb_fielders = cricbuzz_runouts.get(batter_clean)
                    if not cb_fielders:
                        # Try normalized batter name against normalized keys
                        for key, flds in cricbuzz_runouts.items():
                            if normalize_player_name(key) == batter_normalized:
                                cb_fielders = flds
                                break

                    # Fallback: find entry where the IPL fielder appears
                    if not cb_fielders:
                        ipl_fielder = fielders[0].lower()
                        for key, cb_flds in cricbuzz_runouts.items():
                            if any(
                                ipl_fielder in f.lower()
                                for f in cb_flds
                            ):
                                cb_fielders = cb_flds
                                break

                    if cb_fielders and len(cb_fielders) >= 2:
                        logger.info(
                            f"Cricbuzz corrected run out for "
                            f"{batter_clean}: {fielders} -> {cb_fielders}"
                        )
                        fielders = cb_fielders

                if len(fielders) == 1:
                    # Solo run out - full credit (direct hit)
                    self._credit_fielding_action(
                        fielders[0], player_stats, "run_out_direct"
                    )
                elif len(fielders) >= 2:
                    # Multiple fielders involved - each gets indirect credit
                    for f in fielders:
                        self._credit_fielding_action(
                            f, player_stats, "run_out_indirect"
                        )

    # ==================== Override scrape_all_matches ====================

    def _parse_match_number(self, match_order: str) -> str:
        """Extract match number from schedule's MatchOrder field.

        Args:
            match_order: e.g. "Match 1", "Qualifier 1", "Final"

        Returns:
            Cleaned match number string.
        """
        if not match_order:
            return "Unknown"
        # "Match 1" -> "1", "Qualifier 1" -> "Qualifier 1"
        cleaned = match_order.replace("Match ", "").strip()
        return cleaned if cleaned else "Unknown"

    def scrape_all_matches(self) -> Dict[str, Any]:
        """Scrape all completed IPL matches with match numbers from schedule.

        Overrides base to use MatchOrder from the schedule feed,
        since the match summary feed has an empty MatchOrder.
        """
        from app.fantasy_calculator import calculate_fantasy_points

        urls_result = self.get_all_match_urls()
        if not urls_result.get("success"):
            return urls_result

        matches_data = urls_result.get("matches", [])
        all_player_stats: Dict[str, AggregatedPlayerStats] = {}
        matches_processed: List[Dict[str, Any]] = []

        for match_data in matches_data:
            url = match_data["url"]
            match_num = self._parse_match_number(
                match_data.get("match_order", "")
            )
            result = self.scrape_match_scorecard(url, match_number=match_num)
            if not result.success or not result.match_info:
                continue

            match_info = result.match_info
            matches_processed.append(match_info.to_dict())

            for player_name, stats in result.player_stats.items():
                if player_name not in all_player_stats:
                    all_player_stats[player_name] = AggregatedPlayerStats(
                        player_name=player_name
                    )

                fp_result = calculate_fantasy_points(
                    stats.to_dict(), played=True,
                    league=self.league_type.value
                )
                match_points = fp_result.get("total_points", 0)

                agg = all_player_stats[player_name]
                agg.matches_played += 1
                agg.total_runs += stats.runs
                agg.total_wickets += stats.wickets
                agg.total_catches += stats.catches
                agg.total_stumpings += stats.stumpings
                agg.total_run_outs += stats.run_outs_direct + stats.run_outs_indirect
                agg.total_fantasy_points += match_points

                agg.match_details.append({
                    "match": match_info.match_number,
                    "game_id": match_info.game_id,
                    "teams": match_info.teams_display,
                    "stats": stats.to_dict(),
                    "fantasy_points": match_points,
                    "breakdown": fp_result.get("breakdown", []),
                })

        return {
            "success": True,
            "matches_processed": matches_processed,
            "player_stats": {
                name: agg.to_dict()
                for name, agg in all_player_stats.items()
            },
            "total_matches": len(matches_processed),
        }
