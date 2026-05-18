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
from app.security import startup_security_errors

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    security_errors = startup_security_errors()
    if security_errors:
        raise RuntimeError("Unsafe startup configuration: " + "; ".join(security_errors))
    if settings.allow_weak_secrets:
        logger.warning("ALLOW_WEAK_SECRETS is enabled — use only for local development")
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


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    if settings.security_headers_enabled:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

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
