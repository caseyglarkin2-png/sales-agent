# Comprehensive Sprint Roadmap: Sales Agent Phase 4-9
## Production Deployment & Scaling (Phases 4-9)

**Current State (End of Phase 3):**
- ✅ 13-step orchestration engine complete and tested
- ✅ DRAFT_ONLY mode enforced (safety first)
- ✅ Mock tests passing, live connectors validated
- ❌ No webhook receiver → can't get real form submissions
- ❌ No database persistence → workflows not stored
- ❌ No UI → no visibility into system state
- ❌ DRAFT_ONLY constraint → no real sends yet
- ❌ No async processing → synchronous only

**End Goal (Phase 9):**
- ✅ Production-ready system with real sends
- ✅ Full observability (dashboard, metrics, logging)
- ✅ Reliable async processing with retries
- ✅ Multi-tenant capable
- ✅ Scaled to handle 100+ workflows/day
- ✅ Error recovery and rollback mechanisms

---

## Executive Summary

| Sprint | Focus | Demos | Duration |
|--------|-------|-------|----------|
| **Phase 4** | Production Enablement | Real sends enabled, webhook receiver live | 2 weeks |
| **Phase 5** | Core Operations UI | Dashboard, workflow tracking | 2 weeks |
| **Phase 6** | Reliability & Recovery | Retries, dead-letter queue, reconciliation | 2 weeks |
| **Phase 7** | Async Processing | Celery workers, job queuing, prioritization | 2 weeks |
| **Phase 8** | Advanced Observability | Metrics, tracing, anomaly detection | 1.5 weeks |
| **Phase 9** | Scaling & Multi-tenancy | Load balancing, multi-account support | 2 weeks |

**Total: ~11.5 weeks**

---

# PHASE 4: Production Enablement (2 weeks)

**Goal:** Enable production sends and build webhook server to receive real form submissions

**Key Deliverable:** System ready for production deployment with real sends and live form ingestion

---

## Phase 4 Sprint Tasks

### Task 4.1: Database Schema for Workflow Persistence

**Objective:** Design and implement database schema to store all workflow state

**Description:**

Current system has no workflow persistence. Add comprehensive schema to track:
- Workflow execution state (triggered → completed/failed)
- Form submission metadata
- Draft email content (for auditing)
- HubSpot task references
- Error logs and retry counts

**Acceptance Criteria:**
1. ✅ 6 new SQLAlchemy ORM models created
2. ✅ Alembic migration generated and tested
3. ✅ All models have proper indexes and constraints
4. ✅ Unit tests verify model creation and relationships
5. ✅ Migration runs successfully on fresh database

**Files to Create/Modify:**
- [src/models/workflow.py](src/models/workflow.py) (NEW - 200 lines)
- [src/models/form_submission.py](src/models/form_submission.py) (NEW - 150 lines)
- [infra/migrations/versions/001_initial_schema.py](infra/migrations/versions/001_initial_schema.py) (NEW)

**Database Schema:**

```sql
-- Workflow execution tracking
CREATE TABLE workflows (
    id UUID PRIMARY KEY,
    form_submission_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL,  -- triggered, processing, completed, failed
    mode VARCHAR(20) NOT NULL,    -- DRAFT_ONLY, SEND
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    error_message TEXT,
    error_count INT DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (form_submission_id) REFERENCES form_submissions(id)
);
CREATE INDEX idx_workflows_status ON workflows(status);
CREATE INDEX idx_workflows_created_at ON workflows(created_at DESC);

-- Form submission storage
CREATE TABLE form_submissions (
    id UUID PRIMARY KEY,
    portal_id INT NOT NULL,
    form_id VARCHAR(255) NOT NULL,
    form_submission_id VARCHAR(255) NOT NULL UNIQUE,
    prospect_email VARCHAR(255) NOT NULL,
    prospect_first_name VARCHAR(255),
    prospect_last_name VARCHAR(255),
    prospect_company VARCHAR(255),
    raw_payload JSONB,
    hubspot_contact_id VARCHAR(255),
    hubspot_company_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    received_at TIMESTAMP NOT NULL,
    UNIQUE(portal_id, form_id, form_submission_id)
);
CREATE INDEX idx_form_submissions_email ON form_submissions(prospect_email);
CREATE INDEX idx_form_submissions_received_at ON form_submissions(received_at DESC);

-- Draft email storage
CREATE TABLE draft_emails (
    id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL,
    form_submission_id UUID NOT NULL,
    gmail_draft_id VARCHAR(255),
    recipient_email VARCHAR(255) NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    approved_at TIMESTAMP,
    approved_by VARCHAR(255),
    sent_at TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id),
    FOREIGN KEY (form_submission_id) REFERENCES form_submissions(id)
);
CREATE INDEX idx_draft_emails_workflow_id ON draft_emails(workflow_id);

-- HubSpot task references
CREATE TABLE hubspot_tasks (
    id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL,
    hubspot_task_id VARCHAR(255) NOT NULL UNIQUE,
    contact_id VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    due_date TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    hubspot_created_at TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);
CREATE INDEX idx_hubspot_tasks_workflow_id ON hubspot_tasks(workflow_id);

-- Error tracking and retry state
CREATE TABLE workflow_errors (
    id UUID PRIMARY KEY,
    workflow_id UUID NOT NULL,
    error_type VARCHAR(255) NOT NULL,
    error_message TEXT NOT NULL,
    traceback TEXT,
    step_name VARCHAR(255),
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    next_retry_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);
CREATE INDEX idx_workflow_errors_workflow_id ON workflow_errors(workflow_id);
CREATE INDEX idx_workflow_errors_next_retry_at ON workflow_errors(next_retry_at);
```

**SQLAlchemy Models:**

```python
# src/models/workflow.py
from datetime import datetime
from typing import Optional
from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Index, String, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.db import Base

class WorkflowStatus(str, Enum):
    TRIGGERED = "triggered"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class WorkflowMode(str, Enum):
    DRAFT_ONLY = "DRAFT_ONLY"
    SEND = "SEND"

class Workflow(Base):
    __tablename__ = "workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    form_submission_id = Column(UUID(as_uuid=True), ForeignKey("form_submissions.id"), nullable=False)
    status = Column(SQLEnum(WorkflowStatus), nullable=False, default=WorkflowStatus.TRIGGERED)
    mode = Column(SQLEnum(WorkflowMode), nullable=False, default=WorkflowMode.DRAFT_ONLY)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    form_submission = relationship("FormSubmission", back_populates="workflows")
    draft_emails = relationship("DraftEmail", back_populates="workflow")
    hubspot_tasks = relationship("HubSpotTask", back_populates="workflow")
    errors = relationship("WorkflowError", back_populates="workflow")
    
    __table_args__ = (
        Index("idx_workflows_status", "status"),
        Index("idx_workflows_created_at", created_at.desc()),
    )

class FormSubmission(Base):
    __tablename__ = "form_submissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    portal_id = Column(Integer, nullable=False)
    form_id = Column(String(255), nullable=False)
    form_submission_id = Column(String(255), nullable=False, unique=True)
    prospect_email = Column(String(255), nullable=False)
    prospect_first_name = Column(String(255), nullable=True)
    prospect_last_name = Column(String(255), nullable=True)
    prospect_company = Column(String(255), nullable=True)
    raw_payload = Column(JSONB, nullable=True)
    hubspot_contact_id = Column(String(255), nullable=True)
    hubspot_company_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    workflows = relationship("Workflow", back_populates="form_submission")
    
    __table_args__ = (
        Index("idx_form_submissions_email", prospect_email),
        Index("idx_form_submissions_received_at", received_at.desc()),
    )
```

**Testing Approach:**
- Unit tests: Create models, verify relationships, test constraints
- Integration tests: Run migration on test database, verify schema
- Verification: `pytest tests/unit/test_models_workflow.py -v`

**Effort:** 1 day

---

### Task 4.2: Remove DRAFT_ONLY Constraint (Feature Flag)

**Objective:** Implement feature flag system to toggle DRAFT_ONLY mode with proper safety gates

**Description:**

Currently DRAFT_ONLY is hardcoded. Implement feature flag system that:
1. Keeps DRAFT_ONLY as default in all environments
2. Allows toggling to SEND mode only when conditions met:
   - In production environment only
   - With explicit feature flag enabled
   - With operator approval logged
   - With email allowlist configured
3. Creates audit trail for every mode change
4. Prevents SEND mode in development/staging

**Acceptance Criteria:**
1. ✅ Feature flag system implemented with config validation
2. ✅ `mode_draft_only` can be toggled to false only in production
3. ✅ Every send operation checks flag before executing
4. ✅ Mode changes logged to audit trail with who/when/why
5. ✅ Unit tests verify:
   - SEND mode blocked in non-production
   - Audit log created on mode change
   - Backwards-compatible with existing DRAFT_ONLY code
6. ✅ Integration test: Can toggle mode and verify behavior

**Files to Modify:**
- [src/config.py](src/config.py) (enhance ~20 lines)
- [src/connectors/gmail.py](src/connectors/gmail.py) (add send check ~5 lines)
- [src/connectors/hubspot.py](src/connectors/hubspot.py) (add send check ~5 lines)
- [src/audit.py](src/audit.py) (add mode_changed event ~10 lines)
- [tests/unit/test_config.py](tests/unit/test_config.py) (add tests ~50 lines)

**Code Changes:**

```python
# src/config.py - Add validation
class Settings(BaseSettings):
    # ... existing fields ...
    mode_draft_only: bool = Field(default=True)
    allow_auto_send: bool = Field(default=False)
    require_approval: bool = Field(default=True)
    send_email_allowlist: list[str] = Field(
        default=["sales@company.com"],
        description="Emails allowed to send from (production only)"
    )
    
    def validate_send_mode(self) -> None:
        """Validate SEND mode is only enabled in production with proper conditions."""
        if not self.mode_draft_only:  # SEND mode enabled
            if self.api_env != "production":
                raise ValueError("SEND mode only allowed in production environment")
            if not self.allow_auto_send:
                raise ValueError("SEND mode requires allow_auto_send=true")
            if not self.send_email_allowlist:
                raise ValueError("SEND mode requires send_email_allowlist configured")
            logger.warning(
                "⚠️ SEND mode enabled (DRAFT_ONLY=false). Monitor carefully.",
                env=self.api_env,
                allowlist=self.send_email_allowlist
            )

# src/connectors/gmail.py - Add send check
async def send_email(self, to: str, subject: str, body: str) -> str:
    """Send email (checks DRAFT_ONLY flag)."""
    settings = get_settings()
    
    if settings.mode_draft_only:
        logger.warning(f"SEND blocked: DRAFT_ONLY mode active", to=to)
        raise RuntimeError("Cannot send email in DRAFT_ONLY mode")
    
    # Actually send email
    ...

# src/audit.py - Add mode change logging
class AuditTrail:
    @staticmethod
    def log_mode_changed(old_mode: str, new_mode: str, changed_by: str, reason: str):
        """Log mode change."""
        details = {
            "old_mode": old_mode,
            "new_mode": new_mode,
            "changed_by": changed_by,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.info("Mode changed", event_type="mode_changed", **details)
```

**Testing Approach:**
- Unit tests: Verify validation logic, mode checks
- Integration tests: Toggle mode in test environment, verify error handling
- Verification: `pytest tests/unit/test_config.py -v`

**Effort:** 1 day

---

### Task 4.3: Webhook Server Implementation

**Objective:** Build webhook receiver endpoint to accept real HubSpot form submissions

**Description:**

Current system only works with CLI mocking. Implement production webhook receiver that:
1. Receives HubSpot form webhooks at `/api/webhooks/hubspot/forms`
2. Validates webhook signature (HMAC-SHA256)
3. Stores form submission to database
4. Queues workflow for processing
5. Returns success response immediately (async processing)
6. Handles retries and deduplication

