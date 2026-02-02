# Gotchas & Non-Obvious Behaviors

## Database

### Soft Deletes
- All queries must include `is_deleted=False` filter
- The repository base class does this automatically
- Direct queries will return deleted records!

### SQLite Locking
- SQLite doesn't support `SELECT FOR UPDATE`
- We use application-level locking in `db_utils.py`
- Always use `get_for_update()` for auction operations

### Fantasy Points Deduplication
- `game_id` tracks which matches have been scored
- Re-running the scraper won't double-count points
- Check `game_id` before inserting new FantasyPointEntry

## Frontend

### CSRF Token
- All POST/PUT/DELETE requests need CSRF token
- `secureFetch()` handles this automatically
- Manual fetch calls will fail with 400

### Currency Display
- All amounts are in Indian Rupees
- Use `formatCurrency()` for proper Lakhs/Crores formatting
- Raw numbers will confuse users

## Deployment

### GitHub Actions Timing
- Scraper runs every 15 minutes
- PythonAnywhere sync at 6:45 PM UTC
- There's a ~15 min delay between scrape and deploy

### Database Commits
- GitHub Actions auto-commits database changes
- Don't be surprised by automated commits in git history
