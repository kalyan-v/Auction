"""
Base scraper abstract class.

Defines the interface that all league-specific scrapers must implement.
This allows easy addition of new leagues (IPL, BBL, etc.) in the future.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set

import requests

from app.dataclasses import (
    AggregatedPlayerStats,
    LeaderboardEntry,
    MatchInfo,
    PlayerStats,
    PointsTableEntry,
    ScorecardResult,
    StatsResult,
)
from app.enums import LeagueType, PlayerPosition
from app.logger import get_logger

logger = get_logger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for cricket league scrapers.

    Subclasses must implement the abstract methods to provide
    league-specific scraping logic.

    Example usage:
        scraper = WPLScraper()
        orange_cap = scraper.get_orange_cap()
        matches = scraper.get_all_matches()
    """

    # Default request settings (can be overridden by subclasses)
    DEFAULT_TIMEOUT: int = 15
    DEFAULT_HEADERS: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self) -> None:
        """Initialize the scraper."""
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        """Get or create a requests session for connection reuse."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(self.DEFAULT_HEADERS)
        return self._session

    # ==================== Abstract Properties ====================

    @property
    @abstractmethod
    def league_type(self) -> LeagueType:
        """Return the league type this scraper handles."""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the base URL for this league's website."""
        pass

    @property
    @abstractmethod
    def series_id(self) -> str:
        """Return the current series/season ID."""
        pass

    @property
    @abstractmethod
    def known_bowlers(self) -> Set[str]:
        """
        Return set of known bowler names (lowercase).

        Used for duck penalty exemption in fantasy scoring.
        """
        pass

    @property
    @abstractmethod
    def name_mappings(self) -> Dict[str, str]:
        """
        Return name mappings for player name normalization.

        Maps website names to database names.
        """
        pass

    @property
    @abstractmethod
    def team_mappings(self) -> Dict[str, str]:
        """
        Return team ID/code to display name mappings.
        """
        pass

    # ==================== Abstract Methods ====================

    @abstractmethod
    def get_orange_cap(self) -> StatsResult:
        """
        Get the Orange Cap (most runs) leader.

        Returns:
            StatsResult with the runs leaderboard
        """
        pass

    @abstractmethod
    def get_purple_cap(self) -> StatsResult:
        """
        Get the Purple Cap (most wickets) leader.

        Returns:
            StatsResult with the wickets leaderboard
        """
        pass

    @abstractmethod
    def get_mvp(self) -> StatsResult:
        """
        Get the MVP (most valuable player).

        Returns:
            StatsResult with the MVP leaderboard
        """
        pass

    @abstractmethod
    def get_points_table(self) -> Dict[str, Any]:
        """
        Get the league points table.

        Returns:
            Dict with success status and list of PointsTableEntry
        """
        pass

    @abstractmethod
    def get_all_match_urls(self) -> Dict[str, Any]:
        """
        Get URLs for all completed matches.

        Returns:
            Dict with success status and list of match URLs/info
        """
        pass

    @abstractmethod
    def scrape_match_scorecard(self, match_url: str) -> ScorecardResult:
        """
        Scrape detailed scorecard from a match page.

        Args:
            match_url: URL of the match page

        Returns:
            ScorecardResult with player stats
        """
        pass

    # ==================== Concrete Methods ====================

    def get_player_position(self, player_name: str) -> PlayerPosition:
        """
        Determine player position based on known bowlers list.

        Args:
            player_name: Player name to check

        Returns:
            PlayerPosition.BOWLER if known bowler, else ALLROUNDER
        """
        if player_name.lower().strip() in self.known_bowlers:
            return PlayerPosition.BOWLER
        return PlayerPosition.ALLROUNDER

    def normalize_player_name(self, name: str) -> str:
        """
        Normalize a player name using mappings.

        Args:
            name: Raw player name from website

        Returns:
            Normalized name for database matching
        """
        normalized = name.strip().lower()
        return self.name_mappings.get(normalized, normalized)

    def create_empty_player_stats(self, player_name: str = "") -> PlayerStats:
        """
        Create an empty PlayerStats object with position detection.

        Args:
            player_name: Player name for position detection

        Returns:
            PlayerStats with default values and detected position
        """
        return PlayerStats(position=self.get_player_position(player_name))

    def scrape_all_matches(self) -> Dict[str, Any]:
        """
        Scrape all completed matches and aggregate player stats.

        This method uses get_all_match_urls() and scrape_match_scorecard()
        to build a complete picture of all player performances.

        Returns:
            Dict with aggregated player stats and match info
        """
        from app.fantasy_calculator import calculate_fantasy_points

        urls_result = self.get_all_match_urls()
        if not urls_result.get("success"):
            return urls_result

        match_urls = urls_result.get("match_urls", [])
        all_player_stats: Dict[str, AggregatedPlayerStats] = {}
        matches_processed: List[Dict[str, Any]] = []

        for url in match_urls:
            result = self.scrape_match_scorecard(url)
            if not result.success or not result.match_info:
                continue

            match_info = result.match_info
            matches_processed.append(match_info.to_dict())

            for player_name, stats in result.player_stats.items():
                if player_name not in all_player_stats:
                    all_player_stats[player_name] = AggregatedPlayerStats(
                        player_name=player_name
                    )

                # Calculate fantasy points
                fp_result = calculate_fantasy_points(stats.to_dict(), played=True)
                match_points = fp_result.get("total_points", 0)

                # Aggregate stats
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

    def _make_request(
        self,
        url: str,
        timeout: Optional[int] = None
    ) -> Optional[requests.Response]:
        """
        Make an HTTP GET request with error handling.

        Args:
            url: URL to request
            timeout: Request timeout (uses default if not specified)

        Returns:
            Response object or None if request failed
        """
        try:
            response = self.session.get(
                url,
                timeout=timeout or self.DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    def close(self) -> None:
        """Close the requests session."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self) -> "BaseScraper":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close session."""
        self.close()
