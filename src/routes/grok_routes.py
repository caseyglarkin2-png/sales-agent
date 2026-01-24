"""Grok AI API routes for CaseyOS market intelligence.

Endpoints:
- GET /api/grok/health - Check Grok connector health
- POST /api/grok/market-intel - Get market intelligence on a topic
- POST /api/grok/competitive - Get competitive analysis
- POST /api/grok/summarize-signals - Summarize social signals
- POST /api/grok/generate - Generate text with Grok
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.config import get_settings
from src.connectors.grok import get_grok
from src.agents.market_trend_monitor import MarketTrendMonitorAgent
from src.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/grok", tags=["Grok AI"])


# ==================== REQUEST MODELS ====================

class MarketIntelRequest(BaseModel):
    """Request for market intelligence analysis."""
    topic: str = Field(..., description="Topic to analyze (e.g. 'B2B sales automation')")
    industry: str = Field(default="SaaS", description="Industry context")


class CompetitiveRequest(BaseModel):
    """Request for competitive analysis."""
    company: str = Field(..., description="Company to analyze")
    competitors: List[str] = Field(default=[], description="Competitor companies")
    industry: Optional[str] = Field(None, description="Industry context")


class SummarizeSignalsRequest(BaseModel):
    """Request to summarize social signals."""
    signals: List[Dict[str, Any]] = Field(..., description="List of social signals")
    focus_topics: List[str] = Field(default=["sales", "GTM"], description="Topics to focus on")


class GenerateRequest(BaseModel):
    """Request for text generation."""
    prompt: str = Field(..., description="Prompt for Grok")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=8192)
    system_prompt: Optional[str] = Field(None, description="Custom system prompt")


# ==================== ENDPOINTS ====================

@router.get("/health")
async def grok_health() -> Dict[str, Any]:
    """
    Check Grok connector health and configuration.
    
    Returns:
        Configuration status and connectivity info.
    """
    grok = get_grok()
    
    return {
        "configured": grok.is_configured,
        "api_key_set": bool(settings.xai_api_key),
        "model": grok.model if grok.is_configured else None,
        "base_url": grok.base_url if grok.is_configured else None,
        "status": "ready" if grok.is_configured else "not_configured",
    }


@router.post("/market-intel")
async def get_market_intel(request: MarketIntelRequest) -> Dict[str, Any]:
    """
    Get real-time market intelligence on a topic using Grok AI.
    
    Grok has access to real-time X data and current events.
    
    Args:
        request: Topic and industry for analysis
        
    Returns:
        Market intel including trends, opportunities, and risks.
    """
    grok = get_grok()
    
    if not grok.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Grok not configured. Set XAI_API_KEY environment variable."
        )
    
    try:
        # Use the agent for structured analysis
        agent = MarketTrendMonitorAgent()
        result = await agent.execute({
            "action": "grok_market_intel",
            "topic": request.topic,
            "industry": request.industry,
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Grok market intel failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/competitive")
async def get_competitive_analysis(request: CompetitiveRequest) -> Dict[str, Any]:
    """
    Get competitive analysis using Grok AI.
    
    Analyzes a company against its competitors with real-time data.
    
    Args:
        request: Company and competitors to analyze
        
    Returns:
        Competitive analysis with strengths, weaknesses, opportunities.
    """
    grok = get_grok()
    
    if not grok.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Grok not configured. Set XAI_API_KEY environment variable."
        )
    
    try:
        # Use the agent for structured analysis
        agent = MarketTrendMonitorAgent()
        result = await agent.execute({
            "action": "grok_competitive_analysis",
            "company": request.company,
            "competitors": request.competitors,
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Grok competitive analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize-signals")
async def summarize_signals(request: SummarizeSignalsRequest) -> Dict[str, Any]:
    """
    Summarize social signals using Grok AI.
    
    Takes a list of social signals (tweets, mentions) and generates
    actionable insights.
    
    Args:
        request: Signals and focus topics
        
    Returns:
        Summary with key themes and recommended actions.
    """
    grok = get_grok()
    
    if not grok.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Grok not configured. Set XAI_API_KEY environment variable."
        )
    
    try:
        # Use the agent for structured analysis
        agent = MarketTrendMonitorAgent()
        result = await agent.execute({
            "action": "grok_summarize_signals",
            "signals": request.signals,
            "focus_topics": request.focus_topics,
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Grok signal summarization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_text(request: GenerateRequest) -> Dict[str, Any]:
    """
    Generate text using Grok AI.
    
    Direct access to Grok's text generation capabilities.
    
    Args:
        request: Prompt and generation parameters
        
    Returns:
        Generated text and metadata.
    """
    grok = get_grok()
    
    if not grok.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Grok not configured. Set XAI_API_KEY environment variable."
        )
    
    try:
        result = await grok.generate(
            prompt=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            system_prompt=request.system_prompt,
        )
        
        return {
            "text": result,
            "model": grok.model,
            "prompt_length": len(request.prompt),
        }
        
    except Exception as e:
        logger.error(f"Grok generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models() -> Dict[str, Any]:
    """
    List available Grok models.
    
    Returns:
        Available models and their capabilities.
    """
    return {
        "models": [
            {
                "id": "grok-2",
                "name": "Grok 2",
                "description": "Latest Grok model with real-time knowledge",
                "capabilities": ["text", "reasoning", "real-time-data"],
            },
            {
                "id": "grok-2-mini",
                "name": "Grok 2 Mini",
                "description": "Faster, smaller Grok model",
                "capabilities": ["text", "reasoning"],
            },
        ],
        "default": "grok-2",
    }
