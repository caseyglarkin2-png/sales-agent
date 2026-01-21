"""
Audit Service - Comprehensive Audit Trail
==========================================
Tracks all system actions for compliance and debugging.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Types of audit actions."""
    # CRUD operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGE = "password_change"
    TOKEN_REFRESH = "token_refresh"
    
    # API operations
    API_CALL = "api_call"
    WEBHOOK_RECEIVED = "webhook_received"
    WEBHOOK_SENT = "webhook_sent"
    
    # Email operations
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_BOUNCED = "email_bounced"
    
    # Sync operations
    SYNC_STARTED = "sync_started"
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"
    
    # Import/Export
    IMPORT_STARTED = "import_started"
    IMPORT_COMPLETED = "import_completed"
    EXPORT_STARTED = "export_started"
    EXPORT_COMPLETED = "export_completed"
    
    # Settings
    SETTINGS_CHANGED = "settings_changed"
    PERMISSION_CHANGED = "permission_changed"
    
    # Other
    SEARCH = "search"
    BULK_ACTION = "bulk_action"
    ERROR = "error"


class ResourceType(str, Enum):
    """Types of resources being audited."""
    CONTACT = "contact"
    COMPANY = "company"
    DEAL = "deal"
    EMAIL = "email"
    SEQUENCE = "sequence"
    CAMPAIGN = "campaign"
    TEMPLATE = "template"
    TASK = "task"
    NOTE = "note"
    MEETING = "meeting"
    CALL = "call"
    USER = "user"
    TEAM = "team"
    INTEGRATION = "integration"
    SETTINGS = "settings"
    SEGMENT = "segment"
    WORKFLOW = "workflow"
    REPORT = "report"
    GOAL = "goal"
    PIPELINE = "pipeline"
    API_KEY = "api_key"
    WEBHOOK = "webhook"
    SYSTEM = "system"


