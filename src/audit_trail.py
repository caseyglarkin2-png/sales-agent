"""Audit trail logging for compliance and monitoring."""
import json
from datetime import datetime
from typing import Any, Dict, Optional

from src.logger import get_logger

audit_logger = get_logger("audit")


class AuditEvent:
    """Structured audit event for logging."""

    def __init__(
        self,
        event_type: str,
        actor: str,
        resource: str,
        action: str,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize audit event."""
        self.event_id = f"{event_type}-{datetime.utcnow().isoformat()}"
        self.timestamp = datetime.utcnow().isoformat()
        self.event_type = event_type
        self.actor = actor
        self.resource = resource
        self.action = action
        self.status = status
        self.details = details or {}
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor,
            "resource": self.resource,
            "action": self.action,
            "status": self.status,
            "details": self.details,
            "metadata": self.metadata,
        }

    def log(self) -> None:
        """Log the audit event."""
        audit_logger.info(
            f"{self.event_type}: {self.action} on {self.resource}",
            extra=self.to_dict(),
        )


class AuditTrail:
    """Centralized audit trail management."""

    # Event types
    PROSPECT_INTAKE = "prospect_intake"
    PROSPECT_RESEARCH = "prospect_research"
    DRAFT_CREATED = "draft_created"
    DRAFT_SENT = "draft_sent"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    TASK_CREATED = "task_created"
    NOTE_CREATED = "note_created"
    CONNECTOR_ERROR = "connector_error"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    CONFIG_CHANGE = "config_change"
    SECURITY_ALERT = "security_alert"

    @staticmethod
    def log_prospect_intake(
        prospect_email: str,
        source: str,
        actor: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log prospect intake event."""
        event = AuditEvent(
            event_type=AuditTrail.PROSPECT_INTAKE,
            actor=actor,
            resource=prospect_email,
            action="intake",
            details={"source": source},
            metadata=metadata,
        )
        event.log()

    @staticmethod
    def log_draft_created(
        prospect_email: str,
        draft_id: str,
        actor: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log draft creation event."""
        event = AuditEvent(
            event_type=AuditTrail.DRAFT_CREATED,
            actor=actor,
            resource=prospect_email,
            action="create_draft",
            details={"draft_id": draft_id, "mode": "DRAFT_ONLY"},
            metadata=metadata,
        )
        event.log()

    @staticmethod
    def log_draft_sent(
        prospect_email: str,
        draft_id: str,
        approved_by: str,
        actor: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log draft send event."""
        event = AuditEvent(
            event_type=AuditTrail.DRAFT_SENT,
            actor=actor,
            resource=prospect_email,
            action="send_draft",
            details={
                "draft_id": draft_id,
                "approved_by": approved_by,
            },
            metadata=metadata,
        )
        event.log()

    @staticmethod
    def log_approval_requested(
        prospect_email: str,
        draft_id: str,
        requester: str,
        approver: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log approval request event."""
        event = AuditEvent(
            event_type=AuditTrail.APPROVAL_REQUESTED,
            actor=requester,
            resource=prospect_email,
            action="request_approval",
            details={
                "draft_id": draft_id,
                "approver": approver,
            },
            metadata=metadata,
        )
        event.log()

    @staticmethod
    def log_approval_granted(
        prospect_email: str,
        draft_id: str,
        approver: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log approval granted event."""
        event = AuditEvent(
            event_type=AuditTrail.APPROVAL_GRANTED,
            actor=approver,
            resource=prospect_email,
            action="approve",
            details={"draft_id": draft_id},
            metadata=metadata,
        )
        event.log()

    @staticmethod
    def log_approval_denied(
        prospect_email: str,
        draft_id: str,
        approver: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log approval denied event."""
        event = AuditEvent(
            event_type=AuditTrail.APPROVAL_DENIED,
            actor=approver,
            resource=prospect_email,
            action="deny_approval",
            status="denied",
            details={"draft_id": draft_id, "reason": reason},
            metadata=metadata,
        )
        event.log()

    @staticmethod
    def log_connector_error(
        connector_name: str,
        error_msg: str,
        resource: str = "unknown",
        actor: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log connector error event."""
        event = AuditEvent(
            event_type=AuditTrail.CONNECTOR_ERROR,
            actor=actor,
            resource=resource,
            action=f"{connector_name}_error",
            status="error",
            details={"connector": connector_name, "error": error_msg},
            metadata=metadata,
        )
        event.log()

    @staticmethod
    def log_auth_success(
        service: str,
        actor: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log successful authentication."""
        event = AuditEvent(
            event_type=AuditTrail.AUTH_SUCCESS,
            actor=actor,
            resource=service,
            action="authenticate",
            status="success",
            metadata=metadata,
        )
        event.log()

    @staticmethod
    def log_auth_failure(
        service: str,
        reason: str,
        actor: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log failed authentication."""
        event = AuditEvent(
            event_type=AuditTrail.AUTH_FAILURE,
            actor=actor,
            resource=service,
            action="authenticate",
            status="failed",
            details={"reason": reason},
            metadata=metadata,
        )
        event.log()

    @staticmethod
    def log_security_alert(
        alert_type: str,
        description: str,
        resource: str = "unknown",
        actor: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log security alert."""
        event = AuditEvent(
            event_type=AuditTrail.SECURITY_ALERT,
            actor=actor,
            resource=resource,
            action=alert_type,
            status="alert",
            details={"description": description},
            metadata=metadata,
        )
        event.log()

    @staticmethod
    def log_config_change(
        changed_by: str,
        config_key: str,
        old_value: Any,
        new_value: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log configuration change."""
        event = AuditEvent(
            event_type=AuditTrail.CONFIG_CHANGE,
            actor=changed_by,
            resource=config_key,
            action="update_config",
            details={
                "config_key": config_key,
                "old_value": str(old_value) if old_value else None,
                "new_value": str(new_value) if new_value else None,
            },
            metadata=metadata,
        )
        event.log()

    @staticmethod
    def log_task_created(
        prospect_email: str,
        task_id: str,
        title: str,
        actor: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log HubSpot task creation."""
        event = AuditEvent(
            event_type=AuditTrail.TASK_CREATED,
            actor=actor,
            resource=prospect_email,
            action="create_task",
            details={"task_id": task_id, "title": title},
            metadata=metadata,
        )
        event.log()


# Convenience function for GDPR/admin use
async def log_audit_event(
    action: str,
    resource_type: str,
    resource_id: str,
    details: Optional[Dict[str, Any]] = None,
    admin_id: Optional[str] = None,
) -> None:
    """
    Log an audit event for GDPR/admin actions.
    
    Args:
        action: Action performed (e.g., "gdpr_delete", "admin_override")
        resource_type: Type of resource (e.g., "user", "draft")
        resource_id: Resource identifier (e.g., email address)
        details: Additional details
        admin_id: Admin user who performed action
    """
    event = AuditEvent(
        event_type=action,
        actor=admin_id or "system",
        resource=f"{resource_type}:{resource_id}",
        action=action,
        details=details or {},
    )
    event.log()

