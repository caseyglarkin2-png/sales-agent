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
                # Use the search API to filter by sender email for sent emails
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
                
                while len(emails) < limit:
                    # Build search payload to filter by sender
                    filters = []
                    
                    if sent_only:
                        # For sent emails, filter by from_email matching owner
                        filters.append({
                            "propertyName": "hs_email_from_email",
                            "operator": "CONTAINS_TOKEN",
                            "value": owner_email.split("@")[0]  # Match on local part
                        })
                        filters.append({
                            "propertyName": "hs_email_direction",
                            "operator": "EQ",
                            "value": "EMAIL"  # Outbound emails
                        })
                    
                    payload = {
                        "filterGroups": [{"filters": filters}] if filters else [],
                        "sorts": [{"propertyName": "hs_createdate", "direction": "DESCENDING"}],
                        "properties": properties,
                        "limit": min(100, limit - len(emails)),
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
                        # No more results, try without filter to see if any emails exist
                        if len(emails) == 0 and after == 0:
                            logger.info("No filtered emails found, trying unfiltered search")
                            # Try getting any recent emails for debugging
                            unfiltered_payload = {
                                "sorts": [{"propertyName": "hs_createdate", "direction": "DESCENDING"}],
                                "properties": properties,
                                "limit": 10,
                            }
                            debug_resp = await client.post(
                                f"{self.BASE_URL}/crm/v3/objects/emails/search",
                                headers=self.headers,
                                json=unfiltered_payload,
                            )
                            debug_data = debug_resp.json()
                            debug_results = debug_data.get("results", [])
                            if debug_results:
                                logger.info(f"Found {len(debug_results)} unfiltered emails, sample sender: {debug_results[0].get('properties', {}).get('hs_email_from_email', 'N/A')}")
                        break
                    
                    for email in results:
                        props = email.get("properties", {})
                        
                        # Extract email content
                        body = props.get("hs_email_text") or props.get("hs_email_html", "")
                        subject = props.get("hs_email_subject", "")
                        
                        email_obj = {
                            "id": email.get("id"),
                            "subject": subject,
                            "body": body,
                            "recipient": props.get("hs_email_to_email", ""),
                            "sender": props.get("hs_email_from_email", ""),
                            "timestamp": props.get("hs_timestamp") or props.get("hs_createdate"),
                            "direction": props.get("hs_email_direction", ""),
                        }
                        
                        # Only include if has content
                        if email_obj["body"] and len(email_obj["body"]) > 50:
                            emails.append(email_obj)
                    
                    # Check for pagination
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

