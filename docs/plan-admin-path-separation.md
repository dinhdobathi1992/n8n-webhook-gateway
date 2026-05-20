# Plan: Separate Public Webhooks from Admin UI

## Goal

- `https://n8n-gateway.theiconic.com.au/` → returns 502 (or generic error page), no login visible
- `https://n8n-gateway.theiconic.com.au/{slug}/webhook` → works as today (public webhook ingress)
- `https://n8n-gateway.theiconic.com.au/health` → health check (for k8s probes)
- `https://n8n-gateway.theiconic.com.au/admin/` → management UI + API (restricted access)
- `/admin` path is NOT accessible from the public internet — only from internal network

## Architecture After Change

```
Internet (via Cloudflare)
  │
  ├─ /{slug}/webhook  → Inbound handler (public, no auth needed beyond source verification)
  ├─ /health          → Health check (public)
  ├─ /                → 502 or "Not Found" (no UI exposed)
  └─ /admin/*         → BLOCKED by ingress annotation (nginx returns 403)

Internal Network (VPN / kubectl port-forward / internal ingress)
  │
  └─ /admin/*         → Management UI + API (login required)
```

## Implementation Steps

### Step 1: Move API under `/admin/api` prefix

**File: `app/api/router.py`**

Change the API router prefix from `/api` to `/admin/api`.

```python
# Before
api_router = APIRouter(prefix="/api")

# After  
api_router = APIRouter(prefix="/admin/api")
```

This moves:
- `/api/auth/login` → `/admin/api/auth/login`
- `/api/webhooks` → `/admin/api/webhooks`
- `/api/webhooks/{id}/channels` → `/admin/api/webhooks/{id}/channels`

### Step 2: Update React UI to use `/admin` base path

**File: `ui/vite.config.ts`**

Set the base path so all assets are served under `/admin/`:

```typescript
export default defineConfig({
  base: '/admin/',
  // ... existing config
})
```

**File: `ui/src/App.tsx`**

Update BrowserRouter to use `/admin` basename:

```tsx
<BrowserRouter basename="/admin">
```

**File: `ui/src/lib/api.ts`**

Update API base URL from `/api` to `/admin/api`:

```typescript
const BASE = '/admin/api';
```

### Step 3: Serve SPA under `/admin` path in FastAPI

**File: `app/main.py`**

Replace the current catch-all SPA serving with `/admin`-prefixed serving:

```python
# Mount static assets under /admin/assets
if ui_dist.exists():
    app.mount("/admin/assets", StaticFiles(directory=ui_dist / "assets"), name="assets")

    @app.get("/admin/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = (ui_dist / full_path).resolve()
        if file_path.is_relative_to(ui_dist.resolve()) and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(ui_dist / "index.html")
```

### Step 4: Return 502 on root path

**File: `app/main.py`**

Add an explicit root route that returns 502 (before the SPA catch-all):

```python
@app.get("/")
async def root():
    return JSONResponse(status_code=502, content={"detail": "Bad Gateway"})
```

This means anyone hitting `https://n8n-gateway.theiconic.com.au/` sees a generic 502, not the login page.

### Step 5: Block `/admin` from public internet via ingress annotations

**File: `k8s-app/ingress.yaml`**

Split into two ingress resources:

1. **Public ingress** (`n8n-gateway.theiconic.com.au`) — only allows webhook paths
2. **Internal ingress** (old `.snag.eks` domain or separate) — allows `/admin`

**Option A: Use nginx snippet to block `/admin` on the Cloudflare ingress:**

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: n8n-webhook-gateway-app
  namespace: platformbot
  annotations:
    kubernetes.io/tls-acme: "true"
    nginx.ingress.kubernetes.io/server-snippet: |
      location /admin {
        deny all;
        return 403;
      }
spec:
  ingressClassName: external-ingress-nginx
  rules:
    - host: n8n-gateway.theiconic.com.au
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: n8n-webhook-gateway-app
                port:
                  number: 80
  tls:
    - hosts:
        - n8n-gateway.theiconic.com.au
      secretName: n8n-gateway-theiconic-certificate
