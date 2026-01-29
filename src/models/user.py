"""User model for CaseyOS authentication.

Sprint 1, Task 1.1 - Google OAuth Setup
Sprint 53, Task 53.1 - User Profile Extension
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, JSON, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

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
    
    # Profile fields for email signature (Sprint 53)
    display_name = Column(String(255), nullable=True)  # Name to use in emails
    job_title = Column(String(255), nullable=True)  # e.g., "CEO, Pesti"
    company_name = Column(String(255), nullable=True)  # e.g., "Pesti"
    signature_html = Column(Text, nullable=True)  # Custom HTML signature
    calendar_link = Column(String(500), nullable=True)  # HubSpot/Calendly booking link
    phone_number = Column(String(50), nullable=True)  # Contact phone
    default_voice_profile_id = Column(PGUUID(as_uuid=True), nullable=True)  # Preferred voice profile
    
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
    
    def get_display_name(self) -> str:
        """Get the best available display name for the user."""
        return self.display_name or self.name or self.email.split("@")[0]
    
    def get_signature_context(self) -> dict:
        """Get signature context for email draft generation.
        
        Returns dict with sender_name, sender_title, sender_company, calendar_link.
        """
        return {
            "sender_name": self.get_display_name(),
            "sender_title": self.job_title or "",
            "sender_company": self.company_name or "",
            "sender_email": self.email,
            "sender_phone": self.phone_number or "",
            "calendar_link": self.calendar_link or "",
            "signature_html": self.signature_html or "",
        }
    
    def build_signature(self) -> str:
        """Build a text signature from profile fields."""
        parts = ["", "Best,", "", self.get_display_name()]
        if self.job_title:
            parts.append(self.job_title)
        if self.company_name:
            parts.append(self.company_name)
        if self.calendar_link:
            parts.append("")
            parts.append(f"Book time: {self.calendar_link}")
        return "\n".join(parts)
    
    # Relationship to sessions
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """User session for cookie-based authentication.
    
    Sprint 1, Task 1.2 - Session Management
    """
    __tablename__ = "user_sessions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    
    # Session metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 can be up to 45 chars
    user_agent = Column(Text, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to user
    user = relationship("User", back_populates="sessions", lazy="selectin")
    
    def __repr__(self) -> str:
        return f"<UserSession {self.id} user={self.user_id}>"
    
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.utcnow() > self.expires_at
