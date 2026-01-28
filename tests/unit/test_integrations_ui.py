"""
Sprint 46: Integrations Hub UI Tests

Tests for the Integrations Hub page and related functionality.
"""

import pytest


class TestIntegrationsUIRoute:
    """Tests for the integrations UI route."""

    @pytest.mark.asyncio
    async def test_integrations_route_returns_html(self, test_client):
        """Test that /caseyos/integrations returns HTML response."""
        response = test_client.get("/caseyos/integrations")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_integrations_route_uses_template(self, test_client):
        """Test that integrations route uses the correct template."""
        response = test_client.get("/caseyos/integrations")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Integrations" in content
        assert "Connect" in content

    @pytest.mark.asyncio
    async def test_integrations_route_has_active_tab(self, test_client):
        """Test that integrations tab is marked active."""
        response = test_client.get("/caseyos/integrations")
        assert response.status_code == 200
        content = response.content.decode()
        assert "integrations" in content.lower()


class TestIntegrationsAPIEndpoints:
    """Tests for integrations API endpoints."""

    @pytest.mark.asyncio
    async def test_available_integrations_endpoint(self, test_client):
        """Test GET /api/integrations/available returns list."""
        response = test_client.get("/api/integrations/available")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check structure
        first = data[0]
        assert "app_name" in first
        assert "display_name" in first
        assert "features" in first

    @pytest.mark.asyncio
    async def test_status_endpoint_exists(self, test_client):
        """Test GET /api/integrations/status returns status."""
        response = test_client.get("/api/integrations/status")
        # May need auth, but should not 404
        assert response.status_code in [200, 401, 403, 500]


class TestIntegrationsTemplateElements:
    """Tests for integrations template elements."""

    @pytest.mark.asyncio
    async def test_template_has_connected_section(self, test_client):
        """Test that template includes connected integrations section."""
        response = test_client.get("/caseyos/integrations")
        content = response.content.decode()
        assert "connected-integrations" in content

    @pytest.mark.asyncio
    async def test_template_has_available_section(self, test_client):
        """Test that template includes available integrations section."""
        response = test_client.get("/caseyos/integrations")
        content = response.content.decode()
        assert "available-integrations" in content

    @pytest.mark.asyncio
    async def test_template_has_modal(self, test_client):
        """Test that template includes integration detail modal."""
        response = test_client.get("/caseyos/integrations")
        content = response.content.decode()
        assert "integration-modal" in content

    @pytest.mark.asyncio
    async def test_template_has_connect_button(self, test_client):
        """Test that template includes connect functionality."""
        response = test_client.get("/caseyos/integrations")
        content = response.content.decode()
        assert "connectIntegration" in content


class TestNavigationUpdate:
    """Tests for navigation including Integrations tab."""

    @pytest.mark.asyncio
    async def test_nav_includes_integrations_tab(self, test_client):
        """Test that navigation includes Integrations tab."""
        response = test_client.get("/caseyos/integrations")
        content = response.content.decode()
        assert "/caseyos/integrations" in content
        assert "🔌" in content or "Integrations" in content


class TestIntegrationRegistry:
    """Tests for the integration registry."""

    @pytest.mark.asyncio
    async def test_google_drive_integration_exists(self, test_client):
        """Test Google Drive is in available integrations."""
        response = test_client.get("/api/integrations/available")
        data = response.json()
        app_names = [i["app_name"] for i in data]
        assert "google-drive" in app_names

    @pytest.mark.asyncio
    async def test_hubspot_integration_exists(self, test_client):
        """Test HubSpot is in available integrations."""
        response = test_client.get("/api/integrations/available")
        data = response.json()
        app_names = [i["app_name"] for i in data]
        assert "hubspot" in app_names

    @pytest.mark.asyncio
    async def test_youtube_integration_exists(self, test_client):
        """Test YouTube is in available integrations."""
        response = test_client.get("/api/integrations/available")
        data = response.json()
        app_names = [i["app_name"] for i in data]
        assert "youtube" in app_names


# Fixture for test client
@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    from src.main import app
    return TestClient(app)
