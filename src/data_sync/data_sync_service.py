"""
Data Sync Service - Synchronization and Change Tracking
========================================================
Handles data sync between clients, conflict resolution, and change tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid
import hashlib
import json


class SyncOperation(str, Enum):
    """Types of sync operations."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class SyncStatus(str, Enum):
    """Sync status."""
    PENDING = "pending"
    SYNCING = "syncing"
    SYNCED = "synced"
    CONFLICT = "conflict"
    ERROR = "error"


class ConflictResolution(str, Enum):
    """Conflict resolution strategies."""
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"
    LATEST_WINS = "latest_wins"
    MERGE = "merge"
    MANUAL = "manual"


class EntityType(str, Enum):
    """Entity types for sync."""
    CONTACT = "contact"
    ACCOUNT = "account"
    DEAL = "deal"
    TASK = "task"
    MEETING = "meeting"
    NOTE = "note"
    ACTIVITY = "activity"


@dataclass
class ChangeRecord:
    """Record of a data change."""
    id: str
    entity_type: EntityType
    entity_id: str
    operation: SyncOperation
    version: int
    data: dict[str, Any]
    previous_data: Optional[dict[str, Any]] = None
    changed_fields: list[str] = field(default_factory=list)
    checksum: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    synced: bool = False


@dataclass
class SyncConflict:
    """Conflict between local and server data."""
    id: str
    entity_type: EntityType
    entity_id: str
    local_version: int
    server_version: int
    local_data: dict[str, Any]
    server_data: dict[str, Any]
    conflicting_fields: list[str]
    resolution: Optional[ConflictResolution] = None
    resolved_data: Optional[dict[str, Any]] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SyncRecord:
    """Sync operation record."""
    id: str
    client_id: str
    user_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: SyncStatus = SyncStatus.PENDING
    changes_pushed: int = 0
    changes_pulled: int = 0
    conflicts_count: int = 0
    errors: list[str] = field(default_factory=list)
    last_sync_token: Optional[str] = None


@dataclass
class ClientState:
    """Client sync state."""
    client_id: str
    user_id: str
    last_sync_at: Optional[datetime] = None
    last_sync_token: Optional[str] = None
    pending_changes: list[str] = field(default_factory=list)  # Change IDs
    version_map: dict[str, int] = field(default_factory=dict)  # entity_key -> version


