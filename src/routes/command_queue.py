"""Command Queue API v0."""
from typing import Any, Dict, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.models.command_queue import CommandQueueItem
from src.security.auth import require_admin_role
from src.telemetry import log_event

router = APIRouter(prefix="/api/command-queue", tags=["Command Queue"])


@router.get("/")
async def list_items(limit: int = Query(default=10, ge=1, le=100), db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    stmt = select(CommandQueueItem).where(CommandQueueItem.status == "pending").order_by(desc(CommandQueueItem.priority_score)).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        {
            "id": i.id,
            "priority_score": i.priority_score,
            "action_type": i.action_type,
            "owner": i.owner,
            "due_by": i.due_by.isoformat() if i.due_by else None,
            "status": i.status,
        }
        for i in items
    ]


@router.post("/{item_id}/accept", dependencies=[Depends(require_admin_role)])
async def accept_item(item_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    item = await db.get(CommandQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.status = "accepted"
    await db.commit()
    await log_event("recommendation_accepted", {"item_id": item_id, "action_type": item.action_type})
    return {"status": "ok", "item_id": item_id}


@router.post("/{item_id}/dismiss", dependencies=[Depends(require_admin_role)])
async def dismiss_item(item_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    item = await db.get(CommandQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.status = "dismissed"
    await db.commit()
    await log_event("recommendation_dismissed", {"item_id": item_id, "action_type": item.action_type})
    return {"status": "ok", "item_id": item_id}


@router.post("/seed", dependencies=[Depends(require_admin_role)])
async def seed_demo_items(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    now = datetime.utcnow()
    items = [
        CommandQueueItem(priority_score=0.92, action_type="email_follow_up", owner="casey", due_by=now + timedelta(hours=2)),
        CommandQueueItem(priority_score=0.87, action_type="schedule_meeting", owner="casey", due_by=now + timedelta(hours=6)),
        CommandQueueItem(priority_score=0.81, action_type="update_crm", owner="casey", due_by=now + timedelta(days=1)),
    ]
    db.add_all(items)
    await db.commit()
    await log_event("seed_command_queue", {"count": len(items)})
    return {"status": "ok", "count": len(items)}
