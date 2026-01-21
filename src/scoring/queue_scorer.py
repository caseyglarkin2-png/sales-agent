"""Queue scorer for prioritizing draft queue by lead quality.

Scores leads based on:
1. Recent email activity (DEPRIORITIZE if emailed recently)
2. ICP fit (title, function)
3. TAM fit (company, industry)
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from src.connectors.hubspot import create_hubspot_connector
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QueueScore:
    """Score for a draft in the queue."""
    draft_id: str
    email: str
    name: str
    company: str
    
    # Score components (0-100)
    recency_score: int = 50  # 100 = never contacted, 0 = contacted yesterday
    icp_score: int = 50      # How well they match ICP
    tam_score: int = 50      # Revenue potential
    
    # Composite
    total_score: int = 50
    tier: str = "B"          # A, B, C, D
    priority: int = 0        # Rank in queue (lower = higher priority)
    
    # Flags
    recently_contacted: bool = False
    last_contact_date: Optional[str] = None
    contact_found_in_hubspot: bool = False
    
    # Reasons
    factors: List[str] = field(default_factory=list)
    
    def calculate_total(self):
        """Calculate weighted total score."""
        # Recency is KING - if recently contacted, big penalty
        # Weight: Recency 50%, ICP 30%, TAM 20%
        self.total_score = int(
            self.recency_score * 0.50 +
            self.icp_score * 0.30 +
            self.tam_score * 0.20
        )
        
        # Assign tier
        if self.total_score >= 80:
            self.tier = "A"
        elif self.total_score >= 60:
            self.tier = "B"
        elif self.total_score >= 40:
            self.tier = "C"
        else:
            self.tier = "D"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "email": self.email,
            "name": self.name,
            "company": self.company,
            "recency_score": self.recency_score,
            "icp_score": self.icp_score,
            "tam_score": self.tam_score,
            "total_score": self.total_score,
            "tier": self.tier,
            "priority": self.priority,
            "recently_contacted": self.recently_contacted,
            "last_contact_date": self.last_contact_date,
            "contact_found_in_hubspot": self.contact_found_in_hubspot,
            "factors": self.factors,
        }


# ICP title scoring - CHAINge NA is logistics/supply chain conference
ICP_TITLES = {
    # Executive buyer titles (highest)
    "vp": 30, "vice president": 30, "chief": 25, "director": 25,
    "head of": 25, "svp": 30, "evp": 30,
    # Manager level
    "manager": 15, "senior": 12, "lead": 12,
    # Lower but still relevant
    "coordinator": 8, "specialist": 8,
}

# Target functions for logistics/supply chain event
ICP_FUNCTIONS = {
    "logistics": 40, "supply chain": 40, "operations": 35,
    "procurement": 35, "sourcing": 30, "transportation": 35,
    "warehouse": 30, "distribution": 30, "fulfillment": 30,
    "freight": 35, "shipping": 30, "3pl": 35,
    "marketing": 25, "events": 30, "demand gen": 25,
    "sales": 15, "business development": 15,
}

# Company types that fit TAM
TAM_COMPANY_SIGNALS = {
    "software": 20, "technology": 20, "tech": 20,
    "logistics": 30, "supply chain": 30, "freight": 30,
    "manufacturing": 25, "retail": 20, "ecommerce": 20,
    "consulting": 15, "solutions": 15, "services": 10,
}


class QueueScorer:
    """Scores and prioritizes the draft queue."""
    
    def __init__(self):
        self.hubspot = None
        # Cache of contact email -> last contact date
        self._contact_cache: Dict[str, Dict] = {}
    
    async def _get_hubspot(self):
        """Lazy load HubSpot connector."""
        if self.hubspot is None:
            self.hubspot = create_hubspot_connector()
        return self.hubspot
    
    async def score_draft(
        self,
        draft_id: str,
        email: str,
        name: str = "",
        company: str = "",
        job_title: str = "",
        request: str = "",
        check_hubspot: bool = True,
    ) -> QueueScore:
        """Score a single draft/lead.
        
        Args:
            draft_id: Unique draft identifier
            email: Contact email
            name: Contact name
            company: Company name
            job_title: Job title (if available)
            request: Original request/inquiry text
            check_hubspot: Whether to check HubSpot for recent contact
            
        Returns:
            QueueScore with breakdown
        """
        score = QueueScore(
            draft_id=draft_id,
            email=email,
            name=name,
            company=company,
        )
        
        # 1. Check recency - have we emailed them?
        if check_hubspot:
            await self._score_recency(score)
        
        # 2. Score ICP fit
        self._score_icp(score, job_title, name, request)
        
        # 3. Score TAM fit  
        self._score_tam(score, company, request)
        
        # Calculate composite
        score.calculate_total()
        
        logger.debug(f"Scored {email}: {score.total_score} (tier {score.tier})")
        return score
    
    async def _score_recency(self, score: QueueScore):
        """Check HubSpot for recent email activity with this contact."""
        try:
            hubspot = await self._get_hubspot()
            
            # Search for contact
            contact = await hubspot.search_contacts(score.email)
            
            if not contact:
                # Never in HubSpot = fresh lead = high recency score
                score.recency_score = 100
                score.contact_found_in_hubspot = False
                score.factors.append("New contact (not in HubSpot)")
                return
            
            score.contact_found_in_hubspot = True
            contact_id = contact.get("id")
            
            # Get engagements for this contact
            engagements = await hubspot.get_contact_engagements(contact_id, limit=20)
            
            if not engagements:
                # In HubSpot but no engagement history
                score.recency_score = 90
                score.factors.append("In HubSpot but no email history")
                return
            
            # Find most recent EMAIL engagement
            email_engagements = [
                e for e in engagements 
                if e.get("type", "").upper() == "EMAIL"
            ]
            
            if not email_engagements:
                score.recency_score = 85
                score.factors.append("In HubSpot, no email engagements")
                return
            
            # Parse timestamps and find most recent
            now = datetime.utcnow()
            most_recent = None
            
            for eng in email_engagements:
                ts = eng.get("timestamp")
                if ts:
                    try:
                        # HubSpot timestamps are usually ISO or epoch ms
                        if isinstance(ts, (int, float)):
                            eng_date = datetime.fromtimestamp(ts / 1000)
                        else:
                            eng_date = datetime.fromisoformat(ts.replace("Z", "+00:00").replace("+00:00", ""))
                        
                        if most_recent is None or eng_date > most_recent:
                            most_recent = eng_date
                    except Exception:
                        pass
            
            if most_recent is None:
                score.recency_score = 80
                score.factors.append("Email history exists but dates unclear")
                return
            
            # Calculate days since last contact
            days_ago = (now - most_recent).days
            score.last_contact_date = most_recent.isoformat()
            
            if days_ago <= 7:
                # Contacted in last week - DO NOT EMAIL
                score.recency_score = 0
                score.recently_contacted = True
                score.factors.append(f"⚠️ Emailed {days_ago} days ago - SKIP")
            elif days_ago <= 14:
                # 1-2 weeks ago - low priority
                score.recency_score = 20
                score.recently_contacted = True
                score.factors.append(f"Emailed {days_ago} days ago - low priority")
            elif days_ago <= 30:
                # 2-4 weeks ago - moderate
                score.recency_score = 50
                score.factors.append(f"Last email {days_ago} days ago")
            elif days_ago <= 90:
                # 1-3 months ago - okay to reach out
                score.recency_score = 75
                score.factors.append(f"Last email {days_ago} days ago - good timing")
            else:
                # 3+ months - great to re-engage
                score.recency_score = 95
                score.factors.append(f"Last email {days_ago} days ago - perfect for re-engagement")
                
        except Exception as e:
            logger.warning(f"Error checking recency for {score.email}: {e}")
            score.recency_score = 50  # Default if we can't check
            score.factors.append("Could not check email history")
    
    def _score_icp(
        self, 
        score: QueueScore, 
        job_title: str, 
        name: str, 
        request: str
    ):
        """Score ICP fit based on title and function."""
        icp_points = 50  # Start at neutral
        
        # Combine all text for keyword matching
        text = f"{job_title} {name} {request}".lower()
        
        # Check title keywords
        title_match = False
        for keyword, points in ICP_TITLES.items():
            if keyword in text:
                icp_points += points
                title_match = True
                score.factors.append(f"Title match: {keyword} (+{points})")
                break  # Only count best title match
        
        if not title_match:
            score.factors.append("No title signal")
        
        # Check function keywords
        function_match = False
        for keyword, points in ICP_FUNCTIONS.items():
            if keyword in text:
                icp_points += points
                function_match = True
                score.factors.append(f"Function match: {keyword} (+{points})")
                break  # Only count best function match
        
        if not function_match:
            score.factors.append("No function signal")
        
        # Check request content for buying signals
        request_lower = request.lower()
        if "sponsor" in request_lower:
            icp_points += 15
            score.factors.append("Sponsor interest (+15)")
        if "exhibit" in request_lower:
            icp_points += 15
            score.factors.append("Exhibitor interest (+15)")
        if "speak" in request_lower:
            icp_points += 10
            score.factors.append("Speaker interest (+10)")
        if "booth" in request_lower:
            icp_points += 12
            score.factors.append("Booth inquiry (+12)")
        if "attend" in request_lower:
            icp_points += 5
            score.factors.append("Attendee interest (+5)")
        
        # Cap at 100
        score.icp_score = min(100, max(0, icp_points))
    
    def _score_tam(self, score: QueueScore, company: str, request: str):
        """Score TAM fit based on company signals."""
        tam_points = 50  # Start at neutral
        
        text = f"{company} {request}".lower()
        
        # Check company type signals
        for keyword, points in TAM_COMPANY_SIGNALS.items():
            if keyword in text:
                tam_points += points
                score.factors.append(f"Company signal: {keyword} (+{points})")
                break  # Only count best match
        
        # Company name length heuristic (longer often = bigger)
        if len(company) > 20:
            tam_points += 5
            score.factors.append("Large company name (+5)")
        
        # Cap at 100
        score.tam_score = min(100, max(0, tam_points))
    
    async def score_queue(
        self,
        drafts: List[Dict[str, Any]],
        check_hubspot: bool = True,
    ) -> List[QueueScore]:
        """Score all drafts in queue and return sorted by priority.
        
        Args:
            drafts: List of draft objects from queue
            check_hubspot: Whether to check HubSpot (slower but more accurate)
            
        Returns:
            List of QueueScore objects sorted by total_score descending
        """
        scores = []
        
        for draft in drafts:
            # Extract fields - handle different draft formats
            draft_id = draft.get("id", draft.get("draft_id", ""))
            email = draft.get("recipient", draft.get("email", ""))
            name = draft.get("contact_name", draft.get("name", ""))
            company = draft.get("company_name", draft.get("company", ""))
            
            # Check metadata for more fields - handle if it's a string
            metadata = draft.get("metadata", {})
            if isinstance(metadata, str):
                try:
                    import json
                    metadata = json.loads(metadata)
                except Exception:
                    metadata = {}
            if not isinstance(metadata, dict):
                metadata = {}
                
            job_title = metadata.get("job_title", "")
            request = metadata.get("request", metadata.get("original_request", ""))
            
            # Also check if contact info is in metadata
            if not name and metadata.get("contact_name"):
                name = metadata["contact_name"]
            if not company and metadata.get("company_name"):
                company = metadata["company_name"]
            
            try:
                score = await self.score_draft(
                    draft_id=draft_id,
                    email=email,
                    name=name,
                    company=company,
                    job_title=job_title,
                    request=request,
                    check_hubspot=check_hubspot,
                )
                scores.append(score)
            except Exception as e:
                logger.error(f"Error scoring draft {draft_id}: {e}")
                # Add default score
                scores.append(QueueScore(
                    draft_id=draft_id,
                    email=email,
                    name=name,
                    company=company,
                    factors=[f"Scoring error: {str(e)}"],
                ))
        
        # Sort by total score descending
        scores.sort(key=lambda s: s.total_score, reverse=True)
        
        # Assign priority ranks
        for i, s in enumerate(scores):
            s.priority = i + 1
        
        logger.info(f"Scored {len(scores)} drafts. Top tier: {sum(1 for s in scores if s.tier == 'A')}")
        return scores


# Singleton instance
_scorer: Optional[QueueScorer] = None


async def get_queue_scorer() -> QueueScorer:
    """Get the queue scorer singleton."""
    global _scorer
    if _scorer is None:
        _scorer = QueueScorer()
    return _scorer


async def score_pending_queue(check_hubspot: bool = True) -> List[Dict[str, Any]]:
    """Score all pending drafts in the queue.
    
    Convenience function that loads the queue, scores it, and returns results.
    """
    from src.operator_mode import get_draft_queue
    
    queue = get_draft_queue()  # Not async
    drafts = await queue.get_pending_approvals()  # Correct method name
    
    scorer = await get_queue_scorer()
    scores = await scorer.score_queue(drafts, check_hubspot=check_hubspot)
    
    return [s.to_dict() for s in scores]
