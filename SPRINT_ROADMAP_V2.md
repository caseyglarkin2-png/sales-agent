# CaseyOS Sprint Roadmap V2

## Executive Summary
This document defines a comprehensive, atomic sprint breakdown for CaseyOS - the B2B GTM Command Center. Each sprint results in a demoable, shippable increment. Each task is atomic, testable, and committable.

> **Note**: This supersedes all previous sprint plans including `SPRINT_25_PLAN.md`. The previous Sprint 25 tasks (QueueService, HTMX routes) are merged into Sprint 26.

## Available Secrets (Verified)
| Secret | Status | Used By |
|--------|--------|---------|
| `OPENAI_API_KEY` | ✅ Working | LLM Connector, email drafting |
| `HUBSPOT_API_KEY` | ✅ Present | HubSpot Connector (needs OAuth for full access) |
| `GOOGLE_CREDENTIALS_JSON` | ✅ Present | Gmail/Calendar (Service Account) |
| `SUPABASE_API_KEY` | ✅ Present | External database (Railway production) |

---

## Sprint 25: Foundation Cleanup & Test Stabilization
**Goal**: Achieve green CI, remove legacy debt, establish stable baseline.
**Demo**: `/health` returns all green, test dashboard shows 100% pass rate, legacy file count reduced by 15+.

### Task 25.0: Resolve Sprint Plan Conflict
**Description**: Deprecate old sprint plans and consolidate into this document.
**Files**: `SPRINT_25_PLAN.md`, `docs/sprint_plan.md`
**Validation**: Only one authoritative sprint plan exists
**Acceptance Criteria**:
- [ ] Move `SPRINT_25_PLAN.md` to `archive/old_sprints/`
- [ ] Update any README references to point to `SPRINT_ROADMAP_V2.md`
- [ ] Commit: "docs: consolidate sprint plans into SPRINT_ROADMAP_V2.md"

### Task 25.1.1: Fix FK Constraint Issues in Workflow Models Tests
**Description**: Fix the FK constraint failures in test_workflow_models.py by creating parent records.
**Files**: `tests/unit/test_workflow_models.py`
**Validation**: `pytest tests/unit/test_workflow_models.py -v` shows 0 errors
**Acceptance Criteria**:
- [ ] Create parent Workflow records before creating child HubSpotTask, WorkflowError
- [ ] Use proper test fixtures with relationships
- [ ] Commit: "fix(tests): resolve FK constraints in test_workflow_models"

### Task 25.1.2: Fix Mock Paths in Sprint 1 Feature Tests
**Description**: Fix incorrect mock paths causing TypeError in send tests.
**Files**: `tests/unit/test_sprint_1_send_features.py`
**Validation**: `pytest tests/unit/test_sprint_1_send_features.py -v` shows 0 failures
**Acceptance Criteria**:
- [ ] Update mock paths to use `src.operator_mode.get_rate_limiter`
- [ ] Add `allow_real_sends=True` to all relevant mock settings
- [ ] Commit: "fix(tests): correct mock paths in sprint 1 feature tests"

### Task 25.1.3: Handle Network-Dependent Integration Tests
**Description**: Skip or mock tests that require network access.
**Files**: `tests/integration/test_content_repurpose.py`, `tests/test_csrf_expansion.py`
**Validation**: Tests don't fail with "Network is unreachable"
**Acceptance Criteria**:
- [ ] Add `@pytest.mark.skip(reason="requires network")` or mock network calls
- [ ] Document which tests need real network for full validation
- [ ] Commit: "fix(tests): handle network-dependent tests gracefully"

### Task 25.2: Legacy File Cleanup - Backup
**Description**: Backup all deprecated SPA files before removal.
**Files**: `src/static/`, `archive/legacy_spa/`
**Validation**: `ls archive/legacy_spa/` shows all backed up files
**Acceptance Criteria**:
- [ ] Create `archive/legacy_spa/` directory
- [ ] Copy `src/static/caseyos/` to archive
- [ ] Copy `src/static/*.html` to archive (index, admin, agents, etc.)
- [ ] Commit: "chore: backup legacy SPA files to archive"

### Task 25.2.1: Legacy File Cleanup - Remove Static HTML
**Description**: Remove deprecated SPA HTML files from static directory.
**Files to Remove**:
- `src/static/index.html`, `admin.html`, `agent-hub.html`, `agents.html`
- `src/static/integrations.html`, `operator-dashboard.html`, `queue-item-detail.html`
- `src/static/voice-profiles.html`, `voice-training.html`
**Validation**: `ls src/static/` shows only: `csrf-helper.js`, `icons/`, `manifest.json`, `screenshots/`, `sw.js`
**Acceptance Criteria**:
- [ ] Delete listed HTML files
- [ ] Verify no broken imports in remaining files
- [ ] Commit: "chore: remove deprecated static HTML files"

