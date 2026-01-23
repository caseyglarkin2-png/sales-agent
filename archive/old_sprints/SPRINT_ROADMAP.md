# Sales Agent: Comprehensive Sprint & Task Planning

**Status**: Post-Phase 3 (Orchestration engine built & tested)  
**Next Target**: Production-ready system with UI and real sends  
**Total Effort**: 6 phases × 5-8 tasks = ~36-40 atomic tasks  

---

## 📊 Project Overview

```
Phase 3 (Complete)         Phase 4-9 (Roadmap)
├─ Orchestration ✅        ├─ Production Enablement
├─ 13-Step Workflow ✅     ├─ Core Operations UI  
├─ Connectors ✅           ├─ Reliability & Recovery
├─ E2E Testing ✅          ├─ Async & Scaling
└─ Code Complete ✅        ├─ Advanced Observability
                           └─ Multi-tenancy & Go-Live
```

**Success Criteria per Phase**:
- ✅ All atomic tasks completed with passing tests
- ✅ Demoable software at phase end
- ✅ No technical debt introduced
- ✅ Clear commit history (one commit per atomic task)

---

# PHASE 4: PRODUCTION ENABLEMENT (2 weeks)
**Goal**: Enable real sends, receive webhooks, persist data  
**Demoable Output**: System receives form submission, processes it, stores everything

## Phase 4 Architecture
```
HubSpot Form
    ↓
Webhook Server (FastAPI)
    ↓
Request Validation
    ↓
Async Queue (Celery + Redis)
    ↓
Worker Process
    ↓
Orchestrator (existing)
    ↓
Database ← Persist workflows, drafts, tasks
    ↓
Gmail/HubSpot/etc (DRAFT_ONLY flag can be toggled)
```

---

## 4.1: Database Schema & Migrations

**Objective**: Create PostgreSQL schema to persist workflows, forms, drafts, tasks  
**Acceptance Criteria**:
- [ ] Alembic migration files created and tested
- [ ] Schema supports workflow state tracking
- [ ] Schema supports audit trails
- [ ] Schema includes workflow_status, form_submission, draft_email, hubspot_task, workflow_event tables
- [ ] All foreign keys and constraints in place
- [ ] Migration runs without errors on fresh database

**Technical Spec**:

```sql
-- src/db/migrations/alembic/versions/001_initial_schema.py

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Workflows table
    op.create_table(
        'workflows',
        sa.Column('id', sa.String(255), primary_key=True),  # formlead-TIMESTAMP
        sa.Column('status', sa.String(50), nullable=False),  # pending, processing, success, failed
        sa.Column('mode', sa.String(20), nullable=False),  # DRAFT_ONLY or SEND
        sa.Column('form_submission_id', sa.String(255), nullable=False),
        sa.Column('prospect_email', sa.String(255), nullable=False),
        sa.Column('prospect_company', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
    )
    
    # Form submissions table
    op.create_table(
        'form_submissions',
        sa.Column('id', sa.String(255), primary_key=True),  # HubSpot formSubmissionId
        sa.Column('form_id', sa.String(255), nullable=False),
        sa.Column('portal_id', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('first_name', sa.String(255), nullable=True),
        sa.Column('last_name', sa.String(255), nullable=True),
        sa.Column('raw_payload', sa.JSON, nullable=False),
        sa.Column('received_at', sa.DateTime, nullable=False),
    )
    
    # Draft emails table
    op.create_table(
        'draft_emails',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('workflow_id', sa.String(255), sa.ForeignKey('workflows.id')),
        sa.Column('to_email', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('assets_included', sa.Integer, default=0),
        sa.Column('gmail_draft_id', sa.String(255), nullable=True),  # If actually created
        sa.Column('sent', sa.Boolean, default=False),
        sa.Column('sent_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    
    # HubSpot tasks table
    op.create_table(
        'hubspot_tasks',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('workflow_id', sa.String(255), sa.ForeignKey('workflows.id')),
        sa.Column('hubspot_task_id', sa.String(255), nullable=True),
        sa.Column('contact_id', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),  # NOT_STARTED, COMPLETED
        sa.Column('due_date', sa.Date, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    
    # Workflow events (audit trail)
    op.create_table(
        'workflow_events',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('workflow_id', sa.String(255), sa.ForeignKey('workflows.id')),
        sa.Column('event_type', sa.String(100), nullable=False),  # step_completed, error, etc
        sa.Column('step_number', sa.Integer, nullable=True),
        sa.Column('step_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),  # success, failed
        sa.Column('details', sa.JSON, nullable=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    
    # Workflow errors (for debugging)
    op.create_table(
        'workflow_errors',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('workflow_id', sa.String(255), sa.ForeignKey('workflows.id')),
        sa.Column('step_number', sa.Integer, nullable=False),
        sa.Column('error_type', sa.String(255), nullable=False),
        sa.Column('error_message', sa.Text, nullable=False),
        sa.Column('error_traceback', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )

def downgrade():
    op.drop_table('workflow_errors')
    op.drop_table('workflow_events')
    op.drop_table('hubspot_tasks')
    op.drop_table('draft_emails')
    op.drop_table('form_submissions')
    op.drop_table('workflows')
```