class AuditSeverity(str, Enum):
    """Severity levels for audit entries."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """Single audit log entry."""
    id: str
    timestamp: datetime
    action: AuditAction
    resource_type: ResourceType
    resource_id: Optional[str]
    user_id: Optional[str]
    user_email: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    description: str
    severity: AuditSeverity = AuditSeverity.INFO
    
    # Change tracking
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    
    # Request context
    request_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[int] = None
    
    # Additional metadata
    metadata: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    
    # Session info
    session_id: Optional[str] = None
    organization_id: Optional[str] = None


@dataclass
class AuditSearchResult:
    """Paginated audit search results."""
    entries: list[AuditEntry]
    total: int
    page: int
    page_size: int
    has_more: bool


@dataclass
class AuditStats:
    """Statistics about audit entries."""
    total_entries: int
    actions_by_type: dict[str, int]
    resources_by_type: dict[str, int]
    entries_by_severity: dict[str, int]
    entries_by_hour: dict[str, int]
    top_users: list[dict]
    recent_errors: list[AuditEntry]


class AuditService:
    """Service for audit logging."""
    
    def __init__(self):
        self.entries: list[AuditEntry] = []
        self._max_entries = 10000  # In-memory limit
        self._retention_days = 90
        self._create_sample_entries()
    
    def _create_sample_entries(self):
        """Create sample audit entries for demo."""
        now = datetime.utcnow()
        
        samples = [
            AuditEntry(
                id="audit_1",
                timestamp=now - timedelta(hours=1),
                action=AuditAction.CREATE,
                resource_type=ResourceType.CONTACT,
                resource_id="contact_123",
                user_id="user_1",
                user_email="admin@example.com",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
                description="Created new contact: John Doe",
                new_values={"name": "John Doe", "email": "john@example.com"}
            ),
            AuditEntry(
                id="audit_2",
                timestamp=now - timedelta(hours=2),
                action=AuditAction.EMAIL_SENT,
                resource_type=ResourceType.EMAIL,
                resource_id="email_456",
                user_id="user_1",
                user_email="admin@example.com",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
                description="Sent outreach email to john@example.com",
                metadata={"recipient": "john@example.com", "subject": "Quick question"}
            ),
            AuditEntry(
                id="audit_3",
                timestamp=now - timedelta(hours=3),
                action=AuditAction.LOGIN,
                resource_type=ResourceType.USER,
                resource_id="user_1",
                user_id="user_1",
                user_email="admin@example.com",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0",
                description="User logged in successfully"
            ),
            AuditEntry(
                id="audit_4",
                timestamp=now - timedelta(hours=4),
                action=AuditAction.SYNC_COMPLETED,
                resource_type=ResourceType.INTEGRATION,
                resource_id="hubspot_integration",
                user_id="system",
                user_email=None,
                ip_address=None,
                user_agent=None,
                description="HubSpot sync completed: 150 contacts synced",
                metadata={"contacts_synced": 150, "duration_seconds": 45}
            ),
            AuditEntry(
                id="audit_5",
                timestamp=now - timedelta(hours=5),
                action=AuditAction.ERROR,
                resource_type=ResourceType.EMAIL,
                resource_id="email_789",
                user_id="user_2",
                user_email="sales@example.com",
                ip_address="192.168.1.101",
                user_agent="Mozilla/5.0",
                description="Email delivery failed: Invalid recipient address",
                severity=AuditSeverity.ERROR,
                metadata={"error_code": "invalid_recipient", "recipient": "bad@email"}
            )
        ]
        
        self.entries.extend(samples)
    
    async def log(
        self,
        action: AuditAction,
        resource_type: ResourceType,
        description: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        request_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[dict] = None,
        tags: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> AuditEntry:
        """Log an audit entry."""
        entry = AuditEntry(
            id=f"audit_{uuid4().hex[:12]}",
            timestamp=datetime.utcnow(),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            description=description,
            severity=severity,
            old_values=old_values,
            new_values=new_values,
            request_id=request_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            metadata=metadata or {},
            tags=tags or [],
            session_id=session_id,
            organization_id=organization_id
        )
        
        self.entries.append(entry)
        
        # Enforce max entries limit
        if len(self.entries) > self._max_entries:
            self.entries = self.entries[-self._max_entries:]
        
        # Log to standard logger as well
        log_level = {
            AuditSeverity.DEBUG: logging.DEBUG,
            AuditSeverity.INFO: logging.INFO,
            AuditSeverity.WARNING: logging.WARNING,
            AuditSeverity.ERROR: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL
        }.get(severity, logging.INFO)
        
        logger.log(
            log_level,
            f"AUDIT: {action.value} {resource_type.value} - {description}",
            extra={
                "audit_id": entry.id,
                "action": action.value,
                "resource_type": resource_type.value,
                "resource_id": resource_id,
                "user_id": user_id
            }
        )
        
        return entry
    
    async def log_create(
        self,
        resource_type: ResourceType,
        resource_id: str,
        description: str,
        new_values: Optional[dict] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> AuditEntry:
        """Shortcut to log a CREATE action."""
        return await self.log(
            action=AuditAction.CREATE,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            new_values=new_values,
            user_id=user_id,
            **kwargs
        )
    
    async def log_update(
        self,
        resource_type: ResourceType,
        resource_id: str,
        description: str,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> AuditEntry:
        """Shortcut to log an UPDATE action."""
        return await self.log(
            action=AuditAction.UPDATE,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_values=old_values,
            new_values=new_values,
            user_id=user_id,
            **kwargs
        )
    
    async def log_delete(
        self,
        resource_type: ResourceType,
        resource_id: str,
        description: str,
        old_values: Optional[dict] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> AuditEntry:
        """Shortcut to log a DELETE action."""
        return await self.log(
            action=AuditAction.DELETE,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            old_values=old_values,
            user_id=user_id,
            **kwargs
        )
    
    async def log_error(
        self,
        resource_type: ResourceType,
        description: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> AuditEntry:
        """Shortcut to log an ERROR."""
        return await self.log(
            action=AuditAction.ERROR,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            severity=AuditSeverity.ERROR,
            user_id=user_id,
            **kwargs
        )
    
    async def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """Get a specific audit entry by ID."""
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None
    
    async def search(
        self,
        action: Optional[AuditAction] = None,
        resource_type: Optional[ResourceType] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        query: Optional[str] = None,
        tags: Optional[list[str]] = None,
        page: int = 1,
        page_size: int = 50
    ) -> AuditSearchResult:
        """Search audit entries with filters."""
        results = self.entries.copy()
        
        if action:
            results = [e for e in results if e.action == action]
        
        if resource_type:
            results = [e for e in results if e.resource_type == resource_type]
        
        if resource_id:
            results = [e for e in results if e.resource_id == resource_id]
        
        if user_id:
            results = [e for e in results if e.user_id == user_id]
        
        if user_email:
            results = [e for e in results if e.user_email == user_email]
        
        if severity:
            results = [e for e in results if e.severity == severity]
        
        if start_date:
            results = [e for e in results if e.timestamp >= start_date]
        
        if end_date:
            results = [e for e in results if e.timestamp <= end_date]
        
        if ip_address:
            results = [e for e in results if e.ip_address == ip_address]
        
        if query:
            query = query.lower()
            results = [
                e for e in results
                if query in e.description.lower()
                or (e.user_email and query in e.user_email.lower())
            ]
        
        if tags:
            results = [
                e for e in results
                if any(tag in e.tags for tag in tags)
            ]
        
        # Sort by timestamp descending (newest first)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        
        total = len(results)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_entries = results[start_idx:end_idx]
        
        return AuditSearchResult(
            entries=page_entries,
            total=total,
            page=page,
            page_size=page_size,
            has_more=end_idx < total
        )
    
    async def get_resource_history(
        self,
        resource_type: ResourceType,
        resource_id: str,
        limit: int = 50
    ) -> list[AuditEntry]:
        """Get complete audit history for a resource."""
        results = [
            e for e in self.entries
            if e.resource_type == resource_type and e.resource_id == resource_id
        ]
        
        results.sort(key=lambda e: e.timestamp, reverse=True)
        
        return results[:limit]
    
    async def get_user_activity(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        limit: int = 100
    ) -> list[AuditEntry]:
        """Get all activity for a user."""
        results = [e for e in self.entries if e.user_id == user_id]
        
        if start_date:
            results = [e for e in results if e.timestamp >= start_date]
        
        results.sort(key=lambda e: e.timestamp, reverse=True)
        
        return results[:limit]
    
    async def get_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AuditStats:
        """Get audit statistics."""
        entries = self.entries.copy()
        
        if start_date:
            entries = [e for e in entries if e.timestamp >= start_date]
        if end_date:
            entries = [e for e in entries if e.timestamp <= end_date]
        
        # Actions by type
        actions_by_type: dict[str, int] = {}
        for entry in entries:
            action = entry.action.value
            actions_by_type[action] = actions_by_type.get(action, 0) + 1
        
        # Resources by type
        resources_by_type: dict[str, int] = {}
        for entry in entries:
            resource = entry.resource_type.value
            resources_by_type[resource] = resources_by_type.get(resource, 0) + 1
        
        # Entries by severity
        entries_by_severity: dict[str, int] = {}
        for entry in entries:
            severity = entry.severity.value
            entries_by_severity[severity] = entries_by_severity.get(severity, 0) + 1
        
        # Entries by hour
        entries_by_hour: dict[str, int] = {}
        for entry in entries:
            hour = entry.timestamp.strftime("%Y-%m-%d %H:00")
            entries_by_hour[hour] = entries_by_hour.get(hour, 0) + 1
        
        # Top users
        user_counts: dict[str, int] = {}
        for entry in entries:
            if entry.user_id:
                user_counts[entry.user_id] = user_counts.get(entry.user_id, 0) + 1
        
        top_users = sorted(
            [{"user_id": uid, "count": count} for uid, count in user_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]
        
        # Recent errors
        recent_errors = [
            e for e in entries
            if e.severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]
        ]
        recent_errors.sort(key=lambda e: e.timestamp, reverse=True)
        recent_errors = recent_errors[:10]
        
        return AuditStats(
            total_entries=len(entries),
            actions_by_type=actions_by_type,
            resources_by_type=resources_by_type,
            entries_by_severity=entries_by_severity,
            entries_by_hour=entries_by_hour,
            top_users=top_users,
            recent_errors=recent_errors
        )
    
    async def export_entries(
        self,
        format: str = "json",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Export audit entries."""
        entries = self.entries.copy()
        
        if start_date:
            entries = [e for e in entries if e.timestamp >= start_date]
        if end_date:
            entries = [e for e in entries if e.timestamp <= end_date]
        
        entries.sort(key=lambda e: e.timestamp)
        
        if format == "json":
            return {
                "export_date": datetime.utcnow().isoformat(),
                "total_entries": len(entries),
                "entries": [
                    {
                        "id": e.id,
                        "timestamp": e.timestamp.isoformat(),
                        "action": e.action.value,
                        "resource_type": e.resource_type.value,
                        "resource_id": e.resource_id,
                        "user_id": e.user_id,
                        "user_email": e.user_email,
                        "ip_address": e.ip_address,
                        "description": e.description,
                        "severity": e.severity.value,
                        "old_values": e.old_values,
                        "new_values": e.new_values,
                        "metadata": e.metadata
                    }
                    for e in entries
                ]
            }
        
        return {"error": f"Unsupported format: {format}"}
    
    async def cleanup_old_entries(self, days: Optional[int] = None) -> int:
        """Remove entries older than retention period."""
        retention_days = days or self._retention_days
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        
        original_count = len(self.entries)
        self.entries = [e for e in self.entries if e.timestamp >= cutoff]
        
        removed = original_count - len(self.entries)
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} old audit entries")
        
        return removed


# Global service instance
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """Get or create the audit service singleton."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
