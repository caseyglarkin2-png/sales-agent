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
    data = response.json()
    assert data["status"] == "ok"
    # Timestamp may or may not be present depending on implementation


def test_root_endpoint_returns_dashboard(client):
    """Test that root endpoint returns dashboard HTML or service info."""
    response = client.get("/")
    assert response.status_code == 200
    # Root now returns HTML dashboard if static file exists, otherwise JSON
    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        assert "Sales Agent" in response.text
    else:
        data = response.json()
        assert data["service"] == "sales-agent"
        assert data["status"] == "running"


def test_trace_id_propagates(client):
    """Test that trace_id is propagated in response headers."""
    trace_id = "test-trace-123"
    response = client.get("/health", headers={"X-Trace-ID": trace_id})
    assert response.headers["X-Trace-ID"] == trace_id
