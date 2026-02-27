"""
Centralized constants and configuration values for the WPL Auction application.

This module contains all magic numbers, default values, and configuration
constants used throughout the application.
"""

from typing import Final

# ==================== TIMEZONE ====================
DEFAULT_TIMEZONE: Final[str] = 'America/Los_Angeles'

# ==================== HTTP REQUEST SETTINGS ====================
IMAGE_REQUEST_TIMEOUT: Final[int] = 15    # seconds
WIKI_REQUEST_TIMEOUT: Final[int] = 10     # seconds

# ==================== WPL WEBSITE CONFIGURATION ====================
WPL_BASE_URL: Final[str] = "https://www.wplt20.com"
WPL_SERIES_ID: Final[str] = "13458"  # WPL 2026 season

# WPL Team IDs mapping
WPL_TEAM_IDS: Final[dict] = {
    '3513': 'RCB',   # Royal Challengers Bengaluru
    '3514': 'DC',    # Delhi Capitals
    '3515': 'GG',    # Gujarat Giants
    '3516': 'UPW',   # UP Warriorz
    '3517': 'MI',    # Mumbai Indians
}

# Team code to URL slug mapping
TEAM_CODE_TO_SLUG: Final[dict] = {
    'min': 'mumbai-indians',
    'blr': 'royal-challengers-bengaluru',
    'lsg': 'up-warriorz',
    'ggw': 'gujarat-giants',
    'dcw': 'delhi-capitals',
}

# WPL Stats URL patterns
WPL_STATS_URL_PATTERNS: Final[dict] = {
    'most-runs': '/stats/most-runs-2-{series_id}-statistics',
    'most-wickets': '/stats/most-wickets-13-{series_id}-statistics',
    'mvp': '/stats/most-valuable-player-34-{series_id}-statistics',
    'most-sixes': '/stats/most-6s-8-{series_id}-statistics',
    'most-fours': '/stats/most-4s-7-{series_id}-statistics',
    'highest-score': '/stats/highest-score-1-{series_id}-statistics',
    'best-average': '/stats/best-batting-average-3-{series_id}-statistics',
    'best-strike-rate': '/stats/best-batting-strike-rate-4-{series_id}-statistics',
    'most-fifties': '/stats/most-fifties-5-{series_id}-statistics',
    'best-bowling-average': '/stats/best-bowling-average-15-{series_id}-statistics',
    'best-economy': '/stats/best-economy-rates-16-{series_id}-statistics',
    'best-bowling-figures': '/stats/best-bowling-figures-12-{series_id}-statistics',
}

# ==================== HTTP HEADERS ====================
WIKI_HEADERS: Final[dict] = {
    'User-Agent': 'WPLAuctionApp/1.0 (https://github.com/auction; auction@example.com) python-requests'
}

# ==================== PLAYOFF MATCH NUMBERS ====================
# Playoff matches use special match numbers to distinguish from league matches
# These high numbers ensure no collision with regular league matches (1-70+)
PLAYOFF_MATCH_NUMBERS: Final[dict] = {
    'eliminator': 100,
    'qualifier 1': 101,
    'qualifier1': 101,
    'qualifier 2': 102,
    'qualifier2': 102,
    'final': 200,
}

# ==================== IMAGE SETTINGS ====================
MIN_VALID_IMAGE_SIZE: Final[int] = 1000  # bytes - images smaller than this are likely invalid
WPL_IMAGE_URL_TEMPLATE: Final[str] = "https://www.wplt20.com/static-assets/images/players/series/{series_id}/{player_id}.png"
IPL_IMAGE_URL_TEMPLATE: Final[str] = "https://www.iplt20.com/static-assets/images/players/series/{series_id}/{player_id}.png"

# ==================== LEAGUE IMAGE CONFIG ====================
# Maps league type to image URL template and series ID
LEAGUE_IMAGE_CONFIG: Final[dict] = {
    'wpl': {
        'template': WPL_IMAGE_URL_TEMPLATE,
        'series_id': WPL_SERIES_ID,
    },
    'ipl': {
        'template': IPL_IMAGE_URL_TEMPLATE,
        'series_id': '',  # Set when IPL 2026 series ID is known
    },
}