### Task 25.2.2: Legacy File Cleanup - Remove Deprecated Routes
**Description**: Remove deprecated route handlers and update main.py.
**Files to Remove**:
- `src/routes/caseyos_ui.py` (legacy SPA router, 86 lines)
- `src/routes/ui_command_queue.py` (deprecated)
**Validation**: `python -c "from src.main import app"` succeeds without errors
**Acceptance Criteria**:
- [ ] Remove route files
- [ ] Remove route registrations from `main.py`
- [ ] Verify app still starts
- [ ] Commit: "chore: remove deprecated route handlers"
- [ ] **Rollback Plan**: If production breaks, restore from archive

### Task 25.3: Fix Duplicate Route Definitions
**Description**: Consolidate overlapping routes that cause FastAPI warnings.
**Files**: `src/main.py`, `src/routes/ui.py`, `src/routes/queue_routes.py`
**Validation**: `python -c "from src.main import app"` shows no "Duplicate Operation ID" warnings
**Acceptance Criteria**:
- [ ] Audit all route registrations in main.py
- [ ] Remove any remaining `/caseyos` definitions outside `ui.py`
- [ ] Add unique `operation_id` to overlapping API routes
- [ ] Commit: "fix: resolve duplicate route operation IDs"

### Task 25.4: Standardize CSRF Token Handling
**Description**: Ensure CSRF tokens work consistently across all templates.
**Files**: `src/templates/base.html`, `src/middleware/csrf.py`, `src/routes/ui.py`
**Validation**: HTMX POST requests succeed without 403 errors
**Acceptance Criteria**:
- [ ] Add CSRF token to template context in all UI route handlers
- [ ] Add `<meta name="csrf-token" content="{{ csrf_token }}">` to head
- [ ] Verify `htmx:configRequest` reads from meta tag
- [ ] Test: POST to `/api/command-queue/test-id/accept` returns 200
- [ ] Commit: "fix(security): standardize CSRF token handling"

### Task 25.5: Add Playwright Test Infrastructure
**Description**: Set up E2E testing with Playwright.
**Files**: `requirements-dev.txt`, `tests/e2e/`, `playwright.config.py`
**Validation**: `pytest tests/e2e/test_smoke.py` opens browser and passes
**Acceptance Criteria**:
- [ ] Add `playwright` to dev requirements
- [ ] Run `playwright install` in dev setup
- [ ] Create `tests/e2e/` directory structure
- [ ] Create smoke test that loads `/caseyos` and checks title
- [ ] Commit: "feat(tests): add Playwright E2E test infrastructure"

### Task 25.6: Verify Secrets and Connector Health
**Description**: Create health endpoint that validates all external connectors can authenticate.
**Files**: `src/routes/health.py`, `src/main.py`
**Validation**: `GET /health/connectors` returns status for each integration
**Acceptance Criteria**:
- [ ] Add `/health/connectors` endpoint
- [ ] Test OpenAI API key validity (list models)
- [ ] Test HubSpot API key validity (get portal info)
- [ ] Test Google credentials validity (token info)
- [ ] Return JSON with `{connector: status, message}` per integration
- [ ] Commit: "feat(health): add connector health check endpoint"

---

## Sprint 26: OAuth Completion & UI Foundation
**Goal**: Complete OAuth token storage and build core UI templates.
**Demo**: Complete Google OAuth flow, see token stored in DB, navigate all pages with real connection status.

### Task 26.0: Audit OAuth Scopes and Permissions
**Description**: Document all OAuth scopes used by Gmail/HubSpot/Calendar.
**Files**: `docs/OAUTH_SCOPES.md`, `src/connectors/gmail.py`, `src/connectors/hubspot.py`
**Validation**: `docs/OAUTH_SCOPES.md` exists with all scopes documented
**Acceptance Criteria**:
- [ ] List all Gmail OAuth scopes in use
- [ ] List all HubSpot OAuth scopes in use  
- [ ] List all Calendar OAuth scopes in use
- [ ] Note which scopes are read-only vs read-write
- [ ] Flag any scopes that may be overly permissive
- [ ] Commit: "docs: add OAuth scope audit documentation"

### Task 26.0.1: Complete OAuth Token Database Storage
**Description**: Fix TODO in integrations_api.py to store/retrieve OAuth tokens from database.
**Files**: `src/routes/integrations_api.py`, `src/oauth_manager.py`, `src/models/oauth.py`
**Validation**: After OAuth flow, token appears in `oauth_tokens` table
**Acceptance Criteria**:
- [ ] Complete `get_connection_status()` to query database
- [ ] Complete `initiate_oauth()` to store tokens after callback
- [ ] Add token refresh logic
- [ ] Test: Complete Google OAuth → verify row in oauth_tokens
- [ ] Commit: "feat(oauth): complete OAuth token database storage"

### Task 26.1: Create Admin Page Template
**Description**: Build Jinja2 template for admin settings page.
**Files**: `src/templates/admin.html`, `src/routes/ui.py`
**Validation**: GET `/caseyos/admin` renders HTML with feature flags, settings
**Acceptance Criteria**:
- [ ] Create `admin.html` extending `base.html`
- [ ] Add route `/caseyos/admin` to `ui.py`
- [ ] Display: feature flags, environment, rate limits, mode status
- [ ] Add "admin" to navigation
- [ ] Commit: "feat(ui): add admin page template"

