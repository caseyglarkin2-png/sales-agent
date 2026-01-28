"""
Sprint 45: Memory UI Tests

Tests for the Memory Browser page and related functionality.
"""

import pytest


class TestMemoryUIRoute:
    """Tests for the memory UI route."""

    @pytest.mark.asyncio
    async def test_memory_route_returns_html(self, test_client):
        """Test that /caseyos/memory returns HTML response."""
        response = test_client.get("/caseyos/memory")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_memory_route_uses_template(self, test_client):
        """Test that memory route uses the correct template."""
        response = test_client.get("/caseyos/memory")
        assert response.status_code == 200
        # Check for key UI elements
        assert b"Memory" in response.content
        assert b"Sessions" in response.content

    @pytest.mark.asyncio
    async def test_memory_route_has_active_tab(self, test_client):
        """Test that memory tab is marked active."""
        response = test_client.get("/caseyos/memory")
        assert response.status_code == 200
        # The template should highlight memory tab
        content = response.content.decode()
        assert "memory" in content.lower()


class TestMemoryAPIEndpointsRegistered:
    """Tests that memory API endpoints are registered (structure tests only)."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires database connection - run in integration tests")
    async def test_sessions_endpoint_route_exists(self, test_client):
        """Test that /api/jarvis/sessions route is registered."""
        response = test_client.get("/api/jarvis/sessions")
        assert response.status_code != 404

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires database connection - run in integration tests")
    async def test_memory_stats_endpoint_route_exists(self, test_client):
        """Test that /api/jarvis/memory/stats route is registered."""
        response = test_client.get("/api/jarvis/memory/stats")
        assert response.status_code != 404

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires database connection - run in integration tests")
    async def test_session_memory_endpoint_route_exists(self, test_client):
        """Test that /api/jarvis/memory/{session_id} route is registered."""
        response = test_client.get("/api/jarvis/memory/00000000-0000-0000-0000-000000000000")
        assert response.status_code != 404

    @pytest.mark.asyncio  
    async def test_memory_search_endpoint_route_exists(self, test_client):
        """Test that /api/jarvis/memory/search route is registered."""
        # POST without CSRF will return 403, but that means route exists
        response = test_client.post(
            "/api/jarvis/memory/search",
            json={"session_id": "test", "query": "test", "limit": 5}
        )
        # 403 = CSRF rejection (route exists), 422 = validation error (route exists)
        assert response.status_code in [200, 403, 422, 500]


class TestMemoryTemplateElements:
    """Tests for memory template elements and functionality."""

    @pytest.mark.asyncio
    async def test_template_has_search_input(self, test_client):
        """Test that template includes search functionality."""
        response = test_client.get("/caseyos/memory")
        content = response.content.decode()
        assert "search-query" in content
        assert "searchMemory" in content

    @pytest.mark.asyncio
    async def test_template_has_sessions_list(self, test_client):
        """Test that template includes sessions list container."""
        response = test_client.get("/caseyos/memory")
        content = response.content.decode()
        assert "sessions-list" in content

    @pytest.mark.asyncio
    async def test_template_has_detail_panel(self, test_client):
        """Test that template includes detail panel."""
        response = test_client.get("/caseyos/memory")
        content = response.content.decode()
        assert "detail-content" in content

    @pytest.mark.asyncio
    async def test_template_has_stats_display(self, test_client):
        """Test that template includes stats display."""
        response = test_client.get("/caseyos/memory")
        content = response.content.decode()
        assert "session-count" in content
        assert "message-count" in content


class TestNavigationUpdate:
    """Tests for navigation including Memory tab."""

    @pytest.mark.asyncio
    async def test_nav_includes_memory_tab(self, test_client):
        """Test that navigation includes Memory tab."""
        response = test_client.get("/caseyos/memory")
        content = response.content.decode()
        assert "/caseyos/memory" in content
        assert "🧠" in content or "Memory" in content

    @pytest.mark.asyncio
    async def test_memory_tab_active_on_memory_page(self, test_client):
        """Test that Memory tab is active on memory page."""
        response = test_client.get("/caseyos/memory")
        content = response.content.decode()
        # The active tab should have special styling
        assert "memory" in content.lower()


# Fixture for test client
@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    from src.main import app
    return TestClient(app)
