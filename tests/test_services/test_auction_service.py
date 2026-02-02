"""
Tests for the AuctionService.

Tests the business logic for bidding, auction lifecycle, and price management.
"""

import pytest
from app import db
from app.models import AuctionState, Bid, League, Player, Team
from app.services.auction_service import AuctionService
from app.services.base import NotFoundError, ValidationError


class TestAuctionService:
    """Test suite for AuctionService."""

    @pytest.fixture
    def service(self):
        """Create auction service instance."""
        return AuctionService()

    @pytest.fixture
    def setup_auction(self, app):
        """Set up test data for auction tests."""
        with app.app_context():
            # Create league
            league = League(name='Test League', default_purse=500_000_000)
            db.session.add(league)
            db.session.flush()

            # Create team
            team = Team(
                name='Test Team',
                budget=100_000_000,
                initial_budget=100_000_000,
                league_id=league.id
            )
            db.session.add(team)
            db.session.flush()

            # Create player
            player = Player(
                name='Test Player',
                position='Batter',
                base_price=5_000_000,
                current_price=5_000_000,
                status='bidding',
                league_id=league.id
            )
            db.session.add(player)
            db.session.flush()

            # Create auction state
            auction_state = AuctionState(
                current_player_id=player.id,
                is_active=True,
                time_remaining=300
            )
            db.session.add(auction_state)
            db.session.commit()

            yield {
                'league_id': league.id,
                'team_id': team.id,
                'player_id': player.id
            }

    def test_place_bid_success(self, app, service, setup_auction):
        """Test successful bid placement."""
        with app.app_context():
            result = service.place_bid(
                player_id=setup_auction['player_id'],
                team_id=setup_auction['team_id'],
                amount=5_000_000
            )
            assert result['success'] is True
            assert result['current_price'] == 5_000_000

            # Verify bid was recorded
            bid = Bid.query.filter_by(
                player_id=setup_auction['player_id']
            ).first()
            assert bid is not None
            assert bid.amount == 5_000_000

    def test_place_bid_rejects_low_first_bid(self, app, service, setup_auction):
        """Test that first bid below base price is rejected."""
        with app.app_context():
            with pytest.raises(ValidationError) as exc:
                service.place_bid(
                    player_id=setup_auction['player_id'],
                    team_id=setup_auction['team_id'],
                    amount=1_000_000  # Below base price
                )
            assert 'base price' in str(exc.value).lower()

    def test_place_bid_rejects_insufficient_budget(self, app, service, setup_auction):
        """Test that bid exceeding team budget is rejected."""
        with app.app_context():
            with pytest.raises(ValidationError) as exc:
                service.place_bid(
                    player_id=setup_auction['player_id'],
                    team_id=setup_auction['team_id'],
                    amount=500_000_000  # Exceeds budget
                )
            assert 'budget' in str(exc.value).lower()

    def test_place_bid_rejects_when_player_not_bidding(self, app, service, setup_auction):
        """Test that bid is rejected when player is not in bidding status."""
        with app.app_context():
            # Change player status
            player = db.session.get(Player, setup_auction['player_id'])
            player.status = 'available'
            db.session.commit()

            with pytest.raises(ValidationError) as exc:
                service.place_bid(
                    player_id=setup_auction['player_id'],
                    team_id=setup_auction['team_id'],
                    amount=5_000_000
                )
            assert 'not up for auction' in str(exc.value).lower()

    def test_start_auction_success(self, app, service):
        """Test starting an auction."""
        with app.app_context():
            # Create necessary data
            league = League(name='Test League')
            db.session.add(league)
            db.session.flush()

            player = Player(
                name='New Player',
                base_price=5_000_000,
                status='available',
                league_id=league.id
            )
            db.session.add(player)
            db.session.commit()

            result = service.start_auction(player.id)
            assert result['success'] is True

            # Verify player status changed
            db.session.refresh(player)
            assert player.status == 'bidding'
            assert player.current_price == player.base_price

    def test_start_auction_not_found(self, app, service):
        """Test starting auction for non-existent player."""
        with app.app_context():
            with pytest.raises(NotFoundError):
                service.start_auction(99999)

    def test_end_auction_with_bids(self, app, service, setup_auction):
        """Test ending auction assigns player to highest bidder."""
        with app.app_context():
            # Place a bid
            service.place_bid(
                player_id=setup_auction['player_id'],
                team_id=setup_auction['team_id'],
                amount=10_000_000
            )

            result = service.end_auction()
            assert result['success'] is True

            # Verify player is sold
            player = db.session.get(Player, setup_auction['player_id'])
            assert player.status == 'sold'
            assert player.team_id == setup_auction['team_id']

            # Verify team budget decreased
            team = db.session.get(Team, setup_auction['team_id'])
            assert team.budget == 90_000_000

    def test_end_auction_no_bids(self, app, service, setup_auction):
        """Test ending auction with no bids marks player as unsold."""
        with app.app_context():
            result = service.end_auction()
            assert result['success'] is True

            # Verify player is unsold
            player = db.session.get(Player, setup_auction['player_id'])
            assert player.status == 'unsold'

    def test_mark_unsold(self, app, service, setup_auction):
        """Test marking player as unsold."""
        with app.app_context():
            result = service.mark_unsold()
            assert result['success'] is True

            player = db.session.get(Player, setup_auction['player_id'])
            assert player.status == 'unsold'
            assert player.current_price == 0

    def test_reset_price(self, app, service, setup_auction):
        """Test resetting player price."""
        with app.app_context():
            # Place some bids
            service.place_bid(
                player_id=setup_auction['player_id'],
                team_id=setup_auction['team_id'],
                amount=10_000_000
            )

            # Reset to lower price
            result = service.reset_price(7_000_000)
            assert result['success'] is True
            assert result['new_price'] == 7_000_000

            # Verify high bids were soft deleted (not visible in active queries)
            active_high_bids = Bid.query.filter(
                Bid.player_id == setup_auction['player_id'],
                Bid.amount > 7_000_000,
                Bid.is_deleted.is_(False)
            ).count()
            assert active_high_bids == 0

            # Verify the bid still exists but is marked as deleted
            deleted_high_bids = Bid.query.filter(
                Bid.player_id == setup_auction['player_id'],
                Bid.amount > 7_000_000,
                Bid.is_deleted.is_(True)
            ).count()
            assert deleted_high_bids == 1
