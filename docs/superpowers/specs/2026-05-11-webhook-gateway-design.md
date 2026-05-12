# n8n Webhook Gateway — Design Spec

## Overview

HTTP-only webhook gateway. Receives inbound HTTP requests on registered slug endpoints, optionally verifies Slack signatures, forwards to destination URLs (typically n8n webhooks), logs delivery attempts. Management UI built with React + Vite + getdesign apple.

Single FastAPI process. No Slack SDK. No Socket Mode.

## Architecture

```
                   ┌─────────────────────────────────┐
                   │         FastAPI Process          │
                   │                                  │
  Slack HTTP ──────┤  /{slug}/webhook  (inbound)      │
  Any HTTP ────────┤                                  │──── httpx ────▶ n8n / destination
                   │  /api/*           (management)   │
  Browser ─────────┤  /*               (UI static)    │
                   └─────────────────────────────────┘
                              │
                         SQLite DB
```

Two concerns in one process:
1. **Inbound proxy** — `/{slug}/webhook` accepts any HTTP method, verifies signature if configured, forwards to destination, logs delivery.
2. **Management API** — auth, route CRUD, delivery logs.

UI served as static files from `ui/dist/` in production. Vite dev server proxies to FastAPI in development.

## Data Model

### users

| Field | Type | Notes |
|-------|------|-------|
| id | integer PK | auto |
| username | string unique | |
| password_hash | string | bcrypt |
| created_at | datetime | |
| updated_at | datetime | |

Admin user seeded on startup when no users exist. Credentials from `ADMIN_USERNAME` + `ADMIN_PASSWORD` env vars.

### webhook_routes

| Field | Type | Notes |
|-------|------|-------|
| id | integer PK | auto |
| slug | string unique | URL-safe, `^[a-zA-Z0-9_-]{1,64}$` |
| destination_url | string | must be http:// or https:// |
| enabled | boolean | default true |
| signing_secret | string nullable | if set, verify inbound Slack signature + sign outbound |
| description | string nullable | human label for UI |
| created_by | integer FK → users | |
| created_at | datetime | |
| updated_at | datetime | |

Reserved slugs (rejected on create): `api`, `health`, `docs`, `openapi.json`, `redoc`, `ui`.

### delivery_attempts

| Field | Type | Notes |
|-------|------|-------|
| id | integer PK | auto |
| route_id | integer FK → webhook_routes | |
| source_event_id | string nullable | from request header if present |
| method | string | GET, POST, etc. |
| status | string | pending, success, failed |
| attempt_count | integer | |
| response_status | integer nullable | destination HTTP status |
| response_body_excerpt | string nullable | first 1000 chars |
| error | string nullable | exception message |
| latency_ms | integer nullable | round-trip time |
| created_at | datetime | |

## API Surface

### Health

`GET /health` — no auth

```json
{"status": "ok", "routes": 3}
```

### Auth

`POST /api/auth/login` — returns HTTP-only session cookie

```json
// request
{"username": "admin", "password": "password"}
// response
{"ok": true}
```

`POST /api/auth/logout` — clears cookie

### Route CRUD (all require auth)

**Create:** `POST /api/webhooks`

```json
// request
{
  "slug": "my-route",
  "destination_url": "https://n8n.example/webhook/xxx",
  "signing_secret": "optional-secret",
  "description": "Slack events for project X"
}
// response
{
  "id": 1,
  "slug": "my-route",
  "destination_url": "https://n8n.example/webhook/xxx",
  "enabled": true,
  "signing_secret_set": true,
  "description": "Slack events for project X",
  "webhook_url": "https://gateway.example/my-route/webhook",
  "created_at": "2026-05-11T00:00:00Z"
}
```

Validation:
- `slug` must match `^[a-zA-Z0-9_-]{1,64}$`
- `slug` must not be reserved
- `destination_url` must start with `http://` or `https://`

**List:** `GET /api/webhooks` — returns array of routes

**Get:** `GET /api/webhooks/{id}` — single route

**Update:** `PATCH /api/webhooks/{id}` — partial update (destination, enabled, signing_secret, description)

**Delete:** `DELETE /api/webhooks/{id}` — soft-disable (set enabled=false)

**Deliveries:** `GET /api/webhooks/{id}/deliveries` — paginated delivery log

### Inbound Proxy

`ANY /{slug}/webhook` — no auth, public endpoint

Behavior:
1. Look up enabled route by `slug`. 404 if missing or disabled.
2. If route has `signing_secret` and request has `X-Slack-Signature` header: verify Slack signature. 401 if invalid.
3. Forward request: method, query params, raw body, content-type, safe headers.
4. Add gateway headers to forwarded request:
   - `X-Gateway-Route: {slug}`
   - `X-Gateway-Delivery-Id: {uuid}`
   - `X-Gateway-Timestamp: {unix-timestamp}`
   - `X-Gateway-Signature: {hmac}` (only if route has `signing_secret`)
5. Return destination response status + body to caller.
6. Log delivery attempt.

## Forwarding

