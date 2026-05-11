from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.forwarding import forward_request, verify_slack_signature
from app.models import DeliveryAttempt, WebhookRoute

router = APIRouter()


@router.api_route("/{slug}/webhook", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def inbound_webhook(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WebhookRoute).where(WebhookRoute.slug == slug, WebhookRoute.enabled == True)  # noqa: E712
    )
    route = result.scalar_one_or_none()
    if route is None:
        return JSONResponse(status_code=404, content={"detail": "Route not found"})

    body = await request.body()

    if route.signing_secret and request.headers.get("x-slack-signature"):
        timestamp = request.headers.get("x-slack-request-timestamp", "")
        signature = request.headers.get("x-slack-signature", "")
        if not verify_slack_signature(route.signing_secret, timestamp, body, signature):
            return JSONResponse(status_code=401, content={"detail": "Invalid signature"})

    # Slack URL verification challenge — after signature check
    if request.method == "POST" and body:
        try:
            import json
            payload = json.loads(body)
            if isinstance(payload, dict) and payload.get("type") == "url_verification":
                return JSONResponse(content={"challenge": payload.get("challenge", "")})
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    headers = dict(request.headers)
    query_string = str(request.url.query) if request.url.query else ""

    fwd = await forward_request(
        destination_url=route.destination_url,
        method=request.method,
        body=body,
        headers=headers,
        query_string=query_string,
        slug=route.slug,
        signing_secret=route.signing_secret,
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
