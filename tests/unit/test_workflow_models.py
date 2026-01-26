"""Unit tests for workflow models."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db import Base
from src.models.workflow import (
    Workflow,
    WorkflowStatus,
    WorkflowMode,
    DraftEmail,
    HubSpotTask,
    WorkflowError,
)
from src.models.form_submission import FormSubmission


@pytest.fixture
def db_session():
    """Create an in-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, checkfirst=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_form_submission(db_session):
    """Create a sample form submission."""
    submission = FormSubmission(
        portal_id=12345,
        form_id="test-form-123",
        form_submission_id="sub-uuid-456",
        prospect_email="john.doe@example.com",
        prospect_first_name="John",
        prospect_last_name="Doe",
        prospect_company="Acme Corp",
        raw_payload={"test": "data"},
    )
    db_session.add(submission)
    db_session.commit()
    return submission


class TestWorkflowModel:
    """Test Workflow model."""
    
    def test_create_workflow(self, db_session, sample_form_submission):
        """Test creating a workflow."""
        workflow = Workflow(
            form_submission_id=sample_form_submission.id,
            status=WorkflowStatus.TRIGGERED,
            mode=WorkflowMode.DRAFT_ONLY,
        )
        db_session.add(workflow)
        db_session.commit()
        
        assert workflow.id is not None
        assert workflow.status == WorkflowStatus.TRIGGERED
        assert workflow.mode == WorkflowMode.DRAFT_ONLY
        assert workflow.error_count == 0
        assert workflow.started_at is not None
        assert workflow.completed_at is None
    
    def test_workflow_status_enum(self):
        """Test workflow status enum values."""
        assert WorkflowStatus.TRIGGERED == "triggered"
        assert WorkflowStatus.PROCESSING == "processing"
        assert WorkflowStatus.COMPLETED == "completed"
        assert WorkflowStatus.FAILED == "failed"
    
    def test_workflow_mode_enum(self):
        """Test workflow mode enum values."""
        assert WorkflowMode.DRAFT_ONLY == "DRAFT_ONLY"
        assert WorkflowMode.SEND == "SEND"
    
    def test_workflow_relationship_to_form_submission(self, db_session, sample_form_submission):
        """Test workflow relationship to form submission."""
        workflow = Workflow(
            form_submission_id=sample_form_submission.id,
        )
        db_session.add(workflow)
        db_session.commit()
        
        # Test relationship
        assert workflow.form_submission.id == sample_form_submission.id
        assert workflow.form_submission.prospect_email == "john.doe@example.com"
        
        # Test back-reference
        assert len(sample_form_submission.workflows) == 1
        assert sample_form_submission.workflows[0].id == workflow.id
    
    def test_workflow_cascade_delete(self, db_session, sample_form_submission):
        """Test that deleting form submission cascades to workflow."""
        workflow = Workflow(form_submission_id=sample_form_submission.id)
        db_session.add(workflow)
        db_session.commit()
        
        workflow_id = workflow.id
        
        # Delete form submission
        db_session.delete(sample_form_submission)
        db_session.commit()
        
        # Workflow should be deleted
        assert db_session.query(Workflow).filter_by(id=workflow_id).first() is None


