"""Unit tests for main module."""
import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Fixture for FastAPI test client."""
    return TestClient(app)


def test_health_check_returns_ok(client):
    """Test that health check endpoint returns ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint_returns_service_info(client):
    """Test that root endpoint returns service information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "sales-agent"
    assert data["status"] == "running"
    assert "version" in data
    assert "environment" in data


def test_trace_id_propagates(client):
    """Test that trace_id is propagated in response headers."""
    trace_id = "test-trace-123"
    response = client.get("/health", headers={"X-Trace-ID": trace_id})
    assert response.headers["X-Trace-ID"] == trace_id
