# Cloudflared POC — n8n on Cactus EKS

Expose n8n webhooks publicly via Cloudflare Tunnel at `n8n-cactus.theiconic.tech`.

## Traffic Flow

```
Internet (Slack / GChat)
        │
        ▼
n8n-cactus.theiconic.tech
        │  Cloudflare CDN + WAF + TLS
        ▼
Cloudflare Edge
        │  Outbound QUIC/H2 tunnel (no inbound ports)
        ▼
cloudflared pod (cactus cluster, namespace: n8n)
        │  Cluster-internal
        ▼
n8n-test.n8n.svc.cluster.local:5678
```

## Prerequisites

- `cloudflared` CLI installed locally: `brew install cloudflared`
- `theiconic.tech` domain managed by Cloudflare DNS
- `kubectl` context switched to **cactus** cluster
- n8n already running in `n8n` namespace on cactus

## Step 1 — Verify n8n service name on cactus

```bash
kubectl get svc -n n8n
```

Confirm the service name and port. The manifests assume `n8n-test` on port `5678`.
If different, update `configmap.yaml` accordingly.

## Step 2 — Create Cloudflare Tunnel (local CLI, one-time)

```bash
# Authenticate with Cloudflare (opens browser)
cloudflared tunnel login

# Create the tunnel
cloudflared tunnel create n8n-cactus
# Note the Tunnel ID from the output

# Route DNS
cloudflared tunnel route dns n8n-cactus n8n-cactus.theiconic.tech

# Get the token for Kubernetes
cloudflared tunnel token n8n-cactus
# Copy the base64 token string
```

## Step 3 — Update manifests with real values

1. **configmap.yaml** — Replace `<YOUR_TUNNEL_ID>` with the tunnel ID from step 2
2. **secret.yaml** — Replace `REPLACE_ME` with the token (or use kubectl, see below)

## Step 4 — Deploy to cactus

```bash
# Switch to cactus context
# kubectl config use-context <cactus-context>

# Create secret via kubectl (preferred over committing secret.yaml)
kubectl create secret generic cloudflared-secret \
  --namespace=n8n \
  --from-literal=token="<YOUR_TUNNEL_TOKEN>"

# Apply manifests
kubectl apply -f cloudflared-poc/k8s/configmap.yaml
kubectl apply -f cloudflared-poc/k8s/deployment.yaml
kubectl apply -f cloudflared-poc/k8s/pdb.yaml

# Verify pods running
kubectl get pods -n n8n -l app=cloudflared

# Check logs for "Registered tunnel connection"
kubectl logs -n n8n -l app=cloudflared --tail=50 -f
```

## Step 5 — Test

```bash
# Should reach n8n
curl -X POST https://n8n-cactus.theiconic.tech/webhook-test/your-webhook-id \
  -H "Content-Type: application/json" \
  -d '{"source": "test", "message": "hello from cloudflared"}'

# Should return 404 (catch-all blocks non-webhook paths)
curl -i https://n8n-cactus.theiconic.tech/
curl -i https://n8n-cactus.theiconic.tech/api/v1
```

## Step 6 — Zscaler check

If cloudflared pods can't establish outbound connections, Zscaler may be intercepting TLS.
Check pod logs for certificate errors. If present, you'll need to mount the Zscaler CA
into the cloudflared container (similar to how the gateway app Dockerfile handles it).

## Cleanup (when done with POC)

```bash
kubectl delete -f cloudflared-poc/k8s/
kubectl delete secret cloudflared-secret -n n8n
cloudflared tunnel delete n8n-cactus
```
