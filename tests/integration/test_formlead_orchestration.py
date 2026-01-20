"""Integration tests for formlead orchestration."""
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.formlead_orchestrator import FormleadOrchestrator, reset_formlead_orchestrator
from tests.fixtures.seed_data import get_sample_form_submission, SAMPLE_CALENDAR_SLOTS


class MockGmailConnector:
    """Mock Gmail connector."""
    
    async def search_threads(self, *args, **kwargs):
        return [{"id": "thread-123", "snippet": "Previous conversation..."}]
    
    async def get_thread(self, *args, **kwargs):
        return {
            "id": "thread-123",
            "messages": [
                {"internalDate": "2026-01-20T10:00:00Z", "snippet": "First message"},
                {"internalDate": "2026-01-20T14:00:00Z", "snippet": "Recent message"},
            ],
        }
    
    async def create_draft(self, to: str, subject: str, body: str):
        return f"draft-{datetime.utcnow().isoformat()}"


class MockHubSpotConnector:
    """Mock HubSpot connector."""
    
    async def search_contacts(self, email: str):
        return {"id": "contact-123", "email": email}
    
    async def create_note(self, *args, **kwargs):
        return f"note-{datetime.utcnow().isoformat()}"
    
    async def create_task(self, *args, **kwargs):
        return f"task-{datetime.utcnow().isoformat()}"


class MockCalendarConnector:
    """Mock Calendar connector."""
    
    async def find_available_slots(self, *args, **kwargs):
        return SAMPLE_CALENDAR_SLOTS[:3]


