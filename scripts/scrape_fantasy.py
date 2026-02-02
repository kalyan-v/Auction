#!/usr/bin/env python3
"""
Standalone script to scrape WPL fantasy points and update the database.
Used by GitHub Actions for automated updates.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.enums import AwardType
from app.models import FantasyAward, FantasyPointEntry, Player, League
from app.scrapers import get_scraper, ScraperType
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

        # Scrape all matches and awards
        try:
            scraper = get_scraper(ScraperType.WPL)
        except Exception as e:
            print(f"Failed to initialize scraper: {e}")
            return False

        with scraper:
            try:
                result = scraper.scrape_all_matches()
            except Exception as e:
                print(f"Exception during scraping: {e}")
                return False

            if not result.get('success'):
                print(f"Scraping failed: {result.get('error')}")
                return False

            all_player_stats = result.get('player_stats', {})
            matches_processed = result.get('matches_processed', [])

            print(f"Scraped {len(matches_processed)} matches")

            updated_count = 0
            new_entries_count = 0

            for wpl_name, data in all_player_stats.items():
                player = fantasy_service.find_player_by_name(wpl_name, league.id)

                if not player:
                    continue

                # Get existing game_ids
                existing_entries = FantasyPointEntry.query.filter_by(
                    player_id=player.id,
                    league_id=league.id
                ).all()
                existing_game_ids = {e.game_id for e in existing_entries if e.game_id}

                player_new_entries = 0
                for match in data.get('matches', []):
                    game_id = match.get('game_id', '')

                    if game_id and game_id in existing_game_ids:
                        continue

                    match_num_str = match.get('match', '')
                    if isinstance(match_num_str, str):
                        match_num_str = match_num_str.replace('Match ', '').strip()
                    try:
                        match_number = int(match_num_str)
                    except (ValueError, TypeError):
                        continue

                    points = match.get('fantasy_points', 0)

                    entry = FantasyPointEntry(
                        player_id=player.id,
                        match_number=match_number,
                        game_id=game_id,
                        points=points,
                        league_id=league.id
                    )
                    db.session.add(entry)
                    existing_game_ids.add(game_id)
                    player_new_entries += 1

                if player_new_entries > 0:
                    # Recalculate total
                    db.session.flush()
                    total_from_entries = db.session.query(
                        db.func.sum(FantasyPointEntry.points)
                    ).filter_by(
                        player_id=player.id,
                        league_id=league.id
                    ).scalar() or 0
                    player.fantasy_points = total_from_entries
                    updated_count += 1
                    new_entries_count += player_new_entries
                    print(f"  Updated {player.name}: +{player_new_entries} matches, total={total_from_entries}")

            db.session.commit()

            print(f"\nFantasy Points Summary:")
            print(f"  Players updated: {updated_count}")
            print(f"  New match entries: {new_entries_count}")

            # Fetch and update awards (inside scraper context)
            print("\nFetching awards...")
            update_awards(scraper, league.id)

        return True


def update_awards(scraper, league_id):
    """Fetch and update Orange Cap, Purple Cap, and MVP awards."""
    awards_updated = []

    # Orange Cap
    orange_result = scraper.get_orange_cap()
    if orange_result.success and orange_result.leader:
        player_name = orange_result.leader.player_name
        player = fantasy_service.find_player_by_name(player_name, league_id)
        if player:
            award = FantasyAward.query.filter_by(
                award_type=AwardType.ORANGE_CAP.value,
                league_id=league_id
            ).first()
            if not award:
                award = FantasyAward(
                    award_type=AwardType.ORANGE_CAP.value,
                    league_id=league_id
                )
                db.session.add(award)
            award.player_id = player.id
            awards_updated.append(f"Orange Cap: {player.name}")
            print(f"  Orange Cap: {player.name} ({orange_result.leader.stats.get('runs', 0)} runs)")
        else:
            print(f"  Orange Cap: Player '{player_name}' not found in league")
    else:
        print(f"  Orange Cap fetch failed: {orange_result.error}")

    # Purple Cap
    purple_result = scraper.get_purple_cap()
    if purple_result.success and purple_result.leader:
        player_name = purple_result.leader.player_name
        player = fantasy_service.find_player_by_name(player_name, league_id)
        if player:
            award = FantasyAward.query.filter_by(
                award_type=AwardType.PURPLE_CAP.value,
                league_id=league_id
            ).first()
            if not award:
                award = FantasyAward(
                    award_type=AwardType.PURPLE_CAP.value,
                    league_id=league_id
                )
                db.session.add(award)
            award.player_id = player.id
            awards_updated.append(f"Purple Cap: {player.name}")
            print(f"  Purple Cap: {player.name} ({purple_result.leader.stats.get('wickets', 0)} wickets)")
        else:
            print(f"  Purple Cap: Player '{player_name}' not found in league")
    else:
        print(f"  Purple Cap fetch failed: {purple_result.error}")

    # MVP
    mvp_result = scraper.get_mvp()
    if mvp_result.success and mvp_result.leader:
        player_name = mvp_result.leader.player_name
        player = fantasy_service.find_player_by_name(player_name, league_id)
        if player:
            award = FantasyAward.query.filter_by(
                award_type=AwardType.MVP.value,
                league_id=league_id
            ).first()
            if not award:
                award = FantasyAward(
                    award_type=AwardType.MVP.value,
                    league_id=league_id
                )
                db.session.add(award)
            award.player_id = player.id
            awards_updated.append(f"MVP: {player.name}")
            print(f"  MVP: {player.name} ({mvp_result.leader.stats.get('points', 0)} points)")
        else:
            print(f"  MVP: Player '{player_name}' not found in league")
    else:
        print(f"  MVP fetch failed: {mvp_result.error}")

    db.session.commit()
    return awards_updated


if __name__ == '__main__':
    success = scrape_and_update()
    sys.exit(0 if success else 1)
