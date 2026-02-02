"""
Enums for the WPL Auction application.

Provides type-safe constants for player positions, statuses, and award types.
"""

from enum import Enum, auto


class PlayerPosition(str, Enum):
    """Player positions in cricket."""
    BATTER = "Batter"
    BOWLER = "Bowler"
    ALLROUNDER = "Allrounder"
    KEEPER = "Keeper"

    @classmethod
    def from_string(cls, value: str) -> "PlayerPosition":
        """Convert string to PlayerPosition, defaulting to ALLROUNDER."""
        value_lower = value.lower().strip()
        mapping = {
            "batter": cls.BATTER,
            "batsman": cls.BATTER,
            "bowler": cls.BOWLER,
            "allrounder": cls.ALLROUNDER,
            "all-rounder": cls.ALLROUNDER,
            "keeper": cls.KEEPER,
            "wicketkeeper": cls.KEEPER,
            "wk": cls.KEEPER,
        }
        return mapping.get(value_lower, cls.ALLROUNDER)


class PlayerStatus(str, Enum):
    """Player auction status."""
    AVAILABLE = "available"
    SOLD = "sold"
    UNSOLD = "unsold"
    BIDDING = "bidding"


class AwardType(str, Enum):
    """Fantasy award types."""
    MVP = "mvp"
    ORANGE_CAP = "orange_cap"
    PURPLE_CAP = "purple_cap"


class LeagueType(str, Enum):
    """Supported cricket leagues for scraping."""
    WPL = "wpl"
    IPL = "ipl"
    BBL = "bbl"
    PSL = "psl"
    # Add more leagues as needed

    @property
    def display_name(self) -> str:
        """Get human-readable league name."""
        names = {
            LeagueType.WPL: "Women's Premier League",
            LeagueType.IPL: "Indian Premier League",
            LeagueType.BBL: "Big Bash League",
            LeagueType.PSL: "Pakistan Super League",
        }
        return names.get(self, self.value.upper())


class DismissalType(str, Enum):
    """Types of cricket dismissals."""
    BOWLED = "bowled"
    CAUGHT = "caught"
    CAUGHT_AND_BOWLED = "caught_and_bowled"
    LBW = "lbw"
    RUN_OUT = "run_out"
    STUMPED = "stumped"
    HIT_WICKET = "hit_wicket"
    NOT_OUT = "not_out"
