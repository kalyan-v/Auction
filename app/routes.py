from flask import Blueprint, render_template, jsonify, request, current_app, session, redirect, url_for
from datetime import datetime
from zoneinfo import ZoneInfo
from functools import wraps
from app import db
from app.models import Team, Player, Bid, AuctionState

def is_admin():
    """Check if current user is logged in as admin"""
    return session.get('is_admin', False)

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
    """Home page"""
    return render_template('index.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if (username == current_app.config['ADMIN_USERNAME'] and 
            password == current_app.config['ADMIN_PASSWORD']):
            session['is_admin'] = True
            return redirect(request.args.get('next') or url_for('main.setup'))
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
    teams = Team.query.all()
    players = Player.query.all()
    return render_template('setup.html', teams=teams, players=players, admin_mode=is_admin())

@main_bp.route('/squads')
def squads():
    """View all team squads with players and budgets"""
    teams = Team.query.all()
    return render_template('squads.html', teams=teams, admin_mode=is_admin())

@auction_bp.route('/')
def auction_room():
    """Main auction interface"""
    teams = Team.query.all()
    players = Player.query.filter_by(status='available').all()
    unsold_players = Player.query.filter_by(status='unsold').all()
    auction_state = AuctionState.query.first()
    return render_template('auction.html', teams=teams, players=players, unsold_players=unsold_players, auction_state=auction_state, admin_mode=is_admin())

# API endpoints
@api_bp.route('/teams', methods=['GET', 'POST'])
def manage_teams():
    """Get all teams or create a new team"""
    if request.method == 'POST':
        if not is_admin():
            return jsonify({'success': False, 'error': 'Admin login required'}), 403
        data = request.get_json()
        budget = data.get('budget', 500000000)
        team = Team(name=data['name'], budget=budget, initial_budget=budget)
        db.session.add(team)
        db.session.commit()
        return jsonify({'success': True, 'team_id': team.id})
    
    teams = Team.query.all()
    return jsonify([{'id': t.id, 'name': t.name, 'budget': t.budget} for t in teams])

@api_bp.route('/players', methods=['GET', 'POST'])
def manage_players():
    """Get all players or create a new player"""
    if request.method == 'POST':
        if not is_admin():
            return jsonify({'success': False, 'error': 'Admin login required'}), 403
        data = request.get_json()
        player = Player(
            name=data['name'],
            position=data.get('position', ''),
            country=data.get('country', 'Indian'),
            base_price=data.get('base_price', 100000)
        )
        db.session.add(player)
        db.session.commit()
        return jsonify({'success': True, 'player_id': player.id})
    
    players = Player.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'position': p.position,
        'country': p.country,
        'base_price': p.base_price,
        'status': p.status
    } for p in players])

@api_bp.route('/players/<int:player_id>', methods=['PUT', 'DELETE'])
def update_player(player_id):
    """Update or delete a player"""
    if not is_admin():
        return jsonify({'success': False, 'error': 'Admin login required'}), 403
    
    player = Player.query.get(player_id)
    if not player:
        return jsonify({'success': False, 'error': 'Player not found'})
    
    if request.method == 'DELETE':
        # Check if player is in active auction
        auction_state = AuctionState.query.first()
        if auction_state and auction_state.current_player_id == player_id:
            auction_state.current_player_id = None
            auction_state.is_active = False
        
        Bid.query.filter_by(player_id=player_id).delete()
        db.session.delete(player)
        db.session.commit()
        return jsonify({'success': True})
    
    data = request.get_json()
    player.name = data.get('name', player.name)
    player.position = data.get('position', player.position)
    player.country = data.get('country', player.country)
    player.base_price = data.get('base_price', player.base_price)
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
    position = request.args.get('position', '')
    include_unsold = request.args.get('include_unsold', 'false') == 'true'
    
    if include_unsold:
        query = Player.query.filter(Player.status.in_(['available', 'unsold']))
    else:
        query = Player.query.filter_by(status='available')
    
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
    position = request.args.get('position', '')
    include_unsold = request.args.get('include_unsold', 'false') == 'true'
    
    if include_unsold:
        query = Player.query.filter(Player.status.in_(['available', 'unsold']))
    else:
        query = Player.query.filter_by(status='available')
    
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
        return jsonify({'success': False, 'error': 'Player not found'})
    
    bids = Bid.query.filter_by(player_id=player_id).order_by(Bid.amount.desc()).all()
    
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
    
    if amount <= player.current_price:
        return jsonify({'success': False, 'error': 'Bid too low'})
    
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
    player.current_price = new_price
    
    # Clear bids for this player above the new price (optional - keeps history clean)
    Bid.query.filter(Bid.player_id == player.id, Bid.amount > new_price).delete()
    
    db.session.commit()
    
    return jsonify({'success': True, 'new_price': new_price})
