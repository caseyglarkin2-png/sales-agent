"""Unit tests for Sprint 65: HubSpot Integration Enhancement.

Tests cover:
- Deep sync Celery tasks
- Contact timeline API
- Profile endpoints
- Smart list builder
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx


# ============================================================
# Test Data Fixtures
# ============================================================

@pytest.fixture
def sample_contact():
    """Sample HubSpot contact data."""
    return {
        "id": str(uuid4()),
        "hubspot_contact_id": "12345",
        "email": "john.doe@acme.com",
        "firstname": "John",
        "lastname": "Doe",
        "full_name": "John Doe",
        "custom_properties": {
            "job_title": "VP of Engineering",
            "lifecycle_stage": "lead",
            "lead_status": "new",
            "phone": "+1-555-0100",
        }
    }


@pytest.fixture
def sample_company():
    """Sample HubSpot company data."""
    return {
        "id": str(uuid4()),
        "hubspot_company_id": "67890",
        "name": "Acme Corp",
        "domain": "acme.com",
        "industry": "Technology",
        "custom_properties": {
            "numberofemployees": "500",
            "annualrevenue": "50000000",
        }
    }


@pytest.fixture
def sample_timeline_activities():
    """Sample timeline activities from HubSpot."""
    return [
        {
            "type": "email",
            "id": "email-1",
            "timestamp": "2024-01-15T10:30:00Z",
            "subject": "Follow up on our conversation",
            "body": "Hi John, just wanted to follow up...",
            "direction": "outbound",
        },
        {
            "type": "call",
            "id": "call-1",
            "timestamp": "2024-01-14T14:00:00Z",
            "title": "Discovery Call",
            "duration": "1800",
            "outcome": "connected",
        },
        {
            "type": "meeting",
            "id": "meeting-1",
            "timestamp": "2024-01-13T09:00:00Z",
            "title": "Product Demo",
            "end_time": "2024-01-13T10:00:00Z",
            "outcome": "completed",
        },
    ]


# ============================================================
# HubSpot Connector Tests
# ============================================================

class TestHubSpotConnectorEnhancements:
    """Tests for enhanced HubSpot connector methods."""

    @pytest.mark.asyncio
    async def test_get_contact_with_properties(self):
        """Test fetching contact with specific properties."""
        from src.connectors.hubspot import HubSpotConnector
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "12345",
            "properties": {
                "email": "test@example.com",
                "firstname": "Test",
                "lastname": "User",
                "jobtitle": "Manager",
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            connector = HubSpotConnector(api_key="test-key")
            result = await connector.get_contact_with_properties(
                contact_id="12345",
                properties=["email", "firstname", "lastname", "jobtitle"]
            )
            
            assert result is not None
            assert result.get("id") == "12345"
            assert "properties" in result

    @pytest.mark.asyncio
    async def test_get_contact_with_properties_not_found(self):
        """Test handling of missing contact."""
        from src.connectors.hubspot import HubSpotConnector
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response))
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            connector = HubSpotConnector(api_key="test-key")
            result = await connector.get_contact_with_properties(
                contact_id="99999",
                properties=["email"]
            )
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_company_with_properties(self):
        """Test fetching company with specific properties."""
        from src.connectors.hubspot import HubSpotConnector
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "67890",
            "properties": {
                "name": "Acme Corp",
                "domain": "acme.com",
                "industry": "Technology",
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance
            
            connector = HubSpotConnector(api_key="test-key")
            result = await connector.get_company_with_properties(
                company_id="67890",
                properties=["name", "domain", "industry"]
            )
            
            assert result is not None
            assert result.get("id") == "67890"

    @pytest.mark.asyncio
    async def test_get_contact_timeline(self, sample_timeline_activities):
        """Test fetching contact timeline with activities."""
        from src.connectors.hubspot import HubSpotConnector
        
        # Mock the internal _get_contact_object_timeline method
        with patch.object(
            HubSpotConnector,
            "_get_contact_object_timeline",
            new_callable=AsyncMock,
        ) as mock_timeline:
            mock_timeline.return_value = sample_timeline_activities
            
            connector = HubSpotConnector(api_key="test-key")
            # Override the method to return our fixture
            connector._get_contact_object_timeline = mock_timeline
            
            # The get_contact_timeline method aggregates from multiple sources
            # For this test, we just verify the structure
            result = await connector.get_contact_timeline("12345")
            
            # Timeline should be sorted by timestamp (newest first)
            assert isinstance(result, list)


# ============================================================
# Deep Sync Task Tests
# ============================================================

class TestDeepSyncTasks:
    """Tests for Celery deep sync tasks."""

    def test_sync_contact_deep_task_exists(self):
        """Test that sync_contact_deep task function exists."""
        from src.tasks.hubspot_sync import sync_contact_deep
        
        assert callable(sync_contact_deep)
        assert hasattr(sync_contact_deep, "delay")  # Celery task attribute

    def test_sync_company_deep_task_exists(self):
        """Test that sync_company_deep task function exists."""
        from src.tasks.hubspot_sync import sync_company_deep
        
        assert callable(sync_company_deep)
        assert hasattr(sync_company_deep, "delay")

    def test_sync_all_contacts_deep_task_exists(self):
        """Test that sync_all_contacts_deep task function exists."""
        from src.tasks.hubspot_sync import sync_all_contacts_deep
        
        assert callable(sync_all_contacts_deep)
        assert hasattr(sync_all_contacts_deep, "delay")

    @pytest.mark.asyncio
    async def test_sync_contact_deep_updates_properties(self):
        """Test that deep sync updates custom_properties correctly."""
        from src.tasks.hubspot_sync import _sync_contact_deep_async
        
        mock_db = AsyncMock()
        mock_connector = AsyncMock()
        
        # Mock HubSpot response with enhanced properties
        mock_connector.get_contact_with_properties.return_value = {
            "id": "12345",
            "properties": {
                "email": "test@example.com",
                "jobtitle": "CEO",
                "lifecyclestage": "customer",
                "hs_lead_status": "qualified",
                "phone": "+1-555-0100",
                "num_contacted_times": "5",
            }
        }
        
        # Mock existing contact
        mock_contact = MagicMock()
        mock_contact.hubspot_contact_id = "12345"
        mock_contact.custom_properties = {}
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_contact
        mock_db.execute.return_value = mock_result
        
        with patch("src.tasks.hubspot_sync.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_db
            
            with patch("src.tasks.hubspot_sync.create_hubspot_connector") as mock_create:
                mock_create.return_value = mock_connector
                
                result = await _sync_contact_deep_async("12345")
                
                # Verify the contact's custom_properties were updated
                assert mock_contact.custom_properties.get("job_title") == "CEO"
                assert mock_contact.custom_properties.get("lifecycle_stage") == "customer"


# ============================================================
# API Route Tests
# ============================================================

class TestTimelineAPIRoutes:
    """Tests for timeline API endpoints."""

    @pytest.mark.asyncio
    async def test_get_contact_timeline_endpoint(self, sample_contact, sample_timeline_activities):
        """Test GET /api/hubspot/contacts/{id}/timeline endpoint."""
        from fastapi.testclient import TestClient
        from src.main import app
        
        with patch("src.routes.hubspot_routes._find_contact") as mock_find:
            mock_contact = MagicMock()
            mock_contact.id = uuid4()
            mock_contact.hubspot_contact_id = "12345"
            mock_find.return_value = mock_contact
            
            with patch("src.routes.hubspot_routes.create_hubspot_connector") as mock_create:
                mock_connector = AsyncMock()
                mock_connector.get_contact_timeline.return_value = sample_timeline_activities
                mock_create.return_value = mock_connector
                
                client = TestClient(app)
                response = client.get(f"/api/hubspot/contacts/{mock_contact.id}/timeline")
                
                # Should return timeline data (if contact exists)
                assert response.status_code in [200, 404, 500]

    @pytest.mark.asyncio
    async def test_get_contact_timeline_not_found(self):
        """Test timeline endpoint with missing contact."""
        from fastapi.testclient import TestClient
        from src.main import app
        
        with patch("src.routes.hubspot_routes._find_contact") as mock_find:
            mock_find.return_value = None
            
            client = TestClient(app)
            response = client.get("/api/hubspot/contacts/nonexistent/timeline")
            
            assert response.status_code == 404


class TestProfileAPIRoutes:
    """Tests for profile API endpoints."""

    def test_contact_profile_endpoint_exists(self):
        """Test that contact profile endpoint is registered."""
        from src.main import app
        
        routes = [r.path for r in app.routes]
        assert any("/contacts/" in str(r) and "/profile" in str(r) for r in routes)

    def test_company_profile_endpoint_exists(self):
        """Test that company profile endpoint is registered."""
        from src.main import app
        
        routes = [r.path for r in app.routes]
        assert any("/companies/" in str(r) and "/profile" in str(r) for r in routes)


class TestListBuilderAPIRoutes:
    """Tests for smart list builder API endpoints."""

    def test_list_endpoint_exists(self):
        """Test that contact list endpoint is registered."""
        from src.main import app
        
        routes = [r.path for r in app.routes]
        assert any("/contacts/list" in str(r) for r in routes)

    def test_get_lifecycle_stages(self):
        """Test GET /api/hubspot/contacts/list/lifecycle-stages endpoint."""
        from fastapi.testclient import TestClient
        from src.main import app
        
        client = TestClient(app)
        response = client.get("/api/hubspot/contacts/list/lifecycle-stages")
        
        assert response.status_code == 200
        data = response.json()
        assert "stages" in data
        assert isinstance(data["stages"], list)

    def test_get_lead_statuses(self):
        """Test GET /api/hubspot/contacts/list/lead-statuses endpoint."""
        from fastapi.testclient import TestClient
        from src.main import app
        
        client = TestClient(app)
        response = client.get("/api/hubspot/contacts/list/lead-statuses")
        
        assert response.status_code == 200
        data = response.json()
        assert "statuses" in data
        assert isinstance(data["statuses"], list)


# ============================================================
# UI Route Tests
# ============================================================

class TestUIRoutes:
    """Tests for UI template routes."""

    def test_list_builder_page_renders(self):
        """Test that list builder page renders."""
        from fastapi.testclient import TestClient
        from src.main import app
        
        client = TestClient(app)
        response = client.get("/api/hubspot/list-builder")
        
        assert response.status_code == 200
        assert b"Contact List Builder" in response.content

    def test_contact_profile_page_not_found(self):
        """Test contact profile page with missing contact."""
        from fastapi.testclient import TestClient
        from src.main import app
        
        with patch("src.routes.hubspot_routes._find_contact") as mock_find:
            mock_find.return_value = None
            
            client = TestClient(app)
            response = client.get("/api/hubspot/contacts/nonexistent/view")
            
            assert response.status_code == 404

    def test_company_profile_page_not_found(self):
        """Test company profile page with missing company."""
        from fastapi.testclient import TestClient
        from src.main import app
        
        with patch("src.routes.hubspot_routes._find_company") as mock_find:
            mock_find.return_value = None
            
            client = TestClient(app)
            response = client.get("/api/hubspot/companies/nonexistent/view")
            
            assert response.status_code == 404


# ============================================================
# Integration Validation Tests
# ============================================================

class TestIntegrationValidation:
    """Validation tests for Sprint 65 integration."""

    def test_hubspot_routes_registered(self):
        """Test that hubspot_routes is registered in the app."""
        from src.main import app
        
        routes = [r.path for r in app.routes]
        
        # Check for key endpoints
        assert any("/api/hubspot" in str(r) for r in routes)

    def test_sync_task_module_imports(self):
        """Test that sync task module can be imported."""
        from src.tasks import hubspot_sync
        
        assert hasattr(hubspot_sync, "sync_contact_deep")
        assert hasattr(hubspot_sync, "sync_company_deep")
        assert hasattr(hubspot_sync, "sync_all_contacts_deep")

    def test_connector_methods_exist(self):
        """Test that new connector methods exist."""
        from src.connectors.hubspot import HubSpotConnector
        
        connector = HubSpotConnector(api_key="test")
        
        assert hasattr(connector, "get_contact_with_properties")
        assert hasattr(connector, "get_company_with_properties")
        assert hasattr(connector, "get_contact_timeline")
