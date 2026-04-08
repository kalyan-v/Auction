"""
Database models for the WPL Auction application.

Contains all SQLAlchemy models for leagues, teams, players, bids,
fantasy points, and auction state.
"""

import json
from typing import Optional

from app import db
from app.constants import DEFAULT_AUCTION_TIMER, DEFAULT_BID_INCREMENT, DEFAULT_MAX_SQUAD_SIZE, DEFAULT_MIN_SQUAD_SIZE, DEFAULT_PURSE
from app.enums import PlayerStatus
from app.utils import get_pacific_time


class League(db.Model):
    """League model for separating different auctions (WPL 2025, IPL 2026, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # "WPL 2025", "IPL 2026"
    display_name = db.Column(db.String(100))  # "Women's Premier League 2025"
    league_type = db.Column(db.String(20), default='wpl')  # 'wpl', 'ipl', etc. - used for image/scraper routing
    default_purse = db.Column(db.Float, default=DEFAULT_PURSE)  # Default team budget
    max_squad_size = db.Column(db.Integer, default=DEFAULT_MAX_SQUAD_SIZE)  # Maximum players per team
    min_squad_size = db.Column(db.Integer, default=DEFAULT_MIN_SQUAD_SIZE)  # Minimum players per team
    bid_increment_tiers = db.Column(db.Text, default='[{"threshold": 0, "increment": 2500000}]')  # JSON: [{threshold, increment}] sorted by threshold
    max_rtm = db.Column(db.Integer, default=0)  # Max RTMs allowed per team (0 = disabled)
    is_active = db.Column(db.Boolean, default=False)  # Admin-selected active league shown to non-admin users
    is_deleted = db.Column(db.Boolean, default=False)  # Soft delete
    created_at = db.Column(db.DateTime, default=get_pacific_time)

    @property
    def bid_increment_tiers_parsed(self) -> list[dict]:
        """Parse bid_increment_tiers JSON into list of dicts."""
        try:
            tiers = json.loads(self.bid_increment_tiers or '[]')
            return sorted(tiers, key=lambda t: t.get('threshold', 0))
        except (json.JSONDecodeError, TypeError) as e:
            from app.logger import get_logger
            get_logger(__name__).error(
                "League %s: bid_increment_tiers JSON parse failed: %s, using default",
                self.id, e
            )
            return [{'threshold': 0, 'increment': DEFAULT_BID_INCREMENT}]

    def get_bid_increment(self, current_price: int) -> int:
        """Get the bid increment for a given current price.

        Args:
            current_price: Current bid price in raw value (e.g. 50000000 for 5 Cr).

        Returns:
            Increment amount in raw value.
        """
        tiers = self.bid_increment_tiers_parsed
        if not tiers:
            return DEFAULT_BID_INCREMENT
        # Find the highest threshold that current_price meets
        applicable = tiers[0]
        for tier in tiers:
            if current_price >= tier.get('threshold', 0):
                applicable = tier
        return applicable.get('increment', DEFAULT_BID_INCREMENT)

    # Relationships
    teams = db.relationship('Team', backref='league', lazy=True)
    players = db.relationship('Player', backref='league', lazy=True)
    auction_categories = db.relationship('AuctionCategory', backref='league', lazy=True,
                                          order_by='AuctionCategory.sort_order')
    
    def __repr__(self):
        return f'<League {self.name}>'


class AuctionCategory(db.Model):
    """Auction categories for organizing players during auctions (e.g., Marquee, Set 1, Capped, Uncapped).
    
    These are league-specific and set by admin during league creation.
    They are purely for auction organization and do NOT replace player positions.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g., "Marquee", "Set 1"
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False, index=True)
    sort_order = db.Column(db.Integer, default=0)  # For display ordering
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Note: No DB-level unique constraint — soft-delete makes it incompatible.
    # Uniqueness is enforced at the application layer (addCategoryTag prevents duplicates).
    
    def __repr__(self):
        return f'<AuctionCategory {self.name}>'


