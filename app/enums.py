"""
Enums for the WPL Auction application.

Provides type-safe constants for player positions, statuses, and award types.
"""

from enum import Enum


class PlayerPosition(str, Enum):
    """Player positions in cricket."""
    BATTER = "Batter"
    BOWLER = "Bowler"
    ALLROUNDER = "Allrounder"
    KEEPER = "Keeper"


class AwardType(str, Enum):
    """Fantasy award types."""
    MVP = "mvp"
    ORANGE_CAP = "orange_cap"
    PURPLE_CAP = "purple_cap"


class LeagueType(str, Enum):
    """Supported cricket leagues for scraping."""
    WPL = "wpl"
    IPL = "ipl"