**Acceptance Criteria:**
1. ✅ POST endpoint `/api/webhooks/hubspot/forms` working
2. ✅ Webhook signature validation passes/fails correctly
3. ✅ Form submission stored to database with raw payload
4. ✅ Duplicate submissions detected and skipped (idempotent)
5. ✅ Response returned immediately (202 Accepted)
6. ✅ Failed validations logged to audit trail
7. ✅ Integration tests with mock HubSpot webhooks
8. ✅ Manual test with HubSpot sandbox form

**Files to Create/Modify:**
- [src/routes/webhooks.py](src/routes/webhooks.py) (enhance ~100 lines)
- [src/webhooks_processor.py](src/webhooks_processor.py) (NEW - 200 lines)
- [tests/integration/test_webhook_receiver.py](tests/integration/test_webhook_receiver.py) (NEW - 150 lines)

**Endpoint Specification:**

```python
# src/routes/webhooks.py
@router.post("/hubspot/forms", status_code=202, tags=["Webhooks"])
async def receive_hubspot_form_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> JSONResponse:
    """
    Receive HubSpot form submission webhook.
    
    - Validates signature
    - Stores submission to database
    - Queues for async processing
    - Returns 202 Accepted immediately
    
    HubSpot sends X-HubSpot-Signature header with HMAC-SHA256 signature.
    """
    settings = get_settings()
    
    # Get raw body for signature validation
    raw_body = await request.body()
    
    # Validate signature
    signature = request.headers.get("X-HubSpot-Signature", "")
    validator = WebhookValidator(settings.hubspot_webhook_secret)
    if not validator.verify_signature(raw_body.decode(), signature):
        logger.warning("Webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Signature verification failed")
    
    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Store form submission
    form_submission = await store_form_submission(
        portal_id=payload.get("portalId"),
        form_id=payload.get("formId"),
        form_submission_id=payload.get("formSubmissionId"),
        payload=payload,
        session=session
    )
    
    # Queue for async processing (Task 4.4)
    queue_workflow_processing(form_submission.id)
    
    logger.info(f"Webhook received and queued", form_id=payload.get("formId"))
    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "submission_id": str(form_submission.id)}
    )
```

**HubSpot Webhook Configuration:**

```
Endpoint URL: https://your-domain.com/api/webhooks/hubspot/forms
Method: POST
Events: form.submission.create
Authentication: HMAC-SHA256
Signature Header: X-HubSpot-Signature
```

**Testing Approach:**
- Unit tests: Signature validation, payload parsing
- Integration tests: Create mock webhook, verify database storage, check deduplication
- Manual test: Configure real HubSpot form webhook in sandbox
- Verification: `pytest tests/integration/test_webhook_receiver.py -v`

**Effort:** 1.5 days

---

### Task 4.4: Async Processing Queue (Celery)

**Objective:** Implement async task queue to process workflows asynchronously

**Description:**

Current system processes workflows synchronously (blocking). Implement Celery-based queue that:
1. Decouples webhook receiver from workflow processing
2. Allows workflow processing to fail without affecting API response
3. Enables retries with exponential backoff
4. Stores task execution history
5. Provides dead-letter queue for failed tasks

**Acceptance Criteria:**
1. ✅ Celery workers configured and running
2. ✅ `process_workflow_task` celery task implemented
3. ✅ Automatic retries (3 attempts, exponential backoff)
4. ✅ Failed tasks stored to dead-letter queue
5. ✅ Task history stored in database
6. ✅ Unit tests mock celery tasks
7. ✅ Integration tests run workers and verify processing
8. ✅ Works with docker-compose

**Files to Create/Modify:**
- [src/tasks.py](src/tasks.py) (enhance ~100 lines)
- [src/celery_app.py](src/celery_app.py) (NEW - 100 lines)
- [infra/celery_worker.py](infra/celery_worker.py) (NEW - 50 lines)
- [docker-compose.yml](docker-compose.yml) (add celery service)
- [tests/integration/test_celery_tasks.py](tests/integration/test_celery_tasks.py) (NEW - 100 lines)

**Celery Configuration:**

```python
# src/celery_app.py
from celery import Celery
from src.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sales_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 min hard limit
    task_soft_time_limit=25 * 60,  # 25 min soft limit
)

# src/tasks.py - Add celery task
from src.celery_app import celery_app
from src.formlead_orchestrator import FormleadOrchestrator

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def process_workflow_task(self, form_submission_id: str):
    """Process workflow asynchronously with retries."""
    try:
        logger.info(f"Processing workflow {form_submission_id}", task_id=self.request.id)
        
        # Load form submission from database
        form_submission = get_form_submission(form_submission_id)
        
        # Process workflow
        orchestrator = FormleadOrchestrator(...)
        result = asyncio.run(orchestrator.process_formlead(form_submission.raw_payload))
        
        # Store result
        update_workflow_status(form_submission_id, "completed", result)
        logger.info(f"Workflow completed {form_submission_id}")
        
        return result
        
    except Exception as exc:
        logger.error(f"Workflow failed: {exc}", exc_info=True)
        update_workflow_status(form_submission_id, "failed", {"error": str(exc)})
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

**docker-compose.yml Addition:**

```yaml
services:
  celery_worker:
    build: .
    command: celery -A src.celery_app worker --loglevel=info --concurrency=4
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - redis
    volumes:
      - .:/workspaces/sales-agent
```

**Testing Approach:**
- Unit tests: Mock celery tasks, verify retry logic
- Integration tests: Run workers with test broker, verify task execution
- Verification: `pytest tests/integration/test_celery_tasks.py -v`

**Effort:** 1.5 days

---

### Task 4.5: Production Config & Deployment Guide

**Objective:** Document and implement production deployment configuration

**Description:**

Create production-ready configuration and deployment documentation:
1. Environment variables for production (`.env.production.example`)
2. Security hardening checklist
3. Health check endpoints
4. Graceful shutdown handling
5. Monitoring hooks (logs, metrics)
6. Deployment runbook

**Acceptance Criteria:**
1. ✅ `.env.production.example` created with all required vars
2. ✅ Health check endpoint returns comprehensive status
3. ✅ Ready-to-deploy documentation
4. ✅ Pre-flight checklist for production deployment
5. ✅ Rollback procedures documented
6. ✅ Configuration validation tests pass

**Files to Create/Modify:**
- [.env.production.example](.env.production.example) (NEW)
- [docs/PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md) (enhance)
- [src/main.py](src/main.py) (add comprehensive health check)

**Health Check Endpoint:**

```python
# src/main.py
@app.get("/health/live", tags=["Health"])
async def liveness_check() -> JSONResponse:
    """K8s liveness probe - is app running?"""
    return JSONResponse({"status": "alive"})

@app.get("/health/ready", tags=["Health"])
async def readiness_check(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    """K8s readiness probe - can app handle traffic?"""
    try:
        # Check database
        await session.execute(text("SELECT 1"))
        
        # Check Redis
        redis_check = await check_redis_connection()
        
        # Check API keys configured
        settings = get_settings()
        keys_configured = all([
            settings.openai_api_key,
            settings.google_client_id,
            settings.hubspot_api_key,
        ])
        
        if not (redis_check and keys_configured):
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "details": {
                    "database": True,
                    "redis": redis_check,
                    "credentials": keys_configured
                }}
            )
        
        return JSONResponse({"status": "ready"})
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)}
        )
```

**Testing Approach:**
- Unit tests: Config validation
- Integration tests: Health checks with dependencies
- Verification: Deploy to staging and verify all checks pass

**Effort:** 1 day

---

### Task 4.6: Phase 4 Testing & Validation

**Objective:** Comprehensive testing of all Phase 4 features

**Description:**

Create test suite that validates:
1. Webhook receives and queues submissions
2. DRAFT_ONLY flag enforced properly
3. Database persists workflows correctly
4. Celery tasks process and retry
5. Production config validated

**Acceptance Criteria:**
1. ✅ E2E test: Form submission → webhook → queue → workflow → database
2. ✅ E2E test: Failed workflow retries and recovers
3. ✅ Config validation prevents unsafe production mode
4. ✅ All unit tests passing
5. ✅ Coverage > 80% for new code
6. ✅ Integration tests passing

**Files to Create:**
- [tests/integration/test_phase4_e2e.py](tests/integration/test_phase4_e2e.py) (NEW - 200 lines)

**E2E Test Scenario:**

```python
# Test: Form webhook → persisted workflow → completed status
async def test_webhook_to_completion():
    """Test complete workflow from webhook to database."""
    # 1. Send webhook
    webhook_payload = create_mock_webhook()
    response = client.post(
        "/api/webhooks/hubspot/forms",
        json=webhook_payload,
        headers={"X-HubSpot-Signature": compute_signature(webhook_payload)}
    )
    assert response.status_code == 202
    
    # 2. Verify form submission stored
    submission = await get_form_submission_by_id(response.json()["submission_id"])
    assert submission.prospect_email == webhook_payload["fieldValues"][0]["value"]
    
    # 3. Run celery worker
    worker = start_celery_worker()
    
    # 4. Wait for workflow completion
    workflow = await wait_for_workflow_completion(submission.id)
    assert workflow.status == WorkflowStatus.COMPLETED
    
    # 5. Verify artifacts
    assert workflow.draft_emails.count() > 0
    assert workflow.hubspot_tasks.count() > 0
```

**Testing Approach:**
- Unit: Individual component tests
- Integration: Multi-component workflows
- E2E: Complete webhook-to-completion scenarios
- Verification: `pytest tests/integration/test_phase4_e2e.py -v`

**Effort:** 1.5 days

---

## Phase 4 Summary

**What Gets Built:**
- ✅ Database schema for workflow persistence
- ✅ Feature flag system to toggle DRAFT_ONLY mode
- ✅ Webhook receiver for real form submissions
- ✅ Celery async processing with retries
- ✅ Production configuration and health checks

**What Gets Demoed:**
1. Form submission via HubSpot webhook
2. Workflow persisted to database with status tracking
3. Async processing with retry visibility
4. Mode toggle (DRAFT_ONLY → SEND) in production
5. Health checks passing

**Time Breakdown:**
- Task 4.1: Database schema - 1 day
- Task 4.2: Feature flag system - 1 day  
- Task 4.3: Webhook receiver - 1.5 days
- Task 4.4: Celery async processing - 1.5 days
- Task 4.5: Production config - 1 day
- Task 4.6: Testing & validation - 1.5 days
- **Total: 8 days (1.6 weeks)**

---

# PHASE 5: Core Operations UI (2 weeks)

**Goal:** Build dashboard for ops team to see what's happening

**Key Deliverable:** Web-based dashboard showing workflows, drafts, status, and basic controls

---

## Phase 5 Sprint Tasks

### Task 5.1: React Dashboard Project Setup

**Objective:** Initialize modern React app for operations dashboard

**Description:**

Create new React/TypeScript frontend at `/frontend` with:
1. Vite build tool (fast development)
2. TailwindCSS for styling (rapid UI)
3. React Query for API state management
4. TypeScript for type safety
5. Accessible component library

**Acceptance Criteria:**
1. ✅ React app runs on http://localhost:3000
2. ✅ Can call backend API at http://localhost:8000
3. ✅ TypeScript strict mode enabled
4. ✅ Tailwind configured
5. ✅ Build produces optimized bundle
6. ✅ CORS configured between frontend and backend

**Files to Create:**
- [frontend/](frontend/) (NEW directory structure)
- [frontend/package.json](frontend/package.json)
- [frontend/vite.config.ts](frontend/vite.config.ts)
- [frontend/src/main.tsx](frontend/src/main.tsx)
- [frontend/src/App.tsx](frontend/src/App.tsx)
- [frontend/src/api/client.ts](frontend/src/api/client.ts) (NEW)

**Setup Commands:**

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer @tanstack/react-query
npx tailwindcss init -p
```

