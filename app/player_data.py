"""
Unified player data module for the WPL Auction application.

Contains all player-related mappings, name variations, and categorizations
used for matching players across different data sources.
"""

from typing import Final, FrozenSet, Dict, Optional


# ==================== LEAGUE PLAYER ID REGISTRY ====================
# Maps league_type -> player ID dict for image fetching
# This is populated after the individual dicts are defined below
_LEAGUE_PLAYER_IDS: Dict[str, Dict[str, int]] = {}


def get_player_id_for_league(player_name: str, league_type: str) -> Optional[int]:
    """Get player ID for image fetching based on league type.

    Args:
        player_name: The player's name (case-sensitive).
        league_type: The league type ('wpl', 'ipl', etc.).

    Returns:
        Player ID if found, None otherwise.
    """
    player_ids = _LEAGUE_PLAYER_IDS.get(league_type, {})
    return player_ids.get(player_name.strip())

# ==================== IPL PLAYER IDS ====================
# Player ID mapping from iplt20.com for image fetching
# Format: 'Database Name': IPL_Player_ID
# To be populated with IPL 2026 player data

IPL_PLAYER_IDS: Final[Dict[str, int]] = {
    # Add IPL player name -> player ID mappings here
}


# ==================== WPL PLAYER IDS ====================
# Player ID mapping from wplt20.com squad pages for image fetching
# Format: 'Database Name': WPL_Player_ID

WPL_PLAYER_IDS: Final[Dict[str, int]] = {
    # Mumbai Indians
    'Harmanpreet Kaur': 59348,
    'Amanjot Kaur': 75657,
    'Amelia Kerr': 66632,
    'Hayley Matthews': 64970,
    'Nalla Reddy': 83685,
    'Natalie Sciver-Brunt': 63998,
    'Nicola Carey': 63267,
    'Poonam Khemnar': 71472,
    'Sajeevan Sajana': 84022,
    'Sanskriti Gupta': 84334,
    'Triveni Vasistha': 83731,
    'G. Kamalini': 108890,
    'G. Kamlini': 108890,
    'Rahila Firdous': 75635,
    'Milly Illingworth': 100377,
    'Saika Ishaque': 100194,
    'Shabnim Ismail': 6658,

    # Delhi Capitals
    'Deeya Yadav': 117710,
    'Jemimah Rodrigues': 68442,
    'Laura Wolvaardt': 66176,
    'Shafali Verma': 70772,
    'Chinelle Henry': 64347,
    'Marizanne Kapp': 7759,
    'Minnu Mani': 70723,
    'N. Charani': 89194,
    'Niki Prasad': 99166,
    'Sneh Rana': 64550,
    'Lizelle Lee': 64192,
    'Mamatha Madiwala': 89202,
    'Taniya Bhatia': 68443,
    'Taniyaa Bhatia': 68443,
    'Alana King': 67057,
    'Lucy Hamilton': 100376,
    'Nandni Sharma': 75642,

    # Gujarat Giants
    'Anushka Sharma': 84308,
    'Bharti Fulmali': 70708,
    'Danni Wyatt-Hodge': 59131,
    'Danni Wyatt': 59131,
    'Ashleigh Gardner': 67023,
    'Ayushi Soni': 81824,
    'Georgia Wareham': 67047,
    'Kanika Ahuja': 84086,
    'Kim Garth': 19948,
    'Sophie Devine': 62067,
    'Tanuja Kanwer': 70721,
    'Beth Mooney': 64853,
    'Shivani Singh': 84013,
    'Yastika Bhatia': 73424,
    'Happy Kumari': 129259,
    'Kashvee Gautam': 75656,
    'Rajeshwari Gayakwad': 64549,
    'Renuka Singh': 70714,
    'Titas Sadhu': 83663,

    # Royal Challengers Bengaluru
    'Georgia Voll': 75001,
    'Smriti Mandhana': 63992,
    'Arundhati Reddy': 70064,
    'Dayalan Hemalatha': 69399,
    'Gautami Naik': 93529,
    'Grace Harris': 65633,
    'Nadine de Klerk': 67302,
    'Pooja Vastrakar': 68423,
    'Prema Rawat': 112786,
    'Radha Yadav': 68441,
    'Sayali Satghare': 83633,
    'Sayali Satghare ': 83633,  # With trailing space (data quality issue)
    'Shreyanka Patil': 75598,
    'Prathyoosha Kumar': 82877,
    'Richa Ghosh': 74530,
    'Lauren Bell': 69906,
    'Linsey Smith': 69760,

    # UP Warriorz
    'Kiran Navgire': 71461,
    'Meg Lanning': 57908,
    'Phoebe Litchfield': 71357,
    'Shweta Sehrawat': 83619,
    'Simran Shaikh': 83648,
    'Asha Sobhana': 75591,
    'Chloe Tryon': 11858,
    'Deandra Dottin': 59467,
    'Deepti Sharma': 65146,
    'Harleen Deol': 70726,
    'Kranti Goud': 84330,
    'Kranti Gaud': 84330,
    'Pratika Rawal': 83623,
    'Shikha Pandey': 64755,
    'Shipra Giri': 84241,
    'Sophie Ecclestone': 66391,
    'Suman Meena': 83897,
    'Gongadi Trisha': 83660,
    'Trisha Gongadi': 83660,
    'Charli Knott': 70455,
}


# ==================== NAME MAPPINGS ====================
# WPL website name -> Database name mappings for known variations
# Used when matching scraped data to database records

NAME_MAPPINGS: Final[Dict[str, str]] = {
    # Full name to short name
    'renuka singh thakur': 'renuka singh',
    'nat sciver-brunt': 'natalie sciver-brunt',

    # Name order variations
    'sajana sajeevan': 'sajeevan sajana',
    'trisha gongadi': 'gongadi trisha',

    # Spelling variations
    'sree charani': 'shree charani',
    'nandni sharma': 'nandani sharma',
    'kranti gaud': 'kranti goud',

    # Initial format variations
    'g kamalini': 'g. kamlini',
    'g kamlini': 'g. kamlini',
    'n charani': 'n. charani',

    # Nickname to full name
    'danni wyatt': 'danni wyatt-hodge',

    # Other variations
    'taniyaa bhatia': 'taniya bhatia',
}


# ==================== KNOWN BOWLERS ====================
# Players classified as bowlers (exempt from duck penalty in fantasy scoring)
# Names should be lowercase for case-insensitive matching

KNOWN_BOWLERS: Final[FrozenSet[str]] = frozenset({
    # India bowlers
    'renuka singh thakur',
    'renuka singh',
    'titas sadhu',
    'arundhati reddy',
    'shikha pandey',
    'rajeshwari gayakwad',
    'poonam khemnar',
    'prathyoosha kumar',
    'bharti fulmali',
    'shreyanka patil',
    'asha sobhana',
    'kashvee gautam',

    # Overseas bowlers
    'shabnim ismail',
    'saika ishaque',
    'sophie ecclestone',
    'alana king',
    'georgia wareham',
    'lauren bell',
    'linsey smith',
    'kim garth',
})


# ==================== POPULATE LEAGUE REGISTRY ====================
_LEAGUE_PLAYER_IDS['wpl'] = WPL_PLAYER_IDS
_LEAGUE_PLAYER_IDS['ipl'] = IPL_PLAYER_IDS
