"""
Content Memory Models.

These models store ingested content from external sources (YouTube, Drive, Slack)
to power the Content Engine and Deep Research capabilities.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

from sqlalchemy import Column, String, DateTime, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID

from src.db import Base, SafeJSON

class ContentSourceType(str, Enum):
    """Supported content sources."""
    YOUTUBE = "youtube"
    DRIVE = "drive"
    SLACK = "slack"
    MANUAL = "manual"

class ContentMemory(Base):
    """
    Store for ingested content.
    
    Acts as the "Long Term Knowledge" for the agents, distinct from
    conversational memory.
    """
    __tablename__ = "content_memory"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Source identification
    source_type = Column(String(50), nullable=False)  # usage of ContentSourceType values
    source_id = Column(String(255), nullable=False)   # External ID (e.g., Video ID)
    source_url = Column(String(1000), nullable=True)
    
    # Content
    title = Column(String(1000), nullable=False)
    content = Column(Text, nullable=False)            # Full transcript or text
    summary = Column(Text, nullable=True)             # Auto-generated summary
    
    # Metadata & Search
    content_metadata = Column("metadata", SafeJSON, default=dict) # e.g. author, publish_date
    embedding = Column(SafeJSON, nullable=True)          # Vector embedding
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)    # When analysis/embedding finished
    
    def __repr__(self):
        return f"<ContentMemory(id={self.id}, title={self.title}, source={self.source_type})>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "title": self.title,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }
