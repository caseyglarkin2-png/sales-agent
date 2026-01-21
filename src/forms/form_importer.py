"""HubSpot Form Submission Importer.

Fetches form submissions from HubSpot and processes them for outreach.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx

from src.logger import get_logger
from src.connectors.hubspot import HubSpotConnector
from src.models import Prospect

logger = get_logger(__name__)


class FormSubmissionImporter:
    """Imports form submissions from HubSpot."""
    
    def __init__(self, hubspot_connector: HubSpotConnector):
        """Initialize importer with HubSpot connector."""
        self.hubspot = hubspot_connector
    
    async def get_form_submissions(
        self,
        form_guid: Optional[str] = None,
        days_back: int = 30,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetch form submissions from HubSpot.
        
        Args:
            form_guid: Specific form GUID (optional - fetches all if not provided)
            days_back: How many days back to fetch
            limit: Maximum submissions to fetch
            
        Returns:
            List of form submission objects
        """
        submissions = []
        
        try:
            # Calculate timestamp for filtering
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            cutoff_timestamp = int(cutoff_date.timestamp() * 1000)  # HubSpot uses milliseconds
            
            async with httpx.AsyncClient(timeout=30) as client:
                # HubSpot Form Submissions API
                # https://developers.hubspot.com/docs/api/marketing/forms
                
                if form_guid:
                    # Get submissions for specific form
                    url = f"{self.hubspot.BASE_URL}/form-integrations/v1/submissions/forms/{form_guid}"
                else:
                    # Get all recent submissions (via contacts that recently converted)
                    # Using contact search with recent_conversion_date filter
                    url = f"{self.hubspot.BASE_URL}/crm/v3/objects/contacts/search"
                    payload = {
                        "filterGroups": [{
                            "filters": [{
                                "propertyName": "recent_conversion_date",
                                "operator": "GTE",
                                "value": str(cutoff_timestamp)
                            }]
                        }],
                        "properties": [
                            "email", "firstname", "lastname", "company",
                            "jobtitle", "phone", "website", "industry",
                            "recent_conversion_date", "recent_conversion_event_name",
                            "hs_analytics_source", "hs_analytics_source_data_1",
                            "lifecyclestage", "hs_lead_status"
                        ],
                        "limit": limit
                    }
                    
                    response = await client.post(
                        url,
                        headers=self.hubspot.headers,
                        json=payload
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for contact in data.get("results", []):
                        props = contact.get("properties", {})
                        submission = {
                            "contact_id": contact.get("id"),
                            "email": props.get("email"),
                            "first_name": props.get("firstname", ""),
                            "last_name": props.get("lastname", ""),
                            "company": props.get("company", ""),
                            "job_title": props.get("jobtitle", ""),
                            "phone": props.get("phone"),
                            "website": props.get("website"),
                            "industry": props.get("industry"),
                            "conversion_date": props.get("recent_conversion_date"),
                            "conversion_event": props.get("recent_conversion_event_name"),
                            "source": props.get("hs_analytics_source"),
                            "source_data": props.get("hs_analytics_source_data_1"),
                            "lifecycle_stage": props.get("lifecyclestage"),
                            "lead_status": props.get("hs_lead_status"),
                        }
                        submissions.append(submission)
                    
                    logger.info(f"Fetched {len(submissions)} form submissions from HubSpot")
                    return submissions
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching form submissions: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Error fetching form submissions: {e}")
        
        return submissions
    
    async def get_chainge_na_submissions(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get CHAINge NA form submissions specifically.
        
        This fetches contacts who submitted the CHAINge NA form.
        You'll need to find the form GUID from HubSpot.
        """
        # Method 1: Use form-specific endpoint if you have the GUID
        # form_guid = "YOUR_CHAINGE_NA_FORM_GUID"
        # return await self.get_form_submissions(form_guid=form_guid, days_back=days_back)
        
        # Method 2: Filter by form name in conversion event
        all_submissions = await self.get_form_submissions(days_back=days_back)
        
        # Filter for CHAINge NA related submissions
        chainge_submissions = [
            s for s in all_submissions
            if s.get("conversion_event") and "chainge" in s.get("conversion_event", "").lower()
            or s.get("source_data") and "chainge" in s.get("source_data", "").lower()
        ]
        
        logger.info(f"Found {len(chainge_submissions)} CHAINge NA form submissions")
        return chainge_submissions
    
    def submission_to_prospect(self, submission: Dict[str, Any]) -> Prospect:
        """Convert form submission to Prospect model."""
        return Prospect(
            email=submission.get("email", ""),
            first_name=submission.get("first_name", ""),
            last_name=submission.get("last_name", ""),
            company=submission.get("company", ""),
            job_title=submission.get("job_title", ""),
            phone=submission.get("phone"),
        )
    
    async def get_contact_history(self, contact_id: str) -> Dict[str, Any]:
        """Get communication history for a contact.
        
        Args:
            contact_id: HubSpot contact ID
            
        Returns:
            Dict with emails, calls, meetings, notes
        """
        history = {
            "emails": [],
            "calls": [],
            "meetings": [],
            "notes": [],
            "last_contact_date": None,
            "total_engagements": 0,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Get email engagements
                response = await client.get(
                    f"{self.hubspot.BASE_URL}/crm/v3/objects/contacts/{contact_id}/associations/emails",
                    headers=self.hubspot.headers
                )
                
                if response.status_code == 200:
                    email_associations = response.json().get("results", [])
                    history["emails"] = [{"id": e.get("id")} for e in email_associations]
                
                # Get call engagements
                response = await client.get(
                    f"{self.hubspot.BASE_URL}/crm/v3/objects/contacts/{contact_id}/associations/calls",
                    headers=self.hubspot.headers
                )
                
                if response.status_code == 200:
                    call_associations = response.json().get("results", [])
                    history["calls"] = [{"id": c.get("id")} for c in call_associations]
                
                # Get meetings
                response = await client.get(
                    f"{self.hubspot.BASE_URL}/crm/v3/objects/contacts/{contact_id}/associations/meetings",
                    headers=self.hubspot.headers
                )
                
                if response.status_code == 200:
                    meeting_associations = response.json().get("results", [])
                    history["meetings"] = [{"id": m.get("id")} for m in meeting_associations]
                
                # Get notes
                response = await client.get(
                    f"{self.hubspot.BASE_URL}/crm/v3/objects/contacts/{contact_id}/associations/notes",
                    headers=self.hubspot.headers
                )
                
                if response.status_code == 200:
                    note_associations = response.json().get("results", [])
                    history["notes"] = [{"id": n.get("id")} for n in note_associations]
                
                history["total_engagements"] = (
                    len(history["emails"]) +
                    len(history["calls"]) +
                    len(history["meetings"]) +
                    len(history["notes"])
                )
                
                logger.info(f"Retrieved {history['total_engagements']} engagements for contact {contact_id}")
                
        except Exception as e:
            logger.error(f"Error fetching contact history: {e}")
        
        return history
    
    async def get_company_details(self, company_id: str) -> Dict[str, Any]:
        """Get detailed company information.
        
        Args:
            company_id: HubSpot company ID
            
        Returns:
            Company details dict
        """
        try:
            company = await self.hubspot.get_company(company_id)
            
            if company:
                props = company.get("properties", {})
                return {
                    "id": company_id,
                    "name": props.get("name"),
                    "domain": props.get("domain"),
                    "industry": props.get("industry"),
                    "description": props.get("description"),
                    "phone": props.get("phone"),
                    "city": props.get("city"),
                    "state": props.get("state"),
                    "country": props.get("country"),
                    "employee_count": props.get("numberofemployees"),
                    "annual_revenue": props.get("annualrevenue"),
                    "linkedin_url": props.get("linkedin_company_page"),
                    "website": props.get("website"),
                    "type": props.get("type"),
                    "founded_year": props.get("founded_year"),
                }
        except Exception as e:
            logger.error(f"Error fetching company details: {e}")
        
        return {}
    
    async def import_to_contact_queue(
        self,
        form_name: str = "CHAINge NA",
        limit: int = 50,
        days_back: int = 90,
        voice_profile: str = "freight_marketer_voice",
    ) -> Dict[str, Any]:
        """Import form submissions to contact queue.
        
        This is the main workflow method that:
        1. Fetches form submissions
        2. Enriches with contact history
        3. Adds to contact queue for outreach
        
        Returns summary of import operation.
        """
        from src.routes.contact_queue import contact_queue, QueueStatus
        import uuid
        from datetime import datetime
        
        logger.info(f"Importing {form_name} submissions to contact queue")
        
        # Get submissions - use None for form_guid to get all recent submissions
        # Then filter by form name
        submissions = await self.get_form_submissions(
            form_guid=None,  # Get all recent form submissions
            limit=limit * 2,  # Get more to account for filtering
            days_back=days_back
        )
        
        # Filter by form name if we can
        if form_name:
            filtered = []
            for s in submissions:
                props = s.get("properties", {})
                conversion_event = props.get("recent_conversion_event_name", "")
                source_data = props.get("hs_analytics_source_data_1", "")
                
                # Check if form name appears in conversion event or source
                if (form_name.lower() in conversion_event.lower() or
                    form_name.lower() in source_data.lower()):
                    filtered.append(s)
            
            submissions = filtered[:limit]
        
        if not submissions:
            return {
                "imported": 0,
                "skipped": 0,
                "message": f"No {form_name} submissions found"
            }
        
        imported = 0
        skipped = 0
        errors = []
        
        for submission in submissions:
            try:
                # Extract contact data
                props = submission.get("properties", {})
                email = props.get("email", "")
                
                if not email:
                    skipped += 1
                    continue
                
                # Check if already in queue
                existing = [c for c in contact_queue.values() if c["email"] == email]
                if existing:
                    skipped += 1
                    continue
                
                # Get contact history (use email as fallback)
                history = await self.get_contact_history(email)
                
                # Create queue entry
                contact_id = str(uuid.uuid4())
                queue_entry = {
                    "id": contact_id,
                    "email": email,
                    "first_name": props.get("firstname", ""),
                    "last_name": props.get("lastname", ""),
                    "company": props.get("company", ""),
                    "job_title": props.get("jobtitle", ""),
                    "phone": props.get("phone", ""),
                    "linkedin_url": props.get("linkedin_url", ""),
                    "notes": f"Imported from {form_name} form",
                    "voice_profile": voice_profile,
                    "priority": 0,
                    "status": QueueStatus.PENDING.value,
                    "research": None,
                    "form_submission": submission,
                    "contact_history": history,
                    "added_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
                
                contact_queue[contact_id] = queue_entry
                imported += 1
                
                logger.info(f"Imported {email} to queue (ID: {contact_id})")
                
            except Exception as e:
                logger.error(f"Error importing submission: {e}")
                errors.append(str(e))
                skipped += 1
        
        return {
            "imported": imported,
            "skipped": skipped,
            "total_submissions": len(submissions),
            "errors": errors if errors else None,
        }


def create_form_importer(hubspot_connector: HubSpotConnector) -> FormSubmissionImporter:
    """Create a form importer instance."""
    return FormSubmissionImporter(hubspot_connector)
