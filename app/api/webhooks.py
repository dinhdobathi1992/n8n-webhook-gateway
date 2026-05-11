from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
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
