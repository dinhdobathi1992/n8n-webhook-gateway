import hashlib
import hmac
import logging
import time
import uuid
import asyncio
from dataclasses import dataclass

import httpx

from app.config import settings
from app.url_security import assert_destination_allowed

logger = logging.getLogger(__name__)


@dataclass
class ForwardResult:
    delivery_id: str
    status: str
    attempt_count: int
    response_status: int | None
    response_body_excerpt: str | None
    error: str | None
    latency_ms: int


def verify_slack_signature(signing_secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        return False
    if abs(time.time() - ts) > 300:
        return False
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected = "v0=" + hmac.new(
        signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def sign_gateway_payload(signing_secret: str, timestamp: str, body: bytes) -> str:
    sig_input = f"{timestamp}.{body.decode('utf-8')}"
    return "sha256=" + hmac.new(
        signing_secret.encode(), sig_input.encode(), hashlib.sha256
    ).hexdigest()


async def forward_request(
    destination_url: str,
    method: str,
    body: bytes,
    headers: dict[str, str],
    query_string: str,
    slug: str,
    signing_secret: str | None = None,
    auth_header_name: str | None = None,
    auth_header_value: str | None = None,
) -> ForwardResult:
    delivery_id = str(uuid.uuid4())
    timestamp = str(int(time.time()))

    forward_headers = {
        "content-type": headers.get("content-type", "application/json"),
        "X-Gateway-Route": slug,
        "X-Gateway-Delivery-Id": delivery_id,
        "X-Gateway-Timestamp": timestamp,
    }

    if signing_secret:
        forward_headers["X-Gateway-Signature"] = sign_gateway_payload(signing_secret, timestamp, body)

    if auth_header_name and auth_header_value:
        forward_headers[auth_header_name] = auth_header_value

    url = destination_url
    if query_string:
        url = f"{destination_url}?{query_string}"

    try:
        await asyncio.to_thread(assert_destination_allowed, url)
    except ValueError as exc:
        return ForwardResult(
            delivery_id=delivery_id,
            status="failed",
            attempt_count=0,
            response_status=None,
            response_body_excerpt=None,
            error=str(exc),
            latency_ms=0,
        )

    attempt_count = 0
    last_error: str | None = None
    last_status: int | None = None
    last_body: str | None = None
    start_ms = int(time.time() * 1000)

    async with httpx.AsyncClient(timeout=settings.forward_timeout_seconds) as client:
        for attempt in range(1, settings.forward_max_retries + 1):
            attempt_count = attempt
            try:
                resp = await client.request(method, url, content=body, headers=forward_headers)
                last_status = resp.status_code
                last_body = resp.text[:1000]
                last_error = None

                if resp.status_code < 500:
                    break

                logger.warning(f"[{slug}] attempt {attempt} got {resp.status_code}, retrying")

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_error = str(exc)
                last_status = None
                last_body = None
                logger.warning(f"[{slug}] attempt {attempt} failed: {exc}")

            if attempt < settings.forward_max_retries:
                await asyncio.sleep(settings.forward_retry_base_seconds * (2 ** (attempt - 1)))

    elapsed = int(time.time() * 1000) - start_ms
    status = "success" if last_status and last_status < 400 else "failed"

    return ForwardResult(
        delivery_id=delivery_id,
        status=status,
        attempt_count=attempt_count,
        response_status=last_status,
        response_body_excerpt=last_body,
        error=last_error,
        latency_ms=elapsed,
    )
