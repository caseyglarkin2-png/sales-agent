"""CSRF protection middleware for state-changing operations."""
import hashlib
import hmac
import secrets
import time
from typing import Optional, Set

from fastapi import HTTPException, Request, status


class CSRFProtection:
    """CSRF token validation for state-changing operations."""

    def __init__(self, secret_key: str = None):
        """Initialize CSRF protection with secret key."""
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.token_ttl = 3600  # 1 hour
        # Track issued tokens (in production, use Redis)
        self._issued_tokens: Set[str] = set()
        self._max_tokens = 10000  # Limit memory usage

    def generate_token(self) -> str:
        """Generate a new CSRF token."""
        token = secrets.token_urlsafe(32)
        # Track issued token
        if len(self._issued_tokens) >= self._max_tokens:
            # Clear oldest half when at capacity
            self._issued_tokens = set(list(self._issued_tokens)[self._max_tokens // 2:])
        self._issued_tokens.add(token)
        return token

    def validate_token(self, token: str, request_path: str) -> bool:
        """
        Validate CSRF token.

        Args:
            token: CSRF token from client
            request_path: Request path for context

        Returns:
            True if valid, False otherwise
        """
        if not token:
            return False

        # Token format: base64_token (simple validation for this implementation)
        try:
            # Basic validation: token should be non-empty, reasonable length
            if len(token) < 20 or len(token) > 512:
                return False
            # Check if token was issued by us
            return token in self._issued_tokens
        except Exception:
            return False


# Global CSRF instance
csrf_protection = CSRFProtection()


async def verify_csrf_token(request: Request) -> None:
    """
    Verify CSRF token in request.

    For state-changing endpoints (POST, PUT, DELETE).
    Webhooks with signatures are excluded.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: If CSRF token is invalid or missing
    """
    # Skip CSRF check for webhooks (they have signature validation)
    if request.url.path.startswith("/api/webhooks"):
        return

    # For state-changing operations, require CSRF token in header
    csrf_token = request.headers.get("X-CSRF-Token")

    if not csrf_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing. Include X-CSRF-Token header.",
        )

    if not csrf_protection.validate_token(csrf_token, request.url.path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token invalid or expired.",
        )


def exclude_path(path: str) -> bool:
    """
    Check if path should skip CSRF validation.
    
    Excluded paths:
    - /api/webhooks/* - External webhooks with signature validation
    - /mcp/* - MCP server (Claude Desktop integration)
    - /health, /healthz, /ready - Health checks
    - /auth/* - OAuth callbacks
    - /docs, /redoc, /openapi.json - API documentation
    """
    # Webhook endpoints (have signature validation)
    if path.startswith("/api/webhooks"):
        return True

    # MCP server (Claude Desktop integration)
    if path.startswith("/mcp"):
        return True

    # Health checks
    if path in ["/health", "/healthz", "/ready"]:
        return True

    # OAuth callbacks (state validation via OAuth protocol)
    if path.startswith("/auth/"):
        return True

    # API documentation
    if path in ["/docs", "/redoc", "/openapi.json"]:
        return True

    return False
