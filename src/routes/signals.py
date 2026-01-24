"""Signals API routes for CaseyOS signal framework."""
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, text
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


@router.get("/health")
async def signals_health(db: AsyncSession = Depends(get_db)) -> dict:
    """Check signals table health."""
    try:
        # Check if table exists by running a simple count
        result = await db.execute(text("SELECT COUNT(*) FROM signals"))
        count = result.scalar()
        return {"status": "ok", "table_exists": True, "count": count}
    except Exception as e:
        logger.error(f"Signals health check failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


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
    try:
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
    except Exception as e:
        logger.error(f"Error listing signals: {e}", exc_info=True)
        raise


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


@router.post("/twitter/poll")
async def poll_twitter_signals(
    db: AsyncSession = Depends(get_db),
    user_id: str = Query(..., description="User ID to poll Twitter feed for"),
    count: int = Query(50, ge=1, le=200, description="Number of tweets to fetch"),
    min_relevance: float = Query(0.3, ge=0.0, le=1.0, description="Minimum relevance score"),
) -> dict[str, Any]:
    """
    Poll Twitter home timeline for GTM-relevant signals.
    
    Requires user to have completed OAuth flow via /auth/twitter/login.
    
    Returns signals that were created and optionally processed into queue items.
    """
    from src.signals.providers.twitter_home import TwitterHomeProvider, get_twitter_home_provider
    from src.services.signal_processors.social import SocialSignalProcessor
    from src.models.signal import Signal as SignalModel, SignalSource, compute_payload_hash
    
    try:
        # Get the Twitter home provider
        provider = get_twitter_home_provider()
        
        # Check if user is authenticated
        tokens = await provider.get_user_tokens(user_id)
        if not tokens:
            raise HTTPException(
                status_code=401,
                detail=f"User {user_id} not authenticated. Complete OAuth flow at /auth/twitter/login"
            )
        
        # Poll for signals
        since = datetime.utcnow() - timedelta(hours=24)
        signals = await provider.poll_signals(since=since, user_id=user_id)
        
        # Filter by relevance
        relevant_signals = [s for s in signals if s.payload.get("relevance_score", 0) >= min_relevance]
        
        # Store signals and process them
        created_signals = []
        created_queue_items = []
        processor = SocialSignalProcessor()
        
        for signal in relevant_signals[:count]:
            # Create DB model from signal dataclass
            payload_hash = compute_payload_hash(signal.payload)
            
            # Check for duplicates
            existing = await db.execute(
                select(SignalModel).where(SignalModel.payload_hash == payload_hash)
            )
            if existing.scalar_one_or_none():
                logger.debug(f"Skipping duplicate signal: {payload_hash[:16]}")
                continue
            
            # Create DB signal
            db_signal = SignalModel(
                id=signal.id,
                source=SignalSource.TWITTER,
                event_type=signal.event_type,
                payload=signal.payload,
                source_id=signal.source_id,
                payload_hash=payload_hash,
                created_at=datetime.utcnow(),
            )
            db.add(db_signal)
            created_signals.append(db_signal)
            
            # Process into command queue item
            queue_item = await processor.process(db_signal)
            if queue_item:
                db.add(queue_item)
                db_signal.recommendation_id = queue_item.id
                db_signal.processed_at = datetime.utcnow()
                created_queue_items.append(queue_item)
        
        await db.commit()
        
        return {
            "status": "success",
            "user_id": user_id,
            "signals_found": len(signals),
            "signals_relevant": len(relevant_signals),
            "signals_created": len(created_signals),
            "queue_items_created": len(created_queue_items),
            "min_relevance": min_relevance,
            "sample_signals": [
                {
                    "id": s.id,
                    "event_type": s.event_type,
                    "relevance": s.payload.get("relevance_score", 0),
                    "author": s.payload.get("author_handle", ""),
                    "text": s.payload.get("text", "")[:100],
                }
                for s in created_signals[:5]
            ],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error polling Twitter signals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to poll Twitter: {str(e)}")
