"""
Meeting Intelligence Routes - Call recording, transcription, and conversation insights
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from enum import Enum
import structlog
import uuid

logger = structlog.get_logger()

router = APIRouter(prefix="/meeting-intelligence", tags=["Meeting Intelligence"])


class RecordingStatus(str, Enum):
    PENDING = "pending"
    RECORDING = "recording"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class MeetingPlatform(str, Enum):
    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"
    TEAMS = "teams"
    WEBEX = "webex"
    PHONE = "phone"
    IN_PERSON = "in_person"


class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class RecordingCreate(BaseModel):
    meeting_id: Optional[str] = None
    title: str
    platform: MeetingPlatform
    external_meeting_id: Optional[str] = None
    participants: Optional[List[Dict[str, str]]] = None
    scheduled_start: Optional[str] = None


class TranscriptionRequest(BaseModel):
    language: str = "en"
    speaker_diarization: bool = True
    custom_vocabulary: Optional[List[str]] = None


class InsightQuery(BaseModel):
    query: str
    context_window: int = Field(default=5, description="Number of surrounding sentences for context")


class ActionItemCreate(BaseModel):
    description: str
    assignee_id: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "medium"


# In-memory storage
recordings = {}
transcriptions = {}
insights = {}
action_items = {}
meeting_summaries = {}
coaching_notes = {}


# Recordings
@router.post("/recordings")
async def create_recording(
    request: RecordingCreate,
    tenant_id: str = Query(default="default")
):
    """Initialize a new meeting recording"""
    recording_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    recording = {
        "id": recording_id,
        "meeting_id": request.meeting_id,
        "title": request.title,
        "platform": request.platform.value,
        "external_meeting_id": request.external_meeting_id,
        "participants": request.participants or [],
        "scheduled_start": request.scheduled_start,
        "status": RecordingStatus.PENDING.value,
        "duration_seconds": 0,
        "file_size_bytes": 0,
        "storage_url": None,
        "tenant_id": tenant_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    recordings[recording_id] = recording
    logger.info("recording_created", recording_id=recording_id)
    return recording


@router.get("/recordings")
async def list_recordings(
    platform: Optional[MeetingPlatform] = None,
    status: Optional[RecordingStatus] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    tenant_id: str = Query(default="default")
):
    """List meeting recordings"""
    result = [r for r in recordings.values() if r.get("tenant_id") == tenant_id]
    
    if platform:
        result = [r for r in result if r.get("platform") == platform.value]
    if status:
        result = [r for r in result if r.get("status") == status.value]
    
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "recordings": result[offset:offset + limit],
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/recordings/{recording_id}")
async def get_recording(recording_id: str):
    """Get recording details"""
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recordings[recording_id]


@router.post("/recordings/{recording_id}/start")
async def start_recording(recording_id: str):
    """Start recording a meeting"""
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    recording = recordings[recording_id]
    recording["status"] = RecordingStatus.RECORDING.value
    recording["actual_start"] = datetime.utcnow().isoformat()
    recording["updated_at"] = datetime.utcnow().isoformat()
    
    logger.info("recording_started", recording_id=recording_id)
    return recording


@router.post("/recordings/{recording_id}/stop")
async def stop_recording(recording_id: str):
    """Stop recording and begin processing"""
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    recording = recordings[recording_id]
    now = datetime.utcnow()
    
    recording["status"] = RecordingStatus.PROCESSING.value
    recording["actual_end"] = now.isoformat()
    
    # Calculate duration
    if recording.get("actual_start"):
        start = datetime.fromisoformat(recording["actual_start"])
        recording["duration_seconds"] = int((now - start).total_seconds())
    
    recording["updated_at"] = now.isoformat()
    
    # Simulate processing completion
    recording["status"] = RecordingStatus.COMPLETED.value
    recording["storage_url"] = f"https://storage.example.com/recordings/{recording_id}.mp4"
    recording["file_size_bytes"] = recording.get("duration_seconds", 0) * 50000  # ~50KB/sec
    
    logger.info("recording_stopped", recording_id=recording_id, duration=recording["duration_seconds"])
    return recording


@router.post("/recordings/{recording_id}/upload")
async def upload_recording(
    recording_id: str,
    file: UploadFile = File(...)
):
    """Upload a recording file"""
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    recording = recordings[recording_id]
    
    # In production, this would upload to cloud storage
    recording["storage_url"] = f"https://storage.example.com/recordings/{recording_id}/{file.filename}"
    recording["file_name"] = file.filename
    recording["content_type"] = file.content_type
    recording["status"] = RecordingStatus.COMPLETED.value
    recording["updated_at"] = datetime.utcnow().isoformat()
    
    logger.info("recording_uploaded", recording_id=recording_id, filename=file.filename)
    return recording


@router.delete("/recordings/{recording_id}")
async def delete_recording(recording_id: str):
    """Delete a recording"""
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    del recordings[recording_id]
    # Also delete associated transcription
    if recording_id in transcriptions:
        del transcriptions[recording_id]
    
    logger.info("recording_deleted", recording_id=recording_id)
    return {"status": "deleted", "recording_id": recording_id}


# Transcriptions
@router.post("/recordings/{recording_id}/transcribe")
async def request_transcription(
    recording_id: str,
    request: TranscriptionRequest
):
    """Request transcription for a recording"""
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    transcription_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Generate mock transcription
    mock_segments = [
        {"speaker": "Speaker 1", "start": 0.0, "end": 5.2, "text": "Hello everyone, thanks for joining today's call.", "sentiment": "positive"},
        {"speaker": "Speaker 2", "start": 5.5, "end": 12.3, "text": "Thanks for having me. I'm excited to discuss our partnership.", "sentiment": "positive"},
        {"speaker": "Speaker 1", "start": 12.8, "end": 25.1, "text": "Let's start by reviewing the proposal we sent over last week. Did you have any questions?", "sentiment": "neutral"},
        {"speaker": "Speaker 2", "start": 25.5, "end": 42.0, "text": "Yes, we had some concerns about the pricing structure, specifically around the enterprise tier.", "sentiment": "negative"},
        {"speaker": "Speaker 1", "start": 42.5, "end": 60.0, "text": "I understand. Let me walk you through our flexible options. We have several ways to structure this that might work better for your budget.", "sentiment": "positive"},
    ]
    
    transcription = {
        "id": transcription_id,
        "recording_id": recording_id,
        "language": request.language,
        "speaker_diarization": request.speaker_diarization,
        "custom_vocabulary": request.custom_vocabulary or [],
        "status": TranscriptionStatus.COMPLETED.value,
        "segments": mock_segments,
        "full_text": " ".join(s["text"] for s in mock_segments),
        "word_count": sum(len(s["text"].split()) for s in mock_segments),
        "speakers": list(set(s["speaker"] for s in mock_segments)),
        "confidence_score": 0.95,
        "created_at": now.isoformat(),
        "completed_at": now.isoformat()
    }
    
    transcriptions[recording_id] = transcription
    
    logger.info("transcription_completed", recording_id=recording_id, transcription_id=transcription_id)
    return transcription


@router.get("/recordings/{recording_id}/transcription")
async def get_transcription(recording_id: str):
    """Get transcription for a recording"""
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    if recording_id not in transcriptions:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    return transcriptions[recording_id]


@router.get("/recordings/{recording_id}/transcription/search")
async def search_transcription(
    recording_id: str,
    query: str,
    context_sentences: int = Query(default=2, ge=0, le=5)
):
    """Search within a transcription"""
    if recording_id not in transcriptions:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    transcription = transcriptions[recording_id]
    query_lower = query.lower()
    
    matches = []
    for segment in transcription.get("segments", []):
        if query_lower in segment.get("text", "").lower():
            matches.append({
                "segment": segment,
                "timestamp": segment.get("start"),
                "speaker": segment.get("speaker")
            })
    
    return {
        "query": query,
        "matches": matches,
        "total_matches": len(matches)
    }


# Insights
@router.post("/recordings/{recording_id}/analyze")
async def analyze_recording(recording_id: str):
    """Generate AI insights from a recording"""
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    if recording_id not in transcriptions:
        raise HTTPException(status_code=400, detail="Transcription required before analysis")
    
    insight_id = str(uuid.uuid4())
    now = datetime.utcnow()
    transcription = transcriptions[recording_id]
    
    # Generate mock insights
    insight = {
        "id": insight_id,
        "recording_id": recording_id,
        "sentiment_analysis": {
            "overall": "positive",
            "score": 0.72,
            "by_speaker": {
                "Speaker 1": {"sentiment": "positive", "score": 0.85},
                "Speaker 2": {"sentiment": "neutral", "score": 0.58}
            },
            "timeline": [
                {"timestamp": 0, "sentiment": "positive", "score": 0.8},
                {"timestamp": 30, "sentiment": "negative", "score": 0.4},
                {"timestamp": 60, "sentiment": "positive", "score": 0.9}
            ]
        },
        "talk_ratio": {
            "Speaker 1": 55.2,
            "Speaker 2": 44.8
        },
        "key_topics": [
            {"topic": "pricing", "mentions": 3, "sentiment": "mixed"},
            {"topic": "enterprise", "mentions": 2, "sentiment": "positive"},
            {"topic": "partnership", "mentions": 2, "sentiment": "positive"}
        ],
        "questions_asked": [
            {"speaker": "Speaker 1", "question": "Did you have any questions?", "timestamp": 20.5},
            {"speaker": "Speaker 2", "question": "Can we discuss volume discounts?", "timestamp": 85.2}
        ],
        "objections_detected": [
            {
                "text": "concerns about the pricing structure",
                "timestamp": 30.0,
                "handled": True,
                "response_quality": "good"
            }
        ],
        "engagement_score": 78,
        "next_steps_mentioned": [
            "Send revised proposal",
            "Schedule follow-up call",
            "Loop in technical team"
        ],
        "competitor_mentions": [
            {"competitor": "CompetitorX", "context": "compared our solution", "timestamp": 120.5}
        ],
        "created_at": now.isoformat()
    }
    
    insights[recording_id] = insight
    
    logger.info("analysis_completed", recording_id=recording_id, insight_id=insight_id)
    return insight


@router.get("/recordings/{recording_id}/insights")
async def get_insights(recording_id: str):
    """Get insights for a recording"""
    if recording_id not in insights:
        raise HTTPException(status_code=404, detail="Insights not found")
    return insights[recording_id]


# Summaries
@router.post("/recordings/{recording_id}/summarize")
async def generate_summary(recording_id: str):
    """Generate AI summary of a meeting"""
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    summary_id = str(uuid.uuid4())
    now = datetime.utcnow()
    recording = recordings[recording_id]
    
    summary = {
        "id": summary_id,
        "recording_id": recording_id,
        "title": recording.get("title", "Meeting Summary"),
        "executive_summary": "This was a productive meeting to discuss partnership opportunities and pricing options. The prospect expressed interest but had concerns about enterprise pricing that were addressed effectively.",
        "key_points": [
            "Reviewed partnership proposal sent last week",
            "Discussed pricing concerns for enterprise tier",
            "Agreed to send revised proposal with flexible options",
            "Technical deep-dive scheduled for next week"
        ],
        "decisions_made": [
            "Will proceed with standard pricing with volume discounts",
            "Legal review to begin next week"
        ],
        "action_items": [
            {"description": "Send revised proposal", "assignee": "Speaker 1", "due": "Friday"},
            {"description": "Schedule technical review", "assignee": "Speaker 2", "due": "Next Monday"},
            {"description": "Share case studies", "assignee": "Speaker 1", "due": "EOD"}
        ],
        "attendees": recording.get("participants", []),
        "duration_minutes": recording.get("duration_seconds", 0) // 60,
        "next_meeting": "Technical deep-dive scheduled for next Tuesday at 2pm",
        "created_at": now.isoformat()
    }
    
    meeting_summaries[recording_id] = summary
    
    logger.info("summary_generated", recording_id=recording_id, summary_id=summary_id)
    return summary


@router.get("/recordings/{recording_id}/summary")
async def get_summary(recording_id: str):
    """Get meeting summary"""
    if recording_id not in meeting_summaries:
        raise HTTPException(status_code=404, detail="Summary not found")
    return meeting_summaries[recording_id]


# Action Items
@router.post("/recordings/{recording_id}/action-items")
async def create_action_item(
    recording_id: str,
    request: ActionItemCreate
):
    """Create an action item from a meeting"""
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    item_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    item = {
        "id": item_id,
        "recording_id": recording_id,
        "description": request.description,
        "assignee_id": request.assignee_id,
        "due_date": request.due_date,
        "priority": request.priority,
        "status": "pending",
        "created_at": now.isoformat()
    }
    
    if recording_id not in action_items:
        action_items[recording_id] = []
    action_items[recording_id].append(item)
    
    return item


@router.get("/recordings/{recording_id}/action-items")
async def list_action_items(recording_id: str):
    """List action items from a meeting"""
    items = action_items.get(recording_id, [])
    return {"action_items": items, "total": len(items)}


@router.put("/recordings/{recording_id}/action-items/{item_id}")
async def update_action_item(
    recording_id: str,
    item_id: str,
    status: str
):
    """Update action item status"""
    items = action_items.get(recording_id, [])
    for item in items:
        if item.get("id") == item_id:
            item["status"] = status
            item["updated_at"] = datetime.utcnow().isoformat()
            return item
    
    raise HTTPException(status_code=404, detail="Action item not found")


# Coaching
@router.post("/recordings/{recording_id}/coaching")
async def generate_coaching(recording_id: str):
    """Generate sales coaching feedback for a call"""
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    coaching_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    coaching = {
        "id": coaching_id,
        "recording_id": recording_id,
        "overall_score": 82,
        "categories": {
            "discovery": {
                "score": 85,
                "feedback": "Strong discovery questions. Consider asking more about timeline."
            },
            "objection_handling": {
                "score": 78,
                "feedback": "Good response to pricing concerns. Could have probed deeper on budget constraints."
            },
            "active_listening": {
                "score": 88,
                "feedback": "Excellent paraphrasing and acknowledgment of prospect's points."
            },
            "next_steps": {
                "score": 75,
                "feedback": "Clear next steps defined. Consider getting more commitment on timing."
            },
            "talk_ratio": {
                "score": 80,
                "feedback": "Good balance. Try to let prospect talk slightly more (aim for 40/60)."
            }
        },
        "highlights": [
            {"timestamp": 45.0, "type": "positive", "text": "Great job acknowledging the pricing concern before addressing it."},
            {"timestamp": 120.5, "type": "positive", "text": "Excellent use of customer success story to build credibility."}
        ],
        "improvement_areas": [
            {"timestamp": 25.0, "type": "suggestion", "text": "When prospect mentioned concerns, ask clarifying questions before proposing solutions."},
            {"timestamp": 90.0, "type": "suggestion", "text": "Try the 'feel, felt, found' technique for handling objections."}
        ],
        "recommended_training": [
            {"title": "Advanced Objection Handling", "url": "/learning/objection-handling"},
            {"title": "Discovery Mastery", "url": "/learning/discovery"}
        ],
        "created_at": now.isoformat()
    }
    
    coaching_notes[recording_id] = coaching
    
    logger.info("coaching_generated", recording_id=recording_id, score=82)
    return coaching


@router.get("/recordings/{recording_id}/coaching")
async def get_coaching(recording_id: str):
    """Get coaching feedback for a recording"""
    if recording_id not in coaching_notes:
        raise HTTPException(status_code=404, detail="Coaching not found")
    return coaching_notes[recording_id]


# Stats
@router.get("/stats")
async def get_intelligence_stats(
    tenant_id: str = Query(default="default"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get meeting intelligence statistics"""
    tenant_recordings = [r for r in recordings.values() if r.get("tenant_id") == tenant_id]
    
    total_duration = sum(r.get("duration_seconds", 0) for r in tenant_recordings)
    avg_coaching_score = 0
    if coaching_notes:
        scores = [c.get("overall_score", 0) for c in coaching_notes.values()]
        avg_coaching_score = sum(scores) / len(scores) if scores else 0
    
    return {
        "total_recordings": len(tenant_recordings),
        "by_status": {
            status.value: len([r for r in tenant_recordings if r.get("status") == status.value])
            for status in RecordingStatus
        },
        "by_platform": {
            platform.value: len([r for r in tenant_recordings if r.get("platform") == platform.value])
            for platform in MeetingPlatform
        },
        "total_duration_hours": round(total_duration / 3600, 2),
        "total_transcriptions": len(transcriptions),
        "total_insights": len(insights),
        "total_summaries": len(meeting_summaries),
        "average_coaching_score": round(avg_coaching_score, 1),
        "action_items_created": sum(len(items) for items in action_items.values())
    }


