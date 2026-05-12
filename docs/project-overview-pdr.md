# Project Overview & Product Development Requirements

**Project**: n8n Webhook Gateway
**Status**: Production
**Docker Image**: `dinhdobathi/n8n-webhook-gateway`

## Purpose

HTTP webhook gateway that sits between external event sources (Slack, GitHub, etc.) and n8n workflow automation. Provides a stable public URL layer with routing, signature verification, auth injection, retry logic, and delivery tracking.

### Problem Statement

n8n webhook URLs change when workflows are recreated or moved between instances. External integrations (Slack apps, GitHub webhooks) break when URLs change. Direct exposure of n8n webhook URLs also lacks:
- Inbound signature verification (e.g., Slack signing)
- Outbound auth header injection
- Retry on failure
- Delivery audit trail

### Solution

A lightweight HTTP proxy that:
1. Maps stable slugs to destination URLs
2. Verifies inbound signatures (Slack)
3. Injects auth headers on forwarded requests
4. Signs outbound payloads with HMAC
5. Retries on 5xx/timeout with exponential backoff
6. Logs every delivery attempt with status, latency, response excerpt

## Core Features

### Route Management
- CRUD operations on webhook routes via REST API
- Each route: slug, destination URL, optional signing secret, optional auth header, description
- Slug validation: `^[a-zA-Z0-9_-]{1,64}$`, reserved slugs blocked (api, health, docs, etc.)
- Soft-delete (disable) rather than hard delete

### Inbound Proxy
- Public endpoint: `/{slug}/webhook`
- Accepts any HTTP method (GET, POST, PUT, PATCH, DELETE)
- Forwards body, content-type, and query string to destination
- Handles Slack URL verification challenge (after signature check)

### Security Per Route
- **Slack signature verification**: validates `x-slack-signature` using route's signing secret
- **Destination auth header**: injects configurable header (e.g., `x-api-key: value`) on forwarded request
- **Gateway HMAC signing**: adds `X-Gateway-Signature` header (SHA256) on outbound

### Retry Logic
- Retries on HTTP 5xx or connection timeout
- Exponential backoff: `base * 2^(attempt-1)` seconds
- Configurable max retries (default 3), timeout (default 30s), base delay (default 1s)

### Delivery Logging
- Every forwarded request creates a `DeliveryAttempt` record
- Tracks: method, status (success/failed), attempt count, response code, response excerpt (1000 chars), error message, latency in ms
- Queryable via API with pagination (limit/offset)

### Authentication
- JWT cookie-based auth for management API
- Admin user auto-seeded on startup from env vars
- Rate limiting: 5 login attempts per IP per 5 minutes
- httpOnly cookie, secure flag when HTTPS, samesite=lax
- 24-hour token expiry

### Admin UI
- React + Vite + TypeScript SPA
- Pages: Login, Dashboard (route list), RouteForm (create/edit), RouteDetail (deliveries + test)
- Components: RouteTable, DeliveryLog, TestPanel, CopyButton
- Apple-style minimal design
- Served as static files from FastAPI (SPA fallback routing)

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Latency overhead | < 50ms added to forwarding |
| Concurrent routes | Hundreds (SQLite adequate) |
| Availability | Single-replica acceptable; no HA requirement currently |
| Data retention | SQLite file; no auto-cleanup of delivery logs yet |
| Auth model | Single admin user; no multi-tenancy |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, uvicorn |
| HTTP client | httpx (async) |
| Database | SQLAlchemy async + aiosqlite (SQLite) |
| Auth | bcrypt (passwords), python-jose (JWT) |
| Frontend | React 18, Vite, TypeScript |
| Container | Docker multi-stage build |
| Orchestration | Docker Compose, Kubernetes (EKS) |

## User Roles

| Role | Capabilities |
|------|-------------|
| Admin | Full CRUD on routes, view delivery logs, test webhooks |
| Public (unauthenticated) | Send requests to `/{slug}/webhook` endpoints |

## Data Model

### User
- id, username, password_hash, created_at, updated_at

### WebhookRoute
- id, slug (unique, indexed), destination_url, enabled, signing_secret, auth_header_name, auth_header_value, description, created_by (FK to User), created_at, updated_at

### DeliveryAttempt
- id, route_id (FK), source_event_id, method, status, attempt_count, response_status, response_body_excerpt, error, latency_ms, created_at

## API Surface

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | No | Health check + route count |
| `POST /api/auth/login` | No | JWT cookie login |
| `POST /api/auth/logout` | No | Clear cookie |
| `GET /api/webhooks` | Yes | List routes |
| `POST /api/webhooks` | Yes | Create route |
| `GET /api/webhooks/{id}` | Yes | Get route |
| `PATCH /api/webhooks/{id}` | Yes | Update route |
| `DELETE /api/webhooks/{id}` | Yes | Disable route |
| `GET /api/webhooks/{id}/deliveries` | Yes | Delivery log |
| `ANY /{slug}/webhook` | No | Public inbound proxy |

## Constraints & Decisions

1. **SQLite** chosen for simplicity -- single-file DB, no external dependency. Adequate for expected load (< 100 routes, < 1000 req/min).
2. **No Slack SDK** -- pure HTTP signature verification. Avoids SDK dependency bloat.
3. **Soft-delete** on routes -- `DELETE` sets `enabled=false` rather than removing the row. Preserves delivery history.
4. **Single admin** -- no multi-user or RBAC. Sufficient for internal tooling.
5. **Cookie auth** over bearer tokens -- simpler for browser-based UI, httpOnly prevents XSS token theft.
