"""
Training sample model for voice training data ingestion.

Supports multiple input sources: Drive, HubSpot, YouTube, direct upload, share links.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.sql import func

from src.db import Base


class TrainingSampleSource(str, Enum):
    """Source types for training samples."""
    DRIVE = "drive"              # Google Drive file
    HUBSPOT = "hubspot"          # HubSpot email thread, note, or call transcript
    YOUTUBE = "youtube"          # YouTube video transcript
    UPLOAD = "upload"            # Direct file upload
    LINK = "link"                # Shareable link (Dropbox, OneDrive, etc.)


class TrainingSample(Base):
    """
    Training sample for voice profile learning.
    
    Stores content extracted from various sources (Drive, HubSpot, YouTube, uploads)
    for training user's writing style and voice.
    """
    __tablename__ = "training_samples"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    
    # Source metadata
    source_type = Column(String(50), nullable=False, index=True)
    source_id = Column(String(255), nullable=True, comment="Drive file ID, HubSpot object ID, YouTube video ID")
    source_url = Column(Text, nullable=True)
    title = Column(String(500), nullable=True)
    
    # Extracted content
    content = Column(Text, nullable=False)
    extracted_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Processing status
    embedding_generated = Column(Boolean, nullable=False, default=False)
    voice_profile_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)
    
    # Additional metadata (source-specific fields)
    # Note: 'metadata' is reserved by SQLAlchemy, so we use 'source_metadata'
    source_metadata = Column(JSONB, nullable=True, comment="Source-specific metadata (file type, video duration, etc.)")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<TrainingSample id={self.id} source={self.source_type} title='{self.title}'>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "title": self.title,
            "content_preview": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "content_length": len(self.content),
            "extracted_at": self.extracted_at.isoformat() if self.extracted_at else None,
            "embedding_generated": self.embedding_generated,
            "voice_profile_id": str(self.voice_profile_id) if self.voice_profile_id else None,
            "source_metadata": self.source_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
