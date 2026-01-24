"""Signals API routes for CaseyOS signal framework."""
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.models.signal import Signal, SignalSource
from src.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/signals", tags=["Signals"])


class SignalResponse(BaseModel):
    """Response model for a signal."""
    id: str
    source: str
    event_type: str
    payload: dict
    processed_at: Optional[datetime]
    recommendation_id: Optional[str]
    source_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SignalsListResponse(BaseModel):
    """Response model for signals list."""
    signals: list[SignalResponse]
    total: int
    limit: int
    offset: int


@router.get("", response_model=SignalsListResponse)
async def list_signals(
    db: AsyncSession = Depends(get_db),
    source: Optional[str] = Query(None, description="Filter by source (form, hubspot, gmail, manual)"),
    processed: Optional[bool] = Query(None, description="Filter by processed status"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> SignalsListResponse:
    """
    List signals with optional filtering.
    
    Returns recent signals, newest first.
    """
    # Build query
    query = select(Signal)
    count_query = select(func.count(Signal.id))
    
    # Apply filters
    if source:
        try:
            source_enum = SignalSource(source.lower())
            query = query.where(Signal.source == source_enum)
            count_query = count_query.where(Signal.source == source_enum)
        except ValueError:
            # Invalid source, return empty
            return SignalsListResponse(signals=[], total=0, limit=limit, offset=offset)
    
    if processed is not None:
        if processed:
            query = query.where(Signal.processed_at.isnot(None))
            count_query = count_query.where(Signal.processed_at.isnot(None))
        else:
            query = query.where(Signal.processed_at.is_(None))
            count_query = count_query.where(Signal.processed_at.is_(None))
    
    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    
    # Get paginated results
    query = query.order_by(Signal.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    signals = result.scalars().all()
    
    return SignalsListResponse(
        signals=[
            SignalResponse(
                id=s.id,
                source=s.source.value,
                event_type=s.event_type,
                payload=s.payload,
                processed_at=s.processed_at,
                recommendation_id=s.recommendation_id,
                source_id=s.source_id,
                created_at=s.created_at,
            )
            for s in signals
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(
    signal_id: str,
    db: AsyncSession = Depends(get_db),
) -> SignalResponse:
    """Get a specific signal by ID."""
    from fastapi import HTTPException
    
    result = await db.execute(select(Signal).where(Signal.id == signal_id))
    signal = result.scalar_one_or_none()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    return SignalResponse(
        id=signal.id,
        source=signal.source.value,
        event_type=signal.event_type,
        payload=signal.payload,
        processed_at=signal.processed_at,
        recommendation_id=signal.recommendation_id,
        source_id=signal.source_id,
        created_at=signal.created_at,
    )


@router.get("/stats/summary")
async def get_signal_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get signal statistics summary."""
    # Count by source
    source_counts = {}
    for source in SignalSource:
        count_query = select(func.count(Signal.id)).where(Signal.source == source)
        result = await db.execute(count_query)
        source_counts[source.value] = result.scalar() or 0
    
    # Count processed vs unprocessed
    processed_query = select(func.count(Signal.id)).where(Signal.processed_at.isnot(None))
    unprocessed_query = select(func.count(Signal.id)).where(Signal.processed_at.is_(None))
    
    processed_result = await db.execute(processed_query)
    unprocessed_result = await db.execute(unprocessed_query)
    
    processed_count = processed_result.scalar() or 0
    unprocessed_count = unprocessed_result.scalar() or 0
    
    return {
        "total": processed_count + unprocessed_count,
        "processed": processed_count,
        "unprocessed": unprocessed_count,
        "by_source": source_counts,
    }
