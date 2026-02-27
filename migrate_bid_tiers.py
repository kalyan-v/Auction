"""Migration: Replace bid_increment (int) with bid_increment_tiers (JSON text) on league table."""
import json
from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # 1. Add bid_increment_tiers column
    try:
        db.session.execute(text(
            "ALTER TABLE league ADD COLUMN bid_increment_tiers TEXT DEFAULT '[{\"threshold\": 0, \"increment\": 2500000}]'"
        ))
        db.session.commit()
        print('Added bid_increment_tiers column')
    except Exception as e:
        db.session.rollback()
        print(f'bid_increment_tiers column: {e}')

    # 2. Migrate existing bid_increment values into tiers JSON
    try:
        rows = db.session.execute(text('SELECT id, bid_increment FROM league')).fetchall()
        for row in rows:
            league_id, old_increment = row
            if old_increment and old_increment > 0:
                tiers = json.dumps([{'threshold': 0, 'increment': old_increment}])
                db.session.execute(
                    text('UPDATE league SET bid_increment_tiers = :tiers WHERE id = :lid'),
                    {'tiers': tiers, 'lid': league_id}
                )
        db.session.commit()
        print(f'Migrated {len(rows)} league(s) bid_increment -> bid_increment_tiers')
    except Exception as e:
        db.session.rollback()
        print(f'Migration error: {e}')

    print('Done!')
