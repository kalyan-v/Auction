"""
WPL Auction Application

A Flask application for managing WPL cricket auctions with fantasy points tracking.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
socketio = SocketIO()


def create_app() -> Flask:
    """
    Application factory pattern.

    Creates and configures the Flask application with all extensions
    and blueprints registered.

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # Register blueprints from routes package
    from app.routes import main_bp, auction_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auction_bp, url_prefix='/auction')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
