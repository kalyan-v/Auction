"""
League service for managing league operations.

Encapsulates all business logic related to:
- League CRUD operations
- League validation
"""

import json
import re
from typing import List, Optional

from app import db
from app.enums import LeagueType
from app.logger import get_logger
from app.models import AuctionCategory, League
from app.repositories.league_repository import LeagueRepository
from app.services.base import BaseService, NotFoundError, ValidationError

logger = get_logger(__name__)

# Validation constants
MAX_LEAGUE_NAME_LENGTH = 50
MAX_DISPLAY_NAME_LENGTH = 100
LEAGUE_NAME_PATTERN = re.compile(r'^[\w\s\-]+$')
VALID_LEAGUE_TYPES = {lt.value for lt in LeagueType}


class LeagueService(BaseService):
    """Service for league-related operations.

    Handles league CRUD with proper validation and transaction management.
    """

    def __init__(self, league_repo: Optional[LeagueRepository] = None):
        """Initialize service with optional repository injection.

        Args:
            league_repo: LeagueRepository instance (defaults to new instance).
        """
        self.league_repo = league_repo or LeagueRepository()

    def _validate_league_name(self, name: str) -> None:
        """Validate league name format.

        Args:
            name: League name to validate.

        Raises:
            ValidationError: If name is invalid.
        """
        if not name or not name.strip():
            raise ValidationError('League name is required')
        name = name.strip()
        if len(name) > MAX_LEAGUE_NAME_LENGTH:
            raise ValidationError(
                f'League name must be {MAX_LEAGUE_NAME_LENGTH} characters or less'
            )
        if not LEAGUE_NAME_PATTERN.match(name):
            raise ValidationError(
                'League name can only contain letters, numbers, spaces, '
                'underscores, and hyphens'
            )

    def _validate_display_name(self, display_name: str) -> None:
        """Validate display name format.

        Args:
            display_name: Display name to validate.

        Raises:
            ValidationError: If display name is invalid.
        """
        if len(display_name) > MAX_DISPLAY_NAME_LENGTH:
            raise ValidationError(
                f'Display name must be {MAX_DISPLAY_NAME_LENGTH} characters or less'
            )

    def _validate_purse(self, default_purse: float) -> None:
        """Validate default purse value.

        Args:
            default_purse: Purse value to validate.

        Raises:
            ValidationError: If purse is invalid.
        """
        if default_purse <= 0:
            raise ValidationError('Default purse must be positive')

    def _validate_squad_sizes(self, min_squad: int, max_squad: int) -> None:
        """Validate squad size constraints.

        Args:
            min_squad: Minimum squad size.
            max_squad: Maximum squad size.

        Raises:
            ValidationError: If squad sizes are invalid.
        """
        if min_squad <= 0:
            raise ValidationError('Minimum squad size must be positive')
        if max_squad <= 0:
            raise ValidationError('Maximum squad size must be positive')
        if min_squad > max_squad:
            raise ValidationError(
                'Minimum squad size cannot be greater than maximum'
            )

    def _validate_bid_increment_tiers(self, tiers: list) -> None:
        """Validate bid increment tiers structure.

        Args:
            tiers: List of {threshold, increment} dicts.

        Raises:
            ValidationError: If tiers are invalid.
        """
        if not tiers or not isinstance(tiers, list):
            raise ValidationError('Bid increment tiers must be a non-empty list')
        for tier in tiers:
            if not isinstance(tier, dict):
                raise ValidationError('Each tier must be an object with threshold and increment')
            if 'threshold' not in tier or 'increment' not in tier:
                raise ValidationError('Each tier must have threshold and increment')
            try:
                threshold = int(tier['threshold'])
                increment = int(tier['increment'])
            except (TypeError, ValueError):
                raise ValidationError('Threshold and increment must be numbers')
            if threshold < 0:
                raise ValidationError('Threshold must be non-negative')
            if increment <= 0:
                raise ValidationError('Increment must be positive')

        has_base_tier = any(int(t['threshold']) == 0 for t in tiers)
        if not has_base_tier:
            raise ValidationError(
                'Bid increment tiers must include a base tier with threshold 0'
            )

    def _create_auction_categories(
        self, league_id: int, category_names: List[str]
    ) -> None:
        """Create auction categories for a league (must be called within a transaction)."""
        seen: set[str] = set()
        for i, cat_name in enumerate(category_names):
            cat_name = cat_name.strip()
            if cat_name and cat_name.lower() not in seen:
                seen.add(cat_name.lower())
                category = AuctionCategory(
                    name=cat_name,
                    league_id=league_id,
                    sort_order=i
                )
                db.session.add(category)

    def create_league(
        self,
        name: str,
        display_name: Optional[str] = None,
        default_purse: float = 500000000,
        max_squad_size: int = 20,
        min_squad_size: int = 16,
        bid_increment_tiers: Optional[list] = None,
        max_rtm: int = 0,
        league_type: str = 'wpl',
        auction_categories: Optional[List[str]] = None
    ) -> dict:
        """Create a new league.

        Args:
            name: League name (unique).
            display_name: Human-readable league name (defaults to name).
            default_purse: Default team budget.
            max_squad_size: Maximum players per team.
            min_squad_size: Minimum players per team.
            bid_increment_tiers: List of {threshold, increment} dicts.
            max_rtm: Maximum RTM allowed per team (0 = disabled).
            league_type: League type (e.g., 'wpl', 'ipl').
            auction_categories: Optional list of auction category names.

        Returns:
            Dict with success status and league ID.

        Raises:
            ValidationError: If validation fails.
        """
        name = name.strip() if name else ''
        self._validate_league_name(name)

        display_name = (display_name or name).strip()
        self._validate_display_name(display_name)
        self._validate_purse(default_purse)
        self._validate_squad_sizes(min_squad_size, max_squad_size)

        # Validate league type
        if league_type not in VALID_LEAGUE_TYPES:
            raise ValidationError(
                f'Invalid league type. Valid: {", ".join(sorted(VALID_LEAGUE_TYPES))}'
            )

        # Validate and serialize bid increment tiers
        if bid_increment_tiers is None:
            bid_increment_tiers = [{'threshold': 0, 'increment': 2500000}]
        self._validate_bid_increment_tiers(bid_increment_tiers)
        bid_increment_tiers_json = json.dumps(bid_increment_tiers)

        # Check for duplicate league name
        existing = self.league_repo.find_by_name(name)
        if existing:
            raise ValidationError('A league with this name already exists')

        with self.transaction():
            # If this is the first league, mark it as active
            existing_active = League.query.filter_by(is_active=True, is_deleted=False).first()

            league = League(
                name=name,
                display_name=display_name,
                default_purse=default_purse,
                max_squad_size=max_squad_size,
                min_squad_size=min_squad_size,
                bid_increment_tiers=bid_increment_tiers_json,
                max_rtm=max_rtm,
                league_type=league_type,
                is_active=not existing_active  # First league auto-activates
            )
            db.session.add(league)
            self.flush()

            # Create auction categories if provided
            if auction_categories:
                self._create_auction_categories(league.id, auction_categories)

            logger.info(f"Created league: {league.name} (ID: {league.id})")

            return {'success': True, 'league_id': league.id}

    def update_league(
        self,
        league_id: int,
        name: Optional[str] = None,
        display_name: Optional[str] = None,
        default_purse: Optional[float] = None,
        max_squad_size: Optional[int] = None,
        min_squad_size: Optional[int] = None,
        bid_increment_tiers: Optional[list] = None,
        max_rtm: Optional[int] = None,
        league_type: Optional[str] = None,
        auction_categories: Optional[List[str]] = None
    ) -> dict:
        """Update an existing league.

        Args:
            league_id: ID of the league to update.
            name: New name (optional).
            display_name: New display name (optional).
            default_purse: New default purse (optional).
            max_squad_size: New max squad size (optional).
            min_squad_size: New min squad size (optional).
            bid_increment_tiers: New bid increment tiers (optional).
            max_rtm: New max RTM per team (optional).
            league_type: New league type (optional).
            auction_categories: New auction category names (optional).

        Returns:
            Dict with success status.

        Raises:
            NotFoundError: If league not found.
            ValidationError: If validation fails.
        """
        with self.transaction():
            league = self.league_repo.get(league_id)
            if not league:
                raise NotFoundError('League not found')

            if name is not None:
                name = name.strip()
                self._validate_league_name(name)
                # Check for duplicate (excluding current league)
                existing = self.league_repo.first_by(name=name, is_deleted=False)
                if existing and existing.id != league_id:
                    raise ValidationError('A league with this name already exists')
                league.name = name

            if display_name is not None:
                display_name = display_name.strip()
                self._validate_display_name(display_name)
                league.display_name = display_name

            if default_purse is not None:
                self._validate_purse(default_purse)
                league.default_purse = default_purse

            # Handle squad sizes - need to validate together
            new_min = min_squad_size if min_squad_size is not None else league.min_squad_size
            new_max = max_squad_size if max_squad_size is not None else league.max_squad_size

            if min_squad_size is not None or max_squad_size is not None:
                self._validate_squad_sizes(new_min, new_max)
                league.min_squad_size = new_min
                league.max_squad_size = new_max

            if bid_increment_tiers is not None:
                self._validate_bid_increment_tiers(bid_increment_tiers)
                league.bid_increment_tiers = json.dumps(bid_increment_tiers)

            if league_type is not None:
                if league_type not in VALID_LEAGUE_TYPES:
                    raise ValidationError(
                        f'Invalid league type. Valid: {", ".join(sorted(VALID_LEAGUE_TYPES))}'
                    )
                league.league_type = league_type

            if max_rtm is not None:
                if max_rtm < 0:
                    raise ValidationError('Max RTM cannot be negative')
                league.max_rtm = max_rtm

            # Update auction categories if provided
            if auction_categories is not None:
                # Soft-delete existing categories
                existing_cats = AuctionCategory.query.filter_by(
                    league_id=league_id, is_deleted=False
                ).all()
                for cat in existing_cats:
                    cat.is_deleted = True
                # Add new categories
                self._create_auction_categories(league_id, auction_categories)

            logger.info(f"Updated league: {league.name}")

            return {'success': True}

    def delete_league(self, league_id: int) -> dict:
        """Soft-delete a league.

        Args:
            league_id: ID of the league to delete.

        Returns:
            Dict with success status.

        Raises:
            NotFoundError: If league not found.
        """
        with self.transaction():
            league = self.league_repo.get(league_id)
            if not league:
                raise NotFoundError('League not found')

            self.league_repo.soft_delete(league)

            logger.info(f"Deleted league: {league.name}")

            return {'success': True}

    def get_leagues(self) -> List[dict]:
        """Get all active leagues.

        Returns:
            List of league dictionaries.
        """
        leagues = self.league_repo.get_active()

        return [{
            'id': league.id,
            'name': league.name,
            'display_name': league.display_name,
            'league_type': league.league_type,
            'default_purse': league.default_purse,
            'max_squad_size': league.max_squad_size,
            'min_squad_size': league.min_squad_size,
            'bid_increment_tiers': league.bid_increment_tiers_parsed,
            'max_rtm': league.max_rtm,
            'auction_categories': [
                {'id': c.id, 'name': c.name, 'sort_order': c.sort_order}
                for c in league.auction_categories if not c.is_deleted
            ]
        } for league in leagues]


# Singleton instance for use in routes
league_service = LeagueService()