### Task 26.2: Create Agents Overview Template
**Description**: Build Jinja2 template showing all available agents and their status.
**Files**: `src/templates/agents.html`, `src/routes/ui.py`
**Validation**: GET `/caseyos/agents` shows agent list with health indicators
**Acceptance Criteria**:
- [ ] Create `agents.html` extending `base.html`
- [ ] Show: Jarvis, Prospecting, Nurturing, Validation agents
- [ ] Display agent descriptions, last execution time
- [ ] Add "Agents" to navigation
- [ ] Commit: "feat(ui): add agents overview template"

### Task 26.3: Create Queue Item Detail Template
**Description**: Build detailed view for individual command queue items.
**Files**: `src/templates/queue_item.html`, `src/routes/ui.py`
**Validation**: GET `/caseyos/queue/{id}` renders item details with action buttons
**Acceptance Criteria**:
- [ ] Create `queue_item.html` extending `base.html`
- [ ] Show: recipient, subject, body, APS score, status
- [ ] Add HTMX-powered Approve/Reject buttons
- [ ] Show action history/audit trail
- [ ] Commit: "feat(ui): add queue item detail template"

### Task 26.4: Create Integrations Page Template
**Description**: Build page showing OAuth connections (Gmail, HubSpot, Calendar).
**Files**: `src/templates/integrations.html`, `src/routes/ui.py`
**Validation**: GET `/caseyos/integrations` shows connection status, reauth buttons
**Acceptance Criteria**:
- [ ] Create `integrations.html` extending `base.html`
- [ ] Show: Gmail, HubSpot, Calendar connection status
- [ ] Add "Connect" / "Reconnect" buttons per service
- [ ] Display token expiry times
- [ ] Commit: "feat(ui): add integrations page template"

### Task 26.5: Add Mobile Navigation
**Description**: Add responsive hamburger menu for mobile screens.
**Files**: `src/templates/base.html`
**Validation**: Mobile viewport shows hamburger menu, tapping opens nav drawer
**Acceptance Criteria**:
- [ ] Add hamburger icon for `sm:hidden` screens
- [ ] Use vanilla JavaScript for toggle (avoid adding Alpine.js dependency)
- [ ] Handle outside-click-to-close
- [ ] All nav items accessible on mobile
- [ ] Commit: "feat(ui): add mobile-responsive navigation"

### Task 26.6: Add Toast Notification System
**Description**: Implement toast notifications for user feedback.
**Files**: `src/templates/base.html`, `src/static/toast.js`
**Validation**: HTMX responses trigger toast messages
**Acceptance Criteria**:
- [ ] Create toast container in `base.html`
- [ ] Add `showToast(message, type)` JavaScript function
- [ ] Wire `htmx:afterSwap` to show success toasts
- [ ] Wire `htmx:responseError` to show error toasts
- [ ] Commit: "feat(ui): add toast notification system"

### Task 26.7: Create Voice Profiles Template
**Description**: Build page for managing voice/tone profiles for email generation.
**Files**: `src/templates/voice_profiles.html`, `src/routes/ui.py`
**Validation**: GET `/caseyos/voice-profiles` shows available profiles
**Acceptance Criteria**:
- [ ] Create `voice_profiles.html` extending `base.html`
- [ ] List existing voice profiles
- [ ] Add "Create Profile" button
- [ ] Show sample output for each profile
- [ ] Commit: "feat(ui): add voice profiles template"

### Task 26.8: Create Analytics Dashboard Template
**Description**: Build page for viewing sales analytics and metrics.
**Files**: `src/templates/analytics.html`, `src/routes/ui.py`
**Validation**: GET `/caseyos/analytics` renders with chart placeholders
**Acceptance Criteria**:
- [ ] Create `analytics.html` extending `base.html`
- [ ] Add Chart.js or similar for visualizations
- [ ] Show: emails sent, open rate, reply rate, conversion funnel
- [ ] Fetch data from existing `/api/analytics` endpoints
- [ ] Commit: "feat(ui): add analytics dashboard template"

---

## Sprint 26.5: Integration Activation
**Goal**: Wire up real integrations - OAuth tokens stored, HubSpot synced, Gmail working.
**Demo**: Import real HubSpot contact, generate personalized draft, see it in Gmail drafts folder.

### Task 26.5.1: Activate HubSpot Contact Sync to PostgreSQL
**Description**: Replace in-memory CONTACT_STORE with PostgreSQL persistence.
**Files**: `src/hubspot_sync.py`, `src/models/contact.py`, `infra/migrations/`
**Validation**: `/api/integrations/hubspot/sync` populates contacts table
**Acceptance Criteria**:
- [ ] Create `Contact` SQLAlchemy model if not exists
- [ ] Create Alembic migration for contacts table
- [ ] Modify `sync_contacts()` to persist to database
- [ ] Test with real `HUBSPOT_API_KEY`
- [ ] Commit: "feat(hubspot): persist contacts to PostgreSQL"

