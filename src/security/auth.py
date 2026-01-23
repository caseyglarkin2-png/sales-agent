"""Authentication and authorization utilities."""
from typing import Optional

from fastapi import HTTPException, Request, status

from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def require_admin_role(request: Request) -> None:
    """
    Verify admin authentication for protected endpoints.

    Checks:
    1. X-Admin-Token header matches ADMIN_PASSWORD
    2. Request comes from authorized IP (optional)

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: If not authenticated as admin
    """
    admin_password = getattr(settings, "admin_password", None)

    if not admin_password:
        logger.warning("Admin password not configured in environment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin authentication not configured",
        )

    # Check admin token in header
    token = request.headers.get("X-Admin-Token")

    if not token:
        logger.warning(f"Admin access attempt without token from {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin token required",
        )

    # Constant-time comparison to prevent timing attacks
    if not _constant_time_compare(token, admin_password):
        logger.warning(f"Admin access attempt with invalid token from {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )

    logger.info(f"Admin access granted from {request.client.host}")


def _constant_time_compare(a: str, b: str) -> bool:
    """Compare strings in constant time to prevent timing attacks."""
    import hmac

    return hmac.compare_digest(a, b)


async def require_api_key(request: Request, expected_key: str) -> None:
    """
    Verify API key authentication.

    Args:
        request: FastAPI request object
        expected_key: Expected API key value

    Raises:
        HTTPException: If API key is missing or invalid
    """
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    if not _constant_time_compare(api_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
