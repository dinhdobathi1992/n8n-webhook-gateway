# Security Fixes Plan

> Findings from security review on 2026-05-18. Prioritised by severity and effort.

## Implementation Status

Implemented on 2026-05-18:

- Startup now fails closed on weak production secrets unless `ALLOW_WEAK_SECRETS=true`.
- JWT signing and field encryption are separated with `ENCRYPTION_KEY`; legacy decrypt fallback is supported.
- Destination URL validation blocks private/internal IP literals, and forwarding performs DNS/IP checks before egress.
- Inbound webhooks now enforce per-route/client rate limits and request body size limits.
- Login rate limiting uses a proxy-aware client IP helper.
- JWTs now include and validate issuer/audience claims.
- Session cookies can be forced `Secure` in production with `FORCE_HTTPS_COOKIES=true`.
- `python-jose` was replaced with `PyJWT[crypto]`.
- Python dependency specifiers are pinned.
- Docker/Kubernetes runtime hardening was added for non-root execution and dropped capabilities.
- Security headers are added to HTTP responses.

Validation run:

- `pytest tests/ -q` -> 68 passed
- `npm run build` -> passed
- `pipx run pip-audit -r requirements.txt` -> no known vulnerabilities
- `pipx run bandit -r app scripts -q` -> no findings
- `npm audit --json` -> no vulnerabilities

---

## Critical

### 1. Separate JWT Signing Key from Encryption Key

**Problem:** `SECRET_KEY` is used for both JWT signing (`app/auth.py:22`) and Fernet field encryption (`app/crypto.py:8`). Leaking one compromises both authentication and encrypted data (signing_secret, auth_header_value).

**Files to change:**
- `app/config.py` — add `encryption_key: str` setting
- `app/crypto.py` — use `settings.encryption_key` instead of `settings.secret_key`
- `app/auth.py` — keep using `settings.secret_key` for JWT only
- `k8s-app/deployment.yaml` — add `ENCRYPTION_KEY` to secret ref

**Steps:**
- [ ] Add `encryption_key` to `Settings` class with no default (required)
- [ ] Update `app/crypto.py` to derive Fernet key from `settings.encryption_key`
- [ ] Add `ENCRYPTION_KEY` to Kubernetes secret
- [ ] Re-encrypt existing DB fields with new key (migration script)
- [ ] Update tests to set both keys

**Backward compatibility:** Existing encrypted data uses current SECRET_KEY. Need a one-time re-encryption migration or keep SECRET_KEY as fallback during transition.

---

### 2. Refuse to Start with Weak/Default Credentials

**Problem:** App starts with `admin/admin` and `secret_key=change-me` (only logs a warning). Production could accidentally run with defaults.

**Files to change:**
- `app/main.py` — change warning to hard fail in lifespan

**Steps:**
- [ ] In `lifespan()`, raise `SystemExit` if `SECRET_KEY` is in `WEAK_SECRETS`
- [ ] Also check `ADMIN_PASSWORD` is not `admin` or empty
- [ ] Allow override with `ALLOW_WEAK_SECRETS=true` for local dev only
- [ ] Update tests to set proper secrets

---

## High

### 3. SSRF Protection on Destination URLs

**Problem:** Users can set `destination_url` to internal/private IPs (AWS metadata `169.254.169.254`, localhost, k8s services). The gateway then makes HTTP requests to those targets.

**Files to change:**
- `app/schemas.py` — add URL validation that blocks private ranges
- `app/forwarding.py` — add DNS resolution check before connecting

