from flask import Blueprint, render_template, jsonify, request, current_app, session, redirect, url_for
from datetime import datetime
from zoneinfo import ZoneInfo
from functools import wraps
from sqlalchemy.orm import joinedload
import requests
import re
from app import db
from app.models import Team, Player, Bid, AuctionState, FantasyAward, FantasyPointEntry, League

def is_admin():
    """Check if current user is logged in as admin"""
    return session.get('is_admin', False)

def get_current_league():
    """Get the currently selected league from session"""
    league_id = session.get('current_league_id')
    if league_id:
        league = League.query.filter_by(id=league_id, is_deleted=False).first()
        if league:
            return league
    # Default to first non-deleted league
    league = League.query.filter_by(is_deleted=False).first()
    if league:
        session['current_league_id'] = league.id
    return league

def admin_required(f):
    """Decorator to check if user is logged in as admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            return jsonify({'success': False, 'error': 'Admin login required'}), 403
        return f(*args, **kwargs)
    return decorated_function

PACIFIC_TZ = ZoneInfo('America/Los_Angeles')

def to_pacific(dt):
    """Convert datetime to Pacific time"""
    if dt is None:
        return None
    # If naive datetime, assume it's UTC and convert
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo('UTC'))
    return dt.astimezone(PACIFIC_TZ)

# Define blueprints
main_bp = Blueprint('main', __name__)
auction_bp = Blueprint('auction', __name__)
api_bp = Blueprint('api', __name__)

@main_bp.route('/')
def index():
    """Home page - redirects to Fantasy Points"""
    return redirect(url_for('main.fantasy'))

@main_bp.route('/switch-league/<int:league_id>')
def switch_league(league_id):
    """Switch to a different league"""
    league = League.query.filter_by(id=league_id, is_deleted=False).first()
    if league:
        session['current_league_id'] = league.id
    # Validate referrer to prevent open redirect
    referrer = request.referrer
    if referrer and request.host in referrer:
        return redirect(referrer)
    return redirect(url_for('main.fantasy'))

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if (username == current_app.config['ADMIN_USERNAME'] and 
            password == current_app.config['ADMIN_PASSWORD']):
            session['is_admin'] = True
            # Validate next URL to prevent open redirect
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect(url_for('main.setup'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    """Logout admin"""
    session.pop('is_admin', None)
    return redirect(url_for('main.index'))

@main_bp.route('/setup')
def setup():
    """Setup page for adding teams and players - view only if not admin"""
    current_league = get_current_league()
    all_leagues = League.query.filter_by(is_deleted=False).all()
    
    if current_league:
        teams = Team.query.filter_by(league_id=current_league.id, is_deleted=False).all()
        players = Player.query.filter_by(league_id=current_league.id, is_deleted=False).all()
    else:
        teams = []
        players = []
    
    return render_template('setup.html', teams=teams, players=players, 
                           admin_mode=is_admin(), current_league=current_league,
                           all_leagues=all_leagues)

@main_bp.route('/squads')
def squads():
    """View all team squads with players and budgets"""
    current_league = get_current_league()
    all_leagues = League.query.filter_by(is_deleted=False).all()
    
    if current_league:
        teams = Team.query.filter_by(league_id=current_league.id, is_deleted=False).all()
    else:
        teams = []
    
    return render_template('squads.html', teams=teams, admin_mode=is_admin(),
                           current_league=current_league, all_leagues=all_leagues)

@main_bp.route('/fantasy')
def fantasy():
    """Fantasy points page for viewing and managing player points"""
    current_league = get_current_league()
    all_leagues = League.query.filter_by(is_deleted=False).all()
    
    if current_league:
        teams = Team.query.filter_by(league_id=current_league.id, is_deleted=False).all()
        all_players = Player.query.filter_by(league_id=current_league.id, status='sold', is_deleted=False).all()
        
        # Get or create fantasy awards for this league
        mvp = FantasyAward.query.filter_by(award_type='mvp', league_id=current_league.id).first()
        orange_cap = FantasyAward.query.filter_by(award_type='orange_cap', league_id=current_league.id).first()
        purple_cap = FantasyAward.query.filter_by(award_type='purple_cap', league_id=current_league.id).first()
    else:
        teams = []
        all_players = []
        mvp = orange_cap = purple_cap = None
    
    return render_template('fantasy.html', 
                           teams=teams, 
                           all_players=all_players,
                           mvp=mvp,
                           orange_cap=orange_cap,
                           purple_cap=purple_cap,
                           admin_mode=is_admin(),
                           current_league=current_league,
                           all_leagues=all_leagues)

@auction_bp.route('/')
def auction_room():
    """Main auction interface"""
    current_league = get_current_league()
    all_leagues = League.query.filter_by(is_deleted=False).all()
    
    if current_league:
        teams = Team.query.filter_by(league_id=current_league.id, is_deleted=False).all()
        players = Player.query.filter_by(league_id=current_league.id, status='available', is_deleted=False).all()
        unsold_players = Player.query.filter_by(league_id=current_league.id, status='unsold', is_deleted=False).all()
    else:
        teams = []
        players = []
        unsold_players = []
    
    auction_state = AuctionState.query.first()
    return render_template('auction.html', teams=teams, players=players, 
                           unsold_players=unsold_players, auction_state=auction_state, 
                           admin_mode=is_admin(), current_league=current_league,
                           all_leagues=all_leagues)

# API endpoints

# League management API
@api_bp.route('/leagues', methods=['GET', 'POST'])
def manage_leagues():
    """Get all leagues or create a new league"""
    if request.method == 'POST':
        if not is_admin():
            return jsonify({'success': False, 'error': 'Admin login required'}), 403
        data = request.get_json()
        league = League(
            name=data['name'],
            display_name=data.get('display_name', data['name']),
            default_purse=data.get('default_purse', 500000000),
            max_squad_size=data.get('max_squad_size', 20),
            min_squad_size=data.get('min_squad_size', 16)
        )
        db.session.add(league)
        db.session.commit()
        return jsonify({'success': True, 'league_id': league.id})
    
    leagues = League.query.filter_by(is_deleted=False).all()
    return jsonify([{
        'id': l.id, 
        'name': l.name, 
        'display_name': l.display_name,
        'default_purse': l.default_purse,
        'max_squad_size': l.max_squad_size,
        'min_squad_size': l.min_squad_size
    } for l in leagues])

@api_bp.route('/leagues/<int:league_id>', methods=['PUT', 'DELETE'])
def update_league(league_id):
    """Update or soft-delete a league"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    league = League.query.get(league_id)
    if not league:
        return jsonify({'success': False, 'error': 'League not found'})
    
    if request.method == 'DELETE':
        # Soft delete
        league.is_deleted = True
        db.session.commit()
        return jsonify({'success': True})
    
    data = request.get_json()
    league.name = data.get('name', league.name)
    league.display_name = data.get('display_name', league.display_name)
    league.default_purse = data.get('default_purse', league.default_purse)
    league.max_squad_size = data.get('max_squad_size', league.max_squad_size)
    league.min_squad_size = data.get('min_squad_size', league.min_squad_size)
    db.session.commit()
    return jsonify({'success': True})

