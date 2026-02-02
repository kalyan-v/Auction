"""
Data classes for structured data in the WPL Auction application.

Provides type-safe data structures for player stats, match info, and scraping results.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.enums import PlayerPosition


@dataclass
class PlayerStats:
    """Player statistics for a single match."""
    # Batting
    runs: int = 0
    balls_faced: int = 0
    fours: int = 0
    sixes: int = 0
    is_out: bool = False

    # Bowling
    wickets: int = 0
    overs: float = 0.0
    runs_conceded: int = 0
    maidens: int = 0
    dot_balls: int = 0
    lbw_bowled: int = 0  # Wickets via LBW or bowled (for bonus)

    # Fielding
    catches: int = 0
    stumpings: int = 0
    run_outs_direct: int = 0
    run_outs_indirect: int = 0

    # Metadata
    position: PlayerPosition = PlayerPosition.ALLROUNDER

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility with existing code."""
        return {
            "runs": self.runs,
            "balls_faced": self.balls_faced,
            "fours": self.fours,
            "sixes": self.sixes,
            "is_out": self.is_out,
            "wickets": self.wickets,
            "overs": self.overs,
            "runs_conceded": self.runs_conceded,
            "maidens": self.maidens,
            "dot_balls": self.dot_balls,
            "lbw_bowled": self.lbw_bowled,
            "catches": self.catches,
            "stumpings": self.stumpings,
            "run_outs_direct": self.run_outs_direct,
            "run_outs_indirect": self.run_outs_indirect,
            "position": self.position.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlayerStats":
        """Create from dictionary."""
        position = data.get("position", "Allrounder")
        if isinstance(position, str):
            position = PlayerPosition.from_string(position)
        return cls(
            runs=data.get("runs", 0),
            balls_faced=data.get("balls_faced", 0),
            fours=data.get("fours", 0),
            sixes=data.get("sixes", 0),
            is_out=data.get("is_out", False),
            wickets=data.get("wickets", 0),
            overs=data.get("overs", 0.0),
            runs_conceded=data.get("runs_conceded", 0),
            maidens=data.get("maidens", 0),
            dot_balls=data.get("dot_balls", 0),
            lbw_bowled=data.get("lbw_bowled", 0),
            catches=data.get("catches", 0),
            stumpings=data.get("stumpings", 0),
            run_outs_direct=data.get("run_outs_direct", 0),
            run_outs_indirect=data.get("run_outs_indirect", 0),
            position=position,
        )


@dataclass
class MatchInfo:
    """Information about a cricket match."""
    match_number: str
    home_team: str
    away_team: str
    date: str = ""
    venue: str = ""
    result: str = ""
    url: str = ""
    game_id: str = ""  # Unique identifier from the source website

    @property
    def teams_display(self) -> str:
        """Get formatted team display string."""
        return f"{self.home_team} vs {self.away_team}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "match_number": self.match_number,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "date": self.date,
            "venue": self.venue,
            "result": self.result,
            "url": self.url,
            "game_id": self.game_id,
            "teams": self.teams_display,
        }


@dataclass
class LeaderboardEntry:
    """Entry in a statistics leaderboard."""
    player_id: str
    player_name: str
    team_name: str = ""
    team_short_name: str = ""
    matches_played: int = 0
    # Stat-specific fields stored as extras
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "team_name": self.team_name,
            "team_short_name": self.team_short_name,
            "matches_played": self.matches_played,
        }
        result.update(self.stats)
        return result


@dataclass
class ScorecardResult:
    """Result of scraping a match scorecard."""
    success: bool
    match_info: Optional[MatchInfo] = None
    player_stats: Dict[str, PlayerStats] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        if not self.success:
            return {"success": False, "error": self.error or "Unknown error"}
        return {
            "success": True,
            "match_info": self.match_info.to_dict() if self.match_info else {},
            "player_stats": {
                name: stats.to_dict()
                for name, stats in self.player_stats.items()
            },
        }


@dataclass
class StatsResult:
    """Result of scraping statistics."""
    success: bool
    stat_type: str = ""
    players: List[LeaderboardEntry] = field(default_factory=list)
    error: Optional[str] = None
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        if not self.success:
            return {"success": False, "error": self.error or "Unknown error"}
        return {
            "success": True,
            "stat_type": self.stat_type,
            "players": [p.to_dict() for p in self.players],
            "source": self.source,
        }

    @property
    def leader(self) -> Optional[LeaderboardEntry]:
        """Get the leader (first player) from the list."""
        return self.players[0] if self.players else None


@dataclass
class PointsTableEntry:
    """Entry in the points table."""
    team_name: str
    team_short_name: str
    played: int = 0
    won: int = 0
    lost: int = 0
    tied: int = 0
    no_result: int = 0
    points: int = 0
    nrr: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "team_name": self.team_name,
            "team_short_name": self.team_short_name,
            "played": self.played,
            "won": self.won,
            "lost": self.lost,
            "tied": self.tied,
            "no_result": self.no_result,
            "points": self.points,
            "nrr": self.nrr,
        }


@dataclass
class AggregatedPlayerStats:
    """Aggregated statistics across multiple matches."""
    player_name: str
    matches_played: int = 0
    total_runs: int = 0
    total_wickets: int = 0
    total_catches: int = 0
    total_stumpings: int = 0
    total_run_outs: int = 0
    total_fantasy_points: float = 0
    match_details: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "matches_played": self.matches_played,
            "total_runs": self.total_runs,
            "total_wickets": self.total_wickets,
            "total_catches": self.total_catches,
            "total_stumpings": self.total_stumpings,
            "total_run_outs": self.total_run_outs,
            "total_fantasy_points": self.total_fantasy_points,
            "matches": self.match_details,
        }
