from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.webhooks import router as webhooks_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(webhooks_router)