@api_bp.route('/teams', methods=['GET', 'POST'])
def manage_teams():
    """Get all teams or create a new team"""
    current_league = get_current_league()
    
    if request.method == 'POST':
        if not is_admin():
            return jsonify({'success': False, 'error': 'Admin login required'}), 403
        if not current_league:
            return jsonify({'success': False, 'error': 'No league selected. Create a league first.'}), 400
        
        data = request.get_json()
        budget = data.get('budget', current_league.default_purse)
        team = Team(
            name=data['name'], 
            budget=budget, 
            initial_budget=budget,
            league_id=current_league.id
        )
        db.session.add(team)
        db.session.commit()
        return jsonify({'success': True, 'team_id': team.id})
    
    if current_league:
        teams = Team.query.filter_by(league_id=current_league.id, is_deleted=False).all()
    else:
        teams = []
    return jsonify([{'id': t.id, 'name': t.name, 'budget': t.budget} for t in teams])

@api_bp.route('/players', methods=['GET', 'POST'])
def manage_players():
    """Get all players or create a new player"""
    current_league = get_current_league()
    
    if request.method == 'POST':
        if not is_admin():
            return jsonify({'success': False, 'error': 'Admin login required'}), 403
        if not current_league:
            return jsonify({'success': False, 'error': 'No league selected. Create a league first.'}), 400
        
        data = request.get_json()
        player = Player(
            name=data['name'],
            position=data.get('position', ''),
            country=data.get('country', 'Indian'),
            base_price=data.get('base_price', 100000),
            original_team=data.get('original_team', ''),
            league_id=current_league.id
        )
        db.session.add(player)
        db.session.commit()
        return jsonify({'success': True, 'player_id': player.id})
    
    if current_league:
        players = Player.query.filter_by(league_id=current_league.id, is_deleted=False).all()
    else:
        players = []
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'position': p.position,
        'country': p.country,
        'base_price': p.base_price,
        'original_team': p.original_team,
        'status': p.status
    } for p in players])