class TestDraftEmailModel:
    """Test DraftEmail model."""
    
    def test_create_draft_email(self, db_session, sample_form_submission):
        """Test creating a draft email."""
        workflow = Workflow(form_submission_id=sample_form_submission.id)
        db_session.add(workflow)
        db_session.commit()
        
        draft = DraftEmail(
            workflow_id=workflow.id,
            form_submission_id=sample_form_submission.id,
            recipient_email="prospect@example.com",
            subject="Test Subject",
            body="Test email body content here.",
        )
        db_session.add(draft)
        db_session.commit()
        
        assert draft.id is not None
        assert draft.recipient_email == "prospect@example.com"
        assert draft.approved_at is None
        assert draft.sent_at is None
    
    def test_draft_email_approval_workflow(self, db_session, sample_form_submission):
        """Test draft email approval workflow."""
        workflow = Workflow(form_submission_id=sample_form_submission.id)
        draft = DraftEmail(
            workflow_id=workflow.id,
            form_submission_id=sample_form_submission.id,
            recipient_email="test@example.com",
            subject="Subject",
            body="Body",
        )
        db_session.add_all([workflow, draft])
        db_session.commit()
        
        # Approve draft
        draft.approved_at = datetime.utcnow()
        draft.approved_by = "operator@company.com"
        db_session.commit()
        
        assert draft.approved_at is not None
        assert draft.approved_by == "operator@company.com"
        assert draft.rejected_at is None
    
    def test_draft_email_rejection_workflow(self, db_session, sample_form_submission):
        """Test draft email rejection workflow."""
        workflow = Workflow(form_submission_id=sample_form_submission.id)
        draft = DraftEmail(
            workflow_id=workflow.id,
            form_submission_id=sample_form_submission.id,
            recipient_email="test@example.com",
            subject="Subject",
            body="Body",
        )
        db_session.add_all([workflow, draft])
        db_session.commit()
        
        # Reject draft
        draft.rejected_at = datetime.utcnow()
        draft.rejected_by = "operator@company.com"
        draft.rejection_reason = "Tone too aggressive"
        db_session.commit()
        
        assert draft.rejected_at is not None
        assert draft.rejected_by == "operator@company.com"
        assert draft.rejection_reason == "Tone too aggressive"
        assert draft.approved_at is None
    
    def test_draft_email_relationship_to_workflow(self, db_session, sample_form_submission):
        """Test draft email relationship to workflow."""
        workflow = Workflow(form_submission_id=sample_form_submission.id)
        draft1 = DraftEmail(
            workflow_id=workflow.id,
            form_submission_id=sample_form_submission.id,
            recipient_email="test1@example.com",
            subject="Draft 1",
            body="Body 1",
        )
        draft2 = DraftEmail(
            workflow_id=workflow.id,
            form_submission_id=sample_form_submission.id,
            recipient_email="test2@example.com",
            subject="Draft 2",
            body="Body 2",
        )
        db_session.add_all([workflow, draft1, draft2])
        db_session.commit()
        
        # Test relationship
        assert len(workflow.draft_emails) == 2
        assert draft1.workflow.id == workflow.id


class TestHubSpotTaskModel:
    """Test HubSpotTask model."""
    
    def test_create_hubspot_task(self, db_session, sample_form_submission):
        """Test creating a HubSpot task."""
        workflow = Workflow(form_submission_id=sample_form_submission.id)
        task = HubSpotTask(
            workflow_id=workflow.id,
            hubspot_task_id="hs-task-12345",
            contact_id="contact-67890",
            title="Follow up with prospect",
            body="Review draft and follow up",
            due_date=datetime.utcnow() + timedelta(days=2),
        )
        db_session.add_all([workflow, task])
        db_session.commit()
        
        assert task.id is not None
        assert task.hubspot_task_id == "hs-task-12345"
        assert task.contact_id == "contact-67890"
        assert task.title == "Follow up with prospect"
    
    def test_hubspot_task_unique_constraint(self, db_session, sample_form_submission):
        """Test that hubspot_task_id must be unique."""
        workflow1 = Workflow(form_submission_id=sample_form_submission.id)
        workflow2 = Workflow(form_submission_id=sample_form_submission.id)
        
        task1 = HubSpotTask(
            workflow_id=workflow1.id,
            hubspot_task_id="hs-task-12345",
            contact_id="contact-1",
            title="Task 1",
        )
        task2 = HubSpotTask(
            workflow_id=workflow2.id,
            hubspot_task_id="hs-task-12345",  # Same ID
            contact_id="contact-2",
            title="Task 2",
        )
        
        db_session.add_all([workflow1, workflow2, task1])
        db_session.commit()
        
        db_session.add(task2)
        with pytest.raises(Exception):  # IntegrityError for unique constraint
            db_session.commit()


