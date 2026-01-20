"""API routes for agent operations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.demo import DemoAgent
from src.agents.nurturing import NurturingAgent
from src.agents.outcome_reporter import OutcomeReporterAgent
from src.agents.prospecting import ProspectingAgent
from src.agents.validation import ValidationAgent
from src.agents.research import ResearchAgent
from src.connectors.hubspot import HubSpotConnector
from src.connectors.llm import LLMConnector
from src.config import get_settings
from src.deps import get_db_session
from src.logger import get_logger
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import os

from openai import AsyncOpenAI

logger = get_logger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])

# Initialize services
settings = get_settings()


class ProspectingRequest(BaseModel):
    """Request model for prospecting analysis."""

    message_id: str
    sender: str
    subject: str
    body: str


class NurturingRequest(BaseModel):
    """Request model for nurturing workflow."""

    contact_id: str
    company_id: str
    engagement_stage: str


class ValidationRequest(BaseModel):
    """Request model for validation."""

    draft_id: str
    recipient: str
    subject: str
    body: str


class DemoRequest(BaseModel):
    """Request model for demo."""

    demo_type: str
    company_domain: str


class ReportRequest(BaseModel):
    """Request model for reports."""

    report_type: str
    time_period: str


@router.post("/prospecting/analyze", response_model=Dict[str, Any])
async def analyze_prospect(
    request: ProspectingRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Analyze incoming message for prospecting opportunity."""
    try:
        llm = LLMConnector(settings.openai_api_key, settings.openai_model)
        agent = ProspectingAgent(llm)

        result = await agent.execute(request.dict())
        logger.info(f"Prospecting analysis completed for {request.sender}")
        return result
    except Exception as e:
        logger.error(f"Error in prospecting analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nurturing/schedule", response_model=Dict[str, Any])
