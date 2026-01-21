"""Bulk contact processing queue with rate limiting.

Handles processing of large contact lists (like CHAINge NA form submissions)
with configurable rate limits and priority scoring.
"""
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from collections import deque

from pydantic import BaseModel, Field

from src.logger import get_logger

logger = get_logger(__name__)


class ProcessingStatus(str, Enum):
    """Status of a contact in the processing queue."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # e.g., duplicate, missing data


class QueuedContact(BaseModel):
    """A contact in the processing queue."""
    id: str
    email: str
    first_name: str = ""
    last_name: str = ""
    company: str = ""
    job_title: str = ""
    source: str = "form_submission"
    form_id: Optional[str] = None
    priority_score: float = 0.0
    status: ProcessingStatus = ProcessingStatus.QUEUED
    queued_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    workflow_id: Optional[str] = None


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    daily_limit: int = 20
    weekly_limit: int = 100
    hourly_limit: int = 5
    min_delay_seconds: int = 30  # Minimum delay between processing


class BulkProcessingStats(BaseModel):
    """Statistics for bulk processing."""
    total_queued: int = 0
    total_processed: int = 0
    total_failed: int = 0
    total_skipped: int = 0
    processed_today: int = 0
    processed_this_week: int = 0
    remaining: int = 0
    is_paused: bool = False
    next_process_at: Optional[datetime] = None


class BulkProcessor:
    """Manages bulk contact processing with rate limiting."""
    
    def __init__(
        self,
        rate_config: RateLimitConfig = None,
        db=None,
    ):
        self.rate_config = rate_config or RateLimitConfig()
        self.db = db
        self.queue: deque[QueuedContact] = deque()
        self.is_paused = False
        self.is_running = False
        self._processing_task: Optional[asyncio.Task] = None
        
        # Track rate limits
        self._processed_today = 0
        self._processed_this_week = 0
        self._processed_this_hour = 0
        self._last_process_time: Optional[datetime] = None
        self._day_start: Optional[datetime] = None
        self._week_start: Optional[datetime] = None
        self._hour_start: Optional[datetime] = None
    
    async def initialize(self):
        """Initialize the processor and load state from database."""
        if self.db:
            # Load queue state from database
            await self._load_state()
        self._reset_rate_counters()
    
    def _reset_rate_counters(self):
        """Reset rate limit counters based on current time."""
        now = datetime.utcnow()
        
        # Reset daily counter
        if not self._day_start or now.date() != self._day_start.date():
            self._day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            self._processed_today = 0
        
        # Reset weekly counter (Monday = 0)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        if not self._week_start or week_start != self._week_start:
            self._week_start = week_start
            self._processed_this_week = 0
        
        # Reset hourly counter
        hour_start = now.replace(minute=0, second=0, microsecond=0)
        if not self._hour_start or hour_start != self._hour_start:
            self._hour_start = hour_start
            self._processed_this_hour = 0
    
    async def _load_state(self):
        """Load queue state from database."""
        try:
            # Load pending contacts from database
            rows = await self.db.fetch_all("""
                SELECT * FROM bulk_queue 
                WHERE status = 'queued' 
                ORDER BY priority_score DESC, queued_at ASC
            """)
            
            for row in rows:
                contact = QueuedContact(
                    id=row["id"],
                    email=row["email"],
                    first_name=row.get("first_name", ""),
                    last_name=row.get("last_name", ""),
                    company=row.get("company", ""),
                    job_title=row.get("job_title", ""),
                    priority_score=row.get("priority_score", 0.0),
                    status=ProcessingStatus(row["status"]),
                    queued_at=row["queued_at"],
                )
                self.queue.append(contact)
            
            logger.info(f"Loaded {len(self.queue)} contacts from database queue")
        except Exception as e:
            logger.warning(f"Could not load queue state: {e}")
    
    async def add_contacts(
        self,
        contacts: List[Dict[str, Any]],
        source: str = "form_submission",
        form_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add contacts to the processing queue.
        
        Args:
            contacts: List of contact dicts with email, name, company, etc.
            source: Source identifier
            form_id: Optional form ID for tracking
            
        Returns:
            Summary of added contacts
        """
        added = 0
        skipped = 0
        
        # Get existing emails to avoid duplicates
        existing_emails = {c.email.lower() for c in self.queue}
        
        for contact_data in contacts:
            email = contact_data.get("email", "").lower().strip()
            
            if not email or email in existing_emails:
                skipped += 1
                continue
            
            # Calculate priority score
            priority_score = self._calculate_priority(contact_data)
            
            contact = QueuedContact(
                id=f"bulk_{datetime.utcnow().timestamp()}_{added}",
                email=email,
                first_name=contact_data.get("first_name", ""),
                last_name=contact_data.get("last_name", ""),
                company=contact_data.get("company", ""),
                job_title=contact_data.get("job_title", ""),
                source=source,
                form_id=form_id,
                priority_score=priority_score,
            )
            
            self.queue.append(contact)
            existing_emails.add(email)
            added += 1
            
            # Persist to database
            if self.db:
                await self._save_contact(contact)
        
        # Sort queue by priority
        self._sort_queue()
        
        logger.info(f"Added {added} contacts to queue, skipped {skipped} duplicates")
        
        return {
            "added": added,
            "skipped": skipped,
            "total_queued": len(self.queue),
        }
    
    def _calculate_priority(self, contact: Dict[str, Any]) -> float:
        """Calculate priority score for a contact.
        
        Higher score = processed first.
        """
        score = 0.0
        job_title = contact.get("job_title", "").lower()
        company = contact.get("company", "")
        
        # Job title scoring
        executive_terms = ["vp", "vice president", "director", "head of", "chief", "cmo", "cro"]
        manager_terms = ["manager", "lead", "senior"]
        target_functions = ["demand", "field", "event", "marketing", "growth"]
        
        for term in executive_terms:
            if term in job_title:
                score += 30
                break
        
        for term in manager_terms:
            if term in job_title:
                score += 20
                break
        
        for term in target_functions:
            if term in job_title:
                score += 15
        
        # Company presence
        if company:
            score += 10
        
        return score
    
    def _sort_queue(self):
        """Sort queue by priority score (highest first)."""
        sorted_contacts = sorted(self.queue, key=lambda c: -c.priority_score)
        self.queue = deque(sorted_contacts)
    
    async def _save_contact(self, contact: QueuedContact):
        """Save contact to database."""
        try:
            await self.db.execute("""
                INSERT INTO bulk_queue (id, email, first_name, last_name, company, job_title,
                    source, form_id, priority_score, status, queued_at)
                VALUES (:id, :email, :first_name, :last_name, :company, :job_title,
                    :source, :form_id, :priority_score, :status, :queued_at)
                ON CONFLICT (email) DO UPDATE SET
                    priority_score = :priority_score,
                    status = :status
            """, {
                "id": contact.id,
                "email": contact.email,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "company": contact.company,
                "job_title": contact.job_title,
                "source": contact.source,
                "form_id": contact.form_id,
                "priority_score": contact.priority_score,
                "status": contact.status.value,
                "queued_at": contact.queued_at,
            })
        except Exception as e:
            logger.warning(f"Could not save contact to database: {e}")
    
    def can_process_now(self) -> tuple[bool, str]:
        """Check if we can process a contact right now.
        
        Returns:
            (can_process, reason)
        """
        self._reset_rate_counters()
        
        if self.is_paused:
            return False, "Processing is paused"
        
        if len(self.queue) == 0:
            return False, "Queue is empty"
        
        if self._processed_today >= self.rate_config.daily_limit:
            return False, f"Daily limit reached ({self.rate_config.daily_limit})"
        
        if self._processed_this_week >= self.rate_config.weekly_limit:
            return False, f"Weekly limit reached ({self.rate_config.weekly_limit})"
        
        if self._processed_this_hour >= self.rate_config.hourly_limit:
            return False, f"Hourly limit reached ({self.rate_config.hourly_limit})"
        
        # Check minimum delay
        if self._last_process_time:
            elapsed = (datetime.utcnow() - self._last_process_time).total_seconds()
            if elapsed < self.rate_config.min_delay_seconds:
                return False, f"Waiting {self.rate_config.min_delay_seconds - int(elapsed)}s before next"
        
        return True, "Ready to process"
    
    async def process_one(self, orchestrator) -> Optional[Dict[str, Any]]:
        """Process the next contact in queue.
        
        Args:
            orchestrator: ProspectingOrchestrator to handle the workflow
            
        Returns:
            Result of processing, or None if couldn't process
        """
        can_process, reason = self.can_process_now()
        if not can_process:
            logger.info(f"Cannot process: {reason}")
            return None
        
        if not self.queue:
            return None
        
        # Get highest priority contact
        contact = self.queue.popleft()
        contact.status = ProcessingStatus.PROCESSING
        
        try:
            # Create form submission payload
            form_data = {
                "email": contact.email,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "company": contact.company,
                "job_title": contact.job_title,
                "formId": contact.form_id or "bulk-import",
                "formSubmissionId": contact.id,
            }
            
            # Run through orchestrator
            result = await orchestrator.run_complete_workflow(form_data)
            
            # Update status
            contact.status = ProcessingStatus.COMPLETED
            contact.processed_at = datetime.utcnow()
            contact.workflow_id = result.get("workflow_id")
            
            # Update rate counters
            self._processed_today += 1
            self._processed_this_week += 1
            self._processed_this_hour += 1
            self._last_process_time = datetime.utcnow()
            
            # Update database
            if self.db:
                await self._update_contact_status(contact)
            
            logger.info(f"Processed contact {contact.email} (workflow: {contact.workflow_id})")
            
            return {
                "status": "success",
                "email": contact.email,
                "workflow_id": contact.workflow_id,
            }
            
        except Exception as e:
            logger.error(f"Failed to process {contact.email}: {e}")
            contact.status = ProcessingStatus.FAILED
            contact.error_message = str(e)
            contact.processed_at = datetime.utcnow()
            
            if self.db:
                await self._update_contact_status(contact)
            
            return {
                "status": "failed",
                "email": contact.email,
                "error": str(e),
            }
    
    async def _update_contact_status(self, contact: QueuedContact):
        """Update contact status in database."""
        try:
            await self.db.execute("""
                UPDATE bulk_queue SET
                    status = :status,
                    processed_at = :processed_at,
                    workflow_id = :workflow_id,
                    error_message = :error_message
                WHERE id = :id
            """, {
                "id": contact.id,
                "status": contact.status.value,
                "processed_at": contact.processed_at,
                "workflow_id": contact.workflow_id,
                "error_message": contact.error_message,
            })
        except Exception as e:
            logger.warning(f"Could not update contact status: {e}")
    
    def get_stats(self) -> BulkProcessingStats:
        """Get current processing statistics."""
        self._reset_rate_counters()
        
        # Calculate next process time
        next_process = None
        can_process, reason = self.can_process_now()
        if not can_process and self._last_process_time:
            wait_seconds = self.rate_config.min_delay_seconds
            next_process = self._last_process_time + timedelta(seconds=wait_seconds)
        
        return BulkProcessingStats(
            total_queued=len(self.queue),
            total_processed=self._processed_today,  # Simplified for now
            total_failed=0,  # Would need DB query
            total_skipped=0,
            processed_today=self._processed_today,
            processed_this_week=self._processed_this_week,
            remaining=len(self.queue),
            is_paused=self.is_paused,
            next_process_at=next_process,
        )
    
    def pause(self):
        """Pause processing."""
        self.is_paused = True
        logger.info("Bulk processing paused")
    
    def resume(self):
        """Resume processing."""
        self.is_paused = False
        logger.info("Bulk processing resumed")
    
    async def start_background_processing(self, orchestrator):
        """Start background processing loop."""
        if self.is_running:
            logger.warning("Background processing already running")
            return
        
        self.is_running = True
        
        async def process_loop():
            while self.is_running:
                try:
                    result = await self.process_one(orchestrator)
                    if result:
                        logger.info(f"Processed: {result}")
                    
                    # Wait before checking again
                    await asyncio.sleep(self.rate_config.min_delay_seconds)
                except Exception as e:
                    logger.error(f"Error in processing loop: {e}")
                    await asyncio.sleep(60)  # Wait longer on error
        
        self._processing_task = asyncio.create_task(process_loop())
        logger.info("Started background bulk processing")
    
    async def stop_background_processing(self):
        """Stop background processing."""
        self.is_running = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped background bulk processing")


# Global processor instance
_bulk_processor: Optional[BulkProcessor] = None


def get_bulk_processor() -> BulkProcessor:
    """Get or create the global bulk processor."""
    global _bulk_processor
    if _bulk_processor is None:
        _bulk_processor = BulkProcessor()
    return _bulk_processor


async def initialize_bulk_processor(db=None) -> BulkProcessor:
    """Initialize the bulk processor with database."""
    global _bulk_processor
    _bulk_processor = BulkProcessor(db=db)
    await _bulk_processor.initialize()
    return _bulk_processor
