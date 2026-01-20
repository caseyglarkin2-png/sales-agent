"""API routes for agent operations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.demo import DemoAgent
from src.agents.nurturing import NurturingAgent
from src.agents.outcome_reporter import OutcomeReporterAgent
from src.agents.prospecting import ProspectingAgent
from src.agents.validation import ValidationAgent
from src.connectors.hubspot import HubSpotConnector
from src.connectors.llm import LLMConnector
from src.config import get_settings
from src.deps import get_db_session
from src.logger import get_logger
from pydantic import BaseModel
from typing import Any, Dict

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
