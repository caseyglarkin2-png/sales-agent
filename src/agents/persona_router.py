"""Persona-based messaging router.

Routes contacts to appropriate messaging based on job title and role.
"""
from enum import Enum
from typing import Dict, Optional, Tuple

from pydantic import BaseModel

from src.logger import get_logger

logger = get_logger(__name__)


class Persona(str, Enum):
    """Persona categories for messaging."""
    EVENTS = "events"
    DEMAND_GEN = "demand_gen"
    SALES = "sales"
    MARKETING_GENERAL = "marketing_general"
    EXECUTIVE = "executive"
    UNKNOWN = "unknown"


class PersonaConfig(BaseModel):
    """Configuration for a persona's messaging approach."""
    persona: Persona
    focus_area: str
    pain_points: list[str]
    value_props: list[str]
    cta_style: str
    opener_style: str


# Persona configurations
PERSONA_CONFIGS: Dict[Persona, PersonaConfig] = {
    Persona.EVENTS: PersonaConfig(
        persona=Persona.EVENTS,
        focus_area="Field Marketing & Event Execution",
        pain_points=[
            "Event coordination and execution complexity",
            "Measuring event ROI and attribution",
            "Scaling event programs without scaling headcount",
            "Trade show booth traffic and follow-up",
        ],
        value_props=[
            "Pesti handles end-to-end field marketing execution",
            "We staff, manage, and measure your event presence",
            "Turn trade show leads into qualified meetings",
            "Extend your field marketing team without hiring",
        ],
        cta_style="Quick call to discuss your upcoming events calendar",
        opener_style="event-focused",
    ),
    Persona.DEMAND_GEN: PersonaConfig(
        persona=Persona.DEMAND_GEN,
        focus_area="Lead Generation & Pipeline Velocity",
        pain_points=[
            "Lead quality vs quantity trade-offs",
            "Nurturing leads through long sales cycles",
            "MQL to SQL conversion rates",
            "Pipeline velocity and deal acceleration",
        ],
        value_props=[
            "Pesti generates qualified leads, not just names",
            "We accelerate pipeline with targeted outreach",
            "Multi-touch nurturing that actually converts",
            "ABM programs that reach the right accounts",
        ],
        cta_style="15 min to explore your current pipeline challenges",
        opener_style="metrics-focused",
    ),
    Persona.SALES: PersonaConfig(
        persona=Persona.SALES,
        focus_area="Target Accounts & Sales Alignment",
        pain_points=[
            "Getting meetings with target accounts",
            "Marketing-sales alignment and handoff",
            "Account penetration and multi-threading",
            "Competitive displacement",
        ],
        value_props=[
            "Pesti helps sales get into target accounts",
            "We align marketing execution with sales priorities",
            "Multi-channel outreach to decision makers",
            "Research and intelligence on target accounts",
        ],
        cta_style="Chat about your target account list",
        opener_style="results-focused",
    ),
    Persona.MARKETING_GENERAL: PersonaConfig(
        persona=Persona.MARKETING_GENERAL,
        focus_area="Go-to-Market Execution",
        pain_points=[
            "Scaling GTM without scaling team",
            "Executing on too many priorities",
            "Measuring marketing impact",
            "Speed to market",
        ],
        value_props=[
            "Pesti is your GTM execution partner",
            "We handle the execution so you can focus on strategy",
            "Extend your marketing team on demand",
            "Full-funnel execution from awareness to pipeline",
        ],
        cta_style="Quick intro to see if we're a fit",
        opener_style="collaborative",
    ),
    Persona.EXECUTIVE: PersonaConfig(
        persona=Persona.EXECUTIVE,
        focus_area="Revenue Growth & GTM Strategy",
        pain_points=[
            "Scaling revenue efficiently",
            "GTM team productivity",
            "Marketing ROI visibility",
            "Go-to-market velocity",
        ],
        value_props=[
            "Pesti accelerates revenue without headcount growth",
            "Flexible GTM execution at scale",
            "Clear ROI on marketing investments",
            "Speed and agility in GTM execution",
        ],
        cta_style="Brief call to share how similar companies scale GTM",
        opener_style="strategic",
    ),
    Persona.UNKNOWN: PersonaConfig(
        persona=Persona.UNKNOWN,
        focus_area="Go-to-Market Support",
        pain_points=[
            "Marketing and sales execution challenges",
            "Resource constraints",
        ],
        value_props=[
            "Pesti helps with GTM execution",
            "Flexible support for marketing and sales",
        ],
        cta_style="Quick chat to learn more about your needs",
        opener_style="curious",
    ),
}


