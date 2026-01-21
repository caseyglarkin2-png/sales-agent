"""
History Enricher.

Aggregates past deals, meetings, calls, and emails
to build a relationship summary for each contact.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class RelationshipSummary:
    """Summary of relationship with a contact."""
    contact_email: str
    relationship_stage: str = "new"  # new, engaged, active, dormant
    first_touch: Optional[str] = None
    last_touch: Optional[str] = None
    total_touchpoints: int = 0
    
    # Communication history
    emails_sent: int = 0
    emails_received: int = 0
    meetings_count: int = 0
    calls_count: int = 0
    
    # Deal history
    deals: List[Dict[str, Any]] = None
    total_deal_value: float = 0.0
    active_deals: int = 0
    won_deals: int = 0
    
    # Recent activity
    recent_notes: List[Dict[str, str]] = None
    open_tasks: List[Dict[str, str]] = None
    
    # Context for outreach
    key_topics: List[str] = None
    action_items: List[str] = None
    recommended_next_step: Optional[str] = None
    
    def __post_init__(self):
        if self.deals is None:
            self.deals = []
        if self.recent_notes is None:
            self.recent_notes = []
        if self.open_tasks is None:
            self.open_tasks = []
        if self.key_topics is None:
            self.key_topics = []
        if self.action_items is None:
            self.action_items = []
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HistoryEnricher:
    """Enriches contacts with relationship history from HubSpot."""
    
    def __init__(self, hubspot_connector=None):
        self.hubspot = hubspot_connector
    
    async def get_relationship_summary(
        self,
        email: str,
        contact_id: Optional[str] = None,
    ) -> RelationshipSummary:
        """Get comprehensive relationship summary for a contact.
        
        Args:
            email: Contact email
            contact_id: Optional HubSpot contact ID
            
        Returns:
            RelationshipSummary with all history
        """
        summary = RelationshipSummary(contact_email=email)
        
        if not self.hubspot:
            logger.warning("HubSpot connector not available")
            return summary
        
        try:
            # Get contact data
            contact = await self._get_contact(email, contact_id)
            if not contact:
                return summary
            
            contact_id = contact.get("id") or contact.get("hs_object_id")
            
            # Get engagement history
            await self._enrich_engagements(summary, contact_id)
            
            # Get deals
            await self._enrich_deals(summary, contact_id)
            
            # Get notes
            await self._enrich_notes(summary, contact_id)
            
            # Get tasks
            await self._enrich_tasks(summary, contact_id)
            
            # Calculate relationship stage
            summary.relationship_stage = self._determine_stage(summary)
            
            # Generate recommended next step
            summary.recommended_next_step = self._recommend_next_step(summary)
            
        except Exception as e:
            logger.error(f"Error getting relationship summary: {e}")
        
        return summary
    
    async def _get_contact(
        self,
        email: str,
        contact_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Get contact from HubSpot."""
        if contact_id:
            try:
                return await self.hubspot.get_contact(contact_id)
            except Exception:
                pass
        
        try:
            contacts = await self.hubspot.search_contacts(email)
            if contacts:
                return contacts[0]
        except Exception as e:
            logger.warning(f"Could not find contact: {e}")
        
        return None
    
    async def _enrich_engagements(
        self,
        summary: RelationshipSummary,
        contact_id: str,
    ):
        """Enrich with engagement data."""
        try:
            engagements = await self.hubspot.get_contact_engagements(contact_id)
            
            for engagement in engagements:
                eng_type = engagement.get("type", "").lower()
                timestamp = engagement.get("timestamp")
                
                # Track first and last touch
                if timestamp:
                    if not summary.first_touch or timestamp < summary.first_touch:
                        summary.first_touch = timestamp
                    if not summary.last_touch or timestamp > summary.last_touch:
                        summary.last_touch = timestamp
                
                # Count by type
                if eng_type == "email":
                    direction = engagement.get("direction", "").lower()
                    if direction == "outgoing":
                        summary.emails_sent += 1
                    else:
                        summary.emails_received += 1
                elif eng_type == "meeting":
                    summary.meetings_count += 1
                elif eng_type == "call":
                    summary.calls_count += 1
                
                summary.total_touchpoints += 1
                
        except Exception as e:
            logger.warning(f"Could not get engagements: {e}")
    
    async def _enrich_deals(
        self,
        summary: RelationshipSummary,
        contact_id: str,
    ):
        """Enrich with deal history."""
        try:
            deals = await self.hubspot.get_contact_deals(contact_id)
            
            for deal in deals:
                deal_info = {
                    "id": deal.get("id"),
                    "name": deal.get("dealname"),
                    "stage": deal.get("dealstage"),
                    "amount": deal.get("amount", 0),
                    "close_date": deal.get("closedate"),
                }
                summary.deals.append(deal_info)
                
                amount = float(deal.get("amount") or 0)
                summary.total_deal_value += amount
                
                stage = (deal.get("dealstage") or "").lower()
                if stage == "closedwon":
                    summary.won_deals += 1
                elif "closed" not in stage:
                    summary.active_deals += 1
                    
        except Exception as e:
            logger.warning(f"Could not get deals: {e}")
    
    async def _enrich_notes(
        self,
        summary: RelationshipSummary,
        contact_id: str,
    ):
        """Enrich with recent notes."""
        try:
            notes = await self.hubspot.get_contact_notes(contact_id, limit=10)
            
            for note in notes:
                note_info = {
                    "date": note.get("hs_timestamp"),
                    "body": note.get("hs_note_body", "")[:500],  # Truncate
                }
                summary.recent_notes.append(note_info)
                
                # Extract key topics from notes
                body = note.get("hs_note_body", "").lower()
                topics = self._extract_topics(body)
                for topic in topics:
                    if topic not in summary.key_topics:
                        summary.key_topics.append(topic)
                        
        except Exception as e:
            logger.warning(f"Could not get notes: {e}")
    
    async def _enrich_tasks(
        self,
        summary: RelationshipSummary,
        contact_id: str,
    ):
        """Enrich with open tasks."""
        try:
            tasks = await self.hubspot.get_contact_tasks(contact_id)
            
            for task in tasks:
                status = task.get("hs_task_status", "").lower()
                if status not in ["completed", "cancelled"]:
                    task_info = {
                        "subject": task.get("hs_task_subject"),
                        "due_date": task.get("hs_task_due_date"),
                        "type": task.get("hs_task_type"),
                    }
                    summary.open_tasks.append(task_info)
                    
                    # Track as action item
                    subject = task.get("hs_task_subject", "")
                    if subject and subject not in summary.action_items:
                        summary.action_items.append(subject)
                        
        except Exception as e:
            logger.warning(f"Could not get tasks: {e}")
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract key topics from text."""
        topics = []
        
        # Look for common topic indicators
        topic_keywords = {
            "event": ["event", "conference", "trade show", "webinar"],
            "demand gen": ["pipeline", "lead gen", "demand", "mql"],
            "budget": ["budget", "pricing", "cost", "investment"],
            "timeline": ["timeline", "quarter", "q1", "q2", "q3", "q4", "deadline"],
            "competition": ["competitor", "alternative", "comparing"],
            "integration": ["integration", "api", "connect", "hubspot", "salesforce"],
        }
        
        for topic, keywords in topic_keywords.items():
            if any(kw in text for kw in keywords):
                topics.append(topic)
        
        return topics[:5]  # Max 5 topics
    
    def _determine_stage(self, summary: RelationshipSummary) -> str:
        """Determine relationship stage."""
        if summary.won_deals > 0:
            return "customer"
        
        if summary.active_deals > 0:
            return "opportunity"
        
        if summary.meetings_count > 0:
            return "engaged"
        
        if summary.total_touchpoints > 3:
            return "nurturing"
        
        if summary.total_touchpoints > 0:
            return "contacted"
        
        return "new"
    
    def _recommend_next_step(self, summary: RelationshipSummary) -> str:
        """Recommend next action based on history."""
        # Check for open tasks
        if summary.open_tasks:
            return f"Complete open task: {summary.open_tasks[0].get('subject', 'Follow up')}"
        
        # Check for active deals
        if summary.active_deals > 0:
            return "Check deal progress and send update"
        
        # Base on relationship stage
        stage_actions = {
            "customer": "Check in for expansion/referral opportunity",
            "opportunity": "Advance deal with proposal or meeting",
            "engaged": "Schedule discovery call or demo",
            "nurturing": "Send relevant content or case study",
            "contacted": "Follow up on previous outreach",
            "new": "Send personalized intro email",
        }
        
        return stage_actions.get(summary.relationship_stage, "Send outreach email")
    
    async def get_meeting_context(
        self,
        email: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get recent meeting summaries for context.
        
        Args:
            email: Contact email
            limit: Max meetings to return
            
        Returns:
            List of meeting summaries
        """
        meetings = []
        
        if not self.hubspot:
            return meetings
        
        try:
            contact = await self._get_contact(email, None)
            if not contact:
                return meetings
            
            contact_id = contact.get("id") or contact.get("hs_object_id")
            
            meeting_engagements = await self.hubspot.get_contact_meetings(contact_id, limit=limit)
            
            for meeting in meeting_engagements:
                meetings.append({
                    "date": meeting.get("hs_timestamp"),
                    "title": meeting.get("hs_meeting_title"),
                    "body": meeting.get("hs_meeting_body", "")[:1000],
                    "outcome": meeting.get("hs_meeting_outcome"),
                })
                
        except Exception as e:
            logger.error(f"Error getting meeting context: {e}")
        
        return meetings


# Singleton
_enricher: Optional[HistoryEnricher] = None


def get_history_enricher(hubspot_connector=None) -> HistoryEnricher:
    """Get singleton history enricher."""
    global _enricher
    if _enricher is None:
        _enricher = HistoryEnricher(hubspot_connector=hubspot_connector)
    return _enricher
