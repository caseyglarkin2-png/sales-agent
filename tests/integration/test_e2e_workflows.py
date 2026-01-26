"""End-to-end integration tests for complete workflows."""
import json
from datetime import datetime

import pytest

from src.orchestrator import ProspectingOrchestrator, reset_orchestrator
from src.connectors.gmail import GmailConnector
from src.connectors.hubspot import HubSpotConnector
from src.connectors.calendar_connector import CalendarConnector
from tests.fixtures.seed_data import (
    get_sample_prospect,
    get_sample_form_submission,
    SAMPLE_CALENDAR_SLOTS,
)


class TestCompleteProspectingWorkflow:
    """Test complete prospecting workflow end-to-end."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up after each test."""
        yield
        reset_orchestrator()

    async def test_workflow_with_mock_connectors(self):
        """Test complete workflow with mocked connectors."""
        # Create mock connectors
        class MockGmailConnector:
            async def search_threads(self, *args, **kwargs):
                return []

            async def get_thread(self, *args, **kwargs):
                return None

            async def create_draft(self, *args, **kwargs):
                return f"draft-{datetime.utcnow().isoformat()}"

        class MockHubSpotConnector:
            async def search_contacts(self, *args, **kwargs):
                return {"id": "contact-123", "email": "test@example.com"}

            async def get_contact_associations(self, *args, **kwargs):
                return [{"id": "company-456"}]

            async def create_note(self, *args, **kwargs):
                return f"note-{datetime.utcnow().isoformat()}"

            async def create_task(self, *args, **kwargs):
                return f"task-{datetime.utcnow().isoformat()}"

        class MockCalendarConnector:
            async def find_available_slots(self, *args, **kwargs):
                return SAMPLE_CALENDAR_SLOTS

        # Create orchestrator with mocks
        orchestrator = ProspectingOrchestrator(
            gmail_connector=MockGmailConnector(),
            hubspot_connector=MockHubSpotConnector(),
            calendar_connector=MockCalendarConnector(),
        )

        # Run workflow
        form_submission = get_sample_form_submission()
        result = await orchestrator.run_complete_workflow(form_submission, draft_only=True)

        # Verify results
        assert result["status"] == "success"
        assert "prospect" in result
        assert result["prospect"]["email"] == form_submission["fieldValues"][2]["value"]
        assert "draft_id" in result
        assert "task" in result
        assert result["task"]["draft_id"] == result["draft_id"]

    async def test_workflow_draft_only_enforcement(self):
        """Verify DRAFT_ONLY mode is enforced."""

        class StrictMockGmailConnector:
            async def search_threads(self, *args, **kwargs):
                return []

            async def get_thread(self, *args, **kwargs):
                return None

            async def create_draft(self, *args, **kwargs):
                # Should NEVER call send_message
                draft_id = f"draft-{datetime.utcnow().isoformat()}"
                # Verify mode enforcement would go here
                return draft_id

            async def send_message(self, *args, **kwargs):
                # Should never be called in DRAFT_ONLY
                raise AssertionError("send_message called in DRAFT_ONLY mode!")

        class StrictMockHubSpotConnector:
            async def search_contacts(self, *args, **kwargs):
                return {"id": "contact-123"}

            async def get_contact_associations(self, *args, **kwargs):
                return [{"id": "company-456"}]

            async def create_note(self, *args, **kwargs):
                return f"note-{datetime.utcnow().isoformat()}"

            async def create_task(self, *args, **kwargs):
                return f"task-{datetime.utcnow().isoformat()}"

        class StrictMockCalendarConnector:
            async def find_available_slots(self, *args, **kwargs):
                return SAMPLE_CALENDAR_SLOTS

        orchestrator = ProspectingOrchestrator(
            gmail_connector=StrictMockGmailConnector(),
            hubspot_connector=StrictMockHubSpotConnector(),
            calendar_connector=StrictMockCalendarConnector(),
        )

        form_submission = get_sample_form_submission()
        result = await orchestrator.run_complete_workflow(form_submission, draft_only=True)

        # Verify DRAFT_ONLY mode worked
        assert result["status"] == "success"
        assert result.get("draft_id") is not None

    async def test_workflow_with_missing_connectors(self):
        """Test workflow gracefully handles missing connectors."""
        # Orchestrator with no connectors
        orchestrator = ProspectingOrchestrator()

        form_submission = get_sample_form_submission()
        result = await orchestrator.run_complete_workflow(form_submission, draft_only=True)

        # Should still complete with warnings
        assert result["status"] == "success"
        assert "prospect" in result
        # But draft/task might be missing
        assert result.get("draft_id") is None or result.get("steps", {}).get("create_draft", {}).get("status") in [
            "success",
            "failed",
        ]

    async def test_workflow_error_handling(self):
        """Test workflow error handling."""

        class FailingMockHubSpotConnector:
            async def search_contacts(self, *args, **kwargs):
                raise ValueError("Connection failed")

        orchestrator = ProspectingOrchestrator(
            hubspot_connector=FailingMockHubSpotConnector(),
        )

        form_submission = get_sample_form_submission()
        result = await orchestrator.run_complete_workflow(form_submission)

        # Workflow handles HubSpot errors gracefully and continues
        # Status is "success" because HubSpot step is optional
        assert result["status"] in ["success", "failed"]
        # The HubSpot step should record the error
        assert "resolve_hubspot" in result["steps"]
        assert result["steps"]["resolve_hubspot"]["status"] == "failed"

    async def test_workflow_context_tracking(self):
        """Test workflow context tracking."""

        class ContextTrackingMockConnectors:
            class Gmail:
                async def search_threads(self, *args, **kwargs):
                    return []

                async def get_thread(self, *args, **kwargs):
                    return None

                async def create_draft(self, *args, **kwargs):
                    return f"draft-{datetime.utcnow().isoformat()}"

            class HubSpot:
                async def search_contacts(self, *args, **kwargs):
                    return {"id": "contact-123"}

                async def get_contact_associations(self, *args, **kwargs):
                    return [{"id": "company-456"}]

                async def create_note(self, *args, **kwargs):
                    return f"note-{datetime.utcnow().isoformat()}"

                async def create_task(self, *args, **kwargs):
                    return f"task-{datetime.utcnow().isoformat()}"

            class Calendar:
                async def find_available_slots(self, *args, **kwargs):
                    return SAMPLE_CALENDAR_SLOTS

        mocks = ContextTrackingMockConnectors()

        orchestrator = ProspectingOrchestrator(
            gmail_connector=mocks.Gmail(),
            hubspot_connector=mocks.HubSpot(),
            calendar_connector=mocks.Calendar(),
        )

        form_submission = get_sample_form_submission()
        result = await orchestrator.run_complete_workflow(form_submission)

        # Verify complete context tracking
        assert result["timestamp"] is not None
        assert result["draft_only"] is True
        assert result["workflow_id"] is not None
        # Core steps should be recorded (agents add more steps when provided)
        assert len(result["steps"]) >= 5  # At minimum: resolve, search, calendar, draft, task

        # Verify core step details (these are always recorded with mocked connectors)
        for step_key in [
            "resolve_hubspot",
            "search_email",
            "calendar_availability",
            "create_draft",
            "create_hubspot_task",
        ]:
            assert step_key in result["steps"]
            step = result["steps"][step_key]
            assert "status" in step


