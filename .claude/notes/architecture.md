# Architecture Decisions

## Layered Architecture
The project uses a strict 4-layer architecture:
1. **Routes** - HTTP handling only
2. **Services** - Business logic with transaction management
3. **Repositories** - Data access with soft delete support
4. **Models** - SQLAlchemy ORM definitions

## Why This Pattern?
- Clear separation of concerns
- Easy to test (mock repositories in service tests)
- Transaction boundaries are explicit
- Business logic is reusable across different entry points

## Database Choice: SQLite
- Simple deployment (single file)
- Good enough for expected load
- Application-level locking handles concurrency
- Easy backups (just copy the file)

## Multi-League Support
- All major models have `league_id` foreign key
- Unique constraints are per-league (same team name OK in different leagues)
- Session tracks `current_league_id` for UI context
