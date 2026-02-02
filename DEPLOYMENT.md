# PythonAnywhere Deployment Guide

## Quick Start

### 1. Upload Your Code

**Option A: Git (Recommended)**
```bash
# In PythonAnywhere Bash console
cd ~
git clone https://github.com/yourusername/Auction.git
```

**Option B: ZIP Upload**
- Compress your project folder
- Upload via PythonAnywhere Files tab
- Unzip in Bash console: `unzip Auction.zip`

### 2. Create Virtual Environment

```bash
cd ~/Auction
mkvirtualenv --python=/usr/bin/python3.10 auctionenv
pip install -r requirements.txt
```

### 3. Configure WSGI File

1. Go to **Web** tab → Click on your web app
2. In **Code** section, set:
   - **Source code**: `/home/yourusername/Auction`
   - **Working directory**: `/home/yourusername/Auction`
3. Click on **WSGI configuration file** link
4. Replace contents with:

```python
import os
import sys

# Project path
project_home = '/home/yourusername/Auction'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# IMPORTANT: Set secure values!
os.environ['FLASK_CONFIG'] = 'production'
os.environ['SECRET_KEY'] = 'your-secure-random-key-here'  # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
os.environ['ADMIN_USERNAME'] = 'admin'
os.environ['ADMIN_PASSWORD'] = 'your-secure-password-here'
os.environ['DATABASE_URL'] = f'sqlite:///{project_home}/auction.db'

from app import create_app
application = create_app('production')
```

### 4. Configure Static Files

In **Web** tab → **Static files** section, add:

| URL | Directory |
|-----|-----------|
| `/static` | `/home/yourusername/Auction/app/static` |

### 5. Configure Virtualenv

In **Web** tab → **Virtualenv** section:
- Set path to: `/home/yourusername/.virtualenvs/auctionenv`

### 6. Initialize Database

```bash
cd ~/Auction
workon auctionenv
python -c "from app import create_app, db; app = create_app('production'); app.app_context().push(); db.create_all(); print('Database created!')"
```

### 7. Reload Web App

Click the green **Reload** button in the Web tab.

---

## Security Checklist

Before going live:

- [ ] Generate a secure SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Set a strong ADMIN_PASSWORD (16+ chars, mixed case, numbers, symbols)
- [ ] Verify HTTPS is enabled (PythonAnywhere provides this automatically)
- [ ] Test login works correctly
- [ ] Test CSRF protection (forms should work, direct API calls without token should fail)

---

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `FLASK_CONFIG` | Config environment (`production`) | Yes |
| `SECRET_KEY` | Flask session encryption key | Yes |
| `ADMIN_USERNAME` | Admin login username | Yes |
| `ADMIN_PASSWORD` | Admin login password | Yes |
| `DATABASE_URL` | SQLite connection string | Yes |

---

## Troubleshooting

### Error: "No module named 'app'"
- Check `sys.path` includes your project directory
- Verify the project structure is correct

### Error: "SECRET_KEY must be set"
- Add the SECRET_KEY environment variable in WSGI file

### Static files not loading (CSS/JS broken)
- Verify static files mapping in Web tab
- Path must be absolute: `/home/yourusername/Auction/app/static`

### Database errors
- Ensure DATABASE_URL uses absolute path
- Check file permissions: `chmod 664 ~/Auction/auction.db`

### 500 Internal Server Error
- Check error log: Web tab → Error log link
- Common causes: missing dependencies, syntax errors, permission issues

---

## Updating the App

```bash
cd ~/Auction
git pull origin main  # or upload new files
workon auctionenv
pip install -r requirements.txt  # if dependencies changed
```

Then click **Reload** in the Web tab.

---

## Free vs Paid Tier Notes

**Free Tier:**
- SQLite works fine (used by default)
- Limited CPU/bandwidth
- App sleeps after inactivity

**Paid Tier:**
- Can use MySQL for better performance
- Always-on web apps
- More CPU/bandwidth

For MySQL on paid tier, change DATABASE_URL:
```python
os.environ['DATABASE_URL'] = 'mysql://username:password@yourusername.mysql.pythonanywhere-services.com/yourusername$auction'
```
