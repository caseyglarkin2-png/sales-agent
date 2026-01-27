"""Gemini AI Chat API endpoints.

Sprint 34: Gemini Portal Foundation
Sprint 39B: Persistent conversation memory via MemoryService

Provides API endpoints for Gemini AI chat interactions.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.db import get_db, Base, SafeJSON
from src.connectors.gemini import GeminiConnector, GeminiModel, GeminiResponse
from src.auth.decorators import get_current_user_optional
from src.models.user import User
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/gemini", tags=["Gemini AI"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatMessage(BaseModel):
    """A single chat message."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    sources: Optional[List[dict]] = Field(None, description="Grounding sources if any")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp")


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    model: Optional[str] = Field(None, description="Gemini model to use")
    enable_grounding: bool = Field(False, description="Enable Google Search grounding")
    system_prompt: Optional[str] = Field(None, description="System prompt/context")
    session_id: Optional[str] = Field(None, description="Chat session ID for history")
    file_ids: Optional[List[str]] = Field(None, description="Drive file IDs for context")


class ChatResponse(BaseModel):
    """Response from Gemini chat."""
    response: str = Field(..., description="AI response text")
    model_used: str = Field(..., description="Model that generated the response")
    sources: Optional[List[dict]] = Field(None, description="Grounding sources")
    session_id: str = Field(..., description="Chat session ID")
    tokens_used: int = Field(0, description="Total tokens used")


class ModelInfo(BaseModel):
    """Information about a Gemini model."""
    id: str
    name: str
    description: str
    context_window: int
    recommended_for: List[str]


class SystemPromptTemplate(BaseModel):
    """A system prompt template."""
    id: str
    name: str
    description: str
    prompt: str


# ============================================================================
# In-memory chat sessions (to be migrated to DB in Task 34.5)
# ============================================================================

_chat_sessions: dict[str, List[ChatMessage]] = {}


# ============================================================================
# System Prompt Templates
# ============================================================================

SYSTEM_PROMPTS = {
    "sales_assistant": SystemPromptTemplate(
        id="sales_assistant",
        name="Sales Assistant",
        description="Expert B2B sales assistant for outreach and follow-ups",
        prompt="""You are Casey, an expert B2B sales assistant for CaseyOS. You help with:
- Crafting personalized outreach emails
- Analyzing prospects and accounts
- Preparing for sales calls
- Writing follow-up messages
- Handling objections

Be concise, professional, and action-oriented. Focus on value propositions and next steps."""
    ),
    "researcher": SystemPromptTemplate(
        id="researcher",
        name="Research Analyst",
        description="Deep research and competitive analysis",
        prompt="""You are a thorough research analyst. Your job is to:
- Research companies, industries, and market trends
- Analyze competitive landscapes
- Summarize findings with citations
- Identify key insights and opportunities

Always cite your sources when using grounded information. Be comprehensive but organized."""
    ),
    "writer": SystemPromptTemplate(
        id="writer",
        name="Content Writer",
        description="Professional content and copywriting",
        prompt="""You are a professional content writer specializing in B2B marketing. You create:
- Blog posts and articles
- Social media content
- Marketing copy
- Case studies
- Email campaigns

Write in a clear, engaging style. Adapt tone based on the target audience."""
    ),
    "analyst": SystemPromptTemplate(
        id="analyst",
        name="Data Analyst",
        description="Analyze data and generate insights",
        prompt="""You are a data analyst helping interpret sales and business data. You:
- Analyze metrics and KPIs
- Identify trends and patterns
- Generate actionable insights
- Create summaries and reports

Be precise with numbers. Highlight key takeaways and recommended actions."""
    ),
}


# ============================================================================
# Available Models
# ============================================================================

