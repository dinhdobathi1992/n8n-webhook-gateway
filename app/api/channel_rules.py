from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db import get_session
from app.models import ChannelRule, WebhookRoute
from app.schemas import ChannelRuleCreate, ChannelRuleResponse

router = APIRouter(
    prefix="/api/webhooks/{route_id}/channels",
    tags=["channel-rules"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=ChannelRuleResponse, status_code=201)
async def create_channel_rule(
    route_id: int,
    body: ChannelRuleCreate,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(WebhookRoute).where(WebhookRoute.id == route_id))
    route = result.scalar_one_or_none()
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")

    existing = await session.execute(
        select(ChannelRule).where(
            ChannelRule.route_id == route_id,
            ChannelRule.channel_id == body.channel_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Channel rule for '{body.channel_id}' already exists on this route",
        )

    rule = ChannelRule(
        route_id=route_id,
        channel_id=body.channel_id,
        destination_url=body.destination_url,
        workflow_url=body.workflow_url,
        description=body.description,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


@router.get("", response_model=list[ChannelRuleResponse])
async def list_channel_rules(
    route_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(WebhookRoute).where(WebhookRoute.id == route_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Route not found")

    result = await session.execute(
        select(ChannelRule).where(ChannelRule.route_id == route_id).order_by(ChannelRule.id)
    )
    return result.scalars().all()


@router.delete("/{rule_id}")
async def delete_channel_rule(
    route_id: int,
    rule_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ChannelRule).where(ChannelRule.id == rule_id, ChannelRule.route_id == route_id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="Channel rule not found")
    await session.delete(rule)
    await session.commit()
    return {"ok": True}
