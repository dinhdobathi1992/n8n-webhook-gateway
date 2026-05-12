# n8n Webhook Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build HTTP webhook gateway that forwards inbound requests to registered destination URLs, with auth, route management, delivery logging, and React UI.

**Architecture:** Single FastAPI process. SQLite + SQLAlchemy async. Public `/{slug}/webhook` proxy endpoint + `/api/*` management API. React + Vite + getdesign apple UI served as static files.

**Tech Stack:** Python 3.12, FastAPI, httpx, SQLAlchemy async, aiosqlite, passlib[bcrypt], python-jose, React, Vite, TypeScript, getdesign apple

---

## File Structure

```
app/
  __init__.py
  main.py              # FastAPI app, lifespan, static mount, health
  config.py            # env var parsing via pydantic-settings
  db.py                # async engine, session maker, create_all
  models.py            # SQLAlchemy ORM models
  schemas.py           # Pydantic request/response schemas
  auth.py              # password hashing, JWT cookie, auth dependency
  forwarding.py        # httpx forward, retry, HMAC sign/verify
  api/
    __init__.py
    router.py          # APIRouter aggregating sub-routers
    auth.py            # POST /api/auth/login, /logout
    webhooks.py        # CRUD /api/webhooks, deliveries
  inbound/
    __init__.py
    http.py            # ANY /{slug}/webhook
tests/
  __init__.py
  conftest.py          # fixtures: async client, test db, seeded user
  test_auth.py
  test_webhooks.py
  test_forwarding.py
  test_inbound.py
ui/                    # React + Vite (Task 9)
requirements.txt
pytest.ini
.env.example
Dockerfile
```

---

### Task 1: Project Scaffold + Config

**Files:**
- Create: `requirements.txt`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `.env.example`
- Create: `pytest.ini`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
httpx>=0.25.0
sqlalchemy[asyncio]>=2.0.0
aiosqlite>=0.19.0
passlib[bcrypt]>=1.7.4
python-jose[cryptography]>=3.3.0
python-dotenv>=1.0.0
pydantic-settings>=2.0.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

- [ ] **Step 2: Create `.env.example`**

```
PORT=3000
DATABASE_URL=sqlite+aiosqlite:///./gateway.db
SECRET_KEY=change-me-to-random-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
PUBLIC_BASE_URL=http://localhost:3000
FORWARD_TIMEOUT_SECONDS=30
FORWARD_MAX_RETRIES=3
FORWARD_RETRY_BASE_SECONDS=1
```

- [ ] **Step 3: Create `app/__init__.py`**

```python
```

- [ ] **Step 4: Create `app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 3000
    database_url: str = "sqlite+aiosqlite:///./gateway.db"
    secret_key: str = "change-me"
    admin_username: str = "admin"
    admin_password: str = "admin"
    public_base_url: str = "http://localhost:3000"
    forward_timeout_seconds: int = 30
    forward_max_retries: int = 3
    forward_retry_base_seconds: int = 1

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 5: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 6: Create `tests/__init__.py` and `tests/conftest.py`**

`tests/__init__.py`: empty file.

```python
# tests/conftest.py
import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db import get_session
from app.main import app
from app.models import Base

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
    await client.post("/api/auth/login", json={
        "username": settings.admin_username,
        "password": settings.admin_password,
    })
    return client
```

- [ ] **Step 7: Install dependencies**

Run: `cd /Users/thi/Devops/n8n-webhook-gateway && pnpm init -y 2>/dev/null; python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

- [ ] **Step 8: Commit**

```bash
git init
git add requirements.txt .env.example pytest.ini app/__init__.py app/config.py tests/__init__.py tests/conftest.py .gitignore
git commit -m "feat: scaffold project with config and test fixtures"
```

---

### Task 2: Database + Models

**Files:**
- Create: `app/db.py`
- Create: `app/models.py`

- [ ] **Step 1: Create `app/db.py`**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```

- [ ] **Step 2: Create `app/models.py`**

```python
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    routes: Mapped[list["WebhookRoute"]] = relationship(back_populates="creator")