AVAILABLE_MODELS = [
    ModelInfo(
        id="gemini-2.0-flash-exp",
        name="Gemini 2.0 Flash",
        description="Fastest model, great for most tasks",
        context_window=1000000,
        recommended_for=["chat", "quick_tasks", "real_time"]
    ),
    ModelInfo(
        id="gemini-1.5-pro",
        name="Gemini 1.5 Pro",
        description="High capability with massive context",
        context_window=2000000,
        recommended_for=["research", "long_documents", "complex_analysis"]
    ),
    ModelInfo(
        id="gemini-1.5-flash",
        name="Gemini 1.5 Flash",
        description="Fast and versatile",
        context_window=1000000,
        recommended_for=["general", "balanced"]
    ),
    ModelInfo(
        id="gemini-exp-1206",
        name="Gemini Experimental",
        description="Enhanced reasoning capabilities",
        context_window=1000000,
        recommended_for=["complex_reasoning", "coding"]
    ),
]


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Send a message to Gemini and get a response.
    
    Supports:
    - Model selection
    - Google Search grounding
    - System prompts
    - Chat history (via session_id)
    - File context (via file_ids)
    """
    # Initialize connector
    connector = GeminiConnector()
    
    # Get or create session
    session_id = request.session_id or str(uuid4())
    if session_id not in _chat_sessions:
        _chat_sessions[session_id] = []
    
    history = _chat_sessions[session_id]
    
    # Build context from history
    context_parts = []
    if history:
        for msg in history[-10:]:  # Last 10 messages for context
            context_parts.append(f"{msg.role}: {msg.content}")
    
    # Get system prompt
    system_prompt = request.system_prompt
    if system_prompt and system_prompt in SYSTEM_PROMPTS:
        system_prompt = SYSTEM_PROMPTS[system_prompt].prompt
    
    # Build full prompt with context
    if context_parts:
        full_prompt = f"""Previous conversation:
{chr(10).join(context_parts)}

User: {request.message}"""
    else:
        full_prompt = request.message
    
    # Get file context if provided
    if request.file_ids:
        # TODO: Sprint 35 - Integrate Drive file content
        logger.info(f"File context requested for: {request.file_ids}")
    
    try:
        # Select model
        model = None
        if request.model:
            try:
                model = GeminiModel(request.model)
            except ValueError:
                logger.warning(f"Unknown model {request.model}, using default")
        
        # Generate response
        result = await connector.generate(
            prompt=full_prompt,
            model=model,
            system_instruction=system_prompt,
            enable_grounding=request.enable_grounding,
        )
        
        # Store messages in in-memory history
        history.append(ChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.utcnow()
        ))
        history.append(ChatMessage(
            role="assistant",
            content=result.text,
            sources=result.grounding_sources,
            timestamp=datetime.utcnow()
        ))
        
        return ChatResponse(
            response=result.text,
            model_used=result.model,
            sources=result.grounding_sources,
            session_id=session_id,
            tokens_used=result.usage.get("total_tokens", 0)
        )
        
    except Exception as e:
        logger.error(f"Gemini chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
    finally:
        await connector.close()


@router.get("/models", response_model=List[ModelInfo])
async def list_models():
    """List available Gemini models."""
    return AVAILABLE_MODELS


@router.get("/system-prompts", response_model=List[SystemPromptTemplate])
async def list_system_prompts():
    """List available system prompt templates."""
    return list(SYSTEM_PROMPTS.values())


@router.get("/sessions/{session_id}/history", response_model=List[ChatMessage])
async def get_chat_history(session_id: str):
    """Get chat history for a session."""
    if session_id not in _chat_sessions:
        return []
    return _chat_sessions[session_id]


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear a chat session."""
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]
    return {"status": "cleared", "session_id": session_id}


@router.post("/chat/html")
async def chat_html(
    request: ChatRequest,
    user: Optional[User] = Depends(get_current_user_optional),
):
    """
    HTMX-friendly endpoint that returns HTML fragment.
    """
    from fastapi.responses import HTMLResponse
    
    try:
        result = await chat(request, user)
        
        # Format sources if present
        sources_html = ""
        if result.sources:
            sources_html = '<div class="mt-2 text-xs text-gray-500">'
            sources_html += '<span class="font-medium">Sources:</span> '
            for i, src in enumerate(result.sources[:5], 1):
                title = src.get("web", {}).get("title", f"Source {i}")
                uri = src.get("web", {}).get("uri", "#")
                sources_html += f'<a href="{uri}" target="_blank" class="text-blue-600 hover:underline mr-2">[{i}]</a>'
            sources_html += '</div>'
        
        html = f'''
        <div class="flex justify-end mb-4">
            <div class="bg-blue-100 rounded-lg px-4 py-2 max-w-[80%]">
                <p class="text-gray-800">{request.message}</p>
            </div>
        </div>
        <div class="flex justify-start mb-4">
            <div class="bg-white border border-gray-200 rounded-lg px-4 py-2 max-w-[80%] shadow-sm">
                <p class="text-gray-800 whitespace-pre-wrap">{result.response}</p>
                {sources_html}
                <div class="mt-1 text-xs text-gray-400">{result.model_used} • {result.tokens_used} tokens</div>
            </div>
        </div>
        '''
        return HTMLResponse(content=html)
        
    except Exception as e:
        error_html = f'''
        <div class="flex justify-start mb-4">
            <div class="bg-red-50 border border-red-200 rounded-lg px-4 py-2 max-w-[80%]">
                <p class="text-red-600">Error: {str(e)}</p>
            </div>
        </div>
        '''
        return HTMLResponse(content=error_html, status_code=500)


