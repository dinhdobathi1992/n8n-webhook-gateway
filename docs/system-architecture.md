# System Architecture

## Overview

Single-process Python application serving both the API backend and React frontend. No external services beyond SQLite.

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Process                       │
│                                                         │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Static   │  │ Management   │  │ Inbound Proxy    │  │
│  │ Files    │  │ API (/api)   │  │ (/{slug}/webhook)│  │
│  │ (React)  │  │              │  │                  │  │
│  └──────────┘  └──────┬───────┘  └────────┬─────────┘  │
│                       │                    │            │
│                ┌──────┴────────────────────┴──────┐     │
│                │        SQLAlchemy Async          │     │
│                └──────────────┬───────────────────┘     │
│                               │                         │
│                        ┌──────┴──────┐                  │
│                        │   SQLite    │                  │
│                        │  (gateway.db)│                  │
│                        └─────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. FastAPI Application (`app/main.py`)

Entry point. Responsibilities:
- Lifespan management (DB init, admin seeding)
- CORS middleware configuration
- Router registration
- Static file serving (React SPA)

### 2. Management API (`app/api/`)

Protected by JWT cookie auth. Three sub-modules:

| Module | Prefix | Purpose |
|--------|--------|---------|
| `auth.py` | `/api/auth` | Login/logout, rate limiting |
| `webhooks.py` | `/api/webhooks` | Route CRUD, delivery log |
| `router.py` | -- | Aggregates sub-routers |

### 3. Inbound Proxy (`app/inbound/http.py`)

Public-facing. Single catch-all endpoint `/{slug}/webhook`. No authentication required.

### 4. Forwarding Engine (`app/forwarding.py`)

Pure HTTP logic, no DB dependency. Handles:
- Slack signature verification (inbound)
- Gateway HMAC signing (outbound)
- HTTP forwarding with retry + backoff

### 5. Data Layer (`app/db.py`, `app/models.py`)

Async SQLAlchemy with aiosqlite. Three tables, auto-created on startup.

### 6. React UI (`ui/`)

SPA built with Vite, served as static files. Communicates with Management API via cookie auth.

## Data Flow Diagrams

### Inbound Webhook Processing

```
External Source (Slack, GitHub, etc.)
        │
        ▼
  /{slug}/webhook  (any HTTP method)
        │
        ▼
  ┌─────────────────┐
  │ Route Lookup     │──── 404 if not found or disabled
  │ (by slug)        │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ Slack Sig Check  │──── 401 if invalid signature
  │ (if applicable)  │     (only when route has signing_secret
  └────────┬────────┘      AND request has x-slack-signature)
           │
           ▼
  ┌─────────────────┐
  │ URL Verification │──── Returns challenge response
  │ (Slack only)     │     (type: url_verification)
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ Forward Request  │
  │                  │
  │ Headers injected:│
  │ - Content-Type   │
  │ - X-Gateway-*    │
  │ - Auth header    │
  │ - HMAC signature │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐     ┌──────────────┐
  │ Retry Loop      │────►│ Destination  │
  │ (max 3 attempts)│◄────│ (n8n, etc.)  │
  │ Backoff: 1,2,4s │     └──────────────┘
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ Log Delivery    │
  │ Attempt to DB   │
  └────────┬────────┘
           │
           ▼
  Return response to caller
```

### Authentication Flow

```
Browser
  │
  ▼
POST /api/auth/login
  │
  ├─► Rate limit check (5/IP/5min)
  │     └── 429 if exceeded
  │
  ├─► Verify credentials (bcrypt)
  │     └── 401 if invalid
  │
  ├─► Generate JWT (HS256, 24h expiry)
  │
  └─► Set httpOnly cookie (gateway_token)
        │
        ▼
  Subsequent API requests
  include cookie automatically
        │
        ▼
  get_current_user dependency
  decodes JWT, loads User from DB
```

### Route Management Flow

```
Admin UI (React SPA)
  │
  ├─► GET /api/webhooks          → List all routes
  ├─► POST /api/webhooks         → Create route (slug validation)
  ├─► PATCH /api/webhooks/{id}   → Update route fields
  ├─► DELETE /api/webhooks/{id}  → Soft-delete (enabled=false)
  └─► GET /api/webhooks/{id}/deliveries → View delivery log
```

## Database Schema

