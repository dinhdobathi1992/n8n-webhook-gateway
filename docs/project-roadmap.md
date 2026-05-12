# Project Roadmap

## Current State

Production-ready single-instance webhook gateway with core features complete:
- Route CRUD with slug-based routing
- Inbound proxy with Slack signature verification
- Outbound auth header injection and HMAC signing
- Retry with exponential backoff
- Delivery logging
- JWT cookie auth with admin UI
- Docker and Kubernetes deployment

## Phase 1: Data Durability & Cleanup

**Priority**: High -- addresses data loss risk in K8s and unbounded log growth.

### PersistentVolume for K8s
- Add PVC to `k8s/deployment.yaml` for SQLite persistence
- Alternatively: support PostgreSQL via DATABASE_URL (SQLAlchemy already abstracts this)

### Delivery Log Retention
- Auto-delete delivery attempts older than N days (configurable env var)
- Background task or lifespan-triggered cleanup on startup
- Prevents unbounded DB growth

### Database Migrations
- Add Alembic for schema migrations
- Current approach (auto-create tables) breaks on schema changes in production

## Phase 2: Observability

**Priority**: Medium -- needed for production monitoring at scale.

### Structured Logging
- JSON log format for log aggregation (ELK, CloudWatch)
- Include route slug, delivery ID, latency in every log line

### Metrics Endpoint
- Prometheus `/metrics` endpoint
- Key metrics: requests per route, delivery success/failure rate, latency percentiles, retry count distribution

### Webhook Replay
- Store full request payload (opt-in per route)
- Re-send failed deliveries from UI or API
- Useful for debugging destination failures

## Phase 3: Multi-Source Verification

**Priority**: Medium -- extend beyond Slack.

### GitHub Webhook Verification
- Verify `X-Hub-Signature-256` header using route signing secret
- Same pattern as Slack but different signature format

### Generic HMAC Verification
- Configurable inbound signature header name and format per route
- Support common patterns: `X-Signature`, `X-Webhook-Signature`

### IP Allowlisting
- Optional source IP restriction per route
- Useful for known webhook sources (Slack IP ranges, GitHub IP ranges)

## Phase 4: Multi-User & RBAC

**Priority**: Low -- only needed if multiple teams share the gateway.

### User Management
- CRUD for users via API
- Password change endpoint
- User list in admin UI

### Role-Based Access
- Roles: admin (full access), operator (view routes + deliveries, no create/delete)
- Route ownership: users can only edit their own routes (admins override)

### API Keys
- Alternative to cookie auth for programmatic access
- Per-user API keys with optional expiry

## Phase 5: Scaling

**Priority**: Low -- only if traffic exceeds single-instance capacity.

### PostgreSQL Support
- Already partially supported via DATABASE_URL
- Needs: connection pooling config, migration from SQLite
- Enables multi-replica deployment

### Redis Rate Limiting
- Move login rate limiting from in-memory to Redis
- Shared state across replicas

### Async Delivery Queue
- Decouple inbound acceptance from forwarding
- Return 202 Accepted immediately, process delivery in background
- Enables better throughput and resilience

## Phase 6: Developer Experience

**Priority**: Low -- nice-to-have improvements.

### OpenAPI Documentation
- FastAPI auto-generates OpenAPI spec at `/docs`
- Currently blocked by SPA catch-all route (serves index.html for /docs)
- Fix: exclude `/docs` and `/openapi.json` from SPA catch-all

### CLI Tool
- Command-line tool for route management without UI
- `gateway routes list`, `gateway routes create --slug my-hook --dest https://...`

### Webhook Testing UI Improvements
- Show request/response headers in delivery detail
- Diff view for comparing delivery attempts
- Filter deliveries by status, date range

## Backlog (Unscheduled)

| Item | Notes |
|------|-------|
| Rate limiting on proxy endpoint | Per-route or per-source-IP limits on `/{slug}/webhook` |
| Webhook transformation | JSONPath/JQ transforms before forwarding |
| Conditional routing | Route to different destinations based on payload content |
| Event deduplication | Detect and skip duplicate events (by source_event_id) |
| Bulk route import/export | JSON/YAML import for route configuration |
| Dark mode UI | CSS variable-based theme toggle |
| Docker Hub CI/CD | GitHub Actions to build and push on tag |
| Health check with DB write test | Current health only reads; add write canary |
| TLS termination at app level | Support `--ssl-keyfile` / `--ssl-certfile` in uvicorn |
