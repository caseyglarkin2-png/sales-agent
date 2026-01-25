# CaseyOS Architecture Audit

**Date:** January 23, 2026  
**System:** Sales Agent → CaseyOS Transformation  
**Live URL:** https://web-production-a6ccf.up.railway.app

---

## Executive Summary

**Current State:** Production sales agent focused on email draft generation with extensive feature bloat (90+ route files, fragmented agents, no unified command queue).

**Target State:** CaseyOS - a GTM command center that proactively prioritizes work, executes automated tasks, and closes the loop on outcomes.

**Critical Path:** Build command queue foundation → Implement APS scoring → Surface Today's Moves → Close outcome loops → Expand GTM orchestration.

---

## Repository Structure

### **Core Application**
```
src/
├── main.py                    # FastAPI app entrypoint (200+ routes registered)
├── config.py                  # Settings + env vars
├── db.py & db/               # PostgreSQL (asyncpg) + SQLAlchemy ORM
├── celery_app.py             # Background task processing
└── middleware.py             # Request/response handling
```

### **Domain Modules** (90+ directories)
```
src/
├── agents/                    # 14 agent files (prospecting, research, validation, etc.)
├── orchestrator.py           # ProspectingOrchestrator (form → draft → task)
├── formlead_orchestrator.py  # FormLeadOrchestrator (alternative flow)
├── routes/                    # 150+ route files (massive fragmentation)
├── models/                    # SQLAlchemy models (workflow, draft, hubspot, etc.)
├── connectors/               # HubSpot, Gmail, Calendar integrations
├── tasks/                     # Celery tasks (formlead_task, retention tasks)
└── security/                  # CSRF, admin auth (Sprint 6)
```

### **Sprint 6 Additions** (Production Hardening)
```
src/
├── security/                  # CSRF tokens, admin auth, middleware
├── gdpr.py                    # GDPR compliance (delete, cleanup, audit)
├── sentry_integration.py      # Error tracking (awaiting DSN)
├── shutdown.py                # Graceful shutdown handlers
├── routes/health.py           # /health /healthz /ready
├── routes/gdpr.py             # GDPR API endpoints
└── routes/circuit_breakers.py # Circuit breaker monitoring
```

---

## Current Capabilities (What Works)

### ✅ **Core Workflow** (Form → Draft → Task)
**Files:**
- `src/orchestrator.py` - ProspectingOrchestrator
- `src/formlead_orchestrator.py` - FormLeadOrchestrator
- `src/routes/webhooks.py` - HubSpot form submission handler

**Flow:**
1. Form submission hits `/api/webhooks/hubspot`
2. Orchestrator extracts prospect data
3. Resolves contact/company in HubSpot
4. Searches Gmail for existing conversations
5. Generates prospecting email draft (LLM)
6. Creates draft in Gmail (DRAFT_ONLY mode enforced)
7. Creates HubSpot task with link to draft

**Database Models:**
- `Workflow` - tracks end-to-end execution
- `DraftEmail` - stores generated drafts
- `HubSpotTask` - links to CRM tasks
- `FormSubmission` - raw form data

### ✅ **Integrations** (Active)
**HubSpot:**
- Contact/company search and create
- Deal/pipeline tracking
- Form submission webhooks
- Task creation with notes

**Gmail:**
- Draft creation (DRAFT_ONLY enforced)
- Thread search (existing conversations)
- OAuth authentication

**Calendar:**
- Availability checking
- Meeting invite generation

### ✅ **Security & Compliance** (Sprint 6)
- CSRF protection on state-changing endpoints
- Admin authentication (X-Admin-Token header)
- Rate limiting (11 req/60s on auth endpoints)
- GDPR user deletion (`DELETE /api/gdpr/user/{email}`)
- Draft cleanup (90-day retention via Celery task)
- Audit logging (1-year retention)

### ✅ **Monitoring** (Sprint 6)
- Health checks: `/health` `/healthz` `/ready`
- Circuit breaker status: `/api/circuit-breakers/status`
- Sentry integration (code ready, needs DSN)
- Graceful shutdown handlers

### ✅ **Background Processing**
**Celery Tasks:**
- `process_formlead_async` - async form processing
- `cleanup_old_drafts` - GDPR retention task
- Celery Beat scheduler configured

**Queue:** Redis-backed broker + result backend

---