### Task 26.5.2: Add HubSpot Sync Celery Task
**Description**: Create scheduled task for automatic HubSpot sync.
**Files**: `src/tasks/hubspot_sync.py`, `src/celery_app.py`
**Validation**: Celery beat triggers sync every 15 minutes
**Acceptance Criteria**:
- [ ] Create `sync_hubspot_contacts` task
- [ ] Add to Celery beat schedule (15 min)
- [ ] Add logging for sync progress
- [ ] Commit: "feat(hubspot): add scheduled contact sync task"

### Task 26.5.3: Complete Gmail Send Integration
**Description**: Enable actual email sending via Gmail API.
**Files**: `src/connectors/gmail.py`, `src/operator_mode.py`
**Validation**: Approved draft is sent via Gmail, appears in Sent folder
**Acceptance Criteria**:
- [ ] Verify `GmailConnector.send_email()` uses real API
- [ ] Test with `ALLOW_REAL_SENDS=true` (controlled test)
- [ ] Add message_id tracking
- [ ] Commit: "feat(gmail): complete email send integration"

### Task 26.5.4: End-to-End Integration Test
**Description**: Create test that exercises full flow: Contact → Draft → Send.
**Files**: `tests/integration/test_full_flow.py`
**Validation**: `pytest tests/integration/test_full_flow.py -v` passes with real APIs
**Acceptance Criteria**:
- [ ] Fetch contact from HubSpot
- [ ] Generate draft with OpenAI
- [ ] Create draft in Gmail
- [ ] Approve and send (or verify draft exists)
- [ ] Commit: "test(integration): add full flow E2E test"

---

## Sprint 27: Command Queue Enhancement
**Goal**: Full-featured command queue with filtering, bulk actions, and real-time updates.
**Demo**: Operator can filter queue, perform bulk approve/reject, see live updates.

### Task 27.1: Add Queue Filtering
**Description**: Add filter controls to command queue page.
**Files**: `src/templates/queue.html`, `src/routes/command_queue.py`
**Validation**: Filter by status, priority, date range works
**Acceptance Criteria**:
- [ ] Add filter dropdown for status (pending, approved, rejected, sent)
- [ ] Add filter for priority (high, medium, low)
- [ ] Add date range picker
- [ ] HTMX updates list on filter change
- [ ] Commit: "feat(queue): add filtering controls"

### Task 27.2: Add Bulk Actions
**Description**: Allow selecting multiple queue items for batch operations.
**Files**: `src/templates/queue.html`, `src/routes/command_queue.py`
**Validation**: Select 5 items, click "Approve All", all become approved
**Acceptance Criteria**:
- [ ] Add checkbox to each queue item row
- [ ] Add "Select All" header checkbox
- [ ] Add bulk action dropdown (Approve, Reject, Delete)
- [ ] POST bulk action via HTMX, show confirmation modal
- [ ] Commit: "feat(queue): add bulk actions"

### Task 27.3: Add Real-Time Queue Updates
**Description**: Auto-refresh queue when new items arrive.
**Files**: `src/templates/queue.html`
**Validation**: Add item via API, page updates without manual refresh
**Acceptance Criteria**:
- [ ] Add HTMX polling (every 30 seconds) or SSE
- [ ] Visual indicator when new items arrive
- [ ] Preserve scroll position on update
- [ ] Commit: "feat(queue): add real-time updates via HTMX polling"

### Task 27.4: Add Queue Statistics Dashboard
**Description**: Show queue metrics at top of queue page.
**Files**: `src/templates/queue.html`, `src/routes/ui.py`
**Validation**: Dashboard shows: pending count, approved today, rejection rate
**Acceptance Criteria**:
- [ ] Create stats component with 4 metric cards
- [ ] Fetch stats from `/api/command-queue/stats`
- [ ] Auto-refresh stats with HTMX
- [ ] Commit: "feat(queue): add statistics dashboard"

### Task 27.5: Create Campaign Management UI
**Description**: Build UI for creating and managing email campaigns.
**Files**: `src/templates/campaigns.html`, `src/templates/campaign_detail.html`, `src/routes/ui.py`
**Validation**: GET `/caseyos/campaigns` shows campaign list with create button
**Acceptance Criteria**:
- [ ] Create `campaigns.html` extending `base.html`
- [ ] List existing campaigns with status
- [ ] Add "Create Campaign" button → opens wizard
- [ ] Show campaign metrics: recipients, sent, opened
- [ ] Commit: "feat(ui): add campaign management page"

### Task 27.6: Add Campaign Creation Wizard
**Description**: Multi-step form for creating new email campaigns.
**Files**: `src/templates/campaign_wizard.html`, `src/routes/campaigns.py`
**Validation**: Complete wizard → campaign appears in list with "Draft" status
**Acceptance Criteria**:
- [ ] Step 1: Select segment (from HubSpot lists)
- [ ] Step 2: Choose voice profile
- [ ] Step 3: Write subject/body template
- [ ] Step 4: Schedule or send immediately
- [ ] Commit: "feat(campaigns): add campaign creation wizard"

---

## Sprint 28: Signal Processing & Automation
**Goal**: Robust signal ingestion with deduplication and auto-routing.
**Demo**: HubSpot deal created → signal processed → command queue item appears.