# Clips
@router.post("/recordings/{recording_id}/clips")
async def create_clip(
    recording_id: str,
    start_time: float = Query(..., ge=0),
    end_time: float = Query(..., ge=0),
    title: Optional[str] = None
):
    """Create a clip from a recording"""
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    clip_id = str(uuid.uuid4())
    recording = recordings[recording_id]
    
    clip = {
        "id": clip_id,
        "recording_id": recording_id,
        "title": title or f"Clip from {recording.get('title', 'recording')}",
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": end_time - start_time,
        "clip_url": f"https://storage.example.com/clips/{clip_id}.mp4",
        "created_at": datetime.utcnow().isoformat()
    }
    
    logger.info("clip_created", clip_id=clip_id, recording_id=recording_id)
    return clip


@router.post("/recordings/{recording_id}/share")
async def share_recording(
    recording_id: str,
    recipients: List[str] = Query(...),
    include_transcription: bool = True,
    include_summary: bool = True
):
    """Share a recording with team members"""
    if recording_id not in recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    share_id = str(uuid.uuid4())
    
    return {
        "share_id": share_id,
        "recording_id": recording_id,
        "share_link": f"https://app.example.com/recordings/{recording_id}?share={share_id}",
        "recipients": recipients,
        "include_transcription": include_transcription,
        "include_summary": include_summary,
        "expires_at": None,
        "created_at": datetime.utcnow().isoformat()
    }
