"""
CRM Sync Engine
===============
Bidirectional synchronization with CRM systems (HubSpot, Salesforce, etc.).
Handles field mapping, conflict resolution, and incremental sync.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
import structlog
import uuid

logger = structlog.get_logger(__name__)


class SyncDirection(str, Enum):
    """Direction of synchronization."""
    PUSH = "push"  # Local -> CRM
    PULL = "pull"  # CRM -> Local
    BIDIRECTIONAL = "bidirectional"


class SyncStatus(str, Enum):
    """Status of a sync operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ConflictResolution(str, Enum):
    """How to resolve conflicts."""
    CRM_WINS = "crm_wins"
    LOCAL_WINS = "local_wins"
    NEWEST_WINS = "newest_wins"
    MANUAL = "manual"


@dataclass
class FieldMapping:
    """Mapping between local and CRM fields."""
    local_field: str
    crm_field: str
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    transform_to_crm: Optional[Callable] = None
    transform_from_crm: Optional[Callable] = None
    is_required: bool = False
    default_value: Any = None
    
    def to_dict(self) -> dict:
        return {
            "local_field": self.local_field,
            "crm_field": self.crm_field,
            "direction": self.direction.value,
            "is_required": self.is_required,
            "default_value": self.default_value,
        }


@dataclass
class SyncConfig:
    """Configuration for sync operations."""
    id: str
    name: str
    crm_type: str  # hubspot, salesforce, pipedrive
    object_type: str  # contacts, companies, deals
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    field_mappings: list[FieldMapping] = field(default_factory=list)
    conflict_resolution: ConflictResolution = ConflictResolution.NEWEST_WINS
    sync_interval_minutes: int = 15
    is_active: bool = True
    filters: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "crm_type": self.crm_type,
            "object_type": self.object_type,
            "direction": self.direction.value,
            "field_mappings": [m.to_dict() for m in self.field_mappings],
            "conflict_resolution": self.conflict_resolution.value,
            "sync_interval_minutes": self.sync_interval_minutes,
            "is_active": self.is_active,
            "filters": self.filters,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class SyncRecord:
    """Record of a synced item."""
    id: str
    local_id: str
    crm_id: str
    object_type: str
    crm_type: str
    last_synced_at: datetime
    local_updated_at: Optional[datetime] = None
    crm_updated_at: Optional[datetime] = None
    sync_hash: str = ""  # Hash of synced data for change detection
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "local_id": self.local_id,
            "crm_id": self.crm_id,
            "object_type": self.object_type,
            "crm_type": self.crm_type,
            "last_synced_at": self.last_synced_at.isoformat(),
            "local_updated_at": self.local_updated_at.isoformat() if self.local_updated_at else None,
            "crm_updated_at": self.crm_updated_at.isoformat() if self.crm_updated_at else None,
        }


@dataclass
class SyncResult:
    """Result of a sync operation."""
    id: str
    config_id: str
    status: SyncStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_pushed: int = 0
    records_pulled: int = 0
    records_skipped: int = 0
    conflicts_resolved: int = 0
    errors: list[dict] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "config_id": self.config_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "records_pushed": self.records_pushed,
            "records_pulled": self.records_pulled,
            "records_skipped": self.records_skipped,
            "conflicts_resolved": self.conflicts_resolved,
            "errors": self.errors,
        }