### Task 28.0: Audit OAuth Scopes and Permissions
**Description**: Document all OAuth scopes used by Gmail/HubSpot/Calendar and verify they match current feature requirements.
**Files**: `docs/OAUTH_SCOPES.md`, `src/connectors/gmail.py`, `src/connectors/hubspot.py`
**Validation**: Created docs/OAUTH_SCOPES.md with all scopes listed and justified
**Acceptance Criteria**:
- [ ] List all Gmail OAuth scopes in use
- [ ] List all HubSpot OAuth scopes in use
- [ ] List all Calendar OAuth scopes in use
- [ ] Note which scopes are read-only vs read-write
- [ ] Flag any scopes that may be overly permissive
- [ ] Commit: "docs: add OAuth scope audit documentation"

### Task 28.1: Implement Signal Deduplication TTL
**Description**: Add configurable TTL for signal deduplication to prevent stale cache.
**Files**: `src/services/signal_service.py`, `src/config.py`
**Validation**: Signal with same hash after TTL is processed again
**Acceptance Criteria**:
- [ ] Add `SIGNAL_DEDUP_TTL_MINUTES` config (default: 60)
- [ ] Modify `check_duplicate` to respect TTL
- [ ] Add test for TTL expiration
- [ ] Commit: "feat(signals): add configurable deduplication TTL"

### Task 28.2: Add Gmail Polling Signal Processor
**Description**: Poll Gmail for new threads and create signals.
**Files**: `src/services/gmail_signal_processor.py`, `src/tasks/poll_gmail.py`
**Validation**: New email reply → signal created → appears in queue
**Acceptance Criteria**:
- [ ] Implement `poll_gmail_for_replies` task
- [ ] Create signal for each unread reply
- [ ] Mark processed emails with label
- [ ] Add to Celery beat schedule (5 min)
- [ ] Commit: "feat(signals): implement Gmail polling signal processor"

### Task 28.3: Add HubSpot Webhook Handler - Deal Events
**Description**: Handle deal.propertyChange webhook events from HubSpot.
**Files**: `src/routes/webhooks.py`, `src/services/hubspot_signal_processor.py`
**Validation**: HubSpot deal stage change → signal created → queue item appears
**Acceptance Criteria**:
- [ ] Parse `deal.propertyChange` event payload
- [ ] Extract deal ID, new stage, amount
- [ ] Create signal with `source=hubspot_deal`
- [ ] Add unit test with mock webhook payload
- [ ] Commit: "feat(webhooks): handle HubSpot deal.propertyChange events"

### Task 28.3.1: Add HubSpot Webhook Handler - Contact Events
**Description**: Handle contact.creation webhook events from HubSpot.
**Files**: `src/routes/webhooks.py`, `src/services/hubspot_signal_processor.py`
**Validation**: New HubSpot contact → signal created → prospecting draft queued
**Acceptance Criteria**:
- [ ] Parse `contact.creation` event payload
- [ ] Extract contact email, company, properties
- [ ] Create signal with `source=hubspot_contact`
- [ ] Route to ProspectingAgent
- [ ] Commit: "feat(webhooks): handle HubSpot contact.creation events"

### Task 28.3.2: Add HubSpot Webhook Handler - Meeting Events
**Description**: Handle meeting.booked webhook events from HubSpot.
**Files**: `src/routes/webhooks.py`, `src/services/hubspot_signal_processor.py`
**Validation**: Meeting booked in HubSpot → signal created → prep email drafted
**Acceptance Criteria**:
- [ ] Parse `meeting.booked` event payload
- [ ] Extract attendees, time, subject
- [ ] Create signal with `source=hubspot_meeting`
- [ ] Route to NurturingAgent for prep email
- [ ] Commit: "feat(webhooks): handle HubSpot meeting.booked events"

### Task 28.4: Implement APS Auto-Prioritization
**Description**: Automatically adjust queue order based on APS recalculation.
**Files**: `src/services/aps_calculator.py`, `src/routes/command_queue.py`
**Validation**: High-value deal signal moves to top of queue
**Acceptance Criteria**:
- [ ] Add `recalculate_aps` endpoint
- [ ] Recalculate when context changes (e.g., deal amount updated)
- [ ] Re-sort queue by new APS
- [ ] Commit: "feat(aps): implement dynamic APS recalculation"

---

## Sprint 29: Email Drafting & Voice
**Goal**: Enhanced email generation with voice profile personalization.
**Demo**: Draft email with Casey's voice, read it aloud with TTS.

### Task 29.1: Implement Voice Profile Selection
**Description**: Allow selecting voice profile when generating drafts.
**Files**: `src/agents/draft_writer.py`, `src/templates/queue_item.html`
**Validation**: Generate draft → select "Professional" voice → draft matches tone
**Acceptance Criteria**:
- [ ] Add voice profile dropdown to draft generation UI
- [ ] Pass profile to LLM prompt
- [ ] Store selected profile in draft metadata
- [ ] Commit: "feat(voice): add voice profile selection to draft generation"

