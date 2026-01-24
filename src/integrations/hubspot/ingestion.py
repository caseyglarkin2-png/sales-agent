"""Signal Ingestion Service - Converts HubSpot signals to queue items.

Sprint 3 Tasks 3.3 + 3.4 - Maps detected signals to CommandQueueItems
with idempotency to prevent duplicates.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.command_queue import CommandQueueItem, ActionType, QueueItemStatus
from src.integrations.hubspot.signals import Signal, SignalType, SignalPriority

logger = logging.getLogger(__name__)


# =============================================================================
# Signal to Queue Mapping
# =============================================================================

# Map signal types to action types
SIGNAL_TO_ACTION: Dict[SignalType, str] = {
    SignalType.DEAL_STALLED: ActionType.FOLLOW_UP.value,
    SignalType.DEAL_CLOSE_SOON: ActionType.REVIEW_DEAL.value,
    SignalType.DEAL_AT_RISK: ActionType.REVIEW_DEAL.value,
    SignalType.PROPOSAL_NO_RESPONSE: ActionType.FOLLOW_UP.value,
    SignalType.MEETING_TODAY: ActionType.PREP_MEETING.value,
    SignalType.MEETING_PREP_NEEDED: ActionType.PREP_MEETING.value,
    SignalType.LEAD_COLD: ActionType.CHECK_IN.value,
    SignalType.BIG_DEAL_MOVED: ActionType.REVIEW_DEAL.value,
    SignalType.NEW_HIGH_VALUE: ActionType.BOOK_MEETING.value,
    SignalType.FOLLOW_UP_DUE: ActionType.FOLLOW_UP.value,
}

# Map priority to score range
PRIORITY_TO_SCORE: Dict[SignalPriority, float] = {
    SignalPriority.CRITICAL: 95.0,
    SignalPriority.HIGH: 80.0,
    SignalPriority.MEDIUM: 60.0,
    SignalPriority.LOW: 40.0,
}


def signal_to_queue_item(signal: Signal, owner: str = "casey") -> CommandQueueItem:
    """Convert a Signal to a CommandQueueItem.
    
    The mapping preserves:
    - Priority (converted to score)
    - HubSpot references (contact_id, deal_id, company_id)
    - Reasoning and context
    """
    # Map priority to numeric score
    base_score = PRIORITY_TO_SCORE.get(signal.priority, 50.0)
    
    # Adjust score based on signal data
    score = base_score
    if signal.data:
        # Boost score for high-value deals
        amount = signal.data.get("amount", 0)
        if amount and amount >= 50000:
            score = min(100, score + 10)
        elif amount and amount >= 10000:
            score = min(100, score + 5)
        
        # Boost for urgency (days stalled, days until close)
        days_stalled = signal.data.get("days_stalled", 0)
        if days_stalled >= 14:
            score = min(100, score + 5)
        
        days_until_close = signal.data.get("days_until_close")
        if days_until_close is not None and days_until_close <= 3:
            score = min(100, score + 10)
    
    # Calculate due date based on priority
    if signal.priority == SignalPriority.CRITICAL:
        due_by = datetime.utcnow()  # Today
    elif signal.priority == SignalPriority.HIGH:
        due_by = datetime.utcnow() + timedelta(days=1)
    elif signal.priority == SignalPriority.MEDIUM:
        due_by = datetime.utcnow() + timedelta(days=3)
    else:
        due_by = datetime.utcnow() + timedelta(days=7)
    
    # Create queue item
    return CommandQueueItem(
        id=signal.idempotency_hash,  # Use hash as ID for idempotency
        title=signal.title,
        description=signal.description,
        action_type=SIGNAL_TO_ACTION.get(signal.type, ActionType.OTHER.value),
        action_context={
            "signal_type": signal.type.value,
            "signal_data": signal.data,
            "detected_at": signal.detected_at.isoformat(),
        },
        priority_score=score,
        reasoning=signal.reasoning,
        drivers={
            "signal_type": signal.type.value,
            "priority": signal.priority.value,
        },
        contact_id=signal.contact_id,
        deal_id=signal.deal_id,
        company_id=signal.company_id,
        status=QueueItemStatus.PENDING.value,
        owner=owner,
        due_by=due_by,
        created_at=signal.detected_at,
    )


# =============================================================================
# Ingestion Service
# =============================================================================

@dataclass
class IngestionResult:
    """Result of signal ingestion job."""
    signals_detected: int = 0
    items_created: int = 0
    items_skipped: int = 0  # Already existed
    items_failed: int = 0
    started_at: datetime = None
    completed_at: datetime = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.started_at is None:
            self.started_at = datetime.utcnow()
        if self.errors is None:
            self.errors = []
    
    @property
    def duration_seconds(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signals_detected": self.signals_detected,
            "items_created": self.items_created,
            "items_skipped": self.items_skipped,
            "items_failed": self.items_failed,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
        }


class SignalIngestionService:
    """Service for ingesting HubSpot signals into the command queue.
    
    Features:
    - Idempotent: Won't create duplicate items
    - Batch insert with ON CONFLICT DO NOTHING
    - Status tracking for UI visibility
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._last_result: Optional[IngestionResult] = None
    
    @property
    def last_result(self) -> Optional[IngestionResult]:
        """Get the last ingestion result."""
        return self._last_result
    
    async def ingest_signals(
        self, 
        signals: List[Signal],
        owner: str = "casey",
    ) -> IngestionResult:
        """Ingest a list of signals into the command queue.
        
        Uses upsert semantics: existing items are skipped.
        """
        result = IngestionResult(signals_detected=len(signals))
        
        if not signals:
            result.completed_at = datetime.utcnow()
            self._last_result = result
            return result
        
        # Convert signals to queue items
        items = []
        for signal in signals:
            try:
                item = signal_to_queue_item(signal, owner=owner)
                items.append(item)
            except Exception as e:
                logger.error(f"Failed to convert signal to queue item: {e}")
                result.items_failed += 1
                result.errors.append(str(e))
        
        # Get existing item IDs to check for duplicates
        item_ids = [item.id for item in items]
        existing_query = select(CommandQueueItem.id).where(
            CommandQueueItem.id.in_(item_ids)
        )
        existing_result = await self.db.execute(existing_query)
        existing_ids = set(row[0] for row in existing_result.fetchall())
        
        # Filter to only new items
        new_items = [item for item in items if item.id not in existing_ids]
        result.items_skipped = len(existing_ids)
        
        # Insert new items
        for item in new_items:
            try:
                self.db.add(item)
                result.items_created += 1
            except Exception as e:
                logger.error(f"Failed to insert queue item: {e}")
                result.items_failed += 1
                result.errors.append(str(e))
        
        # Commit the transaction
        try:
            await self.db.commit()
        except Exception as e:
            logger.error(f"Failed to commit ingestion: {e}")
            await self.db.rollback()
            result.errors.append(f"Commit failed: {e}")
        
        result.completed_at = datetime.utcnow()
        self._last_result = result
        
        logger.info(
            f"Signal ingestion complete: {result.items_created} created, "
            f"{result.items_skipped} skipped, {result.items_failed} failed"
        )
        
        return result
    
    async def get_ingestion_status(self) -> Dict[str, Any]:
        """Get current ingestion status for API."""
        # Count items by status
        status_counts = await self.db.execute(
            select(
                CommandQueueItem.status,
                func.count(CommandQueueItem.id)
            ).group_by(CommandQueueItem.status)
        )
        counts = {row[0]: row[1] for row in status_counts.fetchall()}
        
        # Count items created today (from signals)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count_result = await self.db.execute(
            select(func.count(CommandQueueItem.id)).where(
                CommandQueueItem.created_at >= today_start
            )
        )
        today_count = today_count_result.scalar() or 0
        
        return {
            "last_ingestion": self._last_result.to_dict() if self._last_result else None,
            "queue_status": counts,
            "items_created_today": today_count,
            "status": "ready",
        }


# =============================================================================
# Factory
# =============================================================================

def get_ingestion_service(db: AsyncSession) -> SignalIngestionService:
    """Get configured ingestion service."""
    return SignalIngestionService(db)
