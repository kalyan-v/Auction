"""
Migration script: Add leaderboard_json to FantasyAward model.

Stores the top-5 leaderboard from the scraper API as JSON on each award.

Run with:
    python migrate_award_leaderboard.py

This script is idempotent — safe to run multiple times.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import inspect, text


def column_exists(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate():
    """Add leaderboard_json column to fantasy_award table."""
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        if column_exists(inspector, 'fantasy_award', 'leaderboard_json'):
            print("Column 'leaderboard_json' already exists. Nothing to do.")
            return

        print("Adding 'leaderboard_json' column to fantasy_award...")
        with db.engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE fantasy_award ADD COLUMN leaderboard_json TEXT"
            ))
        print("Migration complete.")


if __name__ == '__main__':
    migrate()
