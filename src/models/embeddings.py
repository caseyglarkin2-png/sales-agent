"""SQLAlchemy models for embeddings."""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import ARRAY

from src.db import Base


class MessageEmbedding(Base):
    """Message embedding model for similarity search."""

    __tablename__ = "message_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), unique=True, nullable=False)
    embedding = Column(ARRAY(float), nullable=False)  # VECTOR(1536)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("message_id", name="uq_message_embeddings_message_id"),
        Index("ix_message_embeddings_created_at", "created_at"),
    )


class DocumentEmbedding(Base):
    """Document chunk embedding model for similarity search."""

    __tablename__ = "document_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True)
    drive_file_id = Column(String(255), nullable=False, index=True)
    chunk_index = Column(String(50), nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(ARRAY(float), nullable=False)  # VECTOR(1536)
    metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("drive_file_id", "chunk_index", name="uq_doc_embeddings_file_chunk"),
        Index("ix_document_embeddings_drive_file_id", "drive_file_id"),
        Index("ix_document_embeddings_created_at", "created_at"),
    )