- `httpx.AsyncClient` with shared client instance (connection pooling)
- Timeout: configurable, default 30s
- Retry: on 5xx, timeout, connection error. No retry on 4xx.
- Max retries: configurable, default 3
- Backoff: exponential (1s, 2s, 4s)
- HMAC signing: SHA256 of raw body bytes, keyed with route `signing_secret`
- Slack signature verification: stdlib `hmac.compare_digest` using route `signing_secret`

## Signature Verification (Inbound)

When route has `signing_secret` and request has Slack headers:

1. Read `X-Slack-Request-Timestamp` — reject if older than 5 minutes (replay protection).
2. Compute `v0=HMAC-SHA256(signing_secret, "v0:{timestamp}:{body}")`.
3. Compare with `X-Slack-Signature` using constant-time comparison.
4. Reject with 401 if mismatch.

If route has no `signing_secret`: skip verification, forward everything.

## Gateway Signing (Outbound)

When route has `signing_secret`:

1. `X-Gateway-Timestamp`: current unix timestamp.
2. `X-Gateway-Signature`: `sha256=HMAC-SHA256(signing_secret, "{timestamp}.{body}")`.

Destination can verify gateway authenticity using same secret.

## Environment Variables

Required:
```
PORT=3000
DATABASE_URL=sqlite+aiosqlite:///./gateway.db
SECRET_KEY=<random-long-secret>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<initial-password>
PUBLIC_BASE_URL=https://gateway.example
```

Optional:
```
FORWARD_TIMEOUT_SECONDS=30
FORWARD_MAX_RETRIES=3
FORWARD_RETRY_BASE_SECONDS=1
```

## UI

React + Vite + TypeScript SPA with getdesign apple design system.

### Pages

1. **Login** — username/password form, redirects to dashboard on success.
2. **Dashboard** — table of all routes. Columns: slug, destination (truncated), status badge (enabled/disabled), webhook URL (copyable), created date. Actions: edit, disable/enable, delete.
3. **Create/Edit Route** — form with fields: slug, destination URL, description, signing secret (toggle + input). Shows generated webhook URL after save.
4. **Route Detail** — route info + delivery log table. Columns: timestamp, method, status badge (success/failed), response code, latency. Paginated.
5. **Test Panel** — on route detail page. Button to send test POST to `/{slug}/webhook`. Shows response inline.

### Dev Setup

```bash
cd ui
pnpm install
npx getdesign@latest add apple
pnpm dev  # proxies /api and /{slug} to localhost:3000
```

### Production

FastAPI mounts `ui/dist/` as static files at `/`. Catch-all route serves `index.html` for client-side routing. API routes take precedence.

## File Layout

```
app/
  __init__.py
  main.py              # FastAPI app, startup, static mount
  config.py            # env var parsing
  db.py                # async engine, session maker
  models.py            # SQLAlchemy models (users, webhook_routes, delivery_attempts)
  schemas.py           # Pydantic request/response schemas
  auth.py              # password hashing, cookie session, auth dependency
  forwarding.py        # httpx forward, retry, HMAC sign/verify
  api/
    __init__.py
    auth.py            # POST /api/auth/login, /logout
    webhooks.py        # CRUD /api/webhooks
  inbound/
    __init__.py
    http.py            # ANY /{slug}/webhook
ui/
  package.json
  vite.config.ts
  tsconfig.json
  src/
    App.tsx
    main.tsx
    pages/
      Login.tsx
      Dashboard.tsx
      RouteForm.tsx
      RouteDetail.tsx
    components/
      RouteTable.tsx
      DeliveryLog.tsx
      TestPanel.tsx
      CopyButton.tsx
    lib/
      api.ts           # fetch wrapper with cookie auth
tests/
  conftest.py
  test_auth.py
  test_webhooks.py
  test_forwarding.py
  test_inbound.py
requirements.txt
Dockerfile
k8s/
```

## Python Dependencies

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
httpx>=0.25.0
sqlalchemy[asyncio]>=2.0.0
aiosqlite>=0.19.0
passlib[bcrypt]>=1.7.4
python-jose[cryptography]>=3.3.0
python-dotenv>=1.0.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

No slack-bolt. No slack-sdk. Signature verification uses stdlib `hmac` + `hashlib`.

## Acceptance Criteria

- Admin can log in with seeded credentials.
- Admin can create route with slug + destination URL.
- API returns computed `webhook_url` using `PUBLIC_BASE_URL`.
- `POST /{slug}/webhook` forwards payload to destination and returns response.
- `GET /{slug}/webhook` also forwards (any HTTP method supported).
- Disabled route returns 404.
- Route with `signing_secret` verifies inbound Slack signatures. Invalid signature returns 401.
- Route with `signing_secret` adds `X-Gateway-Signature` to outbound request.
- Destination 5xx retries up to configured limit with exponential backoff.
- Destination 4xx recorded as failed, no retry.
- Delivery attempts logged with status, response code, latency.
- UI shows route list, create/edit forms, delivery logs.
- UI copyable webhook URL for each route.
- No real secrets committed to repo.
