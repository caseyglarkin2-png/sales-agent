"""SendGrid Email Connector.

High-volume email sending via SendGrid API.
Sprint 64: SendGrid Integration
"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SendGridResponse:
    """Response from SendGrid API."""
    success: bool
    message_id: Optional[str] = None
    status_code: int = 0
    error: Optional[str] = None


class SendGridConnector:
    """SendGrid email connector."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        sender_email: Optional[str] = None,
        sender_name: Optional[str] = None,
    ):
        """Initialize SendGrid connector.
        
        Args:
            api_key: SendGrid API key (defaults to env var)
            sender_email: Default sender email
            sender_name: Default sender name
        """
        settings = get_settings()
        self.api_key = api_key or settings.sendgrid_api_key
        self.sender_email = sender_email or settings.sendgrid_sender_email
        self.sender_name = sender_name or settings.sendgrid_sender_name or "CaseyOS"
        self.base_url = "https://api.sendgrid.com/v3"
        
        if not self.api_key:
            logger.warning("SendGrid API key not configured")

    @property
    def is_configured(self) -> bool:
        """Check if SendGrid is properly configured."""
        return bool(self.api_key and self.sender_email)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        categories: Optional[List[str]] = None,
        custom_args: Optional[Dict[str, str]] = None,
    ) -> SendGridResponse:
        """Send an email via SendGrid.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: HTML body (optional)
            from_email: Sender email (defaults to configured sender)
            from_name: Sender name
            reply_to: Reply-to address
            categories: SendGrid categories for tracking
            custom_args: Custom arguments for webhooks
            
        Returns:
            SendGridResponse with success status and message ID
        """
        if not self.is_configured:
            return SendGridResponse(
                success=False,
                error="SendGrid not configured. Set SENDGRID_API_KEY and SENDGRID_SENDER_EMAIL.",
            )
        
        # Build email payload
        payload = {
            "personalizations": [
                {
                    "to": [{"email": to_email}],
                }
            ],
            "from": {
                "email": from_email or self.sender_email,
                "name": from_name or self.sender_name,
            },
            "subject": subject,
            "content": [
                {"type": "text/plain", "value": body_text},
            ],
        }
        
        # Add HTML content if provided
        if body_html:
            payload["content"].append({"type": "text/html", "value": body_html})
        
        # Add reply-to if provided
        if reply_to:
            payload["reply_to"] = {"email": reply_to}
        
        # Add tracking categories
        if categories:
            payload["categories"] = categories
        
        # Add custom args for webhook tracking
        if custom_args:
            payload["personalizations"][0]["custom_args"] = custom_args
        
        # Send request
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/mail/send",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=30.0,
                )
            
            if response.status_code in (200, 201, 202):
                # Get message ID from headers
                message_id = response.headers.get("X-Message-Id")
                logger.info(f"SendGrid email sent to {to_email}, message_id={message_id}")
                return SendGridResponse(
                    success=True,
                    message_id=message_id,
                    status_code=response.status_code,
                )
            else:
                error_text = response.text
                logger.error(f"SendGrid error: {response.status_code} - {error_text}")
                return SendGridResponse(
                    success=False,
                    status_code=response.status_code,
                    error=error_text,
                )
        
        except httpx.TimeoutException:
            logger.error("SendGrid request timed out")
            return SendGridResponse(success=False, error="Request timed out")
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return SendGridResponse(success=False, error=str(e))

    async def send_batch(
        self,
        emails: List[Dict[str, Any]],
    ) -> List[SendGridResponse]:
        """Send multiple emails.
        
        Args:
            emails: List of email dicts with to_email, subject, body_text, etc.
            
        Returns:
            List of SendGridResponse for each email
        """
        results = []
        for email_data in emails:
            result = await self.send_email(**email_data)
            results.append(result)
        return results


def create_sendgrid_connector() -> SendGridConnector:
    """Create SendGrid connector with settings from environment."""
    return SendGridConnector()


# Singleton
_connector: Optional[SendGridConnector] = None


def get_sendgrid_connector() -> SendGridConnector:
    """Get singleton SendGrid connector."""
    global _connector
    if _connector is None:
        _connector = create_sendgrid_connector()
    return _connector
