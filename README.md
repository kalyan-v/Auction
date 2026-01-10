# 🏏 Player Auction System

A complete web-based player auction system built with Flask, perfect for managing sports team auctions (cricket, football, etc.). This is a beginner-friendly project with real-time bidding capabilities.

## 📋 Features

- **Multi-League Support**: Create and manage multiple leagues (WPL, IPL, etc.) with separate teams, players, and settings
- **Team Management**: Add and track multiple teams with budgets
- **Player Database**: Manage player information, positions, base prices, and original teams
- **Live Auction**: Real-time bidding interface with countdown timer
- **Budget Tracking**: Automatic budget updates after successful bids
- **Fantasy Points**: Track player fantasy points across matches with MVP, Orange Cap, and Purple Cap awards
- **Bid History**: Track all bids placed during auctions
- **Session-Based League Switching**: Switch between leagues from any page
- **Responsive Design**: Works on desktop and mobile devices

## 🛠️ Technology Stack

- **Backend**: Python 3.x, Flask
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, JavaScript
- **Real-time**: Flask-SocketIO (prepared for future real-time features)

## 📁 Project Structure

```
Auction/
├── app/
│   ├── __init__.py          # Application factory
│   ├── models.py            # Database models
│   ├── routes.py            # Application routes and API endpoints
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css    # Styling
│   │   └── js/
│   │       ├── main.js      # Core JavaScript functions
│   │       ├── setup.js     # Setup page functionality
│   │       └── auction.js   # Auction page functionality
│   └── templates/
│       ├── base.html        # Base template
│       ├── index.html       # Home page
│       ├── setup.html       # Team/Player setup
│       └── auction.html     # Auction interface
├── config.py                # Configuration settings
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
├── .gitignore              # Git ignore file
└── README.md               # This file
```

## 🚀 Getting Started

### Prerequisites

You need to install Python first. Here's how:

1. **Download Python**:
   - Visit https://www.python.org/downloads/
   - Download Python 3.10 or higher
   - **IMPORTANT**: During installation, check "Add Python to PATH"

2. **Verify Installation**:
   Open a new PowerShell terminal and run:
   ```powershell
   python --version
   ```
   You should see something like `Python 3.10.x`

### Installation Steps

1. **Open the Project in VS Code**:
   - The project is already open at `C:\Users\kvaliveti\Downloads\Auction`

2. **Create a Virtual Environment**:
   ```powershell
   python -m venv venv
   ```

3. **Activate the Virtual Environment**:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   You should see `(venv)` appear in your terminal prompt.

4. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

5. **Initialize the Database**:
   ```powershell
   python run.py
   ```
   The database will be created automatically when you first run the app.

### Running the Application

1. Make sure your virtual environment is activated (you should see `(venv)` in terminal)
2. Run the application:
   ```powershell
   python run.py
   ```
3. Open your web browser and go to:
   ```
   http://localhost:5000
   ```

## 📖 How to Use

### Step 0: Login as Admin (Required for Making Changes)

1. Click the **🔐 Login** link in the navigation bar
2. Enter the admin credentials:
   - Username: `admin`
   - Password: `wpl2025`
3. Once logged in, you'll see **👤 Admin** badge in the navbar

### Step 1: Create a League

1. Navigate to **Setup** page
2. In the **Leagues** section:
   - Enter a League ID (e.g., `wpl2025`, `ipl2026`)
   - Enter Display Name (e.g., `WPL 2025`, `IPL 2026`)
   - Set the default purse for teams (in Crores)
   - Click "Create League"
3. The new league will be selected automatically

### Step 2: Setup Teams and Players

1. Navigate to **Setup** page
2. **Add Teams**:
   - Enter team name
   - Set budget (default: from league settings)
   - Click "Add Team"
3. **Add Players**:
   - Enter player name
   - Select position (Batter, Bowler, Allrounder, Keeper)
   - Select country (Indian/Overseas)
   - Set base price (in Lakhs)
   - Optionally set Original Team (e.g., "MI", "CSK")
   - Click "Add Player"