class DataSyncService:
    """Service for data synchronization."""
    
    def __init__(self):
        """Initialize data sync service."""
        self.changes: dict[str, ChangeRecord] = {}
        self.conflicts: dict[str, SyncConflict] = {}
        self.sync_records: dict[str, SyncRecord] = {}
        self.client_states: dict[str, ClientState] = {}
        self._entity_versions: dict[str, int] = {}  # entity_key -> current version
        self._entity_data: dict[str, dict[str, Any]] = {}  # entity_key -> data
        self._change_index: dict[str, list[str]] = {}  # entity_key -> change_ids
    
    def _entity_key(self, entity_type: EntityType, entity_id: str) -> str:
        """Generate entity key."""
        return f"{entity_type.value}:{entity_id}"
    
    def _compute_checksum(self, data: dict[str, Any]) -> str:
        """Compute checksum for data."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(serialized.encode()).hexdigest()
    
    def _generate_sync_token(self) -> str:
        """Generate a sync token."""
        return f"sync_{uuid.uuid4().hex[:16]}_{int(datetime.utcnow().timestamp())}"
    
    async def record_change(
        self,
        entity_type: EntityType,
        entity_id: str,
        operation: SyncOperation,
        data: dict[str, Any],
        previous_data: Optional[dict[str, Any]] = None,
        user_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> ChangeRecord:
        """Record a data change."""
        entity_key = self._entity_key(entity_type, entity_id)
        
        # Get or initialize version
        current_version = self._entity_versions.get(entity_key, 0)
        new_version = current_version + 1
        
        # Determine changed fields
        changed_fields = []
        if previous_data and operation == SyncOperation.UPDATE:
            for key in set(list(data.keys()) + list(previous_data.keys())):
                if data.get(key) != previous_data.get(key):
                    changed_fields.append(key)
        
        change_id = str(uuid.uuid4())
        
        change = ChangeRecord(
            id=change_id,
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            version=new_version,
            data=data,
            previous_data=previous_data,
            changed_fields=changed_fields,
            checksum=self._compute_checksum(data),
            user_id=user_id,
            device_id=device_id,
        )
        
        self.changes[change_id] = change
        
        # Update version and data
        self._entity_versions[entity_key] = new_version
        if operation != SyncOperation.DELETE:
            self._entity_data[entity_key] = data
        else:
            self._entity_data.pop(entity_key, None)
        
        # Update change index
        if entity_key not in self._change_index:
            self._change_index[entity_key] = []
        self._change_index[entity_key].append(change_id)
        
        return change
    
    async def get_changes_since(
        self,
        since_token: Optional[str] = None,
        entity_types: Optional[list[EntityType]] = None,
        limit: int = 1000,
    ) -> tuple[list[ChangeRecord], str]:
        """Get changes since a sync token."""
        changes = list(self.changes.values())
        
        # Filter by sync token (timestamp based)
        if since_token:
            try:
                # Extract timestamp from token
                parts = since_token.split("_")
                if len(parts) >= 3:
                    token_ts = int(parts[2])
                    since_dt = datetime.fromtimestamp(token_ts)
                    changes = [c for c in changes if c.timestamp > since_dt]
            except (ValueError, IndexError):
                pass
        
        # Filter by entity types
        if entity_types:
            changes = [c for c in changes if c.entity_type in entity_types]
        
        # Sort by timestamp
        changes = sorted(changes, key=lambda c: c.timestamp)
        
        # Limit results
        changes = changes[:limit]
        
        # Generate new sync token
        new_token = self._generate_sync_token()
        
        return changes, new_token
    
    async def push_changes(
        self,
        client_id: str,
        user_id: str,
        changes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Push changes from client to server."""
        sync_id = str(uuid.uuid4())
        
        sync_record = SyncRecord(
            id=sync_id,
            client_id=client_id,
            user_id=user_id,
            status=SyncStatus.SYNCING,
        )
        self.sync_records[sync_id] = sync_record
        
        # Get or create client state
        if client_id not in self.client_states:
            self.client_states[client_id] = ClientState(
                client_id=client_id,
                user_id=user_id,
            )
        client_state = self.client_states[client_id]
        
        applied = []
        conflicts = []
        errors = []
        
        for change_data in changes:
            try:
                entity_type = EntityType(change_data.get("entity_type"))
                entity_id = change_data.get("entity_id")
                operation = SyncOperation(change_data.get("operation"))
                data = change_data.get("data", {})
                client_version = change_data.get("version", 0)
                
                entity_key = self._entity_key(entity_type, entity_id)
                server_version = self._entity_versions.get(entity_key, 0)
                
                # Check for conflicts
                if client_version < server_version:
                    # Conflict detected
                    conflict = await self._create_conflict(
                        entity_type, entity_id,
                        client_version, server_version,
                        data, self._entity_data.get(entity_key, {})
                    )
                    conflicts.append(conflict)
                    sync_record.conflicts_count += 1
                else:
                    # Apply change
                    change = await self.record_change(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        operation=operation,
                        data=data,
                        user_id=user_id,
                        device_id=client_id,
                    )
                    change.synced = True
                    applied.append(change.id)
                    sync_record.changes_pushed += 1
                    
                    # Update client version map
                    client_state.version_map[entity_key] = change.version
                    
            except Exception as e:
                errors.append(str(e))
                sync_record.errors.append(str(e))
        
        sync_record.status = SyncStatus.SYNCED if not conflicts else SyncStatus.CONFLICT
        sync_record.completed_at = datetime.utcnow()
        sync_record.last_sync_token = self._generate_sync_token()
        
        client_state.last_sync_at = datetime.utcnow()
        client_state.last_sync_token = sync_record.last_sync_token
        
        return {
            "sync_id": sync_id,
            "applied": applied,
            "conflicts": [c.id for c in conflicts],
            "errors": errors,
            "sync_token": sync_record.last_sync_token,
        }
    
    async def pull_changes(
        self,
        client_id: str,
        user_id: str,
        since_token: Optional[str] = None,
        entity_types: Optional[list[EntityType]] = None,
    ) -> dict[str, Any]:
        """Pull changes from server to client."""
        # Get client state
        client_state = self.client_states.get(client_id)
        
        # Use client's last sync token if not provided
        if not since_token and client_state:
            since_token = client_state.last_sync_token
        
        changes, new_token = await self.get_changes_since(
            since_token=since_token,
            entity_types=entity_types,
        )
        
        # Update client state
        if not client_state:
            client_state = ClientState(
                client_id=client_id,
                user_id=user_id,
            )
            self.client_states[client_id] = client_state
        
        client_state.last_sync_at = datetime.utcnow()
        client_state.last_sync_token = new_token
        
        return {
            "changes": [
                {
                    "id": c.id,
                    "entity_type": c.entity_type.value,
                    "entity_id": c.entity_id,
                    "operation": c.operation.value,
                    "version": c.version,
                    "data": c.data,
                    "changed_fields": c.changed_fields,
                    "timestamp": c.timestamp.isoformat(),
                }
                for c in changes
            ],
            "sync_token": new_token,
            "has_more": False,  # Pagination support
        }
    
    async def _create_conflict(
        self,
        entity_type: EntityType,
        entity_id: str,
        local_version: int,
        server_version: int,
        local_data: dict[str, Any],
        server_data: dict[str, Any],
    ) -> SyncConflict:
        """Create a sync conflict."""
        conflict_id = str(uuid.uuid4())
        
        # Determine conflicting fields
        conflicting_fields = []
        all_keys = set(list(local_data.keys()) + list(server_data.keys()))
        for key in all_keys:
            if local_data.get(key) != server_data.get(key):
                conflicting_fields.append(key)
        
        conflict = SyncConflict(
            id=conflict_id,
            entity_type=entity_type,
            entity_id=entity_id,
            local_version=local_version,
            server_version=server_version,
            local_data=local_data,
            server_data=server_data,
            conflicting_fields=conflicting_fields,
        )
        
        self.conflicts[conflict_id] = conflict
        return conflict
    
    async def resolve_conflict(
        self,
        conflict_id: str,
        resolution: ConflictResolution,
        resolved_data: Optional[dict[str, Any]] = None,
        resolved_by: Optional[str] = None,
    ) -> Optional[SyncConflict]:
        """Resolve a sync conflict."""
        conflict = self.conflicts.get(conflict_id)
        if not conflict:
            return None
        
        conflict.resolution = resolution
        conflict.resolved_at = datetime.utcnow()
        conflict.resolved_by = resolved_by
        
        # Determine final data based on resolution
        if resolution == ConflictResolution.SERVER_WINS:
            conflict.resolved_data = conflict.server_data
        elif resolution == ConflictResolution.CLIENT_WINS:
            conflict.resolved_data = conflict.local_data
        elif resolution == ConflictResolution.LATEST_WINS:
            # Compare timestamps if available
            conflict.resolved_data = conflict.server_data  # Default to server
        elif resolution == ConflictResolution.MERGE:
            # Merge: server data with local changes
            merged = dict(conflict.server_data)
            merged.update(conflict.local_data)
            conflict.resolved_data = merged
        elif resolution == ConflictResolution.MANUAL:
            if not resolved_data:
                return None
            conflict.resolved_data = resolved_data
        
        # Apply resolved data
        if conflict.resolved_data:
            await self.record_change(
                entity_type=conflict.entity_type,
                entity_id=conflict.entity_id,
                operation=SyncOperation.UPDATE,
                data=conflict.resolved_data,
                previous_data=conflict.server_data,
                user_id=resolved_by,
            )
        
        return conflict
    
    async def get_conflict(self, conflict_id: str) -> Optional[SyncConflict]:
        """Get conflict by ID."""
        return self.conflicts.get(conflict_id)
    
    async def list_conflicts(
        self,
        user_id: Optional[str] = None,
        resolved: Optional[bool] = None,
    ) -> list[SyncConflict]:
        """List sync conflicts."""
        conflicts = list(self.conflicts.values())
        
        if resolved is not None:
            if resolved:
                conflicts = [c for c in conflicts if c.resolved_at is not None]
            else:
                conflicts = [c for c in conflicts if c.resolved_at is None]
        
        return sorted(conflicts, key=lambda c: c.created_at, reverse=True)
    
    async def get_entity_version(
        self,
        entity_type: EntityType,
        entity_id: str
    ) -> int:
        """Get current version of an entity."""
        entity_key = self._entity_key(entity_type, entity_id)
        return self._entity_versions.get(entity_key, 0)
    
    async def get_entity_history(
        self,
        entity_type: EntityType,
        entity_id: str,
        limit: int = 50,
    ) -> list[ChangeRecord]:
        """Get change history for an entity."""
        entity_key = self._entity_key(entity_type, entity_id)
        change_ids = self._change_index.get(entity_key, [])
        
        changes = []
        for cid in change_ids[-limit:]:
            change = self.changes.get(cid)
            if change:
                changes.append(change)
        
        return sorted(changes, key=lambda c: c.timestamp, reverse=True)
    
    async def get_client_state(self, client_id: str) -> Optional[ClientState]:
        """Get client sync state."""
        return self.client_states.get(client_id)
    
    async def get_sync_stats(self) -> dict[str, Any]:
        """Get sync statistics."""
        total_changes = len(self.changes)
        synced_changes = len([c for c in self.changes.values() if c.synced])
        unresolved_conflicts = len([c for c in self.conflicts.values() if not c.resolved_at])
        
        return {
            "total_changes": total_changes,
            "synced_changes": synced_changes,
            "pending_changes": total_changes - synced_changes,
            "total_conflicts": len(self.conflicts),
            "unresolved_conflicts": unresolved_conflicts,
            "active_clients": len(self.client_states),
            "total_syncs": len(self.sync_records),
        }


# Singleton instance
_data_sync_service: Optional[DataSyncService] = None


def get_data_sync_service() -> DataSyncService:
    """Get data sync service singleton."""
    global _data_sync_service
    if _data_sync_service is None:
        _data_sync_service = DataSyncService()
    return _data_sync_service
