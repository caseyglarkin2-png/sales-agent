"""SQLAlchemy models for embeddings."""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import ARRAY

from src.db import Base, SafeJSON


class ArrayType(TypeDecorator):
    """ARRAY type that works with both PostgreSQL (ARRAY) and SQLite (JSON)."""
    impl = JSON
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(float))
        return dialect.type_descriptor(JSON())


class MessageEmbedding(Base):
    """Message embedding model for similarity search."""

    __tablename__ = "message_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), unique=True, nullable=False)
    embedding = Column(ArrayType, nullable=False)  # VECTOR(1536)
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
    embedding = Column(ArrayType, nullable=False)  # VECTOR(1536)
    metadata_ = Column("metadata", SafeJSON, nullable=True) # avoiding overlapping with Base.metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("drive_file_id", "chunk_index", name="uq_doc_embeddings_file_chunk"),
        Index("ix_document_embeddings_drive_file_id", "drive_file_id"),
        Index("ix_document_embeddings_created_at", "created_at"),
    )
