"""
Account Analyzer Agent.

Analyzes companies to determine:
- Viability as a target
- Key pain points
- Decision makers
- Matched value propositions
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class CompanySize(Enum):
    STARTUP = "startup"  # < 50 employees
    SMB = "smb"  # 50-200
    MID_MARKET = "mid_market"  # 200-1000
    ENTERPRISE = "enterprise"  # 1000+
    UNKNOWN = "unknown"


@dataclass
class CompanyAnalysis:
    """Analysis of a target company."""
    company_name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    size: CompanySize = CompanySize.UNKNOWN
    employee_count: Optional[int] = None
    viability_score: float = 0.0
    viability_reasons: List[str] = None
    pain_points: List[Dict[str, str]] = None
    value_propositions: List[Dict[str, str]] = None
    recommended_approach: Optional[str] = None
    
    def __post_init__(self):
        if self.viability_reasons is None:
            self.viability_reasons = []
        if self.pain_points is None:
            self.pain_points = []
        if self.value_propositions is None:
            self.value_propositions = []
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["size"] = self.size.value
        return data


# Industry-specific pain points
INDUSTRY_PAIN_POINTS = {
    "technology": [
        {"pain": "Scaling pipeline to match product growth", "solution": "Demand gen orchestration"},
        {"pain": "Event ROI measurement", "solution": "Field marketing analytics"},
        {"pain": "Sales and marketing alignment", "solution": "Unified GTM platform"},
    ],
    "saas": [
        {"pain": "Converting trial users to paid", "solution": "Lifecycle marketing"},
        {"pain": "Expanding into new markets", "solution": "Regional field marketing"},
        {"pain": "Reducing CAC while scaling", "solution": "Efficient demand gen"},
    ],
    "manufacturing": [
        {"pain": "Trade show lead follow-up", "solution": "Event-to-pipeline automation"},
        {"pain": "Long sales cycles", "solution": "Nurture campaigns"},
        {"pain": "Dealer/partner enablement", "solution": "Channel marketing"},
    ],
    "financial_services": [
        {"pain": "Compliance in marketing", "solution": "Compliant campaign templates"},
        {"pain": "Client acquisition costs", "solution": "Targeted demand gen"},
        {"pain": "Relationship-based selling", "solution": "ABM programs"},
    ],
    "healthcare": [
        {"pain": "Reaching decision makers", "solution": "Executive targeting"},
        {"pain": "Long procurement cycles", "solution": "Multi-touch nurturing"},
        {"pain": "Regulatory considerations", "solution": "Compliant messaging"},
    ],
    "default": [
        {"pain": "Generating qualified pipeline", "solution": "Demand generation programs"},
        {"pain": "Event marketing effectiveness", "solution": "Field marketing optimization"},
        {"pain": "Marketing-sales alignment", "solution": "Unified GTM approach"},
    ],
}

# Persona-specific value propositions
PERSONA_VALUE_PROPS = {
    "events": [
        {"prop": "Run 3x more events with same team", "proof": "AI handles logistics and follow-up"},
        {"prop": "Convert event leads faster", "proof": "Automated post-event sequences"},
        {"prop": "Prove event ROI definitively", "proof": "End-to-end attribution tracking"},
    ],
    "demand_gen": [
        {"prop": "Accelerate pipeline velocity", "proof": "AI-powered lead scoring and routing"},
        {"prop": "Scale personalization", "proof": "Dynamic content at scale"},
        {"prop": "Improve lead quality scores", "proof": "Enrichment + intent data"},
    ],
    "sales": [
        {"prop": "Get better leads from marketing", "proof": "Aligned qualification criteria"},
        {"prop": "Focus on ready-to-buy accounts", "proof": "Intent-based prioritization"},
        {"prop": "Shorter sales cycles", "proof": "Warmed leads with context"},
    ],
    "executive": [
        {"prop": "10x GTM efficiency", "proof": "AI agents handle execution"},
        {"prop": "Predictable pipeline growth", "proof": "Data-driven forecasting"},
        {"prop": "Competitive advantage", "proof": "Early AI adoption edge"},
    ],
}


class AccountAnalyzer:
    """Analyzes accounts for targeting and messaging."""
    
    def __init__(self, hubspot_connector=None, openai_client=None):
        self.hubspot = hubspot_connector
        self.openai = openai_client
    
    async def analyze_company(
        self,
        company_name: str,
        company_data: Optional[Dict[str, Any]] = None,
        contact_title: Optional[str] = None,
    ) -> CompanyAnalysis:
        """Perform full company analysis.
        
        Args:
            company_name: Company name
            company_data: Optional pre-fetched company data
            contact_title: Optional contact job title for persona matching
            
        Returns:
            CompanyAnalysis with viability, pain points, and value props
        """
        analysis = CompanyAnalysis(company_name=company_name)
        
        # Get company data if not provided
        if not company_data and self.hubspot:
            company_data = await self._fetch_company_data(company_name)
        
        if company_data:
            analysis.website = company_data.get("website")
            analysis.industry = company_data.get("industry")
            analysis.employee_count = company_data.get("numberofemployees")
            analysis.size = self._determine_size(analysis.employee_count)
        
        # Calculate viability
        analysis.viability_score, analysis.viability_reasons = self._calculate_viability(
            company_data or {}, contact_title
        )
        
        # Get pain points based on industry
        analysis.pain_points = self._get_pain_points(analysis.industry)
        
        # Get value propositions based on contact persona
        if contact_title:
            analysis.value_propositions = self._get_value_props(contact_title)
        
        # Generate recommended approach
        analysis.recommended_approach = self._generate_approach(analysis, contact_title)
        
        return analysis
    
    async def _fetch_company_data(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Fetch company data from HubSpot."""
        try:
            companies = await self.hubspot.search_companies(company_name)
            if companies:
                return companies[0]
        except Exception as e:
            logger.warning(f"Could not fetch company data: {e}")
        return None
    
    def _determine_size(self, employee_count: Optional[int]) -> CompanySize:
        """Determine company size category."""
        if not employee_count:
            return CompanySize.UNKNOWN
        
        if employee_count < 50:
            return CompanySize.STARTUP
        elif employee_count < 200:
            return CompanySize.SMB
        elif employee_count < 1000:
            return CompanySize.MID_MARKET
        else:
            return CompanySize.ENTERPRISE
    
    def _calculate_viability(
        self,
        company_data: Dict[str, Any],
        contact_title: Optional[str],
    ) -> tuple[float, List[str]]:
        """Calculate viability score and reasons."""
        score = 50.0  # Base score
        reasons = []
        
        # Company size scoring
        employee_count = company_data.get("numberofemployees")
        if employee_count:
            if employee_count >= 100:
                score += 20
                reasons.append(f"Good company size ({employee_count} employees)")
            elif employee_count >= 50:
                score += 10
                reasons.append(f"Decent company size ({employee_count} employees)")
            elif employee_count < 20:
                score -= 10
                reasons.append("Small company - may have limited budget")
        
        # Industry scoring
        industry = company_data.get("industry", "").lower()
        high_value_industries = ["technology", "saas", "software", "financial"]
        if any(ind in industry for ind in high_value_industries):
            score += 15
            reasons.append(f"High-value industry: {industry}")
        
        # Contact title scoring
        if contact_title:
            title_lower = contact_title.lower()
            if any(t in title_lower for t in ["vp", "director", "head of", "chief", "cmo", "cro"]):
                score += 20
                reasons.append(f"Decision maker title: {contact_title}")
            elif "manager" in title_lower:
                score += 10
                reasons.append("Manager-level contact")
            
            # Function match scoring
            if any(f in title_lower for f in ["demand", "field", "event", "growth"]):
                score += 15
                reasons.append("Target function match")
        
        # Website presence
        if company_data.get("website"):
            score += 5
            reasons.append("Has website presence")
        
        # HubSpot engagement
        if company_data.get("hs_analytics_num_page_views"):
            score += 10
            reasons.append("Has website engagement")
        
        # Cap score at 100
        score = min(100.0, max(0.0, score))
        
        return score, reasons
    
    def _get_pain_points(self, industry: Optional[str]) -> List[Dict[str, str]]:
        """Get relevant pain points based on industry."""
        if not industry:
            return INDUSTRY_PAIN_POINTS["default"]
        
        industry_lower = industry.lower()
        
        # Match to known industries
        for key, points in INDUSTRY_PAIN_POINTS.items():
            if key in industry_lower:
                return points
        
        # Check for common patterns
        if any(t in industry_lower for t in ["tech", "software", "saas"]):
            return INDUSTRY_PAIN_POINTS["technology"]
        
        if any(t in industry_lower for t in ["bank", "financ", "insurance"]):
            return INDUSTRY_PAIN_POINTS["financial_services"]
        
        return INDUSTRY_PAIN_POINTS["default"]
    
    def _get_value_props(self, contact_title: str) -> List[Dict[str, str]]:
        """Get value propositions based on contact persona."""
        title_lower = contact_title.lower()
        
        if any(t in title_lower for t in ["event", "field"]):
            return PERSONA_VALUE_PROPS["events"]
        
        if any(t in title_lower for t in ["demand", "growth", "acquisition"]):
            return PERSONA_VALUE_PROPS["demand_gen"]
        
        if any(t in title_lower for t in ["sales", "revenue", "business development"]):
            return PERSONA_VALUE_PROPS["sales"]
        
        if any(t in title_lower for t in ["chief", "cmo", "cro", "vp", "president"]):
            return PERSONA_VALUE_PROPS["executive"]
        
        return PERSONA_VALUE_PROPS["demand_gen"]  # Default
    
    def _generate_approach(
        self,
        analysis: CompanyAnalysis,
        contact_title: Optional[str],
    ) -> str:
        """Generate recommended approach based on analysis."""
        approaches = []
        
        # Size-based approach
        if analysis.size == CompanySize.ENTERPRISE:
            approaches.append("Enterprise approach: Focus on ROI and scale")
        elif analysis.size == CompanySize.MID_MARKET:
            approaches.append("Mid-market approach: Emphasize efficiency gains")
        elif analysis.size == CompanySize.SMB:
            approaches.append("SMB approach: Quick wins and ease of use")
        
        # Persona-based approach
        if contact_title:
            title_lower = contact_title.lower()
            if "event" in title_lower:
                approaches.append("Lead with event marketing success stories")
            elif "demand" in title_lower:
                approaches.append("Lead with pipeline acceleration metrics")
            elif "sales" in title_lower:
                approaches.append("Lead with marketing-sales alignment story")
            elif any(t in title_lower for t in ["chief", "cmo", "cro"]):
                approaches.append("Lead with strategic GTM transformation")
        
        # Viability-based approach
        if analysis.viability_score >= 80:
            approaches.append("High priority - personalized outreach recommended")
        elif analysis.viability_score >= 60:
            approaches.append("Good fit - standard sequence appropriate")
        else:
            approaches.append("Lower priority - nurture sequence")
        
        return " | ".join(approaches) if approaches else "Standard outreach approach"
    
    async def find_decision_makers(
        self,
        company_name: str,
    ) -> List[Dict[str, Any]]:
        """Find decision makers at a company.
        
        Args:
            company_name: Company to search
            
        Returns:
            List of contacts ranked by decision-making potential
        """
        decision_makers = []
        
        if not self.hubspot:
            return decision_makers
        
        try:
            # Search for contacts at this company
            contacts = await self.hubspot.search_contacts_by_company(company_name)
            
            # Score each contact
            for contact in contacts:
                score = self._score_decision_maker(contact)
                decision_makers.append({
                    "email": contact.get("email"),
                    "name": f"{contact.get('firstname', '')} {contact.get('lastname', '')}".strip(),
                    "title": contact.get("jobtitle", ""),
                    "score": score,
                    "company": company_name,
                })
            
            # Sort by score
            decision_makers.sort(key=lambda x: -x["score"])
            
        except Exception as e:
            logger.error(f"Error finding decision makers: {e}")
        
        return decision_makers[:10]  # Top 10
    
    def _score_decision_maker(self, contact: Dict[str, Any]) -> float:
        """Score a contact's decision-making potential."""
        score = 0.0
        title = (contact.get("jobtitle") or "").lower()
        
        # Executive level
        if any(t in title for t in ["chief", "cmo", "cro", "ceo", "president"]):
            score += 100
        elif any(t in title for t in ["vp", "vice president"]):
            score += 80
        elif any(t in title for t in ["director", "head of"]):
            score += 60
        elif any(t in title for t in ["senior", "lead"]):
            score += 40
        elif "manager" in title:
            score += 30
        
        # Function relevance
        if any(f in title for f in ["marketing", "demand", "growth", "field", "event"]):
            score += 30
        elif any(f in title for f in ["sales", "revenue", "business"]):
            score += 20
        
        # Engagement signals
        if contact.get("hs_email_last_open_date"):
            score += 10
        if contact.get("hs_analytics_num_page_views"):
            score += 10
        
        return score


# Singleton
_analyzer: Optional[AccountAnalyzer] = None


def get_account_analyzer(hubspot_connector=None) -> AccountAnalyzer:
    """Get singleton account analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = AccountAnalyzer(hubspot_connector=hubspot_connector)
    return _analyzer
