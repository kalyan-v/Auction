# WPL Fantasy Auction System

A web-based fantasy cricket auction and points tracking system for the Women's Premier League (WPL). Features live auction capabilities, automated fantasy point scraping from the official WPL website, and team management.

**Live Demo**: [trevorhawk7.pythonanywhere.com](https://trevorhawk7.pythonanywhere.com)

## Features

### Auction System
- **Live Bidding**: Real-time auction interface with countdown timer
- **Multi-League Support**: Manage multiple leagues with separate teams, players, and settings
- **Team Management**: Track team budgets, player rosters, and spending
- **Player Database**: Manage player info, positions, base prices, and original teams
- **Bid History**: Complete audit trail of all bids

### Fantasy Points
- **Automated Scraping**: Fetches fantasy points directly from wplt20.com
- **Match-by-Match Tracking**: Individual match scores with game_id deduplication
- **Awards**: Orange Cap (most runs), Purple Cap (most wickets), MVP tracking
- **Team Standings**: Aggregate fantasy points by team
- **Player Headshots**: Auto-fetched from WPL website

### Automation
- **GitHub Actions**: Scheduled scraping at 6:30 PM UTC daily
- **Auto-commit**: Database updates pushed to repository automatically
- **PythonAnywhere Deployment**: Production hosting with git pull sync

## Tech Stack

- **Backend**: Python 3.11, Flask, SQLAlchemy
- **Database**: SQLite
- **Frontend**: HTML5, CSS3, JavaScript
- **Scraping**: Requests, BeautifulSoup
- **CI/CD**: GitHub Actions
- **Hosting**: PythonAnywhere

## Project Structure

```
Auction/
├── app/
│   ├── __init__.py           # App factory, extensions init, request hooks
│   ├── models.py             # Database models (League, Team, Player, Bid, etc.)
│   ├── constants.py          # App constants, WPL config, timeouts
│   ├── dataclasses.py        # Data structures for stats & scraping
│   ├── db_utils.py           # SQLite-compatible locking utilities
│   ├── enums.py              # Player positions, statuses, league types
│   ├── extensions.py         # Flask extensions (rate limiter, CSRF)
│   ├── fantasy_calculator.py # Fantasy points calculation engine
│   ├── player_data.py        # Player ID mappings & bowler list
│   ├── utils.py              # Validation, formatting, auth helpers
│   ├── logger.py             # Centralized logging setup
│   ├── routes/
│   │   ├── __init__.py       # Blueprint registration
│   │   ├── main.py           # Main routes (pages, login, health)
│   │   ├── auction.py        # Auction page routes
│   │   └── api/
│   │       ├── __init__.py   # API blueprint
│   │       ├── auction.py    # Bidding & auction control API
│   │       ├── cricket.py    # WPL data scraping API
│   │       ├── fantasy.py    # Fantasy points management API
│   │       ├── leagues.py    # League CRUD API
│   │       └── players.py    # Player management & images API
│   ├── scrapers/
│   │   ├── __init__.py       # Scraper factory & registry
│   │   ├── base.py           # Abstract base scraper class
│   │   └── wpl.py            # WPL website scraper implementation
│   ├── static/
│   │   ├── css/style.css     # Main stylesheet
│   │   ├── js/
│   │   │   ├── main.js       # Shared utilities (CSRF, XSS, formatting)
│   │   │   ├── auction.js    # Auction room functionality
│   │   │   └── setup.js      # Setup page forms
│   │   └── images/players/   # Player headshots
│   └── templates/
│       ├── base.html         # Base template with nav & animations
│       ├── index.html        # Home page
│       ├── login.html        # Admin login
│       ├── setup.html        # Team/Player management
│       ├── auction.html      # Auction room
│       ├── squads.html       # Team rosters
│       ├── fantasy.html      # Fantasy points & awards
│       └── readonly.html     # Access restricted page
├── tests/
│   ├── __init__.py           # Test suite init
│   ├── conftest.py           # Pytest fixtures
│   ├── test_auth.py          # Authentication tests
│   ├── test_bidding.py       # Auction/bidding tests
│   └── test_models.py        # Database model tests
├── scripts/
│   └── scrape_fantasy.py     # GitHub Actions scraper
├── .github/workflows/
│   ├── scrape_wpl.yml        # Daily scraping workflow
│   └── backup_db.yml         # Database backup workflow
├── instance/
│   └── auction.db            # SQLite database
├── config.py                 # Environment-based configuration
├── run.py                    # Development server entry point
├── wsgi.py                   # Production WSGI entry point
└── requirements.txt          # Python dependencies
```

## Quick Start

### Prerequisites
- Python 3.10+

### Installation

```bash
# Clone repository
git clone https://github.com/kalyan-v/Auction.git
cd Auction

# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python run.py
```

Open http://localhost:5000

### Admin Login
- Username: `admin`
- Password: `wpl2026`

## Usage

### 1. Create a League
1. Login as admin
2. Go to **Setup** > Create League
3. Set league ID, name, and default purse

### 2. Add Teams & Players
1. Add teams with budgets
2. Add players with positions and base prices

### 3. Run Auction
1. Go to **Auction Room**
2. Start auction on a player
3. Teams place bids
4. End auction to finalize sale

### 4. Track Fantasy Points
1. Go to **Fantasy Points**
2. Click "Fetch Match Points" to scrape from WPL
3. View standings, match breakdowns, awards

## API Endpoints

### Leagues
- `GET /api/leagues` - List leagues
- `POST /api/leagues` - Create league
- `DELETE /api/leagues/<id>` - Delete league

### Teams
- `GET /api/teams` - List teams
- `POST /api/teams` - Create team
- `PUT /api/teams/<id>` - Update team

### Players
- `GET /api/players` - List players
- `POST /api/players` - Create player
- `PUT /api/players/<id>` - Update player
- `DELETE /api/players/<id>` - Delete player

### Auction
- `POST /api/auction/start/<player_id>` - Start auction
- `POST /api/bid` - Place bid
- `POST /api/auction/end` - End auction

### Fantasy
- `GET /api/fantasy/players` - Get players with points
- `POST /api/fantasy/fetch-match-points` - Scrape from WPL
- `POST /api/fantasy/fetch-awards` - Fetch awards
- `GET /api/fantasy/points/<player_id>` - Get match points
- `POST /api/fantasy/award` - Set award

## Deployment

### PythonAnywhere

1. Clone repo to PythonAnywhere
2. Set up virtual environment
3. Configure WSGI file to point to `wsgi.py`
4. Set up scheduled task for `git pull` at 6:45 PM UTC

### GitHub Actions

The workflow runs daily at 6:30 PM UTC:
1. Scrapes all WPL match scorecards
2. Calculates fantasy points
3. Updates Orange Cap, Purple Cap, MVP
4. Commits database to repository


## Fantasy Points Calculation

Based on official WPL fantasy scoring (see `app/fantasy_calculator.py`):

### Batting
| Category | Points |
|----------|--------|
| Run scored | 1 |
| Boundary (4) | +4 |
| Boundary (6) | +6 |
| 25 runs | +4 |
| 50 runs | +8 |
| 75 runs | +12 |
| 100 runs | +16 |
| Duck (non-bowlers) | -2 |

### Bowling
| Category | Points |
|----------|--------|
| Wicket | 30 |
| Dot ball | +1 |
| Maiden over | +12 |
| LBW/Bowled bonus | +8 |
| 3-wicket haul | +4 |
| 4-wicket haul | +8 |
| 5-wicket haul | +12 |

### Fielding
| Category | Points |
|----------|--------|
| Catch | 8 |
| 3+ catches bonus | +4 |
| Stumping | 12 |
| Direct run out | 12 |
| Indirect run out | 6 |

### Other
| Category | Points |
|----------|--------|
| Playing XI bonus | +4 |

Strike rate and economy bonuses/penalties apply for qualifying balls (min 20 runs/10 balls for SR, min 2 overs for economy).

## Project Stats

| Type | Files | Approx Lines |
|------|-------|--------------|
| Python | 27 | ~6,000 |
| CSS | 1 | ~2,950 |
| HTML (Jinja2) | 8 | ~1,700 |
| JavaScript | 3 | ~1,100 |
| Tests | 5 | ~750 |
| **Total** | **44** | **~14,000** |

## Troubleshooting

**Python not found**: Install from python.org, check "Add to PATH"

**Virtual environment won't activate**: Run as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Database errors**: Delete `instance/auction.db` and restart

**Port 5000 in use**: Change port in `run.py`

## License

MIT
