import pytest
from pydantic import ValidationError

from app.schemas import RouteCreate, SourceType


def test_valid_slug():
    r = RouteCreate(slug="my-route_1", destination_url="https://example.com/hook", signing_secret="test-secret")
    assert r.slug == "my-route_1"


def test_slug_invalid_chars():
    with pytest.raises(ValidationError, match="must match"):
        RouteCreate(slug="bad slug!", destination_url="https://example.com/hook", signing_secret="s")


def test_slug_reserved():
    with pytest.raises(ValidationError, match="reserved"):
        RouteCreate(slug="api", destination_url="https://example.com/hook", signing_secret="s")


def test_slug_too_long():
    with pytest.raises(ValidationError, match="must match"):
        RouteCreate(slug="a" * 65, destination_url="https://example.com/hook", signing_secret="s")


def test_destination_url_must_be_http():
    with pytest.raises(ValidationError, match="must start with"):
        RouteCreate(slug="ok", destination_url="ftp://bad.com", signing_secret="s")


def test_destination_url_https():
    r = RouteCreate(slug="ok", destination_url="https://good.com/webhook", signing_secret="test")
    assert r.destination_url == "https://good.com/webhook"


def test_slack_requires_signing_secret():
    with pytest.raises(ValidationError, match="signing_secret is required"):
        RouteCreate(slug="ok", destination_url="https://example.com/hook", source_type=SourceType.slack)


def test_gchat_requires_signing_secret():
    with pytest.raises(ValidationError, match="signing_secret.*required"):
        RouteCreate(slug="ok", destination_url="https://example.com/hook", source_type=SourceType.gchat)


def test_generic_no_secret_ok():
    r = RouteCreate(slug="ok", destination_url="https://example.com/hook", source_type=SourceType.generic)
    assert r.source_type == SourceType.generic
    assert r.signing_secret is None


def test_generic_with_secret_and_header():
    r = RouteCreate(
        slug="ok",
        destination_url="https://example.com/hook",
        source_type=SourceType.generic,
        signing_secret="my-secret",
        secret_header_name="X-Webhook-Secret",
    )
    assert r.secret_header_name == "X-Webhook-Secret"


def test_default_source_type_is_slack():
    r = RouteCreate(slug="ok", destination_url="https://example.com/hook", signing_secret="test")
    assert r.source_type == SourceType.slack
