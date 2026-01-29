"""Data Decay Agent - Identifies stale contacts needing refresh.

Responsibilities:
- Flag contacts with no activity in 90/180/365 days
- Detect bounced emails
- Identify job title changes (based on LinkedIn enrichment)
- Score data freshness
- Prioritize refresh actions
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class DecayLevel(str, Enum):
    """Level of data decay."""
    FRESH = "fresh"           # Updated in last 90 days
    STALE = "stale"           # 90-180 days
    DECAYED = "decayed"       # 180-365 days
    ZOMBIE = "zombie"         # 365+ days, likely invalid


class DecayAction(str, Enum):
    """Recommended action for decayed contact."""
    NONE = "none"
    ENRICH = "enrich"               # Re-enrich from external sources
    VERIFY_EMAIL = "verify_email"   # Check if email still valid
    ARCHIVE = "archive"             # Move to archive (likely churned)
    DELETE = "delete"               # GDPR delete (requested or zombie)


@dataclass
class DecayAssessment:
    """Assessment of a contact's data decay."""
    contact_id: str
    decay_level: DecayLevel
    decay_score: float  # 0-1, higher = more decayed
    days_since_activity: int
    last_activity_date: Optional[str]
    issues: List[str]
    recommended_action: DecayAction
    priority: int  # 1-5, higher = more urgent


