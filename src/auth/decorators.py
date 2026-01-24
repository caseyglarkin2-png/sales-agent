"""Authentication decorators for CaseyOS.

Sprint 1, Task 1.3 - Protected Route Decorator
"""
from functools import wraps
from typing import Callable, Optional

from fastapi import HTTPException, Request, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.auth.session import get_user_by_session_token
from src.models.user import User
from src.logger import get_logger

logger = get_logger(__name__)

# Cookie name for session
SESSION_COOKIE_NAME = "caseyos_session"


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get the current user from session cookie (optional).
    
    Returns None if not authenticated (doesn't raise exception).
    """
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    
    if not session_token:
        return None
    
    user = await get_user_by_session_token(db, session_token)
    return user


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current user from session cookie.
    
    Raises 401 if not authenticated.
    """
    user = await get_current_user_optional(request, db)
    
    if not user:
        logger.debug("No valid session found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Cookie"},
        )
    
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    
    if not user.is_allowed:
        logger.warning(f"Non-allowed user attempted access: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    return user


async def get_current_user_redirect(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current user, redirecting to login if not authenticated.
    
    Use this for HTML pages that should redirect to login.
    """
    user = await get_current_user_optional(request, db)
    
    if not user:
        # Store the original URL to redirect back after login
        request.session["redirect_after_login"] = str(request.url)
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )
    
    if not user.is_active or not user.is_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    return user


def require_auth(redirect_to_login: bool = False):
    """Deprecated - use Depends(get_current_user) or Depends(get_current_user_redirect) instead.
    
    This decorator exists for backwards compatibility but does nothing.
    The actual auth check is done via FastAPI's Depends() system.
    
    For API routes:
        async def my_route(user: User = Depends(get_current_user)):
            ...
    
    For HTML pages that should redirect to login:
        async def my_page(user: User = Depends(get_current_user_redirect)):
            ...
    """
    import warnings
    warnings.warn(
        "require_auth is deprecated. Use Depends(get_current_user) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_scope(scope: str):
    """Decorator to require a specific OAuth scope.
    
    Args:
        scope: The Google OAuth scope required
    
    Usage:
        @router.post("/send-email")
        @require_scope("https://www.googleapis.com/auth/gmail.send")
        async def send_email(user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, user: User = None, **kwargs):
            if user and not user.has_scope(scope):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required OAuth scope: {scope}",
                )
            return await func(*args, user=user, **kwargs)
        return wrapper
    return decorator
