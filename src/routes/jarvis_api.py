"""
Jarvis API - The AI Gateway for CaseyOS.

Surfaces all agent capabilities, enables natural language queries,
and provides endpoints for agent management and approval workflows.

Sprint 16: Added proactive "Hey Jarvis" endpoints for daemon mode.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.jarvis import get_jarvis, AgentDomain
from src.connectors.llm import get_llm
from src.connectors.gemini import get_gemini
from src.config import get_settings
from src.deps import get_db_session
from src.db import get_session
from src.logger import get_logger
from src.telemetry import log_event

logger = get_logger(__name__)
router = APIRouter(prefix="/api/jarvis", tags=["jarvis"])
settings = get_settings()


# ============================================================================
# Request/Response Models
# ============================================================================

class JarvisQueryRequest(BaseModel):
    """Natural language query to Jarvis."""
    query: str = Field(..., description="What do you want Jarvis to do?")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class JarvisActionRequest(BaseModel):
    """Direct action request to a specific agent."""
    agent: str = Field(..., description="Agent name (e.g., 'draft_writer', 'proposal_generator')")
    action: str = Field(..., description="Action to perform")
    context: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")
    dry_run: bool = Field(default=False, description="Preview without executing")


class AgentApprovalRequest(BaseModel):
    """Request to approve/enable an agent action."""
    agent: str = Field(..., description="Agent name")
    action: str = Field(..., description="Action type to approve")
    scope: str = Field(default="session", description="Approval scope: session, day, always")
    conditions: Optional[Dict[str, Any]] = Field(default=None, description="Conditions for approval")


class AgentConfigRequest(BaseModel):
    """Configure agent behavior."""
    agent: str = Field(..., description="Agent name")
    settings: Dict[str, Any] = Field(..., description="Configuration settings")


class QuickActionRequest(BaseModel):
    """Quick action from the UI."""
    action_type: str = Field(..., description="Type: draft_email, schedule_meeting, create_proposal, etc.")
    target: Dict[str, Any] = Field(..., description="Target entity (contact, deal, company)")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Action options")


# ============================================================================
# Agent Registry & Discovery
# ============================================================================

@router.get("/health")
async def jarvis_health():
    """Jarvis system health check."""
    jarvis = get_jarvis()
    
    # Check LLM connectivity
    llm = get_llm()
    llm_health = await llm.health_check()
    
    # Check Gemini
    gemini = get_gemini()
    gemini_health = await gemini.health_check() if gemini else {"status": "not_configured"}
    
    return {
        "status": "healthy",
        "jarvis_version": "1.0.0",
        "initialized": jarvis._initialized,
        "agent_count": len(jarvis._agents) if jarvis._initialized else 0,
        "llm": llm_health,
        "gemini": gemini_health,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Sprint 16: Proactive "Hey Jarvis" Endpoints (Daemon Mode)
# ============================================================================

@router.get("/whats-up")
async def whats_up(
    user_id: str = Query(default="casey", description="User identifier"),
):
    """
    "Hey Jarvis, what's up?" - Get proactive notifications and suggestions.
    
    This is the primary entry point for daemon mode. Returns:
    - Urgent items needing attention
    - Notification counts by priority
    - Top items to review
    
    The daemon monitor (monitor_signals.py) creates notifications
    automatically when signals are detected.
    """
    from src.services.notification_service import NotificationService
    
    async with get_session() as db:
        notifications = NotificationService(db)
        result = await notifications.get_whats_up(user_id)
        
        log_event("whats_up_checked", user_id=user_id, total=result["total_unread"])
        
        return result


@router.get("/notifications")
async def get_notifications(
    user_id: str = Query(default="casey", description="User identifier"),
    limit: int = Query(default=20, ge=1, le=100),
    include_read: bool = Query(default=False),
):
    """Get notifications for a user."""
    from src.services.notification_service import NotificationService
    
    async with get_session() as db:
        service = NotificationService(db)
        notifications = await service.get_recent(user_id, limit, include_read)
        
        return {
            "notifications": [n.to_dict() for n in notifications],
            "count": len(notifications),
            "user_id": user_id,
        }


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark a notification as read."""
    from src.services.notification_service import NotificationService
    
    async with get_session() as db:
        service = NotificationService(db)
        success = await service.mark_read(notification_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {"status": "marked_read", "notification_id": notification_id}


@router.post("/notifications/{notification_id}/acknowledge")
async def acknowledge_notification(notification_id: str):
    """Acknowledge (dismiss) a notification."""
    from src.services.notification_service import NotificationService
    
    async with get_session() as db:
        service = NotificationService(db)
        success = await service.mark_acknowledged(notification_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {"status": "acknowledged", "notification_id": notification_id}


@router.post("/notifications/{notification_id}/action")
async def notification_actioned(notification_id: str):
    """Mark that the user took the suggested action."""
    from src.services.notification_service import NotificationService
    
    async with get_session() as db:
        service = NotificationService(db)
        success = await service.mark_actioned(notification_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        log_event("notification_action_taken", notification_id=notification_id)
        
        return {"status": "actioned", "notification_id": notification_id}


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    user_id: str = Query(default="casey", description="User identifier"),
):
    """Mark all notifications as read for a user."""
    from src.services.notification_service import NotificationService
    
    async with get_session() as db:
        service = NotificationService(db)
        count = await service.mark_all_read(user_id)
        
        return {"status": "marked_read", "count": count, "user_id": user_id}


# ============================================================================
# Sprint 17: Voice Interface Endpoints
# ============================================================================

class VoiceTranscribeResponse(BaseModel):
    """Response from voice transcription."""
    text: str
    wake_word_detected: bool = False
    wake_word: Optional[str] = None
    language: Optional[str] = None
    duration_seconds: Optional[float] = None


class VoiceSpeakRequest(BaseModel):
    """Request for text-to-speech."""
    text: str = Field(..., description="Text to speak")
    voice: Optional[str] = Field(default="nova", description="Voice: alloy, echo, fable, onyx, nova, shimmer")
    speed: Optional[float] = Field(default=1.0, ge=0.25, le=4.0, description="Speech speed")


class VoiceSpeakResponse(BaseModel):
    """Response from text-to-speech."""
    audio_base64: str
    format: str = "mp3"
    voice: str
    text_length: int


class VoiceConversationRequest(BaseModel):
    """Full voice conversation: audio in → Jarvis → audio out."""
    user_id: Optional[str] = Field(default="casey", description="User identifier")
    session_name: Optional[str] = Field(default="voice", description="Session name")
    voice: Optional[str] = Field(default="nova", description="Response voice")


class VoiceConversationResponse(BaseModel):
    """Response from voice conversation."""
    transcription: str
    response_text: str
    response_audio_base64: str
    wake_word_detected: bool
    session_id: Optional[str] = None


@router.post("/voice/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe_audio(
    audio: bytes = None,  # Will be handled by UploadFile
):
    """Transcribe audio to text using OpenAI Whisper.
    
    Send audio file as multipart/form-data or raw bytes.
    Supports: mp3, wav, webm, m4a, ogg, flac
    """
    from fastapi import UploadFile, File
    # This endpoint needs to be called differently - see voice_transcribe_file below
    raise HTTPException(
        status_code=400, 
        detail="Use /voice/transcribe-file with multipart upload"
    )


@router.post("/voice/transcribe-file", response_model=VoiceTranscribeResponse)
async def transcribe_audio_file(
    file: UploadFile = File(...),
    detect_wake_word: bool = Query(default=True, description="Check for wake word")
):
    """Transcribe uploaded audio file to text.
    
    Accepts multipart/form-data with audio file.
    """
    from src.services.voice_service import get_voice_service
    
    if file is None:
        raise HTTPException(status_code=400, detail="No audio file provided")
    
    try:
        audio_data = await file.read()
        
        voice_service = get_voice_service()
        result = await voice_service.transcribe(
            audio_data=audio_data,
            detect_wake_word=detect_wake_word
        )
        
        log_event("voice_transcribed", text_length=len(result.text), wake_word=result.wake_word_detected)
        
        return VoiceTranscribeResponse(
            text=result.text,
            wake_word_detected=result.wake_word_detected,
            wake_word=result.wake_word,
            language=result.language,
            duration_seconds=result.duration_seconds
        )
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/voice/speak", response_model=VoiceSpeakResponse)
async def text_to_speech(request: VoiceSpeakRequest):
    """Convert text to speech using OpenAI TTS.
    
    Returns base64-encoded MP3 audio.
    """
    from src.services.voice_service import get_voice_service, TTSVoice
    
    try:
        voice_service = get_voice_service()
        
        # Parse voice name
        try:
            voice = TTSVoice(request.voice.lower()) if request.voice else TTSVoice.NOVA
        except ValueError:
            voice = TTSVoice.NOVA
        
        result = await voice_service.speak(
            text=request.text,
            voice=voice,
            speed=request.speed or 1.0
        )
        
        log_event("voice_spoken", text_length=len(request.text), voice=voice.value)
        
        return VoiceSpeakResponse(
            audio_base64=result.audio_base64,
            format=result.format,
            voice=result.voice,
            text_length=result.text_length
        )
        
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail=f"Text-to-speech failed: {str(e)}")


@router.post("/voice/conversation", response_model=VoiceConversationResponse)
async def voice_conversation(
    file: UploadFile = File(...),
    user_id: str = Query(default="casey", description="User identifier"),
    session_name: str = Query(default="voice", description="Session name"),
    voice: str = Query(default="nova", description="Response voice")
):
    """Full voice conversation loop: audio in → Jarvis → audio out.
    
    1. Transcribes audio input
    2. Sends query to Jarvis (with memory)
    3. Synthesizes response to audio
    4. Returns both text and audio
    """
    from src.services.voice_service import get_voice_service, TTSVoice
    
    try:
        audio_data = await file.read()
        voice_service = get_voice_service()
        
        # Step 1: Transcribe
        transcription = await voice_service.transcribe(audio_data, detect_wake_word=True)
        
        # Strip wake word if present
        query_text = voice_service.strip_wake_word(transcription.text) if transcription.wake_word_detected else transcription.text
        
        if not query_text.strip():
            raise HTTPException(status_code=400, detail="No query detected after wake word")
        
        # Step 2: Query Jarvis
        jarvis = get_jarvis()
        if not jarvis._initialized:
            await jarvis.initialize()
        
        response_text = await jarvis.ask(
            query=query_text,
            user_id=user_id,
            session_name=session_name
        )
        
        # Step 3: Synthesize response
        try:
            tts_voice = TTSVoice(voice.lower())
        except ValueError:
            tts_voice = TTSVoice.NOVA
            
        speech = await voice_service.speak(text=response_text, voice=tts_voice)
        
        log_event("voice_conversation", 
                  query_length=len(query_text), 
                  response_length=len(response_text),
                  wake_word=transcription.wake_word_detected)
        
        return VoiceConversationResponse(
            transcription=transcription.text,
            response_text=response_text,
            response_audio_base64=speech.audio_base64,
            wake_word_detected=transcription.wake_word_detected
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice conversation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice conversation failed: {str(e)}")


@router.get("/voice/voices")
async def list_voices():
    """List available TTS voices."""
    from src.services.voice_service import TTSVoice
    
    return {
        "voices": [
            {"id": "alloy", "name": "Alloy", "description": "Neutral, balanced"},
            {"id": "echo", "name": "Echo", "description": "Warm, conversational"},
            {"id": "fable", "name": "Fable", "description": "Expressive, British"},
            {"id": "onyx", "name": "Onyx", "description": "Deep, authoritative"},
            {"id": "nova", "name": "Nova", "description": "Friendly, upbeat (default)"},
            {"id": "shimmer", "name": "Shimmer", "description": "Clear, optimistic"},
        ],
        "default": "nova"
    }


# ============================================================================
# Agent Registry & Discovery
# ============================================================================

@router.get("/agents")
async def list_agents():
    """List all registered agents with their capabilities."""
    jarvis = get_jarvis()
    
    if not jarvis._initialized:
        await jarvis.initialize()
    
    agents = jarvis.list_agents()
    
    # Group by domain
    by_domain = {}
    for name, info in agents.items():
        domain = info["domain"]
        if domain not in by_domain:
            by_domain[domain] = []
        by_domain[domain].append({
            "name": name,
            "description": info["description"],
            "capabilities": info["capabilities"],
        })
    
    return {
        "total": len(agents),
        "domains": list(by_domain.keys()),
        "agents": agents,
        "by_domain": by_domain,
    }


@router.get("/agents/{agent_name}")
async def get_agent_details(agent_name: str):
    """Get detailed information about a specific agent."""
    jarvis = get_jarvis()
    
    if not jarvis._initialized:
        await jarvis.initialize()
    
    if agent_name not in jarvis._agent_registry:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    info = jarvis._agent_registry[agent_name]
    agent = info["agent"]
    
    return {
        "name": agent_name,
        "display_name": agent.name,
        "description": agent.description,
        "domain": info["domain"].value,
        "capabilities": info["capabilities"],
        "registered_at": info["registered_at"],
        "input_schema": getattr(agent, "input_schema", None),
        "output_schema": getattr(agent, "output_schema", None),
    }


@router.get("/domains")
async def list_domains():
    """List all agent domains with their agents."""
    jarvis = get_jarvis()
    
    if not jarvis._initialized:
        await jarvis.initialize()
    
    domains = {}
    for domain in AgentDomain:
        agents = jarvis.get_agents_by_domain(domain)
        domains[domain.value] = {
            "name": domain.value,
            "display_name": domain.value.replace("_", " ").title(),
            "agents": agents,
            "agent_count": len(agents),
        }
    
    return {
        "domains": domains,
        "total_domains": len(domains),
    }


@router.get("/capabilities")
async def list_all_capabilities():
    """List all capabilities across all agents (for search/autocomplete)."""
    jarvis = get_jarvis()
    
    if not jarvis._initialized:
        await jarvis.initialize()
    
    capabilities = {}
    for name, info in jarvis._agent_registry.items():
        for cap in info["capabilities"]:
            if cap not in capabilities:
                capabilities[cap] = []
            capabilities[cap].append(name)
    
    return {
        "capabilities": capabilities,
        "total": len(capabilities),
    }


# ============================================================================
# Natural Language Interface
# ============================================================================

@router.post("/ask")
async def ask_jarvis(request: JarvisQueryRequest):
    """Ask Jarvis a natural language question or request."""
    jarvis = get_jarvis()
    
    if not jarvis._initialized:
        await jarvis.initialize()
    
    await log_event("jarvis_query", properties={"query": request.query[:100]})
    
    try:
        result = await jarvis.ask(request.query, request.context or {})
        
        await log_event("jarvis_response", 
                  properties={"agents_invoked": result.get("agents_invoked", []),
                  "status": result.get("status")})
        
        return result
    except Exception as e:
        logger.error(f"Jarvis query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_action(request: JarvisActionRequest):
    """Execute a specific action on a specific agent."""
    jarvis = get_jarvis()
    
    if not jarvis._initialized:
        await jarvis.initialize()
    
    if request.agent not in jarvis._agents:
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent}' not found")
    
    await log_event("jarvis_execute", 
              properties={"agent": request.agent, 
              "action": request.action,
              "dry_run": request.dry_run})
    
    context = {
        **request.context,
        "action": request.action,
        "dry_run": request.dry_run,
    }
    
    try:
        agent = jarvis._agents[request.agent]
        result = await agent.execute(context)
        
        return {
            "status": "success",
            "agent": request.agent,
            "action": request.action,
            "dry_run": request.dry_run,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Quick Actions (Pre-defined workflows)
# ============================================================================

@router.post("/quick-action")
async def quick_action(request: QuickActionRequest, background_tasks: BackgroundTasks):
    """Execute a pre-defined quick action."""
    jarvis = get_jarvis()
    
    if not jarvis._initialized:
        await jarvis.initialize()
    
    action_handlers = {
        "draft_email": _handle_draft_email,
        "schedule_meeting": _handle_schedule_meeting,
        "create_proposal": _handle_create_proposal,
        "research_company": _handle_research_company,
        "score_lead": _handle_score_lead,
        "generate_followup": _handle_generate_followup,
        "check_health": _handle_check_health,
        "repurpose_content": _handle_repurpose_content,
    }
    
    handler = action_handlers.get(request.action_type)
    if not handler:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown action type: {request.action_type}. Available: {list(action_handlers.keys())}"
        )
    
    await log_event("jarvis_quick_action", properties={"action_type": request.action_type})
    
    try:
        result = await handler(jarvis, request.target, request.options or {})
        return {
            "status": "success",
            "action_type": request.action_type,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Quick action failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_draft_email(jarvis, target: Dict, options: Dict) -> Dict:
    """Draft an email for a contact/deal."""
    agent = jarvis.get_agent("draft_writer")
    if not agent:
        return {"error": "Draft writer agent not available"}
    
    return await agent.execute({
        "action": "write_email",
        "recipient": target.get("email"),
        "context": target,
        "tone": options.get("tone", "professional"),
        "purpose": options.get("purpose", "follow_up"),
    })


async def _handle_schedule_meeting(jarvis, target: Dict, options: Dict) -> Dict:
    """Get meeting slots for a contact."""
    agent = jarvis.get_agent("meeting_slot")
    if not agent:
        return {"error": "Meeting slot agent not available"}
    
    return await agent.execute({
        "action": "propose_slots",
        "attendee": target.get("email"),
        "duration_minutes": options.get("duration", 30),
        "days_ahead": options.get("days_ahead", 7),
    })


async def _handle_create_proposal(jarvis, target: Dict, options: Dict) -> Dict:
    """Generate a proposal for a deal."""
    agent = jarvis.get_agent("proposal_generator")
    if not agent:
        return {"error": "Proposal generator agent not available"}
    
    return await agent.execute({
        "action": "generate_proposal",
        "deal_id": target.get("deal_id"),
        "company": target.get("company"),
        "template": options.get("template", "standard"),
        "include_pricing": options.get("include_pricing", True),
    })


async def _handle_research_company(jarvis, target: Dict, options: Dict) -> Dict:
    """Research a company."""
    agent = jarvis.get_agent("research")
    if not agent:
        return {"error": "Research agent not available"}
    
    return await agent.execute({
        "action": "enrich_prospect",
        "company_domain": target.get("domain") or target.get("company"),
        "depth": options.get("depth", "standard"),
    })


async def _handle_score_lead(jarvis, target: Dict, options: Dict) -> Dict:
    """Score a lead using AI."""
    # Use Gemini's lead scoring if available
    gemini = get_gemini()
    if gemini and settings.gemini_api_key:
        return await gemini.score_lead(
            lead_data=target,
            icp_criteria=options.get("icp_criteria"),
        )
    
    # Fallback to prospecting agent
    agent = jarvis.get_agent("prospecting")
    if not agent:
        return {"error": "Lead scoring not available"}
    
    return await agent.execute({
        "action": "score_relevance",
        "lead": target,
    })


async def _handle_generate_followup(jarvis, target: Dict, options: Dict) -> Dict:
    """Generate follow-up strategy."""
    agent = jarvis.get_agent("nurturing")
    if not agent:
        return {"error": "Nurturing agent not available"}
    
    return await agent.execute({
        "action": "follow_up_sequence",
        "contact_id": target.get("contact_id"),
        "engagement_stage": options.get("stage", "awareness"),
    })


async def _handle_check_health(jarvis, target: Dict, options: Dict) -> Dict:
    """Check client health score."""
    agent = jarvis.get_agent("client_health")
    if not agent:
        return {"error": "Client health agent not available"}
    
    return await agent.execute({
        "action": "monitor_engagement",
        "account_id": target.get("account_id") or target.get("company_id"),
    })


async def _handle_repurpose_content(jarvis, target: Dict, options: Dict) -> Dict:
    """Repurpose content into multiple formats."""
    agent = jarvis.get_agent("content_repurpose")
    if not agent:
        return {"error": "Content repurpose agent not available"}
    
    return await agent.execute({
        "action": "repurpose_content",
        "source_content": target.get("content"),
        "source_url": target.get("url"),
        "formats": options.get("formats", ["linkedin_post", "twitter_thread", "email_snippet"]),
    })


# ============================================================================
# Agent Approval & Configuration
# ============================================================================

# In-memory approval store (would be DB in production)
_agent_approvals: Dict[str, Dict] = {}
_agent_configs: Dict[str, Dict] = {}


@router.post("/agents/{agent_name}/approve")
async def approve_agent_action(agent_name: str, request: AgentApprovalRequest):
    """Approve an agent to perform certain actions."""
    jarvis = get_jarvis()
    
    if not jarvis._initialized:
        await jarvis.initialize()
    
    if agent_name not in jarvis._agents:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    key = f"{agent_name}:{request.action}"
    _agent_approvals[key] = {
        "agent": agent_name,
        "action": request.action,
        "scope": request.scope,
        "conditions": request.conditions,
        "approved_at": datetime.utcnow().isoformat(),
        "expires_at": None,  # Could add expiration logic
    }
    
    await log_event("agent_approved", properties={"agent": agent_name, "action": request.action, "scope": request.scope})
    
    return {
        "status": "approved",
        "agent": agent_name,
        "action": request.action,
        "scope": request.scope,
        "message": f"Agent '{agent_name}' approved for '{request.action}' ({request.scope})",
    }


@router.delete("/agents/{agent_name}/approve/{action}")
async def revoke_agent_approval(agent_name: str, action: str):
    """Revoke an agent's approval for an action."""
    key = f"{agent_name}:{action}"
    
    if key in _agent_approvals:
        del _agent_approvals[key]
        await log_event("agent_approval_revoked", properties={"agent": agent_name, "action": action})
        return {"status": "revoked", "agent": agent_name, "action": action}
    
    raise HTTPException(status_code=404, detail="Approval not found")


@router.get("/approvals")
async def list_approvals():
    """List all current agent approvals."""
    return {
        "approvals": list(_agent_approvals.values()),
        "total": len(_agent_approvals),
    }


@router.post("/agents/{agent_name}/configure")
async def configure_agent(agent_name: str, request: AgentConfigRequest):
    """Configure agent behavior."""
    jarvis = get_jarvis()
    
    if not jarvis._initialized:
        await jarvis.initialize()
    
    if agent_name not in jarvis._agents:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    _agent_configs[agent_name] = {
        **_agent_configs.get(agent_name, {}),
        **request.settings,
        "updated_at": datetime.utcnow().isoformat(),
    }
    
    await log_event("agent_configured", properties={"agent": agent_name, "settings": list(request.settings.keys())})
    
    return {
        "status": "configured",
        "agent": agent_name,
        "settings": _agent_configs[agent_name],
    }


@router.get("/agents/{agent_name}/config")
async def get_agent_config(agent_name: str):
    """Get agent configuration."""
    return {
        "agent": agent_name,
        "config": _agent_configs.get(agent_name, {}),
    }


# ============================================================================
# Batch Operations
# ============================================================================

@router.post("/batch")
async def batch_execute(requests: List[JarvisActionRequest]):
    """Execute multiple agent actions in batch."""
    jarvis = get_jarvis()
    
    if not jarvis._initialized:
        await jarvis.initialize()
    
    if len(requests) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 actions per batch")
    
    results = []
    for req in requests:
        try:
            if req.agent not in jarvis._agents:
                results.append({
                    "agent": req.agent,
                    "action": req.action,
                    "status": "error",
                    "error": f"Agent '{req.agent}' not found",
                })
                continue
            
            agent = jarvis._agents[req.agent]
            context = {**req.context, "action": req.action, "dry_run": req.dry_run}
            result = await agent.execute(context)
            
            results.append({
                "agent": req.agent,
                "action": req.action,
                "status": "success",
                "result": result,
            })
        except Exception as e:
            results.append({
                "agent": req.agent,
                "action": req.action,
                "status": "error",
                "error": str(e),
            })
    
    return {
        "batch_size": len(requests),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "error"),
        "results": results,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Conversation Context
# ============================================================================

@router.get("/context")
async def get_conversation_context():
    """Get current conversation context."""
    jarvis = get_jarvis()
    return {
        "context": jarvis._conversation_context,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.delete("/context")
async def clear_conversation_context():
    """Clear conversation context."""
    jarvis = get_jarvis()
    jarvis._conversation_context = {}
    return {"status": "cleared"}


# ============================================================================
# Agent Playground
# ============================================================================

@router.post("/playground")
async def agent_playground(
    agent_name: str,
    prompt: str,
    use_gemini: bool = False,
):
    """Test an agent with a custom prompt (for development/exploration)."""
    jarvis = get_jarvis()
    
    if not jarvis._initialized:
        await jarvis.initialize()
    
    # If agent specified, use it
    if agent_name != "llm":
        if agent_name not in jarvis._agents:
            raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        
        agent = jarvis._agents[agent_name]
        result = await agent.execute({"query": prompt})
        return {"agent": agent_name, "result": result}
    
    # Direct LLM access
    if use_gemini:
        gemini = get_gemini()
        if not gemini or not settings.gemini_api_key:
            raise HTTPException(status_code=400, detail="Gemini not configured")
        result = await gemini.generate(prompt)
    else:
        llm = get_llm()
        result = await llm.generate_text(prompt)
    
    return {
        "provider": "gemini" if use_gemini else "openai",
        "result": result,
    }
