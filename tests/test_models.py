"""
Tests for database models.

Tests model creation, relationships, and constraints.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import League, Team, Player, Bid


class TestLeagueModel:
    """Tests for the League model."""

    def test_create_league(self, app):
        """Test creating a league."""
        with app.app_context():
            league = League(
                name='test_league',
                display_name='Test League',
                default_purse=500_000_000
            )
            db.session.add(league)
            db.session.commit()

            assert league.id is not None
            assert league.name == 'test_league'
            assert league.is_deleted is False

    def test_league_soft_delete(self, app, sample_league):
        """Test soft delete preserves the record."""
        with app.app_context():
            league = db.session.get(League, sample_league.id)
            league.is_deleted = True
            db.session.commit()

            # Record still exists
            league = db.session.get(League, sample_league.id)
            assert league is not None
            assert league.is_deleted is True


class TestTeamModel:
    """Tests for the Team model."""

    def test_create_team(self, app, sample_league):
        """Test creating a team."""
        with app.app_context():
            team = Team(
                name='Test Team',
                budget=500_000_000,
                initial_budget=500_000_000,
                league_id=sample_league.id
            )
            db.session.add(team)
            db.session.commit()

            assert team.id is not None
            assert team.budget == 500_000_000

    def test_team_league_relationship(self, app, sample_league):
        """Test team-league relationship."""
        with app.app_context():
            team = Team(
                name='Test Team',
                budget=500_000_000,
                league_id=sample_league.id
            )
            db.session.add(team)
            db.session.commit()

            # Refresh to get relationship
            db.session.expire(team)
            assert team.league is not None
            assert team.league.id == sample_league.id


class TestPlayerModel:
    """Tests for the Player model."""

    def test_create_player(self, app, sample_league):
        """Test creating a player."""
        with app.app_context():
            player = Player(
                name='Test Player',
                position='Batter',
                country='India',
                base_price=5_000_000,
                status='available',
                league_id=sample_league.id
            )
            db.session.add(player)
            db.session.commit()

            assert player.id is not None
            assert player.status == 'available'

    def test_player_team_relationship(self, app, sample_league, sample_teams):
        """Test player-team relationship."""
        with app.app_context():
            team = db.session.get(Team, sample_teams[0].id)

            player = Player(
                name='Test Player',
                position='Batter',
                base_price=5_000_000,
                status='sold',
                league_id=sample_league.id,
                team_id=team.id
            )
            db.session.add(player)
            db.session.commit()

            db.session.expire(player)
            assert player.team is not None
            assert player.team.name == 'Team Alpha'

    def test_player_default_values(self, app, sample_league):
        """Test player default values."""
        with app.app_context():
            player = Player(
                name='Test Player',
                position='Batter',
                base_price=5_000_000,
                league_id=sample_league.id
            )
            db.session.add(player)
            db.session.commit()

            assert player.status == 'available'
            assert player.fantasy_points == 0
            assert player.is_deleted is False


class TestBidModel:
    """Tests for the Bid model."""

    def test_create_bid(self, app, sample_league, sample_teams, sample_player):
        """Test creating a bid."""
        with app.app_context():
            team = db.session.get(Team, sample_teams[0].id)
            player = db.session.get(Player, sample_player.id)

            bid = Bid(
                player_id=player.id,
                team_id=team.id,
                amount=5_000_000
            )
            db.session.add(bid)
            db.session.commit()

            assert bid.id is not None
            assert bid.timestamp is not None

    def test_bid_relationships(self, app, sample_league, sample_teams, sample_player):
        """Test bid relationships to player and team."""
        with app.app_context():
            team = db.session.get(Team, sample_teams[0].id)
            player = db.session.get(Player, sample_player.id)

            bid = Bid(
                player_id=player.id,
                team_id=team.id,
                amount=5_000_000
            )
            db.session.add(bid)
            db.session.commit()

            db.session.expire(bid)
            assert bid.player is not None
            assert bid.team is not None
            assert bid.player.name == 'Test Player'
            assert bid.team.name == 'Team Alpha'
