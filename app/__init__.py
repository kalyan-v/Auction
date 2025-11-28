from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
socketio = SocketIO()

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Register blueprints
    from app.routes import main_bp, auction_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auction_bp, url_prefix='/auction')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
