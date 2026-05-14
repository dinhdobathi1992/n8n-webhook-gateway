import hashlib
import hmac as hmac_mod
import time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.auth import hash_password
from app.config import settings
from app.db import get_session
from app.forwarding import ForwardResult
from app.models import User, WebhookRoute


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
            source_type="slack",
            enabled=True,
            created_by=user.id,
        )
        session.add(route)

        route_signed = WebhookRoute(
            slug="test-signed",
            destination_url="https://n8n.example.com/webhook/def",
            source_type="slack",
            enabled=True,
            signing_secret="test-secret",
            created_by=user.id,
        )
        session.add(route_signed)

        generic_route = WebhookRoute(
            slug="test-generic",
            destination_url="https://n8n.example.com/webhook/gen",
            source_type="generic",
            enabled=True,
            signing_secret="my-secret-value",
            secret_header_name="X-Webhook-Secret",
            created_by=user.id,
        )
        session.add(generic_route)

        generic_open = WebhookRoute(
            slug="test-generic-open",
            destination_url="https://n8n.example.com/webhook/open",
            source_type="generic",
            enabled=True,
            created_by=user.id,
        )
        session.add(generic_open)

        gchat_route = WebhookRoute(
            slug="test-gchat",
            destination_url="https://n8n.example.com/webhook/gchat",
            source_type="gchat",
            enabled=True,
            signing_secret="https://gateway.example.com/test-gchat/webhook",
            created_by=user.id,
        )
        session.add(gchat_route)

        disabled = WebhookRoute(
            slug="test-disabled",
            destination_url="https://n8n.example.com/webhook/ghi",
            source_type="slack",
            enabled=False,
            created_by=user.id,
        )
        session.add(disabled)
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


# ── Slack tests ──────────────────────────────────────────────────────


@patch("app.inbound.http.forward_request")
async def test_slack_forward_missing_signature_401(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post("/test-signed/webhook", json={"event": "test"})
    assert resp.status_code == 401
    assert "Missing Slack signature" in resp.json()["detail"]
    mock_fwd.assert_not_called()


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
async def test_slack_no_signing_secret_500(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post(
        "/test-inbound/webhook",
        content=b"body",
        headers={
            "content-type": "application/json",
            "x-slack-request-timestamp": str(int(time.time())),
            "x-slack-signature": "v0=something",
        },
    )
    assert resp.status_code == 500
    assert "misconfigured" in resp.json()["detail"]
    mock_fwd.assert_not_called()


# ── Generic tests ────────────────────────────────────────────────────


@patch("app.inbound.http.forward_request")
async def test_generic_valid_secret(mock_fwd: AsyncMock, client: AsyncClient):
    mock_fwd.return_value = _mock_forward_result()
    resp = await client.post(
        "/test-generic/webhook",
        content=b'{"data":"test"}',
        headers={
            "content-type": "application/json",
            "x-webhook-secret": "my-secret-value",
        },
    )
    assert resp.status_code == 200
    mock_fwd.assert_called_once()


@patch("app.inbound.http.forward_request")
async def test_generic_invalid_secret_401(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post(
        "/test-generic/webhook",
        content=b'{"data":"test"}',
        headers={
            "content-type": "application/json",
            "x-webhook-secret": "wrong-value",
        },
    )
    assert resp.status_code == 401
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
async def test_generic_missing_header_401(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post(
        "/test-generic/webhook",
        content=b'{"data":"test"}',
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 401
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
async def test_generic_open_route_passes(mock_fwd: AsyncMock, client: AsyncClient):
    mock_fwd.return_value = _mock_forward_result()
    resp = await client.post(
        "/test-generic-open/webhook",
        content=b'{"data":"test"}',
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 200
    mock_fwd.assert_called_once()


@patch("app.inbound.http.forward_request")
async def test_generic_bearer_format(mock_fwd: AsyncMock, client: AsyncClient):
    mock_fwd.return_value = _mock_forward_result()
    resp = await client.post(
        "/test-generic/webhook",
        content=b'{"data":"test"}',
        headers={
            "content-type": "application/json",
            "x-webhook-secret": "Bearer my-secret-value",
        },
    )
    assert resp.status_code == 200


# ── Google Chat tests ────────────────────────────────────────────────


@patch("app.inbound.http.forward_request")
async def test_gchat_missing_bearer_401(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post(
        "/test-gchat/webhook",
        content=b'{"data":"test"}',
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 401
    assert "Missing Bearer token" in resp.json()["detail"]
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
@patch("app.inbound.http.verify_gchat_token", return_value=False)
async def test_gchat_invalid_token_401(mock_verify: AsyncMock, mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post(
        "/test-gchat/webhook",
        content=b'{"data":"test"}',
        headers={
            "content-type": "application/json",
            "authorization": "Bearer fake-jwt-token",
        },
    )
    assert resp.status_code == 401
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
@patch("app.inbound.http.verify_gchat_token", return_value=True)
async def test_gchat_valid_token(mock_verify: AsyncMock, mock_fwd: AsyncMock, client: AsyncClient):
    mock_fwd.return_value = _mock_forward_result()
    resp = await client.post(
        "/test-gchat/webhook",
        content=b'{"data":"test"}',
        headers={
            "content-type": "application/json",
            "authorization": "Bearer valid-jwt-token",
        },
    )
    assert resp.status_code == 200
    mock_fwd.assert_called_once()
