"""
Application configuration.

Configuration values can be overridden by environment variables.
Supports development, testing, and production environments.
"""

import os
from datetime import timedelta
from typing import Optional


class Config:
    """Base configuration shared across all environments."""

    # Flask settings
    SECRET_KEY: str = os.environ.get('SECRET_KEY', '')
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Session security
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(hours=2)  # Reduced from 8 hours

    # CORS settings
    CORS_ORIGINS: list = ['http://localhost:3000', 'http://localhost:5000']

    # Admin credentials - MUST be set via environment variables in production!
    ADMIN_USERNAME: str = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD: str = os.environ.get('ADMIN_PASSWORD', '')
    # Hashed password for production (bcrypt) - takes precedence over ADMIN_PASSWORD
    ADMIN_PASSWORD_HASH: str = os.environ.get('ADMIN_PASSWORD_HASH', '')

    # Auction settings
    DEFAULT_AUCTION_TIME: int = 300  # 5 minutes in seconds
    MIN_BID_INCREMENT: int = 1_000_000  # 10 Lakhs
    STARTING_BUDGET: int = 500_000_000  # 50 Crore
    DEFAULT_BASE_PRICE: int = 5_000_000  # 50 Lakhs

    # Cricket API settings
    CRICKET_API_KEY: Optional[str] = os.environ.get('CRICKET_API_KEY', '')


class DevelopmentConfig(Config):
    """Development configuration with relaxed security for local testing."""

    DEBUG: bool = True
    SQLALCHEMY_DATABASE_URI: str = os.environ.get('DATABASE_URL', 'sqlite:///auction.db')
    SESSION_COOKIE_SECURE: bool = False

    # Allow default credentials in development only
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    ADMIN_PASSWORD: str = os.environ.get('ADMIN_PASSWORD', 'wpl2026')


class TestingConfig(Config):
    """Testing configuration."""

    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = 'sqlite:///:memory:'
    SESSION_COOKIE_SECURE: bool = False
    SECRET_KEY: str = 'test-secret-key'
    ADMIN_PASSWORD: str = 'test-password'


class ProductionConfig(Config):
    """Production configuration with strict security requirements."""

    DEBUG: bool = False
    SQLALCHEMY_DATABASE_URI: str = os.environ.get('DATABASE_URL', '')
    SESSION_COOKIE_SECURE: bool = True

    def __init__(self):
        """Validate required production settings."""
        if not self.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY environment variable must be set in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if not self.ADMIN_PASSWORD_HASH:
            raise ValueError(
                "ADMIN_PASSWORD_HASH environment variable must be set in production. "
                "Generate one with: python -c \"from app.auth import hash_password; print(hash_password('your_password'))\""
            )
        if not self.SQLALCHEMY_DATABASE_URI:
            raise ValueError(
                "DATABASE_URL environment variable must be set in production."
            )


# Configuration dictionary for easy access
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