```
┌──────────────┐       ┌───────────────────┐       ┌───────────────────┐
│    users     │       │  webhook_routes   │       │ delivery_attempts │
├──────────────┤       ├───────────────────┤       ├───────────────────┤
│ id (PK)      │◄──┐   │ id (PK)           │◄──┐   │ id (PK)           │
│ username     │   └───│ created_by (FK)   │   └───│ route_id (FK)     │
│ password_hash│       │ slug (unique, idx)│       │ source_event_id   │
│ created_at   │       │ destination_url   │       │ method            │
│ updated_at   │       │ enabled           │       │ status            │
└──────────────┘       │ signing_secret    │       │ attempt_count     │
                       │ auth_header_name  │       │ response_status   │
                       │ auth_header_value │       │ response_body_exc │
                       │ description       │       │ error             │
                       │ created_at        │       │ latency_ms        │
                       │ updated_at        │       │ created_at        │
                       └───────────────────┘       └───────────────────┘
```

## Gateway Headers

Headers injected on every forwarded request:

| Header | Source | Always Present |
|--------|--------|----------------|
| `Content-Type` | Copied from inbound request | Yes |
| `X-Gateway-Route` | Route slug | Yes |
| `X-Gateway-Delivery-Id` | Generated UUID | Yes |
| `X-Gateway-Timestamp` | Unix epoch (seconds) | Yes |
| `X-Gateway-Signature` | HMAC-SHA256 of `{timestamp}.{body}` | Only if signing_secret set |
| Custom auth header | Route's auth_header_name/value | Only if configured |

## Retry Strategy

```
Attempt 1: immediate
  └── 5xx or timeout? → wait 1s
Attempt 2: retry
  └── 5xx or timeout? → wait 2s
Attempt 3: retry
  └── 5xx or timeout? → give up, status=failed
```

- Only retries on HTTP 5xx or connection errors (timeout, connect failure)
- 4xx responses are not retried (treated as success delivery)
- Backoff formula: `base_seconds * 2^(attempt-1)`
- All configurable via env vars

## Security Architecture

### Inbound Security
- **Slack signature verification**: HMAC-SHA256 with route-specific signing secret, 5-min timestamp tolerance
- **No auth on proxy endpoint**: by design -- external sources need unauthenticated access

### Management API Security
- **JWT cookie auth**: httpOnly, secure (when HTTPS), samesite=lax
- **Rate limiting**: 5 login attempts per IP per 5 minutes (in-memory)
- **CORS**: restricted to PUBLIC_BASE_URL origin

### Outbound Security
- **Gateway HMAC signing**: destination can verify request authenticity
- **Auth header injection**: credentials never exposed in route creation response (only `auth_header_set: true/false`)

### Static File Security
- Path traversal protection: `file_path.is_relative_to(ui_dist.resolve())`

## Deployment Architecture

### Docker Compose (development/small production)
```
┌─────────────────────┐
│  docker-compose.yml │
│                     │
│  ┌───────────────┐  │
│  │   gateway     │  │
│  │  (port 3000)  │  │
│  │               │  │
│  │  ┌─────────┐  │  │
│  │  │ SQLite  │  │  │
│  │  │ volume  │  │  │
│  │  └─────────┘  │  │
│  └───────────────┘  │
└─────────────────────┘
```

### Kubernetes (production)
```
┌─ EKS Cluster ─────────────────────────────────────────┐
│                                                        │
│  ┌─ namespace: platformbot ─────────────────────────┐  │
│  │                                                   │  │
│  │  Ingress (external-ingress-nginx, TLS)           │  │
│  │       │                                           │  │
│  │       ▼                                           │  │
│  │  Service (ClusterIP :80)                         │  │
│  │       │                                           │  │
│  │       ▼                                           │  │
│  │  Deployment (1 replica)                          │  │
│  │  ┌─────────────────────────┐                     │  │
│  │  │ n8n-webhook-gateway     │                     │  │
│  │  │ CPU: 50m-200m           │                     │  │
│  │  │ Mem: 64Mi-128Mi         │                     │  │
│  │  │ Port: 3000              │                     │  │
│  │  │ Probes: /health         │                     │  │
│  │  │ Secrets: envFrom        │                     │  │
│  │  └─────────────────────────┘                     │  │
│  └───────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

## Limitations

1. **Single-process**: no horizontal scaling (SQLite doesn't support concurrent writers well)
2. **In-memory rate limiting**: resets on process restart, not shared across replicas
3. **No delivery log cleanup**: logs grow indefinitely
4. **Single admin user**: no multi-user or RBAC
5. **No webhook payload persistence**: only response excerpt (1000 chars) stored
6. **Ephemeral SQLite in K8s**: no PersistentVolume configured -- data lost on pod restart
