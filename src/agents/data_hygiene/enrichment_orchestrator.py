"""Enrichment Orchestrator Agent - Coordinates data enrichment from external sources.

Responsibilities:
- Orchestrate enrichment from Clearbit, Apollo, ZoomInfo, etc.
- Prioritize which contacts to enrich (based on ICP fit, deal value)
- Manage enrichment credits/quotas
- Merge enriched data back into HubSpot
- Track enrichment success rates
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class EnrichmentSource(str, Enum):
    """Available enrichment data sources."""
    CLEARBIT = "clearbit"
    APOLLO = "apollo"
    ZOOMINFO = "zoominfo"
    HUNTER = "hunter"
    LINKEDIN = "linkedin"
    INTERNAL = "internal"  # Our own data from past interactions


class EnrichmentField(str, Enum):
    """Fields that can be enriched."""
    COMPANY_SIZE = "company_size"
    INDUSTRY = "industry"
    REVENUE = "revenue"
    TECHNOLOGY_STACK = "technology_stack"
    JOB_TITLE = "jobtitle"
    PHONE = "phone"
    LINKEDIN_URL = "linkedin_url"
    COMPANY_DESCRIPTION = "company_description"
    FUNDING = "funding"
    EMPLOYEE_COUNT = "employee_count"


@dataclass
class EnrichmentRequest:
    """Request to enrich a contact."""
    contact_id: str
    email: str
    company: Optional[str]
    fields_to_enrich: List[EnrichmentField]
    priority: int  # 1-5
    source_preference: List[EnrichmentSource]


@dataclass
class EnrichmentResult:
    """Result of enrichment attempt."""
    contact_id: str
    success: bool
    source_used: Optional[EnrichmentSource]
    fields_enriched: Dict[str, Any]
    fields_failed: List[str]
    credits_used: int


class EnrichmentOrchestratorAgent(BaseAgent):
    """Orchestrates contact enrichment from multiple sources.
    
    Enrichment Strategy:
    1. Check if we have recent enrichment data (< 30 days)
    2. Determine which fields are missing/stale
    3. Select best source based on field type
    4. Execute enrichment with rate limit awareness
    5. Merge results back into contact record
    
    Credit Management:
    - Track credits per source
    - Prioritize high-value contacts when credits low
    - Fallback to cheaper sources for low-priority contacts
    """
    
    # Field to source mapping (preferred source first)
    FIELD_SOURCES = {
        EnrichmentField.COMPANY_SIZE: [EnrichmentSource.CLEARBIT, EnrichmentSource.APOLLO],
        EnrichmentField.INDUSTRY: [EnrichmentSource.CLEARBIT, EnrichmentSource.APOLLO],
        EnrichmentField.REVENUE: [EnrichmentSource.ZOOMINFO, EnrichmentSource.CLEARBIT],
        EnrichmentField.TECHNOLOGY_STACK: [EnrichmentSource.CLEARBIT],
        EnrichmentField.JOB_TITLE: [EnrichmentSource.LINKEDIN, EnrichmentSource.APOLLO],
        EnrichmentField.PHONE: [EnrichmentSource.ZOOMINFO, EnrichmentSource.APOLLO],
        EnrichmentField.LINKEDIN_URL: [EnrichmentSource.APOLLO, EnrichmentSource.HUNTER],
        EnrichmentField.COMPANY_DESCRIPTION: [EnrichmentSource.CLEARBIT],
        EnrichmentField.FUNDING: [EnrichmentSource.CLEARBIT],
        EnrichmentField.EMPLOYEE_COUNT: [EnrichmentSource.CLEARBIT, EnrichmentSource.APOLLO],
    }
    
    # Credit costs per source (placeholder - would be from config)
    CREDIT_COSTS = {
        EnrichmentSource.CLEARBIT: 1,
        EnrichmentSource.APOLLO: 1,
        EnrichmentSource.ZOOMINFO: 2,
        EnrichmentSource.HUNTER: 0.5,
        EnrichmentSource.LINKEDIN: 0,  # Manual lookup
        EnrichmentSource.INTERNAL: 0,
    }
    
    def __init__(self, connectors: Dict[str, Any] = None):
        super().__init__(
            name="EnrichmentOrchestratorAgent",
            description="Orchestrates contact enrichment from external sources"
        )
        self.connectors = connectors or {}
        # Track credit usage (would be persisted in real implementation)
        self.credits_used = {source: 0 for source in EnrichmentSource}
        self.credits_limit = {
            EnrichmentSource.CLEARBIT: 1000,
            EnrichmentSource.APOLLO: 2000,
            EnrichmentSource.ZOOMINFO: 500,
            EnrichmentSource.HUNTER: 1000,
            EnrichmentSource.LINKEDIN: float('inf'),
            EnrichmentSource.INTERNAL: float('inf'),
        }
    
    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input based on action."""
        action = context.get("action", "enrich")
        if action == "enrich_contact":
            return "contact" in context
        elif action == "enrich_batch":
            return "contacts" in context
        elif action == "get_credit_status":
            return True
        elif action == "prioritize_batch":
            return "contacts" in context
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute enrichment based on action."""
        action = context.get("action", "enrich_contact")
        
        if action == "enrich_contact":
            contact = context.get("contact", {})
            fields = context.get("fields", None)
            result = await self._enrich_contact(contact, fields)
            return {
                "status": "success",
                "result": self._result_to_dict(result),
            }
        
        elif action == "enrich_batch":
            contacts = context.get("contacts", [])
            max_credits = context.get("max_credits", 100)
            fields = context.get("fields", None)
            
            results = await self._enrich_batch(contacts, fields, max_credits)
            
            return {
                "status": "success",
                "total_contacts": len(contacts),
                "enriched": sum(1 for r in results if r.success),
                "failed": sum(1 for r in results if not r.success),
                "credits_used": sum(r.credits_used for r in results),
                "results": [self._result_to_dict(r) for r in results],
            }
        
        elif action == "get_credit_status":
            return {
                "status": "success",
                "credits": {
                    source.value: {
                        "used": self.credits_used[source],
                        "limit": self.credits_limit[source],
                        "remaining": self.credits_limit[source] - self.credits_used[source],
                    }
                    for source in EnrichmentSource
                    if self.credits_limit[source] != float('inf')
                },
            }
        
        elif action == "prioritize_batch":
            contacts = context.get("contacts", [])
            limit = context.get("limit", 100)
            prioritized = self._prioritize_for_enrichment(contacts)
            
            return {
                "status": "success",
                "total_candidates": len(prioritized),
                "top_priority": prioritized[:limit],
            }
        
        elif action == "get_missing_fields":
            contact = context.get("contact", {})
            missing = self._get_missing_fields(contact)
            
            return {
                "status": "success",
                "contact_id": contact.get("id"),
                "missing_fields": [f.value for f in missing],
                "enrichment_sources": {
                    f.value: [s.value for s in self.FIELD_SOURCES.get(f, [])]
                    for f in missing
                },
            }
        
        return {"status": "error", "error": f"Unknown action: {action}"}
    
    async def _enrich_contact(
        self, 
        contact: Dict[str, Any],
        requested_fields: Optional[List[str]] = None
    ) -> EnrichmentResult:
        """Enrich a single contact."""
        contact_id = contact.get("id", "unknown")
        email = contact.get("email", "")
        company = contact.get("company")
        
        # Determine which fields to enrich
        if requested_fields:
            fields = [EnrichmentField(f) for f in requested_fields if f in [e.value for e in EnrichmentField]]
        else:
            fields = self._get_missing_fields(contact)
        
        if not fields:
            return EnrichmentResult(
                contact_id=contact_id,
                success=True,
                source_used=None,
                fields_enriched={},
                fields_failed=[],
                credits_used=0,
            )
        
        # Try to enrich each field
        enriched_data = {}
        failed_fields = []
        total_credits = 0
        sources_used = set()
        
        for field in fields:
            sources = self.FIELD_SOURCES.get(field, [])
            enriched = False
            
            for source in sources:
                # Check credit availability
                if self.credits_used[source] >= self.credits_limit[source]:
                    continue
                
                # Try to enrich from this source
                # In real implementation, would call the actual API
                value = await self._enrich_field_from_source(
                    email, company, field, source
                )
                
                if value is not None:
                    enriched_data[field.value] = value
                    self.credits_used[source] += self.CREDIT_COSTS[source]
                    total_credits += self.CREDIT_COSTS[source]
                    sources_used.add(source)
                    enriched = True
                    break
            
            if not enriched:
                failed_fields.append(field.value)
        
        return EnrichmentResult(
            contact_id=contact_id,
            success=len(enriched_data) > 0,
            source_used=list(sources_used)[0] if sources_used else None,
            fields_enriched=enriched_data,
            fields_failed=failed_fields,
            credits_used=int(total_credits),
        )
    
    async def _enrich_batch(
        self,
        contacts: List[Dict[str, Any]],
        requested_fields: Optional[List[str]],
        max_credits: int
    ) -> List[EnrichmentResult]:
        """Enrich a batch of contacts within credit budget."""
        # Prioritize contacts
        prioritized = self._prioritize_for_enrichment(contacts)
        
        results = []
        credits_spent = 0
        
        for item in prioritized:
            contact = item["contact"]
            estimated_cost = item["estimated_cost"]
            
            if credits_spent + estimated_cost > max_credits:
                # Over budget, add failed result
                results.append(EnrichmentResult(
                    contact_id=contact.get("id"),
                    success=False,
                    source_used=None,
                    fields_enriched={},
                    fields_failed=["budget_exceeded"],
                    credits_used=0,
                ))
                continue
            
            result = await self._enrich_contact(contact, requested_fields)
            results.append(result)
            credits_spent += result.credits_used
        
        return results
    
    async def _enrich_field_from_source(
        self,
        email: str,
        company: Optional[str],
        field: EnrichmentField,
        source: EnrichmentSource
    ) -> Optional[Any]:
        """Enrich a specific field from a specific source.
        
        In real implementation, this would call the actual API.
        For now, returns None (no enrichment available).
        """
        # Check if we have a connector for this source
        connector = self.connectors.get(source.value)
        
        if connector:
            # Would call: connector.enrich(email, field)
            pass
        
        # Placeholder: In real implementation, call the enrichment API
        logger.info(f"Would enrich {field.value} for {email} from {source.value}")
        return None
    
    def _get_missing_fields(self, contact: Dict[str, Any]) -> List[EnrichmentField]:
        """Determine which enrichable fields are missing."""
        missing = []
        
        # Map contact fields to enrichment fields
        field_mapping = {
            EnrichmentField.JOB_TITLE: ["jobtitle"],
            EnrichmentField.PHONE: ["phone", "mobilephone"],
            EnrichmentField.LINKEDIN_URL: ["linkedin_url", "hs_linkedin_url"],
            EnrichmentField.COMPANY_SIZE: ["company_size", "numberofemployees"],
            EnrichmentField.INDUSTRY: ["industry"],
            EnrichmentField.REVENUE: ["annualrevenue"],
        }
        
        for enrich_field, contact_fields in field_mapping.items():
            has_value = any(contact.get(f) for f in contact_fields)
            if not has_value:
                missing.append(enrich_field)
        
        return missing
    
    def _prioritize_for_enrichment(
        self, 
        contacts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prioritize contacts for enrichment based on value."""
        prioritized = []
        
        for contact in contacts:
            missing_fields = self._get_missing_fields(contact)
            if not missing_fields:
                continue
            
            # Calculate priority score
            score = 0
            
            # Higher priority for customers/opportunities
            lifecycle = contact.get("lifecyclestage", "").lower()
            if lifecycle == "customer":
                score += 100
            elif lifecycle == "opportunity":
                score += 80
            elif lifecycle == "lead":
                score += 40
            
            # Higher priority for contacts with deals
            num_deals = int(contact.get("num_associated_deals", 0) or 0)
            score += num_deals * 20
            
            # More missing fields = higher priority
            score += len(missing_fields) * 5
            
            # Estimate enrichment cost
            estimated_cost = sum(
                min(self.CREDIT_COSTS[s] for s in self.FIELD_SOURCES.get(f, [EnrichmentSource.INTERNAL]))
                for f in missing_fields
            )
            
            prioritized.append({
                "contact": contact,
                "contact_id": contact.get("id"),
                "email": contact.get("email"),
                "priority_score": score,
                "missing_fields": [f.value for f in missing_fields],
                "estimated_cost": estimated_cost,
            })
        
        # Sort by priority score descending
        prioritized.sort(key=lambda x: x["priority_score"], reverse=True)
        return prioritized
    
    def _result_to_dict(self, result: EnrichmentResult) -> Dict[str, Any]:
        """Convert result to dict."""
        return {
            "contact_id": result.contact_id,
            "success": result.success,
            "source_used": result.source_used.value if result.source_used else None,
            "fields_enriched": result.fields_enriched,
            "fields_failed": result.fields_failed,
            "credits_used": result.credits_used,
        }