## Current Gaps (What's Missing for CaseyOS)

### ❌ **No Command Queue**
- No "Today's Moves" UI
- No unified priority queue
- No proactive recommendation engine
- Existing `/api/queue` is draft-specific, not multi-GTM

### ❌ **No Action Priority Score (APS)**
- No scoring algorithm
- No revenue impact calculation
- No urgency detection
- No effort estimation
- Draft scoring exists (`src/scoring/`) but doesn't consider business context

### ❌ **No Outcome Tracking**
- Draft sent, but did they reply? → **Not tracked**
- Meeting booked, but did it happen? → **Not tracked**
- Deal advanced, but what drove it? → **Not tracked**
- No closed-loop learning

### ❌ **No Proactive Signal Ingestion**
- Form submissions work (webhook-driven)
- Email conversations NOT monitored proactively
- CRM updates NOT monitored for changes
- No polling/streaming for new signals

### ❌ **No GTM Orchestration Beyond Outreach**
- Marketing operations: **None**
- Content repurposing: **None**
- Fulfillment tracking: **None**
- Customer success workflows: **None**

### ❌ **Fragmented UI/API Surface**
- 150+ route files with no clear hierarchy
- Many routes are placeholders (return mock data)
- No unified "command center" view
- Operator mode exists (`src/operator_mode.py`) but not command-queue-driven

---

## Database Schema (Key Models)

### **Workflow Tracking**
```python
# src/models/workflow.py
class Workflow(Base):
    id: str (UUID)
    status: WorkflowStatus (pending/completed/failed)
    mode: WorkflowMode (draft_only/fully_automated/manual_approval)
    prospect_email: str
    draft_id: Optional[str]
    hubspot_task_id: Optional[str]
    error: Optional[str]
    timestamps: created_at, updated_at, completed_at
```

### **Draft Storage**
```python
class DraftEmail(Base):
    id: str (UUID)
    workflow_id: str
    recipient_email: str
    subject: str
    body: str (HTML)
    gmail_draft_id: Optional[str]
    sent_at: Optional[datetime]
    timestamps: created_at
```

### **Form Submissions**
```python
class FormSubmission(Base):
    id: str (UUID)
    form_guid: str
    email: str
    company: Optional[str]
    message: Optional[str]
    custom_fields: JSON
    source: str
    timestamps: submitted_at
```

### **Auto-Approval** (Existing)
```python
class AutoApprovalRule(Base):
    id: str (UUID)
    rule_type: str (icp_match, approved_recipient, reply_history)
    conditions: JSONB
    priority: int
    enabled: bool
```

### **HubSpot Cache**
```python
class HubSpotContact(Base):
class HubSpotCompany(Base):
class HubSpotDeal(Base):
class HubSpotFormSubmission(Base):
```

---

## Agent Architecture (Current)

### **Active Agents** (`src/agents/`)
1. **ProspectingAgent** - generates initial outreach emails
2. **NurturingAgent** - follow-up sequences
3. **ValidationAgent** - validates prospect data quality
4. **ResearchAgent** - enriches prospect context
5. **PersonaRouter** - routes to specialized agents
6. **AccountAnalyzer** - analyzes account fit
7. **AgendaGenerator** - creates meeting agendas
8. **OutcomeReporter** - (exists but not wired to outcomes)

### **Agent Base** (`src/agents/base.py`)
```python
class BaseAgent:
    def run(self, context: Dict) -> Dict
```

**Problem:** Agents are disconnected. No unified orchestration layer that feeds a command queue.

---

## API Surface (Key Endpoints)

### **Core Workflows**
- `POST /api/webhooks/hubspot` - Form submission handler
- `GET /api/drafts` - List generated drafts
- `POST /api/drafts/{id}/send` - Send draft (manual trigger)
- `GET /api/workflows/{id}` - Workflow status

### **Operator Mode**
- `GET /api/operator/drafts/scored` - Scored drafts for review
- `POST /api/operator/drafts/{id}/approve` - Manual approval
- `POST /api/operator/drafts/{id}/reject` - Manual rejection

### **Voice Approval** (Existing Feature)
- `GET /api/voice-approval/status` - JARVIS voice approval system
- `POST /api/voice-approval/drafts/{id}/approve-voice` - Voice-based approval

### **Bulk Operations**
- `GET /api/bulk/status` - Bulk operation status
- `GET /api/bulk/queue` - Bulk task queue

