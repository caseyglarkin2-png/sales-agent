"""API routes for personalization engine."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.personalization import (
    get_personalization_engine,
    PersonalizationContext,
    InsightCategory,
)

router = APIRouter(prefix="/api/personalization", tags=["personalization"])


class GeneratePersonalizationRequest(BaseModel):
    contact_id: str
    contact_name: str
    contact_email: str
    contact_title: str = ""
    company_id: Optional[str] = None
    company_name: str = ""
    company_domain: str = ""
    company_industry: str = ""
    company_size: str = ""
    persona: str = ""
    campaign_type: str = "cold_outreach"
    product_offering: str = ""
    value_prop: str = ""
    prior_engagement: list[dict] = []
    max_insights: int = 5
    force_refresh: bool = False


class BatchPersonalizationRequest(BaseModel):
    contacts: list[dict]
    max_insights: int = 3


@router.post("/generate")
async def generate_personalization(request: GeneratePersonalizationRequest):
    """Generate personalization for a single contact."""
    engine = get_personalization_engine()
    
    context = PersonalizationContext(
        contact_id=request.contact_id,
        contact_name=request.contact_name,
        contact_email=request.contact_email,
        contact_title=request.contact_title,
        company_id=request.company_id,
        company_name=request.company_name,
        company_domain=request.company_domain,
        company_industry=request.company_industry,
        company_size=request.company_size,
        persona=request.persona,
        campaign_type=request.campaign_type,
        product_offering=request.product_offering,
        value_prop=request.value_prop,
        prior_engagement=request.prior_engagement,
    )
    
    result = await engine.generate_personalization(
        context=context,
        max_insights=request.max_insights,
        force_refresh=request.force_refresh,
    )
    
    return result.to_dict()


@router.post("/batch")
async def batch_personalization(request: BatchPersonalizationRequest):
    """Generate personalization for multiple contacts."""
    engine = get_personalization_engine()
    
    results = []
    for contact in request.contacts:
        try:
            context = PersonalizationContext(
                contact_id=contact.get("contact_id", ""),
                contact_name=contact.get("contact_name", ""),
                contact_email=contact.get("contact_email", ""),
                contact_title=contact.get("contact_title", ""),
                company_id=contact.get("company_id"),
                company_name=contact.get("company_name", ""),
                company_domain=contact.get("company_domain", ""),
                company_industry=contact.get("company_industry", ""),
                company_size=contact.get("company_size", ""),
                persona=contact.get("persona", ""),
                campaign_type=contact.get("campaign_type", "cold_outreach"),
            )
            
            result = await engine.generate_personalization(
                context=context,
                max_insights=request.max_insights,
            )
            results.append(result.to_dict())
        except Exception as e:
            results.append({
                "contact_id": contact.get("contact_id"),
                "error": str(e),
            })
    
    return {
        "results": results,
        "total": len(results),
        "successful": len([r for r in results if "error" not in r]),
    }


@router.get("/insights/categories")
async def list_insight_categories():
    """List all insight categories."""
    return {
        "categories": [
            {
                "category": cat.value,
                "name": cat.name.replace("_", " ").title(),
            }
            for cat in InsightCategory
        ]
    }


@router.delete("/cache")
async def clear_cache(contact_id: Optional[str] = None):
    """Clear personalization cache."""
    engine = get_personalization_engine()
    count = engine.clear_cache(contact_id)
    
    return {
        "message": f"Cleared {count} cached personalization(s)",
        "contact_id": contact_id,
    }


@router.get("/preview/{contact_id}")
async def preview_personalization(
    contact_id: str,
    contact_name: str = "John Doe",
    company_name: str = "Acme Corp",
    industry: str = "technology",
    title: str = "VP Sales",
):
    """Quick preview of personalization for a contact."""
    engine = get_personalization_engine()
    
    context = PersonalizationContext(
        contact_id=contact_id,
        contact_name=contact_name,
        contact_email=f"{contact_name.lower().replace(' ', '.')}@{company_name.lower().replace(' ', '')}.com",
        contact_title=title,
        company_name=company_name,
        company_industry=industry,
    )
    
    result = await engine.generate_personalization(context, max_insights=3)
    
    return {
        "contact_id": contact_id,
        "personalization_score": result.personalization_score,
        "best_opener": result.personalized_openers[0] if result.personalized_openers else None,
        "best_hook": result.personalized_hooks[0] if result.personalized_hooks else None,
        "best_cta": result.personalized_ctas[0] if result.personalized_ctas else None,
        "top_pain_point": result.pain_points[0] if result.pain_points else None,
        "insights_count": len(result.insights),
    }
