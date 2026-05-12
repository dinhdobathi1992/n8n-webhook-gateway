# Codebase Summary

## Stats

- **Backend**: 1193 lines Python across 22 files
- **Frontend**: 1419 lines TypeScript/CSS across 12 files
- **K8s**: 88 lines YAML across 4 files
- **Tests**: 31 passing (pytest-asyncio)

## Directory Structure

```
n8n-webhook-gateway/
├── app/                        # Backend (FastAPI)
│   ├── __init__.py
│   ├── main.py          (77L)  # App setup, lifespan, static serving
│   ├── config.py        (18L)  # Pydantic settings from env
│   ├── db.py            (13L)  # Async SQLAlchemy engine + session
│   ├── models.py        (67L)  # SQLAlchemy ORM models
│   ├── schemas.py       (88L)  # Pydantic request/response schemas
│   ├── auth.py          (33L)  # Password hashing, JWT encode/decode
│   ├── forwarding.py   (119L)  # HTTP forwarding, retry, HMAC signing
│   ├── api/
│   │   ├── router.py     (8L)  # Router aggregation
│   │   ├── auth.py      (73L)  # Login/logout, rate limiting
│   │   └── webhooks.py (122L)  # Route CRUD, delivery log
│   └── inbound/
│       └── http.py      (77L)  # Public webhook proxy endpoint
├── ui/src/                     # Frontend (React + Vite + TypeScript)
│   ├── App.tsx          (29L)  # Router setup
│   ├── main.tsx         (10L)  # Entry point
│   ├── index.css        (65L)  # Global styles
│   ├── lib/
│   │   └── api.ts       (77L)  # HTTP client wrapper
│   ├── pages/
│   │   ├── Login.tsx   (135L)  # Auth page
│   │   ├── Dashboard.tsx(139L) # Route list
│   │   ├── RouteForm.tsx(290L) # Create/edit route
│   │   └── RouteDetail.tsx(237L) # Route detail + deliveries
│   └── components/
│       ├── RouteTable.tsx(161L) # Route list table
│       ├── DeliveryLog.tsx(109L)# Delivery attempt table
│       ├── TestPanel.tsx(121L) # Send test webhook
│       └── CopyButton.tsx(46L) # Copy-to-clipboard
├── tests/                      # Test suite
│   ├── conftest.py             # Fixtures, test DB setup
│   ├── test_auth.py            # Login, logout, rate limiting
│   ├── test_webhooks.py        # Route CRUD
│   ├── test_forwarding.py      # Forward logic, retry, signing
│   ├── test_inbound.py         # Public proxy endpoint
│   ├── test_health.py          # Health check
│   └── test_schemas.py         # Schema validation
├── k8s/                        # Kubernetes manifests
│   ├── deployment.yaml         # Deployment spec
│   ├── service.yaml            # ClusterIP service
│   ├── ingress.yaml            # Ingress with TLS
│   └── secret.yaml.example     # Secret template
├── Dockerfile                  # Multi-stage: Node (UI build) + Python
├── docker-compose.yml          # Single-service compose
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
└── pytest.ini                  # Pytest config
```

## Module Responsibilities

### `app/main.py`
- FastAPI app creation with lifespan handler
- DB table creation on startup
- Admin user auto-seeding if no users exist
- Weak SECRET_KEY warning
- CORS middleware (restricted to PUBLIC_BASE_URL)
- Router registration (API + inbound)
- Static file serving for React SPA with path traversal protection

### `app/config.py`
- Single `Settings` class using pydantic-settings
- Reads from env vars and `.env` file
- All settings have defaults for local dev

### `app/db.py`
- Async SQLAlchemy engine creation from DATABASE_URL
- Session factory and `get_session` dependency generator

### `app/models.py`
Three ORM models:
- **User**: id, username, password_hash, timestamps
- **WebhookRoute**: slug (unique/indexed), destination_url, enabled, signing_secret, auth_header_name/value, description, created_by FK
- **DeliveryAttempt**: route_id FK, method, status, attempt_count, response_status, response_body_excerpt, error, latency_ms