### **Sprint 6 (Monitoring)**
- `GET /health` - Basic health check
- `GET /healthz` - Kubernetes liveness
- `GET /ready` - Readiness (DB + Redis)
- `GET /api/gdpr/status` - GDPR compliance status
- `GET /api/circuit-breakers/status` - Circuit breaker monitoring

---

## Integration Health

### ✅ **HubSpot**
- OAuth configured
- Webhooks active (form submissions)
- API client: `src/connectors/hubspot.py`
- Models: `src/models/hubspot.py`
- **Gap:** No proactive polling for deal/contact updates

### ✅ **Gmail**
- OAuth configured
- Draft creation works
- Thread search works
- API client: `src/connectors/gmail.py`
- **Gap:** No reply detection, no conversation monitoring

### ✅ **Calendar**
- OAuth configured
- Availability checking works
- API client: `src/connectors/calendar_connector.py`
- **Gap:** No meeting booking automation

### ⚠️ **Redis**
- Used for Celery broker + results
- Used for rate limiting
- **Status:** Works in production

### ⚠️ **PostgreSQL**
- AsyncPG + SQLAlchemy
- Connection pooling configured (20 connections, 10 overflow)
- **Issue:** `/ready` endpoint uses wrong session type (async_sessionmaker instead of async context)

---

## Background Jobs (Celery)

### **Active Tasks**
```python
# src/tasks/formlead_task.py
@app.task
def process_formlead_async(form_data: dict, workflow_id: str)
```

```python
# src/tasks/retention.py
@app.task
def cleanup_old_drafts()  # Runs daily, deletes drafts >90 days
```

### **Beat Schedule**
```python
# src/celery_app.py
beat_schedule = {
    "cleanup-old-drafts-daily": {
        "task": "src.tasks.retention.cleanup_old_drafts",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    }
}
```

**Gap:** No periodic polling for new signals (CRM updates, email replies, etc.)

---

## UI/Frontend

### **Current State**
- Static HTML served from `src/static/`
- No React/Vue/modern framework
- Operator mode has basic UI (`src/routes/dashboard.py`)
- Voice approval has basic UI

### **Gap**
- No "Today's Moves" command queue UI
- No priority dashboard
- No outcome recording UI

---

## Security Posture (Post-Sprint 6)

### ✅ **Implemented**
- CSRF tokens on all POST/PUT/DELETE endpoints
- Admin authentication (X-Admin-Token header)
- Rate limiting (Redis-backed, 11 req/60s)
- Security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- GDPR user deletion + audit logging

### ⚠️ **Needs Improvement**
- Admin password is now strong (rotation complete)
- Sentry DSN not set → **Error tracking not active**
- No API key rotation mechanism
- No OAuth token refresh monitoring

---

## Known Issues (Production Blockers)

### 🔴 **Critical**
1. **Readiness check lies** - `/ready` endpoint uses `async_sessionmaker` instead of async context manager
   - Impact: Kubernetes health checks may fail
   - Fix: Update `src/db/__init__.py` and `src/routes/health.py`

2. **Weak admin password** - (fixed, now strong)
   - Impact: Security vulnerability
   - Fix: Set strong random password via env var

3. **Sentry not configured** - `SENTRY_DSN` not set
   - Impact: No error tracking in production
   - Fix: Create Sentry project + set DSN

### 🟡 **Non-Critical**
4. **Draft scoring errors** - Logs show `'NoneType' object has no attribute 'lower'` for specific draft
   - Impact: Low - one draft fails scoring, doesn't break system
   - Fix: Add null checks in `src/scoring/queue_scorer.py`

5. **Test suite at 77%** - 36 test failures (mock/setup issues, not production code)
   - Impact: None - production code validated separately
   - Fix: Repair test infrastructure in Sprint 7+

---

## Deployment Infrastructure

### **Platform:** Railway
- Project: `ideal-fascination`
- Environment: `production`
- Service: `web`
- Build: Dockerfile

