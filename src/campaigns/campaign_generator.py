"""
Campaign Email Generator
========================

Production-ready campaign email generator that creates personalized drafts
for HubSpot contact segments with template-based personalization.

Features:
- Segment-based campaign generation (CHAINge, High Value, Cold)
- Template personalization with {{firstname}}, {{company}} variables
- Integration with DraftGenerator for AI-powered emails
- Batch processing with rate limiting
- Draft queueing for operator approval
- Industry-specific talking points
- Meeting slot integration
- Campaign analytics and tracking

Usage:
    generator = CampaignGenerator()
    result = await generator.generate_for_segment("chainge", limit=50)
    # Returns: {"drafts_created": 50, "queued_for_approval": 50, "errors": 0}
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from src.draft_generator import DraftGenerator, create_draft_generator
from src.operator_mode import DraftQueue, get_draft_queue
from src.hubspot_sync import (
    HubSpotContactSyncService,
    get_sync_service,
    ContactSegment
)
from src.voice_profile import get_voice_profile

logger = logging.getLogger(__name__)


class CampaignSegment(str, Enum):
    """Available campaign segments matching HubSpot contact segments."""
    CHAINGE = "chainge"
    HIGH_VALUE = "high_value"
    ENGAGED = "engaged"
    COLD = "cold"
    ALL = "all"


class CampaignStats:
    """Campaign generation statistics."""
    
    def __init__(self):
        self.drafts_created: int = 0
        self.queued_for_approval: int = 0
        self.errors: int = 0
        self.contacts_processed: int = 0
        self.start_time: datetime = datetime.now(timezone.utc)
        self.segment: Optional[str] = None
        self.error_details: List[Dict[str, str]] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        return {
            "drafts_created": self.drafts_created,
            "queued_for_approval": self.queued_for_approval,
            "errors": self.errors,
            "contacts_processed": self.contacts_processed,
            "segment": self.segment,
            "duration_seconds": round(duration, 2),
            "error_details": self.error_details if self.errors > 0 else None,
        }


# Email templates for different segments
EMAIL_TEMPLATES = {
    CampaignSegment.CHAINGE: {
        "subject": "Re: CHAINge NA — Partnership Opportunity",
        "body": """Hi {{firstname}},

I saw you registered for CHAINge NA — exciting! We're working with several attendees to help them maximize their networking ROI before the event.

{{company}} is in a great position to leverage partnerships in this space. I'd love to share what we've seen work for similar companies and see if there's a fit.

{{meeting_slots}}

Looking forward to connecting!

{{signature}}

P.S. We recently helped another CHAINge attendee 3x their partnership pipeline in 90 days. Happy to share the approach.""",
        "talking_points": [
            "Partnership ecosystem opportunities at CHAINge",
            "Networking ROI maximization strategies",
            "Event-specific collaboration approaches"
        ]
    },
    
    CampaignSegment.HIGH_VALUE: {
        "subject": "Quick question about {{company}}'s growth",
        "body": """Hi {{firstname}},

I've been following {{company}}'s growth in {{industry}} and wanted to reach out.

We're helping similar enterprises unlock 10-20% revenue growth through better sales orchestration and AI-powered outreach. Given your scale, this could translate to significant impact.

{{meeting_slots}}

Worth a quick conversation?

{{signature}}

P.S. Our typical ROI is 5:1 in the first quarter — happy to walk through the numbers.""",
        "talking_points": [
            "Enterprise-scale revenue optimization",
            "ROI-focused sales automation",
            "Competitive advantage through AI orchestration"
        ]
    },
    
    CampaignSegment.ENGAGED: {
        "subject": "Following up on your interest",
        "body": """Hi {{firstname}},

Thanks for your interest in learning more about what we're building!

I wanted to see if you'd like to dive deeper into how we can help {{company}} with {{pain_point}}. We've seen strong results with companies at your stage.

{{meeting_slots}}

Does one of these times work for you?

{{signature}}""",
        "talking_points": [
            "Active interest follow-up",
            "Stage-appropriate solutions",
            "Recent success stories"
        ]
    },
    
    CampaignSegment.COLD: {
        "subject": "Catching up — {{company}} updates?",
        "body": """Hi {{firstname}},

It's been a while since we last connected about {{company}}.