# Keywords for persona detection
PERSONA_KEYWORDS: Dict[Persona, list[str]] = {
    Persona.EVENTS: [
        "event", "events", "field marketing", "trade show", "tradeshow",
        "conference", "conferences", "experiential", "roadshow", "booth",
        "field", "activation", "activations",
    ],
    Persona.DEMAND_GEN: [
        "demand", "demand gen", "demand generation", "lead gen", "lead generation",
        "pipeline", "nurture", "nurturing", "growth marketing", "acquisition",
        "abm", "account based", "account-based", "inbound", "outbound",
        "lifecycle", "velocity", "mql", "sql",
    ],
    Persona.SALES: [
        "sales", "account executive", "ae", "sdr", "bdr", "business development",
        "revenue", "sales ops", "sales operations", "sales enablement",
        "enterprise sales", "strategic accounts", "account manager",
    ],
    Persona.EXECUTIVE: [
        "cmo", "vp", "vice president", "chief", "head of", "director",
        "svp", "evp", "c-suite", "founder", "ceo", "coo", "cro",
    ],
    Persona.MARKETING_GENERAL: [
        "marketing", "brand", "content", "digital", "product marketing",
        "pmm", "communications", "comms", "campaigns",
    ],
}


def detect_persona(job_title: Optional[str], company_name: Optional[str] = None) -> Tuple[Persona, float]:
    """Detect the persona category from job title.
    
    Args:
        job_title: The contact's job title
        company_name: Optional company name for context
        
    Returns:
        Tuple of (Persona, confidence_score)
    """
    if not job_title:
        return Persona.UNKNOWN, 0.0
    
    title_lower = job_title.lower()
    scores: Dict[Persona, float] = {}
    
    for persona, keywords in PERSONA_KEYWORDS.items():
        score = 0.0
        for keyword in keywords:
            if keyword in title_lower:
                # Longer keywords get higher weight
                score += len(keyword) / 10.0
        scores[persona] = score
    
    # Get the highest scoring persona
    if not scores or max(scores.values()) == 0:
        return Persona.UNKNOWN, 0.0
    
    best_persona = max(scores, key=scores.get)
    best_score = scores[best_persona]
    
    # Normalize confidence to 0-1
    confidence = min(best_score, 1.0)
    
    # Check for executive override (executives should be their own category)
    if scores.get(Persona.EXECUTIVE, 0) > 0.5:
        # But only if they're not clearly in another function
        if best_persona != Persona.EXECUTIVE and best_score < 0.8:
            # Executive title but functional role, use functional
            pass
        elif best_persona == Persona.EXECUTIVE or scores[Persona.EXECUTIVE] > best_score:
            return Persona.EXECUTIVE, min(scores[Persona.EXECUTIVE], 1.0)
    
    logger.debug(f"Detected persona {best_persona.value} with confidence {confidence} for '{job_title}'")
    return best_persona, confidence


def get_persona_config(persona: Persona) -> PersonaConfig:
    """Get the messaging configuration for a persona."""
    return PERSONA_CONFIGS.get(persona, PERSONA_CONFIGS[Persona.UNKNOWN])


def get_messaging_context(job_title: Optional[str], company_name: Optional[str] = None) -> Dict:
    """Get full messaging context for a contact.
    
    Args:
        job_title: The contact's job title
        company_name: Optional company name
        
    Returns:
        Dict with persona, config, and messaging guidance
    """
    persona, confidence = detect_persona(job_title, company_name)
    config = get_persona_config(persona)
    
    return {
        "persona": persona.value,
        "confidence": confidence,
        "focus_area": config.focus_area,
        "pain_points": config.pain_points,
        "value_props": config.value_props,
        "cta_style": config.cta_style,
        "opener_style": config.opener_style,
        "job_title": job_title,
        "company_name": company_name,
    }


# Tests
if __name__ == "__main__":
    test_titles = [
        "Director of Field Marketing",
        "Demand Generation Manager",
        "VP of Sales",
        "Account Executive",
        "CMO",
        "Marketing Coordinator",
        "Events Manager",
        "Head of Growth",
        "Sales Development Representative",
        "Senior Demand Gen Specialist",
    ]
    
    for title in test_titles:
        persona, conf = detect_persona(title)
        print(f"{title:40} -> {persona.value:15} ({conf:.2f})")
