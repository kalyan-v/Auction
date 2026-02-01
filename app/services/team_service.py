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
from app.models import Player, Team
from app.services.base import BaseService, NotFoundError, ValidationError

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

    def update_team(
        self,
        team_id: int,
        name: Optional[str] = None,
        budget: Optional[float] = None
    ) -> dict:
        """Update an existing team.

        Args:
            team_id: ID of the team to update.
            name: New name (optional).
            budget: New budget (optional).

        Returns:
            Dict with success status.

        Raises:
            NotFoundError: If team not found.
            ValidationError: If validation fails.
        """
        with self.transaction():
            team = db.session.get(Team, team_id)
            if not team:
                raise NotFoundError("Team not found")

            if name is not None:
                team.name = name.strip()
            if budget is not None:
                if budget < 0:
                    raise ValidationError("Budget cannot be negative")
                team.budget = budget

            logger.info(f"Updated team: {team.name}")

            return {'success': True}

    def delete_team(self, team_id: int) -> dict:
        """Soft-delete a team.

        Args:
            team_id: ID of the team to delete.

        Returns:
            Dict with success status.

        Raises:
            NotFoundError: If team not found.
        """
        with self.transaction():
            team = db.session.get(Team, team_id)
            if not team:
                raise NotFoundError("Team not found")

            team.is_deleted = True

            logger.info(f"Deleted team: {team.name}")

            return {'success': True}

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

    def get_team(self, team_id: int) -> dict:
        """Get a specific team by ID.

        Args:
            team_id: ID of the team.

        Returns:
            Team dictionary.

        Raises:
            NotFoundError: If team not found.
        """
        team = db.session.get(Team, team_id)
        if not team:
            raise NotFoundError("Team not found")

        return {
            'id': team.id,
            'name': team.name,
            'budget': team.budget,
            'initial_budget': team.initial_budget,
            'spent': team.initial_budget - team.budget
        }

    def get_team_squad(self, team_id: int) -> dict:
        """Get team with its players.

        Args:
            team_id: ID of the team.

        Returns:
            Team dictionary with players list.

        Raises:
            NotFoundError: If team not found.
        """
        team = db.session.get(Team, team_id)
        if not team:
            raise NotFoundError("Team not found")

        players = Player.query.filter_by(
            team_id=team_id, is_deleted=False
        ).all()

        return {
            'id': team.id,
            'name': team.name,
            'budget': team.budget,
            'initial_budget': team.initial_budget,
            'spent': team.initial_budget - team.budget,
            'players': [{
                'id': p.id,
                'name': p.name,
                'position': p.position,
                'country': p.country,
                'current_price': p.current_price,
                'fantasy_points': p.fantasy_points
            } for p in players]
        }

    def reset_budget(self, team_id: int) -> dict:
        """Reset team budget to initial value.

        Args:
            team_id: ID of the team.

        Returns:
            Dict with success status.

        Raises:
            NotFoundError: If team not found.
        """
        with self.transaction():
            team = db.session.get(Team, team_id)
            if not team:
                raise NotFoundError("Team not found")

            team.budget = team.initial_budget

            logger.info(f"Reset budget for team: {team.name}")

            return {'success': True, 'budget': team.budget}


# Singleton instance for use in routes
team_service = TeamService()
