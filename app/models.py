from datetime import datetime
from zoneinfo import ZoneInfo
from app import db

def get_pacific_time():
    """Get current time in Pacific timezone"""
    return datetime.now(ZoneInfo('America/Los_Angeles'))

class Team(db.Model):
    """Team model for auction participants"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    budget = db.Column(db.Float, default=500000000)  # 50 Crore
    initial_budget = db.Column(db.Float, default=500000000)  # Starting budget for "Spent" calculation
    players = db.relationship('Player', backref='team', lazy=True)
    
    def __repr__(self):
        return f'<Team {self.name}>'

class Player(db.Model):
    """Player model for auction items"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(50))
    country = db.Column(db.String(20), default='Indian')  # Indian or Overseas
    base_price = db.Column(db.Float, default=5000000)  # 50 Lakhs
    current_price = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='available')  # available, sold, unsold
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    
    def __repr__(self):
        return f'<Player {self.name}>'

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
