import hashlib
import hmac as hmac_mod
import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.auth import hash_password
from app.config import settings
from app.db import get_session
from app.forwarding import ForwardResult
from app.models import ChannelRule, User, WebhookRoute


async def seed_data(client: AsyncClient):
    override = client._transport.app.dependency_overrides[get_session]
    async for session in override():
        user = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        route = WebhookRoute(
            slug="test-inbound",
            destination_url="https://n8n.example.com/webhook/abc",
            enabled=True,
            signing_secret="inbound-secret",
            created_by=user.id,
        )
        session.add(route)
        route_signed = WebhookRoute(
            slug="test-signed",
            destination_url="https://n8n.example.com/webhook/def",
            enabled=True,
            signing_secret="test-secret",
            created_by=user.id,
        )
        session.add(route_signed)
        disabled = WebhookRoute(
            slug="test-disabled",
            destination_url="https://n8n.example.com/webhook/ghi",
            enabled=False,
            created_by=user.id,
        )
        session.add(disabled)
        generic = WebhookRoute(
            slug="test-generic",
            destination_url="https://n8n.example.com/webhook/gen",
            enabled=True,
            source_type="generic",
            signing_secret="my-token-123",
            secret_header_name="X-Webhook-Secret",
            created_by=user.id,
        )
        session.add(generic)
        await session.commit()


@pytest.fixture(autouse=True)
async def _seed(client: AsyncClient):
    await seed_data(client)


def _mock_forward_result(**kwargs):
    defaults = {
        "delivery_id": "test-id",
        "status": "success",
        "attempt_count": 1,
        "response_status": 200,
        "response_body_excerpt": '{"ok":true}',
        "error": None,
        "latency_ms": 50,
    }
    defaults.update(kwargs)
    return ForwardResult(**defaults)


@patch("app.inbound.http.forward_request")
async def test_forward_success(mock_fwd: AsyncMock, client: AsyncClient):
    mock_fwd.return_value = _mock_forward_result()
    body = b'{"event":"test"}'
    timestamp = str(int(time.time()))
    sig_base = f"v0:{timestamp}:{body.decode()}"
    sig = "v0=" + hmac_mod.new(b"inbound-secret", sig_base.encode(), hashlib.sha256).hexdigest()
    resp = await client.post(
        "/test-inbound/webhook",
        content=body,
        headers={
            "content-type": "application/json",
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": sig,
        },
    )
    assert resp.status_code == 200
    mock_fwd.assert_called_once()


