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


async def create_route(auth_client: AsyncClient) -> int:
    resp = await auth_client.post("/admin/api/webhooks", json={
        "slug": "slack-multi",
        "destination_url": "https://n8n.example.com/webhook/default",
        "signing_secret": "test-secret",
        "source_type": "slack",
    })
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_create_channel_rule(auth_client: AsyncClient):
    route_id = await create_route(auth_client)
    resp = await auth_client.post(f"/admin/api/webhooks/{route_id}/channels", json={
        "channel_id": "C0B3WDWKESH",
        "destination_url": "https://n8n.example.com/webhook/channel-a",
        "workflow_url": "https://n8n.example.com/workflow/123",
        "description": "Channel A workflow",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["channel_id"] == "C0B3WDWKESH"
    assert data["destination_url"] == "https://n8n.example.com/webhook/channel-a"
    assert data["workflow_url"] == "https://n8n.example.com/workflow/123"
    assert data["route_id"] == route_id


async def test_create_duplicate_channel_rule_409(auth_client: AsyncClient):
    route_id = await create_route(auth_client)
    rule = {
        "channel_id": "C0B3WDWKESH",
        "destination_url": "https://n8n.example.com/webhook/channel-a",
    }
    await auth_client.post(f"/admin/api/webhooks/{route_id}/channels", json=rule)
    resp = await auth_client.post(f"/admin/api/webhooks/{route_id}/channels", json=rule)
    assert resp.status_code == 409


async def test_list_channel_rules(auth_client: AsyncClient):
    route_id = await create_route(auth_client)
    await auth_client.post(f"/admin/api/webhooks/{route_id}/channels", json={
        "channel_id": "C001",
        "destination_url": "https://n8n.example.com/webhook/1",
    })
    await auth_client.post(f"/admin/api/webhooks/{route_id}/channels", json={
        "channel_id": "C002",
        "destination_url": "https://n8n.example.com/webhook/2",
    })
    resp = await auth_client.get(f"/admin/api/webhooks/{route_id}/channels")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_delete_channel_rule(auth_client: AsyncClient):
    route_id = await create_route(auth_client)
    create_resp = await auth_client.post(f"/admin/api/webhooks/{route_id}/channels", json={
        "channel_id": "C001",
        "destination_url": "https://n8n.example.com/webhook/1",
    })
    rule_id = create_resp.json()["id"]
    resp = await auth_client.delete(f"/admin/api/webhooks/{route_id}/channels/{rule_id}")
    assert resp.status_code == 200
    list_resp = await auth_client.get(f"/admin/api/webhooks/{route_id}/channels")
    assert len(list_resp.json()) == 0


async def test_channel_rules_included_in_route_response(auth_client: AsyncClient):
    route_id = await create_route(auth_client)
    await auth_client.post(f"/admin/api/webhooks/{route_id}/channels", json={
        "channel_id": "C001",
        "destination_url": "https://n8n.example.com/webhook/1",
    })
    resp = await auth_client.get(f"/admin/api/webhooks/{route_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "channel_rules" in data
    assert len(data["channel_rules"]) == 1
    assert data["channel_rules"][0]["channel_id"] == "C001"


async def test_route_without_channel_rules_has_empty_list(auth_client: AsyncClient):
    route_id = await create_route(auth_client)
    resp = await auth_client.get(f"/admin/api/webhooks/{route_id}")
    assert resp.status_code == 200
    assert resp.json()["channel_rules"] == []


async def test_create_channel_rule_on_nonexistent_route_404(auth_client: AsyncClient):
    resp = await auth_client.post("/admin/api/webhooks/9999/channels", json={
        "channel_id": "C001",
        "destination_url": "https://n8n.example.com/webhook/1",
    })
    assert resp.status_code == 404