### Step 3: Run the Auction

1. Navigate to **Auction Room** page
2. Click "Start Auction" on any available player
3. **Place Bids**:
   - Select your team from dropdown
   - Enter bid amount (must be higher than current price)
   - Click "Place Bid"
4. Click "End Current Auction" when done

### Step 3: View Results

- Check which team won the player
- View updated team budgets
- See bid history for each auction
### Step 5: Manage Fantasy Points

1. Navigate to **Fantasy Points** page
2. View player standings with total points
3. Click on a player to add/view match-by-match points
4. Set awards (MVP, Orange Cap, Purple Cap) for top performers

### Switching Between Leagues

- Use the league dropdown in the navbar to switch between different leagues
- Each league has its own teams, players, and fantasy awards
- League selection is saved in your browser session
## ⚙️ Configuration

Edit `config.py` to customize:

```python
DEFAULT_AUCTION_TIME = 300      # Auction duration (seconds)
MIN_BID_INCREMENT = 100000      # Minimum bid increase
STARTING_BUDGET = 10000000      # Default team budget
```

## 🐛 Troubleshooting

**Problem**: Python not found
- **Solution**: Install Python from python.org and ensure "Add to PATH" is checked

**Problem**: `pip` command not found
- **Solution**: Run `python -m pip install -r requirements.txt` instead

**Problem**: Virtual environment won't activate
- **Solution**: Run PowerShell as Administrator and execute:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

**Problem**: Database errors
- **Solution**: Delete `auction.db` file and restart the application

**Problem**: Port 5000 already in use
- **Solution**: Change port in `run.py`: `socketio.run(app, port=5001)`

## 🎯 Next Steps for Learning

1. **Add More Features**:
   - Add player statistics and ratings
   - Implement real-time updates with SocketIO
   - Add user authentication for teams
   - Export results to PDF/Excel

2. **Improve the Design**:
   - Customize colors and fonts in `style.css`
   - Add animations and transitions
   - Make it more responsive

3. **Learn More**:
   - Flask Documentation: https://flask.palletsprojects.com/
   - SQLAlchemy Tutorial: https://docs.sqlalchemy.org/
   - JavaScript MDN: https://developer.mozilla.org/en-US/docs/Web/JavaScript

## 📝 API Endpoints

### League Management
- `GET /api/leagues` - Get all leagues
- `POST /api/leagues` - Create a new league
- `PUT /api/leagues/<league_id>` - Update a league
- `DELETE /api/leagues/<league_id>` - Soft-delete a league

### Teams
- `GET /api/teams` - Get all teams (filtered by current league)
- `POST /api/teams` - Create a new team

### Players
- `GET /api/players` - Get all players (filtered by current league)
- `POST /api/players` - Create a new player
- `PUT /api/players/<player_id>` - Update a player
- `DELETE /api/players/<player_id>` - Soft-delete a player

### Auction
- `POST /api/bid` - Place a bid
- `POST /api/auction/start/<player_id>` - Start auction for player
- `POST /api/auction/end` - End current auction

### Fantasy Points
- `GET /api/fantasy/players` - Get all sold players with fantasy points
- `POST /api/fantasy/points/add` - Add match points for a player
- `GET /api/fantasy/points/<player_id>` - Get match-by-match points
- `POST /api/fantasy/award` - Set an award (MVP, Orange Cap, Purple Cap)
- `GET /api/fantasy/awards` - Get all awards

## 🤝 Contributing

This is your learning project! Feel free to:
- Modify any code
- Add new features
- Experiment with designs
- Break things and fix them (that's how you learn!)

## 📧 Need Help?

If you're stuck:
1. Check the error message in the terminal
2. Read the code comments
3. Search for the error on Google or Stack Overflow
4. Ask in programming communities

## 📄 License

This is a learning project - use it however you want!

---

**Happy Coding! 🎉**
