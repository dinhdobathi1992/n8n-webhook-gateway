import pytest
from httpx import AsyncClient

from app.auth import hash_password
from app.auth import create_access_token, decode_access_token
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


async def test_login_success(client: AsyncClient):
    resp = await client.post("/admin/api/auth/login", json={
        "username": settings.admin_username,
        "password": settings.admin_password,
    })
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert "gateway_token" in resp.cookies


async def test_login_wrong_password(client: AsyncClient):
    resp = await client.post("/admin/api/auth/login", json={
        "username": settings.admin_username,
        "password": "wrong",
    })
    assert resp.status_code == 401


async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post("/admin/api/auth/login", json={
        "username": "nobody",
        "password": "whatever",
    })
    assert resp.status_code == 401


async def test_logout(auth_client: AsyncClient):
    resp = await auth_client.post("/admin/api/auth/logout")
    assert resp.status_code == 200


def test_access_token_claims_decode():
    token = create_access_token(123)
    assert decode_access_token(token) == 123
