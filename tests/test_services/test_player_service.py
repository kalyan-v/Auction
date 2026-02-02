"""
Tests for the PlayerService.

Tests the business logic for player management operations.
"""

import pytest
from app import db
from app.models import Bid, League, Player, Team
from app.services.player_service import PlayerService
from app.services.base import NotFoundError, ValidationError


class TestPlayerService:
    """Test suite for PlayerService."""

    @pytest.fixture
    def service(self):
        """Create player service instance."""
        return PlayerService()

    @pytest.fixture
    def setup_data(self, app):
        """Set up test data."""
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
                country='Indian',
                base_price=5_000_000,
                current_price=10_000_000,
                status='sold',
                team_id=team.id,
                league_id=league.id
            )
            db.session.add(player)
            db.session.commit()

            yield {
                'league_id': league.id,
                'team_id': team.id,
                'player_id': player.id
            }

    def test_create_player(self, app, service, setup_data):
        """Test creating a new player."""
        with app.app_context():
            result = service.create_player(
                name='New Player',
                league_id=setup_data['league_id'],
                position='Bowler',
                country='Overseas',
                base_price=10_000_000
            )
            assert result['success'] is True
            assert 'player_id' in result

            # Verify player was created
            player = db.session.get(Player, result['player_id'])
            assert player is not None
            assert player.name == 'New Player'
            assert player.position == 'Bowler'

    def test_create_player_requires_name(self, app, service, setup_data):
        """Test that player creation requires a name."""
        with app.app_context():
            with pytest.raises(ValidationError) as exc:
                service.create_player(
                    name='',
                    league_id=setup_data['league_id']
                )
            assert 'name' in str(exc.value).lower()

    def test_create_player_rejects_negative_price(self, app, service, setup_data):
        """Test that negative base price is rejected."""
        with app.app_context():
            with pytest.raises(ValidationError) as exc:
                service.create_player(
                    name='Test',
                    league_id=setup_data['league_id'],
                    base_price=-1000
                )
            assert 'negative' in str(exc.value).lower()

    def test_update_player(self, app, service, setup_data):
        """Test updating a player."""
        with app.app_context():
            result = service.update_player(
                player_id=setup_data['player_id'],
                name='Updated Name',
                position='All-rounder'
            )
            assert result['success'] is True

            player = db.session.get(Player, setup_data['player_id'])
            assert player.name == 'Updated Name'
            assert player.position == 'All-rounder'

    def test_update_player_not_found(self, app, service):
        """Test updating non-existent player."""
        with app.app_context():
            with pytest.raises(NotFoundError):
                service.update_player(player_id=99999, name='Test')

    def test_delete_player(self, app, service, setup_data):
        """Test soft-deleting a player."""
        with app.app_context():
            result = service.delete_player(setup_data['player_id'])
            assert result['success'] is True

            player = db.session.get(Player, setup_data['player_id'])
            assert player.is_deleted is True

    def test_release_player(self, app, service, setup_data):
        """Test releasing a player from their team."""
        with app.app_context():
            # Get initial team budget
            team = db.session.get(Team, setup_data['team_id'])
            initial_budget = team.budget

            result = service.release_player(setup_data['player_id'])
            assert result['success'] is True

            # Verify player is released
            player = db.session.get(Player, setup_data['player_id'])
            assert player.status == 'available'
            assert player.team_id is None

            # Verify team budget was refunded
            db.session.refresh(team)
            assert team.budget > initial_budget

    def test_release_player_not_sold(self, app, service, setup_data):
        """Test releasing a player that isn't sold."""
        with app.app_context():
            # Change player status
            player = db.session.get(Player, setup_data['player_id'])
            player.status = 'available'
            db.session.commit()

            with pytest.raises(ValidationError) as exc:
                service.release_player(setup_data['player_id'])
            assert 'not currently sold' in str(exc.value).lower()

    def test_get_players(self, app, service, setup_data):
        """Test getting all players for a league."""
        with app.app_context():
            players = service.get_players(setup_data['league_id'])
            assert len(players) == 1
            assert players[0]['name'] == 'Test Player'

    def test_get_available_players(self, app, service, setup_data):
        """Test getting available players."""
        with app.app_context():
            # Create an available player
            player = Player(
                name='Available Player',
                status='available',
                league_id=setup_data['league_id']
            )
            db.session.add(player)
            db.session.commit()

            available = service.get_available_players(setup_data['league_id'])
            assert len(available) == 1
            assert available[0].name == 'Available Player'

    def test_get_random_player(self, app, service, setup_data):
        """Test getting a random available player."""
        with app.app_context():
            # Create available players
            for i in range(3):
                player = Player(
                    name=f'Player {i}',
                    status='available',
                    league_id=setup_data['league_id']
                )
                db.session.add(player)
            db.session.commit()

            random_player = service.get_random_player(setup_data['league_id'])
            assert random_player is not None
            assert random_player.status == 'available'

    def test_get_random_player_none_available(self, app, service, setup_data):
        """Test getting random player when none available."""
        with app.app_context():
            result = service.get_random_player(setup_data['league_id'])
            assert result is None
