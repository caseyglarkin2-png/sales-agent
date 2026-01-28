"""Tests for UI routes - Sprint 42."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.fixture
def async_client():
    """Create async client for testing."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestExecutionsUIRoute:
    """Tests for the executions UI route."""

    @pytest.mark.asyncio
    async def test_executions_page_loads(self, async_client):
        """GET /caseyos/executions returns 200."""
        async with async_client as client:
            response = await client.get("/caseyos/executions")
        
        assert response.status_code == 200
        assert "Execution History" in response.text

    @pytest.mark.asyncio
    async def test_executions_page_has_stats(self, async_client):
        """Executions page includes stats section."""
        async with async_client as client:
            response = await client.get("/caseyos/executions")
        
        assert response.status_code == 200
        assert "stat-total" in response.text
        assert "stat-success" in response.text
        assert "stat-failed" in response.text

    @pytest.mark.asyncio
    async def test_executions_page_has_filters(self, async_client):
        """Executions page includes filter controls."""
        async with async_client as client:
            response = await client.get("/caseyos/executions")
        
        assert response.status_code == 200
        assert "filter-status" in response.text
        assert "filter-domain" in response.text

    @pytest.mark.asyncio
    async def test_executions_page_has_table(self, async_client):
        """Executions page includes executions table."""
        async with async_client as client:
            response = await client.get("/caseyos/executions")
        
        assert response.status_code == 200
        assert "executions-body" in response.text

    @pytest.mark.asyncio
    async def test_executions_page_has_modal(self, async_client):
        """Executions page includes detail modal."""
        async with async_client as client:
            response = await client.get("/caseyos/executions")
        
        assert response.status_code == 200
        assert "exec-modal" in response.text

    @pytest.mark.asyncio
    async def test_executions_page_has_retry_button(self, async_client):
        """Executions page includes retry button in modal."""
        async with async_client as client:
            response = await client.get("/caseyos/executions")
        
        assert response.status_code == 200
        assert "retryExecution" in response.text
        assert "modal-retry-section" in response.text

    @pytest.mark.asyncio
    async def test_executions_page_has_error_display(self, async_client):
        """Executions page includes error traceback display."""
        async with async_client as client:
            response = await client.get("/caseyos/executions")
        
        assert response.status_code == 200
        assert "modal-error-section" in response.text
        assert "modal-traceback" in response.text

    @pytest.mark.asyncio
    async def test_executions_nav_link(self, async_client):
        """Executions link appears in navigation."""
        async with async_client as client:
            response = await client.get("/caseyos/executions")
        
        assert response.status_code == 200
        # Check navigation includes executions link
        assert "/caseyos/executions" in response.text
        assert "⚡ Executions" in response.text


class TestOtherUIRoutes:
    """Basic tests for other UI routes."""

    @pytest.mark.asyncio
    async def test_agents_page_loads(self, async_client):
        """GET /caseyos/agents returns 200."""
        async with async_client as client:
            response = await client.get("/caseyos/agents")
        
        assert response.status_code == 200
        assert "Agents" in response.text

    @pytest.mark.asyncio
    async def test_agents_page_has_run_now_button(self, async_client):
        """Agents page includes Run Now button in modal."""
        async with async_client as client:
            response = await client.get("/caseyos/agents")
        
        assert response.status_code == 200
        assert "Run Now" in response.text
        assert "execute-modal" in response.text

    @pytest.mark.asyncio
    async def test_agents_page_has_execute_form(self, async_client):
        """Agents page includes execute form elements."""
        async with async_client as client:
            response = await client.get("/caseyos/agents")
        
        assert response.status_code == 200
        assert "exec-context" in response.text
        assert "executeAgent" in response.text

    @pytest.mark.asyncio
    async def test_queue_page_loads(self, async_client):
        """GET /caseyos/queue returns 200."""
        async with async_client as client:
            response = await client.get("/caseyos/queue")
        
        assert response.status_code == 200