```

**Option B: Use Cloudflare WAF rule to block `/admin`:**

In Cloudflare Dashboard → Security → WAF → Create Rule:
- Rule name: "Block admin path"
- Expression: `(http.request.uri.path contains "/admin")`
- Action: Block

This is simpler and doesn't require ingress changes. Cloudflare blocks it before it even reaches the cluster.

**Option C: Keep `/admin` accessible only via the internal `.snag.eks` domain:**

```yaml
# Public ingress - Cloudflare domain, no admin access
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: n8n-webhook-gateway-public
  namespace: platformbot
  annotations:
    kubernetes.io/tls-acme: "true"
    nginx.ingress.kubernetes.io/server-snippet: |
      location /admin {
        return 403;
      }
spec:
  ingressClassName: external-ingress-nginx
  rules:
    - host: n8n-gateway.theiconic.com.au
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: n8n-webhook-gateway-app
                port:
                  number: 80
  tls:
    - hosts:
        - n8n-gateway.theiconic.com.au
      secretName: n8n-gateway-theiconic-certificate
---
# Internal ingress - old domain, full access (admin + webhooks)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: n8n-webhook-gateway-internal
  namespace: platformbot
  annotations:
    kubernetes.io/tls-acme: "true"
spec:
  ingressClassName: external-ingress-nginx
  rules:
    - host: n8n-webhook-gateway-app.platformbot.snag.eks.aws.theiconic.com.au
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: n8n-webhook-gateway-app
                port:
                  number: 80
  tls:
    - hosts:
        - n8n-webhook-gateway-app.platformbot.snag.eks.aws.theiconic.com.au
      secretName: n8n-webhook-gateway-app-certificate
```

Then access admin via: `https://n8n-webhook-gateway-app.platformbot.snag.eks.aws.theiconic.com.au/admin/`
(This domain resolves to the ELB directly — if it's already behind Zscaler/VPN for your team, it's internal-only.)

## Recommended Approach

**Use Option C (separate ingresses) + Option B (Cloudflare WAF rule) as defense-in-depth:**

1. Nginx server-snippet blocks `/admin` on the Cloudflare domain (infra layer)
2. Cloudflare WAF rule blocks `/admin` (edge layer)  
3. Admin still requires JWT login (app layer)
4. Access admin via the `.snag.eks` domain (reachable only via VPN/internal)

Three layers of protection:
- **Edge**: Cloudflare blocks `/admin` before hitting the cluster
- **Infra**: Nginx returns 403 even if Cloudflare is bypassed
- **App**: JWT auth required even if both are bypassed

## Files Changed Summary

| File | Change |
|------|--------|
| `app/main.py` | Move SPA serving to `/admin`, add 502 root route |
| `app/api/router.py` | Change prefix to `/admin/api` |
| `ui/vite.config.ts` | Set `base: '/admin/'` |
| `ui/src/App.tsx` | Set `basename="/admin"` on BrowserRouter |
| `ui/src/lib/api.ts` | Change API base to `/admin/api` |
| `k8s-app/ingress.yaml` | Split into public + internal, block `/admin` on public |

## Testing Checklist

- [ ] `GET /` → 502
- [ ] `GET /{slug}/webhook` → works (forward or 404 if no route)
- [ ] `GET /health` → 200
- [ ] `GET /admin/` → serves login page (from internal domain)
- [ ] `GET /admin/` via Cloudflare domain → 403
- [ ] `POST /admin/api/auth/login` → works from internal domain
- [ ] `GET /admin/api/webhooks` → works with JWT from internal domain
- [ ] All existing webhook functionality unaffected
- [ ] Cloudflare WAF rule blocks `/admin` requests

## Rollback

If anything breaks:
1. Revert `app/main.py` to serve SPA on `/` again
2. Revert API prefix to `/api`
3. Revert UI base path
4. Apply old single ingress
5. Remove Cloudflare WAF rule
