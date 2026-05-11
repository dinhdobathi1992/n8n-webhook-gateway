from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password
from app.config import settings
from app.db import engine, get_session
from app.models import Base, User, WebhookRoute


@asynccontextmanager
async def lifespan(application: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async for session in get_session():
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is None:
            admin = User(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
            )
            session.add(admin)
            await session.commit()
    yield


app = FastAPI(title="n8n Webhook Gateway", lifespan=lifespan)

from app.api.router import api_router  # noqa: E402

app.include_router(api_router)

from app.inbound.http import router as inbound_router  # noqa: E402

app.include_router(inbound_router)


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(func.count()).select_from(WebhookRoute).where(WebhookRoute.enabled == True))  # noqa: E712
    count = result.scalar() or 0
    return {"status": "ok", "routes": count}