**Files to Create**:
- [ ] `src/db/models/__init__.py` - SQLAlchemy models
- [ ] `src/db/models/workflow.py` - Workflow model
- [ ] `src/db/models/form_submission.py` - Form model
- [ ] `src/db/models/draft_email.py` - Draft model
- [ ] `src/db/models/hubspot_task.py` - Task model
- [ ] `src/db/models/workflow_event.py` - Event audit model
- [ ] `src/db/session.py` - Database session management
- [ ] `alembic/versions/001_initial_schema.py` - Migration

**Test Approach**:
```python
# tests/integration/test_migrations.py
import pytest
from sqlalchemy import create_engine
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations

@pytest.mark.integration
async def test_migration_001_creates_all_tables(test_db):
    """Verify migration 001 creates all required tables"""
    # Run migration
    # Check tables exist
    # Check columns exist
    # Check constraints exist
    # Check can insert sample data

@pytest.mark.integration
async def test_workflow_model_crud(test_db):
    """Test basic CRUD operations on Workflow model"""
    # Create
    # Read
    # Update
    # Delete
```

**Validation**:
- Run: `alembic upgrade head` on fresh database ✅
- Check schema with: `psql -d sales_agent -c "\dt"` ✅
- Insert test data and verify constraints ✅

---

## 4.2: Webhook Receiver & Request Validation

**Objective**: Implement FastAPI endpoint to receive HubSpot form submissions  
**Acceptance Criteria**:
- [ ] POST `/webhook/formlead` endpoint created
- [ ] Validates HubSpot portal ID
- [ ] Validates form ID against allowlist
- [ ] Returns 400 for invalid requests
- [ ] Returns 202 for accepted requests
- [ ] Stores raw payload in database
- [ ] Generates form submission record

**Technical Spec**:

