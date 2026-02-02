"""
Tests for auction bidding functionality.

Tests bid placement, auction start/end, and validation rules.
"""

import pytest
from app import db
from app.models import AuctionState, Bid, Player, Team


class TestPlaceBid:
    """Tests for the bid placement endpoint."""

    def test_bid_requires_auth(self, client, app):
        """Test that placing a bid requires admin authentication."""
        response = client.post('/api/bid',
            json={'player_id': 1, 'team_id': 1, 'amount': 5000000},
            content_type='application/json'
        )
        assert response.status_code == 403

    def test_bid_requires_all_fields(self, auth_client, app):
        """Test that bid requires player_id, team_id, and amount."""
        with app.app_context():
            # Missing amount
            response = auth_client.post('/api/bid',
                json={'player_id': 1, 'team_id': 1},
                content_type='application/json'
            )
            assert response.status_code == 400

    def test_first_bid_at_base_price(self, auth_client, app, sample_league, sample_teams, auction_state):
        """Test that first bid can be at base price."""
        with app.app_context():
            state = db.session.get(AuctionState, auction_state.id)
            player = db.session.get(Player, state.current_player_id)
            team = db.session.get(Team, sample_teams[0].id)

            response = auth_client.post('/api/bid',
                json={
                    'player_id': player.id,
                    'team_id': team.id,
                    'amount': player.base_price  # Exactly base price
                },
                content_type='application/json'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['current_price'] == player.base_price

    def test_subsequent_bid_must_be_higher(self, auth_client, app, sample_league, sample_teams, auction_state):
        """Test that subsequent bids must be higher than current price."""
        with app.app_context():
            state = db.session.get(AuctionState, auction_state.id)
            player = db.session.get(Player, state.current_player_id)
            team1 = db.session.get(Team, sample_teams[0].id)
            team2 = db.session.get(Team, sample_teams[1].id)

            # First bid
            auth_client.post('/api/bid',
                json={
                    'player_id': player.id,
                    'team_id': team1.id,
                    'amount': 5_000_000
                },
                content_type='application/json'
            )

            # Second bid at same price should fail
            response = auth_client.post('/api/bid',
                json={
                    'player_id': player.id,
                    'team_id': team2.id,
                    'amount': 5_000_000  # Same as current
                },
                content_type='application/json'
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'higher' in data['error'].lower()

    def test_bid_rejected_when_insufficient_budget(self, auth_client, app, sample_league, sample_teams, auction_state):
        """Test that bid is rejected when team has insufficient budget."""
        with app.app_context():
            state = db.session.get(AuctionState, auction_state.id)
            player = db.session.get(Player, state.current_player_id)
            team = db.session.get(Team, sample_teams[0].id)

            # Bid more than team budget
            response = auth_client.post('/api/bid',
                json={
                    'player_id': player.id,
                    'team_id': team.id,
                    'amount': 600_000_000  # More than 500M budget
                },
                content_type='application/json'
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'budget' in data['error'].lower() or 'insufficient' in data['error'].lower()

    def test_bid_rejected_when_player_not_bidding(self, auth_client, app, sample_league, sample_teams, sample_player):
        """Test that bid is rejected when player is not in bidding status."""
        with app.app_context():
            player = db.session.get(Player, sample_player.id)
            team = db.session.get(Team, sample_teams[0].id)

            # Player is 'available', not 'bidding'
            response = auth_client.post('/api/bid',
                json={
                    'player_id': player.id,
                    'team_id': team.id,
                    'amount': 5_000_000
                },
                content_type='application/json'
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'auction' in data['error'].lower() or 'bidding' in data['error'].lower()

    def test_bid_records_history(self, auth_client, app, sample_league, sample_teams, auction_state):
        """Test that bids are recorded in bid history."""
        with app.app_context():
            state = db.session.get(AuctionState, auction_state.id)
            player = db.session.get(Player, state.current_player_id)
            team = db.session.get(Team, sample_teams[0].id)

            auth_client.post('/api/bid',
                json={
                    'player_id': player.id,
                    'team_id': team.id,
                    'amount': 5_000_000
                },
                content_type='application/json'
            )

            # Check bid was recorded
            bid = Bid.query.filter_by(player_id=player.id).first()
            assert bid is not None
            assert bid.amount == 5_000_000
            assert bid.team_id == team.id


class TestAuctionStart:
    """Tests for starting an auction."""

    def test_start_auction_requires_auth(self, client, app, sample_player):
        """Test that starting auction requires admin auth."""
        with app.app_context():
            response = client.post(f'/api/auction/start/{sample_player.id}')
            assert response.status_code == 403

    def test_start_auction_sets_player_to_bidding(self, auth_client, app, sample_player):
        """Test that starting auction sets player status to bidding."""
        with app.app_context():
            player = db.session.get(Player, sample_player.id)
            assert player.status == 'available'

            response = auth_client.post(f'/api/auction/start/{player.id}')
            assert response.status_code == 200

            # Refresh from database
            db.session.expire(player)
            assert player.status == 'bidding'

    def test_start_auction_creates_auction_state(self, auth_client, app, sample_player):
        """Test that starting auction creates/updates auction state."""
        with app.app_context():
            player = db.session.get(Player, sample_player.id)

            response = auth_client.post(f'/api/auction/start/{player.id}')
            assert response.status_code == 200

            state = AuctionState.query.first()
            assert state is not None
            assert state.current_player_id == player.id
            assert state.is_active is True

    def test_start_auction_resets_price_to_base(self, auth_client, app, sample_player):
        """Test that starting auction resets player price to base price."""
        with app.app_context():
            player = db.session.get(Player, sample_player.id)
            player.current_price = 10_000_000  # Different from base
            db.session.commit()

            response = auth_client.post(f'/api/auction/start/{player.id}')
            assert response.status_code == 200

            db.session.expire(player)
            assert player.current_price == player.base_price


class TestAuctionEnd:
    """Tests for ending an auction."""

    def test_end_auction_requires_auth(self, client, app):
        """Test that ending auction requires admin auth."""
        response = client.post('/api/auction/end')
        assert response.status_code == 403

    def test_end_auction_assigns_to_highest_bidder(self, auth_client, app, sample_league, sample_teams, auction_state):
        """Test that ending auction assigns player to highest bidder."""
        with app.app_context():
            state = db.session.get(AuctionState, auction_state.id)
            player = db.session.get(Player, state.current_player_id)
            team1 = db.session.get(Team, sample_teams[0].id)
            team2 = db.session.get(Team, sample_teams[1].id)

            # Place bids
            auth_client.post('/api/bid',
                json={'player_id': player.id, 'team_id': team1.id, 'amount': 5_000_000},
                content_type='application/json'
            )
            auth_client.post('/api/bid',
                json={'player_id': player.id, 'team_id': team2.id, 'amount': 6_000_000},
                content_type='application/json'
            )

            # End auction
            response = auth_client.post('/api/auction/end')
            assert response.status_code == 200

            # Refresh and check
            db.session.expire_all()
            player = db.session.get(Player, player.id)
            team2 = db.session.get(Team, team2.id)

            assert player.status == 'sold'
            assert player.team_id == team2.id
            assert team2.budget == 500_000_000 - 6_000_000

    def test_end_auction_marks_unsold_when_no_bids(self, auth_client, app, auction_state):
        """Test that ending auction marks player unsold when no bids."""
        with app.app_context():
            state = db.session.get(AuctionState, auction_state.id)
            player_id = state.current_player_id

            # End auction without any bids
            response = auth_client.post('/api/auction/end')
            assert response.status_code == 200

            player = db.session.get(Player, player_id)
            assert player.status == 'unsold'
            assert player.team_id is None

    def test_end_auction_clears_state(self, auth_client, app, auction_state):
        """Test that ending auction clears the auction state."""
        with app.app_context():
            response = auth_client.post('/api/auction/end')
            assert response.status_code == 200

            state = AuctionState.query.first()
            assert state.is_active is False
            assert state.current_player_id is None


class TestMarkUnsold:
    """Tests for marking a player as unsold."""

    def test_mark_unsold_requires_auth(self, client, app):
        """Test that marking unsold requires admin auth."""
        response = client.post('/api/auction/unsold')
        assert response.status_code == 403

    def test_mark_unsold_sets_status(self, auth_client, app, auction_state):
        """Test that marking unsold sets player status correctly."""
        with app.app_context():
            state = db.session.get(AuctionState, auction_state.id)
            player_id = state.current_player_id

            response = auth_client.post('/api/auction/unsold')
            assert response.status_code == 200

            player = db.session.get(Player, player_id)
            assert player.status == 'unsold'
