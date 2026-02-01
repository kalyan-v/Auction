"""
WSGI entry point for PythonAnywhere deployment.

PythonAnywhere Configuration:
1. Set the WSGI configuration file to point to this file
2. Set environment variables in the WSGI config file (see below)
"""

import os
import sys

# Add your project directory to the sys.path
# Replace 'yourusername' with your actual PythonAnywhere username
project_home = '/home/yourusername/Auction'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables for production
# IMPORTANT: Change these values before deployment!
os.environ.setdefault('FLASK_CONFIG', 'production')
os.environ.setdefault('SECRET_KEY', 'CHANGE-THIS-TO-A-REAL-SECRET-KEY')
os.environ.setdefault('ADMIN_USERNAME', 'admin')
os.environ.setdefault('ADMIN_PASSWORD', 'CHANGE-THIS-PASSWORD')

# Database path - use absolute path for PythonAnywhere
# SQLite works on PythonAnywhere free tier
os.environ.setdefault('DATABASE_URL', f'sqlite:///{project_home}/auction.db')

from app import create_app

application = create_app(os.environ.get('FLASK_CONFIG', 'production'))
