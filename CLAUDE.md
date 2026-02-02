# WPL Auction Project - Claude Guidelines

## Project Overview
Fantasy cricket auction system for the Women's Premier League (WPL) with live bidding and automated fantasy point tracking.

**Tech Stack:** Python 3.11, Flask 3.0, SQLAlchemy, SQLite, Vanilla JS

---

## Architecture (Strict Layering)

```
Routes → Services → Repositories → Models
```

### Rules
- **Routes**: Only handle request/response; delegate all logic to services
- **Services**: Business logic + transactions; raise custom exceptions
- **Repositories**: Data access only; no business logic
- **Models**: SQLAlchemy definitions only; no methods with logic

### Transaction Pattern
```python
# Always use context manager in services
with self.transaction():
    # your code here
# Never call db.session.commit() directly
```

---

## Code Style

### Type Hints & Docstrings
- Type hints on ALL function args and returns
- Full docstrings with description, Args, Returns, Example

### Constants & Enums
- Magic numbers → `app/constants.py` as `Final` variables
- Repeated strings → `app/enums.py` as Enums

### Database Access
- Always use repositories, never direct `db.session.query()`
- Use `soft_delete()` for deletions (never hard delete)
- Use `get_for_update()` for concurrent auction operations
- Always filter by `is_deleted=False` in queries

---

## Error Handling

### Exception Types
| Exception | Use For | HTTP Status |
|-----------|---------|-------------|
| `ValidationError` | Input validation failures | 400 |
| `NotFoundError` | Missing resources | 404 |
| `AuthorizationError` | Permission denied | 403 |
| `ServiceError` | Domain logic failures | varies |

### API Responses
```python
# Success
return success_response(data, message="Created", status_code=201)

# Error
return error_response("Invalid input", status_code=400)
```

---

## Frontend (JavaScript)

### Security
- `secureFetch()` - Use for ALL API calls (auto-includes CSRF token)
- `escapeHtml()` - Use for ANY user-controlled content
- Never use `innerHTML` with untrusted data

### Formatting
- `formatCurrency(amount)` - Always use for money (displays in Lakhs/Crores)

---

## Testing

### Fixtures (from `tests/conftest.py`)
- `app` - Flask application
- `client` - Test client
- `auth_client` - Authenticated test client
- `sample_league`, `sample_teams` - Test data

### Rules
- Mock external calls (WPL scraper) to avoid network dependency
- Test database: in-memory SQLite (auto-cleaned per test)

---

## Security

### Authentication
- Use `is_admin()` utility to check auth
- Return 403 if not admin (don't leak info)

### Logging
- Never log passwords, tokens, or PII
- Use `log_audit()` for sensitive operations
- Use `get_logger(__name__)` not `print()`

---

## Common Patterns

### Adding a New API Endpoint
1. Create route in `app/routes/api/`
2. Create/update service in `app/services/`
3. Create/update repository if new data access needed
4. Add tests in `tests/`

### Adding a New Model Field
1. Add field to model in `app/models/`
2. Create migration: `flask db migrate -m "description"`
3. Update repository queries if needed
4. Update service logic
5. Update API responses

---

## Anti-Patterns (Don't Do This)

- ❌ Direct SQL queries (use repositories)
- ❌ Hard deletes (use soft delete)
- ❌ Business logic in routes or models
- ❌ `db.session.commit()` outside transaction context
- ❌ Missing type hints or docstrings
- ❌ `print()` for logging
- ❌ Unhandled exceptions (wrap in custom exceptions)

---

## Self-Improvement & Documentation Rule

**Automatically update documentation when:**

1. **Mistakes/Corrections** - Add a rule to prevent the mistake in the future
2. **New files added** - Update relevant docs (architecture.md, api-patterns.md)
3. **Files modified** - Update any docs that reference the changed behavior
4. **Structure changes** - Update architecture.md and this CLAUDE.md
5. **New patterns discovered** - Document in the relevant section

**Don't wait to be asked** - proactively keep docs in sync with the codebase.

**Which doc to update:**
| Change Type | Update |
|-------------|--------|
| New API endpoint | `.claude/notes/api-patterns.md` |
| New model/service | `.claude/notes/architecture.md` |
| Bug fix / gotcha | `.claude/notes/gotchas.md` |
| New convention | This `CLAUDE.md` |
| Anti-pattern learned | Anti-Patterns section above |

---

## Project Notes
See `.claude/notes/` for detailed context on architecture decisions and gotchas.
