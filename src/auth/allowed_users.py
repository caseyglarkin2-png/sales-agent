"""Allowed users configuration for CaseyOS.

Sprint 1, Task 1.6 - Allowed Users List

Only emails in this list can access the system.
Configure via ALLOWED_EMAILS environment variable (comma-separated).
"""
import os
from typing import Set

from src.logger import get_logger

logger = get_logger(__name__)

# Default allowed emails (Casey's accounts)
DEFAULT_ALLOWED_EMAILS = {
    "casey.l@pesti.io",
    "casey@dwtb.com",
    "caseyglarkin@gmail.com",
}


def get_allowed_emails() -> Set[str]:
    """Get the set of allowed email addresses.
    
    Reads from ALLOWED_EMAILS environment variable if set,
    otherwise uses DEFAULT_ALLOWED_EMAILS.
    
    Returns:
        Set of allowed email addresses (lowercase)
    """
    env_emails = os.environ.get("ALLOWED_EMAILS", "")
    
    if env_emails:
        # Parse comma-separated list
        emails = {email.strip().lower() for email in env_emails.split(",") if email.strip()}
        logger.info(f"Loaded {len(emails)} allowed emails from environment")
        return emails
    
    logger.info(f"Using {len(DEFAULT_ALLOWED_EMAILS)} default allowed emails")
    return {email.lower() for email in DEFAULT_ALLOWED_EMAILS}


def is_email_allowed(email: str) -> bool:
    """Check if an email address is allowed to access the system.
    
    Args:
        email: Email address to check
    
    Returns:
        True if allowed, False otherwise
    """
    allowed = get_allowed_emails()
    is_allowed = email.lower() in allowed
    
    if not is_allowed:
        logger.warning(f"Access denied for email: {email}")
    
    return is_allowed


# Cache the allowed emails on module load
_allowed_emails_cache: Set[str] | None = None


def get_allowed_emails_cached() -> Set[str]:
    """Get allowed emails with caching (for performance)."""
    global _allowed_emails_cache
    if _allowed_emails_cache is None:
        _allowed_emails_cache = get_allowed_emails()
    return _allowed_emails_cache


def clear_allowed_emails_cache() -> None:
    """Clear the allowed emails cache (for testing or config reload)."""
    global _allowed_emails_cache
    _allowed_emails_cache = None
