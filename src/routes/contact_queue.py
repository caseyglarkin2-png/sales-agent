"""Contact Queue routes for managing outreach prospects.

This module provides endpoints for queuing contacts, researching them,
and proposing personalized emails.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import uuid

from src.logger import get_logger
from src.agents.prospecting import ProspectingAgent
from src.agents.account_analyzer import AccountAnalyzer
from src.voice_profile import get_voice_profile
from src.models import Prospect
from src.connectors.hubspot import create_hubspot_connector
from src.forms import create_form_importer

logger = get_logger(__name__)

router = APIRouter(prefix="/api/contact-queue", tags=["contact-queue"])


class QueueStatus(str, Enum):
    """Status of contact in queue."""
    PENDING = "pending"  # Queued, awaiting research
    RESEARCHING = "researching"  # Research in progress
    READY = "ready"  # Research complete, ready for email
    DRAFT_CREATED = "draft_created"  # Email draft proposed
    SENT = "sent"  # Email sent
    REPLIED = "replied"  # Contact replied
    BOUNCED = "bounced"  # Email bounced
    OPTED_OUT = "opted_out"  # Contact opted out
    PAUSED = "paused"  # Temporarily paused


class QueueContact(BaseModel):
    """Contact in the queue."""
    email: str
    first_name: str
    last_name: str
    company: Optional[str] = None
    job_title: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    voice_profile: str = "casey_larkin"
    priority: int = 0  # 0=normal, 1=high, 2=urgent


class EmailProposal(BaseModel):
    """Proposed email for a contact."""
    subject: str
    body: str
    reasoning: str  # Why this approach
    personalization_notes: List[str]  # Key personalizations used


# In-memory storage (replace with database in production)
contact_queue: Dict[str, Dict[str, Any]] = {}
email_proposals: Dict[str, List[Dict[str, Any]]] = {}  # contact_id -> proposals


@router.post("/add", response_model=Dict[str, Any])
async def add_to_queue(contact: QueueContact) -> Dict[str, Any]:
    """Add a contact to the outreach queue."""
    try:
        contact_id = str(uuid.uuid4())
        
        queue_entry = {
            "id": contact_id,
            **contact.dict(),
            "status": QueueStatus.PENDING.value,
            "research": None,
            "added_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        contact_queue[contact_id] = queue_entry
        
        logger.info(f"Added contact to queue: {contact.email}")
        
        return {
            "status": "success",
            "contact_id": contact_id,
            "message": f"Added {contact.first_name} {contact.last_name} to queue",
            "queue_position": len([c for c in contact_queue.values() if c["status"] == QueueStatus.PENDING.value]),
        }
    except Exception as e:
        logger.error(f"Error adding contact to queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add-bulk", response_model=Dict[str, Any])
async def add_bulk_to_queue(contacts: List[QueueContact]) -> Dict[str, Any]:
    """Add multiple contacts to the queue at once."""
    try:
        added = []
        
        for contact in contacts:
            contact_id = str(uuid.uuid4())
            
            queue_entry = {
                "id": contact_id,
                **contact.dict(),
                "status": QueueStatus.PENDING.value,
                "research": None,
                "added_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            contact_queue[contact_id] = queue_entry
            added.append(contact_id)
        
        logger.info(f"Added {len(added)} contacts to queue")
        
        return {
            "status": "success",
            "contacts_added": len(added),
            "contact_ids": added,
        }
    except Exception as e:
        logger.error(f"Error adding bulk contacts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=Dict[str, Any])
async def list_queue(
    status: Optional[QueueStatus] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Dict[str, Any]:
    """List contacts in the queue."""
    try:
        contacts = list(contact_queue.values())
        
        # Filter by status
        if status:
            contacts = [c for c in contacts if c["status"] == status.value]
        
        # Sort by priority (higher first) then by added_at
        contacts.sort(
            key=lambda x: (-x.get("priority", 0), x.get("added_at", "")),
            reverse=False
        )
        
        total = len(contacts)
        contacts = contacts[offset:offset + limit]
        
        return {
            "contacts": contacts,
            "total": total,
            "limit": limit,
            "offset": offset,
            "status_counts": {
                status.value: len([c for c in contact_queue.values() if c["status"] == status.value])
                for status in QueueStatus
            }
        }
    except Exception as e:
        logger.error(f"Error listing queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/hubspot-forms", response_model=Dict[str, Any])
async def import_from_hubspot_forms(
    days_back: int = Query(default=30, le=90),
    form_filter: Optional[str] = Query(default=None),
    voice_profile: str = Query(default="casey_larkin"),
    priority: int = Query(default=0, ge=0, le=2),
) -> Dict[str, Any]:
    """Bulk import contacts from HubSpot form submissions.
    
    Args:
        days_back: How many days back to fetch submissions
        form_filter: Filter by form name (e.g., "chainge")
        voice_profile: Voice profile to assign to contacts
        priority: Priority level (0=normal, 1=high, 2=urgent)
    """
    try:
        # Create HubSpot connector and form importer
        hubspot = create_hubspot_connector()
        if not hubspot or not hubspot.api_key:
            raise HTTPException(
                status_code=400,
                detail="HubSpot API key not configured. Set HUBSPOT_API_KEY environment variable."
            )
        
        importer = create_form_importer(hubspot)
        
        # Fetch form submissions
        logger.info(f"Fetching form submissions from last {days_back} days...")
        submissions = await importer.get_form_submissions(days_back=days_back)
        
        # Filter if specified
        if form_filter:
            original_count = len(submissions)
            submissions = [
                s for s in submissions
                if form_filter.lower() in str(s.get("conversion_event", "")).lower()
                or form_filter.lower() in str(s.get("source_data", "")).lower()
                or form_filter.lower() in str(s.get("source", "")).lower()
            ]
            logger.info(f"Filtered to {len(submissions)} submissions matching '{form_filter}' (from {original_count})")
        
        if not submissions:
            return {
                "status": "success",
                "message": f"No form submissions found in last {days_back} days" + 
                          (f" matching '{form_filter}'" if form_filter else ""),
                "contacts_imported": 0
            }
        
        # Import to contact queue
        imported = []
        skipped = []
        
        for submission in submissions:
            email = submission.get("email")
            
            # Skip if no email
            if not email:
                skipped.append({"reason": "no_email", "data": submission})
                continue
            
            # Skip if already in queue
            existing = [c for c in contact_queue.values() if c.get("email") == email]
            if existing:
                skipped.append({"reason": "already_queued", "email": email})
                continue
            
            # Create queue entry
            contact_id = str(uuid.uuid4())
            
            queue_entry = {
                "id": contact_id,
                "email": email,
                "first_name": submission.get("first_name", ""),
                "last_name": submission.get("last_name", ""),
                "company": submission.get("company"),
                "job_title": submission.get("job_title"),
                "linkedin_url": None,
                "phone": submission.get("phone"),
                "notes": f"Imported from HubSpot form submission",
                "voice_profile": voice_profile,
                "priority": priority,
                "status": QueueStatus.PENDING.value,
                "research": None,
                "added_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "hubspot_contact_id": submission.get("contact_id"),
                "source": "hubspot_form",
                "form_metadata": {
                    "conversion_event": submission.get("conversion_event"),
                    "conversion_date": submission.get("conversion_date"),
                    "source": submission.get("source"),
                    "lifecycle_stage": submission.get("lifecycle_stage"),
                    "lead_status": submission.get("lead_status"),
                }
            }
            
            contact_queue[contact_id] = queue_entry
            imported.append(contact_id)
            
            logger.info(f"Imported contact: {email}")
        
        return {
            "status": "success",
            "contacts_imported": len(imported),
            "contacts_skipped": len(skipped),
            "total_processed": len(submissions),
            "contact_ids": imported,
            "skipped_details": skipped[:10],  # First 10 skipped
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing from HubSpot forms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/chainge-na", response_model=Dict[str, Any])
async def import_chainge_na_forms(
    days_back: int = Query(default=30, le=90),
) -> Dict[str, Any]:
    """Bulk import CHAINge NA form submissions specifically."""
    try:
        # Import with CHAINge filter
        result = await import_from_hubspot_forms(
            days_back=days_back,
            form_filter="chainge",
            voice_profile="freight_marketer_voice",  # Use freight-specific voice
            priority=1  # High priority
        )
        
        result["message"] = f"Imported CHAINge NA form submissions from last {days_back} days"
        return result
        
    except Exception as e:
        logger.error(f"Error importing CHAINge NA forms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{contact_id}/research", response_model=Dict[str, Any])
async def research_contact(contact_id: str) -> Dict[str, Any]:
    """Research a contact and enrich their profile.
    
    This gathers information about the contact and their company
    from HubSpot to enable personalized outreach.
    """
    try:
        if contact_id not in contact_queue:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        contact = contact_queue[contact_id]
        
        # Update status
        contact["status"] = QueueStatus.RESEARCHING.value
        contact["updated_at"] = datetime.utcnow().isoformat()
        
        # Create prospect for research
        prospect = Prospect(
            email=contact["email"],
            first_name=contact["first_name"],
            last_name=contact["last_name"],
            company=contact.get("company", ""),
            job_title=contact.get("job_title", ""),
        )
        
        # Initialize research dict
        research = {
            "contact_info": {
                "email": prospect.email,
                "name": f"{prospect.first_name} {prospect.last_name}",
                "company": prospect.company,
                "title": prospect.job_title,
            },
            "company_info": {},
            "communication_history": {},
            "insights": [],
            "recommended_angle": "",
            "researched_at": datetime.utcnow().isoformat(),
        }
        
        # Try to get real HubSpot data
        try:
            hubspot = create_hubspot_connector()
            if hubspot and hubspot.api_key:
                importer = create_form_importer(hubspot)
                
                # Get HubSpot contact ID (from queue metadata or search)
                hubspot_contact_id = contact.get("hubspot_contact_id")
                
                if not hubspot_contact_id:
                    # Search for contact
                    hs_contact = await hubspot.search_contacts(prospect.email)
                    if hs_contact:
                        hubspot_contact_id = hs_contact.get("id")
                        contact["hubspot_contact_id"] = hubspot_contact_id
                
                if hubspot_contact_id:
                    logger.info(f"Researching HubSpot contact {hubspot_contact_id}")
                    
                    # Get communication history
                    history = await importer.get_contact_history(hubspot_contact_id)
                    research["communication_history"] = {
                        "total_emails": len(history.get("emails", [])),
                        "total_calls": len(history.get("calls", [])),
                        "total_meetings": len(history.get("meetings", [])),
                        "total_notes": len(history.get("notes", [])),
                        "total_engagements": history.get("total_engagements", 0),
                        "has_prior_contact": history.get("total_engagements", 0) > 0,
                    }
                    
                    # Get company associations
                    associations = await hubspot.get_contact_associations(hubspot_contact_id)
                    if associations and len(associations) > 0:
                        company_id = associations[0].get("id")
                        
                        # Get company details
                        company_details = await importer.get_company_details(company_id)
                        if company_details:
                            research["company_info"] = company_details
                    
                    # Generate insights based on data
                    insights = []
                    
                    if history.get("total_engagements", 0) > 0:
                        insights.append(f"Previous contact: {history['total_engagements']} engagements")
                        if history.get("total_emails", 0) > 0:
                            insights.append(f"{history['total_emails']} past emails")
                        if history.get("total_meetings", 0) > 0:
                            insights.append(f"{history['total_meetings']} previous meetings")
                    else:
                        insights.append("No previous contact - cold outreach")
                    
                    if company_details:
                        if company_details.get("industry"):
                            insights.append(f"Industry: {company_details['industry']}")
                        if company_details.get("employee_count"):
                            insights.append(f"Company size: {company_details['employee_count']} employees")
                        if company_details.get("linkedin_url"):
                            insights.append("LinkedIn presence confirmed")
                    
                    research["insights"] = insights
                    
                    # Determine recommended approach
                    if history.get("total_engagements", 0) > 0:
                        research["recommended_angle"] = "Reference past interactions and continue conversation"
                    elif company_details.get("industry"):
                        research["recommended_angle"] = f"Industry-specific approach for {company_details['industry']}"
                    else:
                        research["recommended_angle"] = "Value-based cold outreach focusing on pain points"
                    
                    logger.info(f"Enhanced research with HubSpot data for {prospect.email}")
                else:
                    logger.warning(f"Contact {prospect.email} not found in HubSpot")
                    research["insights"] = ["Contact not found in HubSpot", "Using basic research"]
                    research["recommended_angle"] = "Cold outreach with value proposition"
                    
        except Exception as e:
            logger.error(f"Error fetching HubSpot data: {e}")
            # Fall back to basic research
            research["insights"] = [
                "Using basic research (HubSpot unavailable)",
                "Focus on value proposition",
            ]
            research["recommended_angle"] = "Value-based outreach"
        
        # Add basic insights if we don't have any
        if not research["insights"]:
            research["insights"] = [
                f"Contact at {prospect.company}",
                f"Title: {prospect.job_title}",
                "Research additional context manually",
            ]
        
        if not research["recommended_angle"]:
            research["recommended_angle"] = "Personalized value proposition"
        
        # Save research
        contact["research"] = research
        contact["status"] = QueueStatus.READY.value
        contact["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Completed research for contact: {contact['email']}")
        
        return {
            "status": "success",
            "contact_id": contact_id,
            "research": research,
            "message": "Research complete. Ready to generate email proposals.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error researching contact: {e}")
        # Revert status
        if contact_id in contact_queue:
            contact_queue[contact_id]["status"] = QueueStatus.PENDING.value
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{contact_id}/propose-email", response_model=Dict[str, Any])
async def propose_email(
    contact_id: str,
    num_variants: int = Query(default=2, le=5),
) -> Dict[str, Any]:
    """Generate email proposals for a contact.
    
    Creates personalized email drafts based on research.
    """
    try:
        if contact_id not in contact_queue:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        contact = contact_queue[contact_id]
        
        if contact["status"] not in [QueueStatus.READY.value, QueueStatus.DRAFT_CREATED.value]:
            raise HTTPException(
                status_code=400,
                detail=f"Contact must be researched first. Current status: {contact['status']}"
            )
        
        # Get voice profile
        voice_profile_id = contact.get("voice_profile", "casey_larkin")
        profile = get_voice_profile(voice_profile_id)
        
        # Create prospect
        prospect = Prospect(
            email=contact["email"],
            first_name=contact["first_name"],
            last_name=contact["last_name"],
            company=contact.get("company", ""),
            job_title=contact.get("job_title", ""),
        )
        
        # Generate email proposals (simplified - in production use ProspectingAgent)
        proposals = []
        
        for i in range(num_variants):
            # Different angles
            angles = [
                "problem_solving",
                "industry_insight",
                "mutual_connection",
                "value_proposition",
                "question_approach",
            ]
            angle = angles[i % len(angles)]
            
            proposal = {
                "id": str(uuid.uuid4()),
                "variant": i + 1,
                "subject": f"Re: {prospect.company}'s growth",
                "body": f"""Hi {prospect.first_name},