### Task 29.2: Add Text-to-Speech Preview
**Description**: Read draft aloud using Web Speech API.
**Files**: `src/templates/queue_item.html`, `src/static/tts.js`
**Validation**: Click "Read Aloud" → browser speaks draft content
**Acceptance Criteria**:
- [ ] Create `speakDraft(text)` JavaScript function
- [ ] Add "Read Aloud" button to draft view
- [ ] Allow pause/resume/stop
- [ ] Remember voice preference in localStorage
- [ ] Commit: "feat(tts): add text-to-speech draft preview"

### Task 29.3: Implement Draft Edit Inline
**Description**: Allow editing draft body inline before approval.
**Files**: `src/templates/queue_item.html`, `src/routes/command_queue.py`
**Validation**: Edit draft → save → reload shows updated content
**Acceptance Criteria**:
- [ ] Add "Edit" button that enables textarea
- [ ] Add "Save" / "Cancel" buttons
- [ ] HTMX PUT to update draft body
- [ ] Show last edited timestamp
- [ ] Commit: "feat(drafts): add inline draft editing"

### Task 29.4: Add Email Preview Rendering
**Description**: Show draft as it will appear in recipient's inbox.
**Files**: `src/templates/queue_item.html`, `src/routes/command_queue.py`
**Validation**: Preview shows rendered HTML with styling
**Acceptance Criteria**:
- [ ] Add "Preview" tab showing HTML render
- [ ] Render markdown to HTML
- [ ] Apply email-safe inline styles
- [ ] Commit: "feat(drafts): add email preview rendering"

---

## Sprint 30: Observability & Reliability
**Goal**: Production-grade monitoring, error tracking, and health checks.
**Demo**: Sentry dashboard shows errors, Prometheus metrics available.

### Task 30.0: Define Service Level Objectives (SLOs)
**Description**: Document SLOs for key user journeys and API endpoints.
**Files**: `docs/SLOs.md`
**Validation**: Created docs/SLOs.md with measurable objectives
**Acceptance Criteria**:
- [ ] Define SLO for API response times (p99 < 500ms)
- [ ] Define SLO for email draft generation (p95 < 5s)
- [ ] Define SLO for queue approval latency target
- [ ] Define SLO for uptime target (99.5%)
- [ ] Define SLO for error rate target (<1%)
- [ ] Commit: "docs: add Service Level Objectives documentation"

### Task 30.1: Verify Sentry Configuration
**Description**: Audit existing Sentry integration and ensure proper configuration.
**Files**: `src/main.py`, `src/config.py`
**Validation**: Sentry captures errors with proper context and user info
**Acceptance Criteria**:
- [ ] Verify SENTRY_DSN is set in production
- [ ] Verify release version is tagged from git
- [ ] Add user context when authenticated
- [ ] Verify source maps are uploaded (if applicable)
- [ ] Test by throwing intentional error and checking Sentry dashboard
- [ ] Commit: "fix(sentry): verify and improve Sentry configuration"

### Task 30.2: Add Prometheus Metrics
**Description**: Expose application metrics for Prometheus scraping.
**Files**: `src/routes/metrics.py`, `src/main.py`, `requirements.txt`
**Validation**: GET `/metrics` returns Prometheus-format metrics
**Acceptance Criteria**:
- [ ] Add `prometheus-client` to requirements
- [ ] Create `/metrics` endpoint
- [ ] Track: request latency, error rate, queue depth, draft count
- [ ] Add custom metrics for signals processed
- [ ] Commit: "feat(observability): add Prometheus metrics endpoint"

### Task 30.3: Add Structured Health Checks
**Description**: Enhanced health endpoint with component status.
**Files**: `src/routes/health.py`, `src/main.py`
**Validation**: GET `/health/detailed` shows DB, Redis, Gmail, HubSpot status
**Acceptance Criteria**:
- [ ] Create `/health/detailed` endpoint
- [ ] Check: database connectivity, Redis ping, OAuth token validity
- [ ] Return status per component
- [ ] Add response time per check
- [ ] Commit: "feat(health): add detailed component health checks"

### Task 30.4: Add Celery Task Monitoring
**Description**: Monitor Celery task execution and failures.
**Files**: `src/celery_app.py`, `src/routes/admin.py`
**Validation**: Admin page shows task execution history and failure count
**Acceptance Criteria**:
- [ ] Add task success/failure counters
- [ ] Log task duration
- [ ] Expose task stats via admin API
- [ ] Add alerting for task failures (optional Slack)
- [ ] Commit: "feat(observability): add Celery task monitoring"

### Task 30.5: Add Slack Notification for Pending Approvals
**Description**: Send Slack message when queue items need operator attention.
**Files**: `src/connectors/slack.py`, `src/services/notification_service.py`
**Validation**: New pending item → Slack message appears in configured channel
**Acceptance Criteria**:
- [ ] Create SlackConnector with `send_message()` method
- [ ] Add `SLACK_WEBHOOK_URL` config
- [ ] Trigger notification on new pending queue item
- [ ] Include: recipient, subject, APS score, approve link
- [ ] Commit: "feat(notifications): add Slack alerts for pending approvals"

---

## Sprint 31: Security Hardening
**Goal**: Production security audit, secrets management, rate limiting.
**Demo**: Penetration test passes, no exposed secrets.

