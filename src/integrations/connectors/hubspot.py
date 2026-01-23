"""
HubSpot CRM Integration Connector
==================================

Full HubSpot CRM integration for contacts, deals, companies.

Ship Ship Ship: We already have HUBSPOT_API_KEY in Railway!
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import httpx
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class HubSpotContact(BaseModel):
    """Represents a HubSpot contact"""
    id: str
    email: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    properties: Dict[str, Any] = {}


class HubSpotDeal(BaseModel):
    """Represents a HubSpot deal"""
    id: str
    dealname: str
    amount: Optional[float] = None
    dealstage: Optional[str] = None
    pipeline: Optional[str] = None
    closedate: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    properties: Dict[str, Any] = {}


class HubSpotCompany(BaseModel):
    """Represents a HubSpot company"""
    id: str
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    properties: Dict[str, Any] = {}


class HubSpotConnector:
    """
    HubSpot CRM integration connector.
    
    Uses HubSpot Private App access token (pat-*).
    """
    
    BASE_URL = "https://api.hubapi.com"
    
    def __init__(self, api_key: str):
        """
        Initialize HubSpot connector.
        
        Args:
            api_key: HubSpot Private App access token (from Railway env)
        """
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    async def get_contacts(
        self,
        limit: int = 100,
        after: Optional[str] = None,
        properties: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get contacts from HubSpot.
        
        Args:
            limit: Number of contacts to retrieve
            after: Pagination cursor
            properties: List of properties to retrieve
            
        Returns:
            Dict with contacts and pagination info
        """
        try:
            # Default properties to fetch
            if not properties:
                properties = [
                    "email", "firstname", "lastname", "company",
                    "phone", "jobtitle", "createdate", "lastmodifieddate"
                ]
            
            # Build request params
            params = {
                "limit": limit,
                "properties": ",".join(properties)
            }
            
            if after:
                params["after"] = after
            
            # Make request
            response = await self.client.get("/crm/v3/objects/contacts", params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to HubSpotContact objects
            contacts = []
            for result in data.get("results", []):
                props = result.get("properties", {})
                
                contact = HubSpotContact(
                    id=result["id"],
                    email=props.get("email"),
                    firstname=props.get("firstname"),
                    lastname=props.get("lastname"),
                    company=props.get("company"),
                    phone=props.get("phone"),
                    job_title=props.get("jobtitle"),
                    created_at=props.get("createdate"),
                    updated_at=props.get("lastmodifieddate"),
                    properties=props
                )
                contacts.append(contact)
            
            return {
                "contacts": [c.dict() for c in contacts],
                "paging": data.get("paging", {})
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HubSpot API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"HubSpot API error: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Failed to get HubSpot contacts: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get contacts: {str(e)}")
    
    async def get_deals(
        self,
        limit: int = 100,
        after: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get deals from HubSpot.
        
        Args:
            limit: Number of deals to retrieve
            after: Pagination cursor
            
        Returns:
            Dict with deals and pagination info
        """
        try:
            properties = [
                "dealname", "amount", "dealstage", "pipeline",
                "closedate", "createdate", "hs_lastmodifieddate"
            ]
            
            params = {
                "limit": limit,
                "properties": ",".join(properties)
            }
            
            if after:
                params["after"] = after
            
            response = await self.client.get("/crm/v3/objects/deals", params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to HubSpotDeal objects
            deals = []
            for result in data.get("results", []):
                props = result.get("properties", {})
                
                # Parse amount as float
                amount_str = props.get("amount")
                amount = float(amount_str) if amount_str else None
                
                deal = HubSpotDeal(
                    id=result["id"],
                    dealname=props.get("dealname", ""),
                    amount=amount,
                    dealstage=props.get("dealstage"),
                    pipeline=props.get("pipeline"),
                    closedate=props.get("closedate"),
                    created_at=props.get("createdate"),
                    updated_at=props.get("hs_lastmodifieddate"),
                    properties=props
                )
                deals.append(deal)
            
            return {
                "deals": [d.dict() for d in deals],
                "paging": data.get("paging", {})
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HubSpot API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"HubSpot API error: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Failed to get HubSpot deals: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get deals: {str(e)}")
    
    async def get_companies(
        self,
        limit: int = 100,
        after: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get companies from HubSpot.
        
        Args:
            limit: Number of companies to retrieve
            after: Pagination cursor
            
        Returns:
            Dict with companies and pagination info
        """
        try:
            properties = [
                "name", "domain", "industry",
                "createdate", "hs_lastmodifieddate"
            ]
            
            params = {
                "limit": limit,
                "properties": ",".join(properties)
            }
            
            if after:
                params["after"] = after
            
            response = await self.client.get("/crm/v3/objects/companies", params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to HubSpotCompany objects
            companies = []
            for result in data.get("results", []):
                props = result.get("properties", {})
                
                company = HubSpotCompany(
                    id=result["id"],
                    name=props.get("name", ""),
                    domain=props.get("domain"),
                    industry=props.get("industry"),
                    created_at=props.get("createdate"),
                    updated_at=props.get("hs_lastmodifieddate"),
                    properties=props
                )
                companies.append(company)
            
            return {
                "companies": [c.dict() for c in companies],
                "paging": data.get("paging", {})
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HubSpot API error: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"HubSpot API error: {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Failed to get HubSpot companies: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get companies: {str(e)}")
    
    async def search_contacts(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        company: Optional[str] = None
    ) -> List[HubSpotContact]:
        """
        Search for contacts in HubSpot.
        
        Args:
            email: Email to search for
            name: Name to search for
            company: Company to search for
            
        Returns:
            List of matching contacts
        """
        try:
            filters = []
            
            if email:
                filters.append({
                    "propertyName": "email",
                    "operator": "EQ",
                    "value": email
                })
            
            if name:
                filters.append({
                    "propertyName": "firstname",
                    "operator": "CONTAINS_TOKEN",
                    "value": name
                })
            
            if company:
                filters.append({
                    "propertyName": "company",
                    "operator": "CONTAINS_TOKEN",
                    "value": company
                })
            
            if not filters:
                return []
            
            search_body = {
                "filterGroups": [{"filters": filters}],
                "properties": [
                    "email", "firstname", "lastname", "company",
                    "phone", "jobtitle"
                ]
            }
            
            response = await self.client.post("/crm/v3/objects/contacts/search", json=search_body)
            response.raise_for_status()
            
            data = response.json()
            
            contacts = []
            for result in data.get("results", []):
                props = result.get("properties", {})
                
                contact = HubSpotContact(
                    id=result["id"],
                    email=props.get("email"),
                    firstname=props.get("firstname"),
                    lastname=props.get("lastname"),
                    company=props.get("company"),
                    phone=props.get("phone"),
                    job_title=props.get("jobtitle"),
                    properties=props
                )
                contacts.append(contact)
            
            return contacts
            
        except Exception as e:
            logger.error(f"Failed to search HubSpot contacts: {e}")
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
    async def test_connection(self) -> bool:
        """
        Test HubSpot API connection.
        
        Returns:
            True if connection successful
        """
        try:
            response = await self.client.get("/crm/v3/objects/contacts?limit=1")
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"HubSpot connection test failed: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