class TestFormleadOrchestration:
    """Test formlead orchestration with all 11 steps."""

    @pytest.fixture(autouse=True)
    def cleanup(self):
        """Clean up after each test."""
        yield
        reset_formlead_orchestrator()

    async def test_complete_formlead_workflow(self):
        """Test complete 11-step formlead workflow."""
        orchestrator = FormleadOrchestrator(
            gmail_connector=MockGmailConnector(),
            hubspot_connector=MockHubSpotConnector(),
            calendar_connector=MockCalendarConnector(),
        )

        form_submission = get_sample_form_submission()
        result = await orchestrator.process_formlead(form_submission)

        # Verify all 11 steps completed
        assert result["final_status"] == "success"
        assert result["mode"] == "DRAFT_ONLY"
        assert len(result["steps"]) >= 11
        assert "draft_id" in result
        assert "task_id" in result

        # Verify step completion
        expected_steps = [
            "validate_payload",
            "resolve_hubspot",
            "search_gmail",
            "read_thread",
            "long_memory",
            "asset_hunter",
            "meeting_slots",
            "next_step_plan",
            "draft_writer",
            "create_draft",
            "create_task",
            "label_thread",
        ]
        for step in expected_steps:
            assert step in result["steps"]
            assert result["steps"][step].get("status") in ["success", "partial"]

    async def test_form_validation_rejects_invalid_form_id(self):
        """Test that invalid form IDs are rejected."""
        orchestrator = FormleadOrchestrator()
        
        form_submission = get_sample_form_submission()
        form_submission["formId"] = "invalid-form-id-xyz"
        
        result = await orchestrator.process_formlead(form_submission)
        
        assert result["final_status"] == "failed"
        assert "error" in result

    async def test_hubspot_contact_resolution(self):
        """Test HubSpot contact resolution."""
        orchestrator = FormleadOrchestrator(
            hubspot_connector=MockHubSpotConnector(),
        )
        
        form_submission = get_sample_form_submission()
        result = await orchestrator.process_formlead(form_submission)
        
        # Should find/resolve contact
        assert "prospect" in result
        assert result["prospect"].get("email") is not None

    async def test_gmail_thread_search_and_context(self):
        """Test Gmail thread search and context reading."""
        orchestrator = FormleadOrchestrator(
            gmail_connector=MockGmailConnector(),
        )
        
        form_submission = get_sample_form_submission()
        result = await orchestrator.process_formlead(form_submission)
        
        # Should find threads and read context
        assert result["steps"]["search_gmail"]["threads_found"] > 0
        assert result["steps"]["read_thread"]["has_context"] is True

    async def test_asset_hunter_allowlist_enforcement(self):
        """Test asset hunter enforces allowlist."""
        orchestrator = FormleadOrchestrator()
        
        form_submission = get_sample_form_submission()
        result = await orchestrator.process_formlead(form_submission)
        
        # Verify allowlist was enforced
        asset_step = result["steps"]["asset_hunter"]
        assert asset_step["allowlist_enforced"] is True

    async def test_meeting_slot_proposal(self):
        """Test meeting slot proposal (2-3 slots in 1-3 business days)."""
        orchestrator = FormleadOrchestrator()
        
        form_submission = get_sample_form_submission()
        result = await orchestrator.process_formlead(form_submission)
        
        # Should propose 2-3 slots
        meeting_slots = result["steps"]["meeting_slots"]
        assert meeting_slots["slots_count"] in [2, 3]

    async def test_draft_created_in_draft_only_mode(self):
        """Test draft is created (not sent) in DRAFT_ONLY mode."""
        orchestrator = FormleadOrchestrator(
            gmail_connector=MockGmailConnector(),
        )
        
        form_submission = get_sample_form_submission()
        result = await orchestrator.process_formlead(form_submission)
        
        # Draft should be created
        assert result["steps"]["create_draft"]["status"] == "success"
        assert result["steps"]["create_draft"]["mode"] == "DRAFT_ONLY"
        assert result["draft_id"] is not None
        
        # Should NOT be sent
        assert "send" not in result["steps"]

    async def test_hubspot_task_creation(self):
        """Test HubSpot task creation."""
        orchestrator = FormleadOrchestrator(
            gmail_connector=MockGmailConnector(),
            hubspot_connector=MockHubSpotConnector(),
        )
        
        form_submission = get_sample_form_submission()
        result = await orchestrator.process_formlead(form_submission)
        
        # Task should be created
        assert result["steps"]["create_task"]["status"] == "success"
        assert result["task_id"] is not None

    async def test_voice_profile_usage(self):
        """Test voice profile is used in draft writing."""
        voice_profile = {
            "tone": "consultative",
            "patterns": ["specific_fit", "discovery_focus"],
        }
        
        orchestrator = FormleadOrchestrator(
            gmail_connector=MockGmailConnector(),
        )
        
        form_submission = get_sample_form_submission()
        result = await orchestrator.process_formlead(
            form_submission,
            voice_profile=voice_profile,
        )
        
        # Draft should be created with voice profile
        assert result["steps"]["draft_writer"]["status"] == "success"
        assert result["steps"]["draft_writer"]["has_body"] is True

    async def test_workflow_with_missing_connectors(self):
        """Test workflow handles missing connectors gracefully."""
        orchestrator = FormleadOrchestrator()  # No connectors
        
        form_submission = get_sample_form_submission()
        result = await orchestrator.process_formlead(form_submission)
        
        # Should complete despite missing connectors
        assert result["final_status"] == "success"
        assert result["mode"] == "DRAFT_ONLY"

    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery."""
        class FailingConnector:
            async def search_contacts(self, *args, **kwargs):
                raise ValueError("Connection failed")
        
        orchestrator = FormleadOrchestrator(
            hubspot_connector=FailingConnector(),
        )
        
        form_submission = get_sample_form_submission()
        result = await orchestrator.process_formlead(form_submission)
        
        # Should handle error gracefully
        assert result["final_status"] == "failed"
        assert "error" in result

    async def test_audit_trail_event_creation(self):
        """Test audit trail events are created."""
        orchestrator = FormleadOrchestrator(
            gmail_connector=MockGmailConnector(),
            hubspot_connector=MockHubSpotConnector(),
        )
        
        form_submission = get_sample_form_submission()
        result = await orchestrator.process_formlead(form_submission)
        
        # Should have audit trail capability
        assert result["workflow_id"] is not None
        assert result["timestamp"] is not None