@api_bp.route('/players/<int:player_id>', methods=['PUT', 'DELETE'])
def update_player(player_id):
    """Update or soft-delete a player"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'error': 'Player not found'}), 404
    
    if request.method == 'DELETE':
        # Check if player is in active auction
        auction_state = AuctionState.query.first()
        if auction_state and auction_state.current_player_id == player_id:
            auction_state.current_player_id = None
            auction_state.is_active = False
        
        # Soft delete instead of hard delete
        player.is_deleted = True
        db.session.commit()
        return jsonify({'success': True})
    
    data = request.get_json()
    player.name = data.get('name', player.name)
    player.position = data.get('position', player.position)
    player.country = data.get('country', player.country)
    player.base_price = data.get('base_price', player.base_price)
    player.original_team = data.get('original_team', player.original_team)
    db.session.commit()
    return jsonify({'success': True})

@api_bp.route('/players/<int:player_id>/release', methods=['POST'])
def release_player(player_id):
    """Release a player from their team back to auction pool"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    player = Player.query.get_or_404(player_id)
    
    if player.status != 'sold':
        return jsonify({'success': False, 'error': 'Player is not currently sold to a team'})
    
    # Get the team to refund the budget
    team = player.team
    if team:
        # Refund the team's budget with the player's sale price
        team.budget += player.current_price
    
    # Reset player to available status
    player.status = 'available'
    player.team_id = None
    player.current_price = player.base_price
    
    # Delete all bids for this player
    Bid.query.filter_by(player_id=player_id).delete()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'{player.name} has been released back to auction'
    })

@api_bp.route('/players/random', methods=['GET'])
def get_random_player():
    """Get a random available player, optionally filtered by position"""
    import random
    current_league = get_current_league()
    if not current_league:
        return jsonify({'success': False, 'error': 'No league selected'})
    
    position = request.args.get('position', '')
    include_unsold = request.args.get('include_unsold', 'false') == 'true'
    
    if include_unsold:
        query = Player.query.filter(
            Player.league_id == current_league.id,
            Player.is_deleted == False,
            Player.status.in_(['available', 'unsold'])
        )
    else:
        query = Player.query.filter_by(
            league_id=current_league.id, 
            is_deleted=False, 
            status='available'
        )
    
    if position:
        query = query.filter_by(position=position)
    
    available_players = query.all()
    
    if not available_players:
        position_text = f" for position '{position}'" if position else ""
        return jsonify({'success': False, 'error': f'No available players{position_text}'})
    
    player = random.choice(available_players)
    return jsonify({
        'success': True,
        'player': {
            'id': player.id,
            'name': player.name,
            'position': player.position,
            'base_price': player.base_price
        }
    })

