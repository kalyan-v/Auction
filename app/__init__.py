"""
WPL Auction Application

A Flask application for managing WPL cricket auctions with fantasy points tracking.
"""

import time
import uuid

from flask import Flask, g, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from app.logger import get_logger

db = SQLAlchemy()
migrate = Migrate()
logger = get_logger(__name__)


def create_app(config_name: str = 'default') -> Flask:
    """
    Application factory pattern.

    Creates and configures the Flask application with all extensions
    and blueprints registered.

    Args:
        config_name: Configuration to use ('development', 'production', 'default')

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Load configuration
    from config import config
    app.config.from_object(config.get(config_name, config['default']))

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize rate limiter
    from app.extensions import limiter
    limiter.init_app(app)

    # Initialize CSRF protection
    from app.extensions import csrf
    csrf.init_app(app)

    # Initialize CORS for API endpoints
    from flask_cors import CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', ['http://localhost:3000']),
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "X-CSRF-Token"]
        }
    })

    # Register blueprints from routes package
    from app.routes import main_bp, auction_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auction_bp, url_prefix='/auction')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Request logging middleware
    @app.before_request
    def before_request():
        g.start_time = time.time()
        g.request_id = str(uuid.uuid4())[:8]

    @app.after_request
    def after_request(response):
        # Add request ID to response headers for debugging
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id

        # Add security headers in production
        if not app.debug:
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            # HSTS only if behind HTTPS proxy
            if request.is_secure:
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Request logging
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            # Only log non-static requests
            if not request.path.startswith('/static'):
                logger.info(
                    f"[{g.request_id}] {request.method} {request.path} "
                    f"- {response.status_code} ({elapsed:.3f}s)"
                )
        return response

    # Register centralized error handlers
    from app.errors import register_error_handlers
    register_error_handlers(app)

    # Rate limit error handler (overrides the generic 429 handler with more info)
    from flask import jsonify
    from flask_limiter.errors import RateLimitExceeded

    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit(e):
        return jsonify({
            'success': False,
            'error': 'Too many requests. Please try again later.',
            'retry_after': str(e.description)
        }), 429

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
