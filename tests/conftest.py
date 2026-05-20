import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.auth import clear_login_attempts
from app.config import settings
from app.db import get_session
from app.main import app
from app.models import Base

# Force http for tests so secure cookie flag is off
settings.public_base_url = "http://localhost:3000"
settings.secret_key = "test-secret-key-with-at-least-32-characters"
settings.encryption_key = "test-encryption-key-with-at-least-32-chars"
settings.force_https_cookies = False
settings.allow_weak_secrets = True
settings.webhook_rate_limit_per_min = 200
settings.webhook_max_body_bytes = 1_048_576

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_gateway.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    testing_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        async with testing_session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    clear_login_attempts()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    from app.auth import hash_password
    from app.models import User

    override = app.dependency_overrides.get(get_session)
    if override:
        async for session in override():
            from sqlalchemy import select
            result = await session.execute(select(User).where(User.username == settings.admin_username))
            if result.scalar_one_or_none() is None:
                user = User(
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                )
                session.add(user)
                await session.commit()

    resp = await client.post("/admin/api/auth/login", json={
        "username": settings.admin_username,
        "password": settings.admin_password,
    })
    assert resp.status_code == 200, f"auth_client login failed: {resp.json()}"
    return client
