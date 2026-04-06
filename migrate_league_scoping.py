"""
Migration script: Add league_id to Bid and AuctionState models.

Adds league_id foreign key columns and indexes to support
multi-league concurrent auctions.

Run with:
    python migrate_league_scoping.py

This script is idempotent — safe to run multiple times.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import inspect, text


def column_exists(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(inspector, table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def migrate():
    """Run the migration."""
    app = create_app()

    with app.app_context():
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        print("Starting migration: Add league_id to Bid and AuctionState...")

        with db.engine.connect() as conn:
            # === BID TABLE ===
            if 'bid' in tables:
                if not column_exists(inspector, 'bid', 'league_id'):
                    print("  Adding league_id column to bid table...")

                    # First, determine the default league_id from existing data
                    result = conn.execute(text(
                        "SELECT id FROM league WHERE is_deleted = 0 LIMIT 1"
                    )).fetchone()
                    default_league_id = result[0] if result else 1

                    # Add column with default value
                    conn.execute(text(
                        f"ALTER TABLE bid ADD COLUMN league_id INTEGER NOT NULL DEFAULT {default_league_id}"
                    ))

                    # Backfill: set league_id from the player's league
                    conn.execute(text("""
                        UPDATE bid SET league_id = (
                            SELECT player.league_id FROM player WHERE player.id = bid.player_id
                        ) WHERE EXISTS (
                            SELECT 1 FROM player WHERE player.id = bid.player_id AND player.league_id IS NOT NULL
                        )
                    """))

                    print(f"  Added league_id to bid table (default: {default_league_id})")
                else:
                    print("  bid.league_id already exists, skipping.")

                # Add index on league_id
                if not index_exists(inspector, 'bid', 'ix_bid_league_id'):
                    conn.execute(text(
                        "CREATE INDEX ix_bid_league_id ON bid (league_id)"
                    ))
                    print("  Created index ix_bid_league_id")

                # Add composite index
                if not index_exists(inspector, 'bid', 'idx_bid_league_player'):
                    conn.execute(text(
                        "CREATE INDEX idx_bid_league_player ON bid (league_id, player_id)"
                    ))
                    print("  Created index idx_bid_league_player")

            # === AUCTION_STATE TABLE ===
            if 'auction_state' in tables:
                if not column_exists(inspector, 'auction_state', 'league_id'):
                    print("  Adding league_id column to auction_state table...")

                    result = conn.execute(text(
                        "SELECT id FROM league WHERE is_deleted = 0 LIMIT 1"
                    )).fetchone()
                    default_league_id = result[0] if result else 1

                    conn.execute(text(
                        f"ALTER TABLE auction_state ADD COLUMN league_id INTEGER NOT NULL DEFAULT {default_league_id}"
                    ))

                    # Backfill from current_player_id
                    conn.execute(text("""
                        UPDATE auction_state SET league_id = (
                            SELECT player.league_id FROM player
                            WHERE player.id = auction_state.current_player_id
                        ) WHERE current_player_id IS NOT NULL AND EXISTS (
                            SELECT 1 FROM player
                            WHERE player.id = auction_state.current_player_id
                            AND player.league_id IS NOT NULL
                        )
                    """))

                    # Delete duplicate auction_state rows per league (keep lowest ID)
                    # The new model enforces one auction_state per league
                    conn.execute(text("""
                        DELETE FROM auction_state
                        WHERE id NOT IN (
                            SELECT MIN(id) FROM auction_state GROUP BY league_id
                        )
                    """))

                    print(f"  Added league_id to auction_state table (default: {default_league_id})")
                else:
                    print("  auction_state.league_id already exists, skipping.")

                # Add index
                if not index_exists(inspector, 'auction_state', 'ix_auction_state_league_id'):
                    conn.execute(text(
                        "CREATE INDEX ix_auction_state_league_id ON auction_state (league_id)"
                    ))
                    print("  Created index ix_auction_state_league_id")

            conn.commit()

        print("Migration complete!")


if __name__ == '__main__':
    migrate()