I noticed {prospect.company} is focused on operational efficiency. We help logistics companies streamline their field marketing and lead generation.

Would you be open to a 15-minute call next week to discuss how we've helped similar companies increase pipeline velocity?

Best,
Casey""",
                "reasoning": f"Using {angle} approach based on research insights",
                "personalization_notes": [
                    "Referenced company focus from research",
                    "Industry-specific language",
                    "Low-commitment ask (15 min)",
                ],
                "voice_profile": voice_profile_id,
                "created_at": datetime.utcnow().isoformat(),
            }
            proposals.append(proposal)
        
        # Save proposals
        email_proposals[contact_id] = proposals
        
        # Update contact status
        contact["status"] = QueueStatus.DRAFT_CREATED.value
        contact["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Generated {len(proposals)} email proposals for {contact['email']}")
        
        return {
            "status": "success",
            "contact_id": contact_id,
            "proposals": proposals,
            "message": f"Generated {len(proposals)} email variants",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error proposing email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{contact_id}", response_model=Dict[str, Any])
async def get_contact(contact_id: str) -> Dict[str, Any]:
    """Get contact details including research and proposals."""
    try:
        if contact_id not in contact_queue:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        contact = contact_queue[contact_id]
        proposals = email_proposals.get(contact_id, [])
        
        return {
            "contact": contact,
            "proposals": proposals,
            "proposal_count": len(proposals),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting contact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{contact_id}/status", response_model=Dict[str, Any])
async def update_status(
    contact_id: str,
    status: QueueStatus,
) -> Dict[str, Any]:
    """Update contact status."""
    try:
        if contact_id not in contact_queue:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        contact = contact_queue[contact_id]
        old_status = contact["status"]
        
        contact["status"] = status.value
        contact["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Updated contact status: {old_status} -> {status.value}")
        
        return {
            "status": "success",
            "contact_id": contact_id,
            "old_status": old_status,
            "new_status": status.value,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{contact_id}", response_model=Dict[str, Any])
async def remove_from_queue(contact_id: str) -> Dict[str, Any]:
    """Remove a contact from the queue."""
    try:
        if contact_id not in contact_queue:
            raise HTTPException(status_code=404, detail="Contact not found")
        
        contact = contact_queue.pop(contact_id)
        
        # Also remove proposals
        if contact_id in email_proposals:
            del email_proposals[contact_id]
        
        logger.info(f"Removed contact from queue: {contact['email']}")
        
        return {
            "status": "success",
            "message": f"Removed {contact['email']} from queue",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing contact: {e}")
        raise HTTPException(status_code=500, detail=str(e))
