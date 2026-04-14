#!/usr/bin/env python3
"""
Standalone script to scrape WPL fantasy points and update the database.
Used by GitHub Actions for automated updates.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import League
from app.services.fantasy_service import fantasy_service


def scrape_and_update():
    """Scrape WPL data and update fantasy points in database."""
    app = create_app()

    with app.app_context():
        # Get current league
        league = League.query.filter_by(is_deleted=False).first()
        if not league:
            print("No active league found")
            return False

        print(f"Scraping for league: {league.name}")

        # Use the service function instead of duplicating logic (DRY principle)
        try:
            result = fantasy_service.fetch_match_fantasy_points(league.id)
        except Exception as e:
            print(f"Exception during scraping: {e}")
            return False

        if not result.get('success'):
            print(f"Scraping failed: {result.get('error')}")
            return False

        matches_scraped = result.get('matches_scraped', 0)
        players_updated = result.get('players_updated', 0)
        updated_players = result.get('updated', [])

        print(f"Scraped {matches_scraped} matches")

        # Count new entries
        new_entries_count = sum(p.get('new_matches_added', 0) for p in updated_players)
        players_with_new = [p for p in updated_players if p.get('new_matches_added', 0) > 0]

        for p in players_with_new:
            print(f"  Updated {p['name']}: +{p['new_matches_added']} matches, total={p['total_points']}")

        print(f"\nFantasy Points Summary:")
        print(f"  Players updated: {len(players_with_new)}")
        print(f"  New match entries: {new_entries_count}")

        # Fetch and update awards (uses service to update leader + top-5 leaderboard)
        print("\nFetching awards...")
        try:
            awards_result = fantasy_service.fetch_and_update_awards(league.id)
            if awards_result.get('success'):
                for award_type, info in awards_result.get('results', {}).items():
                    if award_type != 'errors' and info:
                        print(f"  {award_type}: {info.get('player_name', 'N/A')}")
            else:
                for err in awards_result.get('results', {}).get('errors', []):
                    print(f"  Award error: {err}")
        except Exception as e:
            print(f"  Awards fetch failed: {e}")

        return True


if __name__ == '__main__':
    success = scrape_and_update()
    sys.exit(0 if success else 1)
