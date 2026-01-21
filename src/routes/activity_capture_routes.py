"""
Activity Capture Routes - Automatic activity tracking and logging
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid
import random

logger = structlog.get_logger()

router = APIRouter(prefix="/activity-capture", tags=["Activity Capture"])


class ActivityType(str, Enum):
    EMAIL_SENT = "email_sent"
    EMAIL_RECEIVED = "email_received"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_REPLIED = "email_replied"
    CALL_MADE = "call_made"
    CALL_RECEIVED = "call_received"
    MEETING_SCHEDULED = "meeting_scheduled"
    MEETING_COMPLETED = "meeting_completed"
    MEETING_CANCELLED = "meeting_cancelled"
    SMS_SENT = "sms_sent"
    SMS_RECEIVED = "sms_received"
    LINKEDIN_CONNECTION = "linkedin_connection"
    LINKEDIN_MESSAGE = "linkedin_message"
    LINKEDIN_VIEW = "linkedin_view"
    NOTE_CREATED = "note_created"
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    DOCUMENT_VIEWED = "document_viewed"
    DOCUMENT_SIGNED = "document_signed"


class CaptureSource(str, Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    CALENDAR = "calendar"
    PHONE = "phone"
    LINKEDIN = "linkedin"
    ZOOM = "zoom"
    TEAMS = "teams"
    SLACK = "slack"
    MANUAL = "manual"
    API = "api"


class MatchStatus(str, Enum):
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    PENDING = "pending"
    IGNORED = "ignored"
    CONFLICT = "conflict"


class SyncStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    SYNCING = "syncing"
    ERROR = "error"
    PENDING = "pending"


# In-memory storage
captured_activities = {}
activity_matches = {}
capture_sources = {}
sync_logs = {}
capture_rules = {}
user_mappings = {}
activity_analytics = {}
ignored_patterns = {}


class ActivityCapture(BaseModel):
    activity_type: ActivityType
    source: CaptureSource
    subject: Optional[str] = None
    body: Optional[str] = None
    participants: Optional[List[str]] = None
    timestamp: str
    duration_seconds: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class CaptureSourceConfig(BaseModel):
    source: CaptureSource
    credentials: Optional[Dict[str, str]] = None
    sync_frequency_minutes: int = 15
    enabled: bool = True
    settings: Optional[Dict[str, Any]] = None


# Activity Capture
@router.post("/activities")
async def capture_activity(
    request: ActivityCapture,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Capture an activity"""
    activity_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    activity = {
        "id": activity_id,
        "activity_type": request.activity_type.value,
        "source": request.source.value,
        "subject": request.subject,
        "body": request.body,
        "participants": request.participants or [],
        "timestamp": request.timestamp,
        "duration_seconds": request.duration_seconds,
        "metadata": request.metadata or {},
        "match_status": MatchStatus.PENDING.value,
        "matched_records": [],
        "user_id": user_id,
        "tenant_id": tenant_id,
        "captured_at": now.isoformat()
    }
    
    captured_activities[activity_id] = activity
    
    # Auto-match to records
    matched = await auto_match_activity(activity_id, tenant_id)
    
    logger.info("activity_captured", activity_id=activity_id, type=request.activity_type.value)
    return activity


