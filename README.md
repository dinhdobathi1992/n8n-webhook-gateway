# n8n Webhook Gateway

HTTP webhook gateway that forwards inbound requests to registered destination URLs (typically n8n webhooks). Single FastAPI process with React UI. No Slack SDK -- pure HTTP proxy.

## Features

- **Route management** -- register webhook routes with slug-to-destination URL mapping
- **Public proxy endpoint** -- `/{slug}/webhook` forwards any HTTP method to destination
- **Slack signature verification** -- optional inbound Slack request validation per route
- **Destination auth** -- optional auth header (e.g. `x-api-key`) injected per route
- **Gateway HMAC signing** -- outbound `X-Gateway-Signature` header per route
- **Retry with backoff** -- exponential backoff on 5xx/timeout (configurable)
- **Delivery logging** -- every forwarded request logged with status, response code, latency
- **JWT cookie auth** -- management API protected by httpOnly cookie
- **Admin auto-seed** -- first admin user created on startup from env vars
- **React UI** -- Apple-style admin interface for route management and delivery inspection

## Quick Start

### Docker Compose (recommended)

```bash
# 1. Create env file
cp .env.example .env
# Edit .env -- set SECRET_KEY to a strong random value

# 2. Start
docker compose up -d

# 3. Open UI
open http://localhost:3000
```

Default credentials: `admin` / `admin` (change via `ADMIN_USERNAME` / `ADMIN_PASSWORD` in `.env`).

### Local Development

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 3000

# Frontend (separate terminal)
cd ui && npm install && npm run dev
```

## Configuration

All settings via environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3000` | Server port |
| `DATABASE_URL` | `sqlite+aiosqlite:///./gateway.db` | SQLAlchemy async DB URL |
| `SECRET_KEY` | `change-me` | JWT signing key -- **must change in production** |
| `ADMIN_USERNAME` | `admin` | Auto-seeded admin username |
| `ADMIN_PASSWORD` | `admin` | Auto-seeded admin password |
| `PUBLIC_BASE_URL` | `http://localhost:3000` | Used for CORS and webhook URL display |
| `FORWARD_TIMEOUT_SECONDS` | `30` | HTTP timeout per forwarding attempt |
| `FORWARD_MAX_RETRIES` | `3` | Max retry attempts on 5xx/timeout |
| `FORWARD_RETRY_BASE_SECONDS` | `1` | Base delay for exponential backoff |

## API Reference

### Public

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check -- returns `{"status":"ok","routes":N}` |
| `ANY` | `/{slug}/webhook` | Inbound proxy -- forwards to registered destination |

### Auth

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Login -- sets httpOnly JWT cookie |
| `POST` | `/api/auth/logout` | Logout -- clears cookie |

### Webhook Routes (requires auth)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/webhooks` | List all routes |
| `POST` | `/api/webhooks` | Create route |
| `GET` | `/api/webhooks/{id}` | Get route detail |
| `PATCH` | `/api/webhooks/{id}` | Update route |
| `DELETE` | `/api/webhooks/{id}` | Soft-delete (disables) route |
| `GET` | `/api/webhooks/{id}/deliveries` | Delivery attempt log |

### Route Create/Update Payload

```json
{
  "slug": "my-slack-bot",
  "destination_url": "https://n8n.example.com/webhook/abc123",
  "signing_secret": "optional-slack-signing-secret",
  "auth_header_name": "x-api-key",
  "auth_header_value": "secret-value",
  "description": "Slack bot webhook"
}
```

### Forwarded Request Headers

The gateway injects these headers on every forwarded request:

| Header | Value |
|--------|-------|
| `X-Gateway-Route` | Route slug |
| `X-Gateway-Delivery-Id` | UUID for this delivery |
| `X-Gateway-Timestamp` | Unix timestamp |
| `X-Gateway-Signature` | HMAC-SHA256 signature (if signing_secret set) |

## Security

- Path traversal protection on static file serving
- Rate limiting: 5 login attempts per IP per 5 minutes
- Secure cookie flag auto-enabled when `PUBLIC_BASE_URL` is HTTPS
- CORS restricted to `PUBLIC_BASE_URL` origin only
- Slack URL verification challenge handled after signature check
- Weak `SECRET_KEY` warning logged on startup

## Deployment

- **Docker Compose** -- `docker compose up -d` (see above)
- **Kubernetes** -- EKS manifests in `k8s/` (namespace: `platformbot`)
- **Docker Hub** -- `dinhdobathi/n8n-webhook-gateway:latest`

See [docs/deployment-guide.md](docs/deployment-guide.md) for full deployment instructions.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, httpx, SQLAlchemy async, aiosqlite
- **Auth**: bcrypt (password hashing), python-jose (JWT)
- **Frontend**: React, Vite, TypeScript
- **Infra**: Docker, Docker Compose, Kubernetes (EKS)

## Project Structure

```
app/
  main.py          # FastAPI app, lifespan, static serving
  config.py        # Pydantic settings from env
  db.py            # SQLAlchemy async engine + session
  models.py        # User, WebhookRoute, DeliveryAttempt
  schemas.py       # Pydantic request/response models
  auth.py          # Password hashing, JWT encode/decode
  forwarding.py    # HTTP forwarding, retry logic, HMAC signing
  api/
    router.py      # API router aggregation
    auth.py        # Login/logout, rate limiting, cookie auth
    webhooks.py    # Route CRUD, delivery log
  inbound/
    http.py        # Public webhook proxy endpoint
ui/src/
  pages/           # Login, Dashboard, RouteForm, RouteDetail
  components/      # RouteTable, DeliveryLog, TestPanel, CopyButton
  lib/api.ts       # HTTP client for management API
tests/             # pytest-asyncio test suite (31 tests)
k8s/               # Kubernetes deployment manifests
```

## Documentation

- [Project Overview](docs/project-overview-pdr.md)
- [System Architecture](docs/system-architecture.md)
- [Codebase Summary](docs/codebase-summary.md)
- [Code Standards](docs/code-standards.md)
- [Deployment Guide](docs/deployment-guide.md)
- [Project Roadmap](docs/project-roadmap.md)

## License

Internal project.
