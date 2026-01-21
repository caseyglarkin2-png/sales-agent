"""
Account Analyzer API Routes.

Endpoints for analyzing accounts and finding decision makers.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AnalyzeCompanyRequest(BaseModel):
    company_name: str
    contact_title: Optional[str] = None
    company_data: Optional[Dict[str, Any]] = None


class FindDecisionMakersRequest(BaseModel):
    company_name: str


@router.post("/analyze")
async def analyze_company(request: AnalyzeCompanyRequest) -> Dict[str, Any]:
    """Analyze a company for targeting."""
    try:
        from src.agents.account_analyzer import get_account_analyzer
        
        # Get HubSpot connector if available
        hubspot = None
        try:
            from src.connectors.hubspot import get_hubspot_connector
            hubspot = get_hubspot_connector()
        except Exception:
            pass
        
        analyzer = get_account_analyzer(hubspot_connector=hubspot)
        
        analysis = await analyzer.analyze_company(
            company_name=request.company_name,
            company_data=request.company_data,
            contact_title=request.contact_title,
        )
        
        return {
            "status": "success",
            "analysis": analysis.to_dict(),
        }
        
    except Exception as e:
        logger.error(f"Error analyzing company: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decision-makers")
async def find_decision_makers(request: FindDecisionMakersRequest) -> Dict[str, Any]:
    """Find decision makers at a company."""
    try:
        from src.agents.account_analyzer import get_account_analyzer
        
        hubspot = None
        try:
            from src.connectors.hubspot import get_hubspot_connector
            hubspot = get_hubspot_connector()
        except Exception:
            pass
        
        analyzer = get_account_analyzer(hubspot_connector=hubspot)
        
        decision_makers = await analyzer.find_decision_makers(
            company_name=request.company_name,
        )
        
        return {
            "status": "success",
            "company": request.company_name,
            "decision_makers": decision_makers,
            "total": len(decision_makers),
        }
        
    except Exception as e:
        logger.error(f"Error finding decision makers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pain-points/{industry}")
async def get_industry_pain_points(industry: str) -> Dict[str, Any]:
    """Get common pain points for an industry."""
    from src.agents.account_analyzer import INDUSTRY_PAIN_POINTS
    
    industry_lower = industry.lower()
    
    # Try to match industry
    pain_points = INDUSTRY_PAIN_POINTS.get(industry_lower)
    
    if not pain_points:
        # Try partial match
        for key, points in INDUSTRY_PAIN_POINTS.items():
            if key in industry_lower or industry_lower in key:
                pain_points = points
                break
    
    if not pain_points:
        pain_points = INDUSTRY_PAIN_POINTS["default"]
    
    return {
        "industry": industry,
        "pain_points": pain_points,
    }


@router.get("/value-props/{persona}")
async def get_persona_value_props(persona: str) -> Dict[str, Any]:
    """Get value propositions for a persona."""
    from src.agents.account_analyzer import PERSONA_VALUE_PROPS
    
    persona_lower = persona.lower()
    
    value_props = PERSONA_VALUE_PROPS.get(persona_lower)
    
    if not value_props:
        value_props = PERSONA_VALUE_PROPS.get("demand_gen", [])
    
    return {
        "persona": persona,
        "value_propositions": value_props,
    }