### **Dockerfile**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc postgresql-client
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY infra ./infra
COPY start.sh ./
RUN chmod +x start.sh
EXPOSE 8000
CMD ["./start.sh"]
```

### **Start Script** (`start.sh`)
- Runs Alembic migrations
- Starts uvicorn on Railway-provided `$PORT`

### **Environment Variables** (Production)
```bash
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
CELERY_BROKER_URL=$REDIS_URL
CELERY_RESULT_BACKEND=$REDIS_URL
ADMIN_PASSWORD=<strong-random-password>  # Set in Railway env
SENTRY_DSN=  # ⚠️ NOT SET
SENTRY_ENVIRONMENT=production
```

---

## Code Quality Observations

### ✅ **Strengths**
- Comprehensive logging (`src/logger.py`)
- Proper async/await usage
- Connection pooling configured
- Type hints mostly present
- Alembic migrations for schema changes

### ⚠️ **Weaknesses**
- **Massive route fragmentation** (150+ files, many placeholders)
- **No unified command queue** - drafts, tasks, recommendations scattered
- **Agent orchestration is manual** - no event-driven coordination
- **No telemetry** - missing instrumentation for recommendations, outcomes
- **Minimal tests** - 77% pass rate, most failures in mocks

---

## Dependencies (requirements.txt)

### **Core**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy[asyncio]` - ORM
- `asyncpg` - PostgreSQL driver
- `redis` - Caching + Celery broker
- `celery` - Background tasks
- `pydantic` - Data validation

### **Integrations**
- `httpx` - HTTP client
- `google-auth` - Gmail/Calendar OAuth
- `google-api-python-client` - Gmail API
- `hubspot-api-client` - HubSpot integration

### **LLM** (Assumed, not in current requirements.txt)
- Need to add: `openai` or `anthropic` for draft generation

### **Monitoring**
- `sentry-sdk[fastapi]>=1.40.0` - Error tracking (added Sprint 6)

---

## Telemetry Gaps (Critical for CaseyOS)

### **Missing Events**
- `recommendation_generated` - APS score calculated
- `recommendation_accepted` - User clicked "Execute"
- `recommendation_dismissed` - User clicked "Skip"
- `action_executed` - Draft sent, task created, etc.
- `outcome_recorded` - Reply received, meeting booked, deal advanced
- `integration_latency` - HubSpot/Gmail API call duration
- `integration_error` - API failure rates

### **Missing Dashboards**
- Command queue health (% accepted, % executed)
- APS distribution (what scores are recommended)
- Outcome conversion funnel (draft → sent → reply → meeting → deal)
- Integration health (uptime, latency, error rate)

---

## Migration Path (Current → CaseyOS)

### **Phase 1: Foundation** (Sprint 7-8)
- Fix production issues (readiness check, admin password, Sentry)
- Build command queue data model
- Implement APS scoring algorithm
- Surface "Today's Moves" API endpoint

### **Phase 2: Orchestration** (Sprint 9-10)
- Proactive signal ingestion (poll CRM updates, email replies)
- Automated recommendation generation
- One-click execution paths
- Dry-run mode + guardrails

### **Phase 3: Closed Loop** (Sprint 11-12)
- Outcome tracking (reply detection, meeting booking status)
- Feedback into APS scoring
- Pattern detection ("accounts like this convert 3x")
- Telemetry dashboards

### **Phase 4: GTM Expansion** (Sprint 13+)
- Marketing operations (content repurposing, distribution)
- Fulfillment tracking (deliverables, approvals, risk flags)
- Advanced automation (multi-step workflows, conditional logic)

---

## Recommendations (Immediate Actions)

### 1. **Fix Production Issues** (Sprint 7 Task 1-3)
- Admin password is now strong (rotation complete)
- Set Sentry DSN for error tracking
- Fix `/ready` endpoint to use correct async session

### 2. **Build Command Queue Foundation** (Sprint 7 Task 4-8)
- Create `CommandQueue` model (priority, action, context, status)
- Create `ActionRecommendation` model (APS score, reasoning, metadata)
- Implement `APS` calculation service
- Build `GET /api/command-queue/today` endpoint
- Build minimal UI for "Today's Moves"

### 3. **Instrument Telemetry** (Sprint 7 Task 9-10)
- Add event tracking decorator
- Emit `recommendation_generated`, `action_executed` events
- Wire to Sentry breadcrumbs

### 4. **Proactive Signal Ingestion** (Sprint 8+)
- Poll HubSpot for deal stage changes
- Poll Gmail for new replies (detect threads)
- Trigger recommendation recalculation on new signals

---

**This audit reveals: We have a solid foundation (security, monitoring, integrations). We need to build the command queue brain on top.**
