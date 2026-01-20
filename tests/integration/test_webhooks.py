"""Integration tests for HubSpot form webhook and smoke test."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.routes.webhooks import FormSubmissionPayload


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestHubSpotWebhook:
    """Tests for HubSpot form submission webhook."""

    @staticmethod
    def example_payload() -> dict:
        """Generate example payload."""
        return {
            "portalId": 12345,
            "formId": "lead-interest-form",
            "formSubmissionId": "submission-test-001",
            "pageTitle": "Sales Demo Request",
            "pageUri": "https://company.com/demo",
            "timestamp": 1674150000000,
            "submitText": "Request Demo",
            "userMessage": None,
            "fieldValues": [
                {"name": "firstname", "value": "John"},
                {"name": "lastname", "value": "Doe"},
                {"name": "email", "value": "john@company.com"},
                {"name": "company", "value": "Company Inc"},
                {"name": "phone", "value": "+1-555-123-4567"},
            ],
        }

    def test_get_example_payload(self, client):
        """Test retrieving example payload."""
        response = client.get("/api/webhooks/hubspot/form-submission/example-payload")
        assert response.status_code == 200
        data = response.json()
        assert data["portalId"] == 12345
        assert data["formId"] == "lead-interest-form"
        assert data["fieldValues"]

    def test_webhook_test_endpoint_valid_payload(self, client):
        """Test webhook validation endpoint with valid payload."""
        payload = self.example_payload()
        response = client.post(
            "/api/webhooks/hubspot/form-submission/test",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["email"] == "john@company.com"
        assert data["company"] == "Company Inc"
        assert data["first_name"] == "John"
        assert data["received_fields"] == 5

    def test_webhook_test_endpoint_missing_email(self, client):
        """Test webhook with missing email field."""
        payload = self.example_payload()
        payload["fieldValues"] = [f for f in payload["fieldValues"] if f["name"] != "email"]
        response = client.post(
            "/api/webhooks/hubspot/form-submission/test",
            json=payload,
        )
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()

    def test_webhook_test_endpoint_invalid_form_id(self, client):
        """Test webhook with unexpected form ID."""
        payload = self.example_payload()
        payload["formId"] = "unknown-form-id"
        response = client.post(
            "/api/webhooks/hubspot/form-submission/test",
            json=payload,
        )
        # Note: Current implementation accepts any form ID in test mode
        # In production, would validate against expected forms
        assert response.status_code in [200, 400]

    def test_form_submission_payload_extract_email(self):
        """Test FormSubmissionPayload email extraction."""
        payload = FormSubmissionPayload(**self.example_payload())
        assert payload.get_email() == "john@company.com"

    def test_form_submission_payload_extract_name(self):
        """Test FormSubmissionPayload name extraction."""
        payload = FormSubmissionPayload(**self.example_payload())
        assert payload.get_first_name() == "John"
        assert payload.get_last_name() == "Doe"

    def test_form_submission_payload_extract_company(self):
        """Test FormSubmissionPayload company extraction."""
        payload = FormSubmissionPayload(**self.example_payload())
        assert payload.get_company() == "Company Inc"

    def test_form_submission_payload_get_field_case_insensitive(self):
        """Test FormSubmissionPayload case-insensitive field lookup."""
        payload = FormSubmissionPayload(**self.example_payload())
        assert payload.get_field("EMAIL") == "john@company.com"
        assert payload.get_field("Email") == "john@company.com"
        assert payload.get_field("email") == "john@company.com"

    def test_form_submission_payload_missing_field(self):
        """Test FormSubmissionPayload with missing field."""
        payload = FormSubmissionPayload(**self.example_payload())
        assert payload.get_field("nonexistent") is None

    def test_webhook_pydantic_validation(self):
        """Test Pydantic validation of payload."""
        invalid_payload = {
            "portalId": "invalid",  # Should be int
            "formId": "form-id",
            "formSubmissionId": "id",
            "timestamp": 123,
            "fieldValues": [],
        }
        with pytest.raises(Exception):  # ValidationError
            FormSubmissionPayload(**invalid_payload)

    def test_webhook_required_fields(self):
        """Test Pydantic validation of required fields."""
        invalid_payload = {
            "portalId": 123,
            # Missing formId, formSubmissionId, etc.
            "fieldValues": [],
        }
        with pytest.raises(Exception):
            FormSubmissionPayload(**invalid_payload)


class TestSmokeTestIntegration:
    """Tests for the smoke test workflow."""

    @pytest.mark.asyncio
    async def test_smoke_test_mock_mode(self):
        """Test smoke test in mock mode."""
        from src.commands.smoke_formlead import SmokeTestContext, run_smoke_test

        ctx = SmokeTestContext(mock=True)
        results = await run_smoke_test(ctx)

        assert results["final_status"] == "success"
        assert results["draft_id"]
        assert results["task_id"]
        assert "load_payload" in results["steps"]
        assert "hubspot_resolve" in results["steps"]
        assert "gmail_search" in results["steps"]
        assert "create_draft" in results["steps"]
        assert "create_hubspot_task" in results["steps"]

    @pytest.mark.asyncio
    async def test_smoke_test_skip_gmail(self):
        """Test smoke test skipping Gmail operations."""
        from src.commands.smoke_formlead import SmokeTestContext, run_smoke_test

        ctx = SmokeTestContext(mock=True, skip_gmail=True)
        results = await run_smoke_test(ctx)

        assert results["final_status"] == "success"
        assert results["steps"]["gmail_search"]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_smoke_test_skip_calendar(self):
        """Test smoke test skipping Calendar operations."""
        from src.commands.smoke_formlead import SmokeTestContext, run_smoke_test

        ctx = SmokeTestContext(mock=True, skip_calendar=True)
        results = await run_smoke_test(ctx)

        assert results["final_status"] == "success"
        assert results["steps"]["calendar_availability"]["status"] == "skipped"

    def test_smoke_test_records_steps(self):
        """Test that smoke test records all steps."""
        from src.commands.smoke_formlead import SmokeTestContext

        ctx = SmokeTestContext()
        ctx.record_step("test_step", "success", {"detail": "value"})

        assert "test_step" in ctx.results["steps"]
        assert ctx.results["steps"]["test_step"]["status"] == "success"
        assert ctx.results["steps"]["test_step"]["details"]["detail"] == "value"


class TestWebhookEndpointIntegration:
    """Integration tests for webhook endpoints."""

    def test_health_check_before_webhook(self, client):
        """Verify API is healthy before testing webhooks."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_webhook_endpoint_exists(self, client):
        """Test that webhook endpoint exists."""
        # Send OPTIONS request to check endpoint exists
        response = client.options("/api/webhooks/hubspot/form-submission")
        # Expect either 405 (Method Not Allowed) or 200, but not 404
        assert response.status_code != 404

    def test_webhook_returns_202_on_valid_submission(self, client):
        """Test webhook returns 202 Accepted for valid submission."""
        payload = {
            "portalId": 12345,
            "formId": "lead-interest-form",
            "formSubmissionId": "submission-test-001",
            "pageTitle": "Demo",
            "pageUri": "https://example.com",
            "timestamp": 1674150000000,
            "fieldValues": [
                {"name": "email", "value": "test@example.com"},
                {"name": "firstname", "value": "Test"},
            ],
        }
        response = client.post(
            "/api/webhooks/hubspot/form-submission",
            json=payload,
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["submission_id"] == "submission-test-001"
        assert data["email"] == "test@example.com"

    def test_webhook_content_type_validation(self, client):
        """Test webhook requires JSON content-type."""
        payload = "not json"
        response = client.post(
            "/api/webhooks/hubspot/form-submission",
            content=payload,
            headers={"Content-Type": "text/plain"},
        )
        # Should reject or return 422 for invalid JSON
        assert response.status_code in [400, 422, 415]


class TestWebhookSecurity:
    """Security tests for webhook endpoints."""

    def test_webhook_rejects_extra_fields(self, client):
        """Test webhook validation is strict about field types."""
        payload = {
            "portalId": "not-an-int",  # Should be int
            "formId": "form-id",
            "formSubmissionId": "id",
            "timestamp": 123,
            "fieldValues": [],
        }
        response = client.post(
            "/api/webhooks/hubspot/form-submission/test",
            json=payload,
        )
        assert response.status_code == 422  # Unprocessable Entity

    def test_webhook_requires_all_fields(self, client):
        """Test webhook requires all required fields."""
        payload = {
            "formId": "form-id",
            # Missing portalId, formSubmissionId, etc.
            "fieldValues": [],
        }
        response = client.post(
            "/api/webhooks/hubspot/form-submission/test",
            json=payload,
        )
        assert response.status_code == 422

    def test_webhook_large_payload_handling(self, client):
        """Test webhook handles large payloads gracefully."""
        payload = {
            "portalId": 12345,
            "formId": "form-id",
            "formSubmissionId": "id",
            "timestamp": 123,
            "fieldValues": [
                {"name": f"field_{i}", "value": "x" * 1000}
                for i in range(100)
            ],  # 100 fields
        }
        # Should either accept or reject gracefully, not crash
        response = client.post(
            "/api/webhooks/hubspot/form-submission/test",
            json=payload,
        )
        assert response.status_code in [200, 400, 422]


class TestWorkflowMocking:
    """Tests with mocked external services."""

    @patch("src.commands.smoke_formlead.datetime")
    def test_smoke_test_timestamp_handling(self, mock_datetime):
        """Test smoke test handles timestamps correctly."""
        from src.commands.smoke_formlead import SmokeTestContext

        ctx = SmokeTestContext(mock=True)
        assert "timestamp" in ctx.results
        assert "T" in ctx.results["timestamp"]  # ISO format


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
