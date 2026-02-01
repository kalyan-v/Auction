"""
Player service for managing player operations.

Encapsulates all business logic related to:
- Player CRUD operations
- Player release from teams
- Player queries and filtering
- Image management
"""

import os
import random
from typing import List, Optional

import requests
from flask import current_app

from app import db
from app.constants import (
    IMAGE_REQUEST_TIMEOUT,
    MIN_VALID_IMAGE_SIZE,
    WIKI_HEADERS,
    WIKI_REQUEST_TIMEOUT,
    WPL_IMAGE_URL_TEMPLATE,
    WPL_SERIES_ID,
)
from app.db_utils import PlayerLock, get_for_update
from app.logger import get_logger
from app.models import AuctionState, Player, Team
from app.player_data import WPL_PLAYER_IDS
from app.repositories.bid_repository import BidRepository
from app.services.base import BaseService, NotFoundError, ValidationError
from app.utils import create_safe_filename

logger = get_logger(__name__)


class PlayerService(BaseService):
    """Service for player-related operations.

    Handles player CRUD, team release, queries, and image management.
    """

    def __init__(self, bid_repo: Optional[BidRepository] = None):
        """Initialize service with optional repository injection.

        Args:
            bid_repo: BidRepository instance (defaults to new instance).
        """
        self.bid_repo = bid_repo or BidRepository()

    def create_player(
        self,
        name: str,
        league_id: int,
        position: str = '',
        country: str = 'Indian',
        base_price: float = 100000,
        original_team: str = ''
    ) -> dict:
        """Create a new player.

        Args:
            name: Player's name.
            league_id: ID of the league the player belongs to.
            position: Player's position (e.g., 'Batter', 'Bowler').
            country: Player's country ('Indian' or 'Overseas').
            base_price: Starting auction price.
            original_team: Player's previous team.

        Returns:
            Dict with success status and player ID.

        Raises:
            ValidationError: If validation fails.
        """
        if not name or not name.strip():
            raise ValidationError("Player name is required")

        if base_price < 0:
            raise ValidationError("Base price cannot be negative")

        with self.transaction():
            player = Player(
                name=name.strip(),
                position=position,
                country=country,
                base_price=base_price,
                original_team=original_team,
                league_id=league_id
            )
            db.session.add(player)
            self.flush()

            logger.info(f"Created player: {player.name} (ID: {player.id})")

            return {'success': True, 'player_id': player.id}

    def update_player(
        self,
        player_id: int,
        name: Optional[str] = None,
        position: Optional[str] = None,
        country: Optional[str] = None,
        base_price: Optional[float] = None,
        original_team: Optional[str] = None
    ) -> dict:
        """Update an existing player.

        Args:
            player_id: ID of the player to update.
            name: New name (optional).
            position: New position (optional).
            country: New country (optional).
            base_price: New base price (optional).
            original_team: New original team (optional).

        Returns:
            Dict with success status.

        Raises:
            NotFoundError: If player not found.
            ValidationError: If validation fails.
        """
        with self.transaction():
            player = db.session.get(Player, player_id)
            if not player:
                raise NotFoundError("Player not found")

            if name is not None:
                player.name = name
            if position is not None:
                player.position = position
            if country is not None:
                player.country = country
            if original_team is not None:
                player.original_team = original_team
            if base_price is not None:
                if base_price < 0:
                    raise ValidationError("Base price cannot be negative")
                player.base_price = base_price

            logger.info(f"Updated player: {player.name}")

            return {'success': True}

    def delete_player(self, player_id: int) -> dict:
        """Soft-delete a player.

        Args:
            player_id: ID of the player to delete.

        Returns:
            Dict with success status.

        Raises:
            NotFoundError: If player not found.
        """
        with self.transaction():
            player = db.session.get(Player, player_id)
            if not player:
                raise NotFoundError("Player not found")

            # Check if player is in active auction
            auction_state = AuctionState.query.first()
            if auction_state and auction_state.current_player_id == player_id:
                auction_state.current_player_id = None
                auction_state.is_active = False

            player.is_deleted = True

            logger.info(f"Deleted player: {player.name}")

            return {'success': True}

    def release_player(self, player_id: int) -> dict:
        """Release a player from their team back to auction pool.

        Args:
            player_id: ID of the player to release.

        Returns:
            Dict with success status and message.

        Raises:
            NotFoundError: If player not found.
            ValidationError: If player is not sold.
        """
        with PlayerLock():
            with self.transaction():
                player = get_for_update(Player, player_id)

                if not player:
                    raise NotFoundError("Player not found")

                if player.status != 'sold':
                    raise ValidationError("Player is not currently sold to a team")

                player_name = player.name

                # Get team to refund budget
                if player.team_id:
                    team = get_for_update(Team, player.team_id)
                    if team:
                        team.budget += player.current_price

                # Reset player to available status
                player.status = 'available'
                player.team_id = None
                player.current_price = player.base_price

                # Soft delete all bids for this player
                self.bid_repo.soft_delete_for_player(player_id)

                logger.info(f"Released player: {player_name}")

                return {
                    'success': True,
                    'message': f'{player_name} has been released back to auction'
                }

    def get_players(self, league_id: int) -> List[dict]:
        """Get all players for a league.

        Args:
            league_id: ID of the league.

        Returns:
            List of player dictionaries.
        """
        players = Player.query.filter_by(
            league_id=league_id, is_deleted=False
        ).all()

        return [{
            'id': p.id,
            'name': p.name,
            'position': p.position,
            'country': p.country,
            'base_price': p.base_price,
            'original_team': p.original_team,
            'status': p.status
        } for p in players]

    def get_available_players(
        self,
        league_id: int,
        position: Optional[str] = None,
        include_unsold: bool = False
    ) -> List[Player]:
        """Get available players for auction.

        Args:
            league_id: ID of the league.
            position: Filter by position (optional).
            include_unsold: Include unsold players in results.

        Returns:
            List of Player objects.
        """
        if include_unsold:
            query = Player.query.filter(
                Player.league_id == league_id,
                Player.is_deleted.is_(False),
                Player.status.in_(['available', 'unsold'])
            )
        else:
            query = Player.query.filter_by(
                league_id=league_id,
                is_deleted=False,
                status='available'
            )

        if position:
            query = query.filter_by(position=position)

        return query.all()

    def get_random_player(
        self,
        league_id: int,
        position: Optional[str] = None,
        include_unsold: bool = False
    ) -> Optional[Player]:
        """Get a random available player.

        Args:
            league_id: ID of the league.
            position: Filter by position (optional).
            include_unsold: Include unsold players.

        Returns:
            Random Player object or None if none available.
        """
        available = self.get_available_players(league_id, position, include_unsold)
        if not available:
            return None
        return random.choice(available)

    # ==================== IMAGE MANAGEMENT ====================

    def _get_image_path(self) -> str:
        """Get the path to store player images."""
        return os.path.join(current_app.root_path, 'static', 'images', 'players')

    def _validate_image_path(self, filepath: str, image_dir: str) -> bool:
        """Validate that filepath stays within image directory (prevent path traversal)."""
        real_filepath = os.path.realpath(filepath)
        real_image_dir = os.path.realpath(image_dir)
        return real_filepath.startswith(real_image_dir + os.sep)

    def _download_image(
        self,
        image_url: str,
        player_id: int,
        player_name: str,
        extension: str = 'jpg'
    ) -> Optional[str]:
        """Download an image and save it locally.

        Args:
            image_url: URL to download from.
            player_id: Player's ID for filename.
            player_name: Player's name for filename.
            extension: File extension (jpg or png).

        Returns:
            Local path to saved image or None on failure.
        """
        try:
            response = requests.get(
                image_url,
                headers=WIKI_HEADERS,
                timeout=IMAGE_REQUEST_TIMEOUT
            )
            if response.status_code != 200:
                return None

            # Validate content type is an image
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"Invalid content type for {player_name}: {content_type}")
                return None

            # Validate file size (max 5MB)
            max_size = 5 * 1024 * 1024
            if len(response.content) > max_size:
                logger.warning(f"Image too large for {player_name}: {len(response.content)} bytes")
                return None

            # Ensure directory exists
            image_dir = self._get_image_path()
            os.makedirs(image_dir, exist_ok=True)

            # Create safe filename
            safe_name = create_safe_filename(player_name)
            filename = f"{player_id}_{safe_name}.{extension}"
            filepath = os.path.join(image_dir, filename)

            # Security check
            if not self._validate_image_path(filepath, image_dir):
                logger.error(f"Path traversal attempt detected: {filepath}")
                return None

            with open(filepath, 'wb') as f:
                f.write(response.content)

            return f"/static/images/players/{filename}"

        except requests.RequestException as e:
            logger.error(f"Network error downloading image for {player_name}: {e}")
            return None
        except IOError as e:
            logger.error(f"File error saving image for {player_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading image for {player_name}: {e}", exc_info=True)
            return None

    def fetch_player_image(self, player_id: int) -> dict:
        """Search for and download player image.

        Tries WPL official source first, falls back to Wikipedia.

        Args:
            player_id: ID of the player.

        Returns:
            Dict with success status and image URL.

        Raises:
            NotFoundError: If player not found.
        """
        player = db.session.get(Player, player_id)
        if not player:
            raise NotFoundError("Player not found")

        local_path = self._search_and_download_image(player.id, player.name)

        if local_path:
            with self.transaction():
                player.image_url = local_path

            return {
                'success': True,
                'image_url': local_path,
                'message': f'Image downloaded for {player.name}'
            }

        raise ValidationError(f'No image found for {player.name}. Try setting manually.')

    def _search_and_download_image(
        self,
        player_id: int,
        player_name: str
    ) -> Optional[str]:
        """Search for player image from multiple sources.

        Args:
            player_id: Player's ID.
            player_name: Player's name.

        Returns:
            Local path to image or None.
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # Try WPL first
        wpl_player_id = WPL_PLAYER_IDS.get(player_name.strip())
        if wpl_player_id:
            try:
                image_url = WPL_IMAGE_URL_TEMPLATE.format(
                    series_id=WPL_SERIES_ID,
                    player_id=wpl_player_id
                )
                response = requests.get(
                    image_url,
                    headers=headers,
                    timeout=IMAGE_REQUEST_TIMEOUT
                )
                if (response.status_code == 200 and
                        len(response.content) > MIN_VALID_IMAGE_SIZE):
                    max_size = 5 * 1024 * 1024
                    if len(response.content) <= max_size:
                        image_dir = self._get_image_path()
                        os.makedirs(image_dir, exist_ok=True)

                        safe_name = create_safe_filename(player_name)
                        filename = f"{player_id}_{safe_name}.png"
                        filepath = os.path.join(image_dir, filename)

                        if self._validate_image_path(filepath, image_dir):
                            with open(filepath, 'wb') as f:
                                f.write(response.content)
                            return f"/static/images/players/{filename}"

            except requests.RequestException as e:
                logger.error(f"WPL network error for {player_name}: {e}")
            except IOError as e:
                logger.error(f"WPL file error for {player_name}: {e}")
            except Exception as e:
                logger.error(f"WPL unexpected error for {player_name}: {e}", exc_info=True)

        # Fallback to Wikipedia
        try:
            wiki_url = 'https://en.wikipedia.org/w/api.php'
            params = {
                'action': 'query',
                'titles': player_name,
                'prop': 'pageimages',
                'format': 'json',
                'pithumbsize': 200
            }
            response = requests.get(
                wiki_url,
                params=params,
                headers=WIKI_HEADERS,
                timeout=WIKI_REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                pages = data.get('query', {}).get('pages', {})
                for page_id, page_data in pages.items():
                    if page_id != '-1':
                        thumbnail = page_data.get('thumbnail', {})
                        if thumbnail.get('source'):
                            return self._download_image(
                                thumbnail['source'], player_id, player_name
                            )

        except requests.RequestException as e:
            logger.error(f"Wikipedia network error for {player_name}: {e}")
        except Exception as e:
            logger.error(f"Wikipedia unexpected error for {player_name}: {e}", exc_info=True)

        return None

    def update_player_image(self, player_id: int, image_url: str) -> dict:
        """Manually update player image URL.

        Args:
            player_id: ID of the player.
            image_url: New image URL or local path.

        Returns:
            Dict with success status.

        Raises:
            NotFoundError: If player not found.
        """
        with self.transaction():
            player = db.session.get(Player, player_id)
            if not player:
                raise NotFoundError("Player not found")

            player.image_url = image_url if image_url else None

            return {
                'success': True,
                'image_url': player.image_url,
                'message': 'Image URL updated'
            }

    def fetch_all_images(self, league_id: int) -> dict:
        """Fetch images for all players without images.

        Args:
            league_id: ID of the league.

        Returns:
            Dict with results summary.
        """
        players = Player.query.filter(
            Player.league_id == league_id,
            Player.is_deleted.is_(False),
            Player.image_url.is_(None) | (Player.image_url == '')
        ).all()

        results = {'found': 0, 'not_found': 0, 'players': []}

        for player in players:
            local_path = self._search_and_download_image(player.id, player.name)

            if local_path:
                player.image_url = local_path
                results['found'] += 1
                results['players'].append({
                    'name': player.name,
                    'status': 'found',
                    'image_url': local_path
                })
            else:
                results['not_found'] += 1
                results['players'].append({
                    'name': player.name,
                    'status': 'not_found'
                })

        db.session.commit()

        return {
            'success': True,
            'message': (
                f"Downloaded images for {results['found']} players, "
                f"{results['not_found']} not found"
            ),
            'results': results
        }


# Singleton instance for use in routes
player_service = PlayerService()
