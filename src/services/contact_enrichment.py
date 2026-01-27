"""Contact enrichment service for command queue.

Sprint 39B: Provides contact context (name, email) for queue items
by looking up HubSpot contact IDs and caching results.
"""
import asyncio
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
import structlog

from src.connectors.hubspot import HubSpotConnector, create_hubspot_connector

logger = structlog.get_logger(__name__)

# Simple in-memory cache for contact info
# Key: contact_id, Value: ContactInfo
_contact_cache: Dict[str, "ContactInfo"] = {}


@dataclass
class ContactInfo:
    """Contact information from HubSpot."""
    id: str
    name: str
    email: Optional[str] = None
    company: Optional[str] = None
    
    @classmethod
    def from_hubspot(cls, contact_data: Dict[str, Any]) -> "ContactInfo":
        """Create ContactInfo from HubSpot API response."""
        props = contact_data.get("properties", {})
        first = props.get("firstname", "") or ""
        last = props.get("lastname", "") or ""
        name = f"{first} {last}".strip() or "Unknown Contact"
        
        return cls(
            id=contact_data.get("id", ""),
            name=name,
            email=props.get("email"),
            company=props.get("company"),
        )
    
    @classmethod
    def unknown(cls, contact_id: str) -> "ContactInfo":
        """Create placeholder for unknown contact."""
        return cls(
            id=contact_id,
            name="Unknown",
            email=None,
            company=None,
        )


class ContactEnrichmentService:
    """Service for enriching queue items with contact information."""
    
    def __init__(self, hubspot_connector: Optional[HubSpotConnector] = None):
        """Initialize service.
        
        Args:
            hubspot_connector: Optional HubSpot connector. If not provided,
                will create one from environment settings.
        """
        self._connector = hubspot_connector
    
    @property
    def connector(self) -> HubSpotConnector:
        """Lazy-load HubSpot connector."""
        if self._connector is None:
            self._connector = create_hubspot_connector()
        return self._connector
    
    async def get_contact_info(self, contact_id: str) -> ContactInfo:
        """Get contact information by ID.
        
        Args:
            contact_id: HubSpot contact ID
            
        Returns:
            ContactInfo with name, email, etc.
        """
        # Check cache first
        if contact_id in _contact_cache:
            logger.debug("Contact cache hit", contact_id=contact_id)
            return _contact_cache[contact_id]
        
        # Fetch from HubSpot
        try:
            contact_data = await self.connector.get_contact(contact_id)
            if contact_data:
                info = ContactInfo.from_hubspot(contact_data)
                _contact_cache[contact_id] = info
                logger.info("Contact enriched", contact_id=contact_id, name=info.name)
                return info
        except Exception as e:
            logger.error("Failed to enrich contact", contact_id=contact_id, error=str(e))
        
        # Return unknown placeholder
        info = ContactInfo.unknown(contact_id)
        _contact_cache[contact_id] = info
        return info
    
    async def enrich_queue_items(
        self,
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enrich a list of queue items with contact information.
        
        Args:
            items: List of queue item dicts with contact_id field
            
        Returns:
            Same items with contact_name, contact_email added
        """
        # Collect all unique contact IDs
        contact_ids = {
            item.get("contact_id")
            for item in items
            if item.get("contact_id")
        }
        
        if not contact_ids:
            return items
        
        # Fetch all contacts in parallel
        tasks = [
            self.get_contact_info(cid)
            for cid in contact_ids
        ]
        contacts = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build lookup map
        contact_map: Dict[str, ContactInfo] = {}
        for result in contacts:
            if isinstance(result, ContactInfo):
                contact_map[result.id] = result
        
        # Enrich items
        enriched = []
        for item in items:
            item_copy = dict(item)
            cid = item_copy.get("contact_id")
            if cid and cid in contact_map:
                info = contact_map[cid]
                item_copy["contact_name"] = info.name
                item_copy["contact_email"] = info.email
                item_copy["contact_company"] = info.company
            enriched.append(item_copy)
        
        logger.info(
            "Enriched queue items",
            total_items=len(items),
            contacts_enriched=len(contact_map)
        )
        return enriched
    
    def clear_cache(self):
        """Clear the contact cache."""
        _contact_cache.clear()
        logger.info("Contact cache cleared")


# Singleton instance
_enrichment_service: Optional[ContactEnrichmentService] = None


def get_contact_enrichment_service() -> ContactEnrichmentService:
    """Get the singleton enrichment service."""
    global _enrichment_service
    if _enrichment_service is None:
        _enrichment_service = ContactEnrichmentService()
    return _enrichment_service