```python
# src/api/webhooks.py
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel, validator
import hmac
import hashlib
from src.db.session import SessionLocal
from src.db.models import FormSubmission

router = APIRouter()

ALLOWED_FORM_IDS = [
    "db8b22de-c3d4-4fc6-9a16-011fe322e82c-a139838e-99fa-44bd-9052-2d04b26f8bf4",
]

HUBSPOT_WEBHOOK_SECRET = os.getenv("HUBSPOT_WEBHOOK_SECRET")

@router.post("/webhook/formlead")
async def receive_formlead(request: Request, background_tasks: BackgroundTasks):
    """
    Receive HubSpot form submission webhook
    
    Webhook from HubSpot includes:
    - portalId: HubSpot account ID
    - formId: Form identifier
    - formSubmissionId: Unique submission ID
    - timestamp: When submitted
    - fieldValues: Array of form field values
    """
    
    # Get request body
    body = await request.body()
    
    # Verify HubSpot signature
    signature = request.headers.get("X-HubSpot-Signature")
    if not verify_hubspot_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse payload
    try:
        payload = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Validate required fields
    required = ["portalId", "formId", "formSubmissionId", "fieldValues"]
    if not all(field in payload for field in required):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Check form ID in allowlist
    if payload["formId"] not in ALLOWED_FORM_IDS:
        raise HTTPException(status_code=403, detail="Form not allowed")
    
    # Extract email & company from fieldValues
    email = extract_field_value(payload["fieldValues"], "email")
    company = extract_field_value(payload["fieldValues"], "company")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    # Create database record
    db = SessionLocal()
    try:
        form_submission = FormSubmission(
            id=payload["formSubmissionId"],
            form_id=payload["formId"],
            portal_id=payload["portalId"],
            email=email,
            company=company,
            raw_payload=payload,
            received_at=datetime.utcnow(),
        )
        db.add(form_submission)
        db.commit()
        
        # Queue for processing
        background_tasks.add_task(
            process_formlead,
            form_submission_id=payload["formSubmissionId"],
            payload=payload
        )
        
        return {
            "status": "accepted",
            "submission_id": payload["formSubmissionId"],
            "workflow_id": None  # Will be assigned during processing
        }
    finally:
        db.close()

def verify_hubspot_signature(body: bytes, signature: str) -> bool:
    """Verify HubSpot webhook signature"""
    expected = hmac.new(
        HUBSPOT_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

def extract_field_value(field_values: list, field_name: str) -> str:
    """Extract value from HubSpot field array"""
    for field in field_values:
        if field.get("name") == field_name:
            return field.get("value", "")
    return None
```

**Files to Create**:
- [ ] `src/api/__init__.py`
- [ ] `src/api/webhooks.py` - Webhook receiver
- [ ] `src/api/models.py` - Pydantic models for validation

**Test Approach**:
```python
# tests/integration/test_webhooks.py
import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

@pytest.mark.integration
def test_webhook_accepts_valid_submission():
    """POST valid form submission returns 202"""
    payload = {
        "portalId": "12345",
        "formId": "db8b22de-c3d4-4fc6-9a16-011fe322e82c-a139838e-99fa-44bd-9052-2d04b26f8bf4",
        "formSubmissionId": "test-123",
        "fieldValues": [
            {"name": "email", "value": "test@example.com"},
            {"name": "company", "value": "TestCo"},
        ]
    }
    response = client.post("/webhook/formlead", json=payload)
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"

@pytest.mark.integration
def test_webhook_rejects_invalid_form_id():
    """POST with invalid form ID returns 403"""
    payload = {
        "portalId": "12345",
        "formId": "wrong-form-id",
        "formSubmissionId": "test-123",
        "fieldValues": [...]
    }
    response = client.post("/webhook/formlead", json=payload)
    assert response.status_code == 403

@pytest.mark.integration
def test_webhook_stores_in_database(test_db):
    """Webhook payload stored in form_submissions table"""
    # POST request
    # Verify database record created
    # Verify raw_payload matches
```

**Validation**:
- Use `curl` to test endpoint locally ✅
- Send test payload from Postman ✅
- Verify database records created ✅

---

## 4.3: Celery Task Queue Setup

**Objective**: Implement async task processing with Celery + Redis  
**Acceptance Criteria**:
- [ ] Redis installed and running
- [ ] Celery worker configured
- [ ] Task router for different task types
- [ ] Dead-letter queue for failed tasks
- [ ] Can enqueue, process, and monitor tasks

**Technical Spec**:

```python
# src/tasks/celery_app.py
from celery import Celery, Task
from kombu import Queue, Exchange
import os

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "sales_agent",
    broker=redis_url,
    backend=redis_url,
)

# Configure task routing
default_exchange = Exchange("tasks", type="direct")
dlq_exchange = Exchange("dlq", type="direct")

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    
    # Queue configuration
    task_queues=(
        Queue("default", exchange=default_exchange, routing_key="default"),
        Queue("priority", exchange=default_exchange, routing_key="priority"),
        Queue("dlq", exchange=dlq_exchange, routing_key="dlq"),
    ),
    task_default_queue="default",
    task_default_routing_key="default",
    
    # Retry configuration
    task_autoretry_for=(Exception,),
    task_max_retries=3,
    task_default_retry_delay=60,  # 1 minute
)

# Custom Task class for better error handling
class FormsLeadTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

app.Task = FormsLeadTask
```

