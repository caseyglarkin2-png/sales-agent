"""Retry queue API routes.

Sprint 58: Resilience & Error Recovery
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.services.retry_service import RetryService
from src.models.retry_queue import RetryStatus, RetryItemType
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/retry-queue", tags=["Retry Queue"])


# Pydantic models
class RetryItemResponse(BaseModel):
    """Response model for retry item."""
    id: str
    item_type: str
    original_id: Optional[str] = None
    status: str
    attempts: int
    max_attempts: int
    next_retry_at: Optional[datetime] = None
    last_error: Optional[str] = None
    error_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    can_retry: bool
    
    class Config:
        from_attributes = True


class RetryStatsResponse(BaseModel):
    """Response model for retry queue stats."""
    by_status: dict
    pending_by_type: dict
    total_pending: int
    total_failed: int
    total_succeeded: int


class RetryItemCreate(BaseModel):
    """Request model to add item to retry queue."""
    item_type: str
    payload: dict
    original_id: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    max_attempts: int = 3


@router.get("", response_model=List[RetryItemResponse])
async def list_retry_items(
    status: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List all retry queue items, optionally filtered by status."""
    service = RetryService(db)
    
    if status:
        items = await service.get_items_by_status(status, limit)
    else:
        items = await service.get_all_items(limit)
    
    return [
        RetryItemResponse(
            id=str(item.id),
            item_type=item.item_type,
            original_id=item.original_id,
            status=item.status,
            attempts=item.attempts,
            max_attempts=item.max_attempts,
            next_retry_at=item.next_retry_at,
            last_error=item.last_error,
            error_type=item.error_type,
            created_at=item.created_at,
            updated_at=item.updated_at,
            completed_at=item.completed_at,
            can_retry=item.can_retry(),
        )
        for item in items
    ]


@router.get("/stats", response_model=RetryStatsResponse)
async def get_retry_stats(db: AsyncSession = Depends(get_db)):
    """Get retry queue statistics."""
    service = RetryService(db)
    stats = await service.get_stats()
    return RetryStatsResponse(**stats)


@router.get("/due", response_model=List[RetryItemResponse])
async def get_due_items(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get items due for retry."""
    service = RetryService(db)
    items = await service.get_due_items(limit)
    
    return [
        RetryItemResponse(
            id=str(item.id),
            item_type=item.item_type,
            original_id=item.original_id,
            status=item.status,
            attempts=item.attempts,
            max_attempts=item.max_attempts,
            next_retry_at=item.next_retry_at,
            last_error=item.last_error,
            error_type=item.error_type,
            created_at=item.created_at,
            updated_at=item.updated_at,
            completed_at=item.completed_at,
            can_retry=item.can_retry(),
        )
        for item in items
    ]


@router.post("", response_model=RetryItemResponse)
async def add_to_retry_queue(
    item: RetryItemCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add an item to the retry queue."""
    service = RetryService(db)
    
    retry_item = await service.add_to_retry(
        item_type=item.item_type,
        payload=item.payload,
        original_id=item.original_id,
        error=item.error,
        error_type=item.error_type,
        max_attempts=item.max_attempts,
    )
    
    return RetryItemResponse(
        id=str(retry_item.id),
        item_type=retry_item.item_type,
        original_id=retry_item.original_id,
        status=retry_item.status,
        attempts=retry_item.attempts,
        max_attempts=retry_item.max_attempts,
        next_retry_at=retry_item.next_retry_at,
        last_error=retry_item.last_error,
        error_type=retry_item.error_type,
        created_at=retry_item.created_at,
        updated_at=retry_item.updated_at,
        completed_at=retry_item.completed_at,
        can_retry=retry_item.can_retry(),
    )


@router.get("/{item_id}", response_model=RetryItemResponse)
async def get_retry_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific retry item."""
    service = RetryService(db)
    item = await service.get_item(item_id)
    
    if not item:
        raise HTTPException(status_code=404, detail="Retry item not found")
    
    return RetryItemResponse(
        id=str(item.id),
        item_type=item.item_type,
        original_id=item.original_id,
        status=item.status,
        attempts=item.attempts,
        max_attempts=item.max_attempts,
        next_retry_at=item.next_retry_at,
        last_error=item.last_error,
        error_type=item.error_type,
        created_at=item.created_at,
        updated_at=item.updated_at,
        completed_at=item.completed_at,
        can_retry=item.can_retry(),
    )


@router.post("/{item_id}/retry-now")
async def retry_item_now(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Force immediate retry of an item."""
    service = RetryService(db)
    item = await service.retry_now(item_id)
    
    if not item:
        raise HTTPException(status_code=404, detail="Retry item not found")
    
    return {"message": "Retry scheduled", "item_id": str(item_id)}


@router.post("/{item_id}/abandon")
async def abandon_retry_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Abandon a retry item."""
    service = RetryService(db)
    item = await service.abandon_item(item_id)
    
    if not item:
        raise HTTPException(status_code=404, detail="Retry item not found")
    
    return {"message": "Item abandoned", "item_id": str(item_id)}
