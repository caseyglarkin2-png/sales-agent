"""Contact enrichment module.

Enriches contact data from multiple sources:
- Clearbit/Apollo for company data
- LinkedIn (via proxy APIs) for job title verification
- HubSpot for existing CRM data
- Web scraping for company info
"""
import asyncio
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from src.logger import get_logger

logger = get_logger(__name__)


class EnrichedContact(BaseModel):
    """Enriched contact data."""
    email: str
    first_name: str = ""
    last_name: str = ""
    
    # Job info
    job_title: str = ""
    job_title_normalized: str = ""
    seniority_level: str = ""  # executive, director, manager, individual
    department: str = ""  # marketing, sales, ops, etc
    
    # Company info
    company_name: str = ""
    company_domain: str = ""
    company_size: str = ""  # 1-10, 11-50, 51-200, 201-500, 501-1000, 1000+
    company_industry: str = ""
    company_linkedin_url: str = ""
    company_description: str = ""
    company_technologies: List[str] = []
    
    # Social profiles
    linkedin_url: str = ""
    twitter_handle: str = ""
    
    # Enrichment metadata
    enrichment_source: str = ""
    enrichment_confidence: float = 0.0
    enriched_at: str = ""


class ContactEnricher:
    """Enriches contact data from multiple sources."""
    
    def __init__(self):
        self.clearbit_api_key = os.environ.get("CLEARBIT_API_KEY", "")
        self.apollo_api_key = os.environ.get("APOLLO_API_KEY", "")
        self.hubspot_api_key = os.environ.get("HUBSPOT_API_KEY", "")
    
    async def enrich_contact(
        self,
        email: str,
        first_name: str = "",
        last_name: str = "",
        company: str = "",
        job_title: str = "",
    ) -> EnrichedContact:
        """Enrich a single contact from all available sources.
        
        Priority:
        1. HubSpot (if existing contact)
        2. Clearbit (best for company data)
        3. Apollo (good for B2B contacts)
        4. Domain extraction (fallback)
        """
        result = EnrichedContact(
            email=email,
            first_name=first_name,
            last_name=last_name,
            company_name=company,
            job_title=job_title,
        )
        
        # Extract domain from email
        domain = self._extract_domain(email)
        if domain:
            result.company_domain = domain
        
        # Try HubSpot first
        hubspot_data = await self._enrich_from_hubspot(email)
        if hubspot_data:
            result = self._merge_data(result, hubspot_data, "hubspot")
        
        # Try Clearbit if API key available
        if self.clearbit_api_key:
            clearbit_data = await self._enrich_from_clearbit(email)
            if clearbit_data:
                result = self._merge_data(result, clearbit_data, "clearbit")
        
        # Try Apollo if API key available
        if self.apollo_api_key and not result.linkedin_url:
            apollo_data = await self._enrich_from_apollo(email, first_name, last_name, company)
            if apollo_data:
                result = self._merge_data(result, apollo_data, "apollo")
        
        # Normalize job title
        result.job_title_normalized = self._normalize_job_title(result.job_title)
        result.seniority_level = self._detect_seniority(result.job_title)
        result.department = self._detect_department(result.job_title)
        
        logger.info(f"Enriched {email}: {result.company_name}, {result.job_title}")
        return result
    
    async def enrich_batch(
        self,
        contacts: List[Dict[str, Any]],
        max_concurrent: int = 5,
    ) -> List[EnrichedContact]:
        """Enrich multiple contacts with rate limiting."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def enrich_with_limit(contact: Dict[str, Any]) -> EnrichedContact:
            async with semaphore:
                return await self.enrich_contact(
                    email=contact.get("email", ""),
                    first_name=contact.get("first_name", ""),
                    last_name=contact.get("last_name", ""),
                    company=contact.get("company", ""),
                    job_title=contact.get("job_title", ""),
                )
        
        tasks = [enrich_with_limit(c) for c in contacts]
        return await asyncio.gather(*tasks)
    
    def _extract_domain(self, email: str) -> str:
        """Extract company domain from email."""
        if "@" not in email:
            return ""
        
        domain = email.split("@")[1].lower()
        
        # Skip common personal email providers
        personal_domains = {
            "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
            "aol.com", "icloud.com", "mail.com", "protonmail.com",
        }
        if domain in personal_domains:
            return ""
        
        return domain
    
    async def _enrich_from_hubspot(self, email: str) -> Optional[Dict[str, Any]]:
        """Get existing data from HubSpot."""
        if not self.hubspot_api_key:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Search for contact
                response = await client.post(
                    "https://api.hubapi.com/crm/v3/objects/contacts/search",
                    headers={"Authorization": f"Bearer {self.hubspot_api_key}"},
                    json={
                        "filterGroups": [{
                            "filters": [{
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": email,
                            }]
                        }],
                        "properties": [
                            "firstname", "lastname", "jobtitle", "company",
                            "phone", "linkedin", "hs_lead_status",
                        ],
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("results"):
                    contact = data["results"][0]
                    props = contact.get("properties", {})
                    return {
                        "first_name": props.get("firstname", ""),
                        "last_name": props.get("lastname", ""),
                        "job_title": props.get("jobtitle", ""),
                        "company_name": props.get("company", ""),
                        "linkedin_url": props.get("linkedin", ""),
                    }
        except Exception as e:
            logger.warning(f"HubSpot enrichment failed for {email}: {e}")
        
        return None
    
    async def _enrich_from_clearbit(self, email: str) -> Optional[Dict[str, Any]]:
        """Enrich from Clearbit API."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    f"https://person.clearbit.com/v2/combined/find",
                    params={"email": email},
                    headers={"Authorization": f"Bearer {self.clearbit_api_key}"},
                )
                
                if response.status_code == 200:
                    data = response.json()
                    person = data.get("person", {})
                    company = data.get("company", {})
                    
                    return {
                        "first_name": person.get("name", {}).get("givenName", ""),
                        "last_name": person.get("name", {}).get("familyName", ""),
                        "job_title": person.get("employment", {}).get("title", ""),
                        "seniority_level": person.get("employment", {}).get("seniority", ""),
                        "linkedin_url": person.get("linkedin", {}).get("handle", ""),
                        "twitter_handle": person.get("twitter", {}).get("handle", ""),
                        "company_name": company.get("name", ""),
                        "company_domain": company.get("domain", ""),
                        "company_size": self._map_employee_count(company.get("metrics", {}).get("employees")),
                        "company_industry": company.get("category", {}).get("industry", ""),
                        "company_description": company.get("description", ""),
                        "company_linkedin_url": company.get("linkedin", {}).get("handle", ""),
                        "company_technologies": company.get("tech", [])[:10],
                    }
                elif response.status_code == 202:
                    # Clearbit is processing - data not ready
                    logger.info(f"Clearbit processing {email}, data pending")
        except Exception as e:
            logger.warning(f"Clearbit enrichment failed for {email}: {e}")
        
        return None
    
    async def _enrich_from_apollo(
        self,
        email: str,
        first_name: str = "",
        last_name: str = "",
        company: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Enrich from Apollo.io API."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    "https://api.apollo.io/v1/people/match",
                    headers={"Content-Type": "application/json"},
                    json={
                        "api_key": self.apollo_api_key,
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "organization_name": company,
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    person = data.get("person", {})
                    org = person.get("organization", {})
                    
                    if person:
                        return {
                            "first_name": person.get("first_name", ""),
                            "last_name": person.get("last_name", ""),
                            "job_title": person.get("title", ""),
                            "linkedin_url": person.get("linkedin_url", ""),
                            "company_name": org.get("name", ""),
                            "company_size": self._map_employee_count(org.get("estimated_num_employees")),
                            "company_industry": org.get("industry", ""),
                            "company_linkedin_url": org.get("linkedin_url", ""),
                        }
        except Exception as e:
            logger.warning(f"Apollo enrichment failed for {email}: {e}")
        
        return None
    
    def _merge_data(
        self,
        existing: EnrichedContact,
        new_data: Dict[str, Any],
        source: str,
    ) -> EnrichedContact:
        """Merge new data into existing contact, preferring non-empty values."""
        data = existing.model_dump()
        
        for key, value in new_data.items():
            if value and (not data.get(key) or key in ["company_technologies"]):
                data[key] = value
        
        data["enrichment_source"] = source
        data["enrichment_confidence"] = 0.8 if source == "clearbit" else 0.6
        
        return EnrichedContact(**data)
    
    def _map_employee_count(self, count: Optional[int]) -> str:
        """Map employee count to size bucket."""
        if not count:
            return ""
        if count <= 10:
            return "1-10"
        elif count <= 50:
            return "11-50"
        elif count <= 200:
            return "51-200"
        elif count <= 500:
            return "201-500"
        elif count <= 1000:
            return "501-1000"
        else:
            return "1000+"
    
    def _normalize_job_title(self, title: str) -> str:
        """Normalize job title for consistent matching."""
        if not title:
            return ""
        
        title = title.lower().strip()
        
        # Common normalizations
        normalizations = {
            "vp": "vice president",
            "svp": "senior vice president",
            "evp": "executive vice president",
            "dir": "director",
            "mgr": "manager",
            "sr": "senior",
            "jr": "junior",
        }
        
        for abbrev, full in normalizations.items():
            if title.startswith(abbrev + " ") or title.startswith(abbrev + "."):
                title = full + title[len(abbrev):]
        
        return title
    
    def _detect_seniority(self, title: str) -> str:
        """Detect seniority level from job title."""
        if not title:
            return "unknown"
        
        title_lower = title.lower()
        
        if any(x in title_lower for x in ["chief", "ceo", "cfo", "cmo", "cto", "cro", "coo"]):
            return "c-suite"
        elif any(x in title_lower for x in ["vp", "vice president", "evp", "svp"]):
            return "executive"
        elif "director" in title_lower or "head of" in title_lower:
            return "director"
        elif "manager" in title_lower or "lead" in title_lower:
            return "manager"
        elif "senior" in title_lower or "sr" in title_lower:
            return "senior"
        else:
            return "individual"
    
    def _detect_department(self, title: str) -> str:
        """Detect department from job title."""
        if not title:
            return "unknown"
        
        title_lower = title.lower()
        
        departments = {
            "marketing": ["marketing", "demand", "growth", "brand", "content", "event", "field"],
            "sales": ["sales", "account executive", "sdr", "bdr", "business development"],
            "operations": ["operations", "ops", "revenue ops", "sales ops", "marketing ops"],
            "product": ["product", "pm", "product manager"],
            "engineering": ["engineering", "developer", "software", "technical"],
            "finance": ["finance", "accounting", "cfo"],
            "hr": ["hr", "human resources", "people", "talent"],
            "executive": ["ceo", "founder", "president", "general manager"],
        }
        
        for dept, keywords in departments.items():
            if any(kw in title_lower for kw in keywords):
                return dept
        
        return "other"


# Global enricher instance
_enricher: Optional[ContactEnricher] = None


def get_contact_enricher() -> ContactEnricher:
    """Get or create the global contact enricher."""
    global _enricher
    if _enricher is None:
        _enricher = ContactEnricher()
    return _enricher
