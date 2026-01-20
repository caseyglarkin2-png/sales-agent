"""Research Agent - Enriches prospect data with company and person intelligence."""
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

from src.logger import get_logger

logger = get_logger(__name__)


class ResearchAgent:
    """Agent that researches prospects and companies before email drafting.
    
    Gathers context from multiple sources:
    - LinkedIn (via API or scraping)
    - Company website
    - News articles
    - HubSpot history
    - Previous interactions
    """
    
    def __init__(
        self,
        hubspot_connector=None,
        gmail_connector=None,
    ):
        self.hubspot_connector = hubspot_connector
        self.gmail_connector = gmail_connector
        self.research_cache: Dict[str, Dict] = {}
    
    async def research_prospect(
        self,
        email: str,
        company: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Research a prospect before drafting an email.
        
        Returns enriched data including:
        - Company info (size, industry, recent news)
        - Person info (role, tenure, interests)
        - Relationship history (past emails, meetings, deals)
        - Talking points and personalization hooks
        """
        logger.info(f"Researching prospect: {email} at {company}")
        
        research = {
            "email": email,
            "company": company,
            "first_name": first_name,
            "last_name": last_name,
            "researched_at": datetime.utcnow().isoformat(),
            "sources": [],
            "company_intel": {},
            "person_intel": {},
            "relationship_history": {},
            "talking_points": [],
            "personalization_hooks": [],
        }
        
        # 1. Research from HubSpot
        hubspot_data = await self._research_hubspot(email, company)
        if hubspot_data:
            research["sources"].append("hubspot")
            research["relationship_history"] = hubspot_data.get("history", {})
            research["company_intel"].update(hubspot_data.get("company", {}))
            research["person_intel"].update(hubspot_data.get("contact", {}))
        
        # 2. Research from Gmail (past interactions)
        gmail_data = await self._research_gmail(email)
        if gmail_data:
            research["sources"].append("gmail")
            research["relationship_history"]["email_history"] = gmail_data
        
        # 3. Research company (web/news)
        if company:
            company_data = await self._research_company(company)
            if company_data:
                research["sources"].append("web")
                research["company_intel"].update(company_data)
        
        # 4. Generate talking points
        research["talking_points"] = self._generate_talking_points(research)
        
        # 5. Generate personalization hooks
        research["personalization_hooks"] = self._generate_hooks(research)
        
        logger.info(f"Research complete for {email}: {len(research['sources'])} sources, {len(research['talking_points'])} talking points")
        
        return research
    
    async def _research_hubspot(self, email: str, company: Optional[str]) -> Dict[str, Any]:
        """Pull data from HubSpot CRM."""
        if not self.hubspot_connector:
            return {}
        
        try:
            result = {}
            
            # Get contact
            contact = await self.hubspot_connector.search_contacts(email)
            if contact:
                result["contact"] = {
                    "id": contact.get("id"),
                    "lifecycle_stage": contact.get("properties", {}).get("lifecyclestage"),
                    "lead_status": contact.get("properties", {}).get("hs_lead_status"),
                    "last_activity": contact.get("properties", {}).get("notes_last_updated"),
                    "owner": contact.get("properties", {}).get("hubspot_owner_id"),
                }
                
                # Get associated company
                associations = await self.hubspot_connector.get_contact_associations(contact["id"])
                if associations:
                    result["company"] = {
                        "has_company": True,
                        "company_ids": [a.get("id") for a in associations],
                    }
            
            # Get deals if any
            # result["history"]["deals"] = await self._get_deals(contact_id)
            
            return result
        except Exception as e:
            logger.warning(f"HubSpot research failed: {e}")
            return {}
    
    async def _research_gmail(self, email: str) -> Dict[str, Any]:
        """Analyze past email interactions."""
        if not self.gmail_connector:
            return {}
        
        try:
            # Search for threads with this person
            threads = await self.gmail_connector.search_threads(f"from:{email} OR to:{email}", max_results=10)
            
            if not threads:
                return {"thread_count": 0, "last_contact": None}
            
            # Analyze threads
            thread_summaries = []
            for thread in threads[:5]:  # Analyze top 5
                thread_data = await self.gmail_connector.get_thread(thread["id"])
                if thread_data:
                    messages = thread_data.get("messages", [])
                    if messages:
                        thread_summaries.append({
                            "id": thread["id"],
                            "subject": thread_data.get("snippet", "")[:100],
                            "message_count": len(messages),
                            "last_message": messages[-1].get("internalDate") if messages else None,
                        })
            
            return {
                "thread_count": len(threads),
                "recent_threads": thread_summaries,
                "has_prior_contact": len(threads) > 0,
            }
        except Exception as e:
            logger.warning(f"Gmail research failed: {e}")
            return {}
    
    async def _research_company(self, company: str) -> Dict[str, Any]:
        """Research company from web sources.
        
        In production, this would:
        - Query company databases (Clearbit, ZoomInfo, etc.)
        - Scrape company website
        - Search recent news
        """
        # For now, return basic structure
        # TODO: Integrate with Clearbit, Apollo, or similar APIs
        return {
            "name": company,
            "industry_guess": self._guess_industry(company),
            "size_guess": "unknown",
            "research_note": "Full company research requires API integration",
        }
    
    def _guess_industry(self, company: str) -> str:
        """Make educated guess about industry from company name."""
        company_lower = company.lower()
        
        industry_keywords = {
            "logistics": ["freight", "logistics", "shipping", "transport", "trucking", "carrier"],
            "technology": ["tech", "software", "systems", "digital", "cloud", "ai"],
            "manufacturing": ["manufacturing", "industrial", "factory", "production"],
            "retail": ["retail", "store", "shop", "market"],
            "healthcare": ["health", "medical", "pharma", "hospital", "clinic"],
            "finance": ["bank", "financial", "capital", "investment", "fund"],
        }
        
        for industry, keywords in industry_keywords.items():
            if any(kw in company_lower for kw in keywords):
                return industry
        
        return "general"
    
    def _generate_talking_points(self, research: Dict[str, Any]) -> List[str]:
        """Generate relevant talking points based on research."""
        points = []
        
        # Based on email history
        email_history = research.get("relationship_history", {}).get("email_history", {})
        if email_history.get("has_prior_contact"):
            points.append(f"Prior email history: {email_history.get('thread_count', 0)} threads")
        
        # Based on company
        company = research.get("company")
        if company:
            industry = research.get("company_intel", {}).get("industry_guess")
            if industry and industry != "general":
                points.append(f"Industry: {industry} - tailor messaging accordingly")
        
        # Based on lifecycle stage
        lifecycle = research.get("person_intel", {}).get("lifecycle_stage")
        if lifecycle:
            points.append(f"HubSpot lifecycle: {lifecycle}")
        
        return points
    
    def _generate_hooks(self, research: Dict[str, Any]) -> List[str]:
        """Generate personalization hooks for the email."""
        hooks = []
        
        # Reference prior conversations
        email_history = research.get("relationship_history", {}).get("email_history", {})
        if email_history.get("has_prior_contact"):
            hooks.append("Reference previous conversation")
        
        # Company-specific
        industry = research.get("company_intel", {}).get("industry_guess")
        if industry == "logistics":
            hooks.append("Mention freight/logistics expertise")
        
        # If no hooks, suggest cold opener
        if not hooks:
            hooks.append("Warm introduction - mention form submission")
        
        return hooks


def create_research_agent(
    hubspot_connector=None,
    gmail_connector=None,
) -> ResearchAgent:
    """Factory function to create ResearchAgent with connectors."""
    return ResearchAgent(
        hubspot_connector=hubspot_connector,
        gmail_connector=gmail_connector,
    )
