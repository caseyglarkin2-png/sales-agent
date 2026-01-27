"""Production health check tests.

These tests run against the live production deployment.
"""
import os
import httpx
import pytest

PRODUCTION_URL = os.getenv("PRODUCTION_URL", "https://web-production-a6ccf.up.railway.app")


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test that the health endpoint is responding."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{PRODUCTION_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"


@pytest.mark.asyncio
async def test_root_redirect():
    """Test that root redirects to CaseyOS."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(f"{PRODUCTION_URL}/")
        # Should end up at login or dashboard
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_caseyos_accessible():
    """Test that CaseyOS UI is accessible."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(f"{PRODUCTION_URL}/caseyos")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_agents_api():
    """Test that the agents API is responding (Sprint 41)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{PRODUCTION_URL}/api/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert "total" in data
        assert data["total"] >= 30  # We have 31+ agents now
