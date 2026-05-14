# n8n Webhook Gateway

HTTP proxy between webhook sources (Slack, Google Chat, Telegram, etc.) and n8n. Register routes, verify signatures, forward requests, log deliveries.

```
Slack/GChat/Telegram ──HTTP──▶ gateway.example/my-bot/webhook ──▶ n8n.example/webhook/abc
```

## Why

n8n webhooks are public URLs. This gateway adds:
- **Multi-source verification** — Slack HMAC-SHA256, Google Chat JWT, generic header-based
- **Field encryption** — signing secrets and auth values encrypted at rest (Fernet/AES)
- **Auth header injection** — forward requests with n8n Header Auth credentials
- **Retry on failure** — exponential backoff on 5xx/timeout
- **Delivery logging** — status, latency, response excerpt per request
- **Session persistence** — cookie-based auth survives page refresh

## Quick Start

```bash
git clone https://github.com/dinhdobathi1992/n8n-webhook-gateway
cd n8n-webhook-gateway
cp .env.example .env    # edit SECRET_KEY and ADMIN_PASSWORD
docker compose up -d
# open http://localhost:3000
```

Login: `admin` / `admin` (change in `.env`)

## Source Types

| Type | Verification | Required Fields |
|------|-------------|-----------------|
| **slack** | HMAC-SHA256 (`v0:timestamp:body`) + url_verification | `signing_secret` |
| **gchat** | JWT Bearer token via Google public keys | none |
| **generic** | Header value comparison (timing-safe) | `signing_secret` + `secret_header_name` |

### Examples

**Slack** — paste your Signing Secret from Slack App → Basic Information.

**Telegram** — create a generic route with `secret_header_name: X-Telegram-Bot-Api-Secret-Token` and set `signing_secret` to the `secret_token` you pass to `setWebhook`.

**GitHub** — create a generic route with `secret_header_name: X-Hub-Signature-256` and your webhook secret.

## Config

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-me` | JWT signing + field encryption key. **Change this.** |
| `ADMIN_USERNAME` | `admin` | Login username |
| `ADMIN_PASSWORD` | `admin` | Login password |
| `PUBLIC_BASE_URL` | `http://localhost:3000` | Shown in webhook URLs, used as gchat JWT audience |
| `DATABASE_URL` | `sqlite+aiosqlite:///./gateway.db` | DB connection |
| `FORWARD_TIMEOUT_SECONDS` | `30` | Per-attempt timeout |
| `FORWARD_MAX_RETRIES` | `3` | Retry on 5xx/timeout |

## API

```
GET  /health                      → {"status":"ok","routes":3}
POST /api/auth/login              → set cookie
POST /api/auth/logout             → clear cookie

GET  /api/webhooks                → list routes
POST /api/webhooks                → create route
GET  /api/webhooks/:id            → get route
PATCH /api/webhooks/:id           → update route
DELETE /api/webhooks/:id          → disable route
GET  /api/webhooks/:id/deliveries → delivery log

ANY  /:slug/webhook               → public proxy (no auth)
```

### Create Route

**Slack:**
```bash
curl -b cookies -X POST http://localhost:3000/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "my-bot",
    "destination_url": "https://n8n.example.com/webhook/abc",
    "source_type": "slack",
    "signing_secret": "your-slack-signing-secret"
  }'
```

**Generic (Telegram):**
```bash
curl -b cookies -X POST http://localhost:3000/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "telegram",
    "destination_url": "https://n8n.example.com/webhook/xyz",
    "source_type": "generic",
    "signing_secret": "your-telegram-secret-token",
    "secret_header_name": "X-Telegram-Bot-Api-Secret-Token"
  }'
```

Gateway adds these headers when forwarding:
- `X-Gateway-Route` — slug
- `X-Gateway-Delivery-Id` — UUID
- `X-Gateway-Timestamp` — unix timestamp
- `X-Gateway-Signature` — HMAC (if `signing_secret` set)
- Your auth header (if configured)

## Deploy

**Docker Compose** (easiest):
```bash
docker compose up -d
```

**Kubernetes** (EKS manifests in `k8s/`):
```bash
cp k8s/secret.yaml.example k8s/secret.yaml  # fill values
kubectl apply -f k8s/
```

**Docker Hub**: `dinhdobathi/n8n-webhook-gateway:latest` (amd64 + arm64)

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ui && pnpm install && pnpm build && cd ..
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

Run tests:
```bash
pytest tests/ -q    # 46 tests
```

## Stack

Python 3.12 · FastAPI · SQLAlchemy · SQLite · Fernet encryption · React · Vite · Docker

## Docs

- [System Architecture](docs/system-architecture.md)
- [Deployment Guide](docs/deployment-guide.md)
- [Project Roadmap](docs/project-roadmap.md)
