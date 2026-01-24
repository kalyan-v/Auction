"""
Application configuration.

Configuration values can be overridden by environment variables.
"""

import os
from typing import Optional


class Config:
    """Base configuration."""

    # Flask settings
    SECRET_KEY: str = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI: str = os.environ.get('DATABASE_URL') or 'sqlite:///auction.db'
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Admin credentials - override these via environment variables in production!
    ADMIN_USERNAME: str = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD: str = os.environ.get('ADMIN_PASSWORD', 'wpl2026')

    # Auction settings (values from app.constants)
    DEFAULT_AUCTION_TIME: int = 300  # 5 minutes in seconds
    MIN_BID_INCREMENT: int = 1_000_000  # 10 Lakhs
    STARTING_BUDGET: int = 500_000_000  # 50 Crore
    DEFAULT_BASE_PRICE: int = 5_000_000  # 50 Lakhs

    # Cricket API settings (CricketData.org free tier)
    # Get your free API key from https://cricketdata.org/
    CRICKET_API_KEY: Optional[str] = os.environ.get('CRICKET_API_KEY', '')