@api_bp.route('/players/available', methods=['GET'])
def get_available_players():
    """Get all available players for animation, optionally filtered by position"""
    current_league = get_current_league()
    if not current_league:
        return jsonify({'success': False, 'error': 'No league selected', 'players': []})
    
    position = request.args.get('position', '')
    include_unsold = request.args.get('include_unsold', 'false') == 'true'
    
    if include_unsold:
        query = Player.query.filter(
            Player.league_id == current_league.id,
            Player.is_deleted == False,
            Player.status.in_(['available', 'unsold'])
        )
    else:
        query = Player.query.filter_by(
            league_id=current_league.id, 
            is_deleted=False, 
            status='available'
        )
    
    if position:
        query = query.filter_by(position=position)
    
    available_players = query.all()
    
    if not available_players:
        position_text = f" for position '{position}'" if position else ""
        return jsonify({'success': False, 'error': f'No available players{position_text}', 'players': []})
    
    return jsonify({
        'success': True,
        'players': [{
            'id': p.id,
            'name': p.name,
            'position': p.position,
            'base_price': p.base_price
        } for p in available_players]
    })

@api_bp.route('/players/<int:player_id>/bids', methods=['GET'])
def get_player_bids(player_id):
    """Get bid history for a specific player"""
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'error': 'Player not found'}), 404
    
    bids = Bid.query.filter_by(player_id=player_id).options(joinedload(Bid.team)).order_by(Bid.amount.desc()).all()
    
    return jsonify({
        'success': True,
        'player': {
            'id': player.id,
            'name': player.name,
            'position': player.position,
            'status': player.status,
            'final_price': player.current_price
        },
        'bids': [{
            'team_name': bid.team.name,
            'amount': bid.amount,
            'timestamp': to_pacific(bid.timestamp).strftime('%I:%M:%S %p')
        } for bid in bids]
    })

@api_bp.route('/bid', methods=['POST'])
def place_bid():
    """Place a bid on the current player"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    data = request.get_json()
    player_id = data['player_id']
    team_id = data['team_id']
    amount = data['amount']
    
    player = Player.query.get(player_id)
    team = Team.query.get(team_id)
    
    # Validate bid
    if not player or not team:
        return jsonify({'success': False, 'error': 'Invalid player or team'})
    
    # Check player is in active auction
    if player.status != 'bidding':
        return jsonify({'success': False, 'error': 'Player is not up for auction'})
    
    # Check if this is a base price bid (first bid) or a raise
    existing_bids = Bid.query.filter_by(player_id=player_id).count()
    
    if existing_bids == 0:
        # First bid - allow base price (equal to current price)
        if amount < player.current_price:
            return jsonify({'success': False, 'error': 'Bid must be at least the base price'})
    else:
        # Subsequent bids - must be higher than current
        if amount <= player.current_price:
            return jsonify({'success': False, 'error': 'Bid must be higher than current price'})
    
    if amount > team.budget:
        return jsonify({'success': False, 'error': 'Insufficient budget'})
    
    # Record bid
    bid = Bid(player_id=player_id, team_id=team_id, amount=amount)
    player.current_price = amount
    db.session.add(bid)
    db.session.commit()
    
    return jsonify({'success': True, 'current_price': amount})

@api_bp.route('/auction/start/<int:player_id>', methods=['POST'])
def start_auction(player_id):
    """Start auction for a specific player"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'error': 'Player not found'})
    
    # Get or create auction state
    auction_state = AuctionState.query.first()
    if not auction_state:
        auction_state = AuctionState()
        db.session.add(auction_state)
    
    auction_state.current_player_id = player_id
    auction_state.is_active = True
    auction_state.time_remaining = 300
    
    player.current_price = player.base_price
    player.status = 'bidding'
    
    db.session.commit()
    
    return jsonify({'success': True})

