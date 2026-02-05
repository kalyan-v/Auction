"""
Tests for fantasy service functionality.

Tests cover:
- Fantasy point entry management
- Playoff match number parsing
- Player name matching
"""

import pytest
from unittest.mock import MagicMock, patch

from app import db
from app.constants import PLAYOFF_MATCH_NUMBERS
from app.models import FantasyPointEntry, Player
from app.services.fantasy_service import fantasy_service


class TestPlayoffMatchNumbers:
    """Tests for playoff match number parsing."""

    def test_playoff_match_numbers_constant_exists(self):
        """Verify PLAYOFF_MATCH_NUMBERS constant is defined."""
        assert PLAYOFF_MATCH_NUMBERS is not None
        assert isinstance(PLAYOFF_MATCH_NUMBERS, dict)

    def test_playoff_match_numbers_contains_eliminator(self):
        """Verify eliminator is mapped correctly."""
        assert 'eliminator' in PLAYOFF_MATCH_NUMBERS
        assert PLAYOFF_MATCH_NUMBERS['eliminator'] == 100

    def test_playoff_match_numbers_contains_qualifiers(self):
        """Verify qualifiers are mapped correctly."""
        assert PLAYOFF_MATCH_NUMBERS.get('qualifier 1') == 101
        assert PLAYOFF_MATCH_NUMBERS.get('qualifier1') == 101
        assert PLAYOFF_MATCH_NUMBERS.get('qualifier 2') == 102
        assert PLAYOFF_MATCH_NUMBERS.get('qualifier2') == 102

    def test_playoff_match_numbers_contains_final(self):
        """Verify final is mapped correctly."""
        assert 'final' in PLAYOFF_MATCH_NUMBERS
        assert PLAYOFF_MATCH_NUMBERS['final'] == 200

    def test_playoff_numbers_are_high_enough(self):
        """Verify playoff numbers don't conflict with league matches."""
        # League matches are typically 1-70, playoffs should be 100+
        for match_type, number in PLAYOFF_MATCH_NUMBERS.items():
            assert number >= 100, f"{match_type} should have number >= 100"


class TestFantasyPointEntry:
    """Tests for fantasy point entry creation."""

    def test_create_fantasy_point_entry(self, app, sample_league, sample_player):
        """Test creating a fantasy point entry."""
        with app.app_context():
            player = db.session.get(Player, sample_player.id)

            entry = FantasyPointEntry(
                player_id=player.id,
                match_number=1,
                game_id='test_game_001',
                points=50.0,
                league_id=sample_league.id
            )
            db.session.add(entry)
            db.session.commit()

            assert entry.id is not None
            assert entry.points == 50.0
            assert entry.game_id == 'test_game_001'

    def test_create_playoff_entry(self, app, sample_league, sample_player):
        """Test creating an entry for a playoff match."""
        with app.app_context():
            player = db.session.get(Player, sample_player.id)

            # Use eliminator match number from constants
            entry = FantasyPointEntry(
                player_id=player.id,
                match_number=PLAYOFF_MATCH_NUMBERS['eliminator'],
                game_id='eliminator_game_001',
                points=75.0,
                league_id=sample_league.id
            )
            db.session.add(entry)
            db.session.commit()

            assert entry.match_number == 100
            assert entry.points == 75.0

    def test_entry_soft_delete(self, app, sample_league, sample_player):
        """Test soft deleting a fantasy point entry."""
        with app.app_context():
            player = db.session.get(Player, sample_player.id)

            entry = FantasyPointEntry(
                player_id=player.id,
                match_number=1,
                game_id='delete_test_001',
                points=30.0,
                league_id=sample_league.id
            )
            db.session.add(entry)
            db.session.commit()

            # Soft delete
            entry.is_deleted = True
            db.session.commit()

            # Should not appear in non-deleted queries
            active_entries = FantasyPointEntry.query.filter_by(
                player_id=player.id,
                is_deleted=False
            ).all()
            assert len(active_entries) == 0


