"""Security middleware for FastAPI application."""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.logger import get_logger
from src.security.csrf import csrf_protection, exclude_path

logger = get_logger(__name__)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware to validate CSRF tokens on state-changing operations."""

    async def dispatch(self, request: Request, call_next):
        """
        Process request and validate CSRF token if needed.

        CSRF validation is skipped for:
        - GET/HEAD/OPTIONS requests (no state change)
        - Webhook endpoints (they have signature validation)
        - Health check endpoints
        """
        # Skip CSRF check for non-state-changing methods
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return await call_next(request)

        # Skip for excluded paths (webhooks, health checks)
        if exclude_path(request.url.path):
            return await call_next(request)

        # Validate CSRF token
        csrf_token = request.headers.get("X-CSRF-Token")

        if not csrf_token:
            logger.warning(
                f"CSRF token missing for {request.method} {request.url.path} "
                f"from {request.client.host if request.client else 'unknown'}"
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token missing. Include X-CSRF-Token header."},
            )

        if not csrf_protection.validate_token(csrf_token, request.url.path):
            logger.warning(
                f"CSRF token invalid for {request.method} {request.url.path} "
                f"from {request.client.host if request.client else 'unknown'}"
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token invalid or expired."},
            )

        # Token valid, proceed
        return await call_next(request)


class SecurityHeaderMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # CSRF header for client to include
        csrf_token = csrf_protection.generate_token()
        response.headers["X-CSRF-Token"] = csrf_token

        return response