**CORS Configuration (Backend):**

```python
# src/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Effort:** 0.5 days

---

### Task 5.2: Dashboard Layout & Navigation

**Objective:** Build main dashboard layout with navigation structure

**Description:**

Create responsive dashboard layout with:
1. Top navigation bar (logo, user, settings)
2. Sidebar navigation (workflows, drafts, settings, logs)
3. Main content area with breadcrumbs
4. Responsive mobile layout
5. Dark mode toggle

**Acceptance Criteria:**
1. ✅ Layout responsive on desktop/tablet/mobile
2. ✅ Navigation between pages works
3. ✅ Sidebar collapses on mobile
4. ✅ Dark mode CSS variables implemented
5. ✅ All navigation links functional
6. ✅ Accessibility: ARIA labels, keyboard navigation

**Files to Create:**
- [frontend/src/layouts/DashboardLayout.tsx](frontend/src/layouts/DashboardLayout.tsx) (NEW)
- [frontend/src/components/Sidebar.tsx](frontend/src/components/Sidebar.tsx) (NEW)
- [frontend/src/components/TopBar.tsx](frontend/src/components/TopBar.tsx) (NEW)
- [frontend/src/pages/Dashboard.tsx](frontend/src/pages/Dashboard.tsx) (NEW)
- [frontend/src/pages/Workflows.tsx](frontend/src/pages/Workflows.tsx) (NEW - stub)
- [frontend/src/pages/Drafts.tsx](frontend/src/pages/Drafts.tsx) (NEW - stub)
- [frontend/src/pages/Settings.tsx](frontend/src/pages/Settings.tsx) (NEW - stub)

**Component Structure:**

```tsx
// frontend/src/layouts/DashboardLayout.tsx
export const DashboardLayout: React.FC<{children: React.ReactNode}> = ({ children }) => (
  <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
    <Sidebar />
    <div className="flex flex-col flex-1">
      <TopBar />
      <main className="flex-1 overflow-auto p-6">
        {children}
      </main>
    </div>
  </div>
)

