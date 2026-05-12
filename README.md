# n8n Webhook Gateway

HTTP proxy that sits between Slack (or any webhook source) and n8n. Register routes, forward requests, log deliveries.

```
Slack ──HTTP──▶ gateway.example/my-bot/webhook ──▶ n8n.example/webhook/abc
```

## Why

n8n webhooks are public URLs. This gateway adds:
- Auth header injection (n8n Header Auth)
- Slack signature verification
- Retry on failure (exponential backoff)
- Delivery logging (status, latency, response)
- One URL per Slack app, route to multiple n8n workflows

## Quick Start

```bash
git clone https://github.com/dinhdobathi/n8n-webhook-gateway
cd n8n-webhook-gateway
cp .env.example .env    # edit SECRET_KEY and ADMIN_PASSWORD
docker compose up -d
# open http://localhost:3000
```

Login: `admin` / `admin` (change in `.env`)

## How It Works

1. Create route in UI: slug `my-bot` → destination `https://n8n.example.com/webhook/abc`
2. Set auth header if n8n webhook uses Header Auth: name `x-api-key`, value `your-secret`
3. Configure Slack Event Subscriptions URL: `https://gateway.example/my-bot/webhook`
4. Slack sends events → gateway verifies (optional) → forwards with auth → logs delivery

## Config

| Variable | Default | What |
|----------|---------|------|
| `SECRET_KEY` | `change-me` | JWT signing. **Change this.** |
| `ADMIN_USERNAME` | `admin` | Login username |
| `ADMIN_PASSWORD` | `admin` | Login password |
| `PUBLIC_BASE_URL` | `http://localhost:3000` | Shown in webhook URLs |
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

```bash
curl -b cookies -X POST http://localhost:3000/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "my-bot",
    "destination_url": "https://n8n.example.com/webhook/abc",
    "auth_header_name": "x-api-key",
    "auth_header_value": "secret123"
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

**Docker Hub**: `dinhdobathi/n8n-webhook-gateway:latest`

## Stack

Python 3.12 · FastAPI · SQLite · React · Vite · Docker

## Docs

- [System Architecture](docs/system-architecture.md)
- [Deployment Guide](docs/deployment-guide.md)
- [Project Roadmap](docs/project-roadmap.md)
