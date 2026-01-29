"""Retry queue model for failed operations.

Sprint 58: Resilience & Error Recovery
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Any
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Integer, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from src.db import Base, SafeJSON


class RetryStatus(str, Enum):
    """Status of retry item."""
    PENDING = "pending"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"  # Permanent failure after max retries
    ABANDONED = "abandoned"  # Manually abandoned


class RetryItemType(str, Enum):
    """Type of operation being retried."""
    EMAIL_SEND = "email_send"
    HUBSPOT_SYNC = "hubspot_sync"
    GMAIL_SYNC = "gmail_sync"
    WEBHOOK = "webhook"
    AGENT_EXECUTION = "agent_execution"
    OTHER = "other"


class RetryItem(Base):
    """
    Retry queue item for failed operations.
    
    Uses exponential backoff: 1min, 5min, 30min
    Max 3 retries before permanent failure.
    """
    __tablename__ = "retry_queue"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # What we're retrying
    item_type = Column(String(50), nullable=False, index=True)
    original_id = Column(String(255), nullable=True, index=True)  # Reference to original item
    
    # Payload to retry
    payload = Column(SafeJSON, nullable=False, default=dict)
    
    # Status tracking
    status = Column(String(20), nullable=False, default=RetryStatus.PENDING.value, index=True)
    
    # Retry tracking
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    next_retry_at = Column(DateTime, nullable=True, index=True)
    
    # Error tracking
    last_error = Column(Text, nullable=True)
    error_type = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<RetryItem {self.id} type={self.item_type} status={self.status} attempts={self.attempts}>"
    
    def calculate_next_retry(self) -> datetime:
        """Calculate next retry time with exponential backoff."""
        # Backoff: 1min, 5min, 30min
        backoff_minutes = [1, 5, 30]
        idx = min(self.attempts, len(backoff_minutes) - 1)
        delay = timedelta(minutes=backoff_minutes[idx])
        return datetime.utcnow() + delay
    
    def can_retry(self) -> bool:
        """Check if item can be retried."""
        return (
            self.status in (RetryStatus.PENDING.value, RetryStatus.RETRYING.value)
            and self.attempts < self.max_attempts
        )
    
    def mark_retrying(self) -> None:
        """Mark as currently being retried."""
        self.status = RetryStatus.RETRYING.value
        self.attempts += 1
        self.updated_at = datetime.utcnow()
    
    def mark_success(self) -> None:
        """Mark as successfully completed."""
        self.status = RetryStatus.SUCCEEDED.value
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_failed(self, error: str, error_type: str = None) -> None:
        """Mark attempt as failed, schedule next retry or permanent failure."""
        self.last_error = error
        self.error_type = error_type
        self.updated_at = datetime.utcnow()
        
        if self.attempts >= self.max_attempts:
            self.status = RetryStatus.FAILED.value
            self.completed_at = datetime.utcnow()
        else:
            self.status = RetryStatus.PENDING.value
            self.next_retry_at = self.calculate_next_retry()
    
    def mark_abandoned(self) -> None:
        """Manually abandon retry attempts."""
        self.status = RetryStatus.ABANDONED.value
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
