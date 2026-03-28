#!/usr/bin/env python3
"""
Standalone script to scrape IPL fantasy points and update the database.
Used by GitHub Actions for automated daily updates.

Usage:
    python scripts/scrape_ipl_fantasy.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.enums import AwardType
from app.models import FantasyAward, Player, League
from app.scrapers import get_scraper, ScraperType
from app.services.fantasy_service import fantasy_service


def scrape_and_update():
    """Scrape IPL data and update fantasy points in database."""
    app = create_app()

    with app.app_context():
        league = League.query.filter_by(
            league_type='ipl', is_deleted=False
        ).first()
        if not league:
            print("No IPL league found")
            return False

        print(f"Scraping for league: {league.name} (type={league.league_type})")

        # Resolve scraper from league type
        try:
            scraper_type = ScraperType(league.league_type)
            scraper = get_scraper(scraper_type)
        except Exception as e:
            print(f"Failed to initialize scraper: {e}")
            return False

        # Fetch match fantasy points via service (handles scoring + DB updates)
        try:
            result = fantasy_service.fetch_match_fantasy_points(league.id)
        except Exception as e:
            print(f"Exception during scraping: {e}")
            return False

        if not result.get('success'):
            print(f"Scraping failed: {result.get('error')}")
            return False

        matches_scraped = result.get('matches_scraped', 0)
        updated_players = result.get('updated', [])

        print(f"Scraped {matches_scraped} matches")

        new_entries_count = sum(p.get('new_matches_added', 0) for p in updated_players)
        players_with_new = [p for p in updated_players if p.get('new_matches_added', 0) > 0]

        for p in players_with_new:
            print(f"  Updated {p['name']}: +{p['new_matches_added']} matches, total={p['total_points']}")

        print(f"\nFantasy Points Summary:")
        print(f"  Players updated: {len(players_with_new)}")
        print(f"  New match entries: {new_entries_count}")

        # Fetch and update awards
        print("\nFetching awards...")
        with scraper:
            update_awards(scraper, league.id)

        return True


def update_awards(scraper, league_id):
    """Fetch and update Orange Cap, Purple Cap, and MVP awards."""
    awards_updated = []

    award_configs = [
        (AwardType.ORANGE_CAP, 'get_orange_cap', 'Orange Cap', 'runs'),
        (AwardType.PURPLE_CAP, 'get_purple_cap', 'Purple Cap', 'wickets'),
        (AwardType.MVP, 'get_mvp', 'MVP', 'points'),
    ]

    for award_type, method_name, label, stat_key in award_configs:
        result = getattr(scraper, method_name)()
        if result.success and result.leader:
            player_name = result.leader.player_name
            player = fantasy_service.find_player_by_name(player_name, league_id)
            if player:
                award = FantasyAward.query.filter_by(
                    award_type=award_type.value,
                    league_id=league_id
                ).first()
                if not award:
                    award = FantasyAward(
                        award_type=award_type.value,
                        league_id=league_id
                    )
                    db.session.add(award)
                award.player_id = player.id
                stat_val = result.leader.stats.get(stat_key, 0)
                awards_updated.append(f"{label}: {player.name}")
                print(f"  {label}: {player.name} ({stat_val} {stat_key})")
            else:
                print(f"  {label}: Player '{player_name}' not found in league")
        else:
            print(f"  {label} fetch failed: {result.error}")

    db.session.commit()
    return awards_updated


if __name__ == '__main__':
    success = scrape_and_update()
    sys.exit(0 if success else 1)
