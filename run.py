"""
Development server entry point.

Run this file directly to start the Flask development server.
For production deployment, use wsgi.py with a WSGI server like gunicorn.

Usage:
    python run.py

Environment Variables:
    FLASK_CONFIG: Configuration to use ('development', 'production'). Defaults to 'development'.
"""

import os
from app import create_app
config_name = os.environ.get('FLASK_CONFIG', 'development')
app = create_app(config_name)

if __name__ == '__main__':
    debug = config_name == 'development'
    app.run(debug=debug, host='0.0.0.0', port=5000)