@patch("app.inbound.http.forward_request")
async def test_unknown_slug_404(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post("/nonexistent/webhook", json={})
    assert resp.status_code == 404
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
async def test_disabled_route_404(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post("/test-disabled/webhook", json={})
    assert resp.status_code == 404
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
async def test_valid_slack_signature(mock_fwd: AsyncMock, client: AsyncClient):
    mock_fwd.return_value = _mock_forward_result()
    body = b'{"event":"test"}'
    timestamp = str(int(time.time()))
    sig_base = f"v0:{timestamp}:{body.decode()}"
    sig = "v0=" + hmac_mod.new(b"test-secret", sig_base.encode(), hashlib.sha256).hexdigest()
    resp = await client.post(
        "/test-signed/webhook",
        content=body,
        headers={
            "content-type": "application/json",
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": sig,
        },
    )
    assert resp.status_code == 200


@patch("app.inbound.http.forward_request")
async def test_invalid_slack_signature_401(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post(
        "/test-signed/webhook",
        content=b"body",
        headers={
            "content-type": "application/json",
            "x-slack-request-timestamp": str(int(time.time())),
            "x-slack-signature": "v0=invalid",
        },
    )
    assert resp.status_code == 401
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
async def test_signed_route_no_slack_headers_rejects(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post("/test-signed/webhook", json={"data": "no-slack-headers"})
    assert resp.status_code == 401
    assert "Missing Slack signature" in resp.json()["detail"]
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
async def test_generic_valid_header(mock_fwd: AsyncMock, client: AsyncClient):
    mock_fwd.return_value = _mock_forward_result()
    resp = await client.post(
        "/test-generic/webhook",
        json={"data": "test"},
        headers={"X-Webhook-Secret": "my-token-123"},
    )
    assert resp.status_code == 200
    mock_fwd.assert_called_once()


@patch("app.inbound.http.forward_request")
async def test_generic_wrong_header_401(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post(
        "/test-generic/webhook",
        json={"data": "test"},
        headers={"X-Webhook-Secret": "wrong-token"},
    )
    assert resp.status_code == 401
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
async def test_generic_missing_header_401(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post("/test-generic/webhook", json={"data": "test"})
    assert resp.status_code == 401
    mock_fwd.assert_not_called()


async def seed_channel_route(client: AsyncClient):
    """Create a slack route with channel rules for testing."""
    override = client._transport.app.dependency_overrides[get_session]
    async for session in override():
        user = User(
            username="channel-test-user",
            password_hash=hash_password("pass"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        route = WebhookRoute(
            slug="test-channel-routing",
            destination_url="https://n8n.example.com/webhook/default",
            enabled=True,
            signing_secret="channel-secret",
            source_type="slack",
            created_by=user.id,
        )
        session.add(route)
        await session.commit()
        await session.refresh(route)

        rule = ChannelRule(
            route_id=route.id,
            channel_id="C0B3WDWKESH",
            destination_url="https://n8n.example.com/webhook/channel-a",
        )
        session.add(rule)
        await session.commit()


def _slack_sig(secret: str, body: bytes) -> tuple[str, str]:
    timestamp = str(int(time.time()))
    sig_base = f"v0:{timestamp}:{body.decode()}"
    sig = "v0=" + hmac_mod.new(secret.encode(), sig_base.encode(), hashlib.sha256).hexdigest()
    return timestamp, sig


@patch("app.inbound.http.forward_request")
async def test_channel_rule_routes_to_matched_destination(mock_fwd: AsyncMock, client: AsyncClient):
    await seed_channel_route(client)
    mock_fwd.return_value = _mock_forward_result()

    body = json.dumps({
        "token": "test",
        "type": "event_callback",
        "event": {
            "type": "app_mention",
            "channel": "C0B3WDWKESH",
            "text": "hello",
        },
    }).encode()
    timestamp, sig = _slack_sig("channel-secret", body)

    resp = await client.post(
        "/test-channel-routing/webhook",
        content=body,
        headers={
            "content-type": "application/json",
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": sig,
        },
    )
    assert resp.status_code == 200
    mock_fwd.assert_called_once()
    call_kwargs = mock_fwd.call_args
    assert call_kwargs.kwargs["destination_url"] == "https://n8n.example.com/webhook/channel-a"


@patch("app.inbound.http.forward_request")
async def test_channel_rule_drops_unmatched_channel(mock_fwd: AsyncMock, client: AsyncClient):
    await seed_channel_route(client)

    body = json.dumps({
        "token": "test",
        "type": "event_callback",
        "event": {
            "type": "app_mention",
            "channel": "C_UNKNOWN_CHANNEL",
            "text": "hello",
        },
    }).encode()
    timestamp, sig = _slack_sig("channel-secret", body)

    resp = await client.post(
        "/test-channel-routing/webhook",
        content=body,
        headers={
            "content-type": "application/json",
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": sig,
        },
    )
    assert resp.status_code == 200
    assert "dropped" in resp.json()["detail"]
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
async def test_channel_rule_drops_no_channel_in_payload(mock_fwd: AsyncMock, client: AsyncClient):
    await seed_channel_route(client)

    body = json.dumps({
        "token": "test",
        "type": "event_callback",
        "event": {
            "type": "app_mention",
            "text": "hello",
        },
    }).encode()
    timestamp, sig = _slack_sig("channel-secret", body)

    resp = await client.post(
        "/test-channel-routing/webhook",
        content=body,
        headers={
            "content-type": "application/json",
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": sig,
        },
    )
    assert resp.status_code == 200
    assert "dropped" in resp.json()["detail"]
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
async def test_route_without_channel_rules_forwards_normally(mock_fwd: AsyncMock, client: AsyncClient):
    """Routes with no channel rules forward everything (backward compat)."""
    mock_fwd.return_value = _mock_forward_result()

    body = json.dumps({
        "token": "test",
        "type": "event_callback",
        "event": {
            "type": "app_mention",
            "channel": "C_ANY_CHANNEL",
            "text": "hello",
        },
    }).encode()
    timestamp, sig = _slack_sig("inbound-secret", body)

    resp = await client.post(
        "/test-inbound/webhook",
        content=body,
        headers={
            "content-type": "application/json",
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": sig,
        },
    )
    assert resp.status_code == 200
    mock_fwd.assert_called_once()
    call_kwargs = mock_fwd.call_args
    assert call_kwargs.kwargs["destination_url"] == "https://n8n.example.com/webhook/abc"