class TestWorkflowErrorModel:
    """Test WorkflowError model."""
    
    def test_create_workflow_error(self, db_session, sample_form_submission):
        """Test creating a workflow error."""
        workflow = Workflow(form_submission_id=sample_form_submission.id)
        error = WorkflowError(
            workflow_id=workflow.id,
            error_type="APIError",
            error_message="Gmail API rate limit exceeded",
            traceback="Traceback (most recent call last)...",
            step_name="create_draft",
            retry_count=1,
            max_retries=3,
            next_retry_at=datetime.utcnow() + timedelta(minutes=5),
        )
        db_session.add_all([workflow, error])
        db_session.commit()
        
        assert error.id is not None
        assert error.error_type == "APIError"
        assert error.retry_count == 1
        assert error.max_retries == 3
        assert error.next_retry_at is not None
    
    def test_workflow_error_relationship(self, db_session, sample_form_submission):
        """Test workflow error relationship."""
        workflow = Workflow(form_submission_id=sample_form_submission.id)
        error1 = WorkflowError(
            workflow_id=workflow.id,
            error_type="Error1",
            error_message="Message 1",
        )
        error2 = WorkflowError(
            workflow_id=workflow.id,
            error_type="Error2",
            error_message="Message 2",
        )
        db_session.add_all([workflow, error1, error2])
        db_session.commit()
        
        # Test relationship
        assert len(workflow.errors) == 2
        assert error1.workflow.id == workflow.id


class TestFormSubmissionModel:
    """Test FormSubmission model."""
    
    def test_create_form_submission(self, db_session):
        """Test creating a form submission."""
        submission = FormSubmission(
            portal_id=12345,
            form_id="contact-form",
            form_submission_id="sub-uuid-123",
            prospect_email="jane@example.com",
            prospect_first_name="Jane",
            prospect_last_name="Smith",
            prospect_company="Tech Corp",
            raw_payload={"field1": "value1"},
        )
        db_session.add(submission)
        db_session.commit()
        
        assert submission.id is not None
        assert submission.prospect_email == "jane@example.com"
        assert submission.processed == 0  # Pending
    
    def test_form_submission_unique_constraint(self, db_session):
        """Test that form_submission_id must be unique."""
        sub1 = FormSubmission(
            portal_id=12345,
            form_id="form1",
            form_submission_id="sub-123",
            prospect_email="test1@example.com",
        )
        sub2 = FormSubmission(
            portal_id=12345,
            form_id="form1",
            form_submission_id="sub-123",  # Same ID
            prospect_email="test2@example.com",
        )
        
        db_session.add(sub1)
        db_session.commit()
        
        db_session.add(sub2)
        with pytest.raises(Exception):  # IntegrityError for unique constraint
            db_session.commit()
    
    def test_form_submission_prospect_full_name(self, db_session):
        """Test prospect_full_name property."""
        submission = FormSubmission(
            portal_id=12345,
            form_id="form1",
            form_submission_id="sub-123",
            prospect_email="test@example.com",
            prospect_first_name="John",
            prospect_last_name="Doe",
        )
        
        assert submission.prospect_full_name == "John Doe"
        
        # Test with only first name
        submission.prospect_last_name = None
        assert submission.prospect_full_name == "John"
        
        # Test with only last name
        submission.prospect_first_name = None
        submission.prospect_last_name = "Doe"
        assert submission.prospect_full_name == "Doe"
    
    def test_form_submission_processing_state_properties(self, db_session):
        """Test processing state properties."""
        submission = FormSubmission(
            portal_id=12345,
            form_id="form1",
            form_submission_id="sub-123",
            prospect_email="test@example.com",
        )
        
        # Test pending
        assert submission.is_pending
        assert not submission.is_processed
        assert not submission.is_failed
        
        # Test processed
        submission.processed = 1
        assert submission.is_processed
        assert not submission.is_pending
        assert not submission.is_failed
        
        # Test failed
        submission.processed = 2
        assert submission.is_failed
        assert not submission.is_pending
        assert not submission.is_processed
