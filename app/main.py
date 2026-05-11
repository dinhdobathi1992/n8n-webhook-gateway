import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password
from app.config import settings
from app.db import engine, get_session
from app.models import Base, User, WebhookRoute

logger = logging.getLogger(__name__)

WEAK_SECRETS = {"change-me", "change-me-to-random-secret", "secret", ""}


@asynccontextmanager
async def lifespan(application: FastAPI):
    if settings.secret_key in WEAK_SECRETS:
        logger.warning("SECRET_KEY is weak or default — set a strong random value before deploying to production")
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.public_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.router import api_router  # noqa: E402

app.include_router(api_router)

from app.inbound.http import router as inbound_router  # noqa: E402

app.include_router(inbound_router)


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(func.count()).select_from(WebhookRoute).where(WebhookRoute.enabled == True))  # noqa: E712
    count = result.scalar() or 0
    return {"status": "ok", "routes": count}


# --- Static file serving for React UI (must be LAST) ---
ui_dist = Path(__file__).parent.parent / "ui" / "dist"

if ui_dist.exists():
    app.mount("/assets", StaticFiles(directory=ui_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = (ui_dist / full_path).resolve()
        if file_path.is_relative_to(ui_dist.resolve()) and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(ui_dist / "index.html")
