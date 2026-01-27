"""Tests for contact enrichment service.

Sprint 39B: Verify contact enrichment for queue items.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.contact_enrichment import (
    ContactEnrichmentService,
    ContactInfo,
    get_contact_enrichment_service,
    _contact_cache,
)


class TestContactInfo:
    """Test ContactInfo dataclass."""

    def test_from_hubspot_full_data(self):
        """Create ContactInfo from complete HubSpot response."""
        hubspot_data = {
            "id": "123",
            "properties": {
                "firstname": "John",
                "lastname": "Doe",
                "email": "john@example.com",
                "company": "Acme Inc",
            }
        }
        info = ContactInfo.from_hubspot(hubspot_data)
        
        assert info.id == "123"
        assert info.name == "John Doe"
        assert info.email == "john@example.com"
        assert info.company == "Acme Inc"

    def test_from_hubspot_missing_fields(self):
        """Handle missing fields gracefully."""
        hubspot_data = {
            "id": "456",
            "properties": {
                "email": "unknown@example.com",
            }
        }
        info = ContactInfo.from_hubspot(hubspot_data)
        
        assert info.id == "456"
        assert info.name == "Unknown Contact"
        assert info.email == "unknown@example.com"
        assert info.company is None

    def test_from_hubspot_empty_names(self):
        """Handle empty name strings."""
        hubspot_data = {
            "id": "789",
            "properties": {
                "firstname": "",
                "lastname": "",
            }
        }
        info = ContactInfo.from_hubspot(hubspot_data)
        assert info.name == "Unknown Contact"

    def test_unknown_contact(self):
        """Create placeholder for unknown contact."""
        info = ContactInfo.unknown("unknown-id")
        
        assert info.id == "unknown-id"
        assert info.name == "Unknown"
        assert info.email is None
        assert info.company is None


class TestContactEnrichmentService:
    """Test ContactEnrichmentService."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before each test."""
        _contact_cache.clear()
        yield
        _contact_cache.clear()

    @pytest.mark.asyncio
    async def test_get_contact_info_from_hubspot(self):
        """Fetch contact info from HubSpot."""
        mock_connector = MagicMock()
        mock_connector.get_contact = AsyncMock(return_value={
            "id": "12345",
            "properties": {
                "firstname": "Jane",
                "lastname": "Smith",
                "email": "jane@company.com",
                "company": "TechCorp",
            }
        })
        
        service = ContactEnrichmentService(hubspot_connector=mock_connector)
        info = await service.get_contact_info("12345")
        
        assert info.id == "12345"
        assert info.name == "Jane Smith"
        assert info.email == "jane@company.com"
        assert info.company == "TechCorp"
        mock_connector.get_contact.assert_called_once_with("12345")

    @pytest.mark.asyncio
    async def test_get_contact_info_uses_cache(self):
        """Subsequent calls should use cache."""
        mock_connector = MagicMock()
        mock_connector.get_contact = AsyncMock(return_value={
            "id": "cached",
            "properties": {"firstname": "Cached", "lastname": "User"}
        })
        
        service = ContactEnrichmentService(hubspot_connector=mock_connector)
        
        # First call
        await service.get_contact_info("cached")
        # Second call
        await service.get_contact_info("cached")
        
        # Should only call HubSpot once
        mock_connector.get_contact.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_contact_info_handles_error(self):
        """Handle HubSpot API errors gracefully."""
        mock_connector = MagicMock()
        mock_connector.get_contact = AsyncMock(side_effect=Exception("API Error"))
        
        service = ContactEnrichmentService(hubspot_connector=mock_connector)
        info = await service.get_contact_info("error-id")
        
        # Should return unknown placeholder
        assert info.name == "Unknown"
        assert info.id == "error-id"

    @pytest.mark.asyncio
    async def test_enrich_queue_items(self):
        """Enrich multiple queue items with contact info."""
        mock_connector = MagicMock()
        mock_connector.get_contact = AsyncMock(side_effect=[
            {"id": "c1", "properties": {"firstname": "Alice", "lastname": "One", "email": "alice@test.com"}},
            {"id": "c2", "properties": {"firstname": "Bob", "lastname": "Two", "company": "BobCorp"}},
        ])
        
        service = ContactEnrichmentService(hubspot_connector=mock_connector)
        
        items = [
            {"id": "item1", "title": "Task 1", "contact_id": "c1"},
            {"id": "item2", "title": "Task 2", "contact_id": "c2"},
            {"id": "item3", "title": "Task 3", "contact_id": None},  # No contact
        ]
        
        enriched = await service.enrich_queue_items(items)
        
        assert len(enriched) == 3
        assert enriched[0]["contact_name"] == "Alice One"
        assert enriched[0]["contact_email"] == "alice@test.com"
        assert enriched[1]["contact_name"] == "Bob Two"
        assert enriched[1]["contact_company"] == "BobCorp"
        assert "contact_name" not in enriched[2] or enriched[2].get("contact_name") is None

    @pytest.mark.asyncio
    async def test_enrich_queue_items_empty_list(self):
        """Handle empty item list."""
        mock_connector = MagicMock()
        service = ContactEnrichmentService(hubspot_connector=mock_connector)
        
        enriched = await service.enrich_queue_items([])
        
        assert enriched == []
        mock_connector.get_contact.assert_not_called()

    def test_clear_cache(self):
        """Cache can be cleared."""
        _contact_cache["test"] = ContactInfo.unknown("test")
        assert "test" in _contact_cache
        
        service = ContactEnrichmentService()
        service.clear_cache()
        
        assert "test" not in _contact_cache


class TestGetContactEnrichmentService:
    """Test singleton getter."""

    def test_returns_singleton(self):
        """Should return the same instance."""
        service1 = get_contact_enrichment_service()
        service2 = get_contact_enrichment_service()
        
        assert service1 is service2
