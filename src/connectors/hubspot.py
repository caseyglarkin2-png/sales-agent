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