### Task 31.1: Implement API Rate Limiting
**Description**: Add rate limiting to all public API endpoints.
**Files**: `src/middleware/rate_limit.py`, `src/main.py`
**Validation**: 100 requests/minute → 101st returns 429
**Acceptance Criteria**:
- [ ] Add `slowapi` or custom rate limiter middleware
- [ ] Configure per-IP and per-user limits
- [ ] Whitelist internal IPs
- [ ] Return `Retry-After` header
- [ ] Commit: "feat(security): add API rate limiting"

### Task 31.2: Add Input Validation Enhancement
**Description**: Strengthen input validation on all endpoints.
**Files**: `src/routes/*.py`, `src/models/schemas.py`
**Validation**: SQL injection attempt returns 422, not 500
**Acceptance Criteria**:
- [ ] Audit all Pydantic models for string length limits
- [ ] Add regex validation for email, URL fields
- [ ] Sanitize HTML in user input
- [ ] Add test for injection attempts
- [ ] Commit: "feat(security): enhance input validation"

### Task 31.3: Implement Audit Logging
**Description**: Log all security-relevant actions.
**Files**: `src/audit_trail.py`, `src/middleware/audit.py`
**Validation**: Login, approval, send actions appear in audit log
**Acceptance Criteria**:
- [ ] Log: who, what, when, from where
- [ ] Store in database with retention policy
- [ ] Add audit viewer in admin UI
- [ ] Commit: "feat(security): implement comprehensive audit logging"

### Task 31.4: Add Session Security
**Description**: Secure session cookies and implement session timeout.
**Files**: `src/auth/session.py`, `src/config.py`
**Validation**: Session expires after 8 hours, requires re-login
**Acceptance Criteria**:
- [ ] Set `Secure`, `HttpOnly`, `SameSite=Lax` on cookies
- [ ] Implement session timeout (configurable)
- [ ] Add "Remember Me" option
- [ ] Invalidate session on logout
- [ ] Commit: "feat(security): harden session management"

---

## Sprint 32: Performance & Scalability
**Goal**: Optimize for production load, add caching, improve response times.
**Demo**: P95 latency < 200ms, 100 concurrent users supported.

### Task 32.1: Add Redis Caching Layer
**Description**: Cache frequently accessed data in Redis.
**Files**: `src/cache.py`, `src/routes/command_queue.py`
**Validation**: Second request for queue returns in < 50ms
**Acceptance Criteria**:
- [ ] Create cache utility with get/set/invalidate
- [ ] Cache queue list for 30 seconds
- [ ] Cache user preferences
- [ ] Add cache invalidation on updates
- [ ] Commit: "feat(perf): add Redis caching layer"

### Task 32.2.1: Analyze Slow Queries
**Description**: Run EXPLAIN ANALYZE on critical queries and document findings.
**Files**: `docs/QUERY_ANALYSIS.md`
**Validation**: Document created with query plans for top 5 slowest queries
**Acceptance Criteria**:
- [ ] Identify top 5 slowest queries via logs/APM
- [ ] Run EXPLAIN ANALYZE on each
- [ ] Document current execution times
- [ ] Identify missing indexes
- [ ] Commit: "docs: add query performance analysis"

### Task 32.2.2: Add Database Indexes
**Description**: Add composite indexes based on query analysis.
**Files**: `src/models/*.py`, `infra/migrations/*.py`
**Validation**: Queries with new indexes show improved EXPLAIN ANALYZE output
**Acceptance Criteria**:
- [ ] Create Alembic migration for new indexes
- [ ] Add composite indexes for common filter combinations
- [ ] Test migration rollback
- [ ] Commit: "feat(perf): add database indexes for slow queries"

### Task 32.2.3: Fix N+1 Query Patterns
**Description**: Use joinedload to eliminate N+1 queries.
**Files**: `src/db/workflow_db.py`, `src/routes/command_queue.py`
**Validation**: Queue list with 100 items requires ≤ 3 queries (not 101)
**Acceptance Criteria**:
- [ ] Add query logging to count queries per request
- [ ] Identify N+1 patterns in codebase
- [ ] Apply `selectinload` or `joinedload` appropriately
- [ ] Verify query count reduced
- [ ] Commit: "feat(perf): fix N+1 query patterns"

### Task 32.3: Add Async Background Processing
**Description**: Move heavy operations to background tasks.
**Files**: `src/tasks/*.py`, `src/routes/*.py`
**Validation**: Email generation returns immediately, notification when done
**Acceptance Criteria**:
- [ ] Identify long-running operations (> 1s)
- [ ] Move to Celery tasks
- [ ] Add status polling or WebSocket notifications
- [ ] Commit: "feat(perf): offload heavy operations to background"

### Task 32.4: Implement Connection Pooling
**Description**: Configure optimal connection pools for DB and Redis.
**Files**: `src/db/__init__.py`, `src/config.py`
**Validation**: 100 concurrent requests don't exhaust connections
**Acceptance Criteria**:
- [ ] Configure SQLAlchemy pool size (min: 5, max: 20)
- [ ] Configure Redis connection pool
- [ ] Add pool exhaustion alerting
- [ ] Commit: "feat(perf): configure connection pooling"

