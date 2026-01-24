"""Signal service for creating and processing signals."""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.signal import Signal, SignalSource
from src.models.command_queue import CommandQueueItem
from src.services.signal_processors.form import FormSubmissionSignalProcessor
from src.logger import get_logger
from src.telemetry import log_event

logger = get_logger(__name__)


class SignalService:
    """Service for managing signals and triggering processors."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._processors = [
            FormSubmissionSignalProcessor(),
        ]

    async def create_signal(
        self,
        source: SignalSource,
        event_type: str,
        payload: Dict[str, Any],
        source_id: Optional[str] = None,
    ) -> Signal:
        """
        Create and persist a new signal.
        
        Args:
            source: The signal source (FORM, HUBSPOT, GMAIL, MANUAL)
            event_type: Type of event (e.g. 'form_submitted')
            payload: Raw event data
            source_id: Optional external ID (e.g. HubSpot contact ID)
            
        Returns:
            The created Signal instance
        """
        signal = Signal(
            id=str(uuid4()),
            source=source,
            event_type=event_type,
            payload=payload,
            source_id=source_id,
            created_at=datetime.utcnow(),
        )
        
        self.db.add(signal)
        await self.db.flush()  # Get ID without committing
        
        await log_event(
            "signal_received",
            signal_id=signal.id,
            source=source.value,
            event_type=event_type,
        )
        
        logger.info(
            f"Signal created: {signal.id}",
            source=source.value,
            event_type=event_type,
            source_id=source_id,
        )
        
        return signal

    async def process_signal(self, signal: Signal) -> Optional[CommandQueueItem]:
        """
        Process a signal and create a recommendation if appropriate.
        
        Args:
            signal: The signal to process
            
        Returns:
            CommandQueueItem if recommendation created, None otherwise
        """
        for processor in self._processors:
            if processor.can_handle(signal):
                logger.info(
                    f"Processing signal with {processor.source_name} processor",
                    signal_id=signal.id,
                )
                
                try:
                    item = await processor.process(signal)
                    
                    if item:
                        # Persist the command queue item
                        self.db.add(item)
                        
                        # Mark signal as processed
                        signal.processed_at = datetime.utcnow()
                        signal.recommendation_id = item.id
                        
                        await self.db.flush()
                        
                        await log_event(
                            "recommendation_generated",
                            signal_id=signal.id,
                            recommendation_id=item.id,
                            action_type=item.action_type,
                        )
                        
                        logger.info(
                            f"Recommendation created from signal",
                            signal_id=signal.id,
                            recommendation_id=item.id,
                            action_type=item.action_type,
                        )
                        
                        return item
                    else:
                        # Signal processed but no recommendation needed
                        signal.processed_at = datetime.utcnow()
                        await self.db.flush()
                        
                        await log_event(
                            "signal_processed",
                            signal_id=signal.id,
                            recommendation_generated=False,
                        )
                        
                except Exception as e:
                    logger.error(
                        f"Error processing signal: {e}",
                        signal_id=signal.id,
                        processor=processor.source_name,
                        exc_info=True,
                    )
                    raise
        
        logger.debug(f"No processor matched signal {signal.id}")
        return None

    async def create_and_process(
        self,
        source: SignalSource,
        event_type: str,
        payload: Dict[str, Any],
        source_id: Optional[str] = None,
    ) -> tuple[Signal, Optional[CommandQueueItem]]:
        """
        Create a signal and immediately process it.
        
        Convenience method for synchronous signal handling.
        
        Returns:
            Tuple of (Signal, Optional[CommandQueueItem])
        """
        signal = await self.create_signal(source, event_type, payload, source_id)
        item = await self.process_signal(signal)
        return signal, item

    async def get_unprocessed_signals(
        self,
        source: Optional[SignalSource] = None,
        limit: int = 100,
    ) -> list[Signal]:
        """
        Get unprocessed signals for batch processing.
        
        Args:
            source: Optional filter by source
            limit: Max signals to return
            
        Returns:
            List of unprocessed signals
        """
        query = select(Signal).where(Signal.processed_at.is_(None))
        
        if source:
            query = query.where(Signal.source == source)
        
        query = query.order_by(Signal.created_at.asc()).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
