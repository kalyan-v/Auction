"""Migration script to add auction_category, bid_increment, and league_type columns."""

from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # Add bid_increment to league (already done in previous run, handle gracefully)
    try:
        db.session.execute(text('ALTER TABLE league ADD COLUMN bid_increment INTEGER DEFAULT 2500000'))
        print('Added bid_increment to league')
    except Exception as e:
        print(f'bid_increment: {e}')

    # Add league_type to league
    try:
        db.session.execute(text("ALTER TABLE league ADD COLUMN league_type VARCHAR(20) DEFAULT 'wpl'"))
        print('Added league_type to league')
    except Exception as e:
        print(f'league_type: {e}')

    # Add auction_category to player
    try:
        db.session.execute(text('ALTER TABLE player ADD COLUMN auction_category VARCHAR(50)'))
        print('Added auction_category to player')
    except Exception as e:
        print(f'auction_category: {e}')

    db.session.commit()
    
    # Verify columns
    result = db.session.execute(text('PRAGMA table_info(league)'))
    cols = [row[1] for row in result]
    print(f'\nLeague columns: {cols}')

    result = db.session.execute(text('PRAGMA table_info(player)'))
    cols = [row[1] for row in result]
    print(f'Player columns: {cols}')

    result = db.session.execute(text('PRAGMA table_info(auction_category)'))
    cols = [row[1] for row in result]
    print(f'AuctionCategory columns: {cols}')
    
    print('\nMigration complete!')
