"""Command Queue API - Casey's Today's Moves.

This is the core API for managing Casey's prioritized action queue.
Each item represents something Casey should do, ranked by APS (Action Priority Score).
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, asc, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.models.command_queue import CommandQueueItem, ActionType, QueueItemStatus
from src.auth.decorators import get_current_user_optional
from src.models.user import User
from src.telemetry import log_event


# =============================================================================
# Pydantic Schemas
# =============================================================================

class DriverScores(BaseModel):
    """Breakdown of priority score components."""
    urgency: float = Field(default=0, ge=0, le=10, description="Time sensitivity")
    revenue: float = Field(default=0, ge=0, le=10, description="Revenue impact potential")
    effort: float = Field(default=0, ge=0, le=10, description="Effort required (lower = easier)")
    strategic: float = Field(default=0, ge=0, le=10, description="Strategic importance")


class CommandQueueItemCreate(BaseModel):
    """Schema for creating a queue item."""
    title: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    action_type: str = Field(default="other")
    priority_score: float = Field(default=50.0, ge=0, le=100)
    reasoning: Optional[str] = None
    drivers: Optional[DriverScores] = None
    
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    company_id: Optional[str] = None
    
    due_by: Optional[datetime] = None
    action_context: Optional[Dict[str, Any]] = None


class CommandQueueItemUpdate(BaseModel):
    """Schema for updating a queue item."""
    status: Optional[str] = Field(None, description="New status: pending, completed, skipped, snoozed")
    snoozed_until: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority_score: Optional[float] = Field(None, ge=0, le=100)


class CommandQueueItemResponse(BaseModel):
    """Schema for queue item response."""
    id: str
    title: str
    description: Optional[str]
    action_type: str
    priority_score: float
    status: str
    
    reasoning: Optional[str]
    drivers: Optional[Dict[str, Any]]
    
    contact_id: Optional[str]
    deal_id: Optional[str]
    company_id: Optional[str]
    
    due_by: Optional[datetime]
    snoozed_until: Optional[datetime]
    completed_at: Optional[datetime]
    
    owner: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CommandQueueListResponse(BaseModel):
    """Schema for list response with pagination."""
    items: List[CommandQueueItemResponse]
    total: int
    limit: int
    offset: int


class SnoozeOption(str, Enum):
    """Preset snooze durations."""
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    TOMORROW = "tomorrow"
    NEXT_WEEK = "next_week"


class SnoozeRequest(BaseModel):
    """Request to snooze an item."""
    duration: SnoozeOption


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/api/command-queue", tags=["Command Queue"])


def _to_response(item: CommandQueueItem) -> CommandQueueItemResponse:
    """Convert DB model to response schema."""
    return CommandQueueItemResponse(
        id=item.id,
        title=item.title,
        description=item.description,
        action_type=item.action_type,
        priority_score=item.priority_score,
        status=item.status,
        reasoning=item.reasoning,
        drivers=item.drivers,
        contact_id=item.contact_id,
        deal_id=item.deal_id,
        company_id=item.company_id,
        due_by=item.due_by,
        snoozed_until=item.snoozed_until,
        completed_at=item.completed_at,
        owner=item.owner,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


# =============================================================================
# CRUD Endpoints
# =============================================================================

@router.get("", response_model=CommandQueueListResponse)
async def list_queue_items(
    status: Optional[str] = Query(None, description="Filter by status (comma-separated: pending,completed)"),
    action_type: Optional[str] = Query(None, description="Filter by action type (comma-separated)"),
    sort: str = Query("-priority_score", description="Sort field with optional - prefix for desc"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
) -> CommandQueueListResponse:
    """List queue items with filtering and sorting.
    
    Filters:
    - status: pending, completed, skipped, snoozed (comma-separated)
    - action_type: send_email, book_meeting, etc. (comma-separated)
    
    Sort:
    - priority_score (default, descending)
    - created_at
    - due_by
    - Prefix with - for descending
    """
    # Base query
    stmt = select(CommandQueueItem)
    count_stmt = select(CommandQueueItem)
    
    # Filter by owner if user is logged in
    if user:
        stmt = stmt.where(CommandQueueItem.owner == user.email)
        count_stmt = count_stmt.where(CommandQueueItem.owner == user.email)
    
    # Status filter
    if status:
        statuses = [s.strip() for s in status.split(",")]
        stmt = stmt.where(CommandQueueItem.status.in_(statuses))
        count_stmt = count_stmt.where(CommandQueueItem.status.in_(statuses))
    else:
        # Default: show pending items, plus snoozed items that are due
        now = datetime.utcnow()
        stmt = stmt.where(
            or_(
                CommandQueueItem.status == "pending",
                and_(
                    CommandQueueItem.status == "snoozed",
                    CommandQueueItem.snoozed_until <= now
                )
            )
        )
        count_stmt = count_stmt.where(
            or_(
                CommandQueueItem.status == "pending",
                and_(
                    CommandQueueItem.status == "snoozed",
                    CommandQueueItem.snoozed_until <= now
                )
            )
        )
    
    # Action type filter
    if action_type:
        types = [t.strip() for t in action_type.split(",")]
        stmt = stmt.where(CommandQueueItem.action_type.in_(types))
        count_stmt = count_stmt.where(CommandQueueItem.action_type.in_(types))
    
    # Sorting
    descending = sort.startswith("-")
    sort_field = sort.lstrip("-")
    
    sort_map = {
        "priority_score": CommandQueueItem.priority_score,
        "created_at": CommandQueueItem.created_at,
        "due_by": CommandQueueItem.due_by,
        "updated_at": CommandQueueItem.updated_at,
    }
    
    sort_column = sort_map.get(sort_field, CommandQueueItem.priority_score)
    stmt = stmt.order_by(desc(sort_column) if descending else asc(sort_column))
    
    # Get total count
    count_result = await db.execute(count_stmt)
    total = len(count_result.scalars().all())
    
    # Apply pagination
    stmt = stmt.offset(offset).limit(limit)
    
    # Execute
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return CommandQueueListResponse(
        items=[_to_response(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{item_id}", response_model=CommandQueueItemResponse)
async def get_queue_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> CommandQueueItemResponse:
    """Get a single queue item by ID."""
    item = await db.get(CommandQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return _to_response(item)


@router.post("", response_model=CommandQueueItemResponse, status_code=201)
async def create_queue_item(
    data: CommandQueueItemCreate,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
) -> CommandQueueItemResponse:
    """Create a new queue item.
    
    This is primarily for testing and seeding. In production, queue items
    are created by signal ingestion and the APS calculator.
    """
    item = CommandQueueItem(
        id=str(uuid4()),
        title=data.title,
        description=data.description,
        action_type=data.action_type,
        priority_score=data.priority_score,
        reasoning=data.reasoning,
        drivers=data.drivers.model_dump() if data.drivers else None,
        contact_id=data.contact_id,
        deal_id=data.deal_id,
        company_id=data.company_id,
        due_by=data.due_by,
        action_context=data.action_context,
        owner=user.email if user else "casey",
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    db.add(item)
    await db.commit()
    await db.refresh(item)
    
    await log_event("queue_item_created", {
        "item_id": item.id,
        "action_type": item.action_type,
        "priority_score": item.priority_score,
    })
    
    return _to_response(item)


@router.patch("/{item_id}", response_model=CommandQueueItemResponse)
async def update_queue_item(
    item_id: str,
    data: CommandQueueItemUpdate,
    db: AsyncSession = Depends(get_db),
) -> CommandQueueItemResponse:
    """Update a queue item.
    
    Common operations:
    - Mark as completed: `{"status": "completed"}`
    - Skip: `{"status": "skipped"}`
    - Snooze: Use POST /{item_id}/snooze instead for presets
    """
    item = await db.get(CommandQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(item, field, value)
    
    # Track completion time
    if data.status == "completed" and not item.completed_at:
        item.completed_at = datetime.utcnow()
    
    item.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(item)
    
    await log_event("queue_item_updated", {
        "item_id": item_id,
        "changes": list(update_data.keys()),
        "new_status": item.status,
    })
    
    return _to_response(item)


@router.post("/{item_id}/complete", response_model=CommandQueueItemResponse)
async def complete_queue_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> CommandQueueItemResponse:
    """Mark a queue item as completed."""
    item = await db.get(CommandQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    item.status = "completed"
    item.completed_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(item)
    
    await log_event("queue_item_completed", {
        "item_id": item_id,
        "action_type": item.action_type,
    })
    
    return _to_response(item)


@router.post("/{item_id}/skip", response_model=CommandQueueItemResponse)
async def skip_queue_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> CommandQueueItemResponse:
    """Skip a queue item."""
    item = await db.get(CommandQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    item.status = "skipped"
    item.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(item)
    
    await log_event("queue_item_skipped", {
        "item_id": item_id,
        "action_type": item.action_type,
    })
    
    return _to_response(item)


@router.post("/{item_id}/snooze", response_model=CommandQueueItemResponse)
async def snooze_queue_item(
    item_id: str,
    snooze: SnoozeRequest,
    db: AsyncSession = Depends(get_db),
) -> CommandQueueItemResponse:
    """Snooze a queue item for a preset duration."""
    item = await db.get(CommandQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    now = datetime.utcnow()
    
    # Calculate snooze time
    if snooze.duration == SnoozeOption.ONE_HOUR:
        snooze_until = now + timedelta(hours=1)
    elif snooze.duration == SnoozeOption.FOUR_HOURS:
        snooze_until = now + timedelta(hours=4)
    elif snooze.duration == SnoozeOption.TOMORROW:
        # Tomorrow at 9am
        tomorrow = now + timedelta(days=1)
        snooze_until = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    elif snooze.duration == SnoozeOption.NEXT_WEEK:
        # Monday at 9am
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = now + timedelta(days=days_until_monday)
        snooze_until = next_monday.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        snooze_until = now + timedelta(hours=1)  # Default
    
    item.status = "snoozed"
    item.snoozed_until = snooze_until
    item.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(item)
    
    await log_event("queue_item_snoozed", {
        "item_id": item_id,
        "duration": snooze.duration.value,
        "until": snooze_until.isoformat(),
    })
    
    return _to_response(item)


@router.delete("/{item_id}", status_code=204)
async def delete_queue_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a queue item (admin only)."""
    item = await db.get(CommandQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    await db.delete(item)
    await db.commit()
    
    await log_event("queue_item_deleted", {"item_id": item_id})


# =============================================================================
# Legacy endpoints for backward compatibility
# =============================================================================

@router.post("/{item_id}/accept")
async def accept_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Legacy: Accept an item (same as complete)."""
    result = await complete_queue_item(item_id, db)
    return {"status": "ok", "item_id": item_id}


@router.post("/{item_id}/dismiss")
async def dismiss_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Legacy: Dismiss an item (same as skip)."""
    result = await skip_queue_item(item_id, db)
    return {"status": "ok", "item_id": item_id}
