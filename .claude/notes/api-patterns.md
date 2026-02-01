# API Patterns

## Response Format

All API endpoints return JSON with this envelope:

```json
{
  "success": true,
  "data": { ... },
  "message": "Optional message"
}
```

Or for errors:
```json
{
  "success": false,
  "error": "Error message"
}
```

## Authentication

- Session-based (cookie)
- Admin login at `/login`
- Check with `is_admin()` utility
- No JWT or API keys

## Common Endpoints

### Auction
- `GET /api/auction/state` - Current auction state
- `POST /api/auction/bid` - Place a bid
- `POST /api/auction/sell` - Sell player to highest bidder
- `POST /api/auction/skip` - Skip current player

### Players
- `GET /api/players` - List all players
- `GET /api/players/<id>` - Get player details
- `POST /api/players` - Create player (admin)

### Fantasy
- `GET /api/fantasy/standings` - League standings
- `POST /api/fantasy/scrape` - Trigger fantasy points update

## Rate Limiting

- Default: 200 requests/minute per IP
- Override with `@limiter.limit()` decorator if needed