@api_bp.route('/auction/end', methods=['POST'])
def end_auction():
    """End current auction and assign player to highest bidder"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    auction_state = AuctionState.query.first()
    if not auction_state or not auction_state.is_active:
        return jsonify({'success': False, 'error': 'No active auction'})
    
    player = Player.query.get(auction_state.current_player_id)
    
    # Find highest bid
    highest_bid = Bid.query.filter_by(player_id=player.id).order_by(Bid.amount.desc()).first()
    
    if highest_bid:
        # Assign player to team
        team = Team.query.get(highest_bid.team_id)
        team.budget -= highest_bid.amount
        player.team_id = team.id
        player.status = 'sold'
    else:
        player.status = 'unsold'
    
    auction_state.is_active = False
    auction_state.current_player_id = None
    
    db.session.commit()
    
    return jsonify({'success': True})

@api_bp.route('/auction/unsold', methods=['POST'])
def mark_unsold():
    """Mark current player as unsold"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    auction_state = AuctionState.query.first()
    if not auction_state or not auction_state.is_active:
        return jsonify({'success': False, 'error': 'No active auction'})
    
    player = Player.query.get(auction_state.current_player_id)
    player.status = 'unsold'
    player.current_price = 0
    
    auction_state.is_active = False
    auction_state.current_player_id = None
    
    db.session.commit()
    
    return jsonify({'success': True})

@api_bp.route('/auction/reset-price', methods=['POST'])
def reset_price():
    """Reset the current player's price to a specific amount"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    auction_state = AuctionState.query.first()
    if not auction_state or not auction_state.is_active:
        return jsonify({'success': False, 'error': 'No active auction'})
    
    data = request.get_json()
    new_price = data.get('price', 0)
    
    if new_price <= 0:
        return jsonify({'success': False, 'error': 'Invalid price'})
    
    player = Player.query.get(auction_state.current_player_id)
    if not player:
        return jsonify({'success': False, 'error': 'Player not found'}), 404
    
    player.current_price = new_price
    
    # Clear bids for this player above the new price (optional - keeps history clean)
    Bid.query.filter(Bid.player_id == player.id, Bid.amount > new_price).delete()
    
    db.session.commit()
    
    return jsonify({'success': True, 'new_price': new_price})

# Fantasy Points API endpoints
@api_bp.route('/fantasy/points', methods=['POST'])
def update_fantasy_points():
    """Update fantasy points for a player"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    data = request.get_json()
    player_id = data.get('player_id')
    points = data.get('points', 0)
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'error': 'Player not found'})
    
    player.fantasy_points = points
    db.session.commit()
    
    return jsonify({'success': True, 'player_id': player_id, 'points': points})

@api_bp.route('/fantasy/award', methods=['POST'])
def set_fantasy_award():
    """Set a fantasy award (MVP, Orange Cap, Purple Cap)"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    current_league = get_current_league()
    if not current_league:
        return jsonify({'success': False, 'error': 'No league selected'}), 400
    
    data = request.get_json()
    award_type = data.get('award_type')
    player_id = data.get('player_id')
    
    if award_type not in ['mvp', 'orange_cap', 'purple_cap']:
        return jsonify({'success': False, 'error': 'Invalid award type'})
    
    # Get or create the award for this league
    award = FantasyAward.query.filter_by(award_type=award_type, league_id=current_league.id).first()
    if not award:
        award = FantasyAward(award_type=award_type, league_id=current_league.id)
        db.session.add(award)
    
    # Set player (can be None to clear the award)
    award.player_id = player_id if player_id else None
    db.session.commit()
    
    player_name = None
    if player_id:
        player = Player.query.get(player_id)
        player_name = player.name if player else None
    
    return jsonify({
        'success': True, 
        'award_type': award_type, 
        'player_id': player_id,
        'player_name': player_name
    })

@api_bp.route('/fantasy/awards', methods=['GET'])
def get_fantasy_awards():
    """Get all fantasy awards for current league"""
    current_league = get_current_league()
    if not current_league:
        return jsonify({'success': True, 'awards': {}})
    
    awards = FantasyAward.query.filter_by(league_id=current_league.id).all()
    result = {}
    for award in awards:
        result[award.award_type] = {
            'player_id': award.player_id,
            'player_name': award.player.name if award.player else None
        }
    return jsonify({'success': True, 'awards': result})

@api_bp.route('/fantasy/players', methods=['GET'])
def get_fantasy_players():
    """Get all sold players with fantasy points for current league"""
    current_league = get_current_league()
    if not current_league:
        return jsonify({'success': True, 'players': []})
    
    players = Player.query.filter_by(league_id=current_league.id, status='sold', is_deleted=False).all()
    return jsonify({
        'success': True,
        'players': [{
            'id': p.id,
            'name': p.name,
            'position': p.position,
            'team_id': p.team_id,
            'team_name': p.team.name if p.team else None,
            'fantasy_points': p.fantasy_points
        } for p in players]
    })

@api_bp.route('/fantasy/points/add', methods=['POST'])
def add_match_points():
    """Add fantasy points for a specific match"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    current_league = get_current_league()
    if not current_league:
        return jsonify({'success': False, 'error': 'No league selected'}), 400
    
    data = request.get_json()
    player_id = data.get('player_id')
    match_number = data.get('match_number')
    points = data.get('points', 0)
    
    if not player_id or not match_number:
        return jsonify({'success': False, 'error': 'Player ID and match number required'})
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'error': 'Player not found'})
    
    # Check if entry for this match already exists
    existing = FantasyPointEntry.query.filter_by(
        player_id=player_id, 
        match_number=match_number,
        league_id=current_league.id
    ).first()
    
    if existing:
        # Update existing entry
        existing.points = points
    else:
        # Create new entry
        entry = FantasyPointEntry(
            player_id=player_id,
            match_number=match_number,
            points=points,
            league_id=current_league.id
        )
        db.session.add(entry)
    
    # Update total fantasy points for the player
    db.session.flush()
    total_points = db.session.query(db.func.sum(FantasyPointEntry.points)).filter_by(
        player_id=player_id, 
        league_id=current_league.id
    ).scalar() or 0
    player.fantasy_points = total_points
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'player_id': player_id,
        'match_number': match_number,
        'points': points,
        'total_points': total_points
    })

