from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.forwarding import forward_request, verify_gchat_token, verify_generic_secret, verify_slack_signature
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
    source_type = route.source_type or "slack"

    if source_type == "slack":
        slack_sig = request.headers.get("x-slack-signature")
        timestamp = request.headers.get("x-slack-request-timestamp", "")
        if not slack_sig:
            return JSONResponse(status_code=401, content={"detail": "Missing Slack signature"})
        if not route.signing_secret:
            return JSONResponse(status_code=500, content={"detail": "Route misconfigured: no signing_secret"})
        if not verify_slack_signature(route.signing_secret, timestamp, body, slack_sig):
            return JSONResponse(status_code=401, content={"detail": "Invalid Slack signature"})

    elif source_type == "gchat":
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing Bearer token"})
        token = auth_header.removeprefix("Bearer ")
        audience = route.signing_secret or str(request.url)
        if not verify_gchat_token(audience, token):
            return JSONResponse(status_code=401, content={"detail": "Invalid Google Chat token"})

    elif source_type == "generic":
        if route.signing_secret:
            header_name = (route.secret_header_name or "Authorization").lower()
            incoming_value = request.headers.get(header_name, "")
            if not verify_generic_secret(route.signing_secret, incoming_value):
                return JSONResponse(status_code=401, content={"detail": "Invalid secret"})

    if source_type == "slack" and request.method == "POST" and body:
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
