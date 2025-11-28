import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///auction.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Auction settings
    DEFAULT_AUCTION_TIME = 300  # 5 minutes in seconds
    MIN_BID_INCREMENT = 1000000  # Minimum bid increment (10 Lakhs)
    STARTING_BUDGET = 500000000  # Each team starts with 50 Crore (50,00,00,000)
    DEFAULT_BASE_PRICE = 5000000  # Default base price 50 Lakhs