@api_bp.route('/fantasy/points/<int:player_id>', methods=['GET'])
def get_player_match_points(player_id):
    """Get all match point entries for a player"""
    current_league = get_current_league()
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'error': 'Player not found'})
    
    query = FantasyPointEntry.query.filter_by(player_id=player_id)
    if current_league:
        query = query.filter_by(league_id=current_league.id)
    entries = query.order_by(FantasyPointEntry.match_number).all()
    
    return jsonify({
        'success': True,
        'player': {
            'id': player.id,
            'name': player.name,
            'team_name': player.team.name if player.team else None,
            'total_points': player.fantasy_points
        },
        'entries': [{
            'id': e.id,
            'match_number': e.match_number,
            'points': e.points
        } for e in entries]
    })

@api_bp.route('/fantasy/points/delete/<int:entry_id>', methods=['DELETE'])
def delete_match_points(entry_id):
    """Delete a specific match point entry"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    entry = FantasyPointEntry.query.get(entry_id)
    if not entry:
        return jsonify({'success': False, 'error': 'Entry not found'})
    
    player_id = entry.player_id
    league_id = entry.league_id
    db.session.delete(entry)
    
    # Update total fantasy points for the player (filter by league)
    db.session.flush()
    total_points = db.session.query(db.func.sum(FantasyPointEntry.points)).filter_by(
        player_id=player_id,
        league_id=league_id
    ).scalar() or 0
    player = Player.query.get(player_id)
    player.fantasy_points = total_points
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'total_points': total_points
    })


# ==================== Player Image APIs ====================

import os
from flask import current_app

def get_player_image_path():
    """Get the path to store player images"""
    return os.path.join(current_app.root_path, 'static', 'images', 'players')

def download_and_save_image(image_url, player_id, player_name):
    """Download image from URL and save locally"""
    try:
        headers = {
            'User-Agent': 'WPLAuctionApp/1.0 (https://github.com/auction; auction@example.com) python-requests'
        }
        response = requests.get(image_url, headers=headers, timeout=15)
        if response.status_code == 200:
            # Ensure directory exists
            image_dir = get_player_image_path()
            os.makedirs(image_dir, exist_ok=True)
            
            # Create safe filename from player name
            safe_name = "".join(c if c.isalnum() else "_" for c in player_name.lower())
            filename = f"{player_id}_{safe_name}.jpg"
            filepath = os.path.join(image_dir, filename)
            
            # Save image
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            # Return the URL path for the static file
            return f"/static/images/players/{filename}"
        return None
    except Exception as e:
        print(f"Error downloading image for {player_name}: {e}")
        return None

# WPL Player ID mapping (from wplt20.com squad pages)
WPL_PLAYER_IDS = {
    # Mumbai Indians
    'Harmanpreet Kaur': 59348, 'Amanjot Kaur': 75657, 'Amelia Kerr': 66632,
    'Hayley Matthews': 64970, 'Nalla Reddy': 83685, 'Natalie Sciver-Brunt': 63998,
    'Nicola Carey': 63267, 'Poonam Khemnar': 71472, 'Sajeevan Sajana': 84022,
    'Sanskriti Gupta': 84334, 'Triveni Vasistha': 83731, 'G. Kamalini': 108890,
    'G. Kamlini': 108890, 'Rahila Firdous': 75635, 'Milly Illingworth': 100377,
    'Saika Ishaque': 100194, 'Shabnim Ismail': 6658,
    # Delhi Capitals
    'Deeya Yadav': 117710, 'Jemimah Rodrigues': 68442, 'Laura Wolvaardt': 66176,
    'Shafali Verma': 70772, 'Chinelle Henry': 64347, 'Marizanne Kapp': 7759,
    'Minnu Mani': 70723, 'N. Charani': 89194, 'Niki Prasad': 99166,
    'Sneh Rana': 64550, 'Lizelle Lee': 64192, 'Mamatha Madiwala': 89202,
    'Taniya Bhatia': 68443, 'Taniyaa Bhatia': 68443, 'Alana King': 67057,
    'Lucy Hamilton': 100376, 'Nandni Sharma': 75642,
    # Gujarat Giants
    'Anushka Sharma': 84308, 'Bharti Fulmali': 70708, 'Danni Wyatt-Hodge': 59131,
    'Danni Wyatt': 59131, 'Ashleigh Gardner': 67023, 'Ayushi Soni': 81824,
    'Georgia Wareham': 67047, 'Kanika Ahuja': 84086, 'Kim Garth': 19948,
    'Sophie Devine': 62067, 'Tanuja Kanwer': 70721, 'Beth Mooney': 64853,
    'Shivani Singh': 84013, 'Yastika Bhatia': 73424, 'Happy Kumari': 129259,
    'Kashvee Gautam': 75656, 'Rajeshwari Gayakwad': 64549, 'Renuka Singh': 70714,
    'Titas Sadhu': 83663,
    # Royal Challengers Bengaluru
    'Georgia Voll': 75001, 'Smriti Mandhana': 63992, 'Arundhati Reddy': 70064,
    'Dayalan Hemalatha': 69399, 'Gautami Naik': 93529, 'Grace Harris': 65633,
    'Nadine de Klerk': 67302, 'Pooja Vastrakar': 68423, 'Prema Rawat': 112786,
    'Radha Yadav': 68441, 'Sayali Satghare': 83633, 'Sayali Satghare ': 83633,
    'Shreyanka Patil': 75598, 'Prathyoosha Kumar': 82877, 'Richa Ghosh': 74530,
    'Lauren Bell': 69906, 'Linsey Smith': 69760,
    # UP Warriorz
    'Kiran Navgire': 71461, 'Meg Lanning': 57908, 'Phoebe Litchfield': 71357,
    'Shweta Sehrawat': 83619, 'Simran Shaikh': 83648, 'Asha Sobhana': 75591,
    'Chloe Tryon': 11858, 'Deandra Dottin': 59467, 'Deepti Sharma': 65146,
    'Harleen Deol': 70726, 'Kranti Goud': 84330, 'Kranti Gaud': 84330,
    'Pratika Rawal': 83623, 'Shikha Pandey': 64755, 'Shipra Giri': 84241,
    'Sophie Ecclestone': 66391, 'Suman Meena': 83897, 'Gongadi Trisha': 83660,
    'Trisha Gongadi': 83660, 'Charli Knott': 70455,
}

def search_and_download_player_image(player_id, player_name):
    """Search for player image and download it locally - tries WPL first"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # Try WPL first (official source with high-quality headshots)
    wpl_player_id = WPL_PLAYER_IDS.get(player_name.strip())
    if wpl_player_id:
        try:
            image_url = f"https://www.wplt20.com/static-assets/images/players/series/13458/{wpl_player_id}.png"
            response = requests.get(image_url, headers=headers, timeout=15)
            if response.status_code == 200 and len(response.content) > 1000:
                # Ensure directory exists
                image_dir = get_player_image_path()
                os.makedirs(image_dir, exist_ok=True)
                
                # Create safe filename
                safe_name = "".join(c if c.isalnum() else "_" for c in player_name.lower().strip())
                filename = f"{player_id}_{safe_name}.png"
                filepath = os.path.join(image_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                return f"/static/images/players/{filename}"
        except Exception as e:
            print(f"WPL image fetch error for {player_name}: {e}")
    
    # Fallback to Wikipedia for players not in WPL
    wiki_headers = {
        'User-Agent': 'WPLAuctionApp/1.0 (https://github.com/auction; auction@example.com) python-requests'
    }
    try:
        wiki_url = 'https://en.wikipedia.org/w/api.php'
        params = {
            'action': 'query',
            'titles': player_name,
            'prop': 'pageimages',
            'format': 'json',
            'pithumbsize': 200
        }
        response = requests.get(wiki_url, params=params, headers=wiki_headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pages = data.get('query', {}).get('pages', {})
            for page_id, page_data in pages.items():
                if page_id != '-1':
                    thumbnail = page_data.get('thumbnail', {})
                    if thumbnail.get('source'):
                        local_path = download_and_save_image(thumbnail['source'], player_id, player_name)
                        if local_path:
                            return local_path
    except Exception as e:
        print(f"Wikipedia search error for {player_name}: {e}")
    
    return None


@api_bp.route('/players/<int:player_id>/fetch-image', methods=['POST'])
def fetch_player_image(player_id):
    """Fetch, download and save player image locally"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'error': 'Player not found'}), 404
    
    # Search and download image
    local_image_path = search_and_download_player_image(player.id, player.name)
    
    if local_image_path:
        player.image_url = local_image_path
        db.session.commit()
        return jsonify({
            'success': True,
            'image_url': local_image_path,
            'message': f'Image downloaded for {player.name}'
        })
    else:
        return jsonify({
            'success': False,
            'error': f'No image found for {player.name}. Try setting manually.'
        })


@api_bp.route('/players/<int:player_id>/image', methods=['PUT'])
def update_player_image(player_id):
    """Manually update player image URL"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'error': 'Player not found'}), 404
    
    data = request.get_json()
    image_url = data.get('image_url', '').strip()
    
    # Basic URL validation
    if image_url and not image_url.startswith(('http://', 'https://')):
        return jsonify({'success': False, 'error': 'Invalid URL format'})
    
    player.image_url = image_url if image_url else None
    db.session.commit()
    
    return jsonify({
        'success': True,
        'image_url': player.image_url,
        'message': 'Image URL updated'
    })


@api_bp.route('/players/fetch-all-images', methods=['POST'])
def fetch_all_player_images():
    """Fetch images for all players without images"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    current_league = get_current_league()
    if not current_league:
        return jsonify({'success': False, 'error': 'No league selected'})
    
    # Get players without images
    players = Player.query.filter(
        Player.league_id == current_league.id,
        Player.is_deleted == False,
        (Player.image_url == None) | (Player.image_url == '')
    ).all()
    
    results = {'found': 0, 'not_found': 0, 'players': []}
    
    for player in players:
        local_image_path = search_and_download_player_image(player.id, player.name)
        
        if local_image_path:
            player.image_url = local_image_path
            results['found'] += 1
            results['players'].append({'name': player.name, 'status': 'found', 'image_url': local_image_path})
        else:
            results['not_found'] += 1
            results['players'].append({'name': player.name, 'status': 'not_found'})
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f"Downloaded images for {results['found']} players, {results['not_found']} not found",
        'results': results
    })
