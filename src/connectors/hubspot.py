"""HubSpot connector for CRM integration."""
import os
from typing import Any, Dict, List, Optional

import httpx

from src.logger import get_logger

logger = get_logger(__name__)


def create_hubspot_connector() -> "HubSpotConnector":
    """Create a HubSpotConnector with API key from environment.
    
    Looks for HUBSPOT_API_KEY environment variable.
    """
    api_key = os.environ.get("HUBSPOT_API_KEY", "")
    if not api_key:
        logger.warning("HUBSPOT_API_KEY not set, HubSpot connector will fail on API calls")
    return HubSpotConnector(api_key=api_key)


class HubSpotConnector:
    """Connector for HubSpot API."""

    BASE_URL = "https://api.hubapi.com"

    def __init__(self, api_key: str):
        """Initialize HubSpot connector."""
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def search_contacts(self, email: str) -> Optional[Dict[str, Any]]:
        """Search for a contact by email address."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "filterGroups": [
                        {
                            "filters": [
                                {
                                    "propertyName": "email",
                                    "operator": "EQ",
                                    "value": email
                                }
                            ]
                        }
                    ],
                    "limit": 1
                }
                response = await client.post(
                    f"{self.BASE_URL}/crm/v3/objects/contacts/search",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                results = response.json()
                if results.get("results"):
                    contact = results["results"][0]
                    logger.info(f"Found contact {contact['id']} with email {email}")
                    return contact
                logger.info(f"No contact found with email {email}")
                return None
            except Exception as e:
                logger.error(f"Error searching contacts by email: {e}")
                return None

    async def search_companies(self, domain: str) -> Optional[Dict[str, Any]]:
        """Search for a company by domain."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "filterGroups": [
                        {
                            "filters": [
                                {
                                    "propertyName": "hs_lead_status",
                                    "operator": "EQ",
                                    "value": domain
                                }
                            ]
                        }
                    ],
                    "limit": 1
                }
                response = await client.post(
                    f"{self.BASE_URL}/crm/v3/objects/companies/search",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                results = response.json()
                if results.get("results"):
                    company = results["results"][0]
                    logger.info(f"Found company {company['id']} with domain {domain}")
                    return company
                logger.info(f"No company found with domain {domain}")
                return None
            except Exception as e:
                logger.error(f"Error searching companies: {e}")
                return None

    async def get_contact_associations(self, contact_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get associated companies for a contact."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}/associations/companies",
                    headers=self.headers,
                )
                response.raise_for_status()
                results = response.json()
                associations = results.get("results", [])
                logger.info(f"Retrieved {len(associations)} company associations for contact {contact_id}")
                return associations
            except Exception as e:
                logger.error(f"Error retrieving contact associations: {e}")
                return None

    async def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get company details from HubSpot."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/crm/v3/objects/companies/{company_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                logger.info(f"Retrieved company {company_id}")
                return response.json()
            except Exception as e:
                logger.error(f"Error retrieving company {company_id}: {e}")
                return None

    async def get_contact(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Get contact details from HubSpot."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                logger.info(f"Retrieved contact {contact_id}")
                return response.json()
            except Exception as e:
                logger.error(f"Error retrieving contact {contact_id}: {e}")
                return None

    async def create_task(
        self, contact_id: str, title: str, body: str, due_date: Optional[str] = None
    ) -> Optional[str]:
        """Create a task in HubSpot."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "properties": {
                        "hs_task_subject": title,
                        "hs_task_body": body,
                        "hs_task_status": "NOT_STARTED",
                    }
                }
                if due_date:
                    payload["properties"]["hs_task_due_date"] = due_date

                response = await client.post(
                    f"{self.BASE_URL}/crm/v3/objects/tasks",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                task_id = response.json()["id"]
                logger.info(f"Created task {task_id} for contact {contact_id}")
                return task_id
            except Exception as e:
                logger.error(f"Error creating task for contact {contact_id}: {e}")
                return None

    async def create_note(self, contact_id: str, body: str) -> Optional[str]:
        """Create a note in HubSpot."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "properties": {
                        "hs_note_body": body,
                    }
                }
                response = await client.post(
                    f"{self.BASE_URL}/crm/v3/objects/notes",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                note_id = response.json()["id"]
                logger.info(f"Created note {note_id} for contact {contact_id}")
                return note_id
            except Exception as e:
                logger.error(f"Error creating note for contact {contact_id}: {e}")
                return None

    async def get_email_engagements(
        self, 
        owner_email: str, 
        limit: int = 100,
        sent_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get email engagements from HubSpot for voice training.
        
        Args:
            owner_email: Email of the HubSpot user whose emails to fetch
            limit: Max emails to return
            sent_only: If True, only get sent emails (not received)
        
        Returns:
            List of email objects with subject, body, recipient, timestamp
        """
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                # Fetch emails without API filter - filter in code for reliability
                emails = []
                after = 0
                
                properties = [
                    "hs_email_subject",
                    "hs_email_text", 
                    "hs_email_html",
                    "hs_email_to_email",
                    "hs_email_from_email",
                    "hs_email_direction",
                    "hs_timestamp",
                    "hs_createdate",
                ]
                
                owner_local = owner_email.split("@")[0].lower()
                
                while len(emails) < limit:
                    # Get emails without filter, filter in code
                    payload = {
                        "sorts": [{"propertyName": "hs_createdate", "direction": "DESCENDING"}],
                        "properties": properties,
                        "limit": 100,
                        "after": after,
                    }
                    
                    response = await client.post(
                        f"{self.BASE_URL}/crm/v3/objects/emails/search",
                        headers=self.headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    results = data.get("results", [])
                    if not results:
                        break
                    
                    for email in results:
                        props = email.get("properties", {})
                        sender = (props.get("hs_email_from_email") or "").lower()
                        
                        # Filter by sender containing owner email local part
                        if sent_only and owner_local not in sender:
                            continue
                        
                        body = props.get("hs_email_text") or props.get("hs_email_html", "")
                        subject = props.get("hs_email_subject", "")
                        
                        email_obj = {
                            "id": email.get("id"),
                            "subject": subject,
                            "body": body,
                            "recipient": props.get("hs_email_to_email", ""),
                            "sender": sender,
                            "timestamp": props.get("hs_timestamp") or props.get("hs_createdate"),
                            "direction": props.get("hs_email_direction", ""),
                        }
                        
                        if email_obj["body"] and len(email_obj["body"]) > 50:
                            emails.append(email_obj)
                            if len(emails) >= limit:
                                break
                    
                    paging = data.get("paging", {})
                    if paging.get("next", {}).get("after"):
                        after = int(paging["next"]["after"])
                    else:
                        break
                
                logger.info(f"Retrieved {len(emails)} sent emails from HubSpot for {owner_email}")
                return emails[:limit]
                
            except Exception as e:
                logger.error(f"Error getting email engagements: {e}", exc_info=True)
                return []

    async def get_form_submissions(
        self, 
        form_id: str,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Get form submissions for a specific form.
        
        Args:
            form_id: HubSpot form ID (e.g., CHAINge NA form)
            limit: Max submissions to return
            
        Returns:
            List of form submission objects with contact data
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                submissions = []
                after = None
                
                while len(submissions) < limit:
                    params = {
                        "limit": min(50, limit - len(submissions)),
                    }
                    if after:
                        params["after"] = after
                    
                    response = await client.get(
                        f"{self.BASE_URL}/form-integrations/v1/submissions/forms/{form_id}",
                        headers=self.headers,
                        params=params,
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    for submission in data.get("results", []):
                        # Extract field values into a flat object
                        values = {}
                        for field in submission.get("values", []):
                            values[field.get("name")] = field.get("value")
                        
                        sub_obj = {
                            "submission_id": submission.get("submissionId"),
                            "submitted_at": submission.get("submittedAt"),
                            "contact_id": submission.get("contactId"),
                            "email": values.get("email", ""),
                            "first_name": values.get("firstname", values.get("first_name", "")),
                            "last_name": values.get("lastname", values.get("last_name", "")),
                            "company": values.get("company", ""),
                            "job_title": values.get("jobtitle", values.get("job_title", "")),
                            "all_values": values,
                        }
                        submissions.append(sub_obj)
                    
                    # Check for pagination
                    paging = data.get("paging", {})
                    if paging.get("next", {}).get("after"):
                        after = paging["next"]["after"]
                    else:
                        break
                
                logger.info(f"Retrieved {len(submissions)} form submissions for {form_id}")
                return submissions[:limit]
                
            except Exception as e:
                logger.error(f"Error getting form submissions: {e}")
                return []

    async def get_contact_engagements(
        self,
        contact_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get engagements associated with a contact.
        
        Args:
            contact_id: HubSpot contact ID
            limit: Max engagements to return
            
        Returns:
            List of engagement objects
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                # Get engagement associations
                response = await client.get(
                    f"{self.BASE_URL}/crm/v4/objects/contacts/{contact_id}/associations/engagements",
                    headers=self.headers,
                    params={"limit": limit},
                )
                response.raise_for_status()
                data = response.json()
                
                engagements = []
                for result in data.get("results", []):
                    eng_id = result.get("toObjectId")
                    if eng_id:
                        # Get engagement details
                        eng_response = await client.get(
                            f"{self.BASE_URL}/crm/v3/objects/engagements/{eng_id}",
                            headers=self.headers,
                            params={"properties": "hs_engagement_type,hs_timestamp,hs_body_preview"},
                        )
                        if eng_response.status_code == 200:
                            eng_data = eng_response.json()
                            props = eng_data.get("properties", {})
                            engagements.append({
                                "id": eng_id,
                                "type": props.get("hs_engagement_type"),
                                "timestamp": props.get("hs_timestamp"),
                                "preview": props.get("hs_body_preview"),
                            })
                
                return engagements
                
            except Exception as e:
                logger.warning(f"Error getting contact engagements: {e}")
                return []

    async def get_contact_deals(
        self,
        contact_id: str,
    ) -> List[Dict[str, Any]]:
        """Get deals associated with a contact.
        
        Args:
            contact_id: HubSpot contact ID
            
        Returns:
            List of deal objects
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                # Get deal associations
                response = await client.get(
                    f"{self.BASE_URL}/crm/v4/objects/contacts/{contact_id}/associations/deals",
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()
                
                deals = []
                for result in data.get("results", []):
                    deal_id = result.get("toObjectId")
                    if deal_id:
                        deal_response = await client.get(
                            f"{self.BASE_URL}/crm/v3/objects/deals/{deal_id}",
                            headers=self.headers,
                            params={"properties": "dealname,dealstage,amount,closedate"},
                        )
                        if deal_response.status_code == 200:
                            deal_data = deal_response.json()
                            deals.append({
                                "id": deal_id,
                                **deal_data.get("properties", {}),
                            })
                
                return deals
                
            except Exception as e:
                logger.warning(f"Error getting contact deals: {e}")
                return []

    async def get_contact_notes(
        self,
        contact_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get notes associated with a contact.
        
        Args:
            contact_id: HubSpot contact ID
            limit: Max notes to return
            
        Returns:
            List of note objects
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/crm/v4/objects/contacts/{contact_id}/associations/notes",
                    headers=self.headers,
                    params={"limit": limit},
                )
                response.raise_for_status()
                data = response.json()
                
                notes = []
                for result in data.get("results", []):
                    note_id = result.get("toObjectId")
                    if note_id:
                        note_response = await client.get(
                            f"{self.BASE_URL}/crm/v3/objects/notes/{note_id}",
                            headers=self.headers,
                            params={"properties": "hs_note_body,hs_timestamp"},
                        )
                        if note_response.status_code == 200:
                            note_data = note_response.json()
                            notes.append({
                                "id": note_id,
                                **note_data.get("properties", {}),
                            })
                
                return notes[:limit]
                
            except Exception as e:
                logger.warning(f"Error getting contact notes: {e}")
                return []

    async def get_contact_tasks(
        self,
        contact_id: str,
    ) -> List[Dict[str, Any]]:
        """Get tasks associated with a contact.
        
        Args:
            contact_id: HubSpot contact ID
            
        Returns:
            List of task objects
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/crm/v4/objects/contacts/{contact_id}/associations/tasks",
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()
                
                tasks = []
                for result in data.get("results", []):
                    task_id = result.get("toObjectId")
                    if task_id:
                        task_response = await client.get(
                            f"{self.BASE_URL}/crm/v3/objects/tasks/{task_id}",
                            headers=self.headers,
                            params={"properties": "hs_task_subject,hs_task_status,hs_task_due_date,hs_task_type"},
                        )
                        if task_response.status_code == 200:
                            task_data = task_response.json()
                            tasks.append({
                                "id": task_id,
                                **task_data.get("properties", {}),
                            })
                
                return tasks
                
            except Exception as e:
                logger.warning(f"Error getting contact tasks: {e}")
                return []

    async def get_contact_meetings(
        self,
        contact_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get meetings associated with a contact.
        
        Args:
            contact_id: HubSpot contact ID
            limit: Max meetings to return
            
        Returns:
            List of meeting objects
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/crm/v4/objects/contacts/{contact_id}/associations/meetings",
                    headers=self.headers,
                    params={"limit": limit},
                )
                response.raise_for_status()
                data = response.json()
                
                meetings = []
                for result in data.get("results", []):
                    meeting_id = result.get("toObjectId")
                    if meeting_id:
                        meeting_response = await client.get(
                            f"{self.BASE_URL}/crm/v3/objects/meetings/{meeting_id}",
                            headers=self.headers,
                            params={"properties": "hs_meeting_title,hs_meeting_body,hs_meeting_outcome,hs_timestamp"},
                        )
                        if meeting_response.status_code == 200:
                            meeting_data = meeting_response.json()
                            meetings.append({
                                "id": meeting_id,
                                **meeting_data.get("properties", {}),
                            })
                
                return meetings[:limit]
                
            except Exception as e:
                logger.warning(f"Error getting contact meetings: {e}")
                return []

    async def search_contacts_by_company(
        self,
        company_name: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search for contacts at a specific company.
        
        Args:
            company_name: Company name to search
            limit: Max contacts to return
            
        Returns:
            List of contact objects
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                payload = {
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "company",
                            "operator": "CONTAINS_TOKEN",
                            "value": company_name,
                        }]
                    }],
                    "properties": ["email", "firstname", "lastname", "jobtitle", "company"],
                    "limit": limit,
                }
                
                response = await client.post(
                    f"{self.BASE_URL}/crm/v3/objects/contacts/search",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                
                contacts = []
                for result in data.get("results", []):
                    contacts.append({
                        "id": result.get("id"),
                        **result.get("properties", {}),
                    })
                
                return contacts
                
            except Exception as e:
                logger.warning(f"Error searching contacts by company: {e}")
                return []


    async def get_marketing_emails(
        self,
        search: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Fetch marketing emails from HubSpot.
        
        This fetches published marketing emails (newsletters, campaigns).
        
        Args:
            search: Search term to filter emails
            limit: Maximum emails to return
            
        Returns:
            List of marketing email objects
        """
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                # HubSpot Marketing Email API v3
                url = f"{self.BASE_URL}/marketing/v3/emails"
                params = {"limit": limit}
                
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                
                emails = data.get("results", [])
                
                # Filter by search term if provided
                if search:
                    emails = [
                        e for e in emails
                        if search.lower() in e.get("name", "").lower()
                        or search.lower() in e.get("subject", "").lower()
                    ]
                
                logger.info(f"Retrieved {len(emails)} marketing emails from HubSpot")
                return emails[:limit]
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error fetching marketing emails: {e.response.status_code} - {e.response.text}")
                return []
            except Exception as e:
                logger.error(f"Error fetching marketing emails: {e}")
                return []


_hubspot_connector: Optional["HubSpotConnector"] = None


def get_hubspot_connector() -> Optional["HubSpotConnector"]:
    """Get singleton HubSpot connector."""
    global _hubspot_connector
    if _hubspot_connector is None:
        api_key = os.getenv("HUBSPOT_API_KEY")
        if api_key:
            _hubspot_connector = HubSpotConnector(api_key)
        else:
            logger.warning("HUBSPOT_API_KEY not configured")
            return None
    return _hubspot_connector


