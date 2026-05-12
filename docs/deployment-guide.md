# Deployment Guide

## Prerequisites

- Docker and Docker Compose (for container deployment)
- kubectl and access to EKS cluster (for Kubernetes deployment)
- Python 3.12+ (for local development)

## Docker Compose (Recommended for Small Deployments)

### 1. Setup

```bash
git clone <repo-url> && cd n8n-webhook-gateway
cp .env.example .env
```

Edit `.env` -- **must change these for production**:

```env
SECRET_KEY=<generate-random-64-char-string>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<strong-password>
PUBLIC_BASE_URL=https://your-domain.com
```

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 2. Start

```bash
docker compose up -d
```

### 3. Verify

```bash
curl http://localhost:3000/health
# {"status":"ok","routes":0}
```

Open `http://localhost:3000` in browser, login with admin credentials.

### 4. Persistence

Docker Compose uses a named volume `gateway-data` for the SQLite database. The DATABASE_URL is overridden in compose to `sqlite+aiosqlite:///./data/gateway.db` so the DB lives inside the volume mount.

Data survives container restarts and image upgrades. To backup:

```bash
docker compose exec gateway cp /app/data/gateway.db /app/data/gateway.db.bak
docker cp $(docker compose ps -q gateway):/app/data/gateway.db.bak ./gateway-backup.db
```

### 5. Upgrade

```bash
docker compose pull
docker compose up -d
```

### 6. Logs

```bash
docker compose logs -f gateway
```

## Docker (Standalone)

```bash
docker run -d \
  --name n8n-webhook-gateway \
  -p 3000:3000 \
  -v gateway-data:/app/data \
  -e DATABASE_URL=sqlite+aiosqlite:///./data/gateway.db \
  -e SECRET_KEY=your-secret-key \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=your-password \
  -e PUBLIC_BASE_URL=http://localhost:3000 \
  dinhdobathi/n8n-webhook-gateway:latest
```

## Kubernetes (EKS)

### Namespace

All resources deploy to `platformbot` namespace:

```bash
kubectl create namespace platformbot  # if not exists
```

### 1. Create Secret

```bash
cp k8s/secret.yaml.example k8s/secret.yaml
```

Edit `k8s/secret.yaml` with real values:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: n8n-webhook-gateway-secrets
  namespace: platformbot
type: Opaque
stringData:
  DATABASE_URL: "sqlite+aiosqlite:///./gateway.db"
  SECRET_KEY: "<generate-random-secret>"
  ADMIN_USERNAME: "admin"
  ADMIN_PASSWORD: "<strong-password>"
  PUBLIC_BASE_URL: "https://your-ingress-hostname"
```

**Never commit `k8s/secret.yaml` to git.** The `.gitignore` should exclude it (only `secret.yaml.example` is tracked).

```bash
kubectl apply -f k8s/secret.yaml
```

### 2. Deploy

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

### 3. Verify

```bash
kubectl -n platformbot get pods -l app=n8n-webhook-gateway
kubectl -n platformbot logs -l app=n8n-webhook-gateway
```

### 4. Ingress Configuration

Current ingress uses:
- **Ingress class**: `external-ingress-nginx`
- **Host**: `n8n-webhook-gateway.platformbot.snag.eks.aws.theiconic.com.au`
- **TLS**: enabled with `kubernetes.io/tls-acme: "true"` annotation
- **TLS secret**: `n8n-webhook-gateway-certificate`

To change the hostname, edit `k8s/ingress.yaml`:
```yaml
spec:
  rules:
    - host: your-hostname.example.com
  tls:
    - hosts:
        - your-hostname.example.com
      secretName: your-tls-secret
```

### 5. Resource Limits

Default resource allocation:
```yaml
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 200m
    memory: 128Mi
```

Adjust in `k8s/deployment.yaml` if needed. Current limits are sufficient for low-to-moderate traffic (< 100 req/min).

### 6. Health Probes

Deployment includes both probes hitting `/health`:
- **Liveness**: initial delay 5s, period 30s
- **Readiness**: initial delay 3s, period 10s

### 7. Known K8s Limitations

**SQLite persistence**: current deployment has no PersistentVolume. SQLite DB lives in the container filesystem and is lost on pod restart/reschedule. Options:
- Add a PersistentVolumeClaim (recommended)
- Switch to PostgreSQL for production K8s deployments
- Accept data loss (delivery logs are non-critical)

## Local Development

### Backend

```bash
# Create virtualenv
python3.12 -m venv .venv
source .venv/bin/activate

# Install deps
pip install -r requirements.txt

# Configure
cp .env.example .env

# Run
uvicorn app.main:app --reload --port 3000
```

### Frontend

```bash
cd ui
npm install
npm run dev
```

Vite dev server proxies API calls to `http://localhost:3000`.

### Tests

```bash
pytest          # run all
pytest -v       # verbose
pytest -x       # stop on first failure
```

## Environment Variables Reference

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `PORT` | No | `3000` | Server listen port |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./gateway.db` | SQLAlchemy async URL |
| `SECRET_KEY` | **Yes** (production) | `change-me` | JWT signing -- weak default warns on startup |
| `ADMIN_USERNAME` | No | `admin` | First admin user |
| `ADMIN_PASSWORD` | No | `admin` | First admin password |
| `PUBLIC_BASE_URL` | **Yes** (production) | `http://localhost:3000` | CORS origin + webhook URL generation |
| `FORWARD_TIMEOUT_SECONDS` | No | `30` | Per-attempt HTTP timeout |
| `FORWARD_MAX_RETRIES` | No | `3` | Max forwarding attempts |
| `FORWARD_RETRY_BASE_SECONDS` | No | `1` | Backoff base delay |

## Reverse Proxy (Optional)

If placing behind nginx/Caddy:

```nginx
# nginx example
location / {
    proxy_pass http://localhost:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Set `PUBLIC_BASE_URL` to the external URL (e.g., `https://webhooks.example.com`).

## Monitoring

### Health Check
```bash
curl https://your-domain.com/health
# {"status":"ok","routes":5}
```

### Logs
The application logs to stdout. Key log messages:
- `WARNING: SECRET_KEY is weak or default` -- change your secret key
- `[slug] attempt N got 5xx, retrying` -- forwarding retry
- `[slug] attempt N failed: <error>` -- connection/timeout error

### Delivery Inspection
Use the admin UI or API to inspect delivery attempts:
```bash
curl -b cookies.txt https://your-domain.com/api/webhooks/1/deliveries?limit=10
```