---

## Test Strategy Per Sprint

### Unit Tests
- Each task includes at least 2 unit tests
- Mock external dependencies
- Target: 80% code coverage per new file

### Integration Tests
- One integration test per feature
- Use test database
- Target: 60% coverage of happy paths

### E2E Tests
- One E2E test per sprint
- Uses real browser (Playwright)
- Validates critical user journey

---

## Definition of Done

Each task is complete when:
1. ✅ Code implemented and follows project patterns
2. ✅ Unit tests pass locally
3. ✅ Integration tests pass (if applicable)
4. ✅ No linting errors (`make lint`)
5. ✅ Documentation updated (if API change)
6. ✅ Committed with conventional commit message
7. ✅ PR reviewed and approved
8. ✅ Merged to main
9. ✅ Deployed to staging (automatic)

---

## Priority Matrix

| Priority | Sprint | Business Value | Technical Risk | Demo |
|----------|--------|----------------|----------------|------|
| P0 | 25 | Fix broken tests | Low | Health check green |
| P0 | 25 | Remove legacy files | Low | Cleaner codebase |
| P0 | 26 | Complete OAuth | Medium | Real token stored |
| P1 | 26 | Core UI templates | Medium | Navigate all pages |
| P1 | 26.5 | Integration activation | High | Real HubSpot → Gmail flow |
| P1 | 27 | Queue + Campaigns | Medium | Filter, bulk approve, create campaign |
| P2 | 28 | Signal processing | High | Webhook → queue item |
| P2 | 29 | Email/voice | Medium | Voice-styled draft |
| P3 | 30 | Observability | Low | Sentry + Slack alerts |
| P3 | 31 | Security | Medium | Rate limiting + audit |
| P3 | 32 | Performance | High | <200ms P95 |

---

## Test Requirements Per Sprint

### Sprint 25 Tests
- [ ] `tests/unit/test_health.py` - connector health endpoint
- [ ] `tests/e2e/test_smoke.py` - Playwright smoke test

### Sprint 26 Tests  
- [ ] `tests/unit/test_oauth_storage.py` - token persistence
- [ ] `tests/e2e/test_navigation.py` - all pages load

### Sprint 26.5 Tests
- [ ] `tests/integration/test_hubspot_sync.py` - real API sync
- [ ] `tests/integration/test_full_flow.py` - contact → draft → send

### Sprint 27 Tests
- [ ] `tests/unit/test_queue_filtering.py` - filter logic
- [ ] `tests/unit/test_bulk_actions.py` - batch approve/reject
- [ ] `tests/e2e/test_campaign_wizard.py` - campaign creation

### Sprint 28 Tests
- [ ] `tests/unit/test_signal_dedup.py` - TTL logic
- [ ] `tests/integration/test_hubspot_webhook.py` - webhook handling
- [ ] `tests/unit/test_gmail_polling.py` - reply detection

### Sprint 29 Tests
- [ ] `tests/unit/test_voice_profiles.py` - tone generation
- [ ] `tests/e2e/test_draft_editing.py` - inline edit

### Sprint 30 Tests
- [ ] `tests/unit/test_metrics.py` - Prometheus format
- [ ] `tests/integration/test_sentry.py` - error capture

### Sprint 31 Tests
- [ ] `tests/security/test_rate_limiting.py` - 429 responses
- [ ] `tests/security/test_injection.py` - input sanitization

### Sprint 32 Tests
- [ ] `tests/performance/test_latency.py` - P95 < 200ms
- [ ] `tests/load/test_concurrent.py` - 100 users

---

## Appendix: Technical Debt Items

1. **Duplicate index definitions** in SQLAlchemy models (fixed in Sprint 25)
2. **Legacy Service Worker** causing cache issues (mitigated with kill switch)
3. **Inline HTML** in route handlers (migrate to templates in Sprint 26)
4. **Missing type hints** in older modules
5. **Inconsistent error handling** patterns
6. **Test fixtures not using factories**
7. **OAuth TODO in integrations_api.py** (fixed in Sprint 26.0.1)
8. **In-memory CONTACT_STORE** instead of PostgreSQL (fixed in Sprint 26.5.1)
9. **Campaigns.py (605 lines)** has no UI (fixed in Sprint 27.5-27.6)

---

## Appendix: Known TODOs in Codebase

| File | Line | TODO | Sprint |
|------|------|------|--------|
| `src/routes/integrations_api.py` | 157 | Query database for OAuth token | 26.0.1 |
| `src/hubspot_sync.py` | 42 | Persist to database | 26.5.1 |
| `src/agents/content/repurpose.py` | - | Web scraping not implemented | Backlog |
| `src/agents/content/social_scheduler.py` | - | LinkedIn scheduling not implemented | Backlog |
| `src/auto_approval.py` | - | Gmail API search for replies | 28.2 |
| `src/agents/fulfillment/client_health.py` | - | Real HubSpot data | 26.5.1 |

---

*Generated: 2026-01-26*
*Version: 2.1*
*Reviewed by: Subagent Analysis*