```python
# src/tasks/process_formlead.py
from src.tasks.celery_app import app
from src.logger import get_logger
from src.formlead_orchestrator import get_formlead_orchestrator
from src.db.session import SessionLocal
from src.db.models import Workflow, WorkflowError

logger = get_logger(__name__)

@app.task(bind=True, queue="default")
def process_formlead_async(self, form_submission_id: str, payload: dict):
    """
    Process form submission asynchronously
    
    Args:
        form_submission_id: HubSpot form submission ID
        payload: Full webhook payload
    """
    workflow_id = f"formlead-{datetime.utcnow().isoformat()}"
    db = SessionLocal()
    
    try:
        # Create workflow record
        workflow = Workflow(
            id=workflow_id,
            status="processing",
            mode=os.getenv("WORKFLOW_MODE", "DRAFT_ONLY"),
            form_submission_id=form_submission_id,
            prospect_email=payload.get("email"),
            prospect_company=payload.get("company"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
        )
        db.add(workflow)
        db.commit()
        
        logger.info(f"Processing formlead {workflow_id}")
        
        # Run orchestration
        orchestrator = get_formlead_orchestrator()
        result = asyncio.run(orchestrator.process_formlead(payload))
        
        # Update workflow record
        workflow.status = "success" if result.get("final_status") == "success" else "failed"
        workflow.updated_at = datetime.utcnow()
        workflow.completed_at = datetime.utcnow()
        workflow.duration_ms = int((datetime.utcnow() - workflow.started_at).total_seconds() * 1000)
        
        # Store result details
        db.commit()
        
        logger.info(f"Workflow {workflow_id} completed: {workflow.status}")
        return {
            "workflow_id": workflow_id,
            "status": workflow.status,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Workflow {workflow_id} failed: {e}", exc_info=True)
        
        # Store error
        error = WorkflowError(
            id=f"err-{uuid.uuid4()}",
            workflow_id=workflow_id,
            step_number=result.get("current_step", 0),
            error_type=type(e).__name__,
            error_message=str(e),
            error_traceback=traceback.format_exc(),
            created_at=datetime.utcnow(),
        )
        db.add(error)
        
        workflow.status = "failed"
        workflow.updated_at = datetime.utcnow()
        db.commit()
        
        # Celery will retry based on config
        raise
    finally:
        db.close()
```

**Files to Create**:
- [ ] `src/tasks/__init__.py`
- [ ] `src/tasks/celery_app.py` - Celery config
- [ ] `src/tasks/process_formlead.py` - Task implementation
- [ ] `infra/docker-compose.redis.yml` - Redis container

**Test Approach**:
```python
# tests/integration/test_celery.py
import pytest
from src.tasks.process_formlead import process_formlead_async

@pytest.mark.integration
def test_celery_task_processes_formlead(test_db):
    """Task processes formlead and updates database"""
    payload = {...}
    result = process_formlead_async.apply(
        args=(form_submission_id, payload),
        throw=True
    )
    assert result.successful()
    
    # Verify workflow record created
    # Verify status is success/failed
```

**Validation**:
- Start Redis: `redis-server` ✅
- Start Celery: `celery -A src.tasks.celery_app worker --loglevel=info` ✅
- Queue task and verify processing ✅

---

## 4.4: Feature Flag System (DRAFT_ONLY Toggle)

**Objective**: Create system to toggle DRAFT_ONLY mode per workflow  
**Acceptance Criteria**:
- [ ] Feature flag stored in database
- [ ] Can be updated via environment variable or API
- [ ] Affects email sending, task creation, drive operations
- [ ] Safe defaults (always DRAFT_ONLY in development)
- [ ] Can be toggled per workflow or globally

**Technical Spec**:

