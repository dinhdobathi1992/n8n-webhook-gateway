# Code Standards & Patterns

## Python Backend

### Framework & Style
- **Python 3.12** with type hints throughout
- **FastAPI** with async/await everywhere (no sync endpoints)
- **Pydantic v2** for request/response validation (`model_config = {"from_attributes": True}`)
- **pydantic-settings** for environment configuration
- **SQLAlchemy 2.0** mapped_column style (not legacy Column)

### Project Layout
```
app/
  main.py           # App entry, lifespan, middleware, static serving
  config.py          # Single Settings class
  db.py              # Engine + session factory
  models.py          # All ORM models
  schemas.py         # All Pydantic schemas
  auth.py            # Pure functions (hash, verify, encode, decode)
  forwarding.py      # HTTP forwarding logic (no DB dependency)
  api/               # Authenticated management endpoints
    router.py        # Router aggregation
    auth.py          # Login/logout + auth dependency
    webhooks.py      # Route CRUD + delivery log
  inbound/           # Public proxy endpoints
    http.py          # Webhook catch-all route
```

### Patterns Used

**Dependency injection**: FastAPI `Depends()` for DB sessions and auth.
```python
async def get_current_user(request: Request, session: AsyncSession = Depends(get_session)) -> User:
```

**Lifespan context manager**: startup/shutdown logic in `@asynccontextmanager` rather than deprecated `on_event`.
```python
@asynccontextmanager
async def lifespan(application: FastAPI):
    # startup: create tables, seed admin
    yield
    # shutdown: (nothing currently)
```

**Dataclass for internal results**: `ForwardResult` is a plain dataclass, not a Pydantic model -- it never crosses API boundaries.

**Response builder pattern**: `_to_response()` in webhooks.py converts ORM model to Pydantic response with computed fields (webhook_url, signing_secret_set).

**In-memory rate limiting**: `defaultdict(list)` of timestamps per IP. Simple, no Redis dependency. Cleared on process restart (acceptable for single-instance).

### Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Python files | snake_case | `forwarding.py` |
| Python classes | PascalCase | `WebhookRoute`, `ForwardResult` |
| Python functions | snake_case | `forward_request`, `verify_slack_signature` |
| API routes | kebab-style paths | `/api/webhooks`, `/api/auth/login` |
| DB tables | snake_case plural | `webhook_routes`, `delivery_attempts` |
| Env vars | UPPER_SNAKE_CASE | `SECRET_KEY`, `FORWARD_MAX_RETRIES` |
| TypeScript files | PascalCase (pages/components), camelCase (lib) | `RouteForm.tsx`, `api.ts` |

### Error Handling
- FastAPI `HTTPException` for all API errors with appropriate status codes
- 401 for auth failures, 404 for missing routes, 409 for slug conflicts, 429 for rate limits
- Forwarding errors caught as `httpx.TimeoutException` / `httpx.ConnectError` -- logged and retried
- Response body excerpts capped at 1000 chars to prevent DB bloat

### Validation Rules
- Slug: `^[a-zA-Z0-9_-]{1,64}$` regex, reserved slugs blocked (`api`, `health`, `docs`, `openapi.json`, `redoc`, `ui`)
- Destination URL: must start with `http://` or `https://`
- Login rate limit: 5 attempts per IP per 300 seconds

### Security Patterns
- Passwords hashed with bcrypt (auto-salted)
- JWT tokens signed with HS256, 24h expiry
- httpOnly cookies (no JS access to token)
- Secure cookie flag derived from PUBLIC_BASE_URL scheme
- CORS restricted to single origin (PUBLIC_BASE_URL)
- Path traversal check on static file serving: `file_path.is_relative_to(ui_dist.resolve())`
- Slack signature verification uses `hmac.compare_digest` (timing-safe comparison)
- 5-minute timestamp tolerance on Slack signatures

### Database Patterns
- Async SQLAlchemy with aiosqlite
- `async_sessionmaker` with `expire_on_commit=False`
- Tables auto-created on startup via `Base.metadata.create_all`
- No migration framework (Alembic) -- tables created fresh, schema changes require manual migration
- Soft-delete for routes (enabled=false), hard-create for delivery logs

## TypeScript Frontend

### Stack
- React 18 with functional components and hooks
- Vite build tool
- TypeScript strict mode
- No state management library (local state + prop drilling)
- No CSS framework -- custom CSS with Apple-style design

### Patterns
- **Page-level data fetching**: each page fetches its own data in `useEffect`
- **API module**: centralized `api.ts` with typed fetch wrappers, credentials: "include"
- **Cookie auth**: no token management in frontend -- browser handles httpOnly cookie automatically
- **SPA routing**: React Router with catch-all served by FastAPI

### Component Structure
- Pages: full-page views with data fetching (Login, Dashboard, RouteForm, RouteDetail)
- Components: presentational/reusable (RouteTable, DeliveryLog, TestPanel, CopyButton)
- No shared layout component -- each page self-contained

## Testing

### Framework
- pytest with pytest-asyncio (`asyncio_mode = auto`)
- In-memory SQLite for test DB
- httpx `ASGITransport` for testing FastAPI without network
- `unittest.mock.patch` for mocking httpx calls in forwarding tests

### Test Organization
- `conftest.py`: shared fixtures (test client, auth helper, DB setup)
- One test file per module/feature
- Test functions named `test_<behavior>` (e.g., `test_login_success`, `test_slug_conflict`)

### Running Tests
```bash
pytest                    # all tests
pytest tests/test_auth.py # single file
pytest -v                 # verbose output
```

## Docker

### Build Pattern
Multi-stage Dockerfile:
1. **Stage 1** (`node:20-slim`): build React UI (`npm run build`)
2. **Stage 2** (`python:3.12-slim`): install Python deps, copy app code + built UI

### Compose Pattern
- Single service with named volume for DB persistence
- Health check using Python httpx
- `env_file` for configuration
- DATABASE_URL overridden to use volume mount path
