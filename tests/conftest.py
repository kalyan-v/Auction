"""
Pytest fixtures for WPL Auction application tests.

Provides fixtures for app, client, database, and sample data.
"""

import pytest
from app import create_app, db
from app.models import AuctionState, Bid, League, Player, Team


@pytest.fixture
def app():
    """Create application for testing with fresh database."""
    app = create_app('testing')

    # Disable CSRF for testing
    app.config['WTF_CSRF_ENABLED'] = False
    # Disable rate limiting for testing
    app.config['RATELIMIT_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client for making requests."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def auth_client(client, app):
    """Authenticated test client with admin session."""
    with client.session_transaction() as session:
        session['is_admin'] = True
    return client


@pytest.fixture
def sample_league(app):
    """Create a sample league for testing."""
    with app.app_context():
        league = League(
            name='test_league',
            display_name='Test League',
            default_purse=500_000_000,
            max_squad_size=15,
            min_squad_size=11
        )
        db.session.add(league)
        db.session.commit()

        # Return a fresh query to avoid detached instance
        league_id = league.id
        yield db.session.get(League, league_id)


@pytest.fixture
def sample_teams(app, sample_league):
    """Create sample teams for testing."""
    with app.app_context():
        league = db.session.get(League, sample_league.id)

        team1 = Team(
            name='Team Alpha',
            budget=500_000_000,
            initial_budget=500_000_000,
            league_id=league.id
        )
        team2 = Team(
            name='Team Beta',
            budget=500_000_000,
            initial_budget=500_000_000,
            league_id=league.id
        )

        db.session.add_all([team1, team2])
        db.session.commit()

        # Return fresh queries
        yield [
            db.session.get(Team, team1.id),
            db.session.get(Team, team2.id)
        ]


@pytest.fixture
def sample_player(app, sample_league):
    """Create a sample player for testing."""
    with app.app_context():
        league = db.session.get(League, sample_league.id)

        player = Player(
            name='Test Player',
            position='Batter',
            country='India',
            base_price=5_000_000,
            current_price=5_000_000,
            status='available',
            league_id=league.id
        )
        db.session.add(player)
        db.session.commit()

        yield db.session.get(Player, player.id)


@pytest.fixture
def sample_players(app, sample_league):
    """Create multiple sample players for testing."""
    with app.app_context():
        league = db.session.get(League, sample_league.id)

        players = [
            Player(
                name=f'Player {i}',
                position='Batter' if i % 2 == 0 else 'Bowler',
                country='India',
                base_price=5_000_000,
                current_price=5_000_000,
                status='available',
                league_id=league.id
            )
            for i in range(5)
        ]

        db.session.add_all(players)
        db.session.commit()

        yield [db.session.get(Player, p.id) for p in players]


@pytest.fixture
def auction_state(app, sample_player):
    """Create an active auction state with a player in bidding."""
    with app.app_context():
        player = db.session.get(Player, sample_player.id)
        player.status = 'bidding'

        state = AuctionState(
            current_player_id=player.id,
            is_active=True,
            time_remaining=300
        )
        db.session.add(state)
        db.session.commit()

        yield db.session.get(AuctionState, state.id)
