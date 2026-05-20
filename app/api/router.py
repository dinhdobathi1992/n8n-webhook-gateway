from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.channel_rules import router as channel_rules_router
from app.api.webhooks import router as webhooks_router

api_router = APIRouter(prefix="/admin")
api_router.include_router(auth_router)
api_router.include_router(webhooks_router)
api_router.include_router(channel_rules_router)
