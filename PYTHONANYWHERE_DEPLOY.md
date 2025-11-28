# PythonAnywhere Deployment Guide

## Step-by-Step Instructions

### 1. Create Account
Go to https://www.pythonanywhere.com and sign up for a **free Beginner account**

### 2. Upload Your Code

**Option A: Using Git (Recommended)**
1. Push your code to GitHub first
2. On PythonAnywhere, go to **Consoles** → **Bash**
3. Run:
```bash
git clone https://github.com/YOUR_USERNAME/Auction.git
cd Auction
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Option B: Manual Upload**
1. Go to **Files** tab
2. Create a folder called `Auction`
3. Upload all your project files there

### 3. Set Up Virtual Environment (if using manual upload)
1. Go to **Consoles** → **Bash**
2. Run:
```bash
cd Auction
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Create Web App
1. Go to **Web** tab
2. Click **Add a new web app**
3. Choose **Manual configuration** (NOT Flask)
4. Select **Python 3.10**

### 5. Configure WSGI File
1. In the **Web** tab, click on the **WSGI configuration file** link
2. Delete all the content and replace with:

```python
import sys
import os

# Add your project directory to the path
project_home = '/home/YOUR_USERNAME/Auction'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
os.environ['SECRET_KEY'] = 'your-secret-key-here-change-this'

# Import the Flask app
from wsgi import application
```

**Replace `YOUR_USERNAME` with your actual PythonAnywhere username!**

### 6. Configure Virtualenv
1. In the **Web** tab, find **Virtualenv** section
2. Enter: `/home/YOUR_USERNAME/Auction/venv`

### 7. Configure Static Files
1. In the **Web** tab, find **Static files** section
2. Add:
   - URL: `/static/`
   - Directory: `/home/YOUR_USERNAME/Auction/app/static`

### 8. Initialize Database
1. Go to **Consoles** → **Bash**
2. Run:
```bash
cd Auction
source venv/bin/activate
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print('Database created!')"
```

### 9. Reload Web App
1. Go back to **Web** tab
2. Click the green **Reload** button

### 10. Visit Your Site!
Your app will be live at: `https://YOUR_USERNAME.pythonanywhere.com`

---

## Adding Players After Deployment

Go to **Consoles** → **Bash** and run:
```bash
cd Auction
source venv/bin/activate
python -c "
from app import create_app, db
from app.models import Player, Team

app = create_app()
with app.app_context():
    # Add teams
    teams = [
        Team(name='MI', budget=500000000, initial_budget=500000000),
        Team(name='DC', budget=500000000, initial_budget=500000000),
        Team(name='RCB', budget=500000000, initial_budget=500000000),
    ]
    for team in teams:
        db.session.add(team)
    
    # Add your players here...
    db.session.commit()
    print('Done!')
"
```

---

## Troubleshooting

**Error: No module named 'app'**
- Make sure the project path in WSGI file is correct

**Error: Database not found**
- Run the database initialization command in step 8

**Static files not loading**
- Double-check the static files path in Web tab

**Site not updating after changes**
- Always click **Reload** in the Web tab after making changes