class CRMSyncEngine:
    """
    Manages bidirectional synchronization with CRM systems.
    """
    
    def __init__(self):
        self.configs: dict[str, SyncConfig] = {}
        self.sync_records: dict[str, SyncRecord] = {}  # key: f"{crm_type}:{object_type}:{crm_id}"
        self.sync_history: list[SyncResult] = []
        self._setup_default_configs()
    
    def _setup_default_configs(self) -> None:
        """Set up default sync configurations."""
        # HubSpot contacts sync
        hubspot_contacts = self.create_config(
            name="HubSpot Contacts Sync",
            crm_type="hubspot",
            object_type="contacts",
            direction=SyncDirection.BIDIRECTIONAL,
        )
        
        # Add field mappings
        self.add_field_mapping(hubspot_contacts.id, "email", "email", SyncDirection.BIDIRECTIONAL, is_required=True)
        self.add_field_mapping(hubspot_contacts.id, "first_name", "firstname", SyncDirection.BIDIRECTIONAL)
        self.add_field_mapping(hubspot_contacts.id, "last_name", "lastname", SyncDirection.BIDIRECTIONAL)
        self.add_field_mapping(hubspot_contacts.id, "phone", "phone", SyncDirection.BIDIRECTIONAL)
        self.add_field_mapping(hubspot_contacts.id, "company", "company", SyncDirection.BIDIRECTIONAL)
        self.add_field_mapping(hubspot_contacts.id, "title", "jobtitle", SyncDirection.BIDIRECTIONAL)
        self.add_field_mapping(hubspot_contacts.id, "linkedin_url", "hs_linkedin_url", SyncDirection.PUSH)
        
        # HubSpot companies sync
        hubspot_companies = self.create_config(
            name="HubSpot Companies Sync",
            crm_type="hubspot",
            object_type="companies",
            direction=SyncDirection.BIDIRECTIONAL,
        )
        
        self.add_field_mapping(hubspot_companies.id, "name", "name", SyncDirection.BIDIRECTIONAL, is_required=True)
        self.add_field_mapping(hubspot_companies.id, "domain", "domain", SyncDirection.BIDIRECTIONAL)
        self.add_field_mapping(hubspot_companies.id, "industry", "industry", SyncDirection.BIDIRECTIONAL)
        self.add_field_mapping(hubspot_companies.id, "employee_count", "numberofemployees", SyncDirection.BIDIRECTIONAL)
        
        logger.info("default_sync_configs_created", count=2)
    
    def create_config(
        self,
        name: str,
        crm_type: str,
        object_type: str,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        conflict_resolution: ConflictResolution = ConflictResolution.NEWEST_WINS,
        sync_interval_minutes: int = 15,
    ) -> SyncConfig:
        """Create a sync configuration."""
        config = SyncConfig(
            id=str(uuid.uuid4()),
            name=name,
            crm_type=crm_type,
            object_type=object_type,
            direction=direction,
            conflict_resolution=conflict_resolution,
            sync_interval_minutes=sync_interval_minutes,
        )
        
        self.configs[config.id] = config
        
        logger.info("sync_config_created", config_id=config.id, name=name)
        
        return config
    
    def get_config(self, config_id: str) -> Optional[SyncConfig]:
        """Get a sync configuration by ID."""
        return self.configs.get(config_id)
    
    def list_configs(
        self,
        crm_type: str = None,
        object_type: str = None,
        active_only: bool = True,
    ) -> list[SyncConfig]:
        """List sync configurations."""
        configs = list(self.configs.values())
        
        if crm_type:
            configs = [c for c in configs if c.crm_type == crm_type]
        
        if object_type:
            configs = [c for c in configs if c.object_type == object_type]
        
        if active_only:
            configs = [c for c in configs if c.is_active]
        
        return configs
    
    def update_config(
        self,
        config_id: str,
        updates: dict,
    ) -> Optional[SyncConfig]:
        """Update a sync configuration."""
        config = self.configs.get(config_id)
        if not config:
            return None
        
        for key, value in updates.items():
            if hasattr(config, key) and key not in ["id", "created_at", "field_mappings"]:
                setattr(config, key, value)
        
        config.updated_at = datetime.utcnow()
        return config
    
    def delete_config(self, config_id: str) -> bool:
        """Delete a sync configuration."""
        if config_id in self.configs:
            del self.configs[config_id]
            return True
        return False
    
    def add_field_mapping(
        self,
        config_id: str,
        local_field: str,
        crm_field: str,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        is_required: bool = False,
        default_value: Any = None,
    ) -> Optional[FieldMapping]:
        """Add a field mapping to a configuration."""
        config = self.configs.get(config_id)
        if not config:
            return None
        
        mapping = FieldMapping(
            local_field=local_field,
            crm_field=crm_field,
            direction=direction,
            is_required=is_required,
            default_value=default_value,
        )
        
        config.field_mappings.append(mapping)
        config.updated_at = datetime.utcnow()
        
        return mapping
    
    def remove_field_mapping(
        self,
        config_id: str,
        local_field: str,
    ) -> bool:
        """Remove a field mapping from a configuration."""
        config = self.configs.get(config_id)
        if not config:
            return False
        
        for i, mapping in enumerate(config.field_mappings):
            if mapping.local_field == local_field:
                config.field_mappings.pop(i)
                config.updated_at = datetime.utcnow()
                return True
        
        return False
    
    def sync(
        self,
        config_id: str,
        local_records: list[dict] = None,
        crm_records: list[dict] = None,
    ) -> SyncResult:
        """Run a sync operation."""
        config = self.configs.get(config_id)
        if not config:
            return SyncResult(
                id=str(uuid.uuid4()),
                config_id=config_id,
                status=SyncStatus.FAILED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                errors=[{"message": "Config not found"}],
            )
        
        result = SyncResult(
            id=str(uuid.uuid4()),
            config_id=config_id,
            status=SyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
        )
        
        try:
            # Push local records to CRM
            if config.direction in [SyncDirection.PUSH, SyncDirection.BIDIRECTIONAL]:
                if local_records:
                    for record in local_records:
                        push_result = self._push_record(config, record)
                        if push_result.get("success"):
                            result.records_pushed += 1
                        elif push_result.get("skipped"):
                            result.records_skipped += 1
                        else:
                            result.errors.append(push_result.get("error", {}))
            
            # Pull CRM records to local
            if config.direction in [SyncDirection.PULL, SyncDirection.BIDIRECTIONAL]:
                if crm_records:
                    for record in crm_records:
                        pull_result = self._pull_record(config, record)
                        if pull_result.get("success"):
                            result.records_pulled += 1
                        elif pull_result.get("conflict"):
                            result.conflicts_resolved += 1
                        elif pull_result.get("skipped"):
                            result.records_skipped += 1
                        else:
                            result.errors.append(pull_result.get("error", {}))
            
            result.status = SyncStatus.COMPLETED if not result.errors else SyncStatus.PARTIAL
            
        except Exception as e:
            result.status = SyncStatus.FAILED
            result.errors.append({"message": str(e)})
            logger.error("sync_failed", config_id=config_id, error=str(e))
        
        result.completed_at = datetime.utcnow()
        self.sync_history.append(result)
        
        logger.info(
            "sync_completed",
            config_id=config_id,
            pushed=result.records_pushed,
            pulled=result.records_pulled,
            status=result.status.value,
        )
        
        return result
    
    def _push_record(
        self,
        config: SyncConfig,
        local_record: dict,
    ) -> dict:
        """Push a local record to CRM."""
        local_id = local_record.get("id")
        
        # Check if already synced
        sync_key = f"{config.crm_type}:{config.object_type}:{local_id}"
        existing = self.sync_records.get(sync_key)
        
        # Map fields
        crm_data = {}
        for mapping in config.field_mappings:
            if mapping.direction in [SyncDirection.PUSH, SyncDirection.BIDIRECTIONAL]:
                value = local_record.get(mapping.local_field, mapping.default_value)
                if mapping.transform_to_crm and value is not None:
                    value = mapping.transform_to_crm(value)
                if value is not None or mapping.is_required:
                    crm_data[mapping.crm_field] = value
        
        # Simulate CRM push (would use actual API in production)
        crm_id = existing.crm_id if existing else f"crm_{uuid.uuid4().hex[:8]}"
        
        # Create/update sync record
        sync_record = SyncRecord(
            id=str(uuid.uuid4()),
            local_id=local_id,
            crm_id=crm_id,
            object_type=config.object_type,
            crm_type=config.crm_type,
            last_synced_at=datetime.utcnow(),
            local_updated_at=local_record.get("updated_at"),
        )
        self.sync_records[sync_key] = sync_record
        
        return {"success": True, "crm_id": crm_id}
    
    def _pull_record(
        self,
        config: SyncConfig,
        crm_record: dict,
    ) -> dict:
        """Pull a CRM record to local."""
        crm_id = crm_record.get("id")
        
        # Map fields
        local_data = {}
        for mapping in config.field_mappings:
            if mapping.direction in [SyncDirection.PULL, SyncDirection.BIDIRECTIONAL]:
                value = crm_record.get(mapping.crm_field, mapping.default_value)
                if mapping.transform_from_crm and value is not None:
                    value = mapping.transform_from_crm(value)
                if value is not None or mapping.is_required:
                    local_data[mapping.local_field] = value
        
        # Simulate local update (would update actual database in production)
        local_id = f"local_{uuid.uuid4().hex[:8]}"
        
        # Create sync record
        sync_key = f"{config.crm_type}:{config.object_type}:{crm_id}"
        sync_record = SyncRecord(
            id=str(uuid.uuid4()),
            local_id=local_id,
            crm_id=crm_id,
            object_type=config.object_type,
            crm_type=config.crm_type,
            last_synced_at=datetime.utcnow(),
            crm_updated_at=crm_record.get("updated_at"),
        )
        self.sync_records[sync_key] = sync_record
        
        return {"success": True, "local_id": local_id, "data": local_data}
    
    def get_sync_history(
        self,
        config_id: str = None,
        limit: int = 50,
    ) -> list[SyncResult]:
        """Get sync history."""
        history = self.sync_history
        
        if config_id:
            history = [h for h in history if h.config_id == config_id]
        
        return sorted(history, key=lambda h: h.started_at, reverse=True)[:limit]
    
    def get_sync_record(
        self,
        crm_type: str,
        object_type: str,
        crm_id: str,
    ) -> Optional[SyncRecord]:
        """Get a sync record by CRM details."""
        sync_key = f"{crm_type}:{object_type}:{crm_id}"
        return self.sync_records.get(sync_key)
    
    def get_pending_syncs(self) -> list[SyncConfig]:
        """Get configs that need to be synced."""
        now = datetime.utcnow()
        pending = []
        
        for config in self.configs.values():
            if not config.is_active:
                continue
            
            # Check last sync time
            last_sync = None
            for result in self.sync_history:
                if result.config_id == config.id and result.status == SyncStatus.COMPLETED:
                    if not last_sync or result.completed_at > last_sync:
                        last_sync = result.completed_at
            
            # If never synced or past interval, add to pending
            if not last_sync or (now - last_sync) > timedelta(minutes=config.sync_interval_minutes):
                pending.append(config)
        
        return pending
    
    def get_sync_stats(self) -> dict:
        """Get overall sync statistics."""
        total_syncs = len(self.sync_history)
        successful = len([h for h in self.sync_history if h.status == SyncStatus.COMPLETED])
        failed = len([h for h in self.sync_history if h.status == SyncStatus.FAILED])
        
        total_pushed = sum(h.records_pushed for h in self.sync_history)
        total_pulled = sum(h.records_pulled for h in self.sync_history)
        
        return {
            "total_syncs": total_syncs,
            "successful_syncs": successful,
            "failed_syncs": failed,
            "success_rate": (successful / total_syncs * 100) if total_syncs > 0 else 0,
            "total_records_pushed": total_pushed,
            "total_records_pulled": total_pulled,
            "active_configs": len([c for c in self.configs.values() if c.is_active]),
            "synced_records": len(self.sync_records),
        }


# Singleton instance
_engine: Optional[CRMSyncEngine] = None


def get_crm_sync_engine() -> CRMSyncEngine:
    """Get the CRM sync engine singleton."""
    global _engine
    if _engine is None:
        _engine = CRMSyncEngine()
    return _engine
