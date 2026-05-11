import pytest
from httpx import AsyncClient

from app.auth import hash_password
from app.config import settings
from app.db import get_session
from app.models import User


async def seed_admin(client: AsyncClient):
    override = client._transport.app.dependency_overrides[get_session]
    async for session in override():
        user = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
        )
        session.add(user)
        await session.commit()


@pytest.fixture(autouse=True)
async def _seed(client: AsyncClient):
    await seed_admin(client)


async def test_create_route(auth_client: AsyncClient):
    resp = await auth_client.post("/api/webhooks", json={
        "slug": "test-route",
        "destination_url": "https://n8n.example.com/webhook/abc",
        "description": "Test route",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "test-route"
    assert data["enabled"] is True
    assert data["signing_secret_set"] is False
    assert "webhook_url" in data


async def test_create_duplicate_slug(auth_client: AsyncClient):
    await auth_client.post("/api/webhooks", json={
        "slug": "dup",
        "destination_url": "https://example.com/hook",
    })
    resp = await auth_client.post("/api/webhooks", json={
        "slug": "dup",
        "destination_url": "https://example.com/hook2",
    })
    assert resp.status_code == 409


async def test_create_reserved_slug(auth_client: AsyncClient):
    resp = await auth_client.post("/api/webhooks", json={
        "slug": "api",
        "destination_url": "https://example.com/hook",
    })
    assert resp.status_code == 422


async def test_list_routes(auth_client: AsyncClient):
    await auth_client.post("/api/webhooks", json={
        "slug": "r1",
        "destination_url": "https://example.com/hook1",
    })
    resp = await auth_client.get("/api/webhooks")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_get_route(auth_client: AsyncClient):
    create = await auth_client.post("/api/webhooks", json={
        "slug": "get-me",
        "destination_url": "https://example.com/hook",
    })
    route_id = create.json()["id"]
    resp = await auth_client.get(f"/api/webhooks/{route_id}")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "get-me"


async def test_update_route(auth_client: AsyncClient):
    create = await auth_client.post("/api/webhooks", json={
        "slug": "upd",
        "destination_url": "https://example.com/hook",
    })
    route_id = create.json()["id"]
    resp = await auth_client.patch(f"/api/webhooks/{route_id}", json={
        "destination_url": "https://new.example.com/hook",
        "enabled": False,
    })
    assert resp.status_code == 200
    assert resp.json()["destination_url"] == "https://new.example.com/hook"
    assert resp.json()["enabled"] is False


async def test_delete_route_soft_disables(auth_client: AsyncClient):
    create = await auth_client.post("/api/webhooks", json={
        "slug": "del-me",
        "destination_url": "https://example.com/hook",
    })
    route_id = create.json()["id"]
    resp = await auth_client.delete(f"/api/webhooks/{route_id}")
    assert resp.status_code == 200
    get_resp = await auth_client.get(f"/api/webhooks/{route_id}")
    assert get_resp.json()["enabled"] is False


async def test_unauthenticated_rejected(client: AsyncClient):
    resp = await client.get("/api/webhooks")
    assert resp.status_code == 401
