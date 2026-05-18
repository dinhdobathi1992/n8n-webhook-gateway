import hashlib
import hmac as hmac_mod
import time

import pytest

from app.forwarding import ForwardResult, forward_request, sign_gateway_payload, verify_slack_signature


def test_verify_slack_signature_valid():
    secret = "my-secret"
    body = b'{"event":"test"}'
    timestamp = str(int(time.time()))
    sig_base = f"v0:{timestamp}:{body.decode()}"
    sig = "v0=" + hmac_mod.new(secret.encode(), sig_base.encode(), hashlib.sha256).hexdigest()
    assert verify_slack_signature(secret, timestamp, body, sig) is True


def test_verify_slack_signature_invalid():
    assert verify_slack_signature("secret", str(int(time.time())), b"body", "v0=bad") is False


def test_verify_slack_signature_expired():
    secret = "my-secret"
    body = b"body"
    old_ts = str(int(time.time()) - 600)
    sig_base = f"v0:{old_ts}:{body.decode()}"
    sig = "v0=" + hmac_mod.new(secret.encode(), sig_base.encode(), hashlib.sha256).hexdigest()
    assert verify_slack_signature(secret, old_ts, body, sig) is False


def test_sign_gateway_payload():
    sig = sign_gateway_payload("secret", "12345", b"hello")
    assert sig.startswith("sha256=")
    expected = hmac_mod.new("secret".encode(), b"12345.hello", hashlib.sha256).hexdigest()
    assert sig == f"sha256={expected}"


def test_forward_result_fields():
    r = ForwardResult(
        delivery_id="abc",
        status="success",
        attempt_count=1,
        response_status=200,
        response_body_excerpt="ok",
        error=None,
        latency_ms=50,
    )
    assert r.status == "success"
    assert r.delivery_id == "abc"


async def test_forward_request_blocks_private_destination():
    result = await forward_request(
        destination_url="http://127.0.0.1:9/internal",
        method="POST",
        body=b"{}",
        headers={"content-type": "application/json"},
        query_string="",
        slug="blocked",
    )
    assert result.status == "failed"
    assert result.attempt_count == 0
    assert "blocked private/internal" in (result.error or "")
