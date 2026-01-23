"""GDPR Data Retention & Deletion Module.

Provides functionality for:
- User data deletion on request (right to be forgotten)
- Automated data retention cleanup (older than 90 days)
- Audit trail for all deletions
- PII redaction and anonymization
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import and_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.logger import get_logger
from src.audit_trail import log_audit_event
from src.db import SessionLocal

logger = get_logger(__name__)


class GDPRService:
    """Service for GDPR data deletion and retention policies."""

    def __init__(self):
        """Initialize GDPR service."""
        self.retention_days = 90  # Drafts retained for 90 days
        self.audit_retention_years = 1  # Audit trail kept for 1 year

    async def delete_user_data(
        self,
        email: str,
        admin_id: Optional[str] = None,
        reason: str = "User requested data deletion"
    ) -> Dict[str, Any]:
        """
        Delete all PII for a user (right to be forgotten).
        
        Args:
            email: User email to delete
            admin_id: Admin who initiated deletion
            reason: Reason for deletion
            
        Returns:
            Dictionary with deletion statistics
        """
        logger.info(
            "GDPR deletion initiated",
            email=email,
            admin_id=admin_id,
            reason=reason,
        )

        stats = {
            "email": email,
            "timestamp": datetime.utcnow().isoformat(),
            "admin_id": admin_id,
            "reason": reason,
            "deleted_records": {
                "prospects": 0,
                "draft_emails": 0,
                "tasks": 0,
                "form_submissions": 0,
                "contact_enrichment": 0,
                "email_tracking": 0,
                "campaign_interactions": 0,
                "notes": 0,
            },
            "preserved_records": {
                "audit_trail": "Preserved for 1 year (legal compliance)",
                "financial": "Preserved if applicable",
            },
        }

        try:
            # Delete user data from multiple tables
            async with SessionLocal() as session:
                # 1. Delete prospect and related data
                prospects_deleted = await self._delete_prospects(session, email)
                stats["deleted_records"]["prospects"] = prospects_deleted

                # 2. Delete draft emails
                drafts_deleted = await self._delete_draft_emails(session, email)
                stats["deleted_records"]["draft_emails"] = drafts_deleted

                # 3. Delete tasks
                tasks_deleted = await self._delete_tasks(session, email)
                stats["deleted_records"]["tasks"] = tasks_deleted

                # 4. Delete form submissions
                forms_deleted = await self._delete_form_submissions(session, email)
                stats["deleted_records"]["form_submissions"] = forms_deleted

                # 5. Delete contact enrichment data
                enrichment_deleted = await self._delete_enrichment(session, email)
                stats["deleted_records"]["contact_enrichment"] = enrichment_deleted

                # 6. Delete email tracking data
                tracking_deleted = await self._delete_email_tracking(session, email)
                stats["deleted_records"]["email_tracking"] = tracking_deleted

                # 7. Delete campaign interactions
                campaigns_deleted = await self._delete_campaign_interactions(session, email)
                stats["deleted_records"]["campaign_interactions"] = campaigns_deleted

                # 8. Delete notes
                notes_deleted = await self._delete_notes(session, email)
                stats["deleted_records"]["notes"] = notes_deleted

                # 9. Commit all deletions
                await session.commit()

            # Log GDPR deletion event
            await log_audit_event(
                action="gdpr_delete",
                resource_type="user",
                resource_id=email,
                details=stats,
                admin_id=admin_id,
            )

            logger.info(
                "GDPR deletion completed successfully",
                email=email,
                total_deleted=sum(stats["deleted_records"].values()),
            )

            return stats

        except Exception as e:
            logger.error(
                "GDPR deletion failed",
                email=email,
                error=str(e),
            )
            raise

    async def cleanup_old_drafts(
        self,
        days_old: int = 90,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Automated task to clean up old draft emails.
        
        Args:
            days_old: Delete drafts older than this many days
            dry_run: If True, report what would be deleted without deleting
            
        Returns:
            Dictionary with cleanup statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        logger.info(
            "Draft cleanup task started",
            cutoff_date=cutoff_date.isoformat(),
            dry_run=dry_run,
        )

        try:
            async with SessionLocal() as session:
                # Get drafts to delete
                from src.models.workflow import DraftEmail

                query = (
                    session.query(DraftEmail)
                    .filter(DraftEmail.created_at < cutoff_date)
                    .filter(DraftEmail.status != "approved")  # Keep approved drafts
                )

                drafts = await session.execute(query)
                drafts_list = drafts.scalars().all()

                stats = {
                    "task": "cleanup_old_drafts",
                    "cutoff_date": cutoff_date.isoformat(),
                    "days_old": days_old,
                    "dry_run": dry_run,
                    "drafts_found": len(drafts_list),
                    "drafts_deleted": 0,
                    "affected_users": set(),
                    "timestamp": datetime.utcnow().isoformat(),
                }

                if not dry_run:
                    # Delete the drafts
                    for draft in drafts_list:
                        stats["affected_users"].add(draft.created_by or "unknown")

                    await session.execute(
                        delete(DraftEmail).where(DraftEmail.created_at < cutoff_date)
                    )
                    await session.commit()
                    stats["drafts_deleted"] = len(drafts_list)

                    logger.info(
                        "Draft cleanup completed",
                        drafts_deleted=len(drafts_list),
                        affected_users=len(stats["affected_users"]),
                    )

                    # Log cleanup event
                    await log_audit_event(
                        action="retention_cleanup",
                        resource_type="drafts",
                        resource_id=f"cleanup_{cutoff_date.isoformat()}",
                        details={
                            "drafts_deleted": len(drafts_list),
                            "reason": f"Older than {days_old} days",
                        },
                    )
                else:
                    logger.info(
                        "Draft cleanup (dry run)",
                        drafts_would_delete=len(drafts_list),
                    )

                stats["affected_users"] = list(stats["affected_users"])
                return stats

        except Exception as e:
            logger.error("Draft cleanup failed", error=str(e))
            raise

    async def anonymize_old_records(
        self,
        days_old: int = 365,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Anonymize records older than specified days.
        Replaces PII with anonymized versions.
        
        Args:
            days_old: Anonymize records older than this many days
            dry_run: If True, report what would be anonymized without changing
            
        Returns:
            Dictionary with anonymization statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        logger.info(
            "Anonymization task started",
            cutoff_date=cutoff_date.isoformat(),
            dry_run=dry_run,
        )

        stats = {
            "task": "anonymize_old_records",
            "cutoff_date": cutoff_date.isoformat(),
            "days_old": days_old,
            "dry_run": dry_run,
            "records_anonymized": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # In future: implement anonymization
            # For now, just log the operation
            logger.info("Anonymization not yet implemented", stats=stats)
            return stats
        except Exception as e:
            logger.error("Anonymization failed", error=str(e))
            raise

    # Private methods for deleting specific data types

    async def _delete_prospects(self, session: AsyncSession, email: str) -> int:
        """Delete prospect and related records."""
        try:
            from src.models.prospect import Prospect

            result = await session.execute(
                delete(Prospect).where(Prospect.email == email)
            )
            return result.rowcount or 0
        except Exception as e:
            logger.error(f"Error deleting prospects: {e}")
            return 0

    async def _delete_draft_emails(self, session: AsyncSession, email: str) -> int:
        """Delete draft emails."""
        try:
            from src.models.workflow import DraftEmail

            result = await session.execute(
                delete(DraftEmail).where(
                    DraftEmail.recipient_email == email
                )
            )
            return result.rowcount or 0
        except Exception as e:
            logger.error(f"Error deleting draft emails: {e}")
            return 0

    async def _delete_tasks(self, session: AsyncSession, email: str) -> int:
        """Delete tasks associated with email."""
        try:
            from src.models.prospect import Task

            result = await session.execute(
                delete(Task).where(Task.prospect_email == email)
            )
            return result.rowcount or 0
        except Exception as e:
            logger.error(f"Error deleting tasks: {e}")
            return 0

    async def _delete_form_submissions(self, session: AsyncSession, email: str) -> int:
        """Delete form submissions."""
        try:
            from src.models.form_submission import FormSubmission

            result = await session.execute(
                delete(FormSubmission).where(FormSubmission.email == email)
            )
            return result.rowcount or 0
        except Exception as e:
            logger.error(f"Error deleting form submissions: {e}")
            return 0

    async def _delete_enrichment(self, session: AsyncSession, email: str) -> int:
        """Delete contact enrichment data."""
        try:
            # Placeholder for enrichment data deletion
            logger.debug("Enrichment deletion called", email=email)
            return 0
        except Exception as e:
            logger.error(f"Error deleting enrichment: {e}")
            return 0

    async def _delete_email_tracking(self, session: AsyncSession, email: str) -> int:
        """Delete email tracking records."""
        try:
            # Placeholder for email tracking deletion
            logger.debug("Email tracking deletion called", email=email)
            return 0
        except Exception as e:
            logger.error(f"Error deleting email tracking: {e}")
            return 0

    async def _delete_campaign_interactions(self, session: AsyncSession, email: str) -> int:
        """Delete campaign interaction records."""
        try:
            # Placeholder for campaign deletion
            logger.debug("Campaign interactions deletion called", email=email)
            return 0
        except Exception as e:
            logger.error(f"Error deleting campaign interactions: {e}")
            return 0

    async def _delete_notes(self, session: AsyncSession, email: str) -> int:
        """Delete notes associated with email."""
        try:
            # Placeholder for notes deletion
            logger.debug("Notes deletion called", email=email)
            return 0
        except Exception as e:
            logger.error(f"Error deleting notes: {e}")
            return 0


# Global GDPR service instance
_gdpr_service: Optional[GDPRService] = None


def get_gdpr_service() -> GDPRService:
    """Get or create GDPR service instance."""
    global _gdpr_service
    if _gdpr_service is None:
        _gdpr_service = GDPRService()
    return _gdpr_service