class Team(db.Model):
    """Team model for auction participants"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    budget = db.Column(db.Float, default=DEFAULT_PURSE)  # 50 Crore
    initial_budget = db.Column(db.Float, default=DEFAULT_PURSE)  # Starting budget for "Spent" calculation
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=True, index=True)
    is_deleted = db.Column(db.Boolean, default=False, index=True)  # Soft delete
    
    # Relationships
    players = db.relationship('Player', backref='team', lazy=True)
    
    # Unique constraint: same team name can exist in different leagues
    __table_args__ = (db.UniqueConstraint('name', 'league_id', name='unique_team_per_league'),)
    
    def __repr__(self):
        return f'<Team {self.name}>'


class Player(db.Model):
    """Player model for auction items"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(50), index=True)
    country = db.Column(db.String(20), default='Indian')  # Indian or Overseas
    base_price = db.Column(db.Float, default=5000000)  # 50 Lakhs
    current_price = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default=PlayerStatus.AVAILABLE, index=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True, index=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=True, index=True)
    original_team = db.Column(db.String(100), nullable=True, index=True)  # Previous/original team name
    auction_category = db.Column(db.String(50), nullable=True, index=True)  # Auction tier (Marquee, Set 1, etc.)
    fantasy_points = db.Column(db.Float, default=0)  # Total fantasy points
    image_url = db.Column(db.String(500), nullable=True)  # Player image URL
    is_rtm = db.Column(db.Boolean, default=False)  # Whether this player was acquired via RTM
    is_deleted = db.Column(db.Boolean, default=False, index=True)  # Soft delete

    # Composite indexes for common query patterns
    __table_args__ = (
        db.Index('idx_player_league_status', 'league_id', 'status', 'is_deleted'),
        db.Index('idx_player_team_status', 'team_id', 'status'),
    )

    def __repr__(self):
        return f'<Player {self.name}>'


class FantasyAward(db.Model):
    """Model for special fantasy awards (MVP, Orange Cap, Purple Cap)"""
    id = db.Column(db.Integer, primary_key=True)
    award_type = db.Column(db.String(50), nullable=False)  # 'mvp', 'orange_cap', 'purple_cap'
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=True)
    leaderboard_json = db.Column(db.Text, nullable=True)  # JSON: top-5 leaderboard from scraper
    
    player = db.relationship('Player', backref='awards')
    league = db.relationship('League', backref='awards')
    
    # Unique constraint: one award type per league
    __table_args__ = (db.UniqueConstraint('award_type', 'league_id', name='unique_award_per_league'),)
    
    def __repr__(self):
        return f'<FantasyAward {self.award_type}>'


class FantasyPointEntry(db.Model):
    """Model for individual match fantasy point entries"""
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False, index=True)
    match_number = db.Column(db.Integer, nullable=False)
    game_id = db.Column(db.String(50), nullable=True, index=True)  # Unique match identifier from source
    points = db.Column(db.Float, default=0)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=True, index=True)
    timestamp = db.Column(db.DateTime, default=get_pacific_time)
    is_deleted = db.Column(db.Boolean, default=False)  # Soft delete

    player = db.relationship('Player', backref='point_entries')
    league = db.relationship('League', backref='point_entries')

    # Unique constraint: use game_id as primary deduplication key (more reliable than match_number)
    __table_args__ = (
        db.UniqueConstraint('player_id', 'league_id', 'game_id', name='unique_player_game_entry'),
        db.Index('idx_player_league_game', 'player_id', 'league_id', 'game_id'),
    )
    
    def __repr__(self):
        return f'<FantasyPointEntry Match {self.match_number}: {self.points} pts>'


class Bid(db.Model):
    """Bid history model"""
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False, index=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False, index=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=get_pacific_time)
    is_deleted = db.Column(db.Boolean, default=False)  # Soft delete

    player = db.relationship('Player', backref='bids')
    team = db.relationship('Team', backref='bids')
    league = db.relationship('League', backref='bids')

    # Composite index for finding highest bid quickly
    __table_args__ = (
        db.Index('idx_bid_player_amount', 'player_id', 'amount'),
        db.Index('idx_bid_league_player', 'league_id', 'player_id'),
    )

    def __repr__(self):
        return f'<Bid {self.amount} by Team {self.team_id}>'


class AuctionState(db.Model):
    """Current auction state — one per league for concurrent auctions."""
    id = db.Column(db.Integer, primary_key=True)
    current_player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=False)
    time_remaining = db.Column(db.Integer, default=DEFAULT_AUCTION_TIMER)  # seconds
    
    current_player = db.relationship('Player')
    league = db.relationship('League', backref='auction_state')
    
    # One auction state per league
    __table_args__ = (
        db.UniqueConstraint('league_id', name='unique_auction_state_per_league'),
    )

    def __repr__(self):
        return f'<AuctionState league={self.league_id} active={self.is_active}>'
