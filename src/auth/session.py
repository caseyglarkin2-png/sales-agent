"""Session management for CaseyOS.

Sprint 1, Task 1.2 - Session Management
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User, UserSession
from src.logger import get_logger

logger = get_logger(__name__)

# Session configuration
SESSION_EXPIRY_DAYS = 7
SESSION_TOKEN_LENGTH = 64  # 256 bits of entropy


def generate_session_token() -> str:
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(SESSION_TOKEN_LENGTH)


async def create_session(
    db: AsyncSession,
    user_id: UUID,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> UserSession:
    """Create a new session for a user.
    
    Args:
        db: Database session
        user_id: User UUID
        ip_address: Client IP address
        user_agent: Client user agent
    
    Returns:
        Created UserSession
    """
    session = UserSession(
        user_id=user_id,
        session_token=generate_session_token(),
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.utcnow() + timedelta(days=SESSION_EXPIRY_DAYS),
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    logger.info(f"Created session for user {user_id}")
    return session


async def get_session_by_token(
    db: AsyncSession,
    token: str,
) -> Optional[UserSession]:
    """Get a session by its token.
    
    Args:
        db: Database session
        token: Session token
    
    Returns:
        UserSession if found and not expired, None otherwise
    """
    result = await db.execute(
        select(UserSession).where(UserSession.session_token == token)
    )
    session = result.scalar_one_or_none()
    
    if session and session.is_expired():
        # Clean up expired session
        await db.delete(session)
        await db.commit()
        logger.debug(f"Deleted expired session {session.id}")
        return None
    
    # Update last accessed
    if session:
        session.last_accessed = datetime.utcnow()
        await db.commit()
    
    return session


async def get_user_by_session_token(
    db: AsyncSession,
    token: str,
) -> Optional[User]:
    """Get the user associated with a session token.
    
    Args:
        db: Database session
        token: Session token
    
    Returns:
        User if session is valid, None otherwise
    """
    session = await get_session_by_token(db, token)
    if not session:
        return None
    
    result = await db.execute(
        select(User).where(User.id == session.user_id)
    )
    return result.scalar_one_or_none()


async def delete_session(
    db: AsyncSession,
    token: str,
) -> bool:
    """Delete a session by its token.
    
    Args:
        db: Database session
        token: Session token
    
    Returns:
        True if session was deleted, False if not found
    """
    result = await db.execute(
        delete(UserSession).where(UserSession.session_token == token)
    )
    await db.commit()
    
    deleted = result.rowcount > 0
    if deleted:
        logger.info(f"Deleted session")
    return deleted


async def delete_all_user_sessions(
    db: AsyncSession,
    user_id: UUID,
) -> int:
    """Delete all sessions for a user.
    
    Args:
        db: Database session
        user_id: User UUID
    
    Returns:
        Number of sessions deleted
    """
    result = await db.execute(
        delete(UserSession).where(UserSession.user_id == user_id)
    )
    await db.commit()
    
    logger.info(f"Deleted {result.rowcount} sessions for user {user_id}")
    return result.rowcount


async def cleanup_expired_sessions(db: AsyncSession) -> int:
    """Delete all expired sessions.
    
    Args:
        db: Database session
    
    Returns:
        Number of sessions deleted
    """
    result = await db.execute(
        delete(UserSession).where(UserSession.expires_at < datetime.utcnow())
    )
    await db.commit()
    
    if result.rowcount > 0:
        logger.info(f"Cleaned up {result.rowcount} expired sessions")
    return result.rowcount
