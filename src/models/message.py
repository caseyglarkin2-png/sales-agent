"""SQLAlchemy models for messages and threads."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, String, Text, UniqueConstraint, JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import ARRAY

from src.db import Base


class JSONType(TypeDecorator):
    """JSON type that works with both PostgreSQL (JSONB) and SQLite (JSON)."""
    impl = JSON
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class ArrayType(TypeDecorator):
    """ARRAY type that works with both PostgreSQL (ARRAY) and SQLite (JSON)."""
    impl = JSON
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(float))
        return dialect.type_descriptor(JSON())


class Message(Base):
    """Gmail message model."""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True)
    gmail_message_id = Column(String(255), unique=True, nullable=False, index=True)
    gmail_thread_id = Column(String(255), nullable=False)  # Index defined in __table_args__
    sender = Column(String(255), nullable=False)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(512), nullable=False)
    body = Column(Text, nullable=False)
    embedding = Column(ArrayType, nullable=True)  # Vector(1536)
    gmail_metadata = Column(JSONType, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_messages_gmail_thread_id", "gmail_thread_id"),
        Index("ix_messages_created_at", "created_at"),
    )


class Thread(Base):
    """Gmail thread model."""

    __tablename__ = "threads"

    id = Column(UUID(as_uuid=True), primary_key=True)
    gmail_thread_id = Column(String(255), unique=True, nullable=False, index=True)
    hubspot_company_id = Column(String(255), nullable=True)  # Index in __table_args__
    hubspot_contact_id = Column(String(255), nullable=True)  # Index in __table_args__
    subject = Column(String(512), nullable=False)
    last_message_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_threads_hubspot_company_id", "hubspot_company_id"),
        Index("ix_threads_hubspot_contact_id", "hubspot_contact_id"),
    )
