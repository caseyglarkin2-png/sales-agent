"""LLM API routes for testing and managing AI providers.

Endpoints:
- GET /api/llm/health - Check LLM provider health
- GET /api/llm/providers - List available providers
- POST /api/llm/generate - Generate text (for testing)
- POST /api/llm/research - Deep research with Gemini
"""
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException

from src.config import get_settings
from src.connectors.llm import get_llm, LLMConnector
from src.connectors.gemini import get_gemini, GeminiModel
from src.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/llm", tags=["LLM"])


# Request/Response models
class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Prompt to generate from")
    provider: Optional[str] = Field(None, description="Provider: openai or gemini")
    model: Optional[str] = Field(None, description="Model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(500, ge=1, le=8192)
    enable_grounding: bool = Field(False, description="Enable Google Search grounding (Gemini only)")


class GenerateResponse(BaseModel):
    text: str
    provider: str
    model: str
    tokens_used: Optional[int] = None


class ResearchRequest(BaseModel):
    topic: str = Field(..., description="Research topic")
    max_steps: int = Field(5, ge=1, le=10)


class ResearchResponse(BaseModel):
    summary: str
    findings: list
    sources: list
    confidence: float


class EmailDraftRequest(BaseModel):
    recipient_name: str
    recipient_company: str
    recipient_role: Optional[str] = None
    purpose: str
    thread_context: Optional[str] = None
    voice_style: Optional[str] = None


@router.get("/health")
async def llm_health():
    """
    Check LLM provider health.
    
    Returns status of configured LLM providers.
    """
    results = {
        "primary_provider": settings.llm_provider,
        "openai": {"configured": bool(settings.openai_api_key)},
        "gemini": {"configured": bool(settings.gemini_api_key)},
    }
    
    # Test OpenAI if configured
    if settings.openai_api_key:
        try:
            llm = LLMConnector(provider="openai")
            response = await llm.generate_text("Reply with 'ok'", max_tokens=10)
            results["openai"]["status"] = "healthy" if response else "degraded"
        except Exception as e:
            results["openai"]["status"] = "error"
            results["openai"]["error"] = str(e)
    
    # Test Gemini if configured
    if settings.gemini_api_key:
        try:
            gemini = get_gemini()
            health = await gemini.health_check()
            results["gemini"]["status"] = health.get("status", "unknown")
            if "error" in health:
                results["gemini"]["error"] = health["error"]
        except Exception as e:
            results["gemini"]["status"] = "error"
            results["gemini"]["error"] = str(e)
    
    return results


@router.get("/providers")
async def list_providers():
    """
    List available LLM providers and models.
    """
    providers = []
    
    if settings.openai_api_key:
        providers.append({
            "name": "openai",
            "models": [
                {"id": "gpt-4-turbo-preview", "description": "GPT-4 Turbo (default)"},
                {"id": "gpt-4", "description": "GPT-4 base"},
                {"id": "gpt-3.5-turbo", "description": "GPT-3.5 Turbo (fast)"},
            ],
            "features": ["text_generation", "embeddings", "function_calling"],
        })
    
    if settings.gemini_api_key:
        providers.append({
            "name": "gemini",
            "models": [
                {"id": "gemini-2.0-flash-exp", "description": "Gemini 2.0 Flash (default, fast)"},
                {"id": "gemini-1.5-pro", "description": "Gemini 1.5 Pro (1M context)"},
                {"id": "gemini-1.5-flash", "description": "Gemini 1.5 Flash"},
                {"id": "gemini-1.5-flash-8b", "description": "Gemini 1.5 Flash 8B (efficient)"},
                {"id": "gemini-exp-1206", "description": "Experimental (enhanced reasoning)"},
            ],
            "features": [
                "text_generation",
                "grounding",  # Google Search grounding
                "deep_research",
                "multimodal",
                "long_context",
            ],
        })
    
    return {
        "primary_provider": settings.llm_provider,
        "providers": providers,
    }


@router.post("/generate", response_model=GenerateResponse)
async def generate_text(request: GenerateRequest):
    """
    Generate text using LLM.
    
    Useful for testing different providers and models.
    """
    provider = request.provider or settings.llm_provider
    
    if provider == "gemini":
        if not settings.gemini_api_key:
            raise HTTPException(status_code=400, detail="Gemini API key not configured")
        
        gemini = get_gemini()
        response = await gemini.generate(
            prompt=request.prompt,
            model=GeminiModel(request.model) if request.model else None,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            enable_grounding=request.enable_grounding,
        )
        
        return GenerateResponse(
            text=response.text,
            provider="gemini",
            model=response.model,
            tokens_used=response.usage.get("total_tokens"),
        )
    else:
        if not settings.openai_api_key:
            raise HTTPException(status_code=400, detail="OpenAI API key not configured")
        
        llm = LLMConnector(provider="openai")
        text = await llm.generate_text(
            prompt=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        if not text:
            raise HTTPException(status_code=500, detail="Failed to generate text")
        
        return GenerateResponse(
            text=text,
            provider="openai",
            model=request.model or settings.openai_model,
        )


@router.post("/research", response_model=ResearchResponse)
async def deep_research(request: ResearchRequest):
    """
    Perform deep research on a topic using Gemini with Google Search grounding.
    
    Features:
    - Multi-step research
    - Citation of sources
    - Confidence scoring
    
    Requires Gemini API key.
    """
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=400,
            detail="Deep research requires Gemini API key (GEMINI_API_KEY)",
        )
    
    gemini = get_gemini()
    
    try:
        result = await gemini.deep_research(
            topic=request.topic,
            max_steps=request.max_steps,
        )
        
        return ResearchResponse(
            summary=result.summary,
            findings=result.findings,
            sources=result.sources,
            confidence=result.confidence,
        )
    except Exception as e:
        logger.error(f"Research failed: {e}")
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@router.post("/draft-email")
async def draft_email(request: EmailDraftRequest):
    """
    Draft a personalized email using Gemini.
    
    Uses context about recipient to create personalized outreach.
    """
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=400,
            detail="Email drafting with Gemini requires GEMINI_API_KEY",
        )
    
    gemini = get_gemini()
    
    recipient_context = {
        "name": request.recipient_name,
        "company": request.recipient_company,
    }
    if request.recipient_role:
        recipient_context["role"] = request.recipient_role
    
    try:
        draft = await gemini.draft_email(
            recipient_context=recipient_context,
            purpose=request.purpose,
            thread_context=request.thread_context,
            voice_style=request.voice_style,
        )
        
        return {
            "draft": draft,
            "recipient": request.recipient_name,
            "company": request.recipient_company,
            "model": "gemini-2.0-flash-exp",
        }
    except Exception as e:
        logger.error(f"Email drafting failed: {e}")
        raise HTTPException(status_code=500, detail=f"Drafting failed: {str(e)}")


@router.post("/analyze-company")
async def analyze_company(company_name: str, domain: Optional[str] = None):
    """
    Research and analyze a company for sales context.
    
    Uses Gemini with Google Search grounding for current information.
    """
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=400,
            detail="Company analysis requires GEMINI_API_KEY",
        )
    
    gemini = get_gemini()
    
    try:
        analysis = await gemini.analyze_company(
            company_name=company_name,
            domain=domain,
        )
        
        return {
            "company": company_name,
            "analysis": analysis,
            "model": "gemini-2.0-flash-exp",
        }
    except Exception as e:
        logger.error(f"Company analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