// frontend/src/components/Sidebar.tsx
export const Sidebar: React.FC = () => (
  <nav className="w-64 bg-white dark:bg-gray-800 shadow-lg">
    <div className="p-4">
      <h1 className="text-2xl font-bold">Sales Agent</h1>
    </div>
    <ul className="space-y-2">
      <li><Link to="/workflows">📊 Workflows</Link></li>
      <li><Link to="/drafts">✉️ Drafts</Link></li>
      <li><Link to="/tasks">📋 Tasks</Link></li>
      <li><Link to="/logs">📝 Logs</Link></li>
      <li><Link to="/settings">⚙️ Settings</Link></li>
    </ul>
  </nav>
)
```

**Effort:** 1 day

---

### Task 5.3: Workflows List & Detail Pages

**Objective:** Build workflow list and detail views with real data

**Description:**

Create pages to view and manage workflows:
1. Workflows list view (table, pagination, filters)
2. Workflow detail view (full context, step-by-step status)
3. Real-time status updates (polling or WebSocket)
4. Filter by date, status, prospect
5. Manual retry button

**Acceptance Criteria:**
1. ✅ List shows all workflows with: ID, prospect, status, created_at
2. ✅ Pagination works (20 per page)
3. ✅ Can filter by status, date range, prospect email
4. ✅ Detail page shows all 13 workflow steps with status
5. ✅ Can click to retry failed workflow
6. ✅ Real-time updates (10-second polling)
7. ✅ Mobile-responsive table

**Files to Create:**
- [frontend/src/pages/Workflows.tsx](frontend/src/pages/Workflows.tsx) (NEW - 300 lines)
- [frontend/src/pages/WorkflowDetail.tsx](frontend/src/pages/WorkflowDetail.tsx) (NEW - 300 lines)
- [frontend/src/components/WorkflowTable.tsx](frontend/src/components/WorkflowTable.tsx) (NEW)
- [frontend/src/components/WorkflowSteps.tsx](frontend/src/components/WorkflowSteps.tsx) (NEW)
- [frontend/src/hooks/useWorkflows.ts](frontend/src/hooks/useWorkflows.ts) (NEW)

**Backend API Endpoints Needed:**
- `GET /api/workflows` - List workflows with pagination/filters
- `GET /api/workflows/{id}` - Get workflow detail
- `POST /api/workflows/{id}/retry` - Retry failed workflow

**Workflows List Table:**

```tsx
// frontend/src/pages/Workflows.tsx
export const Workflows: React.FC = () => {
  const { workflows, isLoading } = useWorkflows();
  
  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Workflows</h1>
      
      <div className="mb-4 flex gap-4">
        <Input placeholder="Filter by email..." onChange={setEmailFilter} />
        <Select value={statusFilter} onChange={setStatusFilter}>
          <option value="">All Status</option>
          <option value="triggered">Triggered</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </Select>
      </div>
      
      <table className="w-full border-collapse bg-white rounded shadow">
        <thead>
          <tr className="bg-gray-100">
            <th className="p-3 text-left">ID</th>
            <th className="p-3 text-left">Prospect</th>
            <th className="p-3 text-left">Status</th>
            <th className="p-3 text-left">Created</th>
            <th className="p-3 text-center">Actions</th>
          </tr>
        </thead>
        <tbody>
          {workflows.map(w => (
            <tr key={w.id} className="border-b hover:bg-gray-50">
              <td className="p-3"><Link to={`/workflows/${w.id}`}>{w.id.slice(0,8)}</Link></td>
              <td className="p-3">{w.prospect_email}</td>
              <td className="p-3">
                <StatusBadge status={w.status} />
              </td>
              <td className="p-3">{new Date(w.created_at).toLocaleDateString()}</td>
              <td className="p-3 text-center">
                {w.status === "failed" && (
                  <Button onClick={() => retryWorkflow(w.id)}>Retry</Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

**Backend API Implementation:**

```python
# src/routes/api.py (NEW)
@router.get("/workflows", tags=["Workflows"])
async def list_workflows(
    status: Optional[str] = None,
    email: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """List workflows with pagination and filters."""
    query = select(Workflow).order_by(Workflow.created_at.desc())
    
    if status:
        query = query.where(Workflow.status == status)
    if email:
        query = query.join(FormSubmission).where(
            FormSubmission.prospect_email.ilike(f"%{email}%")
        )
    
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    workflows = result.scalars().all()
    
    return {
        "workflows": [workflow.to_dict() for workflow in workflows],
        "total": len(workflows)
    }

@router.get("/workflows/{workflow_id}", tags=["Workflows"])
async def get_workflow_detail(
    workflow_id: str,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get workflow detail including all steps."""
    result = await session.execute(
        select(Workflow).where(Workflow.id == UUID(workflow_id))
    )
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return workflow.to_detail_dict()
```

**Testing Approach:**
- Component tests: Rendering, pagination, filtering
- Integration tests: Mock API responses, verify display
- E2E tests: User interactions, filtering, navigation

**Effort:** 2 days

---

### Task 5.4: Drafts Review & Approval UI

**Objective:** Build UI for reviewing and approving draft emails

**Description:**

Create draft review interface where sales ops can:
1. See all pending drafts (awaiting approval)
2. Preview full email (subject, body)
3. See prospect context (company, past emails)
4. Approve or reject draft
5. Add notes/comments before approval
6. Bulk operations (approve multiple at once)

**Acceptance Criteria:**
1. ✅ Drafts list shows pending/approved/rejected
2. ✅ Detail view shows full email with context
3. ✅ Can approve/reject individual draft
4. ✅ Bulk approve working
5. ✅ Approval logged with timestamp and approver name
6. ✅ Rejected drafts show reason
7. ✅ Mobile-friendly draft preview

**Files to Create:**
- [frontend/src/pages/Drafts.tsx](frontend/src/pages/Drafts.tsx) (NEW - 300 lines)
- [frontend/src/pages/DraftDetail.tsx](frontend/src/pages/DraftDetail.tsx) (NEW - 250 lines)
- [frontend/src/components/DraftPreview.tsx](frontend/src/components/DraftPreview.tsx) (NEW)
- [frontend/src/hooks/useDrafts.ts](frontend/src/hooks/useDrafts.ts) (NEW)

**Backend API Endpoints Needed:**
- `GET /api/drafts` - List drafts by status
- `GET /api/drafts/{id}` - Get draft with context
- `POST /api/drafts/{id}/approve` - Approve draft
- `POST /api/drafts/{id}/reject` - Reject draft

**Drafts List Component:**

```tsx
// frontend/src/pages/Drafts.tsx
export const Drafts: React.FC = () => {
  const [draftStatus, setDraftStatus] = useState<"pending" | "approved" | "rejected">("pending");
  const { drafts, isLoading } = useDrafts(draftStatus);
  
  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Draft Emails</h1>
      
      <div className="mb-4 flex gap-2">
        {["pending", "approved", "rejected"].map(status => (
          <Button
            key={status}
            variant={draftStatus === status ? "primary" : "secondary"}
            onClick={() => setDraftStatus(status as any)}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)} ({drafts.length})
          </Button>
        ))}
      </div>
      
      <div className="space-y-3">
        {drafts.map(draft => (
          <div key={draft.id} className="border rounded p-4 hover:bg-gray-50">
            <div className="flex justify-between">
              <div>
                <h3 className="font-bold">{draft.recipient_email}</h3>
                <p className="text-sm text-gray-600">{draft.subject}</p>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => viewDraft(draft.id)}>View</Button>
                {draftStatus === "pending" && (
                  <>
                    <Button size="sm" variant="success" onClick={() => approveDraft(draft.id)}>
                      Approve
                    </Button>
                    <Button size="sm" variant="danger" onClick={() => rejectDraft(draft.id)}>
                      Reject
                    </Button>
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Effort:** 2 days

---

### Task 5.5: Real-time Status Updates & WebSockets (Optional)

**Objective:** Implement WebSocket for real-time workflow updates

**Description:**

Add WebSocket support for real-time updates (instead of polling):
1. WebSocket connection at `/ws/workflows`
2. Subscribe to workflow updates
3. Auto-refresh when status changes
4. Dashboard shows "live" badge

**Acceptance Criteria:**
1. ✅ WebSocket endpoint working
2. ✅ Frontend subscribes to updates
3. ✅ Workflows list updates automatically
4. ✅ Falls back to polling if WebSocket unavailable
5. ✅ Graceful reconnect on disconnect

**Files to Create:**
- [src/websockets.py](src/websockets.py) (NEW - 100 lines)
- [frontend/src/hooks/useWorkflowUpdates.ts](frontend/src/hooks/useWorkflowUpdates.ts) (NEW)

**Backend Implementation:**

```python
# src/websockets.py
@app.websocket("/ws/workflows")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time workflow updates."""
    await websocket.accept()
    try:
        while True:
            # Broadcast workflow updates every 5 seconds
            workflows = await get_recent_workflows()
            await websocket.send_json({
                "type": "workflows_update",
                "data": workflows
            })
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info("Client disconnected from workflows WebSocket")
```

**Effort:** 1 day (optional, can defer)

---

### Task 5.6: Settings & Admin Controls

**Objective:** Build settings page for operators

**Description:**

Create settings page for:
1. DRAFT_ONLY / SEND mode toggle (production only)
2. Approval workflows (auto-approve certain patterns)
3. Email allowlist management
4. Webhook configuration
5. System health status
6. Audit log viewer

**Acceptance Criteria:**
1. ✅ Settings page shows current configuration
2. ✅ Can toggle mode (with confirmation prompt)
3. ✅ Allowlist management UI
4. ✅ Health check displayed
5. ✅ Audit log searchable
6. ✅ Settings changes logged

**Files to Create:**
- [frontend/src/pages/Settings.tsx](frontend/src/pages/Settings.tsx) (NEW - 300 lines)
- [frontend/src/pages/AuditLog.tsx](frontend/src/pages/AuditLog.tsx) (NEW - 200 lines)
- [frontend/src/hooks/useSettings.ts](frontend/src/hooks/useSettings.ts) (NEW)

**Settings Page Layout:**

```tsx
// frontend/src/pages/Settings.tsx
export const Settings: React.FC = () => {
  const { settings, updateSettings } = useSettings();
  
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Settings</h1>
      
      <Card>
        <h2 className="text-xl font-bold mb-4">Mode Configuration</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold">DRAFT_ONLY Mode</p>
              <p className="text-sm text-gray-600">When enabled, all emails created as drafts</p>
            </div>
            <Toggle
              checked={settings.mode_draft_only}
              onChange={(checked) => updateSettings({ mode_draft_only: checked })}
            />
          </div>
          
          {!settings.mode_draft_only && (
            <Alert severity="warning">
              ⚠️ SEND mode is ENABLED. Emails will be sent automatically.
            </Alert>
          )}
        </div>
      </Card>
      
      <Card>
        <h2 className="text-xl font-bold mb-4">System Health</h2>
        <SystemHealthStatus />
      </Card>
      
      <Card>
        <h2 className="text-xl font-bold mb-4">Email Allowlist</h2>
        <AllowlistManager />
      </Card>
    </div>
  );
}
```

**Backend Settings API:**

```python
# src/routes/api.py
@router.get("/settings", tags=["Settings"])
async def get_settings_for_ui() -> Dict[str, Any]:
    """Get current settings for UI."""
    settings = get_settings()
    return {
        "mode_draft_only": settings.mode_draft_only,
        "allow_auto_send": settings.allow_auto_send,
        "require_approval": settings.require_approval,
        "api_env": settings.api_env,
        "send_email_allowlist": settings.send_email_allowlist,
    }

@router.post("/settings/mode", tags=["Settings"])
async def update_mode(
    mode_draft_only: bool,
    reason: str,
    current_user: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update mode (DRAFT_ONLY toggle)."""
    old_mode = "DRAFT_ONLY" if get_settings().mode_draft_only else "SEND"
    new_mode = "DRAFT_ONLY" if mode_draft_only else "SEND"
    
    AuditTrail.log_mode_changed(old_mode, new_mode, current_user, reason)
    
    # Update environment/config
    update_config("MODE_DRAFT_ONLY", str(mode_draft_only))
    
    return {"status": "updated", "old_mode": old_mode, "new_mode": new_mode}
```

**Effort:** 1.5 days

---

### Task 5.7: Phase 5 Testing & Documentation

**Objective:** Test all dashboard features and document for operators

**Description:**

1. Component and integration tests for frontend
2. API contract tests
3. User acceptance testing checklist
4. Operator training documentation

**Acceptance Criteria:**
1. ✅ All React components have tests
2. ✅ Happy path E2E tests
3. ✅ API contract verified
4. ✅ Operator guide created

**Files to Create:**
- [frontend/src/__tests__/](frontend/src/__tests__/) (NEW test directory)
- [docs/OPERATOR_GUIDE.md](docs/OPERATOR_GUIDE.md) (NEW)

**Effort:** 1.5 days

---

## Phase 5 Summary

**What Gets Built:**
- ✅ React dashboard app with Tailwind styling
- ✅ Workflows list and detail pages
- ✅ Draft review and approval interface
- ✅ Settings and admin controls
- ✅ Real-time status updates (polling)
- ✅ Comprehensive operator documentation

**What Gets Demoed:**
1. Dashboard loads with recent workflows
2. Filter and search workflows
3. View workflow details with step-by-step status
4. Approve/reject draft emails
5. Toggle DRAFT_ONLY / SEND mode
6. View system health

**Tech Stack:**
- React 18 + TypeScript
- Vite build tool
- TailwindCSS
- React Query (data management)
- Axios (API client)

**Time Breakdown:**
- Task 5.1: React setup - 0.5 days
- Task 5.2: Layout & navigation - 1 day
- Task 5.3: Workflows pages - 2 days
- Task 5.4: Drafts & approval - 2 days
- Task 5.5: WebSocket (optional) - 1 day
- Task 5.6: Settings & admin - 1.5 days
- Task 5.7: Testing & docs - 1.5 days
- **Total: 9.5 days (1.9 weeks)**

---

# PHASE 6: Reliability & Error Recovery (2 weeks)

**Goal:** Make system resilient with proper error handling, retries, and recovery

**Key Deliverable:** System can recover from failures gracefully with full observability

---

## Phase 6 Sprint Tasks

### Task 6.1: Comprehensive Error Classification

**Objective:** Implement error categorization and handling strategy

**Description:**

Different errors need different responses:
1. **Transient** (retry immediately): Network timeouts, rate limits
2. **Recoverable** (retry with backoff): Temporary API outages
3. **Configuration** (alert ops): Missing API keys
4. **Invalid Input** (fail fast): Bad email format
5. **External Dependency** (dead-letter): HubSpot API not responding

Create error hierarchy and routing system.

**Acceptance Criteria:**
1. ✅ Error base class with categories
2. ✅ Each error type has retry strategy
3. ✅ Retry decision made automatically
4. ✅ Non-retryable errors fail fast
5. ✅ All errors logged with context
6. ✅ Metrics tracked by error type

**Files to Create/Modify:**
- [src/errors.py](src/errors.py) (NEW - 150 lines)
- [src/retry_strategy.py](src/retry_strategy.py) (NEW - 200 lines)

**Error Hierarchy:**

```python
# src/errors.py
class SalesAgentError(Exception):
    """Base error for sales agent."""
    category: str = "unknown"
    retryable: bool = False
    retry_delay: int = 0
    max_retries: int = 0

class TransientError(SalesAgentError):
    """Errors that should be retried immediately."""
    category = "transient"
    retryable = True
    max_retries = 3
    retry_delay = 1

class RecoverableError(SalesAgentError):
    """Errors that should be retried with backoff."""
    category = "recoverable"
    retryable = True
    max_retries = 5
    retry_delay = 5  # exponential backoff applies

class ConfigurationError(SalesAgentError):
    """Configuration errors - alert ops, don't retry."""
    category = "configuration"
    retryable = False

class InvalidInputError(SalesAgentError):
    """Invalid input - fail immediately."""
    category = "invalid_input"
    retryable = False

class ExternalServiceError(SalesAgentError):
    """External service unavailable - dead-letter."""
    category = "external_service"
    retryable = True
    max_retries = 2
    retry_delay = 30

# Specific errors
class GmailConnectionError(TransientError):
    """Gmail connection failed."""
    pass

class HubSpotRateLimitError(RecoverableError):
    """HubSpot rate limit hit."""
    pass

class InvalidEmailError(InvalidInputError):
    """Email validation failed."""
    pass

class MissingAPIKeyError(ConfigurationError):
    """API key not configured."""
    pass
```

**Effort:** 1 day

---

### Task 6.2: Retry Logic & Exponential Backoff

**Objective:** Implement robust retry mechanism with exponential backoff and jitter

**Description:**

Build retry decorator/wrapper that:
1. Retries based on error type
2. Uses exponential backoff (1s, 2s, 4s, 8s...)
3. Adds jitter to prevent thundering herd
4. Tracks retry count and timing
5. Respects max retries
6. Logs each retry attempt

**Acceptance Criteria:**
1. ✅ Decorator `@with_retry` working
2. ✅ Exponential backoff verified (1, 2, 4, 8, 16...)
3. ✅ Jitter added (±20%)
4. ✅ Max retries respected
5. ✅ Non-retryable errors fail immediately
6. ✅ Unit tests verify retry behavior

**Files to Modify:**
- [src/retry_strategy.py](src/retry_strategy.py) (NEW - 300 lines)
- [src/connectors/gmail.py](src/connectors/gmail.py) (add retry decorator)
- [src/connectors/hubspot.py](src/connectors/hubspot.py) (add retry decorator)
- [tests/unit/test_retry.py](tests/unit/test_retry.py) (NEW - 200 lines)

**Retry Decorator:**

```python
# src/retry_strategy.py
import random
import time
from functools import wraps
from typing import Callable, TypeVar

F = TypeVar('F', bound=Callable)

def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: float = 0.2
):
    """Decorator for retry logic with exponential backoff."""
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            last_exception = None
            
            while retries <= max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # Check if error is retryable
                    if hasattr(e, 'retryable') and not e.retryable:
                        raise
                    
                    if retries >= max_retries:
                        logger.error(
                            f"Max retries exceeded for {func.__name__}",
                            retries=retries,
                            error=str(e)
                        )
                        raise
                    
                    last_exception = e
                    
                    # Calculate backoff with jitter
                    delay = min(base_delay * (2 ** retries), max_delay)
                    jitter_amount = delay * jitter * random.uniform(-1, 1)
                    sleep_time = max(0, delay + jitter_amount)
                    
                    logger.warning(
                        f"Retry {retries + 1}/{max_retries} for {func.__name__}",
                        error=str(e),
                        sleep_seconds=sleep_time
                    )
                    
                    await asyncio.sleep(sleep_time)
                    retries += 1
            
            raise last_exception
        
        return wrapper
    return decorator

# Usage
@with_retry(max_retries=3)
async def send_email(...):
    # Will retry on transient errors
    pass
```

**Unit Tests:**

```python
# tests/unit/test_retry.py
async def test_retry_succeeds_on_second_attempt():
    """Verify retry succeeds after initial failure."""
    call_count = 0
    
    @with_retry(max_retries=2, base_delay=0.01)
    async def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise TransientError("Network timeout")
        return "success"
    
    result = await flaky_function()
    assert result == "success"
    assert call_count == 2

async def test_retry_respects_max_retries():
    """Verify max retries enforced."""
    @with_retry(max_retries=2, base_delay=0.01)
    async def always_fails():
        raise TransientError("Network timeout")
    
    with pytest.raises(TransientError):
        await always_fails()

async def test_non_retryable_error_fails_immediately():
    """Non-retryable errors should not retry."""
    call_count = 0
    
    @with_retry(max_retries=2, base_delay=0.01)
    async def invalid_input():
        nonlocal call_count
        call_count += 1
        error = InvalidInputError("Bad email")
        error.retryable = False
        raise error
    
    with pytest.raises(InvalidInputError):
        await invalid_input()
    
    assert call_count == 1  # Only one attempt
```

**Effort:** 1.5 days

---

### Task 6.3: Dead-Letter Queue for Failed Tasks

**Objective:** Implement dead-letter queue to capture permanently failed tasks

**Description:**

Build DLQ system for tasks that exhaust retries:
1. Tasks moved to DLQ table after max retries
2. DLQ items stored with full context
3. Dashboard page to view DLQ
4. Manual retry from UI
5. Export DLQ for analysis

**Acceptance Criteria:**
1. ✅ DLQ table created in database
2. ✅ Failed tasks automatically moved to DLQ
3. ✅ Full error context stored
4. ✅ Can manually retry from UI
5. ✅ Can view/search DLQ
6. ✅ Can export DLQ to CSV

**Files to Create/Modify:**
- [src/models/dlq.py](src/models/dlq.py) (NEW - 100 lines)
- [src/tasks.py](src/tasks.py) (enhance to use DLQ)
- [src/routes/dlq.py](src/routes/dlq.py) (NEW - 150 lines)
- [infra/migrations/versions/002_dlq_table.py](infra/migrations/versions/002_dlq_table.py)
- [frontend/src/pages/DeadLetterQueue.tsx](frontend/src/pages/DeadLetterQueue.tsx) (NEW)

**DLQ Model:**

```python
# src/models/dlq.py
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.db import Base

class DeadLetterItem(Base):
    """Task that permanently failed - moved to DLQ."""
    __tablename__ = "dead_letter_queue"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    task_name = Column(String(255), nullable=False)
    task_args = Column(JSONB, nullable=False)
    error_message = Column(Text, nullable=False)
    error_type = Column(String(255), nullable=False)
    traceback = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    moved_to_dlq_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    manually_retried_at = Column(DateTime, nullable=True)
    manually_retried_count = Column(Integer, default=0)
```

**Effort:** 1.5 days

---

### Task 6.4: Graceful Degradation & Circuit Breaker

**Objective:** Implement circuit breaker to prevent cascading failures

**Description:**

Add circuit breaker pattern to external service calls:
1. Track consecutive failures
2. "Open" circuit after N failures (stop trying)
3. "Half-open" after cooldown (try 1 request)
4. "Closed" after success (resume normal)
5. Alert ops when circuit opens

**Acceptance Criteria:**
1. ✅ Circuit breaker class implemented
2. ✅ Failure threshold configurable
3. ✅ Cooldown period configurable
4. ✅ States working (open/half-open/closed)
5. ✅ Metrics tracked
6. ✅ Alerts sent when circuit opens

**Files to Create/Modify:**
- [src/circuit_breaker.py](src/circuit_breaker.py) (NEW - 200 lines)
- [src/connectors/gmail.py](src/connectors/gmail.py) (wrap calls)
- [src/connectors/hubspot.py](src/connectors/hubspot.py) (wrap calls)
- [tests/unit/test_circuit_breaker.py](tests/unit/test_circuit_breaker.py) (NEW)

**Circuit Breaker Implementation:**

```python
# src/circuit_breaker.py
from datetime import datetime, timedelta
from enum import Enum

class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker for external service calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception(f"Circuit breaker OPEN for {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker recovered - entering CLOSED state")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker OPEN - {self.failure_count} failures",
                recovery_timeout=self.recovery_timeout
            )
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time passed to attempt reset."""
        if not self.last_failure_time:
            return False
        
        cooldown = timedelta(seconds=self.recovery_timeout)
        return datetime.utcnow() - self.last_failure_time > cooldown
```

**Effort:** 1.5 days

---

### Task 6.5: Reconciliation & Repair Jobs

**Objective:** Build jobs to detect and fix inconsistencies

**Description:**

Create background jobs to:
1. Detect orphaned drafts (draft not linked to workflow)
2. Detect orphaned tasks (task not in HubSpot)
3. Detect duplicate submissions (same email, same form, within 5 min)
4. Reconcile with HubSpot (verify tasks exist)
5. Alert ops on anomalies

**Acceptance Criteria:**
1. ✅ Reconciliation job runs daily
2. ✅ Finds orphaned drafts
3. ✅ Detects duplicate submissions
4. ✅ Reconciles with HubSpot
5. ✅ Report generated and stored
6. ✅ Can be triggered manually from UI

**Files to Create:**
- [src/jobs/reconciliation.py](src/jobs/reconciliation.py) (NEW - 300 lines)
- [src/models/reconciliation_report.py](src/models/reconciliation_report.py) (NEW)
- [src/routes/jobs.py](src/routes/jobs.py) (NEW - 100 lines)
- [tests/integration/test_reconciliation.py](tests/integration/test_reconciliation.py) (NEW)

**Reconciliation Job:**

```python
# src/jobs/reconciliation.py
@celery_app.task
def run_reconciliation_job():
    """Nightly reconciliation job."""
    logger.info("Starting reconciliation job")
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "issues_found": [],
        "issues_fixed": 0,
    }
    
    # 1. Check for orphaned drafts
    orphaned_drafts = find_orphaned_drafts()
    if orphaned_drafts:
        report["issues_found"].append({
            "type": "orphaned_drafts",
            "count": len(orphaned_drafts),
            "draft_ids": [d.id for d in orphaned_drafts]
        })
    
    # 2. Check for duplicate submissions
    duplicate_submissions = find_duplicate_submissions()
    if duplicate_submissions:
        report["issues_found"].append({
            "type": "duplicates",
            "count": len(duplicate_submissions),
            "samples": [d.id for d in duplicate_submissions[:5]]
        })
    
    # 3. Reconcile with HubSpot
    reconcile_with_hubspot()
    
    # Store report
    save_reconciliation_report(report)
    
    logger.info(f"Reconciliation complete: {len(report['issues_found'])} issues found")
    return report
```

**Effort:** 1.5 days

---

### Task 6.6: Observability Enhancements

**Objective:** Add comprehensive logging and metrics

**Description:**

Enhance observability for debugging and monitoring:
1. Structured logging (JSON with context)
2. Request tracing (trace_id through all logs)
3. Performance metrics (latency, duration)
4. Error metrics (error types, frequencies)
5. Business metrics (workflows/day, approval rate)

**Acceptance Criteria:**
1. ✅ All logs in JSON format with context
2. ✅ trace_id propagated through entire request
3. ✅ Performance metrics logged
4. ✅ Error rate tracked
5. ✅ Metrics exportable (Prometheus format)
6. ✅ Dashboard shows key metrics

**Files to Modify:**
- [src/logger.py](src/logger.py) (enhance - add metrics)
- [src/middleware.py](src/middleware.py) (add timing/tracing)
- [src/metrics.py](src/metrics.py) (NEW - 200 lines)

**Structured Logging:**

```python
# src/logger.py - Enhance logging
import json
from pythonjsonlogger import jsonlogger

def configure_logging(log_level: str, log_format: str):
    """Configure structured logging."""
    logger = logging.getLogger()
    
    if log_format == "json":
        # Use JSON formatter
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level"
            }
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    logger.setLevel(getattr(logging, log_level.upper()))

# Usage in code
logger.info(
    "Workflow completed",
    workflow_id=workflow.id,
    prospect_email=prospect.email,
    duration_seconds=elapsed,
    steps_completed=11,
    trace_id=request.state.trace_id
)
```

**Metrics:**

```python
# src/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Counters
workflow_created = Counter(
    'workflows_created_total',
    'Total workflows created'
)
workflow_completed = Counter(
    'workflows_completed_total',
    'Total workflows completed'
)
workflow_failed = Counter(
    'workflows_failed_total',
    'Total workflows failed'
)
draft_approved = Counter(
    'drafts_approved_total',
    'Total drafts approved'
)

# Histograms
workflow_duration = Histogram(
    'workflow_duration_seconds',
    'Workflow execution duration'
)
step_duration = Histogram(
    'workflow_step_duration_seconds',
    'Duration of individual workflow step',
    labelnames=['step_name']
)

# Gauges
active_workflows = Gauge(
    'active_workflows',
    'Number of workflows currently processing'
)
```

**Effort:** 1 day

---

### Task 6.7: Phase 6 Testing & Validation

**Objective:** Test all reliability features

**Description:**

Comprehensive testing of error handling, retries, and recovery.

**Acceptance Criteria:**
1. ✅ Retry logic tested
2. ✅ Circuit breaker tested
3. ✅ DLQ working
4. ✅ Reconciliation job passing
5. ✅ Error scenarios covered

**Files to Create:**
- [tests/integration/test_phase6_reliability.py](tests/integration/test_phase6_reliability.py) (NEW)

**Effort:** 1 day

---

## Phase 6 Summary

**What Gets Built:**
- ✅ Error classification and handling
- ✅ Retry logic with exponential backoff
- ✅ Dead-letter queue for failed tasks
- ✅ Circuit breaker for service calls
- ✅ Reconciliation jobs
- ✅ Enhanced observability and metrics

**What Gets Demoed:**
1. Failed workflow auto-retries
2. Circuit breaker opens/closes properly
3. DLQ captures permanently failed tasks
4. Manual retry from UI works
5. Reconciliation job finds issues
6. Metrics and logs in dashboard

**Time Breakdown:**
- Task 6.1: Error classification - 1 day
- Task 6.2: Retry logic - 1.5 days
- Task 6.3: DLQ - 1.5 days
- Task 6.4: Circuit breaker - 1.5 days
- Task 6.5: Reconciliation - 1.5 days
- Task 6.6: Observability - 1 day
- Task 6.7: Testing - 1 day
- **Total: 9 days (1.8 weeks)**

---

# PHASE 7: Async Processing & Scaling (2 weeks)

**Goal:** Enable high-volume processing with Celery workers and load balancing

**Key Deliverable:** System can handle 100+ workflows/day with proper queuing and worker management

---

## Phase 7 Sprint Tasks

### Task 7.1: Multi-Queue Architecture

**Objective:** Implement multi-queue system for prioritization

**Description:**

Create queue hierarchy:
1. **Priority Queue** (high-value customers, urgent workflows)
2. **Normal Queue** (standard submissions)
3. **Batch Queue** (bulk imports, campaigns)
4. **Cleanup Queue** (reconciliation, maintenance)

Workers assigned to each queue proportionally.

**Acceptance Criteria:**
1. ✅ Queue routing logic working
2. ✅ Can mark submission as priority
3. ✅ Workers balanced across queues
4. ✅ Metrics show queue depths
5. ✅ Dashboard shows queue status

**Files to Create/Modify:**
- [src/queue_router.py](src/queue_router.py) (NEW - 150 lines)
- [src/tasks.py](src/tasks.py) (enhance)
- [src/celery_app.py](src/celery_app.py) (enhance)

**Queue Routing:**

```python
# src/queue_router.py
class QueueRouter:
    """Route tasks to appropriate queue."""
    
    PRIORITY_CUSTOMERS = ["acme.com", "techcorp.io"]  # Configurable
    
    def route_workflow(self, form_submission) -> str:
        """Determine which queue task should go to."""
        prospect_email = form_submission.prospect_email
        domain = prospect_email.split("@")[1]
        
        if domain in self.PRIORITY_CUSTOMERS:
            return "priority_queue"
        
        if form_submission.tags.contains("bulk_import"):
            return "batch_queue"
        
        return "normal_queue"

# Usage in webhook
queue = queue_router.route_workflow(form_submission)
process_workflow_task.apply_async(
    args=(form_submission.id,),
    queue=queue
)
```

**Effort:** 1 day

---

### Task 7.2: Celery Worker Pool & Auto-Scaling

**Objective:** Implement worker pool with monitoring and auto-scaling hooks

**Description:**

1. Multiple worker processes (pool of workers)
2. Health monitoring for each worker
3. Auto-restart failed workers
4. Graceful shutdown on deploy
5. Scaling recommendations based on queue depth

**Acceptance Criteria:**
1. ✅ 4+ worker processes running
2. ✅ Worker health monitored
3. ✅ Dead workers auto-restarted
4. ✅ Graceful shutdown working
5. ✅ docker-compose scales workers

**Files to Modify:**
- [docker-compose.yml](docker-compose.yml) (add worker scaling)
- [infra/worker-supervisor.py](infra/worker-supervisor.py) (NEW)
- [src/celery_app.py](src/celery_app.py) (enhance)

**docker-compose.yml Scaling:**

```yaml
services:
  celery_worker:
    build: .
    command: celery -A src.celery_app worker --loglevel=info --concurrency=4
    deploy:
      replicas: 3  # Scale horizontally
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - redis
      - postgres
      - celery_flower  # Monitor workers

  celery_flower:
    image: mher/flower:2.0
    command: celery --broker=redis://redis:6379/1 flower --port=5555
    ports:
      - "5555:5555"
```

**Effort:** 1.5 days

---

### Task 7.3: Load Testing & Performance Tuning

**Objective:** Test system under load and optimize

**Description:**

1. Simulate 100+ concurrent form submissions
2. Measure throughput (workflows/second)
3. Measure latency (p50, p95, p99)
4. Identify bottlenecks
5. Tune database, redis, celery
6. Document performance characteristics

**Acceptance Criteria:**
1. ✅ Can process 100+ workflows/day
2. ✅ Average latency < 5 seconds
3. ✅ P95 latency < 15 seconds
4. ✅ P99 latency < 30 seconds
5. ✅ No database connection exhaustion
6. ✅ Workers don't get stuck

**Files to Create:**
- [tests/performance/load_test.py](tests/performance/load_test.py) (NEW - 300 lines)
- [docs/PERFORMANCE_TUNING.md](docs/PERFORMANCE_TUNING.md) (NEW)

**Load Test:**

```python
# tests/performance/load_test.py
import asyncio
from locust import HttpUser, task, between

class WorkflowLoadTest(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def create_workflow(self):
        """Simulate form submission."""
        payload = create_mock_webhook()
        self.client.post(
            "/api/webhooks/hubspot/forms",
            json=payload,
            headers={"X-HubSpot-Signature": compute_signature(payload)}
        )
    
    @task
    def list_workflows(self):
        """List workflows."""
        self.client.get("/api/workflows?limit=20")
    
    @task
    def get_metrics(self):
        """Get system metrics."""
        self.client.get("/metrics")

# Run: locust -f tests/performance/load_test.py --host=http://localhost:8000
```

**Performance Targets:**
- Throughput: 10+ workflows/second
- P50 latency: 2 seconds
- P95 latency: 10 seconds
- P99 latency: 25 seconds
- CPU: < 80%
- Memory: < 2GB

**Effort:** 1.5 days

---

### Task 7.4: Bulk Import API

**Objective:** Add API for bulk importing form submissions

**Description:**

Enable importing historical submissions or bulk campaigns:
1. `POST /api/imports` - Upload CSV of submissions
2. Routes to batch_queue
3. Processes asynchronously
4. Returns import ID for tracking
5. Dashboard shows import progress

**Acceptance Criteria:**
1. ✅ CSV upload endpoint working
2. ✅ Validation of CSV format
3. ✅ Bulk submissions queued to batch_queue
4. ✅ Import progress trackable
5. ✅ Can pause/cancel import
6. ✅ Error reporting per row

**Files to Create/Modify:**
- [src/routes/imports.py](src/routes/imports.py) (NEW - 200 lines)
- [src/models/import_job.py](src/models/import_job.py) (NEW)
- [src/tasks.py](src/tasks.py) (add bulk processing task)
- [frontend/src/pages/Imports.tsx](frontend/src/pages/Imports.tsx) (NEW)

**Import API:**

```python
# src/routes/imports.py
@router.post("/imports", tags=["Imports"])
async def create_import(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    Upload CSV of form submissions for bulk processing.
    
    CSV format:
    email,firstName,lastName,company,formId
    john@acme.com,John,Smith,ACME Corp,form-123
    """
    import_id = str(uuid4())
    
    try:
        # Parse CSV
        content = await file.read()
        submissions = parse_csv(content)
        
        # Create import job
        import_job = ImportJob(
            id=import_id,
            filename=file.filename,
            total_rows=len(submissions),
            status="pending"
        )
        session.add(import_job)
        await session.commit()
        
        # Queue processing
        for idx, submission in enumerate(submissions):
            process_import_row.apply_async(
                args=(import_id, idx, submission),
                queue="batch_queue"
            )
        
        logger.info(f"Import {import_id} created with {len(submissions)} rows")
        return {
            "import_id": import_id,
            "rows": len(submissions),
            "status": "processing"
        }
    
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
```

**Effort:** 1.5 days

---

### Task 7.5: Worker Monitoring Dashboard

**Objective:** Dashboard page to monitor worker health and queue status

**Description:**

Add dashboard showing:
1. Worker count and status
2. Queue depths by queue type
3. Task success/failure rates
4. Average processing time per task
5. Historical throughput

**Acceptance Criteria:**
1. ✅ Worker status displayed
2. ✅ Queue depths real-time
3. ✅ Success/failure metrics
4. ✅ Throughput graph
5. ✅ Can manually scale workers (if using Docker)

**Files to Create:**
- [frontend/src/pages/Workers.tsx](frontend/src/pages/Workers.tsx) (NEW - 300 lines)
- [src/routes/workers.py](src/routes/workers.py) (NEW - 150 lines)

**Worker Status API:**

```python
# src/routes/workers.py
@router.get("/workers", tags=["Workers"])
async def get_worker_status() -> Dict[str, Any]:
    """Get worker pool status."""
    from celery import Celery
    from src.celery_app import celery_app
    
    stats = celery_app.control.inspect().stats()
    active = celery_app.control.inspect().active()
    
    return {
        "workers": len(stats or {}),
        "active_tasks": sum(len(tasks) for tasks in (active or {}).values()),
        "worker_details": [
            {
                "name": name,
                "pool": stats[name].get("pool", {}).get("implementation"),
                "max_concurrency": stats[name].get("pool", {}).get("max-concurrency", 4),
                "active_tasks": len(active.get(name, []))
            }
            for name in (stats or {}).keys()
        ]
    }

@router.get("/queues", tags=["Workers"])
async def get_queue_status() -> Dict[str, Any]:
    """Get queue depths."""
    redis_client = get_redis_client()
    
    queues = ["priority_queue", "normal_queue", "batch_queue", "cleanup_queue"]
    
    return {
        "queues": [
            {
                "name": queue,
                "depth": redis_client.llen(queue),
                "priority": queue == "priority_queue"
            }
            for queue in queues
        ]
    }
```

**Effort:** 1.5 days

---

### Task 7.6: Database Query Optimization

**Objective:** Optimize database queries for high volume

**Description:**

1. Index key columns for queries
2. Batch operations where possible
3. Connection pooling tuned
4. Query analysis and optimization
5. Monitor slow queries

**Acceptance Criteria:**
1. ✅ All indexes in place
2. ✅ N+1 query problems fixed
3. ✅ Batch inserts used
4. ✅ Connection pool optimized
5. ✅ Query execution times logged
6. ✅ Slow query alerts configured

**Files to Modify:**
- [src/models/](src/models/) (add indexes)
- [src/db.py](src/db.py) (tune connection pool)
- [infra/migrations/](infra/migrations/) (add indexes)

**Indexing Strategy:**

```python
# src/models/workflow.py - Add comprehensive indexes
class Workflow(Base):
    __tablename__ = "workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    form_submission_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    
    __table_args__ = (
        Index("idx_workflows_status", status),
        Index("idx_workflows_created_at", created_at.desc()),
        Index("idx_workflows_form_submission_id", form_submission_id),
        Index("idx_workflows_status_created", status, created_at.desc()),  # Composite
    )
```

**Effort:** 1 day

---

### Task 7.7: Phase 7 Testing & Load Validation

**Objective:** Complete testing and validation

**Description:**

Full load testing, performance validation, and production readiness.

**Acceptance Criteria:**
1. ✅ Load test passes (100+ workflows)
2. ✅ Performance targets met
3. ✅ Workers scale properly
4. ✅ No memory leaks
5. ✅ Database performant
6. ✅ Ready for production scaling

**Files to Create:**
- [tests/performance/test_phase7_scaling.py](tests/performance/test_phase7_scaling.py) (NEW)

**Effort:** 1 day

---

## Phase 7 Summary

**What Gets Built:**
- ✅ Multi-queue architecture with priority routing
- ✅ Worker pool with auto-scaling support
- ✅ Performance testing framework
- ✅ Bulk import API
- ✅ Worker monitoring dashboard
- ✅ Database query optimization

**What Gets Demoed:**
1. Import 100 workflows from CSV
2. Monitor workers processing in parallel
3. Queue depths shown in real-time
4. Load test shows 100+ workflows/day capacity
5. Performance metrics within targets

**Performance Targets Achieved:**
- ✅ 100+ workflows/day
- ✅ 10+ workflows/second
- ✅ P95 latency < 15 seconds
- ✅ Workers scale horizontally

**Time Breakdown:**
- Task 7.1: Multi-queue - 1 day
- Task 7.2: Worker pool - 1.5 days
- Task 7.3: Load testing - 1.5 days
- Task 7.4: Bulk import - 1.5 days
- Task 7.5: Worker dashboard - 1.5 days
- Task 7.6: DB optimization - 1 day
- Task 7.7: Testing - 1 day
- **Total: 9 days (1.8 weeks)**

---

# PHASE 8: Advanced Observability (1.5 weeks)

**Goal:** Production-grade monitoring, alerting, and troubleshooting

**Key Deliverable:** Complete visibility into system health with proactive alerts

---

## Phase 8 Sprint Tasks

### Task 8.1: Prometheus Metrics Export

**Objective:** Export all metrics in Prometheus format

**Description:**

Expose metrics at `/metrics` endpoint for Prometheus scraping:
- Request count/duration
- Task completion/failure rates
- Database connection pool
- Redis queue depths
- Error rates by type
- Custom business metrics

**Acceptance Criteria:**
1. ✅ `/metrics` endpoint returns Prometheus-compatible output
2. ✅ All key metrics exported
3. ✅ Metrics updated in real-time
4. ✅ Can be scraped by Prometheus
5. ✅ cardinality limits enforced (not thousands of metrics)

**Files to Modify:**
- [src/metrics.py](src/metrics.py) (enhance)
- [src/main.py](src/main.py) (add /metrics endpoint)
- [docker-compose.yml](docker-compose.yml) (add Prometheus service)

**Effort:** 1 day

---

### Task 8.2: Grafana Dashboards

**Objective:** Create operational dashboards in Grafana

**Description:**

Build dashboards for:
1. **System Health** - CPU, memory, uptime
2. **Workflow Metrics** - throughput, success rate, latency
3. **Queue Status** - depths, worker utilization
4. **Error Analysis** - error types, trends
5. **Business Metrics** - workflows/day, prospects contacted

**Acceptance Criteria:**
1. ✅ 5 dashboards created
2. ✅ Auto-refresh working
3. ✅ Alerts configured
4. ✅ Drilldown into details
5. ✅ Mobile-friendly

**Files to Create:**
- [infra/grafana/dashboards/](infra/grafana/dashboards/) (NEW - JSON dashboards)
- [docker-compose.yml](docker-compose.yml) (add Grafana service)

**Effort:** 1.5 days

---

### Task 8.3: Alerting Rules & PagerDuty Integration

**Objective:** Configure alerts for production issues

**Description:**

Set up alert rules for:
1. High error rate (> 5%)
2. Long queue depths (> 100 pending)
3. Worker down
4. Database connection pool exhausted
5. Slow queries (> 5 seconds)
6. Memory usage > 80%

Send alerts to PagerDuty (or Slack for dev).

**Acceptance Criteria:**
1. ✅ Alert rules configured in Prometheus
2. ✅ Alerts route to PagerDuty
3. ✅ Escalation policies set
4. ✅ Test alert working
5. ✅ Documentation on runbooks

**Files to Create:**
- [infra/prometheus/alerts.yml](infra/prometheus/alerts.yml) (NEW)
- [docs/RUNBOOK.md](docs/RUNBOOK.md) (NEW - debugging guide)
- [infra/alertmanager/config.yml](infra/alertmanager/config.yml) (NEW)

**Effort:** 1 day

---

### Task 8.4: Distributed Tracing (Jaeger)

**Objective:** Implement distributed tracing for request flow

**Description:**

Add OpenTelemetry instrumentation:
1. Trace requests from webhook → task → result
2. Span for each workflow step
3. Export traces to Jaeger
4. View complete request flow

**Acceptance Criteria:**
1. ✅ OpenTelemetry middleware added
2. ✅ Traces exported to Jaeger
3. ✅ Can view request waterfall
4. ✅ Step durations visible
5. ✅ Errors show in trace

**Files to Create:**
- [src/tracing.py](src/tracing.py) (NEW - 150 lines)
- [docker-compose.yml](docker-compose.yml) (add Jaeger)

**Effort:** 1 day

---

### Task 8.5: Log Aggregation (ELK or Loki)

**Objective:** Centralized log aggregation and search

**Description:**

Aggregate logs from all services:
1. API server logs
2. Worker logs
3. Database logs
4. Search and filter UI
5. Alert on log patterns

Using either:
- ELK Stack (Elasticsearch, Logstash, Kibana) - heavier
- Loki (Grafana's lightweight log aggregation) - simpler

**Acceptance Criteria:**
1. ✅ Logs shipped from all services
2. ✅ Searchable dashboard
3. ✅ Can filter by service/level/trace_id
4. ✅ Performance acceptable
5. ✅ Retention policy set (30 days)

**Files to Create:**
- [docker-compose.yml](docker-compose.yml) (add Loki service)
- [infra/loki/config.yml](infra/loki/config.yml) (NEW)

**Effort:** 1.5 days

---

### Task 8.6: Synthetic Monitoring

**Objective:** Proactive monitoring with synthetic tests

**Description:**

Run synthetic checks to catch issues before users:
1. Webhook receiver health check
2. API endpoints health check
3. Database connectivity
4. External service connectivity
5. End-to-end workflow test every 5 minutes

Alert if checks fail.

**Acceptance Criteria:**
1. ✅ Synthetic tests running
2. ✅ Health checks pass
3. ✅ Alerts on failure
4. ✅ Results dashboard
5. ✅ SLA calculated (99.9%)

**Files to Create:**
- [tests/synthetic/](tests/synthetic/) (NEW directory)
- [tests/synthetic/health_check.py](tests/synthetic/health_check.py) (NEW)
- [tests/synthetic/workflow_test.py](tests/synthetic/workflow_test.py) (NEW)

**Effort:** 1 day

---

### Task 8.7: Phase 8 Validation

**Objective:** Test all observability features

**Description:**

Validate monitoring, alerting, tracing all working properly.

**Acceptance Criteria:**
1. ✅ Metrics displayed in Grafana
2. ✅ Alerts fire correctly
3. ✅ Traces visible in Jaeger
4. ✅ Logs searchable
5. ✅ Synthetic tests passing

**Effort:** 0.5 days

---

## Phase 8 Summary

**What Gets Built:**
- ✅ Prometheus metrics export
- ✅ Grafana operational dashboards
- ✅ Prometheus alerting rules
- ✅ PagerDuty integration
- ✅ Jaeger distributed tracing
- ✅ Loki log aggregation
- ✅ Synthetic monitoring

**What Gets Demoed:**
1. Grafana dashboard shows live metrics
2. Alert fires and escalates to PagerDuty
3. Trace shows complete request flow
4. Logs searched and correlated by trace_id
5. Synthetic health check passes

**Observability Stack:**
- Prometheus (metrics)
- Grafana (dashboards)
- Jaeger (distributed tracing)
- Loki (log aggregation)
- PagerDuty (alerting)

**Time Breakdown:**
- Task 8.1: Prometheus - 1 day
- Task 8.2: Grafana - 1.5 days
- Task 8.3: Alerting - 1 day
- Task 8.4: Jaeger - 1 day
- Task 8.5: Loki - 1.5 days
- Task 8.6: Synthetic - 1 day
- Task 8.7: Validation - 0.5 days
- **Total: 7.5 days (1.5 weeks)**

---

# PHASE 9: Multi-tenancy & Final Production Prep (2 weeks)

**Goal:** Multi-account support and final production readiness

**Key Deliverable:** Production-grade system ready for enterprise deployment

---

## Phase 9 Sprint Tasks

### Task 9.1: Multi-tenancy Architecture

**Objective:** Design and implement multi-tenant data isolation

**Description:**

Currently single-tenant. Add multi-tenant support:
1. Tenant model in database
2. Row-level security (RLS) policies
3. Data isolation by tenant
4. Tenant-specific configuration
5. Billing/metering per tenant

**Acceptance Criteria:**
1. ✅ Tenant model created
2. ✅ RLS policies enforced
3. ✅ Tenant ID in all queries
4. ✅ Cannot see other tenant's data
5. ✅ Configuration per tenant
6. ✅ Tests verify isolation

**Files to Create/Modify:**
- [src/models/tenant.py](src/models/tenant.py) (NEW)
- [src/middleware.py](src/middleware.py) (enhance - extract tenant)
- [src/deps.py](src/deps.py) (enhance - add tenant to deps)
- [infra/migrations/versions/003_add_tenancy.py](infra/migrations/versions/003_add_tenancy.py)

**Tenant Model:**

```python
# src/models/tenant.py
class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(255), nullable=False, unique=True)
    api_key = Column(String(255), nullable=False, unique=True)
    
    # Configuration
    max_workflows_per_day = Column(Integer, default=1000)
    draft_only_mode = Column(Boolean, default=True)
    approval_required = Column(Boolean, default=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String(255), nullable=False)
    
    # Relationships
    workflows = relationship("Workflow", back_populates="tenant")
    api_keys = relationship("TenantAPIKey", back_populates="tenant")
```

**Effort:** 2 days

---

### Task 9.2: API Key & Authentication

**Objective:** Implement API key authentication for multi-tenant access

**Description:**

1. Generate unique API keys per tenant
2. Key rotation mechanism
3. Rate limiting per key
4. Access audit trail
5. Webhook secret per tenant

**Acceptance Criteria:**
1. ✅ Can generate API keys
2. ✅ API requests verified with key
3. ✅ Key rate limits enforced
4. ✅ Key access logged
5. ✅ Can revoke keys
6. ✅ Webhook secret per tenant

**Files to Create/Modify:**
- [src/models/tenant_apikey.py](src/models/tenant_apikey.py) (NEW)
- [src/auth/apikey.py](src/auth/apikey.py) (NEW - 150 lines)
- [src/routes/auth.py](src/routes/auth.py) (NEW - 200 lines)

**Effort:** 1.5 days

---

### Task 9.3: Billing & Metering

**Objective:** Implement usage tracking for billing

**Description:**

Track per-tenant:
1. Workflows processed
2. Emails sent
3. HubSpot tasks created
4. API calls made
5. Storage used

Store metering data for billing.

**Acceptance Criteria:**
1. ✅ Usage tracked per tenant
2. ✅ Metering data stored
3. ✅ Usage visible in dashboard
4. ✅ Can query usage by date range
5. ✅ Can export for billing

**Files to Create:**
- [src/models/metering.py](src/models/metering.py) (NEW)
- [src/metering.py](src/metering.py) (NEW - 150 lines)
- [frontend/src/pages/Billing.tsx](frontend/src/pages/Billing.tsx) (NEW)

**Effort:** 1.5 days

---

### Task 9.4: Security Hardening

**Objective:** Final security review and hardening

**Description:**

1. CORS validation
2. Input validation & sanitization
3. Rate limiting tuning
4. HTTPS enforcement
5. Security headers
6. Dependency vulnerability scan
7. SQL injection prevention
8. XSS prevention

**Acceptance Criteria:**
1. ✅ All security headers present
2. ✅ No known vulnerabilities
3. ✅ Input validation comprehensive
4. ✅ Rate limits appropriate
5. ✅ HTTPS configured
6. ✅ Penetration test pass (if available)
7. ✅ Security audit completed

**Files to Modify:**
- [src/main.py](src/main.py) (add security headers)
- [src/middleware.py](src/middleware.py) (enhance)
- [docker-compose.yml](docker-compose.yml) (add reverse proxy)

**Security Headers:**

```python
# src/main.py
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware

# ... existing middleware ...

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

**Effort:** 1.5 days

---

### Task 9.5: Documentation & Runbooks

**Objective:** Complete documentation for operations team

**Description:**

Document:
1. API documentation (OpenAPI/Swagger)
2. Deployment guide
3. Operations runbook
4. Troubleshooting guide
5. Scaling guide
6. Disaster recovery procedure
7. Architecture decisions (ADRs)

**Acceptance Criteria:**
1. ✅ OpenAPI docs at /docs
2. ✅ Deployment guide step-by-step
3. ✅ Runbooks for 10 common issues
4. ✅ Scaling procedures documented
5. ✅ DR plan documented
6. ✅ Training completed

**Files to Create:**
- [docs/API.md](docs/API.md) (NEW - generated from OpenAPI)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) (NEW - enhanced)
- [docs/RUNBOOK.md](docs/RUNBOOK.md) (enhanced)
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) (NEW)
- [docs/SCALING.md](docs/SCALING.md) (NEW)
- [docs/DISASTER_RECOVERY.md](docs/DISASTER_RECOVERY.md) (NEW)
- [docs/ARCHITECTURE_DECISIONS.md](docs/ARCHITECTURE_DECISIONS.md) (NEW)

**Effort:** 1.5 days

---

### Task 9.6: Production Deployment

**Objective:** Deploy to production environment

**Description:**

1. Provision infrastructure (EC2/ECS or similar)
2. Configure DNS
3. Set up SSL/TLS certificates
4. Deploy containers
5. Run health checks
6. Verify all endpoints
7. Monitor for issues

**Acceptance Criteria:**
1. ✅ System deployed to production
2. ✅ Health checks passing
3. ✅ API responding
4. ✅ Webhooks receiving
5. ✅ Workflows processing
6. ✅ Monitoring/alerting active
7. ✅ Logs flowing to aggregation

**Files to Create:**
- [infra/terraform/](infra/terraform/) (Infrastructure as Code)
- [docs/PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md) (NEW)

**Effort:** 2 days

---

### Task 9.7: Load Testing & Performance Validation

**Objective:** Final performance validation before production

**Description:**

Run production load tests:
1. 500+ concurrent workflows
2. Measure throughput, latency
3. Verify no issues under load
4. Database performance acceptable
5. Worker scaling works
6. No memory leaks

**Acceptance Criteria:**
1. ✅ Handles 500+ workflows
2. ✅ P99 latency < 30 seconds
3. ✅ No crashes or errors
4. ✅ Memory stable
5. ✅ Database responsive
6. ✅ Workers scale properly

**Effort:** 1 day

---

### Task 9.8: Cutover & Go-Live

**Objective:** Smooth transition to production

**Description:**

1. Final testing checklist
2. Operator training
3. Cutover plan
4. Rollback plan
5. Run cutover
6. Monitor for issues
7. Gradual ramp-up

**Acceptance Criteria:**
1. ✅ Pre-cutover checklist 100% complete
2. ✅ Team trained
3. ✅ Cutover successful
4. ✅ System stable for 24 hours
5. ✅ Team confident
6. ✅ Celebration! 🎉

**Files to Create:**
- [docs/CUTOVER_CHECKLIST.md](docs/CUTOVER_CHECKLIST.md) (NEW)
- [docs/ROLLBACK_PLAN.md](docs/ROLLBACK_PLAN.md) (NEW)

**Pre-Cutover Checklist:**

```markdown
# Production Cutover Checklist

## Infrastructure
- [ ] Production database provisioned and backed up
- [ ] Redis cluster configured with replication
- [ ] Load balancer configured
- [ ] SSL certificates installed
- [ ] DNS pointing to production load balancer
- [ ] Monitoring and alerting configured
- [ ] Log aggregation working

## Application
- [ ] All tests passing (unit, integration, E2E)
- [ ] Load test passed (500+ workflows)
- [ ] Security audit completed
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] API keys generated for production tenants
- [ ] Webhook secrets generated

## Operations
- [ ] Runbooks prepared
- [ ] Team trained on system
- [ ] Escalation procedures defined
- [ ] On-call rotation set up
- [ ] War room setup for cutover
- [ ] Communication plan ready
- [ ] Rollback plan documented

## Go/No-Go Decision
- [ ] Architecture review: GO / NO-GO
- [ ] Security review: GO / NO-GO
- [ ] Operations review: GO / NO-GO
- [ ] Final: GO / NO-GO → Proceed to cutover
```

**Effort:** 1.5 days

---

## Phase 9 Summary

**What Gets Built:**
- ✅ Multi-tenant architecture
- ✅ API key authentication
- ✅ Usage metering for billing
- ✅ Security hardening
- ✅ Comprehensive documentation
- ✅ Production infrastructure
- ✅ Tested and validated

**What Gets Demoed:**
1. Create new tenant, get API key
2. Tenant isolation verified
3. Usage metering showing in dashboard
4. Production system handling load
5. Team trained and ready
6. System live and stable ✨

**Enterprise-Ready Features:**
- ✅ Multi-tenancy
- ✅ API authentication
- ✅ Billing/metering
- ✅ Security hardened
- ✅ Production monitoring
- ✅ Documented
- ✅ Tested

**Time Breakdown:**
- Task 9.1: Multi-tenancy - 2 days
- Task 9.2: API auth - 1.5 days
- Task 9.3: Billing - 1.5 days
- Task 9.4: Security - 1.5 days
- Task 9.5: Documentation - 1.5 days
- Task 9.6: Deployment - 2 days
- Task 9.7: Load testing - 1 day
- Task 9.8: Cutover - 1.5 days
- **Total: 12.5 days (2.5 weeks)**

---

# Summary & Key Metrics

## Overall Roadmap Statistics

| Metric | Value |
|--------|-------|
| **Total Phases** | 6 (Phase 4-9) |
| **Total Sprints** | 36-40 tasks |
| **Estimated Duration** | 11.5 weeks (2-3 months) |
| **Lines of Code** | ~5,000 new |
| **Test Coverage** | 80%+ |
| **Documentation Pages** | 15+ |
| **Team Size** | 2-3 engineers |

## Phased Delivery

```
Week 1-2:  Phase 4 ✅ Production Enablement
           (DRAFT_ONLY toggle, webhooks, async processing)
           
Week 3-4:  Phase 5 ✅ Operations UI
           (Dashboard, workflow tracking, draft approval)
           
Week 5-6:  Phase 6 ✅ Reliability
           (Error handling, retries, DLQ, circuit breakers)
           
Week 7-8:  Phase 7 ✅ Scaling
           (Multi-queue, load testing, bulk imports)
           
Week 9:    Phase 8 ✅ Observability
           (Metrics, tracing, alerting)
           
Week 10-11: Phase 9 ✅ Multi-tenancy & Go-Live
            (API keys, billing, security, deployment)
```

## Key Architectural Improvements

### Current (Phase 3)
```
CLI Only
     ↓
Form (mocked) → Orchestrator → Draft (DRAFT_ONLY) → Log
     ↓
No persistence, no UI, no async, no webhooks
```

### Final (Phase 9)
```
Multi-tenant with webhook receiver
         ↓
Form Webhook → Validation → Queue → Workers (4+) → Database
         ↓                                              ↓
    Tenant isolation                          Complete audit trail
    API key auth                              Multi-queue routing
         ↓
    Dashboard UI ← Metrics/Tracing ← Worker Pool
         ↓
    Production deployment (ECS/K8s)
    Multi-region ready
    99.9% SLA capable
```

## Critical Success Factors

1. **Test as you build** - Every task must have tests
2. **Database first** - Persistence is foundation for everything else
3. **Async early** - Enables scaling and reliability
4. **Observability throughout** - Logging, metrics, tracing from start
5. **Security hardening** - Don't retrofit, build in from start
6. **Documentation parallel** - Write docs as you code

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Database schema not extensible | Review schema design before implementation |
| Performance degradation under load | Load test frequently, early in timeline |
| Celery/async complexity | Start simple, add features incrementally |
| Multi-tenancy retrofitted badly | Design upfront, implement early (Phase 9.1) |
| Security holes found late | Security audit mid-way (Phase 8), not end |
| Team context loss | Extensive documentation, pair programming |

## Success Metrics

After Phase 9, system should achieve:

| Metric | Target | Verification |
|--------|--------|-------------|
| Webhook uptime | 99.9% | Synthetic monitoring |
| Workflow latency (P95) | < 15 sec | Load tests |
| Throughput | 100+ workflows/day | Load tests |
| Error rate | < 1% | Dashboard metrics |
| MTTR (mean time to recovery) | < 5 min | Incident records |
| Test coverage | 80%+ | Coverage reports |
| Observability | 100% of requests traced | Jaeger UI |
| Security audit | Pass | Third-party audit |
| Ops team readiness | Full training | Training completion |

---

# Analysis & Improvement Suggestions

## Gaps You Might Have Missed

### 1. **Blast Radius Limiting**
   - What if a workflow crashes and takes down all workers?
   - **Mitigation:** Add per-task memory limits, task timeouts, graceful shutdown
   - **Task:** Add to Phase 6 or 7

### 2. **Webhook Deduplication**
   - HubSpot may send same webhook twice (at-least-once delivery)
   - **Mitigation:** Deduplicate by form_submission_id, idempotency keys
   - **Task:** Already in Task 4.3 but emphasize

### 3. **Data Retention & GDPR**
   - How long to keep prospect data? GDPR compliance?
   - **Mitigation:** Add data retention policy, deletion jobs
   - **Task:** Add new task in Phase 9

### 4. **Performance Under Draft Review Delays**
   - If ops take 24 hours to review drafts, queue grows
   - **Mitigation:** Auto-approve after timeout? Escalate manually?
   - **Task:** Add approval workflow tuning task

### 5. **Webhook Validation Rigor**
   - Currently checking form_id allowlist, but is this robust enough?
   - **Mitigation:** Add request signing validation, timestamp checking
   - **Task:** Enhance Task 4.3

### 6. **Workflow Resumption After Failure**
   - If workflow fails at step 8/13, do we retry from step 1 or step 8?
   - **Mitigation:** Implement step-level retry, not just full-workflow
   - **Task:** Add to Phase 6 error handling

### 7. **Customer Communication During Issues**
   - If processing fails, how do prospects get notified?
   - **Mitigation:** Alert workflow + notification task
   - **Task:** Add to Phase 6 or later

### 8. **Rate Limiting Bypass**
   - Is per-contact rate limiting enforced on HubSpot side too?
   - **Mitigation:** Log all rate limit hits, coordinate with HubSpot
   - **Task:** Enhance config validation

### 9. **Integration Test Data Management**
   - How to manage test accounts/contacts across environments?
   - **Mitigation:** Dedicated test tenant, seeded data, cleanup jobs
   - **Task:** Add test data management task

### 10. **Rollback Strategy for Schema Changes**
   - If migration fails in production, how to rollback?
   - **Mitigation:** Reversible migrations, shadow tables, dual-write
   - **Task:** Enhance migration strategy in Phase 9

---

## Suggested Task Reordering

Consider adjusting order if:

1. **Your team prefers UI-first**: Move Phase 5 earlier (after Phase 4.1)
   - Pro: Get visibility early, ops feedback sooner
   - Con: Backend may not be stable yet

2. **You want multi-tenancy early**: Move Phase 9.1-9.2 to after Phase 4
   - Pro: Build with tenancy from start (cleaner)
   - Con: More complex early on

3. **You need security audit first**: Do security hardening (Phase 9.4) before Phase 4
   - Pro: No rework needed
   - Con: Delays getting to production

**Recommended order (as documented) is solid for**: Single-tenant → multi-tenant progression, early integration testing, UI after core backend stable.

---

## Tech Stack Enhancements to Consider

1. **Message Broker Alternatives**
   - Redis (current for Celery) ✅ Good
   - RabbitMQ - More robust, better durability
   - Apache Kafka - Overkill for now, but consider if scaling to 1000+ workflows/day

2. **Database Scaling**
   - PostgreSQL replicas for read scale (Phase 9)
   - Connection pooling (PgBouncer) at Phase 7

3. **Caching Layer**
   - Redis for contact cache, thread cache
   - Consider: Memcached for simple K/V

4. **API Gateway**
   - Kong or AWS API Gateway for rate limiting, auth, logging
   - Consider: Nginx as simpler alternative

5. **Container Orchestration**
   - Docker Compose (current) ✅ for dev/test
   - ECS or Kubernetes for production (Phase 9)

---

# Recommendations for Your Sprint Planning

## Week-by-Week Suggested Breakdown

### Week 1: Phase 4.1-4.3
- Database schema (Task 4.1)
- Feature flag (Task 4.2)
- Webhook receiver (Task 4.3)
- **Demo:** Webhook receives form, stores to DB

### Week 2: Phase 4.4-4.6
- Celery async (Task 4.4)
- Production config (Task 4.5)
- Testing (Task 4.6)
- **Demo:** Workflow queued, processed async, retried on failure

### Week 3: Phase 5.1-5.3
- React setup (Task 5.1)
- Dashboard layout (Task 5.2)
- Workflows list/detail (Task 5.3)
- **Demo:** View workflows in browser

### Week 4: Phase 5.4-5.7
- Drafts review UI (Task 5.4)
- WebSocket updates (Task 5.5)
- Settings page (Task 5.6)
- Testing (Task 5.7)
- **Demo:** Full dashboard with live updates

### Week 5: Phase 6.1-6.3
- Error classification (Task 6.1)
- Retry logic (Task 6.2)
- Dead-letter queue (Task 6.3)
- **Demo:** Failed workflow retries, DLQ catches exhausted tasks

### Week 6: Phase 6.4-6.7
- Circuit breaker (Task 6.4)
- Reconciliation (Task 6.5)
- Observability (Task 6.6)
- Testing (Task 6.7)
- **Demo:** Comprehensive error handling and recovery

### Week 7: Phase 7.1-7.3
- Multi-queue (Task 7.1)
- Worker pool (Task 7.2)
- Load testing (Task 7.3)
- **Demo:** 100+ workflows processed successfully

### Week 8: Phase 7.4-7.7
- Bulk import API (Task 7.4)
- Worker dashboard (Task 7.5)
- DB optimization (Task 7.6)
- Testing (Task 7.7)
- **Demo:** Bulk import processed, workers visible

### Week 9: Phase 8.1-8.7
- Prometheus (Task 8.1)
- Grafana dashboards (Task 8.2)
- Alerting (Task 8.3)
- Tracing (Task 8.4)
- Log aggregation (Task 8.5)
- Synthetic monitoring (Task 8.6)
- Validation (Task 8.7)
- **Demo:** Full observability stack operational

### Week 10-11: Phase 9.1-9.8
- Multi-tenancy (Task 9.1)
- API keys (Task 9.2)
- Billing (Task 9.3)
- Security (Task 9.4)
- Documentation (Task 9.5)
- Deployment (Task 9.6)
- Load test (Task 9.7)
- Cutover (Task 9.8)
- **Demo:** Live in production! 🚀

---

# Final Recommendations

## Do These Things

1. **Start with Task 4.1** (Database schema) - Foundation for everything
2. **Write tests as you go** - Not after (debt accumulates fast)
3. **Deploy early and often** - Even if to staging
4. **Get feedback from ops team** - They'll use this system
5. **Document architecture decisions** - Future you will thank present you

## Don't Do These Things

1. ❌ Skip testing "we'll add it later" - You won't
2. ❌ Build multi-tenancy first - Start single-tenant, add later
3. ❌ Premature optimization - Profile, then optimize
4. ❌ Skip security review - Retrofit security = $$$
5. ❌ Postpone monitoring setup - Debug after-the-fact = ugh

## Success Criteria at Each Phase

| Phase | Must Achieve |
|-------|-------------|
| 4 | Real webhooks in, workflows processing async, DRAFT_ONLY toggleable |
| 5 | Ops team can see everything via dashboard |
| 6 | Failed workflows auto-recover without manual intervention |
| 7 | System handles 100+ workflows/day with <15s P95 latency |
| 8 | Issues detected and alerted before customer impact |
| 9 | Multi-tenant system deployable to production |

---

**This roadmap is designed to be aggressive but achievable with 2-3 experienced engineers working full-time. Each task is scoped to 1-3 days of work, building incrementally toward a production-grade system.**

**Good luck! 🚀**
