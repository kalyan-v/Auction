"""
Database Migration Script: Add Multi-League Support

This script migrates the existing database to support multiple leagues.
It adds the necessary columns and creates a default league for existing data.

Run this script ONCE after updating the models.py file.
"""

import os
import sys
import sqlite3

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import League, Team, Player, FantasyAward, FantasyPointEntry

def add_column_if_not_exists(cursor, table_name, column_name, column_type):
    """Add a column to a table if it doesn't already exist"""
    # First check if the table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        print(f"  Table '{table_name}' does not exist, skipping...")
        return False
    
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    
    if column_name not in columns:
        print(f"  Adding column '{column_name}' to '{table_name}'...")
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        return True
    else:
        print(f"  Column '{column_name}' already exists in '{table_name}'")
        return False

def migrate():
    app = create_app()
    
    with app.app_context():
        print("Starting migration to multi-league support...")
        
        # Get the database path - handle the instance folder
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        if db_uri.startswith('sqlite:///'):
            db_relative_path = db_uri.replace('sqlite:///', '')
            # The database is in the instance folder
            db_path = os.path.join(app.instance_path, db_relative_path)
        else:
            db_path = db_uri.replace('sqlite:///', '')
        
        print(f"Database: {db_path}")
        
        if not os.path.exists(db_path):
            print(f"Database file not found at {db_path}")
            print("Creating new database with all tables...")
            db.create_all()
            print("Database created. Now setting up default league...")
            # After creating all tables, we can use SQLAlchemy directly
            default_league = League(
                name='wpl2026',
                display_name='WPL 2026',
                default_purse=500000000,
                max_squad_size=20,
                min_squad_size=16
            )
            db.session.add(default_league)
            db.session.commit()
            print(f"\n✅ New database created with WPL 2026 league!")
            return
        
        # Connect directly to SQLite to add columns
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Step 1: Create the league table if it doesn't exist
        print("\n1. Creating league table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS league (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL UNIQUE,
                display_name VARCHAR(200) NOT NULL,
                default_purse INTEGER DEFAULT 500000000,
                max_squad_size INTEGER DEFAULT 20,
                min_squad_size INTEGER DEFAULT 16,
                is_deleted BOOLEAN DEFAULT 0
            )
        ''')
        conn.commit()
        print("  League table ready.")
        
        # Step 2: Add new columns to existing tables
        print("\n2. Adding new columns to existing tables...")
        
        # Team table
        add_column_if_not_exists(cursor, 'team', 'league_id', 'INTEGER')
        add_column_if_not_exists(cursor, 'team', 'is_deleted', 'BOOLEAN DEFAULT 0')
        
        # Player table
        add_column_if_not_exists(cursor, 'player', 'league_id', 'INTEGER')
        add_column_if_not_exists(cursor, 'player', 'original_team', 'VARCHAR(100)')
        add_column_if_not_exists(cursor, 'player', 'is_deleted', 'BOOLEAN DEFAULT 0')
        
        # Fantasy award table - check if it exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fantasy_award'")
        if cursor.fetchone():
            add_column_if_not_exists(cursor, 'fantasy_award', 'league_id', 'INTEGER')
        
        # Fantasy point entry table - check if it exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fantasy_point_entry'")
        if cursor.fetchone():
            add_column_if_not_exists(cursor, 'fantasy_point_entry', 'league_id', 'INTEGER')
        
        conn.commit()
        
        # Step 3: Create default league
        print("\n3. Creating default WPL 2026 league...")
        cursor.execute("SELECT id FROM league WHERE name = 'wpl2026'")
        existing = cursor.fetchone()
        
        if existing:
            default_league_id = existing[0]
            print(f"  Default league already exists (ID: {default_league_id})")
        else:
            cursor.execute('''
                INSERT INTO league (name, display_name, default_purse, max_squad_size, min_squad_size, is_deleted)
                VALUES ('wpl2026', 'WPL 2026', 500000000, 20, 16, 0)
            ''')
            default_league_id = cursor.lastrowid
            print(f"  Created league: WPL 2026 (ID: {default_league_id})")
        
        conn.commit()
        
        # Step 4: Update existing data to belong to default league
        print("\n4. Updating existing data to belong to WPL 2026...")
        
        # Update teams
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='team'")
        teams_updated = 0
        if cursor.fetchone():
            cursor.execute("UPDATE team SET league_id = ? WHERE league_id IS NULL", (default_league_id,))
            teams_updated = cursor.rowcount
        print(f"  Teams updated: {teams_updated}")
        
        # Update players
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player'")
        players_updated = 0
        if cursor.fetchone():
            cursor.execute("UPDATE player SET league_id = ? WHERE league_id IS NULL", (default_league_id,))
            players_updated = cursor.rowcount
        print(f"  Players updated: {players_updated}")
        
        # Update fantasy awards
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fantasy_award'")
        awards_updated = 0
        if cursor.fetchone():
            cursor.execute("UPDATE fantasy_award SET league_id = ? WHERE league_id IS NULL", (default_league_id,))
            awards_updated = cursor.rowcount
        print(f"  Fantasy Awards updated: {awards_updated}")
        
        # Update fantasy point entries
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fantasy_point_entry'")
        entries_updated = 0
        if cursor.fetchone():
            cursor.execute("UPDATE fantasy_point_entry SET league_id = ? WHERE league_id IS NULL", (default_league_id,))
            entries_updated = cursor.rowcount
        print(f"  Fantasy Point Entries updated: {entries_updated}")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Migration completed successfully!")
        print(f"\nSummary:")
        print(f"  - Default League: WPL 2026 (ID: {default_league_id})")
        print(f"  - Teams updated: {teams_updated}")
        print(f"  - Players updated: {players_updated}")
        print(f"  - Fantasy Awards updated: {awards_updated}")
        print(f"  - Fantasy Point Entries updated: {entries_updated}")
        print("\nYou can now start the application and switch between leagues using the dropdown in the navbar.")

if __name__ == '__main__':
    migrate()