# ============================================================================
# Sprint 36: Jarvis-Integrated Endpoints
# ============================================================================

class JarvisRequest(BaseModel):
    """Request for Jarvis-powered chat."""
    message: str = Field(..., min_length=1, max_length=10000)
    enable_tools: bool = Field(True, description="Enable agent tool calling")


class JarvisResponse(BaseModel):
    """Response from Jarvis."""
    response: str
    tool_calls: Optional[List[dict]] = None
    status: str = "success"


@router.post("/jarvis/chat", response_model=JarvisResponse)
async def jarvis_chat(
    request: JarvisRequest,
    user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Chat with Jarvis - the AI orchestrator with tool access.
    
    Jarvis can:
    - Search Google Drive for documents
    - Draft emails
    - Query HubSpot CRM
    - Check/schedule calendar events
    - Research companies
    """
    from src.agents.jarvis import get_jarvis
    
    try:
        jarvis = get_jarvis()
        
        # Initialize if needed
        if not jarvis._initialized:
            await jarvis.initialize()
        
        if request.enable_tools:
            # Use tool-calling flow
            result = await jarvis.ask_with_tools(request.message)
        else:
            # Use standard ask
            result = await jarvis.ask(request.message)
        
        return JarvisResponse(
            response=result.get("response", str(result)),
            tool_calls=result.get("tool_calls"),
            status=result.get("status", "success"),
        )
        
    except Exception as e:
        logger.error(f"Jarvis chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jarvis/tools")
async def list_jarvis_tools():
    """List available Jarvis tools for Gemini."""
    from src.agents.jarvis import get_jarvis
    
    jarvis = get_jarvis()
    return {"tools": jarvis.get_tool_definitions()}


@router.post("/jarvis/chat/html")
async def jarvis_chat_html(
    request: JarvisRequest,
    user: Optional[User] = Depends(get_current_user_optional),
):
    """HTMX-friendly Jarvis chat endpoint."""
    from fastapi.responses import HTMLResponse
    
    try:
        result = await jarvis_chat(request, user)
        
        # Format tool calls if present
        tools_html = ""
        if result.tool_calls:
            tools_html = '<div class="mt-2 text-xs text-gray-500 border-t pt-2">'
            tools_html += '<span class="font-medium">🔧 Tools used:</span> '
            for tc in result.tool_calls:
                tools_html += f'<span class="bg-gray-100 px-2 py-1 rounded mr-1">{tc.get("tool")}</span>'
            tools_html += '</div>'
        
        html = f'''
        <div class="flex justify-start mb-4">
            <div class="bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-lg px-4 py-2 max-w-[80%] shadow-sm">
                <div class="flex items-center space-x-2 mb-1">
                    <span class="text-sm font-medium text-purple-700">🤖 Jarvis</span>
                </div>
                <p class="text-gray-800 whitespace-pre-wrap">{result.response}</p>
                {tools_html}
            </div>
        </div>
        '''
        return HTMLResponse(content=html)
        
    except Exception as e:
        error_html = f'''
        <div class="flex justify-start mb-4">
            <div class="bg-red-50 border border-red-200 rounded-lg px-4 py-2 max-w-[80%]">
                <p class="text-red-600">Jarvis Error: {str(e)}</p>
            </div>
        </div>
        '''
        return HTMLResponse(content=error_html, status_code=500)

