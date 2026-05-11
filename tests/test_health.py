import pytest
from httpx import AsyncClient

from app.auth import hash_password
from app.config import settings
from app.db import get_session
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
            slug="health-check",
            destination_url="https://example.com/hook",
            enabled=True,
            created_by=user.id,
        )
        session.add(route)
        await session.commit()


async def test_health(client: AsyncClient):
    await seed_data(client)
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["routes"] == 1


async def test_health_no_routes(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["routes"] == 0
