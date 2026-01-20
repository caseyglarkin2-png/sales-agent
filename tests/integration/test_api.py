"""Integration tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Fixture for FastAPI test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_system_status(client):
    """Test system status endpoint."""
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "operator_mode" in data
    assert "rate_limits" in data


def test_prospecting_demo(client):
    """Test prospecting demo endpoint."""
    response = client.get("/api/agents/demo/prospecting")
    assert response.status_code == 200
    data = response.json()
    assert data["demo_type"] == "prospecting"
    assert "scenario" in data


def test_validation_demo(client):
    """Test validation demo endpoint."""
    response = client.get("/api/agents/demo/validation")
    assert response.status_code == 200
    data = response.json()
    assert data["demo_type"] == "validation"


def test_nurturing_demo(client):
    """Test nurturing demo endpoint."""
    response = client.get("/api/agents/demo/nurturing")
    assert response.status_code == 200
    data = response.json()
    assert data["demo_type"] == "nurturing"


def test_create_draft(client):
    """Test creating a draft."""
    response = client.post(
        "/api/operator/drafts?draft_id=draft-123",
        json={
            "recipient": "prospect@example.com",
            "subject": "Follow-up",
            "body": "Hi, I wanted to follow up on our earlier conversation about your growth strategy. Would you be available for a brief call next week?"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "draft-123"
    assert data["status"] in ["PENDING_APPROVAL", "APPROVED"]


def test_get_pending_drafts(client):
    """Test getting pending drafts."""
    # Create a draft first
    client.post(
        "/api/operator/drafts?draft_id=draft-pending",
        json={
            "recipient": "prospect@example.com",
            "subject": "Subject",
            "body": "This is a message body that is long enough to pass validation requirements."
        }
    )
    
    response = client.get("/api/operator/drafts/pending")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_approve_draft(client):
    """Test approving a draft."""
    # Create draft
    client.post(
        "/api/operator/drafts?draft_id=draft-approve",
        json={
            "recipient": "prospect@example.com",
            "subject": "Subject",
            "body": "This is a long enough message body for validation."
        }
    )
    
    # Approve draft
    response = client.post(
        "/api/operator/drafts/draft-approve/approve",
        json={"approved_by": "operator@company.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APPROVED"


def test_reject_draft(client):
    """Test rejecting a draft."""
    # Create draft
    client.post(
        "/api/operator/drafts?draft_id=draft-reject",
        json={
            "recipient": "prospect@example.com",
            "subject": "Subject",
            "body": "This is a long enough message body for validation."
        }
    )
    
    # Reject draft
    response = client.post(
        "/api/operator/drafts/draft-reject/reject",
        json={
            "reason": "Too generic",
            "rejected_by": "operator@company.com"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "REJECTED"


def test_get_quota(client):
    """Test getting quota for contact."""
    response = client.get("/api/operator/quota/prospect@example.com")
    assert response.status_code == 200
    data = response.json()
    assert "remaining_today" in data
    assert "remaining_this_week" in data
    assert "remaining_for_contact" in data
