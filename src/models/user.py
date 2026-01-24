"""User model for CaseyOS authentication.

Sprint 1, Task 1.1 - Google OAuth Setup
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, JSON, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from src.db import Base


class User(Base):
    """User model for CaseyOS.
    
    Stores Google OAuth credentials and user profile information.
    Only allowed users (casey.l@pesti.io, etc.) can access the system.
    """
    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    picture = Column(Text, nullable=True)  # Google profile picture URL
    
    # Google OAuth tokens (encrypted in production)
    google_access_token = Column(Text, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    google_token_expiry = Column(DateTime, nullable=True)
    google_token_scopes = Column(JSON, nullable=True)  # List of granted scopes
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_allowed = Column(Boolean, default=False, nullable=False)  # Must be in allowed list
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
    
    def has_valid_google_token(self) -> bool:
        """Check if the user has a valid (non-expired) Google token."""
        if not self.google_access_token:
            return False
        if not self.google_token_expiry:
            return False
        return self.google_token_expiry > datetime.utcnow()
    
    def has_scope(self, scope: str) -> bool:
        """Check if the user has a specific OAuth scope."""
        if not self.google_token_scopes:
            return False
        return scope in self.google_token_scopes


class UserSession(Base):
    """User session for cookie-based authentication.
    
    Sprint 1, Task 1.2 - Session Management
    """
    __tablename__ = "user_sessions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    
    # Session metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 can be up to 45 chars
    user_agent = Column(Text, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<UserSession {self.id} user={self.user_id}>"
    
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.utcnow() > self.expires_at