```python
# src/config/feature_flags.py
from enum import Enum
import os
from src.db.session import SessionLocal
from src.db.models import FeatureFlag

class WorkflowMode(str, Enum):
    DRAFT_ONLY = "DRAFT_ONLY"
    SEND = "SEND"

class FeatureFlagManager:
    """Manages feature flags with database backing"""
    
    @staticmethod
    def get_workflow_mode() -> WorkflowMode:
        """Get global workflow mode"""
        mode = os.getenv("WORKFLOW_MODE", "DRAFT_ONLY")
        return WorkflowMode(mode)
    
    @staticmethod
    def is_send_enabled() -> bool:
        """Check if sending is enabled"""
        return FeatureFlagManager.get_workflow_mode() == WorkflowMode.SEND
    
    @staticmethod
    def set_workflow_mode(mode: WorkflowMode):
        """Update workflow mode (requires auth)"""
        os.environ["WORKFLOW_MODE"] = mode.value

# Use in orchestrator
if FeatureFlagManager.is_send_enabled():
    await gmail_connector.send_message(...)  # Actually send
else:
    draft_id = await gmail_connector.create_draft(...)  # Only create draft
```

**Files to Create**:
- [ ] `src/config/feature_flags.py` - Feature flag logic
- [ ] `src/api/admin.py` - Admin endpoints to toggle

**Test Approach**:
```python
def test_draft_only_prevents_sends(monkeypatch):
    monkeypatch.setenv("WORKFLOW_MODE", "DRAFT_ONLY")
    # Verify draft created, not sent
    
def test_send_mode_sends(monkeypatch):
    monkeypatch.setenv("WORKFLOW_MODE", "SEND")
    # Verify email sent
```

---

## 4.5: Orchestrator Integration with Database

**Objective**: Persist workflow events and results to database  
**Acceptance Criteria**:
- [ ] Each orchestrator step creates WorkflowEvent record
- [ ] Errors create WorkflowError records
- [ ] Draft emails stored in database
- [ ] HubSpot tasks stored in database
- [ ] Audit trail complete and queryable

**Technical Spec**:

```python
# Update src/formlead_orchestrator.py

async def process_formlead(self, form_submission: Dict, workflow_id: str = None):
    """Process with database persistence"""
    workflow_id = workflow_id or f"formlead-{datetime.utcnow().isoformat()}"
    db = SessionLocal()
    
    try:
        # Create workflow record
        workflow = Workflow(
            id=workflow_id,
            status="processing",
            ...
        )
        db.add(workflow)
        db.commit()
        
        # Step 1: Validate
        try:
            result = await self._validate_form_payload(form_submission)
            self._record_event(db, workflow_id, 1, "validate_payload", "success", duration_ms=0)
        except Exception as e:
            self._record_error(db, workflow_id, 1, "validation_error", str(e))
            raise
        
        # ... repeat for each step ...
        
        # After draft creation
        draft = await self._create_draft(...)
        draft_record = DraftEmail(
            id=draft["id"],
            workflow_id=workflow_id,
            to_email=prospect["email"],
            subject=draft["subject"],
            body=draft["body"],
            gmail_draft_id=draft.get("gmail_id"),
            created_at=datetime.utcnow(),
        )
        db.add(draft_record)
        db.commit()
        
        # Update workflow final status
        workflow.status = "success"
        workflow.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        workflow.status = "failed"
        db.commit()
        raise
    finally:
        db.close()
    
    def _record_event(self, db, workflow_id, step, event_type, status, duration_ms):
        event = WorkflowEvent(
            id=f"evt-{uuid.uuid4()}",
            workflow_id=workflow_id,
            event_type=event_type,
            step_number=step,
            status=status,
            duration_ms=duration_ms,
            created_at=datetime.utcnow(),
        )
        db.add(event)
        db.commit()
```

---

## 4.6: Testing - E2E Workflow via Webhook

**Objective**: E2E test that form submission flows through webhook → queue → orchestrator → database  
**Acceptance Criteria**:
- [ ] Can POST form submission to webhook
- [ ] Task enqueued and processed
- [ ] Workflow record created
- [ ] Events recorded
- [ ] Draft email stored
- [ ] HubSpot task stored

**Test Approach**:

