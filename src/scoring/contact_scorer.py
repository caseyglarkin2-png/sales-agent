"""
Contact Scoring Engine.

Scores contacts based on fit, engagement, and intent signals.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ScoreTier(Enum):
    HOT = "hot"       # 80-100
    WARM = "warm"     # 60-79
    COOL = "cool"     # 40-59
    COLD = "cold"     # 0-39


@dataclass
class ContactScore:
    """Scored contact."""
    email: str
    name: str
    company: str
    
    # Score components (0-100 each)
    fit_score: int = 0       # ICP fit
    engagement_score: int = 0  # Activity/engagement
    intent_score: int = 0      # Buying intent signals
    
    # Combined score
    total_score: int = 0
    tier: ScoreTier = ScoreTier.COLD
    
    # Factors
    fit_factors: List[str] = None
    engagement_factors: List[str] = None
    intent_factors: List[str] = None
    
    scored_at: datetime = None
    
    def __post_init__(self):
        if self.fit_factors is None:
            self.fit_factors = []
        if self.engagement_factors is None:
            self.engagement_factors = []
        if self.intent_factors is None:
            self.intent_factors = []
        if self.scored_at is None:
            self.scored_at = datetime.utcnow()
        
        # Calculate total and tier
        self._calculate_total()
    
    def _calculate_total(self):
        # Weighted average: Fit 40%, Engagement 30%, Intent 30%
        self.total_score = int(
            self.fit_score * 0.4 +
            self.engagement_score * 0.3 +
            self.intent_score * 0.3
        )
        
        if self.total_score >= 80:
            self.tier = ScoreTier.HOT
        elif self.total_score >= 60:
            self.tier = ScoreTier.WARM
        elif self.total_score >= 40:
            self.tier = ScoreTier.COOL
        else:
            self.tier = ScoreTier.COLD
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "email": self.email,
            "name": self.name,
            "company": self.company,
            "fit_score": self.fit_score,
            "engagement_score": self.engagement_score,
            "intent_score": self.intent_score,
            "total_score": self.total_score,
            "tier": self.tier.value,
            "fit_factors": self.fit_factors,
            "engagement_factors": self.engagement_factors,
            "intent_factors": self.intent_factors,
            "scored_at": self.scored_at.isoformat() if self.scored_at else None,
        }


# ICP scoring criteria
ICP_CRITERIA = {
    "title_keywords": {
        "vp": 25,
        "director": 20,
        "head": 20,
        "chief": 25,
        "manager": 10,
        "lead": 10,
    },
    "department_keywords": {
        "marketing": 20,
        "demand": 25,
        "field": 25,
        "growth": 20,
        "revenue": 20,
        "sales": 15,
        "operations": 10,
    },
    "company_size": {
        "enterprise": 25,  # 1000+
        "mid_market": 20,  # 200-999
        "smb": 10,         # 50-199
    },
    "industries": {
        "technology": 20,
        "software": 20,
        "saas": 25,
        "fintech": 20,
        "healthcare": 15,
        "financial": 15,
    },
}


class ContactScorer:
    """Scores contacts for prioritization."""
    
    def __init__(self):
        self.scored_contacts: Dict[str, ContactScore] = {}
    
    def score_contact(
        self,
        email: str,
        name: str,
        company: str,
        job_title: Optional[str] = None,
        company_size: Optional[int] = None,
        industry: Optional[str] = None,
        engagements: Optional[List[Dict]] = None,
        intent_signals: Optional[List[str]] = None,
    ) -> ContactScore:
        """Score a contact based on fit, engagement, and intent.
        
        Args:
            email: Contact email
            name: Contact name
            company: Company name
            job_title: Job title
            company_size: Number of employees
            industry: Company industry
            engagements: List of engagement events
            intent_signals: Intent signals detected
            
        Returns:
            Scored contact
        """
        fit_score, fit_factors = self._calculate_fit(
            job_title=job_title,
            company_size=company_size,
            industry=industry,
        )
        
        engagement_score, engagement_factors = self._calculate_engagement(
            engagements=engagements or [],
        )
        
        intent_score, intent_factors = self._calculate_intent(
            intent_signals=intent_signals or [],
        )
        
        score = ContactScore(
            email=email,
            name=name,
            company=company,
            fit_score=fit_score,
            engagement_score=engagement_score,
            intent_score=intent_score,
            fit_factors=fit_factors,
            engagement_factors=engagement_factors,
            intent_factors=intent_factors,
        )
        
        self.scored_contacts[email] = score
        logger.info(f"Scored {email}: {score.total_score} ({score.tier.value})")
        
        return score
    
    def _calculate_fit(
        self,
        job_title: Optional[str],
        company_size: Optional[int],
        industry: Optional[str],
    ) -> tuple[int, List[str]]:
        """Calculate ICP fit score."""
        score = 0
        factors = []
        
        if job_title:
            title_lower = job_title.lower()
            
            # Title seniority
            for keyword, points in ICP_CRITERIA["title_keywords"].items():
                if keyword in title_lower:
                    score += points
                    factors.append(f"Title: {keyword} (+{points})")
                    break
            
            # Department alignment
            for keyword, points in ICP_CRITERIA["department_keywords"].items():
                if keyword in title_lower:
                    score += points
                    factors.append(f"Department: {keyword} (+{points})")
                    break
        
        if company_size:
            if company_size >= 1000:
                score += ICP_CRITERIA["company_size"]["enterprise"]
                factors.append(f"Enterprise ({company_size}+ employees)")
            elif company_size >= 200:
                score += ICP_CRITERIA["company_size"]["mid_market"]
                factors.append(f"Mid-market ({company_size} employees)")
            elif company_size >= 50:
                score += ICP_CRITERIA["company_size"]["smb"]
                factors.append(f"SMB ({company_size} employees)")
        
        if industry:
            industry_lower = industry.lower()
            for ind, points in ICP_CRITERIA["industries"].items():
                if ind in industry_lower:
                    score += points
                    factors.append(f"Industry: {ind} (+{points})")
                    break
        
        return min(score, 100), factors
    
    def _calculate_engagement(
        self,
        engagements: List[Dict],
    ) -> tuple[int, List[str]]:
        """Calculate engagement score from activity."""
        score = 0
        factors = []
        
        if not engagements:
            return 0, ["No engagement history"]
        
        # Score by engagement type
        engagement_weights = {
            "email_open": 5,
            "email_click": 15,
            "email_reply": 30,
            "meeting": 40,
            "form_submit": 25,
            "website_visit": 10,
            "content_download": 20,
        }
        
        for engagement in engagements:
            eng_type = engagement.get("type", "").lower()
            for key, points in engagement_weights.items():
                if key in eng_type:
                    score += points
                    factors.append(f"{eng_type} (+{points})")
                    break
        
        # Recency bonus
        recent_count = sum(
            1 for e in engagements
            if e.get("timestamp") and 
            datetime.fromisoformat(e["timestamp"]) > datetime.utcnow() - timedelta(days=7)
        )
        
        if recent_count > 0:
            recency_bonus = min(recent_count * 5, 20)
            score += recency_bonus
            factors.append(f"Recent activity ({recent_count} in 7 days)")
        
        return min(score, 100), factors
    
    def _calculate_intent(
        self,
        intent_signals: List[str],
    ) -> tuple[int, List[str]]:
        """Calculate intent score from signals."""
        score = 0
        factors = []
        
        intent_weights = {
            "pricing_page": 25,
            "demo_request": 40,
            "competitor_research": 20,
            "solution_research": 20,
            "job_posting": 15,  # Hiring for related roles
            "funding_round": 15,
            "executive_change": 10,
            "expansion": 20,
            "pain_point_mention": 25,
        }
        
        for signal in intent_signals:
            signal_lower = signal.lower()
            for key, points in intent_weights.items():
                if key in signal_lower:
                    score += points
                    factors.append(f"{signal} (+{points})")
                    break
            else:
                # Default intent signal
                score += 10
                factors.append(f"{signal} (+10)")
        
        return min(score, 100), factors
    
    def get_top_contacts(
        self,
        tier: Optional[ScoreTier] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get top scored contacts."""
        contacts = list(self.scored_contacts.values())
        
        if tier:
            contacts = [c for c in contacts if c.tier == tier]
        
        return [
            c.to_dict() for c in 
            sorted(contacts, key=lambda x: x.total_score, reverse=True)[:limit]
        ]
    
    def get_score_distribution(self) -> Dict[str, int]:
        """Get score distribution by tier."""
        return {
            "hot": sum(1 for c in self.scored_contacts.values() if c.tier == ScoreTier.HOT),
            "warm": sum(1 for c in self.scored_contacts.values() if c.tier == ScoreTier.WARM),
            "cool": sum(1 for c in self.scored_contacts.values() if c.tier == ScoreTier.COOL),
            "cold": sum(1 for c in self.scored_contacts.values() if c.tier == ScoreTier.COLD),
            "total": len(self.scored_contacts),
        }
    
    def get_contact_score(self, email: str) -> Optional[Dict[str, Any]]:
        """Get score for a specific contact."""
        score = self.scored_contacts.get(email)
        return score.to_dict() if score else None
    
    async def score_from_hubspot(
        self,
        email: str,
    ) -> Optional[ContactScore]:
        """Score a contact using HubSpot data."""
        try:
            from src.connectors.hubspot import get_hubspot_connector
            hubspot = get_hubspot_connector()
            
            # Get contact details
            contacts = hubspot.search_contacts_by_email(email)
            if not contacts:
                return None
            
            contact = contacts[0]
            props = contact.get("properties", {})
            
            # Get engagements
            engagements = await hubspot.get_contact_engagements(contact["id"])
            
            return self.score_contact(
                email=email,
                name=f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                company=props.get("company", ""),
                job_title=props.get("jobtitle"),
                industry=props.get("industry"),
                engagements=engagements,
            )
            
        except Exception as e:
            logger.error(f"Error scoring from HubSpot: {e}")
            return None


# Singleton
_scorer: Optional[ContactScorer] = None


def get_contact_scorer() -> ContactScorer:
    """Get singleton contact scorer."""
    global _scorer
    if _scorer is None:
        _scorer = ContactScorer()
    return _scorer