class DataDecayAgent(BaseAgent):
    """Identifies contacts with stale/decaying data.
    
    Decay Scoring:
    - No activity in 90 days: score += 0.2
    - No activity in 180 days: score += 0.3
    - No activity in 365 days: score += 0.3
    - Email bounced: score += 0.2
    - No recent engagement (opens/clicks): score += 0.1
    
    Refresh Triggers:
    - Job title change detected
    - Email bounce detected
    - Website visit after long silence
    - Deal stage change
    """
    
    # Decay thresholds in days
    STALE_THRESHOLD = 90
    DECAYED_THRESHOLD = 180
    ZOMBIE_THRESHOLD = 365
    
    def __init__(self):
        super().__init__(
            name="DataDecayAgent",
            description="Identifies stale contacts and recommends refresh actions"
        )
    
    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input based on action."""
        action = context.get("action", "assess")
        if action == "assess_contact":
            return "contact" in context
        elif action == "assess_batch":
            return "contacts" in context
        elif action == "get_decay_report":
            return "contacts" in context
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute decay assessment based on action."""
        action = context.get("action", "assess_contact")
        now = context.get("reference_date") or datetime.utcnow()
        if isinstance(now, str):
            now = datetime.fromisoformat(now.replace("Z", "+00:00"))
        
        if action == "assess_contact":
            contact = context.get("contact", {})
            assessment = self._assess_contact(contact, now)
            return {
                "status": "success",
                "assessment": self._assessment_to_dict(assessment),
            }
        
        elif action == "assess_batch":
            contacts = context.get("contacts", [])
            assessments = [self._assess_contact(c, now) for c in contacts]
            
            # Group by decay level
            by_level = {level.value: [] for level in DecayLevel}
            for a in assessments:
                by_level[a.decay_level.value].append(self._assessment_to_dict(a))
            
            return {
                "status": "success",
                "total_contacts": len(contacts),
                "summary": {
                    "fresh": len(by_level["fresh"]),
                    "stale": len(by_level["stale"]),
                    "decayed": len(by_level["decayed"]),
                    "zombie": len(by_level["zombie"]),
                },
                "by_level": by_level,
            }
        
        elif action == "get_decay_report":
            contacts = context.get("contacts", [])
            assessments = [self._assess_contact(c, now) for c in contacts]
            
            # Filter to actionable items
            actionable = [a for a in assessments if a.recommended_action != DecayAction.NONE]
            actionable.sort(key=lambda x: (x.priority, x.decay_score), reverse=True)
            
            # Group by recommended action
            by_action = {}
            for a in actionable:
                action_name = a.recommended_action.value
                if action_name not in by_action:
                    by_action[action_name] = []
                by_action[action_name].append(self._assessment_to_dict(a))
            
            return {
                "status": "success",
                "total_actionable": len(actionable),
                "by_action": by_action,
                "top_priority": [
                    self._assessment_to_dict(a) 
                    for a in actionable[:20]
                ],
            }
        
        elif action == "get_refresh_candidates":
            # Get contacts that should be re-enriched
            contacts = context.get("contacts", [])
            limit = context.get("limit", 100)
            
            assessments = [self._assess_contact(c, now) for c in contacts]
            refresh_candidates = [
                a for a in assessments 
                if a.recommended_action == DecayAction.ENRICH
            ]
            refresh_candidates.sort(key=lambda x: x.priority, reverse=True)
            
            return {
                "status": "success",
                "candidates": [
                    {
                        "contact_id": a.contact_id,
                        "decay_level": a.decay_level.value,
                        "days_stale": a.days_since_activity,
                        "issues": a.issues,
                    }
                    for a in refresh_candidates[:limit]
                ],
            }
        
        return {"status": "error", "error": f"Unknown action: {action}"}
    
    def _assess_contact(self, contact: Dict[str, Any], now: datetime) -> DecayAssessment:
        """Assess a single contact's data decay."""
        contact_id = contact.get("id", "unknown")
        issues = []
        decay_score = 0.0
        
        # Find last activity date
        last_activity = self._get_last_activity_date(contact)
        if last_activity:
            days_since = (now - last_activity).days
        else:
            # No activity found, use creation date
            created = contact.get("createdate")
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    days_since = (now - created_dt).days
                except (ValueError, AttributeError) as e:
                    logger.warning("contact_createdate_parse_error", contact_id=contact.get("id"), raw_date=created, error=str(e))
                    days_since = 999
            else:
                days_since = 999
        
        # Determine decay level
        if days_since >= self.ZOMBIE_THRESHOLD:
            decay_level = DecayLevel.ZOMBIE
            decay_score += 0.8
            issues.append(f"No activity in {days_since} days (zombie)")
        elif days_since >= self.DECAYED_THRESHOLD:
            decay_level = DecayLevel.DECAYED
            decay_score += 0.5
            issues.append(f"No activity in {days_since} days (decayed)")
        elif days_since >= self.STALE_THRESHOLD:
            decay_level = DecayLevel.STALE
            decay_score += 0.2
            issues.append(f"No activity in {days_since} days (stale)")
        else:
            decay_level = DecayLevel.FRESH
        
        # Check for email issues
        email_status = contact.get("hs_email_status", "").lower()
        if email_status in ["bounced", "invalid"]:
            decay_score += 0.2
            issues.append(f"Email status: {email_status}")
        
        # Check for unsubscribed
        if contact.get("hs_email_optout"):
            issues.append("Contact has opted out of email")
        
        # Check engagement metrics
        email_opens = int(contact.get("hs_email_open_count", 0) or 0)
        email_clicks = int(contact.get("hs_email_click_count", 0) or 0)
        if decay_level != DecayLevel.FRESH and email_opens == 0 and email_clicks == 0:
            decay_score += 0.1
            issues.append("No email engagement ever")
        
        # Check for missing key data
        if not contact.get("jobtitle"):
            issues.append("Missing job title")
        if not contact.get("phone") and not contact.get("mobilephone"):
            issues.append("Missing phone number")
        
        # Determine recommended action
        recommended_action = self._determine_action(decay_level, issues, contact)
        
        # Determine priority (1-5)
        priority = self._calculate_priority(contact, decay_level, issues)
        
        return DecayAssessment(
            contact_id=contact_id,
            decay_level=decay_level,
            decay_score=min(decay_score, 1.0),
            days_since_activity=days_since,
            last_activity_date=last_activity.isoformat() if last_activity else None,
            issues=issues,
            recommended_action=recommended_action,
            priority=priority,
        )
    
    def _get_last_activity_date(self, contact: Dict[str, Any]) -> Optional[datetime]:
        """Get the most recent activity date for a contact."""
        date_fields = [
            "notes_last_updated",
            "hs_last_sales_activity_date",
            "hs_lastmodifieddate",
            "lastmodifieddate",
            "hs_email_last_email_date",
            "hs_email_last_reply_date",
        ]
        
        latest = None
        for field in date_fields:
            value = contact.get(field)
            if value:
                try:
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    if latest is None or dt > latest:
                        latest = dt
                except (ValueError, AttributeError) as e:
                    logger.debug("activity_date_parse_skip", field=field, error=str(e))
                    continue
        
        return latest
    
    def _determine_action(
        self, 
        decay_level: DecayLevel, 
        issues: List[str],
        contact: Dict[str, Any]
    ) -> DecayAction:
        """Determine recommended action based on decay level and issues."""
        # Check if email is bounced
        email_status = contact.get("hs_email_status", "").lower()
        if email_status in ["bounced", "invalid"]:
            return DecayAction.VERIFY_EMAIL
        
        # Zombie contacts should be archived
        if decay_level == DecayLevel.ZOMBIE:
            # Unless they have deals
            if int(contact.get("num_associated_deals", 0) or 0) > 0:
                return DecayAction.ENRICH
            return DecayAction.ARCHIVE
        
        # Decayed contacts should be enriched
        if decay_level == DecayLevel.DECAYED:
            return DecayAction.ENRICH
        
        # Stale contacts - enrich if high value
        if decay_level == DecayLevel.STALE:
            lifecycle = contact.get("lifecyclestage", "").lower()
            if lifecycle in ["opportunity", "customer"]:
                return DecayAction.ENRICH
        
        return DecayAction.NONE
    
    def _calculate_priority(
        self, 
        contact: Dict[str, Any],
        decay_level: DecayLevel,
        issues: List[str]
    ) -> int:
        """Calculate priority 1-5 for refresh action."""
        priority = 1
        
        # Higher priority for important lifecycle stages
        lifecycle = contact.get("lifecyclestage", "").lower()
        if lifecycle == "customer":
            priority += 2
        elif lifecycle == "opportunity":
            priority += 1
        
        # Higher priority for contacts with deals
        if int(contact.get("num_associated_deals", 0) or 0) > 0:
            priority += 1
        
        # Higher priority for bounced emails (need to fix)
        if any("bounced" in i.lower() or "invalid" in i.lower() for i in issues):
            priority += 1
        
        return min(priority, 5)
    
    def _assessment_to_dict(self, assessment: DecayAssessment) -> Dict[str, Any]:
        """Convert assessment to dict."""
        return {
            "contact_id": assessment.contact_id,
            "decay_level": assessment.decay_level.value,
            "decay_score": round(assessment.decay_score, 2),
            "days_since_activity": assessment.days_since_activity,
            "last_activity_date": assessment.last_activity_date,
            "issues": assessment.issues,
            "recommended_action": assessment.recommended_action.value,
            "priority": assessment.priority,
        }