**Steps:**
- [ ] Create `app/url_validator.py` with a function to reject private IPs
- [ ] Block: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.0.0/16`, `fd00::/8`
- [ ] Add validation in `RouteCreate` schema's `destination_url` field validator
- [ ] Also validate in `ChannelRuleCreate` schema
- [ ] Add DNS resolution check in `forward_request` (resolve hostname, check IP before connecting)
- [ ] Allow override via `ALLOWED_INTERNAL_HOSTS` env var for legitimate internal destinations (e.g., n8n's internal URL)
- [ ] Add tests for blocked and allowed URLs

**Note:** Since n8n IS an internal service, we need an allowlist. Suggested approach: allowlist specific hostnames/patterns (e.g., `*.n8n.cactus.eks.aws.theiconic.com.au`).

---

### 4. Rate Limiting on Inbound Webhook Endpoint

**Problem:** `/{slug}/webhook` has no rate limiting. An attacker can flood it, causing amplified outbound requests (with retries) and DB growth.

**Files to change:**
- `app/inbound/http.py` — add rate limiting middleware or per-route check

**Steps:**
- [ ] Add in-memory sliding window rate limiter (similar to login rate limiter)
- [ ] Limit per slug: 200 requests/minute (configurable via `WEBHOOK_RATE_LIMIT_PER_MIN`)
- [ ] Return `429 Too Many Requests` when exceeded
- [ ] Log rate-limited requests
- [ ] Add `WEBHOOK_RATE_LIMIT_PER_MIN` to config.py
- [ ] Add tests

---

### 5. Fix Client IP Detection Behind Proxy

**Problem:** Rate limiter uses `request.client.host` which behind ingress/proxy is always the proxy IP.

**Files to change:**
- `app/api/auth.py` — extract real IP from `X-Forwarded-For`
- `app/inbound/http.py` — same for webhook rate limiter

**Steps:**
- [ ] Create helper `get_client_ip(request)` that reads `X-Forwarded-For` header (first IP)
- [ ] Use in login rate limiter and webhook rate limiter
- [ ] Add `TRUSTED_PROXY_DEPTH` config (default 1) to prevent spoofing

---

## Medium

### 6. Add Request Body Size Limit

**Problem:** No limit on inbound webhook body size. Large payloads consume memory and get forwarded.

**Files to change:**
- `app/inbound/http.py` — check content-length before reading body

**Steps:**
- [ ] Add `WEBHOOK_MAX_BODY_BYTES` to config (default: 1MB = 1_048_576)
- [ ] Before `request.body()`, check `content-length` header
- [ ] If no header, read with a streaming limit
- [ ] Return `413 Payload Too Large` if exceeded
- [ ] Add test

---

### 7. Add JWT Issuer/Audience Claims

**Problem:** JWT tokens have no `iss`/`aud` claims. Token confusion possible if secret is shared.

**Files to change:**
- `app/auth.py` — add claims on encode, validate on decode

**Steps:**
- [ ] Add `iss: "n8n-webhook-gateway"` and `aud: "n8n-webhook-gateway"` to `create_access_token`
- [ ] Validate both in `decode_access_token`
- [ ] Existing tokens will fail validation — users will need to re-login (acceptable)

---

### 8. Migrate from python-jose to PyJWT

**Problem:** `python-jose` is unmaintained and has known vulnerabilities.

**Files to change:**
- `requirements.txt` — replace `python-jose[cryptography]` with `PyJWT[crypto]`
- `app/auth.py` — update import and API calls
- `app/inbound/verify_gchat.py` — update JWT decode for Google Chat verification

**Steps:**
- [ ] Replace `from jose import jwt, JWTError` with `import jwt` and `from jwt.exceptions import PyJWTError`
- [ ] Update `jwt.encode()` and `jwt.decode()` calls (mostly compatible API)
- [ ] For GChat: `jwt.decode(token, key, algorithms=["RS256"], audience=..., issuer=...)`
- [ ] Update requirements.txt
- [ ] Run tests

---

### 9. Pin Dependencies

**Problem:** All deps use `>=` specifiers. Builds are non-reproducible, supply chain risk.

**Files to change:**
- `requirements.txt` — pin exact versions

**Steps:**
- [ ] Run `pip freeze` in venv to get current versions
- [ ] Pin all deps to exact versions (e.g., `fastapi==0.115.0`)
- [ ] Add `requirements-dev.txt` for test deps
- [ ] Consider adding a `pip-compile` workflow

---

### 10. Secure Cookie Flag Always On in Production

**Problem:** `secure` flag is based on `request.url.scheme` which may be `http` behind proxy.

**Files to change:**
- `app/api/auth.py:57-65`

**Steps:**
- [ ] Add `FORCE_HTTPS_COOKIES` config (default: `true`)
- [ ] Always set `secure=True` when `FORCE_HTTPS_COOKIES` is true, regardless of detected scheme
- [ ] Set to `false` only for local dev

---

## Low

### 11. Run Container as Non-Root

**Files to change:**
- `Dockerfile`

**Steps:**
- [ ] Add after `COPY` steps:
  ```dockerfile
  RUN useradd -r -s /bin/false appuser && chown -R appuser:appuser /app
  USER appuser
  ```
- [ ] Ensure `/data` volume mount is writable by appuser (init container runs as root for migration, main container as appuser)
- [ ] Add `securityContext` to k8s deployment:
  ```yaml
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
  ```

---

### 12. Remove Zscaler Cert from Production Image

**Files to change:**
- `Dockerfile`

**Steps:**
- [ ] Move Zscaler cert to build stages only (Node + pip install)
- [ ] Don't include in final runtime layer
- [ ] Or: only `COPY` and `update-ca-certificates` during `RUN pip install`, then remove after

---

### 13. Add Security Headers Middleware

**Files to change:**
- `app/main.py` — add middleware

**Steps:**
- [ ] Add a middleware that sets:
  ```
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  Referrer-Policy: strict-origin-when-cross-origin
  ```
- [ ] Apply to all responses

---

## Implementation Order

| Phase | Items | Effort |
|-------|-------|--------|
| **Phase 1** (immediate) | #2 refuse weak defaults, #5 client IP fix, #6 body size limit | ~1 hour |
| **Phase 2** (this week) | #1 separate keys, #4 webhook rate limit, #7 JWT claims | ~2 hours |
| **Phase 3** (next sprint) | #3 SSRF protection, #8 migrate python-jose, #9 pin deps | ~3 hours |
| **Phase 4** (hardening) | #10 secure cookies, #11 non-root, #12 zscaler cert, #13 security headers | ~1 hour |

---

*Total estimated effort: ~7 hours across 4 phases*
