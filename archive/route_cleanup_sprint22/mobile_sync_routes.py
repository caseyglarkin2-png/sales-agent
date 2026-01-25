"""
Mobile Sync Routes - Mobile app data synchronization
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random
import hashlib

logger = structlog.get_logger()

router = APIRouter(prefix="/mobile-sync", tags=["Mobile Sync"])


class SyncStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CONFLICT = "conflict"


class SyncDirection(str, Enum):
    PUSH = "push"
    PULL = "pull"
    BIDIRECTIONAL = "bidirectional"


class ConflictResolution(str, Enum):
    CLIENT_WINS = "client_wins"
    SERVER_WINS = "server_wins"
    MANUAL = "manual"
    LATEST_WINS = "latest_wins"
    MERGE = "merge"


class EntityType(str, Enum):
    CONTACT = "contact"
    ACCOUNT = "account"
    OPPORTUNITY = "opportunity"
    ACTIVITY = "activity"
    TASK = "task"
    NOTE = "note"
    EVENT = "event"


class DevicePlatform(str, Enum):
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


# In-memory storage
sync_sessions = {}
sync_records = {}
devices = {}
offline_queues = {}
conflicts = {}
sync_settings = {}
delta_tokens = {}


class DeviceRegistration(BaseModel):
    device_id: str
    platform: DevicePlatform
    app_version: str
    os_version: Optional[str] = None
    push_token: Optional[str] = None


class SyncRequest(BaseModel):
    entity_types: List[EntityType]
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    delta_token: Optional[str] = None
    changes: Optional[List[Dict[str, Any]]] = None
    conflict_resolution: ConflictResolution = ConflictResolution.LATEST_WINS


class OfflineChange(BaseModel):
    entity_type: EntityType
    entity_id: str
    operation: str  # create, update, delete
    data: Dict[str, Any]
    local_timestamp: str


# Device Registration
@router.post("/devices/register")
async def register_device(
    request: DeviceRegistration,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Register a mobile device for sync"""
    now = datetime.utcnow()
    
    device = {
        "device_id": request.device_id,
        "platform": request.platform.value,
        "app_version": request.app_version,
        "os_version": request.os_version,
        "push_token": request.push_token,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "registered_at": now.isoformat(),
        "last_sync_at": None,
        "sync_count": 0,
        "is_active": True
    }
    
    devices[request.device_id] = device
    
    # Initialize sync settings for device
    sync_settings[request.device_id] = {
        "sync_interval_minutes": 15,
        "sync_on_wifi_only": False,
        "auto_sync_enabled": True,
        "entities_to_sync": [e.value for e in EntityType]
    }
    
    logger.info("device_registered", device_id=request.device_id, platform=request.platform.value)
    return device


