import hmac

from fastapi import Request

from app.models import WebhookRoute


async def verify_generic(route: WebhookRoute, request: Request, body: bytes) -> str | None:
    if not route.secret_header_name or not route.signing_secret:
        return "Generic route missing secret_header_name or signing_secret"

    header_val = request.headers.get(route.secret_header_name)
    if not header_val:
        return f"Missing required header: {route.secret_header_name}"

    if not hmac.compare_digest(header_val, route.signing_secret):
        return "Invalid secret header value"

    return None
