import json
import time
from collections import defaultdict

from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.forwarding import forward_request
from app.inbound.verify_gchat import verify_gchat
from app.inbound.verify_generic import verify_generic
from app.inbound.verify_slack import verify_slack
from app.models import DeliveryAttempt, WebhookRoute
from app.config import settings
from app.security import get_client_ip

router = APIRouter()
_webhook_attempts: dict[str, list[float]] = defaultdict(list)

VERIFIERS = {
    "slack": verify_slack,
    "gchat": verify_gchat,
    "generic": verify_generic,
}


def clear_webhook_rate_limits():
    _webhook_attempts.clear()


def _rate_limited(route_key: str) -> bool:
    if settings.webhook_rate_limit_per_min <= 0:
        return False
    now = time.time()
    attempts = _webhook_attempts[route_key]
    attempts[:] = [t for t in attempts if now - t < 60]
    if len(attempts) >= settings.webhook_rate_limit_per_min:
        return True
    attempts.append(now)
    return False


async def _read_body_limited(request: Request) -> bytes | JSONResponse:
    max_bytes = settings.webhook_max_body_bytes
    if max_bytes <= 0:
        return await request.body()

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                return JSONResponse(status_code=413, content={"detail": "Payload too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})

    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > max_bytes:
            return JSONResponse(status_code=413, content={"detail": "Payload too large"})
        chunks.append(chunk)
    return b"".join(chunks)


def _extract_channel_id(body: bytes) -> str | None:
    try:
        payload = json.loads(body)
        if isinstance(payload, dict):
            event = payload.get("event")
            if isinstance(event, dict):
                return event.get("channel")
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return None


@router.api_route("/{slug}/webhook", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def inbound_webhook(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WebhookRoute)
        .options(selectinload(WebhookRoute.channel_rules))
        .where(WebhookRoute.slug == slug, WebhookRoute.enabled == True)  # noqa: E712
    )
    route = result.scalar_one_or_none()
    if route is None:
        return JSONResponse(status_code=404, content={"detail": "Route not found"})

    rate_key = f"{route.slug}:{get_client_ip(request)}"
    if _rate_limited(rate_key):
        return JSONResponse(status_code=429, content={"detail": "Too many webhook requests"})

    body_or_response = await _read_body_limited(request)
    if isinstance(body_or_response, JSONResponse):
        return body_or_response
    body = body_or_response

    verifier = VERIFIERS.get(route.source_type)
    if verifier:
        error = await verifier(route, request, body)
        if error:
            return JSONResponse(status_code=401, content={"detail": error})

    if route.source_type == "slack" and request.method == "POST" and body:
        try:
            payload = json.loads(body)
            if isinstance(payload, dict) and payload.get("type") == "url_verification":
                return JSONResponse(content={"challenge": payload.get("challenge", "")})
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # Channel-based routing: if route has channel rules, require a match
    destination_url = route.destination_url
    if route.channel_rules:
        channel_id = _extract_channel_id(body)
        if channel_id is None:
            return JSONResponse(
                status_code=200,
                content={"detail": "No channel in payload, dropped"},
            )
        matched_rule = next(
            (cr for cr in route.channel_rules if cr.channel_id == channel_id),
            None,
        )
        if matched_rule is None:
            return JSONResponse(
                status_code=200,
                content={"detail": f"No rule for channel {channel_id}, dropped"},
            )
        destination_url = matched_rule.destination_url

    headers = dict(request.headers)
    query_string = str(request.url.query) if request.url.query else ""

    fwd = await forward_request(
        destination_url=destination_url,
        method=request.method,
        body=body,
        headers=headers,
        query_string=query_string,
        slug=route.slug,
        signing_secret=route.signing_secret,
        auth_header_name=route.auth_header_name,
        auth_header_value=route.auth_header_value,
    )

    delivery = DeliveryAttempt(
        route_id=route.id,
        source_event_id=request.headers.get("x-slack-request-timestamp"),
        method=request.method,
        status=fwd.status,
        attempt_count=fwd.attempt_count,
        response_status=fwd.response_status,
        response_body_excerpt=fwd.response_body_excerpt,
        error=fwd.error,
        latency_ms=fwd.latency_ms,
    )
    session.add(delivery)
    await session.commit()

    return Response(
        content=fwd.response_body_excerpt or "",
        status_code=fwd.response_status or 502,
        media_type="application/json",
    )
