"""Lead scoring module for prioritizing contacts.

Scores leads based on job title, company signals, and engagement history.
"""
from typing import Any, Dict, Optional

from pydantic import BaseModel

from src.agents.persona_router import detect_persona, Persona
from src.logger import get_logger

logger = get_logger(__name__)


class LeadScore(BaseModel):
    """Detailed lead scoring breakdown."""
    total_score: float
    title_score: float = 0.0
    company_score: float = 0.0
    engagement_score: float = 0.0
    recency_score: float = 0.0
    fit_score: float = 0.0
    persona: str = "unknown"
    persona_confidence: float = 0.0
    tier: str = "C"  # A, B, C, D
    priority_rank: int = 0
    notes: list[str] = []


class LeadScorer:
    """Scores and prioritizes leads for outreach."""
    
    # Title scoring weights
    EXECUTIVE_TITLES = {
        "cmo": 50, "vp": 45, "vice president": 45, "chief": 50,
        "head of": 40, "director": 35, "svp": 45, "evp": 45,
        "cro": 50, "ceo": 30, "founder": 30,  # Lower for CEO/founder - often not the buyer
    }
    
    MANAGER_TITLES = {
        "manager": 25, "lead": 25, "senior": 20, "principal": 25,
    }
    
    # Function scoring - how well does the function match Pesti's offerings
    TARGET_FUNCTIONS = {
        "demand generation": 40,
        "demand gen": 40,
        "field marketing": 40,
        "events": 35,
        "event marketing": 40,
        "growth": 35,
        "marketing ops": 30,
        "marketing operations": 30,
        "abm": 40,
        "account based": 40,
        "pipeline": 35,
        "lead generation": 35,
    }
    
    # Less ideal but still relevant functions
    ADJACENT_FUNCTIONS = {
        "marketing": 20,
        "sales": 15,  # Sales titles may be buyers but different messaging
        "revenue": 25,
        "business development": 15,
        "partnerships": 15,
    }
    
    def __init__(self):
        pass
    
    def score_lead(
        self,
        email: str,
        job_title: str = "",
        company: str = "",
        hubspot_data: Optional[Dict[str, Any]] = None,
        engagement_data: Optional[Dict[str, Any]] = None,
    ) -> LeadScore:
        """Score a lead based on available data.
        
        Args:
            email: Contact email
            job_title: Job title
            company: Company name
            hubspot_data: Optional HubSpot contact/company data
            engagement_data: Optional prior engagement data
            
        Returns:
            LeadScore with detailed breakdown
        """
        notes = []
        
        # Score title
        title_score, title_notes = self._score_title(job_title)
        notes.extend(title_notes)
        
        # Score company
        company_score, company_notes = self._score_company(company, hubspot_data)
        notes.extend(company_notes)
        
        # Score engagement
        engagement_score, engagement_notes = self._score_engagement(engagement_data)
        notes.extend(engagement_notes)
        
        # Score fit (persona match)
        persona, persona_confidence = detect_persona(job_title, company)
        fit_score = self._calculate_fit_score(persona, persona_confidence)
        if persona != Persona.UNKNOWN:
            notes.append(f"Persona: {persona.value} ({persona_confidence:.0%} confidence)")
        
        # Calculate total
        total_score = title_score + company_score + engagement_score + fit_score
        
        # Determine tier
        tier = self._calculate_tier(total_score)
        
        score = LeadScore(
            total_score=round(total_score, 1),
            title_score=round(title_score, 1),
            company_score=round(company_score, 1),
            engagement_score=round(engagement_score, 1),
            fit_score=round(fit_score, 1),
            persona=persona.value,
            persona_confidence=round(persona_confidence, 2),
            tier=tier,
            notes=notes,
        )
        
        logger.debug(f"Scored {email}: {score.total_score} (Tier {tier})")
        return score
    
    def _score_title(self, job_title: str) -> tuple[float, list[str]]:
        """Score based on job title."""
        if not job_title:
            return 0.0, ["No job title provided"]
        
        title_lower = job_title.lower()
        score = 0.0
        notes = []
        
        # Check executive titles
        for term, points in self.EXECUTIVE_TITLES.items():
            if term in title_lower:
                score += points
                notes.append(f"Executive title: +{points}")
                break
        
        # Check manager titles (additive)
        for term, points in self.MANAGER_TITLES.items():
            if term in title_lower:
                score += points
                notes.append(f"Manager level: +{points}")
                break
        
        # Check target functions
        for term, points in self.TARGET_FUNCTIONS.items():
            if term in title_lower:
                score += points
                notes.append(f"Target function ({term}): +{points}")
                break
        else:
            # Check adjacent functions if no target match
            for term, points in self.ADJACENT_FUNCTIONS.items():
                if term in title_lower:
                    score += points
                    notes.append(f"Adjacent function ({term}): +{points}")
                    break
        
        return score, notes
    
    def _score_company(
        self,
        company: str,
        hubspot_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[float, list[str]]:
        """Score based on company signals."""
        score = 0.0
        notes = []
        
        if not company:
            return 0.0, ["No company provided"]
        
        # Base points for having company
        score += 10
        notes.append("Company provided: +10")
        
        if hubspot_data:
            # Company size scoring
            num_employees = hubspot_data.get("numberofemployees")
            if num_employees:
                try:
                    emp_count = int(num_employees)
                    if emp_count >= 1000:
                        score += 25
                        notes.append(f"Enterprise ({emp_count}+ employees): +25")
                    elif emp_count >= 200:
                        score += 20
                        notes.append(f"Mid-market ({emp_count} employees): +20")
                    elif emp_count >= 50:
                        score += 15
                        notes.append(f"SMB ({emp_count} employees): +15")
                except (ValueError, TypeError):
                    pass
            
            # Revenue scoring
            annual_revenue = hubspot_data.get("annualrevenue")
            if annual_revenue:
                try:
                    revenue = float(annual_revenue)
                    if revenue >= 100_000_000:  # $100M+
                        score += 20
                        notes.append("$100M+ revenue: +20")
                    elif revenue >= 10_000_000:  # $10M+
                        score += 15
                        notes.append("$10M+ revenue: +15")
                except (ValueError, TypeError):
                    pass
            
            # Industry fit (if detected)
            industry = hubspot_data.get("industry", "")
            b2b_industries = ["technology", "software", "saas", "fintech", "b2b"]
            if any(ind in industry.lower() for ind in b2b_industries):
                score += 15
                notes.append(f"B2B industry ({industry}): +15")
        
        return score, notes
    
    def _score_engagement(
        self,
        engagement_data: Optional[Dict[str, Any]] = None,
    ) -> tuple[float, list[str]]:
        """Score based on prior engagement."""
        if not engagement_data:
            return 0.0, []
        
        score = 0.0
        notes = []
        
        # Prior email threads
        thread_count = engagement_data.get("email_thread_count", 0)
        if thread_count > 0:
            points = min(thread_count * 10, 30)  # Cap at 30
            score += points
            notes.append(f"Prior email history ({thread_count} threads): +{points}")
        
        # Website visits
        page_views = engagement_data.get("page_views", 0)
        if page_views > 0:
            points = min(page_views * 2, 20)  # Cap at 20
            score += points
            notes.append(f"Website visits ({page_views}): +{points}")
        
        # Form submissions
        form_count = engagement_data.get("form_submissions", 0)
        if form_count > 1:
            points = (form_count - 1) * 15  # Bonus for multiple submissions
            score += points
            notes.append(f"Multiple form submissions ({form_count}): +{points}")
        
        return score, notes
    
    def _calculate_fit_score(self, persona: Persona, confidence: float) -> float:
        """Calculate fit score based on persona match."""
        if persona == Persona.UNKNOWN:
            return 0.0
        
        # Base fit by persona
        persona_fit = {
            Persona.EVENTS: 35,
            Persona.DEMAND_GEN: 40,
            Persona.SALES: 20,
            Persona.MARKETING_GENERAL: 25,
            Persona.EXECUTIVE: 30,
        }
        
        base_fit = persona_fit.get(persona, 10)
        
        # Adjust by confidence
        return base_fit * confidence
    
    def _calculate_tier(self, total_score: float) -> str:
        """Calculate lead tier based on total score."""
        if total_score >= 100:
            return "A"
        elif total_score >= 60:
            return "B"
        elif total_score >= 30:
            return "C"
        else:
            return "D"
    
    def rank_leads(
        self,
        leads: list[Dict[str, Any]],
    ) -> list[Dict[str, Any]]:
        """Score and rank a list of leads.
        
        Args:
            leads: List of lead dicts with email, job_title, company, etc.
            
        Returns:
            Sorted list with scores attached
        """
        scored_leads = []
        
        for lead in leads:
            score = self.score_lead(
                email=lead.get("email", ""),
                job_title=lead.get("job_title", ""),
                company=lead.get("company", ""),
                hubspot_data=lead.get("hubspot_data"),
                engagement_data=lead.get("engagement_data"),
            )
            
            lead_with_score = {
                **lead,
                "score": score.model_dump(),
                "total_score": score.total_score,
                "tier": score.tier,
            }
            scored_leads.append(lead_with_score)
        
        # Sort by score descending
        scored_leads.sort(key=lambda x: -x["total_score"])
        
        # Add rank
        for i, lead in enumerate(scored_leads):
            lead["priority_rank"] = i + 1
            lead["score"]["priority_rank"] = i + 1
        
        return scored_leads


# Global scorer instance
_lead_scorer: Optional[LeadScorer] = None


def get_lead_scorer() -> LeadScorer:
    """Get or create the global lead scorer."""
    global _lead_scorer
    if _lead_scorer is None:
        _lead_scorer = LeadScorer()
    return _lead_scorer
