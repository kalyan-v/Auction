"""Inspect the current state of auction.db."""
from app import create_app, db
from app.models import League, Team, Player, FantasyAward, FantasyPointEntry
from sqlalchemy import text

app = create_app()
with app.app_context():
    # Tables
    result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
    print("=== Tables ===")
    for row in result:
        print(f"  {row[0]}")

    # Leagues
    print("\n=== Leagues ===")
    for l in League.query.all():
        print(f"  id={l.id} name={l.name} type={l.league_type} active={l.is_active} deleted={l.is_deleted}")

    # Teams
    print("\n=== Teams ===")
    for t in Team.query.filter_by(is_deleted=False).all():
        player_count = Player.query.filter_by(team_id=t.id, is_deleted=False).count()
        print(f"  id={t.id} name={t.name} league={t.league_id} players={player_count}")

    # Player summary per league
    print("\n=== Players per League ===")
    for l in League.query.filter_by(is_deleted=False).all():
        total = Player.query.filter_by(league_id=l.id, is_deleted=False).count()
        sold = Player.query.filter_by(league_id=l.id, is_deleted=False).filter(Player.team_id.isnot(None)).count()
        with_pts = Player.query.filter_by(league_id=l.id, is_deleted=False).filter(Player.fantasy_points > 0).count()
        print(f"  {l.name}: total={total} sold={sold} with_fantasy_pts={with_pts}")

    # Fantasy Awards
    print("\n=== Fantasy Awards ===")
    awards = FantasyAward.query.all()
    if awards:
        for a in awards:
            player = db.session.get(Player, a.player_id)
            pname = player.name if player else "?"
            print(f"  {a.award_type} -> {pname} (league_id={a.league_id})")
    else:
        print("  None")

    # Fantasy Point Entries
    print("\n=== Fantasy Point Entries ===")
    for l in League.query.filter_by(is_deleted=False).all():
        count = FantasyPointEntry.query.filter_by(league_id=l.id).count()
        print(f"  {l.name}: {count} entries")

    # Migration version
    try:
        result = db.session.execute(text("SELECT version_num FROM alembic_version"))
        for row in result:
            print(f"\n=== Migration version: {row[0]} ===")
    except Exception:
        print("\n=== No alembic_version table ===")