```python
# tests/integration/test_e2e_webhook_flow.py
@pytest.mark.integration
async def test_complete_formlead_via_webhook(client, test_db):
    """
    Complete E2E: webhook -> queue -> orchestrator -> database
    """
    # Send webhook
    payload = {...}
    response = client.post("/webhook/formlead", json=payload)
    assert response.status_code == 202
    
    # Wait for task to process (with timeout)
    workflow_id = response.json()["workflow_id"]
    await wait_for_workflow_completion(workflow_id, timeout=30)
    
    # Verify workflow record
    db = SessionLocal()
    workflow = db.query(Workflow).filter_by(id=workflow_id).first()
    assert workflow is not None
    assert workflow.status == "success"
    
    # Verify events
    events = db.query(WorkflowEvent).filter_by(workflow_id=workflow_id).all()
    assert len(events) == 12  # All 12 steps
    
    # Verify draft email
    draft = db.query(DraftEmail).filter_by(workflow_id=workflow_id).first()
    assert draft is not None
    assert draft.to_email == payload["email"]
    
    # Verify HubSpot task
    task = db.query(HubspotTask).filter_by(workflow_id=workflow_id).first()
    assert task is not None
```

---

## 4.7: Production Configuration

**Objective**: Production-ready environment variables, security, logging  
**Acceptance Criteria**:
- [ ] All secrets in environment variables (no hardcoding)
- [ ] Database connection pooling configured
- [ ] Logging goes to file + stdout
- [ ] CORS configured for webhook

**Files to Create**:
- [ ] `.env.production` - Template
- [ ] `src/config/settings.py` - Config management
- [ ] `logging.yml` - Logging configuration

---

## 4.8: Phase 4 Validation & Demo