Wanted to check in — are you still looking at ways to improve {{pain_point}}? We've rolled out some new capabilities that might be a better fit now.

{{meeting_slots}}

Let me know if you'd like a quick update on what's changed.

{{signature}}

P.S. No pressure if timing isn't right — happy to reconnect whenever makes sense.""",
        "talking_points": [
            "Re-engagement approach",
            "New capabilities since last contact",
            "Low-pressure reconnection"
        ]
    },
}


# Industry-specific pain points for personalization
INDUSTRY_PAIN_POINTS = {
    "technology": "scaling sales operations efficiently",
    "software": "pipeline velocity and conversion rates",
    "saas": "customer acquisition costs and retention",
    "finance": "compliance while maintaining growth",
    "consulting": "client relationship management",
    "healthcare": "patient engagement and retention",
    "manufacturing": "supply chain optimization",
    "retail": "customer experience and loyalty",
    "real estate": "deal flow management",
    "education": "student engagement and enrollment",
    "default": "revenue growth and operational efficiency"
}


class CampaignGenerator:
    """
    Campaign email generator with personalization and queuing.
    
    Integrates with:
    - HubSpotContactSyncService for contact data
    - DraftGenerator for AI-powered email generation
    - DraftQueue for operator approval workflow
    """
    
    def __init__(
        self,
        draft_generator: Optional[DraftGenerator] = None,
        draft_queue: Optional[DraftQueue] = None,
        sync_service: Optional[HubSpotContactSyncService] = None
    ):
        """
        Initialize campaign generator.
        
        Args:
            draft_generator: Email draft generator (defaults to singleton)
            draft_queue: Draft approval queue (defaults to singleton)
            sync_service: HubSpot sync service (defaults to singleton)
        """
        self.draft_generator = draft_generator or create_draft_generator()
        self.draft_queue = draft_queue or get_draft_queue()
        self.sync_service = sync_service or get_sync_service()
        self.voice_profile = get_voice_profile()
        
        logger.info("Campaign generator initialized")
    
    async def generate_for_segment(
        self,
        segment_name: str,
        limit: int = 50,
        auto_queue: bool = True,
        batch_size: int = 10,
    ) -> Dict[str, Any]:
        """
        Generate campaign drafts for a specific segment.
        
        Args:
            segment_name: Segment to target (chainge, high_value, engaged, cold, all)
            limit: Max number of drafts to generate
            auto_queue: Automatically queue drafts for approval
            batch_size: Number of drafts to generate concurrently
            
        Returns:
            Campaign statistics dictionary
        """
        stats = CampaignStats()
        stats.segment = segment_name
        
        logger.info(f"Starting campaign generation for segment: {segment_name}, limit: {limit}")
        
        try:
            # Validate segment
            if segment_name not in [s.value for s in CampaignSegment]:
                raise ValueError(f"Invalid segment: {segment_name}. Must be one of: {', '.join([s.value for s in CampaignSegment])}")
            
            # Get contacts for segment
            contacts = self._get_segment_contacts(segment_name, limit)
            
            if not contacts:
                logger.warning(f"No contacts found for segment: {segment_name}")
                return stats.to_dict()
            
            logger.info(f"Found {len(contacts)} contacts for segment: {segment_name}")
            
            # Generate drafts in batches to avoid rate limits
            for i in range(0, len(contacts), batch_size):
                batch = contacts[i:i + batch_size]
                logger.info(f"Processing batch {i // batch_size + 1}/{(len(contacts) + batch_size - 1) // batch_size}")
                
                # Generate drafts concurrently within batch
                tasks = [
                    self._generate_contact_draft(contact, segment_name, auto_queue, stats)
                    for contact in batch
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Small delay between batches to avoid rate limiting
                if i + batch_size < len(contacts):
                    await asyncio.sleep(1)
            
            logger.info(
                f"Campaign generation complete: {stats.drafts_created} drafts created, "
                f"{stats.errors} errors, segment={segment_name}"
            )
            
            return stats.to_dict()
            
        except Exception as e:
            logger.error(f"Campaign generation failed for segment {segment_name}: {e}")
            stats.errors += 1
            stats.error_details.append({
                "error": str(e),
                "segment": segment_name
            })
            return stats.to_dict()
    
    async def generate_for_contacts(
        self,
        contact_list: List[Dict[str, Any]],
        segment_name: Optional[str] = None,
        auto_queue: bool = True,
        batch_size: int = 10,
    ) -> Dict[str, Any]:
        """
        Generate campaign drafts for a specific list of contacts.
        
        Args:
            contact_list: List of contact dictionaries
            segment_name: Optional segment name for template selection
            auto_queue: Automatically queue drafts for approval
            batch_size: Number of drafts to generate concurrently
            
        Returns:
            Campaign statistics dictionary
        """
        stats = CampaignStats()
        stats.segment = segment_name or "custom_list"
        
        logger.info(f"Starting campaign generation for {len(contact_list)} contacts")
        
        try:
            # Determine segment for each contact if not specified
            effective_segment = segment_name or CampaignSegment.ENGAGED.value
            
            # Generate drafts in batches
            for i in range(0, len(contact_list), batch_size):
                batch = contact_list[i:i + batch_size]
                logger.info(f"Processing batch {i // batch_size + 1}/{(len(contact_list) + batch_size - 1) // batch_size}")
                
                tasks = [
                    self._generate_contact_draft(contact, effective_segment, auto_queue, stats)
                    for contact in batch
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
                
                if i + batch_size < len(contact_list):
                    await asyncio.sleep(1)
            
            logger.info(
                f"Custom list campaign complete: {stats.drafts_created} drafts created, "
                f"{stats.errors} errors"
            )
            
            return stats.to_dict()
            
        except Exception as e:
            logger.error(f"Campaign generation failed for contact list: {e}")
            stats.errors += 1
            stats.error_details.append({
                "error": str(e),
                "type": "custom_list"
            })
            return stats.to_dict()
    
    async def _generate_contact_draft(
        self,
        contact: Dict[str, Any],
        segment_name: str,
        auto_queue: bool,
        stats: CampaignStats
    ) -> None:
        """
        Generate a draft for a single contact.
        
        Args:
            contact: Contact data dictionary
            segment_name: Segment name for template selection
            auto_queue: Queue draft for approval
            stats: Campaign statistics to update
        """
        try:
            stats.contacts_processed += 1
            
            email = contact.get("email")
            if not email:
                logger.warning(f"Skipping contact without email: {contact}")
                stats.errors += 1
                return
            
            # Get template for segment
            template = self._get_template(segment_name)
            
            # Personalize email
            personalized = self.personalize_email(contact, template["body"])
            personalized_subject = self.personalize_email(contact, template["subject"])
            
            # Generate meeting slots
            meeting_slots = self._generate_meeting_slots()
            
            # Get talking points
            talking_points = template.get("talking_points", [])
            
            # Add personalization hooks
            personalization_hooks = self._get_personalization_hooks(contact)
            
            # Generate draft using DraftGenerator
            draft_result = await self.draft_generator.generate_draft(
                prospect_email=email,
                prospect_name=contact.get("firstname", "there"),
                company_name=contact.get("company", "your company"),
                thread_context=None,  # Initial outreach
                meeting_slots=meeting_slots,
                asset_link=None,
                voice_profile=self.voice_profile,
                talking_points=talking_points,
                personalization_hooks=personalization_hooks,
            )
            
            # Check if draft was blocked by PII detector
            if draft_result.get("blocked"):
                logger.warning(f"Draft blocked for {email}: {draft_result.get('pii_safety')}")
                stats.errors += 1
                stats.error_details.append({
                    "email": email,
                    "error": "PII safety block",
                    "details": str(draft_result.get('pii_safety'))
                })
                return
            
            # Create draft ID
            draft_id = str(uuid.uuid4())
            
            # Create draft in queue
            if auto_queue:
                await self.draft_queue.create_draft(
                    draft_id=draft_id,
                    recipient=email,
                    subject=draft_result["subject"],
                    body=draft_result["body"],
                    metadata={
                        "segment": segment_name,
                        "campaign": f"{segment_name}_campaign_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                        "contact_id": contact.get("hubspot_id"),
                        "company_name": contact.get("company"),
                        "firstname": contact.get("firstname"),
                        "model": draft_result.get("model"),
                        "voice_profile": draft_result.get("voice_profile"),
                        "tokens_used": draft_result.get("tokens_used", 0),
                    },
                    contact_id=contact.get("hubspot_id"),
                    company_name=contact.get("company"),
                )
                stats.queued_for_approval += 1
            
            stats.drafts_created += 1
            logger.debug(f"Draft created for {email} (segment: {segment_name})")
            
        except Exception as e:
            logger.error(f"Failed to generate draft for {contact.get('email')}: {e}")
            stats.errors += 1
            stats.error_details.append({
                "email": contact.get("email"),
                "error": str(e)
            })
    
    def personalize_email(self, contact: Dict[str, Any], template: str) -> str:
        """
        Personalize email template with contact data.
        
        Replaces variables:
        - {{firstname}} -> contact.firstname
        - {{lastname}} -> contact.lastname
        - {{company}} -> contact.company
        - {{jobtitle}} -> contact.jobtitle
        - {{industry}} -> detected industry
        - {{pain_point}} -> industry-specific pain point
        - {{signature}} -> voice profile signature
        - {{meeting_slots}} -> formatted meeting slots
        
        Args:
            contact: Contact data dictionary
            template: Email template string with {{variables}}
            
        Returns:
            Personalized email text
        """
        # Extract contact data with defaults
        firstname = contact.get("firstname") or "there"
        lastname = contact.get("lastname") or ""
        company = contact.get("company") or "your company"
        jobtitle = contact.get("jobtitle") or "your role"
        
        # Detect industry from company name
        industry = self._detect_industry(company)
        pain_point = INDUSTRY_PAIN_POINTS.get(industry, INDUSTRY_PAIN_POINTS["default"])
        
        # Replace variables
        result = template
        result = result.replace("{{firstname}}", firstname)
        result = result.replace("{{lastname}}", lastname)
        result = result.replace("{{company}}", company)
        result = result.replace("{{jobtitle}}", jobtitle)
        result = result.replace("{{industry}}", industry)
        result = result.replace("{{pain_point}}", pain_point)
        result = result.replace("{{signature}}", self.voice_profile.signature_style)
        
        # Remove meeting slots placeholder (will be added by DraftGenerator)
        result = result.replace("{{meeting_slots}}\n\n", "")
        result = result.replace("{{meeting_slots}}", "")
        
        return result
    
    async def queue_all_drafts(self) -> Dict[str, Any]:
        """
        Queue all generated drafts for operator approval.
        
        Note: Drafts are already queued during generation if auto_queue=True.
        This method is for queuing drafts that were generated without auto_queue.
        
        Returns:
            Statistics on queued drafts
        """
        try:
            pending = await self.draft_queue.get_pending_approvals()
            
            return {
                "total_pending": len(pending),
                "status": "success",
                "message": f"{len(pending)} drafts pending approval"
            }
            
        except Exception as e:
            logger.error(f"Failed to queue drafts: {e}")
            return {
                "total_pending": 0,
                "status": "error",
                "message": str(e)
            }
    
    def _get_segment_contacts(
        self,
        segment_name: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Get contacts for a specific segment from HubSpot sync.
        
        Args:
            segment_name: Segment to filter by
            limit: Max number of contacts to return
            
        Returns:
            List of contact dictionaries
        """
        if segment_name == CampaignSegment.ALL.value:
            # Get all contacts regardless of segment
            result = self.sync_service.get_contacts(
                segment=None,
                limit=limit,
                offset=0
            )
        else:
            # Get contacts for specific segment
            result = self.sync_service.get_contacts(
                segment=segment_name,
                limit=limit,
                offset=0
            )
        
        return result.get("contacts", [])
    
    def _get_template(self, segment_name: str) -> Dict[str, Any]:
        """
        Get email template for segment.
        
        Args:
            segment_name: Segment name
            
        Returns:
            Template dictionary with subject, body, talking_points
        """
        # Map segment to template
        if segment_name == CampaignSegment.CHAINGE.value:
            return EMAIL_TEMPLATES[CampaignSegment.CHAINGE]
        elif segment_name == CampaignSegment.HIGH_VALUE.value:
            return EMAIL_TEMPLATES[CampaignSegment.HIGH_VALUE]
        elif segment_name == CampaignSegment.ENGAGED.value:
            return EMAIL_TEMPLATES[CampaignSegment.ENGAGED]
        elif segment_name == CampaignSegment.COLD.value:
            return EMAIL_TEMPLATES[CampaignSegment.COLD]
        else:
            # Default to engaged template
            return EMAIL_TEMPLATES[CampaignSegment.ENGAGED]
    
    def _generate_meeting_slots(self) -> List[Dict[str, Any]]:
        """
        Generate meeting time slots for next week.
        
        Returns:
            List of meeting slot dictionaries
        """
        slots = []
        now = datetime.now(timezone.utc)
        
        # Generate 3 slots over next 5 business days
        # Slots at 10am, 2pm, 4pm ET
        base_date = now + timedelta(days=1)
        
        slot_times = [
            {"hour": 10, "label": "10am ET"},
            {"hour": 14, "label": "2pm ET"},
            {"hour": 16, "label": "4pm ET"},
        ]
        
        for i, slot_time in enumerate(slot_times):
            slot_date = base_date + timedelta(days=i)
            
            # Skip weekends
            while slot_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
                slot_date += timedelta(days=1)
            
            slot_datetime = slot_date.replace(
                hour=slot_time["hour"],
                minute=0,
                second=0,
                microsecond=0
            )
            
            slots.append({
                "start": slot_datetime.isoformat(),
                "display": f"{slot_date.strftime('%A, %B %d')} at {slot_time['label']}"
            })
        
        return slots
    
    def _detect_industry(self, company_name: str) -> str:
        """
        Detect industry from company name.
        
        Simple keyword-based detection. Could be enhanced with ML or external APIs.
        
        Args:
            company_name: Company name
            
        Returns:
            Industry name (lowercase)
        """
        company_lower = company_name.lower()
        
        if any(word in company_lower for word in ["tech", "software", "app", "digital", "cyber"]):
            return "technology"
        elif any(word in company_lower for word in ["saas", "cloud", "platform"]):
            return "saas"
        elif any(word in company_lower for word in ["finance", "bank", "capital", "invest"]):
            return "finance"
        elif any(word in company_lower for word in ["consult", "advisory", "strategy"]):
            return "consulting"
        elif any(word in company_lower for word in ["health", "medical", "pharma", "clinic"]):
            return "healthcare"
        elif any(word in company_lower for word in ["manufact", "industrial", "factory"]):
            return "manufacturing"
        elif any(word in company_lower for word in ["retail", "store", "shop", "commerce"]):
            return "retail"
        elif any(word in company_lower for word in ["real estate", "property", "realty"]):
            return "real estate"
        elif any(word in company_lower for word in ["education", "school", "university", "learning"]):
            return "education"
        else:
            return "default"
    
    def _get_personalization_hooks(self, contact: Dict[str, Any]) -> List[str]:
        """
        Generate personalization hooks based on contact data.
        
        Args:
            contact: Contact data dictionary
            
        Returns:
            List of personalization suggestions
        """
        hooks = []
        
        # Company-based hook
        company = contact.get("company")
        if company:
            hooks.append(f"Reference {company}'s position in their industry")
        
        # Role-based hook
        jobtitle = contact.get("jobtitle")
        if jobtitle:
            if any(word in jobtitle.lower() for word in ["ceo", "founder", "chief"]):
                hooks.append("Speak to strategic growth and competitive positioning")
            elif any(word in jobtitle.lower() for word in ["sales", "revenue", "business development"]):
                hooks.append("Focus on pipeline growth and sales efficiency")
            elif any(word in jobtitle.lower() for word in ["marketing", "growth"]):
                hooks.append("Emphasize lead generation and conversion optimization")
            elif any(word in jobtitle.lower() for word in ["operations", "ops"]):
                hooks.append("Highlight automation and operational efficiency")
        
        # Segment-based hooks
        segments = contact.get("segments", [])
        if ContactSegment.CHAINGE in segments:
            hooks.append("Mention CHAINge event and networking opportunities")
        if ContactSegment.HIGH_VALUE in segments:
            hooks.append("Lead with ROI and enterprise-scale impact")
        if ContactSegment.COLD in segments:
            hooks.append("Use soft re-engagement tone, mention what's new")
        
        return hooks


# Factory function
def create_campaign_generator() -> CampaignGenerator:
    """
    Create a campaign generator with default dependencies.
    
    Returns:
        CampaignGenerator instance
    """
    return CampaignGenerator()
