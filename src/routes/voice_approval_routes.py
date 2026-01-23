"""API routes for voice-enabled approval interface."""
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from src.logger import get_logger
from src.config import get_settings
from src.voice_approval import (
    get_voice_approval,
    ApprovalItem,
    VoiceApprovalInterface
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/voice-approval", tags=["voice-approval"])


class VoiceInputRequest(BaseModel):
    """Request with text input (alternative to audio upload)."""
    text: str
    

class AddEmailDraftRequest(BaseModel):
    """Add email draft to approval queue."""
    draft_id: str
    to_email: str
    to_name: str
    subject: str
    body: str
    context: Dict[str, Any] = {}
    agent: str = "email_drafter"


class AddItemRequest(BaseModel):
    """Add generic item to approval queue."""
    id: str
    type: str
    title: str
    content: Dict[str, Any]
    context: Dict[str, Any] = {}
    agent_source: str = "unknown"
    priority: str = "normal"


@router.post("/voice-input", response_model=Dict[str, Any])
async def process_voice_input_text(request: VoiceInputRequest) -> Dict[str, Any]:
    """Process voice input as text (for testing or text-based UI).
    
    Example commands:
    - "Approve this email"
    - "Reject and move to next"
    - "Change the subject line to 'Quick question about logistics'"
    - "Show me the next one"
    - "Why was this draft created?"
    - "Approve everything for Bristol Myers Squibb"
    """
    try:
        jarvis = get_voice_approval()
        response = await jarvis.process_voice_input(text_input=request.text)
        return response
    except Exception as e:
        logger.error(f"Error processing voice input: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice-input/audio", response_model=Dict[str, Any])
async def process_voice_input_audio(audio: UploadFile = File(...)) -> Dict[str, Any]:
    """Process voice input from audio file.
    
    Upload an audio file (MP3, WAV, etc.) with your voice command.
    Jarvis will transcribe, parse, and execute your command.
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        jarvis = get_voice_approval()
        response = await jarvis.process_voice_input(audio_data=audio_data)
        return response
    except Exception as e:
        logger.error(f"Error processing voice audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-email-draft", response_model=Dict[str, Any])
async def add_email_draft(request: AddEmailDraftRequest) -> Dict[str, Any]:
    """Add an email draft to the approval queue."""
    try:
        jarvis = get_voice_approval()
        jarvis.add_email_draft(
            draft_id=request.draft_id,
            to_email=request.to_email,
            to_name=request.to_name,
            subject=request.subject,
            body=request.body,
            context=request.context,
            agent=request.agent
        )
        
        return {
            "status": "added",
            "draft_id": request.draft_id,
            "queue_length": len(jarvis.pending_items)
        }
    except Exception as e:
        logger.error(f"Error adding email draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-item", response_model=Dict[str, Any])
async def add_item(request: AddItemRequest) -> Dict[str, Any]:
    """Add any type of item to the approval queue."""
    try:
        jarvis = get_voice_approval()
        
        item = ApprovalItem(
            id=request.id,
            type=request.type,
            title=request.title,
            content=request.content,
            context=request.context,
            created_at="",  # Will be set by ApprovalItem
            agent_source=request.agent_source,
            priority=request.priority
        )
        
        jarvis.add_item(item)
        
        return {
            "status": "added",
            "item_id": request.id,
            "queue_length": len(jarvis.pending_items)
        }
    except Exception as e:
        logger.error(f"Error adding item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=Dict[str, Any])
async def get_status() -> Dict[str, Any]:
    """Get current approval queue status from real draft queue."""
    try:
        jarvis = get_voice_approval()
        return await jarvis.get_status_async()
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation-history", response_model=List[Dict[str, Any]])
async def get_conversation_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent conversation history with Jarvis."""
    try:
        jarvis = get_voice_approval()
        return jarvis.conversation_history[-limit:]
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tts-config", response_model=Dict[str, Any])
async def get_tts_config() -> Dict[str, Any]:
    """Get Text-to-Speech configuration for frontend."""
    try:
        settings = get_settings()
        return {
            "enabled": settings.tts_enabled,
            "rate": settings.tts_rate,
            "pitch": settings.tts_pitch,
            "volume": settings.tts_volume,
            "voice_name": settings.tts_voice_name
        }
    except Exception as e:
        logger.error(f"Error getting TTS config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-queue", response_model=Dict[str, Any])
async def clear_queue() -> Dict[str, Any]:
    """Clear all pending items."""
    try:
        jarvis = get_voice_approval()
        count = len(jarvis.pending_items)
        jarvis.pending_items.clear()
        jarvis.current_item = None
        
        return {
            "status": "cleared",
            "items_cleared": count
        }
    except Exception as e:
        logger.error(f"Error clearing queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-add-drafts", response_model=Dict[str, Any])
async def bulk_add_drafts(drafts: List[AddEmailDraftRequest]) -> Dict[str, Any]:
    """Add multiple email drafts at once."""
    try:
        jarvis = get_voice_approval()
        
        for draft in drafts:
            jarvis.add_email_draft(
                draft_id=draft.draft_id,
                to_email=draft.to_email,
                to_name=draft.to_name,
                subject=draft.subject,
                body=draft.body,
                context=draft.context,
                agent=draft.agent
            )
        
        return {
            "status": "added",
            "count": len(drafts),
            "queue_length": len(jarvis.pending_items)
        }
    except Exception as e:
        logger.error(f"Error bulk adding drafts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