@router.get("/devices")
async def list_devices(
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """List registered devices"""
    user_devices = [
        d for d in devices.values() 
        if d.get("user_id") == user_id and d.get("tenant_id") == tenant_id
    ]
    
    return {"devices": user_devices, "total": len(user_devices)}


@router.delete("/devices/{device_id}")
async def unregister_device(device_id: str):
    """Unregister a device"""
    if device_id not in devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    devices.pop(device_id)
    sync_settings.pop(device_id, None)
    
    return {"message": "Device unregistered", "device_id": device_id}


@router.put("/devices/{device_id}/settings")
async def update_device_settings(
    device_id: str,
    sync_interval_minutes: Optional[int] = None,
    sync_on_wifi_only: Optional[bool] = None,
    auto_sync_enabled: Optional[bool] = None,
    entities_to_sync: Optional[List[EntityType]] = None
):
    """Update device sync settings"""
    if device_id not in devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    settings = sync_settings.get(device_id, {})
    
    if sync_interval_minutes is not None:
        settings["sync_interval_minutes"] = sync_interval_minutes
    if sync_on_wifi_only is not None:
        settings["sync_on_wifi_only"] = sync_on_wifi_only
    if auto_sync_enabled is not None:
        settings["auto_sync_enabled"] = auto_sync_enabled
    if entities_to_sync is not None:
        settings["entities_to_sync"] = [e.value for e in entities_to_sync]
    
    sync_settings[device_id] = settings
    
    return settings


# Sync Operations
@router.post("/sync")
async def sync_data(
    request: SyncRequest,
    device_id: str = Query(...),
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Perform data synchronization"""
    if device_id not in devices:
        raise HTTPException(status_code=404, detail="Device not registered")
    
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    sync_session = {
        "id": session_id,
        "device_id": device_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "entity_types": [e.value for e in request.entity_types],
        "direction": request.direction.value,
        "status": SyncStatus.IN_PROGRESS.value,
        "started_at": now.isoformat(),
        "records_pushed": 0,
        "records_pulled": 0,
        "conflicts_detected": 0,
        "conflicts_resolved": 0
    }
    
    sync_sessions[session_id] = sync_session
    
    # Process client changes (push)
    if request.changes and request.direction in [SyncDirection.PUSH, SyncDirection.BIDIRECTIONAL]:
        push_result = await process_push_changes(session_id, request.changes, request.conflict_resolution)
        sync_session["records_pushed"] = push_result["processed"]
        sync_session["conflicts_detected"] = push_result["conflicts"]
    
    # Get server changes (pull)
    pull_result = []
    new_delta_token = None
    if request.direction in [SyncDirection.PULL, SyncDirection.BIDIRECTIONAL]:
        pull_result, new_delta_token = await get_server_changes(
            request.entity_types, 
            request.delta_token,
            user_id,
            tenant_id
        )
        sync_session["records_pulled"] = len(pull_result)
    
    sync_session["status"] = SyncStatus.COMPLETED.value
    sync_session["completed_at"] = datetime.utcnow().isoformat()
    
    # Update device last sync
    devices[device_id]["last_sync_at"] = now.isoformat()
    devices[device_id]["sync_count"] += 1
    
    logger.info("sync_completed", session_id=session_id, pushed=sync_session["records_pushed"], pulled=sync_session["records_pulled"])
    
    return {
        "session_id": session_id,
        "status": sync_session["status"],
        "records_pushed": sync_session["records_pushed"],
        "records_pulled": sync_session["records_pulled"],
        "changes": pull_result,
        "delta_token": new_delta_token,
        "conflicts": sync_session["conflicts_detected"],
        "completed_at": sync_session["completed_at"]
    }


@router.get("/sync/{session_id}")
async def get_sync_session(session_id: str):
    """Get sync session details"""
    if session_id not in sync_sessions:
        raise HTTPException(status_code=404, detail="Sync session not found")
    
    return sync_sessions[session_id]


@router.get("/sync/history")
async def get_sync_history(
    device_id: str = Query(...),
    limit: int = Query(default=20, le=50)
):
    """Get sync history for a device"""
    history = [s for s in sync_sessions.values() if s.get("device_id") == device_id]
    history.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    
    return {"sessions": history[:limit], "total": len(history)}


# Delta Sync
@router.get("/delta/{entity_type}")
async def get_delta_changes(
    entity_type: EntityType,
    delta_token: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Get incremental changes since last sync"""
    changes = []
    
    # Simulate changes since delta token
    for i in range(random.randint(5, min(50, limit))):
        change = {
            "id": str(uuid.uuid4()),
            "entity_type": entity_type.value,
            "entity_id": str(uuid.uuid4()),
            "operation": random.choice(["create", "update", "delete"]),
            "data": {"field": "value", "updated": True},
            "server_timestamp": datetime.utcnow().isoformat(),
            "version": random.randint(1, 10)
        }
        changes.append(change)
    
    new_token = hashlib.sha256(datetime.utcnow().isoformat().encode()).hexdigest()[:32]
    
    return {
        "entity_type": entity_type.value,
        "changes": changes,
        "delta_token": new_token,
        "has_more": len(changes) >= limit
    }


# Offline Queue
@router.post("/offline/queue")
async def add_to_offline_queue(
    request: OfflineChange,
    device_id: str = Query(...)
):
    """Add a change to offline queue"""
    queue_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    queued_change = {
        "id": queue_id,
        "device_id": device_id,
        "entity_type": request.entity_type.value,
        "entity_id": request.entity_id,
        "operation": request.operation,
        "data": request.data,
        "local_timestamp": request.local_timestamp,
        "queued_at": now.isoformat(),
        "status": "pending",
        "retry_count": 0
    }
    
    offline_queues[queue_id] = queued_change
    
    return queued_change


@router.get("/offline/queue")
async def get_offline_queue(device_id: str = Query(...)):
    """Get pending offline changes"""
    queue = [q for q in offline_queues.values() if q.get("device_id") == device_id and q.get("status") == "pending"]
    queue.sort(key=lambda x: x.get("local_timestamp", ""))
    
    return {"queue": queue, "total": len(queue)}


@router.post("/offline/flush")
async def flush_offline_queue(
    device_id: str = Query(...),
    conflict_resolution: ConflictResolution = ConflictResolution.LATEST_WINS
):
    """Flush offline queue and sync changes"""
    queue = [q for q in offline_queues.values() if q.get("device_id") == device_id and q.get("status") == "pending"]
    
    processed = 0
    failed = 0
    conflicts_found = 0
    
    for item in queue:
        # Simulate processing
        if random.random() > 0.1:  # 90% success rate
            item["status"] = "synced"
            item["synced_at"] = datetime.utcnow().isoformat()
            processed += 1
        elif random.random() > 0.5:
            item["status"] = "conflict"
            conflicts_found += 1
        else:
            item["status"] = "failed"
            item["retry_count"] += 1
            failed += 1
    
    return {
        "processed": processed,
        "failed": failed,
        "conflicts": conflicts_found,
        "remaining": len([q for q in offline_queues.values() if q.get("device_id") == device_id and q.get("status") == "pending"])
    }


# Conflict Management
@router.get("/conflicts")
async def list_conflicts(
    device_id: Optional[str] = None,
    entity_type: Optional[EntityType] = None,
    status: str = Query(default="pending"),
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """List sync conflicts"""
    result = [c for c in conflicts.values() if c.get("tenant_id") == tenant_id]
    
    if device_id:
        result = [c for c in result if c.get("device_id") == device_id]
    if entity_type:
        result = [c for c in result if c.get("entity_type") == entity_type.value]
    if status:
        result = [c for c in result if c.get("status") == status]
    
    return {"conflicts": result, "total": len(result)}


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    resolution: ConflictResolution,
    merged_data: Optional[Dict[str, Any]] = None
):
    """Resolve a sync conflict"""
    if conflict_id not in conflicts:
        raise HTTPException(status_code=404, detail="Conflict not found")
    
    conflict = conflicts[conflict_id]
    now = datetime.utcnow()
    
    if resolution == ConflictResolution.MERGE and not merged_data:
        raise HTTPException(status_code=400, detail="Merged data required for merge resolution")
    
    conflict["status"] = "resolved"
    conflict["resolution"] = resolution.value
    conflict["resolved_at"] = now.isoformat()
    
    if merged_data:
        conflict["resolved_data"] = merged_data
    elif resolution == ConflictResolution.CLIENT_WINS:
        conflict["resolved_data"] = conflict.get("client_data")
    else:
        conflict["resolved_data"] = conflict.get("server_data")
    
    return conflict


# Push Notifications
@router.post("/push/send")
async def send_push_notification(
    device_id: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None
):
    """Send push notification to device"""
    if device_id not in devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device = devices[device_id]
    
    if not device.get("push_token"):
        raise HTTPException(status_code=400, detail="No push token registered")
    
    notification = {
        "id": str(uuid.uuid4()),
        "device_id": device_id,
        "title": title,
        "body": body,
        "data": data or {},
        "sent_at": datetime.utcnow().isoformat(),
        "status": "sent"
    }
    
    return notification


@router.post("/push/sync-trigger")
async def trigger_sync_push(
    device_id: str,
    entity_types: Optional[List[EntityType]] = None
):
    """Send push notification to trigger sync"""
    if device_id not in devices:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return {
        "device_id": device_id,
        "notification_type": "sync_trigger",
        "entity_types": [e.value for e in entity_types] if entity_types else ["all"],
        "sent_at": datetime.utcnow().isoformat()
    }


# Analytics
@router.get("/analytics")
async def get_sync_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get mobile sync analytics"""
    tenant_devices = [d for d in devices.values() if d.get("tenant_id") == tenant_id]
    tenant_sessions = [s for s in sync_sessions.values() if s.get("tenant_id") == tenant_id]
    
    by_platform = {}
    for platform in DevicePlatform:
        by_platform[platform.value] = len([
            d for d in tenant_devices if d.get("platform") == platform.value
        ])
    
    return {
        "total_devices": len(tenant_devices),
        "active_devices": len([d for d in tenant_devices if d.get("is_active")]),
        "total_syncs": len(tenant_sessions),
        "by_platform": by_platform,
        "avg_sync_time_seconds": round(random.uniform(2, 10), 2),
        "sync_success_rate": round(random.uniform(0.95, 0.99), 3),
        "total_records_synced": sum(s.get("records_pushed", 0) + s.get("records_pulled", 0) for s in tenant_sessions),
        "conflicts_rate": round(random.uniform(0.01, 0.05), 3),
        "period": {"start_date": start_date, "end_date": end_date}
    }


@router.get("/analytics/devices")
async def get_device_analytics(tenant_id: str = Query(default="default")):
    """Get device-level analytics"""
    tenant_devices = [d for d in devices.values() if d.get("tenant_id") == tenant_id]
    
    device_stats = []
    for device in tenant_devices:
        device_sessions = [s for s in sync_sessions.values() if s.get("device_id") == device["device_id"]]
        
        device_stats.append({
            "device_id": device["device_id"],
            "platform": device["platform"],
            "app_version": device["app_version"],
            "sync_count": len(device_sessions),
            "last_sync_at": device.get("last_sync_at"),
            "total_records_synced": sum(s.get("records_pushed", 0) + s.get("records_pulled", 0) for s in device_sessions)
        })
    
    return {"devices": device_stats, "total": len(device_stats)}


# Helper functions
async def process_push_changes(session_id: str, changes: List[Dict], resolution: ConflictResolution) -> Dict:
    """Process changes pushed from client"""
    processed = 0
    conflicts_found = 0
    
    for change in changes:
        # Check for conflicts
        if random.random() > 0.95:  # 5% conflict rate
            conflict_id = str(uuid.uuid4())
            conflicts[conflict_id] = {
                "id": conflict_id,
                "session_id": session_id,
                "entity_type": change.get("entity_type"),
                "entity_id": change.get("entity_id"),
                "client_data": change.get("data"),
                "server_data": {"field": "server_value"},
                "status": "pending",
                "detected_at": datetime.utcnow().isoformat()
            }
            conflicts_found += 1
        else:
            processed += 1
    
    return {"processed": processed, "conflicts": conflicts_found}


async def get_server_changes(entity_types: List[EntityType], delta_token: Optional[str], user_id: str, tenant_id: str):
    """Get changes from server since delta token"""
    changes = []
    
    for entity_type in entity_types:
        for i in range(random.randint(2, 10)):
            changes.append({
                "id": str(uuid.uuid4()),
                "entity_type": entity_type.value,
                "entity_id": str(uuid.uuid4()),
                "operation": random.choice(["create", "update"]),
                "data": {"name": f"Test {i}", "updated": True},
                "server_timestamp": datetime.utcnow().isoformat()
            })
    
    new_token = hashlib.sha256(datetime.utcnow().isoformat().encode()).hexdigest()[:32]
    
    return changes, new_token
