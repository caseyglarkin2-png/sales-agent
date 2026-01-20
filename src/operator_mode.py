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
    """Management of draft approvals in operator mode with database persistence."""

    def __init__(self, approval_required: bool = True):
        """Initialize draft queue."""
        self.approval_required = approval_required
        # In-memory cache for quick access (also persisted to DB)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._db = None
        logger.info(f"Draft queue initialized, approval_required={approval_required}")

    async def _get_db(self):
        """Get the workflow database instance."""
        if self._db is None:
            from src.db.workflow_db import get_workflow_db
            self._db = await get_workflow_db()
        return self._db

    async def create_draft(
        self, 
        draft_id: str, 
        recipient: str, 
        subject: str, 
        body: str, 
        metadata: Optional[Dict] = None,
        gmail_draft_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        contact_id: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new draft and persist to database."""
        draft = {
            "id": draft_id,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "metadata": metadata or {},
            "status": DraftStatus.CREATED.value,
            "created_at": datetime.utcnow().isoformat(),
            "approved_at": None,
            "approved_by": None,
            "rejected_reason": None,
            "gmail_draft_id": gmail_draft_id,
            "workflow_id": workflow_id,
            "contact_id": contact_id,
            "company_name": company_name,
        }

        # Cache locally
        self._cache[draft_id] = draft
        logger.info(f"Draft created: {draft_id} for {recipient}")

        # Validate draft (may change status)
        await self._validate_draft(draft_id)

        # Persist to database
        try:
            db = await self._get_db()
            await db.save_pending_draft(
                draft_id=draft_id,
                gmail_draft_id=gmail_draft_id or "",
                recipient=recipient,
                subject=subject,
                body=body,
                workflow_id=workflow_id,
                contact_id=contact_id,
                company_name=company_name,
                metadata={
                    **draft["metadata"],
                    "status": draft["status"],
                    "created_at": draft["created_at"],
                },
            )
            logger.info(f"Draft {draft_id} persisted to database")
        except Exception as e:
            logger.error(f"Failed to persist draft {draft_id} to database: {e}")

        return draft

    async def _validate_draft(self, draft_id: str) -> None:
        """Validate draft for compliance."""
        draft = self._cache.get(draft_id)
        if not draft:
            return

        # Check basic validation
        if len(draft["body"]) < 50:
            draft["status"] = DraftStatus.REJECTED.value
            draft["rejected_reason"] = "Message too short"
            logger.warning(f"Draft {draft_id} rejected: message too short")
            return

        if self.approval_required:
            draft["status"] = DraftStatus.PENDING_APPROVAL.value
            logger.info(f"Draft {draft_id} moved to pending approval")
        else:
            draft["status"] = DraftStatus.APPROVED.value
            logger.info(f"Draft {draft_id} auto-approved")

    async def approve_draft(self, draft_id: str, approved_by: str) -> bool:
        """Approve a draft for sending."""
        draft = await self.get_draft(draft_id)
        if not draft:
            logger.error(f"Draft not found: {draft_id}")
            return False

        current_status = draft.get("status")
        if current_status != DraftStatus.PENDING_APPROVAL.value:
            logger.warning(f"Cannot approve draft {draft_id} with status {current_status}")
            return False

        draft["status"] = DraftStatus.APPROVED.value
        draft["approved_at"] = datetime.utcnow().isoformat()
        draft["approved_by"] = approved_by
        
        # Update cache
        self._cache[draft_id] = draft
        
        # Update database
        try:
            db = await self._get_db()
            await db.update_draft_status(draft_id, "approved")
        except Exception as e:
            logger.error(f"Failed to update draft status in database: {e}")
        
        logger.info(f"Draft approved by {approved_by}: {draft_id}")
        return True

    async def reject_draft(self, draft_id: str, reason: str, rejected_by: str) -> bool:
        """Reject a draft."""
        draft = await self.get_draft(draft_id)
        if not draft:
            logger.error(f"Draft not found: {draft_id}")
            return False

        draft["status"] = DraftStatus.REJECTED.value
        draft["rejected_reason"] = reason
        draft["approved_by"] = rejected_by
        
        # Update cache
        self._cache[draft_id] = draft
        
        # Update database
        try:
            db = await self._get_db()
            await db.update_draft_status(draft_id, "rejected", reason)
        except Exception as e:
            logger.error(f"Failed to update draft status in database: {e}")
        
        logger.info(f"Draft rejected by {rejected_by}: {draft_id} - {reason}")
        return True

    async def mark_sent(self, draft_id: str) -> bool:
        """Mark draft as sent."""
        draft = await self.get_draft(draft_id)
        if not draft:
            return False

        draft["status"] = DraftStatus.SENT.value
        
        # Update cache
        self._cache[draft_id] = draft
        
        # Update database
        try:
            db = await self._get_db()
            await db.update_draft_status(draft_id, "sent")
        except Exception as e:
            logger.error(f"Failed to update draft status in database: {e}")
        
        logger.info(f"Draft marked as sent: {draft_id}")
        return True

    async def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all drafts pending operator approval from database."""
        try:
            db = await self._get_db()
            db_drafts = await db.get_pending_drafts("pending")
            
            # Convert database format to API format
            pending = []
            for db_draft in db_drafts:
                draft = {
                    "id": db_draft.get("draft_id"),
                    "recipient": db_draft.get("recipient"),
                    "subject": db_draft.get("subject"),
                    "body": db_draft.get("body"),
                    "metadata": db_draft.get("metadata") or {},
                    "status": DraftStatus.PENDING_APPROVAL.value,
                    "created_at": db_draft.get("created_at").isoformat() if db_draft.get("created_at") else None,
                    "gmail_draft_id": db_draft.get("gmail_draft_id"),
                    "workflow_id": db_draft.get("workflow_id"),
                    "contact_id": db_draft.get("contact_id"),
                    "company_name": db_draft.get("company_name"),
                }
                pending.append(draft)
                # Update cache
                self._cache[draft["id"]] = draft
            
            logger.debug(f"Found {len(pending)} pending approvals from database")
            return pending
        except Exception as e:
            logger.error(f"Error fetching pending approvals from database: {e}")
            # Fallback to cache
            pending = [
                draft
                for draft in self._cache.values()
                if draft.get("status") == DraftStatus.PENDING_APPROVAL.value
            ]
            return pending

    async def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Get draft details from cache or database."""
        # Check cache first
        if draft_id in self._cache:
            return self._cache[draft_id]
        
        # Try database
        try:
            db = await self._get_db()
            db_draft = await db.get_draft_by_id(draft_id)
            if db_draft:
                draft = {
                    "id": db_draft.get("draft_id"),
                    "recipient": db_draft.get("recipient"),
                    "subject": db_draft.get("subject"),
                    "body": db_draft.get("body"),
                    "metadata": db_draft.get("metadata") or {},
                    "status": db_draft.get("status", "pending").upper(),
                    "created_at": db_draft.get("created_at").isoformat() if db_draft.get("created_at") else None,
                    "gmail_draft_id": db_draft.get("gmail_draft_id"),
                    "workflow_id": db_draft.get("workflow_id"),
                    "contact_id": db_draft.get("contact_id"),
                    "company_name": db_draft.get("company_name"),
                }
                self._cache[draft_id] = draft
                return draft
        except Exception as e:
            logger.error(f"Error fetching draft from database: {e}")
        
        return None


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

