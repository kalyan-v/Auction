from datetime import datetime
from zoneinfo import ZoneInfo
from app import db

def get_pacific_time():
    """Get current time in Pacific timezone"""
    return datetime.now(ZoneInfo('America/Los_Angeles'))


class League(db.Model):
    """League model for separating different auctions (WPL 2025, IPL 2026, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # "WPL 2025", "IPL 2026"
    display_name = db.Column(db.String(100))  # "Women's Premier League 2025"
    default_purse = db.Column(db.Float, default=500000000)  # Default team budget
    max_squad_size = db.Column(db.Integer, default=20)  # Maximum players per team
    min_squad_size = db.Column(db.Integer, default=16)  # Minimum players per team
    is_deleted = db.Column(db.Boolean, default=False)  # Soft delete
    created_at = db.Column(db.DateTime, default=get_pacific_time)
    
    # Relationships
    teams = db.relationship('Team', backref='league', lazy=True)
    players = db.relationship('Player', backref='league', lazy=True)
    
    def __repr__(self):
        return f'<League {self.name}>'


class Team(db.Model):
    """Team model for auction participants"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    budget = db.Column(db.Float, default=500000000)  # 50 Crore
    initial_budget = db.Column(db.Float, default=500000000)  # Starting budget for "Spent" calculation
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
    status = db.Column(db.String(20), default='available', index=True)  # available, sold, unsold
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True, index=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=True, index=True)
    original_team = db.Column(db.String(100), nullable=True, index=True)  # Previous/original team name
    fantasy_points = db.Column(db.Float, default=0)  # Total fantasy points
    image_url = db.Column(db.String(500), nullable=True)  # Player image URL
    is_deleted = db.Column(db.Boolean, default=False, index=True)  # Soft delete
    
    def __repr__(self):
        return f'<Player {self.name}>'


class FantasyAward(db.Model):
    """Model for special fantasy awards (MVP, Orange Cap, Purple Cap)"""
    id = db.Column(db.Integer, primary_key=True)
    award_type = db.Column(db.String(50), nullable=False)  # 'mvp', 'orange_cap', 'purple_cap'
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=True)
    
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
    points = db.Column(db.Float, default=0)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'), nullable=True, index=True)
    timestamp = db.Column(db.DateTime, default=get_pacific_time)
    
    player = db.relationship('Player', backref='point_entries')
    league = db.relationship('League', backref='point_entries')
    
    # Composite index for common query pattern
    __table_args__ = (
        db.Index('idx_player_league_match', 'player_id', 'league_id', 'match_number'),
    )
    
    def __repr__(self):
        return f'<FantasyPointEntry Match {self.match_number}: {self.points} pts>'


class Bid(db.Model):
    """Bid history model"""
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=get_pacific_time)
    
    player = db.relationship('Player', backref='bids')
    team = db.relationship('Team', backref='bids')
    
    def __repr__(self):
        return f'<Bid {self.amount} by Team {self.team_id}>'


class AuctionState(db.Model):
    """Current auction state"""
    id = db.Column(db.Integer, primary_key=True)
    current_player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=False)
    time_remaining = db.Column(db.Integer, default=300)  # seconds
    
    current_player = db.relationship('Player')
    
    def __repr__(self):
        return f'<AuctionState active={self.is_active}>'
