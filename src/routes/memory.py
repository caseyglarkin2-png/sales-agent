"""
Memory API Endpoints for Jarvis Persistent Memory.

These endpoints provide access to Jarvis's persistent memory system,
enabling Henry-style memory management across sessions.

Endpoints:
- GET /api/jarvis/memory/{session_id} - Get session memory
- POST /api/jarvis/memory/search - Semantic search across memory
- DELETE /api/jarvis/memory/{session_id} - Clear session memory (GDPR)
- GET /api/jarvis/sessions - List all sessions for a user
- POST /api/jarvis/remember - Manually add a memory
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.db import get_session
from src.services.memory_service import MemoryService
from src.logger import get_logger
from src.security.csrf import verify_csrf_token

logger = get_logger(__name__)

router = APIRouter(prefix="/api/jarvis", tags=["memory"])


# =========================================================================
# Request/Response Models
# =========================================================================

class MemorySearchRequest(BaseModel):
    """Request for semantic memory search."""
    session_id: str
    query: str
    limit: int = Field(default=5, ge=1, le=20)


class MemorySearchResult(BaseModel):
    """Single search result."""
    content: str
    role: str
    similarity: float
    created_at: datetime
    metadata: dict = {}


class RememberRequest(BaseModel):
    """Request to manually add a memory."""
    session_id: str
    role: str = Field(default="user", pattern="^(user|assistant|system)$")
    content: str = Field(min_length=1, max_length=10000)
    metadata: dict = Field(default_factory=dict)


class SessionInfo(BaseModel):
    """Session information."""
    id: str
    session_name: str
    last_topic: Optional[str]
    message_count: int
    last_active: datetime
    created_at: datetime
    is_active: bool


# =========================================================================
# Endpoints
# =========================================================================

@router.get("/sessions")
async def list_sessions(
    user_id: str = Query(default="casey", description="User identifier"),
    include_inactive: bool = Query(default=False, description="Include inactive sessions"),
):
    """
    List all Jarvis sessions for a user.
    
    Returns:
        List of session info objects
    """
    async with get_session() as db:
        memory = MemoryService(db)
        sessions = await memory.list_sessions(user_id, include_inactive)
        
        return {
            "user_id": user_id,
            "sessions": [
                {
                    "id": str(s.id),
                    "session_name": s.session_name,
                    "last_topic": s.last_topic,
                    "message_count": s.message_count,
                    "last_active": s.last_active.isoformat() if s.last_active else None,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "is_active": s.is_active,
                }
                for s in sessions
            ],
            "count": len(sessions),
        }


@router.get("/memory/{session_id}")
async def get_session_memory(
    session_id: str,
    limit: int = Query(default=20, ge=1, le=100, description="Max messages to return"),
):
    """
    Get conversation history for a session.
    
    Returns:
        Recent messages from the session
    """
    async with get_session() as db:
        memory = MemoryService(db)
        messages = await memory.recall(session_id, limit=limit)
        
        if not messages:
            return {
                "session_id": session_id,
                "messages": [],
                "count": 0,
                "note": "No messages found. Session may not exist.",
            }
        
        return {
            "session_id": session_id,
            "messages": [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "importance": m.importance,
                    "metadata": m.message_metadata or {},
                }
                for m in messages
            ],
            "count": len(messages),
        }


@router.post("/memory/search")
async def search_memory(request: MemorySearchRequest):
    """
    Semantic search across session memory.
    
    Finds messages similar to the query using embedding-based search.
    
    Returns:
        List of relevant messages with similarity scores
    """
    async with get_session() as db:
        memory = MemoryService(db)
        results = await memory.search_similar(
            request.session_id,
            request.query,
            limit=request.limit,
        )
        
        return {
            "session_id": request.session_id,
            "query": request.query,
            "results": [
                {
                    "content": r.content,
                    "role": r.role,
                    "similarity": getattr(r, '_similarity', 0.0),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "metadata": r.message_metadata or {},
                }
                for r in results
            ],
            "count": len(results),
        }


@router.post("/remember", dependencies=[Depends(verify_csrf_token)])
async def manually_remember(request: RememberRequest):
    """
    Manually add a memory to a session.
    
    Useful for:
    - Injecting context from external sources
    - Recording important facts
    - Adding system messages
    
    Returns:
        Created memory record
    """
    async with get_session() as db:
        memory = MemoryService(db)
        
        # Verify session exists
        from sqlalchemy import select
        from src.models.memory import JarvisSession
        result = await db.execute(
            select(JarvisSession).where(JarvisSession.id == request.session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(status_code=404, detail=f"Session not found: {request.session_id}")
        
        # Remember the content
        message = await memory.remember(
            session_id=request.session_id,
            role=request.role,
            content=request.content,
            metadata=request.metadata,
        )
        
        return {
            "status": "remembered",
            "message_id": str(message.id),
            "session_id": request.session_id,
            "role": request.role,
            "content_preview": request.content[:100] + "..." if len(request.content) > 100 else request.content,
        }


@router.delete("/memory/{session_id}", dependencies=[Depends(verify_csrf_token)])
async def clear_session_memory(session_id: str):
    """
    Clear all memory for a session (GDPR compliance).
    
    This permanently deletes:
    - All messages in the session
    - All summaries for the session
    - The session itself
    
    Returns:
        Confirmation of deletion
    """
    async with get_session() as db:
        memory = MemoryService(db)
        
        # Use forget method (GDPR-compliant deletion)
        deleted = await memory.forget(session_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
        
        logger.info(f"Deleted memory for session {session_id} (GDPR request)")
        
        return {
            "status": "deleted",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.post("/sessions/create")
async def create_session(
    user_id: str = Query(default="casey", description="User identifier"),
    session_name: str = Query(default="default", description="Session name"),
):
    """
    Create a new Jarvis session.
    
    Returns:
        Created session info
    """
    async with get_session() as db:
        memory = MemoryService(db)
        session = await memory.get_or_create_session(user_id, session_name)
        
        return {
            "status": "created",
            "session": {
                "id": str(session.id),
                "user_id": session.user_id,
                "session_name": session.session_name,
                "created_at": session.created_at.isoformat() if session.created_at else None,
            },
        }


@router.get("/memory/stats")
async def get_memory_stats(
    user_id: str = Query(default="casey", description="User identifier"),
):
    """
    Get memory usage statistics for a user.
    
    Returns:
        Total sessions, messages, summaries, etc.
    """
    async with get_session() as db:
        from sqlalchemy import select, func
        from src.models.memory import JarvisSession, ConversationMemory, MemorySummary
        
        # Count sessions
        session_result = await db.execute(
            select(func.count(JarvisSession.id)).where(
                JarvisSession.user_id == user_id
            )
        )
        session_count = session_result.scalar() or 0
        
        # Count messages across all sessions
        message_result = await db.execute(
            select(func.count(ConversationMemory.id)).where(
                ConversationMemory.session_id.in_(
                    select(JarvisSession.id).where(JarvisSession.user_id == user_id)
                )
            )
        )
        message_count = message_result.scalar() or 0
        
        # Count summaries
        summary_result = await db.execute(
            select(func.count(MemorySummary.id)).where(
                MemorySummary.session_id.in_(
                    select(JarvisSession.id).where(JarvisSession.user_id == user_id)
                )
            )
        )
        summary_count = summary_result.scalar() or 0
        
        return {
            "user_id": user_id,
            "stats": {
                "total_sessions": session_count,
                "total_messages": message_count,
                "total_summaries": summary_count,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
