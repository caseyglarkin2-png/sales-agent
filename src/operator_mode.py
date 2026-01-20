"""Operator mode and draft approval workflow."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from src.logger import get_logger

logger = get_logger(__name__)


class DraftStatus(str, Enum):
    """Draft status enumeration."""
    CREATED = "CREATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SENT = "SENT"


class DraftQueue:
    """Management of draft approvals in operator mode."""

    def __init__(self, approval_required: bool = True):
        """Initialize draft queue."""
        self.approval_required = approval_required
        self.drafts: Dict[str, Dict[str, Any]] = {}
        logger.info(f"Draft queue initialized, approval_required={approval_required}")

    async def create_draft(
        self, draft_id: str, recipient: str, subject: str, body: str, metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a new draft."""
        draft = {
            "id": draft_id,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "metadata": metadata or {},
            "status": DraftStatus.CREATED,
            "created_at": datetime.utcnow().isoformat(),
            "approved_at": None,
            "approved_by": None,
            "rejected_reason": None,
        }

        self.drafts[draft_id] = draft
        logger.info(f"Draft created: {draft_id} for {recipient}")

        # Validate draft
        await self._validate_draft(draft_id)

        return draft

    async def _validate_draft(self, draft_id: str) -> None:
        """Validate draft for compliance."""
        draft = self.drafts.get(draft_id)
        if not draft:
            return

        # Check basic validation
        if len(draft["body"]) < 50:
            draft["status"] = DraftStatus.REJECTED
            draft["rejected_reason"] = "Message too short"
            logger.warning(f"Draft {draft_id} rejected: message too short")
            return

        if self.approval_required:
            draft["status"] = DraftStatus.PENDING_APPROVAL
            logger.info(f"Draft {draft_id} moved to pending approval")
        else:
            draft["status"] = DraftStatus.APPROVED
            logger.info(f"Draft {draft_id} auto-approved")

    async def approve_draft(self, draft_id: str, approved_by: str) -> bool:
        """Approve a draft for sending."""
        draft = self.drafts.get(draft_id)
        if not draft:
            logger.error(f"Draft not found: {draft_id}")
            return False

        if draft["status"] != DraftStatus.PENDING_APPROVAL:
            logger.warning(f"Cannot approve draft {draft_id} with status {draft['status']}")
            return False

        draft["status"] = DraftStatus.APPROVED
        draft["approved_at"] = datetime.utcnow().isoformat()
        draft["approved_by"] = approved_by
        logger.info(f"Draft approved by {approved_by}: {draft_id}")
        return True

    async def reject_draft(self, draft_id: str, reason: str, rejected_by: str) -> bool:
        """Reject a draft."""
        draft = self.drafts.get(draft_id)
        if not draft:
            logger.error(f"Draft not found: {draft_id}")
            return False

        draft["status"] = DraftStatus.REJECTED
        draft["rejected_reason"] = reason
        draft["approved_by"] = rejected_by
        logger.info(f"Draft rejected by {rejected_by}: {draft_id} - {reason}")
        return True

    async def mark_sent(self, draft_id: str) -> bool:
        """Mark draft as sent."""
        draft = self.drafts.get(draft_id)
        if not draft:
            return False

        draft["status"] = DraftStatus.SENT
        logger.info(f"Draft marked as sent: {draft_id}")
        return True

    async def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all drafts pending operator approval."""
        pending = [
            draft
            for draft in self.drafts.values()
            if draft["status"] == DraftStatus.PENDING_APPROVAL
        ]
        logger.debug(f"Found {len(pending)} pending approvals")
        return pending

    async def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Get draft details."""
        return self.drafts.get(draft_id)


# Global draft queue instance
_draft_queue: Optional[DraftQueue] = None


def get_draft_queue() -> DraftQueue:
    """Get or create global draft queue."""
    global _draft_queue
    if _draft_queue is None:
        from src.config import get_settings
        settings = get_settings()
        _draft_queue = DraftQueue(approval_required=settings.operator_approval_required)
    return _draft_queue
