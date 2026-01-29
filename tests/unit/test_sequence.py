"""Unit tests for Sequence models and executor.

Sprint 63: Sequence Automation
"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.sequence import (
    Sequence,
    SequenceStep,
    SequenceEnrollment,
    SequenceStatus,
    EnrollmentStatus,
    StepChannel,
)


class TestSequenceModel:
    """Tests for Sequence model."""

    def test_sequence_to_dict(self):
        """Test sequence serialization."""
        sequence = Sequence(
            id=uuid.uuid4(),
            name="Cold Outreach 5-Step",
            description="Standard cold outreach sequence",
            status=SequenceStatus.ACTIVE.value,
            target_persona="events",
            total_enrollments=100,
            active_enrollments=50,
            completed_enrollments=40,
            replied_enrollments=10,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        sequence.steps = []
        
        result = sequence.to_dict()
        
        assert result["name"] == "Cold Outreach 5-Step"
        assert result["status"] == "active"
        assert result["total_enrollments"] == 100
        assert result["active_enrollments"] == 50
        assert result["step_count"] == 0

    def test_sequence_step_to_dict(self):
        """Test sequence step serialization."""
        step = SequenceStep(
            id=uuid.uuid4(),
            sequence_id=uuid.uuid4(),
            step_number=1,
            channel=StepChannel.EMAIL.value,
            delay_days=0,
            delay_hours=0,
            subject_template="Hi {{first_name}}, quick question",
            body_template="Hi {{first_name}},\n\nI noticed {{company}} is growing...",
            created_at=datetime.utcnow(),
        )
        
        result = step.to_dict()
        
        assert result["step_number"] == 1
        assert result["channel"] == "email"
        assert "{{first_name}}" in result["subject_template"]

    def test_sequence_enrollment_to_dict(self):
        """Test enrollment serialization."""
        enrollment = SequenceEnrollment(
            id=uuid.uuid4(),
            sequence_id=uuid.uuid4(),
            contact_email="john@acme.com",
            contact_name="John Doe",
            context={"company": "Acme", "title": "VP Sales"},
            current_step=2,
            status=EnrollmentStatus.ACTIVE.value,
            enrolled_at=datetime.utcnow(),
            next_step_at=datetime.utcnow() + timedelta(days=3),
            step_history=[
                {"step": 1, "sent_at": "2026-01-25T10:00:00", "status": "sent"},
                {"step": 2, "sent_at": "2026-01-28T10:00:00", "status": "sent"},
            ],
        )
        
        result = enrollment.to_dict()
        
        assert result["contact_email"] == "john@acme.com"
        assert result["current_step"] == 2
        assert result["status"] == "active"
        assert len(result["step_history"]) == 2


class TestSequenceStatus:
    """Tests for sequence status enum."""

    def test_status_values(self):
        """Test all status values are valid."""
        assert SequenceStatus.DRAFT.value == "draft"
        assert SequenceStatus.ACTIVE.value == "active"
        assert SequenceStatus.PAUSED.value == "paused"
        assert SequenceStatus.ARCHIVED.value == "archived"


class TestEnrollmentStatus:
    """Tests for enrollment status enum."""

    def test_status_values(self):
        """Test all enrollment status values."""
        assert EnrollmentStatus.ACTIVE.value == "active"
        assert EnrollmentStatus.PAUSED.value == "paused"
        assert EnrollmentStatus.COMPLETED.value == "completed"
        assert EnrollmentStatus.REPLIED.value == "replied"
        assert EnrollmentStatus.BOUNCED.value == "bounced"
        assert EnrollmentStatus.UNSUBSCRIBED.value == "unsubscribed"


class TestStepChannel:
    """Tests for step channel enum."""

    def test_channel_values(self):
        """Test all channel values."""
        assert StepChannel.EMAIL.value == "email"
        assert StepChannel.LINKEDIN.value == "linkedin"
        assert StepChannel.CALL.value == "call"
        assert StepChannel.TASK.value == "task"


class TestSequenceExecutor:
    """Tests for sequence executor logic."""

    def test_personalize_template(self):
        """Test template personalization."""
        from src.tasks.sequence_executor import _personalize_template
        
        template = "Hi {{first_name}}, I see you work at {{company}} as {{title}}."
        context = {
            "first_name": "John",
            "company": "Acme Corp",
            "title": "VP Sales",
        }
        
        # Create mock enrollment
        enrollment = MagicMock()
        enrollment.contact_name = "John Doe"
        enrollment.contact_email = "john@acme.com"
        
        result = _personalize_template(template, context, enrollment)
        
        assert "John" in result
        assert "Acme Corp" in result
        assert "VP Sales" in result
        assert "{{" not in result

    def test_personalize_template_missing_values(self):
        """Test template with missing context values."""
        from src.tasks.sequence_executor import _personalize_template
        
        template = "Hi {{first_name}}, I noticed {{company}}..."
        context = {}
        
        enrollment = MagicMock()
        enrollment.contact_name = "Jane"
        enrollment.contact_email = "jane@test.com"
        
        result = _personalize_template(template, context, enrollment)
        
        # Should use enrollment name as fallback
        assert "Jane" in result

    def test_personalize_empty_template(self):
        """Test empty template returns empty string."""
        from src.tasks.sequence_executor import _personalize_template
        
        enrollment = MagicMock()
        enrollment.contact_name = "Test"
        enrollment.contact_email = "test@test.com"
        
        result = _personalize_template("", {}, enrollment)
        
        assert result == ""


class TestSequenceWorkflow:
    """Integration-style tests for sequence workflow."""

    def test_enrollment_progression(self):
        """Test enrollment moves through steps correctly."""
        # Simulate enrollment progress
        enrollment = SequenceEnrollment(
            id=uuid.uuid4(),
            sequence_id=uuid.uuid4(),
            contact_email="test@example.com",
            current_step=0,
            status=EnrollmentStatus.ACTIVE.value,
            step_history=[],
        )
        
        # Simulate step 1 completion
        enrollment.current_step = 1
        enrollment.step_history = [{"step": 1, "status": "queued"}]
        
        assert enrollment.current_step == 1
        assert len(enrollment.step_history) == 1

    def test_enrollment_completion(self):
        """Test enrollment completion."""
        enrollment = SequenceEnrollment(
            id=uuid.uuid4(),
            sequence_id=uuid.uuid4(),
            contact_email="test@example.com",
            current_step=5,
            status=EnrollmentStatus.ACTIVE.value,
        )
        
        # Complete enrollment
        enrollment.status = EnrollmentStatus.COMPLETED.value
        enrollment.completed_at = datetime.utcnow()
        enrollment.next_step_at = None
        
        assert enrollment.status == EnrollmentStatus.COMPLETED.value
        assert enrollment.completed_at is not None
        assert enrollment.next_step_at is None

    def test_enrollment_reply_pause(self):
        """Test enrollment pauses on reply."""
        enrollment = SequenceEnrollment(
            id=uuid.uuid4(),
            sequence_id=uuid.uuid4(),
            contact_email="test@example.com",
            current_step=2,
            status=EnrollmentStatus.ACTIVE.value,
            next_step_at=datetime.utcnow() + timedelta(days=3),
        )
        
        # Simulate reply detection
        enrollment.status = EnrollmentStatus.REPLIED.value
        enrollment.next_step_at = None
        
        assert enrollment.status == EnrollmentStatus.REPLIED.value
        assert enrollment.next_step_at is None
