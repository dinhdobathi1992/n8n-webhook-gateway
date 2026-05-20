from fastapi import Request

from app.forwarding import verify_slack_signature
from app.models import WebhookRoute


async def verify_slack(route: WebhookRoute, request: Request, body: bytes) -> str | None:
    if not route.signing_secret:
        return "Signing secret not configured"

    slack_sig = request.headers.get("x-slack-signature")
    timestamp = request.headers.get("x-slack-request-timestamp", "")

    if not slack_sig:
        return "Missing signature"

    if not verify_slack_signature(route.signing_secret, timestamp, body, slack_sig):
        return "Invalid signature"

    return None