**Objective**: Demonstrate complete production-enabled workflow  
**Demo Flow**:
1. POST form submission to webhook endpoint
2. Show in logs: task queued
3. Show Celery worker processing
4. Query database for workflow record
5. Show workflow events in audit trail
6. Show draft email created
7. Toggle DRAFT_ONLY mode
8. Show same workflow but with send enabled (don't actually send)

**Acceptance Criteria**:
- [ ] All Phase 4 tests passing
- [ ] Database populated with workflow data
- [ ] Can query audit trail
- [ ] Webhook accepts real HubSpot format
- [ ] No errors in logs
- [ ] Performance acceptable (<5sec per workflow)

---

# PHASE 5: CORE OPERATIONS UI (2 weeks)
**Goal**: Web dashboard for operators to see what's happening  
**Demoable Output**: Web interface showing workflows, drafts, recent activity

## 5.1: Frontend Setup (React + TypeScript)

**Objective**: Set up React + TypeScript, routing, component structure  
**Files to Create**:
- [ ] `frontend/package.json`
- [ ] `frontend/src/index.tsx`
- [ ] `frontend/src/App.tsx`
- [ ] `frontend/src/routes.tsx`
- [ ] Component structure for Dashboard, Workflows, Drafts

---

## 5.2: Workflow Dashboard Page

**Objective**: Display list of recent workflows with status  
**Features**:
- List of last 20 workflows
- Status indicators (processing, success, failed)
- Click to see details
- Filter by date range

---

## 5.3: Workflow Detail Page

**Objective**: Show complete audit trail for single workflow  
**Features**:
- Step-by-step execution timeline
- Timestamps for each step
- Links to Gmail draft, HubSpot task
- Error details if failed

---

## 5.4: Draft Email Viewer

**Objective**: Preview draft emails created  
**Features**:
- Show full email content
- Show assets included
- Show recipient
- Link to approve/send (if admin)

---

## 5.5: Settings & Admin Panel

**Objective**: Operational controls  
**Features**:
- Toggle DRAFT_ONLY mode
- View API logs
- Retry failed workflows
- Configure allowed form IDs

---

## 5.6: Real-time Updates (WebSockets)

**Objective**: Dashboard updates in real-time as workflows process  
**Features**:
- WebSocket connection to server
- Workflow status updates
- New workflow notifications

---

## 5.7: API Endpoints for Frontend

**Objective**: RESTful API for dashboard  
**Endpoints**:
- `GET /api/workflows` - List workflows
- `GET /api/workflows/{id}` - Workflow detail
- `GET /api/workflows/{id}/events` - Audit trail
- `GET /api/drafts` - Recent drafts
- `POST /api/admin/settings` - Update settings

---

## 5.8: Phase 5 Demo

**Demo Flow**:
1. Load dashboard
2. Show list of workflows
3. Click workflow to see audit trail
4. Click draft to preview email
5. Go to admin panel
6. Send test form submission
7. Watch it appear in dashboard in real-time

---

# PHASE 6: RELIABILITY & RECOVERY (2 weeks)

## 6.1: Error Classification

## 6.2: Retry Logic with Exponential Backoff

## 6.3: Dead-Letter Queue

## 6.4: Circuit Breaker Pattern

## 6.5: Reconciliation Jobs

## 6.6: Alert System

## 6.7: Observability Improvements

## 6.8: Phase 6 Demo

---

# PHASE 7: ASYNC & SCALING (2 weeks)

## 7.1: Multi-Queue Architecture

## 7.2: Worker Pool Management

## 7.3: Load Testing

## 7.4: Bulk Import API

## 7.5: Worker Monitoring

## 7.6: Database Optimization

## 7.7: Caching Layer

## 7.8: Phase 7 Demo

---

# PHASE 8: ADVANCED OBSERVABILITY (1.5 weeks)

## 8.1: Prometheus Metrics

## 8.2: Grafana Dashboards

## 8.3: PagerDuty Integration

## 8.4: Distributed Tracing (Jaeger)

## 8.5: Log Aggregation (Loki)

## 8.6: Synthetic Monitoring

## 8.7: Phase 8 Demo

---

# PHASE 9: MULTI-TENANCY & GO-LIVE (2.5 weeks)

## 9.1: Multi-Tenant Data Isolation

## 9.2: API Key Authentication

## 9.3: Billing & Usage Metering

## 9.4: Security Hardening

## 9.5: Comprehensive Documentation

## 9.6: Deployment Runbook

## 9.7: User Training Materials

## 9.8: Phase 9 Demo & Go-Live

---

# APPENDIX: Key Improvements from Subagent Review

1. **Database-First Design**: Schema designed before code ensures data integrity
2. **Feature Flags**: DRAFT_ONLY toggle allows safe production deployment
3. **Async Processing**: Celery queue prevents webhook timeouts
4. **Audit Trail**: Every step recorded for debugging and compliance
5. **Real-time UI**: WebSockets allow operators to monitor live
6. **Error Recovery**: Dead-letter queues + retries handle failures gracefully
7. **Multi-tenancy**: Prepared from Phase 9, not retrofitted
8. **Observability**: Metrics, logs, traces at every layer
9. **Scalability Path**: Single instance → multi-worker → Kubernetes
10. **Security**: HMAC validation, API keys, row-level isolation

---

# QUICK REFERENCE: Task Completion Checklist

## Phase 4 (Production Enablement)
- [ ] 4.1: Database schema created & migrated
- [ ] 4.2: Webhook receiver working & validated
- [ ] 4.3: Celery + Redis running & tasks queuing
- [ ] 4.4: Feature flags system implemented
- [ ] 4.5: Orchestrator persisting to database
- [ ] 4.6: E2E tests passing
- [ ] 4.7: Production config complete
- [ ] 4.8: Demo successful

## Phase 5 (UI)
- [ ] 5.1: React frontend scaffolded
- [ ] 5.2: Workflow dashboard page
- [ ] 5.3: Detail page & audit trail
- [ ] 5.4: Draft viewer
- [ ] 5.5: Admin panel
- [ ] 5.6: WebSocket real-time updates
- [ ] 5.7: API endpoints
- [ ] 5.8: Demo successful

*(Phases 6-9 detailed similarly)*

---

# TEAM ROADMAP

**Recommended Team Structure**:
- 1 Backend Engineer (Phases 4, 6, 7, 9)
- 1 Frontend Engineer (Phase 5)
- 1 DevOps/Infrastructure (Phases 4, 7, 8, 9)

**Total Duration**: ~12 weeks (3 months)  
**Total Effort**: ~480 engineer-hours (assuming 2 weeks per phase, 3 people)

