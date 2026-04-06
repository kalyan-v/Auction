"""
Centralized constants and configuration values for the WPL Auction application.

This module contains all magic numbers, default values, and configuration
constants used throughout the application.
"""

from typing import Final

# ==================== TIMEZONE ====================
DEFAULT_TIMEZONE: Final[str] = 'America/Los_Angeles'

# ==================== AUCTION DEFAULTS ====================
DEFAULT_PURSE: Final[int] = 500_000_000           # 50 Crore default team budget
DEFAULT_BID_INCREMENT: Final[int] = 2_500_000     # 25 Lakh default bid increment
DEFAULT_AUCTION_TIMER: Final[int] = 600           # 10 minutes auction timer (seconds)
DEFAULT_MAX_SQUAD_SIZE: Final[int] = 20
DEFAULT_MIN_SQUAD_SIZE: Final[int] = 16

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

# ==================== IPL WEBSITE CONFIGURATION ====================
IPL_BASE_URL: Final[str] = "https://www.iplt20.com"
IPL_FEED_URL: Final[str] = "https://scores.iplt20.com/ipl/feeds"
IPL_COMPETITION_ID: Final[str] = "284"  # IPL 2026 season
CRICBUZZ_IPL_SERIES_ID: Final[str] = "9237"  # Cricbuzz series ID for IPL 2026
CRICBUZZ_SCORECARD_URL: Final[str] = "https://www.cricbuzz.com/live-cricket-scorecard"
CRICBUZZ_BASE_MATCH_ID: Final[int] = 149618  # Cricbuzz match ID for IPL 2026 Match 1
CRICBUZZ_MATCH_ID_STEP: Final[int] = 11      # Approximate ID increment between consecutive matches
CRICBUZZ_MIN_SCORECARD_SIZE: Final[int] = 400000  # bytes - valid scorecards are > 400KB

# IPL Team IDs mapping (from scores feeds)
IPL_TEAM_IDS: Final[dict] = {
    '13': 'CSK',   # Chennai Super Kings
    '14': 'DC',    # Delhi Capitals
    '15': 'GT',    # Gujarat Titans
    '16': 'KKR',   # Kolkata Knight Riders
    '17': 'LSG',   # Lucknow Super Giants
    '18': 'MI',    # Mumbai Indians
    '21': 'PBKS',  # Punjab Kings
    '22': 'RR',    # Rajasthan Royals
    '19': 'RCB',   # Royal Challengers Bengaluru
    '20': 'SRH',   # Sunrisers Hyderabad
}

# IPL Team code to URL slug mapping (for match URLs)
IPL_TEAM_CODE_TO_SLUG: Final[dict] = {
    'CSK': 'chennai-super-kings',
    'DC': 'delhi-capitals',
    'GT': 'gujarat-titans',
    'KKR': 'kolkata-knight-riders',
    'LSG': 'lucknow-super-giants',
    'MI': 'mumbai-indians',
    'PBKS': 'punjab-kings',
    'RR': 'rajasthan-royals',
    'RCB': 'royal-challengers-bengaluru',
    'SRH': 'sunrisers-hyderabad',
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
IPL_IMAGE_URL_TEMPLATE: Final[str] = "https://documents.iplt20.com/ipl/IPLHeadshot{series_id}/{player_id}.png"
IPL_HEADSHOT_YEAR: Final[str] = "2026"  # Year suffix for IPL headshot images on documents.iplt20.com

# ==================== LEAGUE IMAGE CONFIG ====================
# Maps league type to image URL template and series ID
LEAGUE_IMAGE_CONFIG: Final[dict] = {
    'wpl': {
        'template': WPL_IMAGE_URL_TEMPLATE,
        'series_id': WPL_SERIES_ID,
    },
    'ipl': {
        'template': IPL_IMAGE_URL_TEMPLATE,
        'series_id': IPL_HEADSHOT_YEAR,
        'fallback_series_ids': ['2025', '2024'],
    },
}
