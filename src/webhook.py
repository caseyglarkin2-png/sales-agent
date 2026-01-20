"""Webhook security and signature verification."""
import hashlib
import hmac
from typing import Optional

from src.logger import get_logger

logger = get_logger(__name__)


class WebhookValidator:
    """Validate webhook signatures for security."""

    def __init__(self, secret: str):
        """Initialize webhook validator."""
        self.secret = secret

    def verify_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature."""
        expected_signature = self._compute_signature(payload)
        is_valid = hmac.compare_digest(expected_signature, signature)
        
        if is_valid:
            logger.debug("Webhook signature verified")
        else:
            logger.warning("Webhook signature verification failed")
        
        return is_valid

    def _compute_signature(self, payload: str) -> str:
        """Compute expected signature for payload."""
        return hmac.new(
            self.secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def get_signature_header(self, payload: str) -> str:
        """Get signature header value for a payload."""
        return self._compute_signature(payload)