@router.get("/activities")
async def list_captured_activities(
    activity_type: Optional[ActivityType] = None,
    source: Optional[CaptureSource] = None,
    match_status: Optional[MatchStatus] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List captured activities"""
    result = [a for a in captured_activities.values() if a.get("tenant_id") == tenant_id]
    
    if activity_type:
        result = [a for a in result if a.get("activity_type") == activity_type.value]
    if source:
        result = [a for a in result if a.get("source") == source.value]
    if match_status:
        result = [a for a in result if a.get("match_status") == match_status.value]
    if start_date:
        result = [a for a in result if a.get("timestamp", "") >= start_date]
    if end_date:
        result = [a for a in result if a.get("timestamp", "") <= end_date]
    
    result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "activities": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/activities/{activity_id}")
async def get_activity(activity_id: str):
    """Get activity details"""
    if activity_id not in captured_activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    return captured_activities[activity_id]


@router.post("/activities/{activity_id}/match")
async def match_activity_to_record(
    activity_id: str,
    record_type: str,
    record_id: str
):
    """Manually match activity to a record"""
    if activity_id not in captured_activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    activity = captured_activities[activity_id]
    now = datetime.utcnow()
    
    match = {
        "record_type": record_type,
        "record_id": record_id,
        "matched_at": now.isoformat(),
        "match_method": "manual"
    }
    
    activity["matched_records"].append(match)
    activity["match_status"] = MatchStatus.MATCHED.value
    
    return activity


@router.post("/activities/{activity_id}/ignore")
async def ignore_activity(activity_id: str, reason: Optional[str] = None):
    """Mark activity as ignored"""
    if activity_id not in captured_activities:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    activity = captured_activities[activity_id]
    activity["match_status"] = MatchStatus.IGNORED.value
    activity["ignore_reason"] = reason
    activity["ignored_at"] = datetime.utcnow().isoformat()
    
    return activity


@router.get("/activities/unmatched")
async def get_unmatched_activities(
    limit: int = Query(default=50, le=100),
    tenant_id: str = Query(default="default")
):
    """Get activities pending matching"""
    unmatched = [
        a for a in captured_activities.values() 
        if a.get("tenant_id") == tenant_id and a.get("match_status") in ["pending", "unmatched"]
    ]
    
    unmatched.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "activities": unmatched[:limit],
        "total": len(unmatched)
    }


# Capture Sources
@router.post("/sources")
async def configure_capture_source(
    request: CaptureSourceConfig,
    user_id: str = Query(default="default"),
    tenant_id: str = Query(default="default")
):
    """Configure a capture source"""
    source_id = f"{tenant_id}_{user_id}_{request.source.value}"
    now = datetime.utcnow()
    
    source = {
        "id": source_id,
        "source": request.source.value,
        "sync_frequency_minutes": request.sync_frequency_minutes,
        "enabled": request.enabled,
        "settings": request.settings or {},
        "status": SyncStatus.PENDING.value,
        "last_sync_at": None,
        "activities_captured": 0,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "configured_at": now.isoformat()
    }
    
    capture_sources[source_id] = source
    
    return source


@router.get("/sources")
async def list_capture_sources(
    user_id: Optional[str] = None,
    status: Optional[SyncStatus] = None,
    tenant_id: str = Query(default="default")
):
    """List configured capture sources"""
    result = [s for s in capture_sources.values() if s.get("tenant_id") == tenant_id]
    
    if user_id:
        result = [s for s in result if s.get("user_id") == user_id]
    if status:
        result = [s for s in result if s.get("status") == status.value]
    
    return {"sources": result, "total": len(result)}


@router.post("/sources/{source_id}/connect")
async def connect_source(source_id: str, auth_code: Optional[str] = None):
    """Connect/authenticate a capture source"""
    if source_id not in capture_sources:
        raise HTTPException(status_code=404, detail="Source not found")
    
    source = capture_sources[source_id]
    now = datetime.utcnow()
    
    # Simulate OAuth connection
    source["status"] = SyncStatus.CONNECTED.value
    source["connected_at"] = now.isoformat()
    
    return source


@router.post("/sources/{source_id}/disconnect")
async def disconnect_source(source_id: str):
    """Disconnect a capture source"""
    if source_id not in capture_sources:
        raise HTTPException(status_code=404, detail="Source not found")
    
    source = capture_sources[source_id]
    source["status"] = SyncStatus.DISCONNECTED.value
    source["disconnected_at"] = datetime.utcnow().isoformat()
    
    return source


@router.post("/sources/{source_id}/sync")
async def trigger_sync(source_id: str):
    """Trigger manual sync for a source"""
    if source_id not in capture_sources:
        raise HTTPException(status_code=404, detail="Source not found")
    
    source = capture_sources[source_id]
    now = datetime.utcnow()
    
    if source["status"] != SyncStatus.CONNECTED.value:
        raise HTTPException(status_code=400, detail="Source not connected")
    
    source["status"] = SyncStatus.SYNCING.value
    
    # Simulate sync
    activities_synced = random.randint(5, 50)
    
    sync_log = {
        "id": str(uuid.uuid4()),
        "source_id": source_id,
        "started_at": now.isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "activities_synced": activities_synced,
        "status": "completed"
    }
    
    sync_logs[sync_log["id"]] = sync_log
    
    source["status"] = SyncStatus.CONNECTED.value
    source["last_sync_at"] = now.isoformat()
    source["activities_captured"] = source.get("activities_captured", 0) + activities_synced
    
    return {
        "source_id": source_id,
        "sync_result": sync_log
    }


@router.get("/sources/{source_id}/logs")
async def get_sync_logs(
    source_id: str,
    limit: int = Query(default=20, le=50)
):
    """Get sync logs for a source"""
    logs = [l for l in sync_logs.values() if l.get("source_id") == source_id]
    logs.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    
    return {"logs": logs[:limit], "total": len(logs)}


# Capture Rules
@router.post("/rules")
async def create_capture_rule(
    name: str,
    source: CaptureSource,
    conditions: List[Dict[str, Any]],
    actions: List[Dict[str, Any]],
    enabled: bool = True,
    tenant_id: str = Query(default="default")
):
    """Create a capture rule"""
    rule_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    rule = {
        "id": rule_id,
        "name": name,
        "source": source.value,
        "conditions": conditions,
        "actions": actions,
        "enabled": enabled,
        "matches": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    capture_rules[rule_id] = rule
    
    return rule


@router.get("/rules")
async def list_capture_rules(
    source: Optional[CaptureSource] = None,
    enabled: Optional[bool] = None,
    tenant_id: str = Query(default="default")
):
    """List capture rules"""
    result = [r for r in capture_rules.values() if r.get("tenant_id") == tenant_id]
    
    if source:
        result = [r for r in result if r.get("source") == source.value]
    if enabled is not None:
        result = [r for r in result if r.get("enabled") == enabled]
    
    return {"rules": result, "total": len(result)}


@router.put("/rules/{rule_id}")
async def update_capture_rule(
    rule_id: str,
    name: Optional[str] = None,
    conditions: Optional[List[Dict[str, Any]]] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    enabled: Optional[bool] = None
):
    """Update a capture rule"""
    if rule_id not in capture_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = capture_rules[rule_id]
    
    if name is not None:
        rule["name"] = name
    if conditions is not None:
        rule["conditions"] = conditions
    if actions is not None:
        rule["actions"] = actions
    if enabled is not None:
        rule["enabled"] = enabled
    
    rule["updated_at"] = datetime.utcnow().isoformat()
    
    return rule


@router.delete("/rules/{rule_id}")
async def delete_capture_rule(rule_id: str):
    """Delete a capture rule"""
    if rule_id not in capture_rules:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    capture_rules.pop(rule_id)
    
    return {"message": "Rule deleted", "rule_id": rule_id}


# Ignore Patterns
@router.post("/ignore-patterns")
async def create_ignore_pattern(
    pattern_type: str,
    pattern: str,
    description: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Create an ignore pattern"""
    pattern_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    ignore_pattern = {
        "id": pattern_id,
        "pattern_type": pattern_type,
        "pattern": pattern,
        "description": description,
        "matches": 0,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    ignored_patterns[pattern_id] = ignore_pattern
    
    return ignore_pattern


@router.get("/ignore-patterns")
async def list_ignore_patterns(tenant_id: str = Query(default="default")):
    """List ignore patterns"""
    patterns = [p for p in ignored_patterns.values() if p.get("tenant_id") == tenant_id]
    return {"patterns": patterns, "total": len(patterns)}


@router.delete("/ignore-patterns/{pattern_id}")
async def delete_ignore_pattern(pattern_id: str):
    """Delete an ignore pattern"""
    if pattern_id not in ignored_patterns:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    ignored_patterns.pop(pattern_id)
    
    return {"message": "Pattern deleted", "pattern_id": pattern_id}


# User Mappings
@router.post("/user-mappings")
async def create_user_mapping(
    external_email: str,
    internal_user_id: str,
    source: CaptureSource,
    tenant_id: str = Query(default="default")
):
    """Map external email to internal user"""
    mapping_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    mapping = {
        "id": mapping_id,
        "external_email": external_email,
        "internal_user_id": internal_user_id,
        "source": source.value,
        "tenant_id": tenant_id,
        "created_at": now.isoformat()
    }
    
    user_mappings[mapping_id] = mapping
    
    return mapping


@router.get("/user-mappings")
async def list_user_mappings(
    source: Optional[CaptureSource] = None,
    tenant_id: str = Query(default="default")
):
    """List user mappings"""
    mappings = [m for m in user_mappings.values() if m.get("tenant_id") == tenant_id]
    
    if source:
        mappings = [m for m in mappings if m.get("source") == source.value]
    
    return {"mappings": mappings, "total": len(mappings)}


# Analytics
@router.get("/analytics/overview")
async def get_capture_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    tenant_id: str = Query(default="default")
):
    """Get activity capture analytics"""
    tenant_activities = [a for a in captured_activities.values() if a.get("tenant_id") == tenant_id]
    
    by_type = {}
    for activity_type in ActivityType:
        by_type[activity_type.value] = len([
            a for a in tenant_activities if a.get("activity_type") == activity_type.value
        ])
    
    by_source = {}
    for source in CaptureSource:
        by_source[source.value] = len([
            a for a in tenant_activities if a.get("source") == source.value
        ])
    
    return {
        "total_captured": len(tenant_activities),
        "matched": len([a for a in tenant_activities if a.get("match_status") == "matched"]),
        "unmatched": len([a for a in tenant_activities if a.get("match_status") in ["pending", "unmatched"]]),
        "ignored": len([a for a in tenant_activities if a.get("match_status") == "ignored"]),
        "match_rate": round(random.uniform(0.7, 0.95), 3),
        "by_type": by_type,
        "by_source": by_source,
        "period": {"start_date": start_date, "end_date": end_date}
    }


@router.get("/analytics/sources")
async def get_source_analytics(tenant_id: str = Query(default="default")):
    """Get analytics by capture source"""
    tenant_sources = [s for s in capture_sources.values() if s.get("tenant_id") == tenant_id]
    
    source_stats = []
    for source in tenant_sources:
        source_stats.append({
            "source": source["source"],
            "status": source["status"],
            "activities_captured": source.get("activities_captured", 0),
            "last_sync_at": source.get("last_sync_at"),
            "sync_frequency_minutes": source.get("sync_frequency_minutes")
        })
    
    return {"sources": source_stats, "total": len(source_stats)}


@router.get("/analytics/activity-timeline")
async def get_activity_timeline(
    days: int = Query(default=30, ge=7, le=90),
    tenant_id: str = Query(default="default")
):
    """Get activity capture timeline"""
    timeline = []
    
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=i)).isoformat()[:10]
        timeline.append({
            "date": date,
            "emails": random.randint(20, 100),
            "calls": random.randint(5, 30),
            "meetings": random.randint(2, 15),
            "total": random.randint(30, 150)
        })
    
    return {"timeline": timeline[::-1], "days": days}


# Helper function
async def auto_match_activity(activity_id: str, tenant_id: str) -> bool:
    """Automatically match activity to records based on participants"""
    activity = captured_activities[activity_id]
    
    # Simulate matching based on participants
    if activity.get("participants"):
        # In real implementation, search contacts/accounts by email
        if random.random() > 0.3:  # 70% match rate
            activity["match_status"] = MatchStatus.MATCHED.value
            activity["matched_records"].append({
                "record_type": random.choice(["contact", "account", "opportunity"]),
                "record_id": str(uuid.uuid4()),
                "matched_at": datetime.utcnow().isoformat(),
                "match_method": "auto",
                "confidence": round(random.uniform(0.8, 1.0), 2)
            })
            return True
        else:
            activity["match_status"] = MatchStatus.UNMATCHED.value
    
    return False
