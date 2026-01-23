"""Sentry Error Tracking Integration.

Provides centralized error tracking and performance monitoring via Sentry.
"""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging
from typing import Optional

from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)


def init_sentry() -> bool:
    """
    Initialize Sentry SDK for error tracking.
    
    Returns:
        True if Sentry was initialized, False if disabled
    """
    settings = get_settings()
    
    # Skip if no DSN provided
    if not settings.sentry_dsn:
        logger.info("Sentry DSN not configured, error tracking disabled")
        return False
    
    try:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            
            # Performance monitoring
            traces_sample_rate=settings.sentry_traces_sample_rate,
            
            # Enable/disable features
            send_default_pii=False,  # Don't send PII by default
            attach_stacktrace=True,
            
            # Integrations
            integrations=[
                FastApiIntegration(
                    transaction_style="endpoint",  # Group by endpoint
                ),
                SqlalchemyIntegration(),
                RedisIntegration(),
                CeleryIntegration(),
                LoggingIntegration(
                    level=logging.INFO,  # Capture info and above
                    event_level=logging.ERROR  # Send errors to Sentry
                ),
            ],
            
            # Release tracking
            release=get_release_version(),
            
            # Before send hook to filter events
            before_send=before_send_hook,
            
            # Before breadcrumb hook to filter breadcrumbs
            before_breadcrumb=before_breadcrumb_hook,
        )
        
        logger.info(
            "Sentry initialized successfully",
            environment=settings.sentry_environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def get_release_version() -> str:
    """Get the current release version for Sentry."""
    try:
        # Try to read from version file
        with open("/workspaces/sales-agent/VERSION", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback to git commit
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd="/workspaces/sales-agent"
            )
            if result.returncode == 0:
                return f"git-{result.stdout.strip()}"
        except Exception:
            pass
    
    return "unknown"


def before_send_hook(event, hint):
    """
    Filter events before sending to Sentry.
    
    Use this to:
    - Remove sensitive data
    - Filter out known errors
    - Add custom tags/context
    """
    # Don't send health check errors
    if event.get("transaction") in ["/health", "/healthz", "/ready"]:
        return None
    
    # Don't send expected HTTP errors
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        if exc_type.__name__ in ["HTTPException", "ValidationError"]:
            # Only send 5xx errors, not 4xx
            if hasattr(exc_value, "status_code"):
                if 400 <= exc_value.status_code < 500:
                    return None
    
    # Redact sensitive data from event
    event = redact_sensitive_data(event)
    
    return event


def before_breadcrumb_hook(crumb, hint):
    """
    Filter breadcrumbs before adding to event.
    
    Breadcrumbs are the trail of events leading up to an error.
    """
    # Don't log OAuth token requests in breadcrumbs
    if crumb.get("category") == "httplib":
        url = crumb.get("data", {}).get("url", "")
        if "/oauth" in url or "/token" in url:
            return None
    
    # Don't log password-related queries
    if crumb.get("category") == "query":
        query = crumb.get("message", "")
        if "password" in query.lower():
            crumb["message"] = "[REDACTED PASSWORD QUERY]"
    
    return crumb


def redact_sensitive_data(event):
    """Remove sensitive data from Sentry event."""
    # Redact request body if it contains sensitive fields
    if "request" in event:
        if "data" in event["request"]:
            data = event["request"]["data"]
            if isinstance(data, dict):
                for key in ["password", "token", "secret", "api_key"]:
                    if key in data:
                        data[key] = "[REDACTED]"
        
        # Redact headers
        if "headers" in event["request"]:
            headers = event["request"]["headers"]
            for key in ["Authorization", "X-Admin-Token", "X-API-Key"]:
                if key in headers:
                    headers[key] = "[REDACTED]"
    
    # Redact environment variables
    if "extra" in event and "sys.argv" in event["extra"]:
        # Don't send command line args that might contain secrets
        event["extra"]["sys.argv"] = "[REDACTED]"
    
    return event


def capture_exception(error: Exception, **kwargs) -> Optional[str]:
    """
    Manually capture an exception to Sentry.
    
    Args:
        error: Exception to capture
        **kwargs: Additional context (tags, extra data)
        
    Returns:
        Event ID if sent to Sentry, None otherwise
    """
    try:
        # Add custom context
        if "tags" in kwargs:
            for key, value in kwargs["tags"].items():
                sentry_sdk.set_tag(key, value)
        
        if "extra" in kwargs:
            for key, value in kwargs["extra"].items():
                sentry_sdk.set_context(key, value)
        
        # Capture exception
        event_id = sentry_sdk.capture_exception(error)
        
        logger.debug(f"Exception sent to Sentry: {event_id}")
        return event_id
        
    except Exception as e:
        logger.error(f"Failed to send exception to Sentry: {e}")
        return None


def capture_message(message: str, level: str = "info", **kwargs) -> Optional[str]:
    """
    Manually capture a message to Sentry.
    
    Args:
        message: Message to capture
        level: Severity level (debug, info, warning, error, fatal)
        **kwargs: Additional context
        
    Returns:
        Event ID if sent to Sentry, None otherwise
    """
    try:
        event_id = sentry_sdk.capture_message(message, level=level)
        return event_id
    except Exception as e:
        logger.error(f"Failed to send message to Sentry: {e}")
        return None


def set_user_context(user_id: str, email: Optional[str] = None, **kwargs):
    """
    Set user context for Sentry events.
    
    Args:
        user_id: User ID
        email: User email (will be redacted if send_default_pii=False)
        **kwargs: Additional user attributes
    """
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
        **kwargs
    })


def add_breadcrumb(message: str, category: str = "default", level: str = "info", **data):
    """
    Add a breadcrumb to the current scope.
    
    Breadcrumbs are logged events that provide context when an error occurs.
    
    Args:
        message: Breadcrumb message
        category: Category (e.g., "http", "db", "auth")
        level: Severity level
        **data: Additional data
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data
    )


def start_transaction(name: str, op: str = "function") -> Optional[object]:
    """
    Start a performance monitoring transaction.
    
    Args:
        name: Transaction name (e.g., "POST /api/drafts")
        op: Operation type (e.g., "http.server", "db.query")
        
    Returns:
        Transaction object (use with context manager)
        
    Example:
        with start_transaction("process_webhook", "task"):
            # ... do work ...
            pass
    """
    return sentry_sdk.start_transaction(name=name, op=op)


# Convenience function for FastAPI exception handler
def sentry_exception_handler(request, exc):
    """
    Exception handler for FastAPI that sends to Sentry.
    
    Add to FastAPI app:
        from fastapi.exceptions import RequestValidationError
        app.add_exception_handler(Exception, sentry_exception_handler)
    """
    # Capture to Sentry
    event_id = capture_exception(
        exc,
        tags={"endpoint": request.url.path},
        extra={"request_body": request.body()}
    )
    
    # Re-raise to let FastAPI handle the response
    raise exc
