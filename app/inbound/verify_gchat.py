import logging
import time

import httpx
import jwt
from jwt.exceptions import PyJWTError

from fastapi import Request

from app.config import settings
from app.models import WebhookRoute

logger = logging.getLogger(__name__)

GOOGLE_CERTS_URL = (
    "https://www.googleapis.com/service_accounts/v1/metadata/x509/"
    "chat@system.gserviceaccount.com"
)
CACHE_TTL = 3600

_cached_certs: dict | None = None
_certs_fetched_at: float = 0


async def _get_google_certs() -> dict:
    global _cached_certs, _certs_fetched_at
    if _cached_certs and (time.time() - _certs_fetched_at) < CACHE_TTL:
        return _cached_certs
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(GOOGLE_CERTS_URL)
            resp.raise_for_status()
            _cached_certs = resp.json()
            _certs_fetched_at = time.time()
            return _cached_certs
    except Exception as e:
        logger.error(f"Failed to fetch Google certs: {e}")
        if _cached_certs:
            return _cached_certs
        raise


async def verify_gchat(route: WebhookRoute, request: Request, body: bytes) -> str | None:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return "Missing or invalid Authorization header"

    token = auth_header[7:]
    try:
        certs = await _get_google_certs()
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid or kid not in certs:
            return "Unknown key ID in JWT"

        jwt.decode(
            token,
            certs[kid],
            algorithms=["RS256"],
            audience=settings.public_base_url,
            issuer="chat@system.gserviceaccount.com",
        )
    except PyJWTError as e:
        return f"JWT verification failed: {e}"
    except Exception as e:
        logger.error(f"Google Chat verification error: {e}")
        return "Verification service unavailable"

    return None
