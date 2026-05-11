import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.requests import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, decode_access_token, hash_password, verify_password
from app.config import settings
from app.db import get_session
from app.models import User
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "gateway_token"
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 300
_login_attempts: dict[str, list[float]] = defaultdict(list)


def clear_login_attempts():
    _login_attempts.clear()


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
async def login(body: LoginRequest, request: Request, response: Response, session: AsyncSession = Depends(get_session)):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    attempts = _login_attempts[client_ip]
    attempts[:] = [t for t in attempts if now - t < LOCKOUT_SECONDS]
    if len(attempts) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many login attempts, try again later")

    result = await session.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        attempts.append(now)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    attempts.clear()
    is_https = settings.public_base_url.startswith("https://")
    token = create_access_token(user.id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_https,
        samesite="lax",
        max_age=60 * 60 * 24,
    )
    return LoginResponse()


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME)
    return {"ok": True}