async def schedule_nurturing(
    request: NurturingRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Schedule nurturing workflow for contact."""
    try:
        hubspot = HubSpotConnector(settings.hubspot_api_key)
        agent = NurturingAgent(hubspot)

        result = await agent.execute(request.dict())
        logger.info(f"Nurturing workflow scheduled for {request.contact_id}")
        return result
    except Exception as e:
        logger.error(f"Error scheduling nurturing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validation/check", response_model=Dict[str, Any])
async def validate_draft(
    request: ValidationRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Validate draft for compliance and quality."""
    try:
        agent = ValidationAgent()
        result = await agent.execute(request.dict())
        logger.info(f"Draft validation completed: {request.draft_id}")
        return result
    except Exception as e:
        logger.error(f"Error validating draft: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/demo/run", response_model=Dict[str, Any])
async def run_demo(request: DemoRequest) -> Dict[str, Any]:
    """Run demo scenario."""
    try:
        agent = DemoAgent()
        result = await agent.execute(request.dict())
        logger.info(f"Demo executed: {request.demo_type}")
        return result
    except Exception as e:
        logger.error(f"Error running demo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reporting/generate", response_model=Dict[str, Any])
async def generate_report(request: ReportRequest) -> Dict[str, Any]:
    """Generate engagement report."""
    try:
        agent = OutcomeReporterAgent()
        result = await agent.execute(request.dict())
        logger.info(f"Report generated: {request.report_type}")
        return result
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/prospecting", response_model=Dict[str, Any])
async def demo_prospecting() -> Dict[str, Any]:
    """Run prospecting demo."""
    try:
        agent = DemoAgent()
        result = await agent.execute({"demo_type": "prospecting", "company_domain": "techcorp.com"})
        return result
    except Exception as e:
        logger.error(f"Error running prospecting demo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/validation", response_model=Dict[str, Any])
async def demo_validation() -> Dict[str, Any]:
    """Run validation demo."""
    try:
        agent = DemoAgent()
        result = await agent.execute({"demo_type": "validation", "company_domain": "example.com"})
        return result
    except Exception as e:
        logger.error(f"Error running validation demo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/nurturing", response_model=Dict[str, Any])
async def demo_nurturing() -> Dict[str, Any]:
    """Run nurturing demo."""
    try:
        agent = DemoAgent()
        result = await agent.execute({"demo_type": "nurturing", "company_domain": "growth-co.com"})
        return result
    except Exception as e:
        logger.error(f"Error running nurturing demo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ChatRequest(BaseModel):
    """Request model for agent chat."""
    agent_id: str
    message: str
    context: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    """Response model for agent chat."""
    response: str
    agent_id: str
    sources: List[str] = []


# Agent context for chat
AGENT_SYSTEM_PROMPTS = {
    "orchestrator": """You are the Orchestrator Agent for a sales automation system.
You coordinate the entire workflow from form submission to draft creation.
The workflow steps are: 1) Validate payload, 2) Resolve HubSpot contact, 3) Research prospect, 
4) Search Gmail threads, 5) Read thread context, 6) Find patterns, 7) Hunt assets, 
8) Propose meeting slots, 9) Plan next step, 10) Write draft, 11) Create Gmail draft.
Answer questions about the workflow, current status, and how components work together.""",

    "research": """You are the Research Agent for a sales automation system.
You research prospects and companies before emails are drafted.
You gather context from HubSpot data, Gmail history, and company information.
You generate talking points and personalization hooks for more effective outreach.
Answer questions about prospect research, company intelligence, and personalization strategies.""",

    "thread_reader": """You are the Thread Reader Agent for a sales automation system.
You analyze existing email threads to understand conversation context.
You extract key points, open questions, commitments, and the relationship state.
This helps avoid repetitive messages and keeps conversations coherent.
Answer questions about email thread analysis and conversation context.""",

    "draft_writer": """You are the Draft Writer Agent for a sales automation system.
You generate personalized email drafts using voice profiles and research context.
You ensure emails match the user's tone, include relevant meeting slots, and have a single CTA.
All drafts go to the operator queue for human review before sending.
Answer questions about draft generation, voice profiles, and email best practices.""",

    "asset_hunter": """You are the Asset Hunter Agent for a sales automation system.
You search Google Drive for relevant case studies, proposals, and materials.
You only search approved folders to ensure compliance.
You match assets to the prospect's industry and needs.
Answer questions about asset discovery and content matching.""",

    "meeting_slot": """You are the Meeting Planner Agent for a sales automation system.
You check calendar availability and propose 2-3 meeting slots.
You look at the next 1-3 business days for quick turnaround.
Slots are formatted for easy copy-paste into emails.
Answer questions about meeting scheduling and availability.""",
}


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest) -> ChatResponse:
    """Chat with an agent to ask questions about its role and current state."""
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            # Fallback response without OpenAI
            return ChatResponse(
                response=_get_fallback_response(request.agent_id, request.message),
                agent_id=request.agent_id,
                sources=["fallback"],
            )
        
        client = AsyncOpenAI(api_key=api_key)
        
        # Get system prompt for agent
        system_prompt = AGENT_SYSTEM_PROMPTS.get(
            request.agent_id,
            "You are a helpful assistant for a sales automation system."
        )
        
        # Add recent workflow context
        try:
            from src.db.workflow_db import get_workflow_db
            db = await get_workflow_db()
            recent = await db.get_recent_workflows(limit=5)
            if recent:
                workflow_context = "\n\nRecent workflow activity:\n"
                for wf in recent:
                    workflow_context += f"- {wf.get('contact_email', 'Unknown')}: {wf.get('status', 'unknown')}\n"
                system_prompt += workflow_context
        except:
            pass
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context from previous messages
        if request.context:
            for msg in request.context[-5:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # Add current message
        messages.append({"role": "user", "content": request.message})
        
        # Get response
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=300,
        )
        
        return ChatResponse(
            response=response.choices[0].message.content,
            agent_id=request.agent_id,
            sources=["openai"],
        )
        
    except Exception as e:
        logger.error(f"Error in agent chat: {e}")
        return ChatResponse(
            response=_get_fallback_response(request.agent_id, request.message),
            agent_id=request.agent_id,
            sources=["fallback"],
        )


def _get_fallback_response(agent_id: str, message: str) -> str:
    """Get a contextual fallback response."""
    responses = {
        "orchestrator": "I coordinate the workflow from form submission to draft creation. Each step is tracked and logged for visibility.",
        "research": "I research prospects using HubSpot data and Gmail history to find personalization opportunities.",
        "thread_reader": "I analyze email threads to understand the conversation context and relationship state.",
        "draft_writer": "I generate personalized drafts using voice profiles. All drafts require human approval.",
        "asset_hunter": "I search approved Drive folders for relevant case studies and proposals.",
        "meeting_slot": "I check calendar availability and propose 2-3 meeting times in the next few days.",
    }
    return responses.get(agent_id, "I'm here to help with the sales automation workflow.")


@router.get("/status", response_model=Dict[str, Any])
async def get_agents_status() -> Dict[str, Any]:
    """Get status of all agents."""
    try:
        from src.db.workflow_db import get_workflow_db
        db = await get_workflow_db()
        stats = await db.get_workflow_stats()
        
        return {
            "agents": [
                {"id": "orchestrator", "name": "Orchestrator", "status": "active"},
                {"id": "research", "name": "Research Agent", "status": "active"},
                {"id": "thread_reader", "name": "Thread Reader", "status": "active"},
                {"id": "draft_writer", "name": "Draft Writer", "status": "active"},
                {"id": "asset_hunter", "name": "Asset Hunter", "status": "active"},
                {"id": "meeting_slot", "name": "Meeting Planner", "status": "active"},
            ],
            "workflow_stats": stats,
        }
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        return {"agents": [], "error": str(e)}
