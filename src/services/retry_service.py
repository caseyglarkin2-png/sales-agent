"""Retry service for failed operations.

Sprint 58: Resilience & Error Recovery
"""
from datetime import datetime
from typing import Optional, List, Any, Callable, Awaitable
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.retry_queue import RetryItem, RetryStatus, RetryItemType
from src.logger import get_logger

logger = get_logger(__name__)


class RetryService:
    """Service for managing retry queue."""
    
    def __init__(self, db: AsyncSession):
        """Initialize retry service."""
        self.db = db
    
    async def add_to_retry(
        self,
        item_type: str,
        payload: dict,
        original_id: Optional[str] = None,
        error: Optional[str] = None,
        error_type: Optional[str] = None,
        max_attempts: int = 3,
    ) -> RetryItem:
        """
        Add a failed operation to the retry queue.
        
        Args:
            item_type: Type of operation (email_send, hubspot_sync, etc.)
            payload: Data needed to retry the operation
            original_id: Reference to original item
            error: Error message from failure
            error_type: Type of error (e.g., "TimeoutError")
            max_attempts: Maximum retry attempts
        
        Returns:
            Created RetryItem
        """
        item = RetryItem(
            item_type=item_type,
            original_id=original_id,
            payload=payload,
            status=RetryStatus.PENDING.value,
            attempts=1,  # First attempt already failed
            max_attempts=max_attempts,
            last_error=error,
            error_type=error_type,
            next_retry_at=RetryItem().calculate_next_retry(),
        )
        
        # Calculate initial backoff
        item.next_retry_at = item.calculate_next_retry()
        
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        
        logger.info(
            "Added item to retry queue",
            item_id=str(item.id),
            item_type=item_type,
            original_id=original_id,
            next_retry_at=item.next_retry_at.isoformat(),
        )
        
        return item
    
    async def get_due_items(self, limit: int = 100) -> List[RetryItem]:
        """
        Get items due for retry.
        
        Args:
            limit: Maximum items to return
        
        Returns:
            List of RetryItems ready to retry
        """
        now = datetime.utcnow()
        
        stmt = (
            select(RetryItem)
            .where(
                and_(
                    RetryItem.status == RetryStatus.PENDING.value,
                    RetryItem.next_retry_at <= now,
                )
            )
            .order_by(RetryItem.next_retry_at)
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_item(self, item_id: UUID) -> Optional[RetryItem]:
        """Get a retry item by ID."""
        stmt = select(RetryItem).where(RetryItem.id == item_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_items_by_status(
        self,
        status: str,
        limit: int = 100,
    ) -> List[RetryItem]:
        """Get items by status."""
        stmt = (
            select(RetryItem)
            .where(RetryItem.status == status)
            .order_by(RetryItem.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_all_items(self, limit: int = 100) -> List[RetryItem]:
        """Get all retry items, most recent first."""
        stmt = (
            select(RetryItem)
            .order_by(RetryItem.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def process_item(
        self,
        item: RetryItem,
        handler: Callable[[dict], Awaitable[bool]],
    ) -> bool:
        """
        Process a retry item.
        
        Args:
            item: RetryItem to process
            handler: Async function that takes payload and returns True on success
        
        Returns:
            True if succeeded, False if failed
        """
        item.mark_retrying()
        await self.db.commit()
        
        try:
            success = await handler(item.payload)
            
            if success:
                item.mark_success()
                logger.info(
                    "Retry succeeded",
                    item_id=str(item.id),
                    item_type=item.item_type,
                    attempts=item.attempts,
                )
            else:
                item.mark_failed("Handler returned False", "HandlerError")
                logger.warning(
                    "Retry failed",
                    item_id=str(item.id),
                    item_type=item.item_type,
                    attempts=item.attempts,
                )
            
            await self.db.commit()
            return success
            
        except Exception as e:
            item.mark_failed(str(e), type(e).__name__)
            await self.db.commit()
            
            logger.error(
                "Retry failed with exception",
                item_id=str(item.id),
                item_type=item.item_type,
                error=str(e),
                attempts=item.attempts,
            )
            return False
    
    async def abandon_item(self, item_id: UUID) -> Optional[RetryItem]:
        """Manually abandon a retry item."""
        item = await self.get_item(item_id)
        if item:
            item.mark_abandoned()
            await self.db.commit()
            logger.info("Retry item abandoned", item_id=str(item_id))
        return item
    
    async def retry_now(self, item_id: UUID) -> Optional[RetryItem]:
        """Force immediate retry by resetting next_retry_at."""
        item = await self.get_item(item_id)
        if item and item.can_retry():
            item.next_retry_at = datetime.utcnow()
            item.status = RetryStatus.PENDING.value
            await self.db.commit()
            logger.info("Retry scheduled immediately", item_id=str(item_id))
        return item
    
    async def get_stats(self) -> dict:
        """Get retry queue statistics."""
        from sqlalchemy import func
        
        # Count by status
        stmt = (
            select(RetryItem.status, func.count(RetryItem.id))
            .group_by(RetryItem.status)
        )
        result = await self.db.execute(stmt)
        status_counts = {row[0]: row[1] for row in result}
        
        # Count by type
        stmt = (
            select(RetryItem.item_type, func.count(RetryItem.id))
            .where(RetryItem.status == RetryStatus.PENDING.value)
            .group_by(RetryItem.item_type)
        )
        result = await self.db.execute(stmt)
        type_counts = {row[0]: row[1] for row in result}
        
        return {
            "by_status": status_counts,
            "pending_by_type": type_counts,
            "total_pending": status_counts.get(RetryStatus.PENDING.value, 0),
            "total_failed": status_counts.get(RetryStatus.FAILED.value, 0),
            "total_succeeded": status_counts.get(RetryStatus.SUCCEEDED.value, 0),
        }