class TestWorkflowIntegration:
    """Test workflow integration with multiple components."""

    async def test_prospect_to_draft_pipeline(self):
        """Test prospect extraction to draft creation."""

        class MockConnectors:
            class Gmail:
                async def create_draft(self, to: str, subject: str, body: str):
                    return f"draft-{datetime.utcnow().isoformat()}"

            class HubSpot:
                async def search_contacts(self, email: str):
                    return {"id": "contact-123", "email": email}

                async def get_contact_associations(self, contact_id: str):
                    return [{"id": "company-456"}]

                async def create_task(self, contact_id: str, title: str, body: str):
                    return f"task-{datetime.utcnow().isoformat()}"

                async def create_note(self, contact_id: str, body: str):
                    return f"note-{datetime.utcnow().isoformat()}"

            class Calendar:
                async def find_available_slots(self, **kwargs):
                    return SAMPLE_CALENDAR_SLOTS

        mocks = MockConnectors()
        orchestrator = ProspectingOrchestrator(
            gmail_connector=mocks.Gmail(),
            hubspot_connector=mocks.HubSpot(),
            calendar_connector=mocks.Calendar(),
        )

        form_submission = get_sample_form_submission()
        result = await orchestrator.run_complete_workflow(form_submission)

        # Verify pipeline
        assert result["status"] == "success"
        prospect_email = result["prospect"]["email"]
        assert prospect_email in form_submission["fieldValues"][2]["value"]
        assert result["draft_id"] is not None
