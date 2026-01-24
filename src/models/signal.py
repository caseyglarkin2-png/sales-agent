"""Signal models for CaseyOS signal ingestion framework."""
import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


class SignalSource(str, Enum):
    """Source of the signal."""
    FORM = "form"
    HUBSPOT = "hubspot"
    GMAIL = "gmail"
    MANUAL = "manual"
    TWITTER = "twitter"  # Twitter/X social signals


def compute_payload_hash(payload: Dict[str, Any]) -> str:
    """
    Compute a hash of the payload for deduplication.
    
    Uses SHA-256 of the JSON-serialized payload.
    """
    # Sort keys for consistent hashing
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(payload_str.encode()).hexdigest()


class Signal(Base):
    """
    Represents a detected signal from various sources.
    
    Signals are raw events that may generate recommendations in the command queue.
    Examples: form submission, HubSpot deal change, Gmail reply received.
    """

    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    
    source: Mapped[SignalSource] = mapped_column(
        SQLEnum(
            SignalSource, 
            name="signal_source_enum",
            values_callable=lambda enum: [e.value for e in enum],
        ),
        nullable=False,
        index=True
    )
    
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Specific event type, e.g. 'form_submitted', 'deal_stage_changed', 'reply_received'"
    )
    
    payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Raw event data from the source"
    )
    
    # Processing state
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        index=True,
        comment="When signal was processed into a recommendation (null if pending)"
    )
    
    recommendation_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        default=None,
        index=True,
        comment="FK to command_queue_items if a recommendation was generated"
    )
    
    # Metadata
    source_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True,
        comment="External ID from source system (e.g. HubSpot contact ID, Gmail thread ID)"
    )
    
    payload_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="SHA-256 hash of payload for deduplication"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    def __repr__(self) -> str:
        return f"<Signal {self.id[:8]} source={self.source.value} event={self.event_type}>"

    @property
    def is_processed(self) -> bool:
        """Check if signal has been processed."""
        return self.processed_at is not None
