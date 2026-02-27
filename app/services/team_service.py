"""
Team service for managing team operations.

Encapsulates all business logic related to:
- Team CRUD operations
- Budget management
- Squad management
"""

from typing import List, Optional

from app import db
from app.logger import get_logger
from app.models import Team
from app.services.base import BaseService, ValidationError

logger = get_logger(__name__)


class TeamService(BaseService):
    """Service for team-related operations.

    Handles team CRUD, budget tracking, and squad management.
    """

    def create_team(
        self,
        name: str,
        league_id: int,
        budget: Optional[float] = None,
        default_purse: float = 500000000
    ) -> dict:
        """Create a new team.

        Args:
            name: Team name.
            league_id: ID of the league.
            budget: Team budget (defaults to league default purse).
            default_purse: Default budget if none specified.

        Returns:
            Dict with success status and team ID.

        Raises:
            ValidationError: If validation fails.
        """
        if not name or not name.strip():
            raise ValidationError("Team name is required")

        team_budget = budget if budget is not None else default_purse

        with self.transaction():
            team = Team(
                name=name.strip(),
                budget=team_budget,
                initial_budget=team_budget,
                league_id=league_id
            )
            db.session.add(team)
            self.flush()

            logger.info(f"Created team: {team.name} (ID: {team.id})")

            return {'success': True, 'team_id': team.id}

    def get_teams(self, league_id: int) -> List[dict]:
        """Get all teams for a league.

        Args:
            league_id: ID of the league.

        Returns:
            List of team dictionaries.
        """
        teams = Team.query.filter_by(
            league_id=league_id, is_deleted=False
        ).all()

        return [{
            'id': t.id,
            'name': t.name,
            'budget': t.budget,
            'initial_budget': t.initial_budget,
            'spent': t.initial_budget - t.budget
        } for t in teams]


# Singleton instance for use in routes
team_service = TeamService()