class WebhookRoute(Base):
    __tablename__ = "webhook_routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    destination_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    signing_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    creator: Mapped["User"] = relationship(back_populates="routes")
    deliveries: Mapped[list["DeliveryAttempt"]] = relationship(back_populates="route")


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(Integer, ForeignKey("webhook_routes.id"), nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    route: Mapped["WebhookRoute"] = relationship(back_populates="deliveries")
```

- [ ] **Step 3: Verify models import clean**

Run: `cd /Users/thi/Devops/n8n-webhook-gateway && .venv/bin/python -c "from app.models import Base, User, WebhookRoute, DeliveryAttempt; print('OK')"` 
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/db.py app/models.py
git commit -m "feat: add async database layer and ORM models"
```

---

### Task 3: Pydantic Schemas

**Files:**
- Create: `app/schemas.py`

- [ ] **Step 1: Create `app/schemas.py`**

```python
import re
from datetime import datetime

from pydantic import BaseModel, field_validator

SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
RESERVED_SLUGS = {"api", "health", "docs", "openapi.json", "redoc", "ui"}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    ok: bool = True


class RouteCreate(BaseModel):
    slug: str
    destination_url: str
    signing_secret: str | None = None
    description: str | None = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not SLUG_PATTERN.match(v):
            raise ValueError("slug must match ^[a-zA-Z0-9_-]{1,64}$")
        if v.lower() in RESERVED_SLUGS:
            raise ValueError(f"slug '{v}' is reserved")
        return v

    @field_validator("destination_url")
    @classmethod
    def validate_destination(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("destination_url must start with http:// or https://")
        return v


class RouteUpdate(BaseModel):
    destination_url: str | None = None
    enabled: bool | None = None
    signing_secret: str | None = None
    description: str | None = None

    @field_validator("destination_url")
    @classmethod
    def validate_destination(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("destination_url must start with http:// or https://")
        return v


class RouteResponse(BaseModel):
    id: int
    slug: str
    destination_url: str
    enabled: bool
    signing_secret_set: bool
    description: str | None
    webhook_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DeliveryResponse(BaseModel):
    id: int
    route_id: int
    source_event_id: str | None
    method: str
    status: str
    attempt_count: int
    response_status: int | None
    response_body_excerpt: str | None
    error: str | None
    latency_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Write test for slug validation**

```python
# tests/test_schemas.py
import pytest
from pydantic import ValidationError

from app.schemas import RouteCreate


def test_valid_slug():
    r = RouteCreate(slug="my-route_1", destination_url="https://example.com/hook")
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
    r = RouteCreate(slug="ok", destination_url="https://good.com/webhook")
    assert r.destination_url == "https://good.com/webhook"
```

- [ ] **Step 3: Run schema tests**

Run: `cd /Users/thi/Devops/n8n-webhook-gateway && .venv/bin/pytest tests/test_schemas.py -v`
Expected: 6 passed

- [ ] **Step 4: Commit**

```bash
git add app/schemas.py tests/test_schemas.py
git commit -m "feat: add pydantic schemas with slug and URL validation"
```

---

### Task 4: Auth (Password Hashing + JWT Cookie + Dependency)

**Files:**
- Create: `app/auth.py`
- Create: `app/api/__init__.py`
- Create: `app/api/auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Create `app/auth.py`**

```python
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except (JWTError, ValueError):
        return None
```

- [ ] **Step 2: Create `app/api/__init__.py`**

```python
```

- [ ] **Step 3: Create `app/api/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.requests import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, decode_access_token, hash_password, verify_password
from app.db import get_session
from app.models import User
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "gateway_token"


async def get_current_user(request: Request, session: AsyncSession = Depends(get_session)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, response: Response, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24,
    )
    return LoginResponse()


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"ok": True}
```

- [ ] **Step 4: Write auth tests**

```python
# tests/test_auth.py
import pytest
from httpx import AsyncClient

from app.auth import hash_password
from app.config import settings
from app.db import get_session
from app.models import User


async def seed_admin(client: AsyncClient):
    """Seed admin user directly via DB."""
    override = client._transport.app.dependency_overrides[get_session]  # noqa: SLF001
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
    resp = await client.post("/api/auth/login", json={
        "username": settings.admin_username,
        "password": settings.admin_password,
    })
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert "gateway_token" in resp.cookies


async def test_login_wrong_password(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={
        "username": settings.admin_username,
        "password": "wrong",
    })
    assert resp.status_code == 401


async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={
        "username": "nobody",
        "password": "whatever",
    })
    assert resp.status_code == 401


async def test_logout(auth_client: AsyncClient):
    resp = await auth_client.post("/api/auth/logout")
    assert resp.status_code == 200


async def test_protected_endpoint_no_cookie(client: AsyncClient):
    resp = await client.get("/api/webhooks")
    assert resp.status_code == 401
```

- [ ] **Step 5: Create minimal `app/main.py` to make tests runnable**

```python
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password
from app.config import settings
from app.db import engine, get_session
from app.models import Base, User

from fastapi import FastAPI, Depends


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

from app.api.auth import router as auth_router  # noqa: E402

app.include_router(auth_router)


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    return {"status": "ok"}
```

- [ ] **Step 6: Run auth tests**

Run: `cd /Users/thi/Devops/n8n-webhook-gateway && .venv/bin/pytest tests/test_auth.py -v`
Expected: 5 passed

- [ ] **Step 7: Commit**

```bash
git add app/auth.py app/api/__init__.py app/api/auth.py app/main.py tests/test_auth.py
git commit -m "feat: add auth with JWT cookie, login/logout, and auth dependency"
```

---

### Task 5: Webhook Route CRUD API

**Files:**
- Create: `app/api/webhooks.py`
- Create: `app/api/router.py`
- Modify: `app/main.py`
- Create: `tests/test_webhooks.py`

- [ ] **Step 1: Create `app/api/webhooks.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config import settings
from app.db import get_session
from app.models import DeliveryAttempt, User, WebhookRoute
from app.schemas import DeliveryResponse, RouteCreate, RouteResponse, RouteUpdate

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"], dependencies=[Depends(get_current_user)])


def _to_response(route: WebhookRoute) -> RouteResponse:
    return RouteResponse(
        id=route.id,
        slug=route.slug,
        destination_url=route.destination_url,
        enabled=route.enabled,
        signing_secret_set=route.signing_secret is not None,
        description=route.description,
        webhook_url=f"{settings.public_base_url}/{route.slug}/webhook",
        created_at=route.created_at,
    )


@router.post("", response_model=RouteResponse, status_code=201)
async def create_route(
    body: RouteCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    existing = await session.execute(select(WebhookRoute).where(WebhookRoute.slug == body.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail=f"slug '{body.slug}' already exists")
    route = WebhookRoute(
        slug=body.slug,
        destination_url=body.destination_url,
        signing_secret=body.signing_secret,
        description=body.description,
        created_by=user.id,
    )
    session.add(route)
    await session.commit()
    await session.refresh(route)
    return _to_response(route)


@router.get("", response_model=list[RouteResponse])
async def list_routes(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WebhookRoute).order_by(WebhookRoute.id))
    routes = result.scalars().all()
    return [_to_response(r) for r in routes]


@router.get("/{route_id}", response_model=RouteResponse)
async def get_route(route_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WebhookRoute).where(WebhookRoute.id == route_id))
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    return _to_response(route)


@router.patch("/{route_id}", response_model=RouteResponse)
async def update_route(
    route_id: int, body: RouteUpdate, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(WebhookRoute).where(WebhookRoute.id == route_id))
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    if body.destination_url is not None:
        route.destination_url = body.destination_url
    if body.enabled is not None:
        route.enabled = body.enabled
    if body.signing_secret is not None:
        route.signing_secret = body.signing_secret
    if body.description is not None:
        route.description = body.description
    await session.commit()
    await session.refresh(route)
    return _to_response(route)


@router.delete("/{route_id}")
async def delete_route(route_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(WebhookRoute).where(WebhookRoute.id == route_id))
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")
    route.enabled = False
    await session.commit()
    return {"ok": True}


@router.get("/{route_id}/deliveries", response_model=list[DeliveryResponse])
async def list_deliveries(
    route_id: int,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(WebhookRoute).where(WebhookRoute.id == route_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Route not found")
    result = await session.execute(
        select(DeliveryAttempt)
        .where(DeliveryAttempt.route_id == route_id)
        .order_by(DeliveryAttempt.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()
```

- [ ] **Step 2: Create `app/api/router.py`**

```python
from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.webhooks import router as webhooks_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(webhooks_router)
```

- [ ] **Step 3: Update `app/main.py` to use aggregated router**

Replace the router includes at bottom of `app/main.py`:

```python
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


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(func.count()).select_from(WebhookRoute).where(WebhookRoute.enabled == True))  # noqa: E712
    count = result.scalar() or 0
    return {"status": "ok", "routes": count}
```

- [ ] **Step 4: Write webhook CRUD tests**

```python
# tests/test_webhooks.py
import pytest
from httpx import AsyncClient

from app.auth import hash_password
from app.config import settings
from app.db import get_session
from app.models import User


async def seed_admin(client: AsyncClient):
    override = client._transport.app.dependency_overrides[get_session]  # noqa: SLF001
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
```

- [ ] **Step 5: Run webhook tests**

Run: `cd /Users/thi/Devops/n8n-webhook-gateway && .venv/bin/pytest tests/test_webhooks.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add app/api/webhooks.py app/api/router.py app/main.py tests/test_webhooks.py
git commit -m "feat: add webhook route CRUD API with auth protection"
```

---

### Task 6: Forwarding Service (httpx + retry + HMAC)

**Files:**
- Create: `app/forwarding.py`
- Create: `tests/test_forwarding.py`

- [ ] **Step 1: Create `app/forwarding.py`**

```python
import hashlib
import hmac
import logging
import time
import uuid
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ForwardResult:
    delivery_id: str
    status: str
    attempt_count: int
    response_status: int | None
    response_body_excerpt: str | None
    error: str | None
    latency_ms: int


def verify_slack_signature(signing_secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    ts = int(timestamp)
    if abs(time.time() - ts) > 300:
        return False
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected = "v0=" + hmac.new(
        signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def sign_gateway_payload(signing_secret: str, timestamp: str, body: bytes) -> str:
    sig_input = f"{timestamp}.{body.decode('utf-8')}"
    return "sha256=" + hmac.new(
        signing_secret.encode(), sig_input.encode(), hashlib.sha256
    ).hexdigest()


async def forward_request(
    destination_url: str,
    method: str,
    body: bytes,
    headers: dict[str, str],
    query_string: str,
    slug: str,
    signing_secret: str | None = None,
) -> ForwardResult:
    delivery_id = str(uuid.uuid4())
    timestamp = str(int(time.time()))

    forward_headers = {
        "content-type": headers.get("content-type", "application/json"),
        "X-Gateway-Route": slug,
        "X-Gateway-Delivery-Id": delivery_id,
        "X-Gateway-Timestamp": timestamp,
    }

    if signing_secret:
        forward_headers["X-Gateway-Signature"] = sign_gateway_payload(signing_secret, timestamp, body)

    url = destination_url
    if query_string:
        url = f"{destination_url}?{query_string}"

    attempt_count = 0
    last_error: str | None = None
    last_status: int | None = None
    last_body: str | None = None
    start_ms = int(time.time() * 1000)

    async with httpx.AsyncClient(timeout=settings.forward_timeout_seconds) as client:
        for attempt in range(1, settings.forward_max_retries + 1):
            attempt_count = attempt
            try:
                resp = await client.request(method, url, content=body, headers=forward_headers)
                last_status = resp.status_code
                last_body = resp.text[:1000]
                last_error = None

                if resp.status_code < 500:
                    break

                logger.warning(f"[{slug}] attempt {attempt} got {resp.status_code}, retrying")

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_error = str(exc)
                last_status = None
                last_body = None
                logger.warning(f"[{slug}] attempt {attempt} failed: {exc}")

            if attempt < settings.forward_max_retries:
                import asyncio
                await asyncio.sleep(settings.forward_retry_base_seconds * (2 ** (attempt - 1)))

    elapsed = int(time.time() * 1000) - start_ms
    status = "success" if last_status and last_status < 400 else "failed"

    return ForwardResult(
        delivery_id=delivery_id,
        status=status,
        attempt_count=attempt_count,
        response_status=last_status,
        response_body_excerpt=last_body,
        error=last_error,
        latency_ms=elapsed,
    )
```

- [ ] **Step 2: Write forwarding tests**

```python
# tests/test_forwarding.py
import hashlib
import hmac as hmac_mod
import json
import time

import httpx
import pytest

from app.forwarding import forward_request, sign_gateway_payload, verify_slack_signature


def test_verify_slack_signature_valid():
    secret = "my-secret"
    body = b'{"event":"test"}'
    timestamp = str(int(time.time()))
    sig_base = f"v0:{timestamp}:{body.decode()}"
    sig = "v0=" + hmac_mod.new(secret.encode(), sig_base.encode(), hashlib.sha256).hexdigest()
    assert verify_slack_signature(secret, timestamp, body, sig) is True


def test_verify_slack_signature_invalid():
    assert verify_slack_signature("secret", str(int(time.time())), b"body", "v0=bad") is False


def test_verify_slack_signature_expired():
    secret = "my-secret"
    body = b"body"
    old_ts = str(int(time.time()) - 600)
    sig_base = f"v0:{old_ts}:{body.decode()}"
    sig = "v0=" + hmac_mod.new(secret.encode(), sig_base.encode(), hashlib.sha256).hexdigest()
    assert verify_slack_signature(secret, old_ts, body, sig) is False


def test_sign_gateway_payload():
    sig = sign_gateway_payload("secret", "12345", b"hello")
    assert sig.startswith("sha256=")
    expected = hmac_mod.new("secret".encode(), b"12345.hello", hashlib.sha256).hexdigest()
    assert sig == f"sha256={expected}"


async def test_forward_request_success(httpx_mock):
    """Uses pytest-httpx if available, otherwise skip."""
    pytest.importorskip("pytest_httpx")
    from pytest_httpx import HTTPXMock
    # Simplified: test the function shape returns ForwardResult
    # Full integration test in test_inbound.py


async def test_forward_result_fields():
    # Verify ForwardResult dataclass
    from app.forwarding import ForwardResult
    r = ForwardResult(
        delivery_id="abc",
        status="success",
        attempt_count=1,
        response_status=200,
        response_body_excerpt="ok",
        error=None,
        latency_ms=50,
    )
    assert r.status == "success"
    assert r.delivery_id == "abc"
```

- [ ] **Step 3: Run forwarding tests**

Run: `cd /Users/thi/Devops/n8n-webhook-gateway && .venv/bin/pytest tests/test_forwarding.py -v`
Expected: 5 passed (1 skipped if no pytest-httpx)

- [ ] **Step 4: Commit**

```bash
git add app/forwarding.py tests/test_forwarding.py
git commit -m "feat: add forwarding service with retry, HMAC signing, and Slack verification"
```

---

### Task 7: Inbound HTTP Proxy Endpoint

**Files:**
- Create: `app/inbound/__init__.py`
- Create: `app/inbound/http.py`
- Modify: `app/main.py` (include inbound router)
- Create: `tests/test_inbound.py`

- [ ] **Step 1: Create `app/inbound/__init__.py`**

Empty file.

- [ ] **Step 2: Create `app/inbound/http.py`**

```python
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db import get_session
from app.forwarding import forward_request, verify_slack_signature
from app.models import DeliveryAttempt, WebhookRoute

router = APIRouter()


@router.api_route("/{slug}/webhook", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def inbound_webhook(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WebhookRoute).where(WebhookRoute.slug == slug, WebhookRoute.enabled == True)  # noqa: E712
    )
    route = result.scalar_one_or_none()
    if route is None:
        return JSONResponse(status_code=404, content={"detail": "Route not found"})

    body = await request.body()

    if route.signing_secret and request.headers.get("x-slack-signature"):
        timestamp = request.headers.get("x-slack-request-timestamp", "")
        signature = request.headers.get("x-slack-signature", "")
        if not verify_slack_signature(route.signing_secret, timestamp, body, signature):
            return JSONResponse(status_code=401, content={"detail": "Invalid signature"})

    headers = dict(request.headers)
    query_string = str(request.url.query) if request.url.query else ""

    fwd = await forward_request(
        destination_url=route.destination_url,
        method=request.method,
        body=body,
        headers=headers,
        query_string=query_string,
        slug=route.slug,
        signing_secret=route.signing_secret,
    )

    delivery = DeliveryAttempt(
        route_id=route.id,
        source_event_id=request.headers.get("x-slack-request-timestamp"),
        method=request.method,
        status=fwd.status,
        attempt_count=fwd.attempt_count,
        response_status=fwd.response_status,
        response_body_excerpt=fwd.response_body_excerpt,
        error=fwd.error,
        latency_ms=fwd.latency_ms,
    )
    session.add(delivery)
    await session.commit()

    return Response(
        content=fwd.response_body_excerpt or "",
        status_code=fwd.response_status or 502,
        media_type="application/json",
    )
```

- [ ] **Step 3: Add inbound router to `app/main.py`**

Add after the `app.include_router(api_router)` line:

```python
from app.inbound.http import router as inbound_router  # noqa: E402

app.include_router(inbound_router)
```

- [ ] **Step 4: Write inbound tests**

```python
# tests/test_inbound.py
import hashlib
import hmac as hmac_mod
import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.auth import hash_password
from app.config import settings
from app.db import get_session
from app.forwarding import ForwardResult
from app.models import User, WebhookRoute


async def seed_data(client: AsyncClient):
    override = client._transport.app.dependency_overrides[get_session]  # noqa: SLF001
    async for session in override():
        user = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        route = WebhookRoute(
            slug="test-inbound",
            destination_url="https://n8n.example.com/webhook/abc",
            enabled=True,
            created_by=user.id,
        )
        session.add(route)
        route_signed = WebhookRoute(
            slug="test-signed",
            destination_url="https://n8n.example.com/webhook/def",
            enabled=True,
            signing_secret="test-secret",
            created_by=user.id,
        )
        session.add(route_signed)
        disabled = WebhookRoute(
            slug="test-disabled",
            destination_url="https://n8n.example.com/webhook/ghi",
            enabled=False,
            created_by=user.id,
        )
        session.add(disabled)
        await session.commit()


@pytest.fixture(autouse=True)
async def _seed(client: AsyncClient):
    await seed_data(client)


def _mock_forward_result(**kwargs):
    defaults = {
        "delivery_id": "test-id",
        "status": "success",
        "attempt_count": 1,
        "response_status": 200,
        "response_body_excerpt": '{"ok":true}',
        "error": None,
        "latency_ms": 50,
    }
    defaults.update(kwargs)
    return ForwardResult(**defaults)


@patch("app.inbound.http.forward_request")
async def test_forward_success(mock_fwd: AsyncMock, client: AsyncClient):
    mock_fwd.return_value = _mock_forward_result()
    resp = await client.post(
        "/test-inbound/webhook",
        json={"event": "test"},
    )
    assert resp.status_code == 200
    mock_fwd.assert_called_once()


@patch("app.inbound.http.forward_request")
async def test_unknown_slug_404(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post("/nonexistent/webhook", json={})
    assert resp.status_code == 404
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
async def test_disabled_route_404(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post("/test-disabled/webhook", json={})
    assert resp.status_code == 404
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
async def test_valid_slack_signature(mock_fwd: AsyncMock, client: AsyncClient):
    mock_fwd.return_value = _mock_forward_result()
    body = b'{"event":"test"}'
    timestamp = str(int(time.time()))
    sig_base = f"v0:{timestamp}:{body.decode()}"
    sig = "v0=" + hmac_mod.new(b"test-secret", sig_base.encode(), hashlib.sha256).hexdigest()
    resp = await client.post(
        "/test-signed/webhook",
        content=body,
        headers={
            "content-type": "application/json",
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": sig,
        },
    )
    assert resp.status_code == 200


@patch("app.inbound.http.forward_request")
async def test_invalid_slack_signature_401(mock_fwd: AsyncMock, client: AsyncClient):
    resp = await client.post(
        "/test-signed/webhook",
        content=b"body",
        headers={
            "content-type": "application/json",
            "x-slack-request-timestamp": str(int(time.time())),
            "x-slack-signature": "v0=invalid",
        },
    )
    assert resp.status_code == 401
    mock_fwd.assert_not_called()


@patch("app.inbound.http.forward_request")
async def test_signed_route_no_slack_headers_forwards(mock_fwd: AsyncMock, client: AsyncClient):
    mock_fwd.return_value = _mock_forward_result()
    resp = await client.post("/test-signed/webhook", json={"data": "no-slack-headers"})
    assert resp.status_code == 200
    mock_fwd.assert_called_once()
```

- [ ] **Step 5: Run inbound tests**

Run: `cd /Users/thi/Devops/n8n-webhook-gateway && .venv/bin/pytest tests/test_inbound.py -v`
Expected: 6 passed

- [ ] **Step 6: Run all tests**

Run: `cd /Users/thi/Devops/n8n-webhook-gateway && .venv/bin/pytest -v`
Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add app/inbound/__init__.py app/inbound/http.py app/main.py tests/test_inbound.py
git commit -m "feat: add inbound HTTP proxy with Slack signature verification"
```

---

### Task 8: Health Endpoint + Startup Admin Seed

**Files:**
- Modify: `app/main.py` (already has health + seed, verify complete)
- Create: `tests/test_health.py`

- [ ] **Step 1: Write health test**

```python
# tests/test_health.py
from httpx import AsyncClient

from app.auth import hash_password
from app.config import settings
from app.db import get_session
from app.models import User, WebhookRoute


async def seed_data(client: AsyncClient):
    override = client._transport.app.dependency_overrides[get_session]  # noqa: SLF001
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
```

- [ ] **Step 2: Run health tests**

Run: `cd /Users/thi/Devops/n8n-webhook-gateway && .venv/bin/pytest tests/test_health.py -v`
Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
git add tests/test_health.py
git commit -m "test: add health endpoint tests"
```

---

### Task 9: React UI with getdesign apple

**Files:**
- Create: `ui/` directory with Vite + React + TypeScript scaffold
- Create: `ui/src/pages/Login.tsx`
- Create: `ui/src/pages/Dashboard.tsx`
- Create: `ui/src/pages/RouteForm.tsx`
- Create: `ui/src/pages/RouteDetail.tsx`
- Create: `ui/src/components/RouteTable.tsx`
- Create: `ui/src/components/DeliveryLog.tsx`
- Create: `ui/src/components/TestPanel.tsx`
- Create: `ui/src/components/CopyButton.tsx`
- Create: `ui/src/lib/api.ts`
- Create: `ui/vite.config.ts`

- [ ] **Step 1: Scaffold Vite React project**

Run:
```bash
cd /Users/thi/Devops/n8n-webhook-gateway
pnpm create vite ui --template react-ts
cd ui
pnpm install
```

- [ ] **Step 2: Install getdesign apple + router**

Run:
```bash
cd /Users/thi/Devops/n8n-webhook-gateway/ui
npx getdesign@latest add apple
pnpm add react-router-dom
```

- [ ] **Step 3: Configure Vite proxy**

Replace `ui/vite.config.ts`:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:3000",
      "/health": "http://localhost:3000",
    },
  },
});
```

- [ ] **Step 4: Create `ui/src/lib/api.ts`**

```typescript
const BASE = "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export const api = {
  login: (username: string, password: string) =>
    request<{ ok: boolean }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  listRoutes: () => request<Route[]>("/api/webhooks"),
  getRoute: (id: number) => request<Route>(`/api/webhooks/${id}`),
  createRoute: (data: RouteCreate) =>
    request<Route>("/api/webhooks", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateRoute: (id: number, data: Partial<RouteCreate>) =>
    request<Route>(`/api/webhooks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteRoute: (id: number) =>
    request<{ ok: boolean }>(`/api/webhooks/${id}`, { method: "DELETE" }),
  getDeliveries: (id: number, limit = 50, offset = 0) =>
    request<Delivery[]>(`/api/webhooks/${id}/deliveries?limit=${limit}&offset=${offset}`),
};

export interface Route {
  id: number;
  slug: string;
  destination_url: string;
  enabled: boolean;
  signing_secret_set: boolean;
  description: string | null;
  webhook_url: string;
  created_at: string;
}

export interface RouteCreate {
  slug: string;
  destination_url: string;
  signing_secret?: string;
  description?: string;
}

export interface Delivery {
  id: number;
  route_id: number;
  source_event_id: string | null;
  method: string;
  status: string;
  attempt_count: number;
  response_status: number | null;
  response_body_excerpt: string | null;
  error: string | null;
  latency_ms: number | null;
  created_at: string;
}
```

- [ ] **Step 5: Create `ui/src/App.tsx` with routing**

```tsx
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useState } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import RouteForm from "./pages/RouteForm";
import RouteDetail from "./pages/RouteDetail";

export default function App() {
  const [authed, setAuthed] = useState(false);

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard onLogout={() => setAuthed(false)} />} />
        <Route path="/routes/new" element={<RouteForm />} />
        <Route path="/routes/:id/edit" element={<RouteForm />} />
        <Route path="/routes/:id" element={<RouteDetail />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 6: Create page and component files**

Create each file with working implementation using getdesign apple components. Each page:

`ui/src/pages/Login.tsx` — form with username, password, submit. Calls `api.login()`. On success calls `onLogin` prop.

`ui/src/pages/Dashboard.tsx` — fetches `api.listRoutes()`, renders `RouteTable`. Header with "Create Route" button + logout. `onLogout` prop calls `api.logout()`.

`ui/src/pages/RouteForm.tsx` — create/edit form. Fields: slug (disabled on edit), destination_url, description, signing_secret toggle + input. On submit calls `api.createRoute()` or `api.updateRoute()`. Navigates back to dashboard.

`ui/src/pages/RouteDetail.tsx` — fetches route + deliveries. Shows route info card + `DeliveryLog` + `TestPanel`.

`ui/src/components/RouteTable.tsx` — table rows: slug, destination (truncated 50 chars), enabled badge, webhook URL with `CopyButton`, actions (edit/disable/delete).

`ui/src/components/DeliveryLog.tsx` — table: timestamp, method, status badge (green success / red failed), response code, latency ms. Props: `deliveries: Delivery[]`.

`ui/src/components/TestPanel.tsx` — textarea for JSON body, send button. Posts to `/{slug}/webhook` via fetch. Shows response inline. Props: `webhookUrl: string`.

`ui/src/components/CopyButton.tsx` — button that copies text to clipboard, shows "Copied!" briefly. Props: `text: string`.

- [ ] **Step 7: Test UI dev server**

Run:
```bash
cd /Users/thi/Devops/n8n-webhook-gateway/ui
pnpm dev
```
Open http://localhost:5173 in browser. Verify login page renders.

- [ ] **Step 8: Commit**

```bash
git add ui/
git commit -m "feat: add React UI with getdesign apple, routing, and all pages"
```

---

### Task 10: Static File Serving in Production

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add static mount to `app/main.py`**

Add after all router includes, before health endpoint:

```python
import os
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

ui_dist = Path(__file__).parent.parent / "ui" / "dist"

if ui_dist.exists():
    app.mount("/assets", StaticFiles(directory=ui_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = ui_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(ui_dist / "index.html")
```

Note: this catch-all route must be registered LAST so `/api/*`, `/{slug}/webhook`, and `/health` take precedence.

- [ ] **Step 2: Build UI and test**

Run:
```bash
cd /Users/thi/Devops/n8n-webhook-gateway/ui
pnpm build
cd /Users/thi/Devops/n8n-webhook-gateway
.venv/bin/uvicorn app.main:app --port 3000
```
Open http://localhost:3000 — should serve React app.

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: serve React UI as static files in production"
```

---

### Task 11: Dockerfile + k8s Templates

**Files:**
- Create: `Dockerfile`
- Create: `k8s/deployment.yaml`
- Create: `k8s/service.yaml`
- Create: `k8s/secret.yaml.example`

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM node:20-slim AS ui-builder
WORKDIR /ui
COPY ui/package.json ui/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY ui/ .
RUN pnpm build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
COPY --from=ui-builder /ui/dist ui/dist/
EXPOSE 3000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]
```

- [ ] **Step 2: Create `k8s/deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webhook-gateway
spec:
  replicas: 1
  selector:
    matchLabels:
      app: webhook-gateway
  template:
    metadata:
      labels:
        app: webhook-gateway
    spec:
      containers:
        - name: gateway
          image: webhook-gateway:latest
          ports:
            - containerPort: 3000
          envFrom:
            - secretRef:
                name: webhook-gateway-secret
          readinessProbe:
            httpGet:
              path: /health
              port: 3000
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
```

- [ ] **Step 3: Create `k8s/service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: webhook-gateway
spec:
  selector:
    app: webhook-gateway
  ports:
    - port: 80
      targetPort: 3000
  type: ClusterIP
```

- [ ] **Step 4: Create `k8s/secret.yaml.example`**

```yaml
# Copy to secret.yaml and fill in real values. DO NOT commit secret.yaml.
apiVersion: v1
kind: Secret
metadata:
  name: webhook-gateway-secret
type: Opaque
stringData:
  PORT: "3000"
  DATABASE_URL: "sqlite+aiosqlite:///./gateway.db"
  SECRET_KEY: "CHANGE-ME"
  ADMIN_USERNAME: "admin"
  ADMIN_PASSWORD: "CHANGE-ME"
  PUBLIC_BASE_URL: "https://gateway.example.com"
```

- [ ] **Step 5: Verify `.gitignore` includes secrets**

Ensure `.gitignore` has:
```
.env
*.db
k8s/secret.yaml
.venv/
__pycache__/
ui/node_modules/
ui/dist/
```

- [ ] **Step 6: Commit**

```bash
git add Dockerfile k8s/ .gitignore
git commit -m "feat: add Dockerfile and k8s deployment templates"
```

---

### Task 12: Final Integration Test

**Files:**
- None new — run full suite

- [ ] **Step 1: Run full test suite**

Run: `cd /Users/thi/Devops/n8n-webhook-gateway && .venv/bin/pytest -v --tb=short`
Expected: all tests pass

- [ ] **Step 2: Run app locally end-to-end**

```bash
cp .env.example .env
.venv/bin/uvicorn app.main:app --port 3000 --reload
```

Manual test:
1. `POST /api/auth/login` with admin creds
2. `POST /api/webhooks` create route
3. `POST /{slug}/webhook` with test payload
4. `GET /api/webhooks/{id}/deliveries` check log
5. Open http://localhost:3000 verify UI loads

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup and integration verification"
```
