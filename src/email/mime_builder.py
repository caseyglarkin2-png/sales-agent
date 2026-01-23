"""MIME message construction for RFC 2822 compliant emails.

This module builds properly formatted email messages that work with
Gmail API and comply with email standards.
"""
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from typing import Optional

from src.logger import get_logger

logger = get_logger(__name__)


def build_mime_message(
    from_email: str,
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
) -> str:
    """Build RFC 2822 compliant MIME message for Gmail API.
    
    Args:
        from_email: Sender email address
        to_email: Recipient email address
        subject: Email subject line
        body_text: Plain text email body (required)
        body_html: HTML email body (optional)
        in_reply_to: Message-ID of email being replied to (for threading)
        references: Space-separated Message-IDs for thread context
        
    Returns:
        RFC 2822 formatted message string (ready for base64 encoding)
        
    Example:
        >>> msg = build_mime_message(
        ...     from_email="alex@pesti.io",
        ...     to_email="prospect@company.com",
        ...     subject="Follow-up on your inquiry",
        ...     body_text="Hi there, following up..."
        ... )
        >>> import base64
        >>> encoded = base64.urlsafe_b64encode(msg.encode()).decode()
    """
    # Create multipart message if HTML provided, otherwise simple text
    if body_html:
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(body_text, "plain", "utf-8"))
        message.attach(MIMEText(body_html, "html", "utf-8"))
    else:
        message = MIMEText(body_text, "plain", "utf-8")
    
    # Required headers
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain=from_email.split("@")[-1])
    
    # Threading headers (keep conversation context)
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
    if references:
        message["References"] = references
    
    # Convert to string
    mime_string = message.as_string()
    
    logger.info(
        f"Built MIME message: from={from_email}, to={to_email}, "
        f"subject='{subject[:50]}...', size={len(mime_string)} bytes"
    )
    
    return mime_string


def validate_mime_message(mime_string: str) -> dict:
    """Validate MIME message structure.
    
    Args:
        mime_string: RFC 2822 formatted message
        
    Returns:
        dict with validation results:
            - valid: bool
            - errors: list of error messages
            - warnings: list of warnings
            - size_bytes: int
    """
    from email import message_from_string
    
    errors = []
    warnings = []
    
    try:
        msg = message_from_string(mime_string)
        
        # Check required headers
        required_headers = ["From", "To", "Subject", "Date", "Message-ID"]
        for header in required_headers:
            if not msg.get(header):
                errors.append(f"Missing required header: {header}")
        
        # Check size (Gmail limit: 25MB, but draft limit: 1MB recommended)
        size_bytes = len(mime_string.encode('utf-8'))
        if size_bytes > 1_000_000:  # 1MB
            warnings.append(f"Message size {size_bytes} bytes exceeds 1MB recommendation")
        if size_bytes > 25_000_000:  # 25MB
            errors.append(f"Message size {size_bytes} bytes exceeds Gmail 25MB limit")
        
        # Check body exists
        if msg.is_multipart():
            parts = list(msg.walk())
            if len(parts) < 2:
                errors.append("Multipart message has no body parts")
        else:
            if not msg.get_payload():
                errors.append("Message has no body")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "size_bytes": size_bytes,
        }
    
    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Failed to parse MIME message: {str(e)}"],
            "warnings": warnings,
            "size_bytes": len(mime_string.encode('utf-8')),
        }
