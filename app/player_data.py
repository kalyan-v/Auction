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
        player_name: The player's name (case-insensitive).
        league_type: The league type ('wpl', 'ipl', etc.).

    Returns:
        Player ID if found, None otherwise.
    """
    player_ids = _LEAGUE_PLAYER_IDS.get(league_type, {})
    # Try exact match first, then case-insensitive fallback
    name = player_name.strip()
    result = player_ids.get(name)
    if result is not None:
        return result
    # Case-insensitive lookup
    name_lower = name.lower()
    for key, value in player_ids.items():
        if key.lower() == name_lower:
            return value
    return None

# ==================== IPL PLAYER IDS ====================
# Headshot ID mapping from iplt20.com squad pages for image fetching
# These IDs correspond to IPLHeadshot images on documents.iplt20.com
# Format: 'Database Name': IPL_Headshot_ID

IPL_PLAYER_IDS: Final[Dict[str, int]] = {
    # CSK
    'Akeal Hosein': 722,
    'Aman Khan': 979,
    'Anshul Kamboj': 3106,
    'Ayush Mhatre': 3497,
    'Dewald Brevis': 797,
    'Gurjapneet Singh': 2256,
    'Jamie Overton': 1216,
    'Kartik Sharma': 4540,
    'Khaleel Ahmed': 8,
    'MS Dhoni': 57,
    'Matt Henry': 71,
    'Matthew William Short': 2032,
    'Mukesh Choudhary': 970,
    'Noor Ahmad': 975,
    'Prashant Veer': 4541,
    'Rahul Chahar': 171,
    'Ramakrishna Ghosh': 3559,
    'Ruturaj Gaikwad': 102,
    'Sanju Samson': 190,
    'Sarfaraz Khan': 139,
    'Shivam Dube': 211,
    'Shreyas Gopal': 192,
    'Urvil Patel': 1486,
    'Zak Foulkes': 3493,

    # DC
    'Abishek Porel': 1580,
    'Ajay Mandal': 1931,
    'Ashutosh Sharma': 3109,
    'Axar Patel': 110,
    'Dushmantha Chameera': 608,
    'KL Rahul': 19,
    'Karun Nair': 131,
    'Kuldeep Yadav': 14,
    'Lungisani Ngidi': 99,
    'Madhav Tiwari': 3561,
    'Mitchell Starc': 31,
    'Mukesh Kumar': 1462,
    'Prithvi Shaw': 51,
    'Sameer Rizvi': 1229,
    'T. Natarajan': 224,
    'Tripurana Vijay': 3563,
    'Tristan Stubbs': 1017,
    'Vipraj Nigam': 3560,

    # GT
    'Anuj Rawat': 534,
    'Glenn Phillips': 635,
    'Gurnoor Singh Brar': 1231,
    'Ishant Sharma': 50,
    'Jayant Yadav': 165,
    'Jos Buttler': 182,
    'Kagiso Rabada': 116,
    'Kumar Kushagra': 3101,
    'Manav Suthar': 2443,
    'Mohammed Siraj': 63,
    'Mohd. Arshad Khan': 988,
    'Nishant Sindhu': 791,
    'Prasidh Krishna': 150,
    'Rahul Tewatia': 120,
    'Rashid Khan': 218,
    'Sai Kishore': 544,
    'Sai Sudharsan': 976,
    'Shahrukh Khan': 590,
    'Shubman Gill': 62,
    'Washington Sundar': 20,

    # KKR
    'Ajinkya Rahane': 44,
    'Angkrish Raghuvanshi': 787,
    'Anukul Roy': 160,
    'Blessing Muzarabani': 827,
    'Cameron Green': 550,
    'Daksh Kamra': 4548,
    'Finn Allen': 595,
    'Kartik Tyagi': 536,
    'Manish Pandey': 16,
    'Navdeep Saini': 207,
    'Prashant Solanki': 972,
    'Rachin Ravindra': 724,
    'Rahul Tripathi': 188,
    'Ramandeep Singh': 991,
    'Rinku Singh': 152,
    'Rovman Powell': 329,
    'Sarthak Ranjan': 4203,
    'Saurabh Dubey': 1010,
    'Sunil Narine': 156,
    'Tejasvi Singh': 4281,
    'Tim Seifert': 82,
    'Umran Malik': 637,
    'Vaibhav Arora': 583,
    'Varun Chakaravarthy': 140,

    # LSG
    'Abdul Samad': 525,
    'Aiden Markram': 287,
    'Akash Singh': 535,
    'Arshin Kulkarni': 2788,
    'Avesh Khan': 109,
    'Ayush Badoni': 985,
    'Digvesh Singh': 3565,
    'Himmat Singh': 203,
    'M. Siddharth': 532,
    'Matthew Breetzke': 2805,
    'Mayank Yadav': 987,
    'Mitchell Marsh': 40,
    'Mohsin Khan': 541,
    'Nicholas Pooran': 136,
    'Prince Yadav': 1225,
    'Rishabh Pant': 18,
    'Shahbaz Ahamad': 523,

    # MI
    'Allah Ghazanfar': 2761,
    'Ashwani Kumar': 3569,
    'Atharva Ankolekar': 4544,
    'Corbin Bosch': 1041,
    'Danish Malewar': 4546,
    'Deepak Chahar': 91,
    'Hardik Pandya': 54,
    'Jasprit Bumrah': 9,
    'Mayank Markande': 87,
    'Mayank Rawat': 1228,
    'Mitchell Santner': 75,
    'Mohammad Izhar': 4545,
    'N. Tilak Varma': 993,
    'Naman Dhir': 3107,
    'Quinton de Kock': 170,
    'Raghu Sharma': 3869,
    'Raj Angad Bawa': 781,
    'Robin Minz': 3103,
    'Rohit Sharma': 6,
    'Ryan Rickelton': 743,
    'Shardul Thakur': 105,
    'Sherfane Rutherford': 122,
    'Surya Kumar Yadav': 174,
    'Trent Boult': 66,
    'Will Jacks': 1941,

    # PBKS
    'Arshdeep Singh': 125,
    'Azmatullah Omarzai': 1354,
    'Harnoor Pannu': 784,
    'Harpreet Brar': 130,
    'Marco Jansen': 586,
    'Marcus Stoinis': 23,
    'Mitch Owen': 3870,
    'Musheer Khan': 2813,
    'Nehal Wadhera': 1541,
    'Prabhsimran Singh': 137,
    'Pravin Dubey': 548,
    'Priyansh Arya': 3571,
    'Pyla Avinash': 3573,
    'Shashank Singh': 191,
    'Shreyas Iyer': 12,
    'Suryansh Shedge': 2146,
    'Vishnu Vinod': 581,
    'Vyshak Vijaykumar': 2034,
    'Xavier Bartlett': 3572,
    'Yash Thakur': 1550,
    'Yuzvendra Chahal': 10,

    # RR
    'Adam Milne': 157,
    'Aman Rao Perala': 4552,
    'Brijesh Sharma': 4551,
    'Dasun Shanaka': 375,
    'Dhruv Jurel': 1004,
    'Donovan Ferreira': 2033,
    'Jofra Archer': 181,
    'Kuldeep Sen': 1005,
    'Kwena Maphaka': 801,
    'Lhuan-dre Pretorious': 2827,
    'Nandre Burger': 2806,
    'Ravi Bishnoi': 520,
    'Ravi Singh': 4550,
    'Ravindra Jadeja': 46,
    'Riyan Parag': 189,
    'Sandeep Sharma': 220,
    'Shimron Hetmyer': 210,
    'Shubham Dubey': 3112,
    'Sushant Mishra': 1016,
    'Tushar Deshpande': 539,
    'Vaibhav Suryavanshi': 3498,
    'Vignesh Puthur': 3566,
    'Yash Raj Punja': 4553,
    'Yashasvi Jaiswal': 533,
    'Yudhvir Singh Charak': 587,

    # RCB
    'Abhinandan Singh': 3574,
    'Bhuvneshwar Kumar': 15,
    'Devdutt Padikkal': 200,
    'Jacob Bethell': 869,
    'Jacob Duffy': 1701,
    'Jitesh Sharma': 1000,
    'Jordan Cox': 3372,
    'Josh Hazlewood': 36,
    'Kanishk Chouhan': 4016,
    'Krunal Pandya': 17,
    'Mangesh Yadav': 4554,
    'Nuwan Thushara': 813,
    'Phil Salt': 1220,
    'Rajat Patidar': 597,
    'Rasikh Dar': 172,
    'Romario Shepherd': 371,
    'Satvik Deswal': 4555,
    'Suyash Sharma': 1932,
    'Swapnil Singh': 1483,
    'Tim David': 636,
    'Venkatesh Iyer': 584,
    'Vicky Ostwal': 786,
    'Vihaan Malhotra': 4012,
    'Virat Kohli': 2,
    'Yash Dayal': 978,

    # SRH
    'Abhishek Sharma': 212,
    'Amit Kumar': 4559,
    'Aniket Verma': 3576,
    'Brydon Carse': 1221,
    'David Payne': 5007,
    'Eshan Malinga': 3339,
    'Harsh Dubey': 1494,
    'Harshal Patel': 114,
    'Heinrich Klaasen': 202,
    'Ishan Kishan': 164,
    'Jaydev Unadkat': 180,
    'Kamindu Mendis': 627,
    'Krains Fuletra': 4557,
    'Liam Livingstone': 183,
    'Nitish Kumar Reddy': 1944,
    'Onkar Tarmale': 4560,
    'Pat Cummins': 33,
    'Praful Hinge': 4558,
    'Sakib Hussain': 3104,
    'Salil Arora': 4556,
    'Shivam Mavi': 154,
    'Shivang Kumar': 4561,
    'Smaran Ravichandran': 3752,
    'Travis Head': 37,
    'Zeeshan Ansari': 3575,

    # Additional DB name variants
    'Harshit Rana': 1013,
    'Lhuan-Dre Pretorius': 2827,

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


# ==================== IPL NAME MAPPINGS ====================
# IPL feed name -> Database name mappings for known variations
# Used when matching scraped data to database records

IPL_NAME_MAPPINGS: Final[Dict[str, str]] = {
    # Add IPL name variations as needed
    'surya kumar yadav': 'suryakumar yadav',
    'n. tilak varma': 'tilak varma',
    'k l rahul': 'kl rahul',
    'vaibhav sooryavanshi': 'vaibhav suryavanshi',
    'quinton de kock': 'quinton de kock',
}


# ==================== IPL KNOWN BOWLERS ====================
# IPL players classified as bowlers (exempt from duck penalty in fantasy scoring)
# Names should be lowercase for case-insensitive matching

IPL_KNOWN_BOWLERS: Final[FrozenSet[str]] = frozenset({
    # India bowlers
    'jasprit bumrah',
    'mohammed siraj',
    'arshdeep singh',
    'kuldeep yadav',
    'yuzvendra chahal',
    'harshal patel',
    'khaleel ahmed',
    'mukesh choudhary',
    't. natarajan',
    'avesh khan',
    'tushar deshpande',
    'yash dayal',
    'varun chakaravarthy',
    'harshit rana',
    'rasikh dar',
    'sandeep sharma',
    'jaydev unadkat',
    'bhuvneshwar kumar',
    'sai kishore',
    'mukesh kumar',
    'mohsin khan',

    # Overseas bowlers
    'trent boult',
    'josh hazlewood',
    'mitchell starc',
    'kagiso rabada',
    'rashid khan',
    'pat cummins',
    'jofra archer',
    'nathan ellis',
    'noor ahmad',
    'marco jansen',
    'lungisani ngidi',
    'dushmantha chameera',
    'nuwan thushara',
})


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
