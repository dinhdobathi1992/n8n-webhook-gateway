import pytest
from pydantic import ValidationError

from app.schemas import RouteCreate


def test_valid_slug():
    r = RouteCreate(slug="my-route_1", destination_url="https://example.com/hook", signing_secret="test-secret")
    assert r.slug == "my-route_1"


def test_slug_invalid_chars():
    with pytest.raises(ValidationError, match="must match"):
        RouteCreate(slug="bad slug!", destination_url="https://example.com/hook")


def test_slug_reserved():
    with pytest.raises(ValidationError, match="reserved"):
        RouteCreate(slug="api", destination_url="https://example.com/hook")


def test_slug_too_long():
    with pytest.raises(ValidationError, match="must match"):
        RouteCreate(slug="a" * 65, destination_url="https://example.com/hook")


def test_destination_url_must_be_http():
    with pytest.raises(ValidationError, match="must start with"):
        RouteCreate(slug="ok", destination_url="ftp://bad.com")


def test_destination_url_https():
    r = RouteCreate(slug="ok", destination_url="https://good.com/webhook", signing_secret="test")
    assert r.destination_url == "https://good.com/webhook"


def test_signing_secret_required():
    with pytest.raises(ValidationError, match="signing_secret is required"):
        RouteCreate(slug="ok", destination_url="https://example.com/hook")


def test_gchat_no_signing_secret_ok():
    r = RouteCreate(slug="gchat-test", destination_url="https://example.com/hook", source_type="gchat")
    assert r.signing_secret is None


def test_generic_requires_signing_secret():
    with pytest.raises(ValidationError, match="signing_secret is required for generic"):
        RouteCreate(slug="gen", destination_url="https://example.com/hook", source_type="generic", secret_header_name="X-Secret")


def test_generic_requires_secret_header_name():
    with pytest.raises(ValidationError, match="secret_header_name is required for generic"):
        RouteCreate(slug="gen", destination_url="https://example.com/hook", source_type="generic", signing_secret="s3cret")


def test_generic_valid():
    r = RouteCreate(slug="gen", destination_url="https://example.com/hook", source_type="generic", signing_secret="s3cret", secret_header_name="X-Token")
    assert r.source_type == "generic"


def test_invalid_source_type():
    with pytest.raises(ValidationError):
        RouteCreate(slug="ok", destination_url="https://example.com/hook", source_type="invalid")