### `app/schemas.py`
Pydantic models with validation:
- **RouteCreate**: slug validation (regex + reserved words), destination_url must be http/https
- **RouteUpdate**: partial update, same destination_url validation
- **RouteResponse**: computed fields (signing_secret_set, auth_header_set, webhook_url)
- **DeliveryResponse**: flat delivery attempt data

### `app/auth.py`
- `hash_password` / `verify_password` using bcrypt
- `create_access_token` / `decode_access_token` using python-jose HS256
- 24-hour token expiry

### `app/forwarding.py`
- `verify_slack_signature`: HMAC-SHA256 verification of Slack request signatures, 5-min timestamp tolerance
- `sign_gateway_payload`: generates outbound HMAC-SHA256 signature
- `forward_request`: async HTTP forwarding with retry loop, exponential backoff, configurable timeout
- Returns `ForwardResult` dataclass with delivery metadata

### `app/api/auth.py`
- Login endpoint with rate limiting (5 attempts/IP/5min, in-memory dict)
- Cookie-based JWT auth (`gateway_token` httpOnly cookie)
- `get_current_user` dependency for protected routes
- Secure cookie flag based on PUBLIC_BASE_URL scheme

### `app/api/webhooks.py`
- Full CRUD for WebhookRoute (all routes require auth)
- DELETE is soft-delete (sets enabled=false)
- Delivery log endpoint with limit/offset pagination (default 50, max 200)
- Response builder converts ORM model to Pydantic response with computed webhook_url

### `app/inbound/http.py`
- Single catch-all route: `/{slug}/webhook` accepting GET/POST/PUT/PATCH/DELETE
- Looks up enabled route by slug
- Optional Slack signature verification (if route has signing_secret AND request has x-slack-signature)
- Slack URL verification challenge response (after sig check)
- Forwards via `forward_request`, creates DeliveryAttempt record
- Returns destination response to caller

### `ui/src/lib/api.ts`
- Fetch wrapper with credentials: "include" for cookie auth
- Functions: login, logout, getRoutes, createRoute, updateRoute, deleteRoute, getDeliveries, testWebhook
- Base URL from window.location.origin

### Frontend Pages
- **Login**: username/password form, redirects to dashboard on success
- **Dashboard**: route list with enable/disable toggle, create button
- **RouteForm**: create/edit form with all route fields, slug auto-generation
- **RouteDetail**: route info, delivery log table, test panel for sending test requests

## Key Data Flows

### Inbound Webhook Flow
```
External Source -> GET/POST /{slug}/webhook
  -> Lookup enabled route by slug (404 if not found)
  -> [Optional] Verify Slack signature (401 if invalid)
  -> [Optional] Handle Slack URL verification challenge
  -> Forward to destination_url via httpx
    -> Inject gateway headers (route, delivery-id, timestamp)
    -> [Optional] Add gateway HMAC signature
    -> [Optional] Add auth header
    -> Retry on 5xx/timeout (exponential backoff)
  -> Create DeliveryAttempt record
  -> Return destination response to caller
```

### Auth Flow
```
POST /api/auth/login (username, password)
  -> Rate limit check (5/IP/5min)
  -> Verify credentials against DB
  -> Create JWT token (24h expiry)
  -> Set httpOnly cookie
  -> Subsequent requests: cookie -> decode JWT -> load user
```

## Test Coverage Areas

| Test File | Coverage |
|-----------|----------|
| test_auth.py | Login success/failure, rate limiting, logout |
| test_webhooks.py | Route CRUD, slug conflicts, delivery listing |
| test_forwarding.py | Forward success, retry on 5xx, signing |
| test_inbound.py | Proxy endpoint, Slack verification, disabled routes |
| test_health.py | Health endpoint response |
| test_schemas.py | Slug validation, reserved slugs, URL validation |