class TestPlayerNameMatching:
    """Tests for player name matching functionality."""

    def test_find_player_exact_match(self, app, sample_league):
        """Test finding player by exact name match."""
        with app.app_context():
            league = db.session.get(Player, sample_league.id)

            # Create a player
            player = Player(
                name='Smriti Mandhana',
                position='Batter',
                country='India',
                base_price=5_000_000,
                league_id=sample_league.id
            )
            db.session.add(player)
            db.session.commit()

            # Find by exact name
            found = fantasy_service.find_player_by_name('Smriti Mandhana', sample_league.id)
            assert found is not None
            assert found.name == 'Smriti Mandhana'

    def test_find_player_case_insensitive(self, app, sample_league):
        """Test finding player with different case."""
        with app.app_context():
            player = Player(
                name='Beth Mooney',
                position='Keeper',
                country='Overseas',
                base_price=5_000_000,
                league_id=sample_league.id
            )
            db.session.add(player)
            db.session.commit()

            # Find with different case
            found = fantasy_service.find_player_by_name('beth mooney', sample_league.id)
            assert found is not None
            assert found.name == 'Beth Mooney'

    def test_find_player_not_found(self, app, sample_league):
        """Test that non-existent player returns None."""
        with app.app_context():
            found = fantasy_service.find_player_by_name('Nonexistent Player', sample_league.id)
            assert found is None


class TestFantasyService:
    """Tests for fantasy service methods."""

    def test_add_match_points_to_player(self, app, sample_league, sample_player):
        """Test adding fantasy points to a player."""
        with app.app_context():
            player = db.session.get(Player, sample_player.id)
            player.status = 'sold'  # Player must be sold to have points
            db.session.commit()

            result = fantasy_service.add_match_points(
                player_id=player.id,
                match_number=1,
                points=50.0,
                league_id=sample_league.id
            )

            assert result['success'] is True
            assert result['points'] == 50.0

    def test_add_match_points_creates_entry(self, app, sample_league, sample_player):
        """Test that adding points creates a FantasyPointEntry."""
        with app.app_context():
            player = db.session.get(Player, sample_player.id)
            player.status = 'sold'
            db.session.commit()

            fantasy_service.add_match_points(
                player_id=player.id,
                match_number=5,
                points=75.0,
                league_id=sample_league.id
            )

            entries = FantasyPointEntry.query.filter_by(
                player_id=player.id,
                is_deleted=False
            ).all()
            assert len(entries) == 1
            assert entries[0].match_number == 5
            assert entries[0].points == 75.0

    def test_update_existing_match_points(self, app, sample_league, sample_player):
        """Test updating points for an existing match (add_match_points updates if exists)."""
        with app.app_context():
            player = db.session.get(Player, sample_player.id)
            player.status = 'sold'
            db.session.commit()

            # Add initial points
            fantasy_service.add_match_points(
                player_id=player.id,
                match_number=3,
                points=40.0,
                league_id=sample_league.id
            )

            # Update points for same match (add_match_points updates existing)
            result = fantasy_service.add_match_points(
                player_id=player.id,
                match_number=3,
                points=60.0,
                league_id=sample_league.id
            )

            assert result['success'] is True
            assert result['points'] == 60.0

            # Verify update - should only be one entry
            entries = FantasyPointEntry.query.filter_by(
                player_id=player.id,
                match_number=3,
                is_deleted=False
            ).all()
            assert len(entries) == 1
            assert entries[0].points == 60.0

    def test_delete_match_points(self, app, sample_league, sample_player):
        """Test deleting points for a specific match."""
        with app.app_context():
            player = db.session.get(Player, sample_player.id)
            player.status = 'sold'
            db.session.commit()

            # Add points
            fantasy_service.add_match_points(
                player_id=player.id,
                match_number=7,
                points=55.0,
                league_id=sample_league.id
            )

            entry = FantasyPointEntry.query.filter_by(
                player_id=player.id,
                match_number=7,
                is_deleted=False
            ).first()

            # Delete the entry
            result = fantasy_service.delete_match_points(entry.id)
            assert result['success'] is True

            # Verify soft deleted
            deleted_entry = db.session.get(FantasyPointEntry, entry.id)
            assert deleted_entry.is_deleted is True

    def test_total_points_calculated_correctly(self, app, sample_league, sample_player):
        """Test that total points are calculated correctly from entries."""
        with app.app_context():
            player = db.session.get(Player, sample_player.id)
            player.status = 'sold'
            db.session.commit()

            # Add multiple match entries
            fantasy_service.add_match_points(player.id, 1, 30.0, sample_league.id)
            fantasy_service.add_match_points(player.id, 2, 45.0, sample_league.id)
            fantasy_service.add_match_points(player.id, 3, 25.0, sample_league.id)

            # Verify total is correct
            updated_player = db.session.get(Player, player.id)
            assert updated_player.fantasy_points == 100.0
