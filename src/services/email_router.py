"""Email Router Service.

Routes emails to appropriate provider based on configuration and volume.
Sprint 64: SendGrid Integration
"""
import logging
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

from src.config import get_settings
from src.connectors.gmail import create_gmail_connector
from src.connectors.sendgrid import get_sendgrid_connector

logger = logging.getLogger(__name__)


class EmailProvider(str, Enum):
    """Email provider options."""
    GMAIL = "gmail"
    SENDGRID = "sendgrid"
    AUTO = "auto"  # Automatically choose based on volume/config


@dataclass
class EmailResult:
    """Result of sending an email."""
    success: bool
    provider: str
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "provider": self.provider,
            "message_id": self.message_id,
            "thread_id": self.thread_id,
            "error": self.error,
        }


class EmailRouter:
    """Routes emails to appropriate provider."""

    def __init__(self):
        """Initialize email router."""
        settings = get_settings()
        self.default_provider = EmailProvider(
            settings.email_provider if hasattr(settings, 'email_provider') else "gmail"
        )
        self.gmail_daily_limit = 500  # Gmail free limit
        self._daily_gmail_count = 0

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        provider: Optional[EmailProvider] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmailResult:
        """Send email via appropriate provider.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            from_email: Sender email
            reply_to: Reply-to address
            provider: Force specific provider
            user_id: User ID for Gmail OAuth
            metadata: Additional tracking metadata
            
        Returns:
            EmailResult with send status
        """
        # Determine provider
        selected_provider = provider or self.default_provider
        
        if selected_provider == EmailProvider.AUTO:
            selected_provider = self._select_provider()
        
        logger.info(f"Routing email to {to_email} via {selected_provider.value}")
        
        if selected_provider == EmailProvider.SENDGRID:
            return await self._send_via_sendgrid(
                to_email=to_email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                from_email=from_email,
                reply_to=reply_to,
                metadata=metadata,
            )
        else:
            return await self._send_via_gmail(
                to_email=to_email,
                subject=subject,
                body_text=body_text,
                from_email=from_email,
                user_id=user_id,
            )

    def _select_provider(self) -> EmailProvider:
        """Auto-select provider based on availability and limits."""
        # Check if SendGrid is configured
        sendgrid = get_sendgrid_connector()
        if sendgrid.is_configured:
            # Prefer SendGrid for high volume
            if self._daily_gmail_count >= self.gmail_daily_limit * 0.8:
                return EmailProvider.SENDGRID
        
        # Default to Gmail
        return EmailProvider.GMAIL

    async def _send_via_gmail(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        from_email: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> EmailResult:
        """Send via Gmail API."""
        try:
            gmail = create_gmail_connector()
            
            result = await gmail.send_email(
                from_email=from_email or "",
                to_email=to_email,
                subject=subject,
                body_text=body_text,
            )
            
            self._daily_gmail_count += 1
            
            return EmailResult(
                success=True,
                provider="gmail",
                message_id=result.get("message_id") or result.get("id"),
                thread_id=result.get("thread_id") or result.get("threadId"),
            )
        
        except Exception as e:
            logger.error(f"Gmail send failed: {e}")
            return EmailResult(
                success=False,
                provider="gmail",
                error=str(e),
            )

    async def _send_via_sendgrid(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EmailResult:
        """Send via SendGrid API."""
        try:
            sendgrid = get_sendgrid_connector()
            
            if not sendgrid.is_configured:
                return EmailResult(
                    success=False,
                    provider="sendgrid",
                    error="SendGrid not configured",
                )
            
            # Build custom args for webhook tracking
            custom_args = None
            if metadata:
                custom_args = {k: str(v) for k, v in metadata.items()}
            
            result = await sendgrid.send_email(
                to_email=to_email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                from_email=from_email,
                reply_to=reply_to,
                custom_args=custom_args,
            )
            
            return EmailResult(
                success=result.success,
                provider="sendgrid",
                message_id=result.message_id,
                error=result.error,
            )
        
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            return EmailResult(
                success=False,
                provider="sendgrid",
                error=str(e),
            )


# Singleton
_router: Optional[EmailRouter] = None


def get_email_router() -> EmailRouter:
    """Get singleton email router."""
    global _router
    if _router is None:
        _router = EmailRouter()
    return _router
