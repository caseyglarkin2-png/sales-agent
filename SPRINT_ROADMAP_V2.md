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

## Sprint 33: OAuth Consolidation & Production Fix ✅ COMPLETE
**Goal**: Fix production OAuth authentication, consolidate callback routes, enable Google Workspace access.
**Demo**: User clicks "Sign in with Google" on production → successfully authenticates → lands on dashboard.

### Task 33.0: Verify Google Console OAuth Configuration ✅
**Description**: Ensure Google Cloud Console has correct redirect URIs.
**Files**: `docs/INTEGRATION_SETUP.md`
**Validation**: Google Console shows `https://web-production-a6ccf.up.railway.app/auth/callback`
**Acceptance Criteria**:
- [x] Verify production redirect URI in Google Console
- [x] Add both `/auth/callback` as authorized redirect URI
- [x] Remove any `/auth/google/callback` if present (consolidation)
- [x] Document in INTEGRATION_SETUP.md
- [x] Commit: "docs: update Google Console OAuth redirect URI"

### Task 33.1: Deprecate Legacy OAuth Callback Route ✅
**Description**: Add deprecation warning to `/auth/google/callback` and redirect to primary flow.
**Files**: `src/routes/auth_routes.py`
**Validation**: Hitting `/auth/google/callback` redirects with deprecation log
**Acceptance Criteria**:
- [x] Add deprecation warning log to `/auth/google/callback`
- [x] Redirect users to `/login` with message
- [x] Plan removal in Sprint 35
- [x] Commit: "chore(auth): deprecate legacy OAuth callback route"

### Task 33.2: Add Drive OAuth Scope to Web Auth ✅
**Description**: Request Drive read-only scope during OAuth to enable file access.
**Files**: `src/routes/web_auth.py`
**Validation**: OAuth consent shows "View files in Google Drive"
**Acceptance Criteria**:
- [x] Add `https://www.googleapis.com/auth/drive.readonly` to OAUTH_SCOPES
- [x] Test OAuth flow shows Drive permission request
- [x] Commit: "feat(oauth): add Drive read scope to OAuth flow"

### Task 33.3: Store Drive Token in OAuth Manager ✅
**Description**: Ensure Drive access token is stored and refreshable.
**Files**: `src/oauth_manager.py`, `src/models/oauth.py`
**Validation**: After OAuth, `oauth_tokens` table has entry with Drive scope
**Acceptance Criteria**:
- [x] Verify token storage includes all granted scopes
- [x] Add test: OAuth callback stores token with Drive scope
- [x] Commit: "feat(oauth): store Drive scope in OAuth tokens"

### Task 33.4: Create User-OAuth Drive Connector ✅
**Description**: Modify DriveConnector to use user OAuth tokens instead of service account.
**Files**: `src/connectors/drive.py`, `src/oauth_manager.py`
**Validation**: `drive.search_assets()` uses user's OAuth token
**Acceptance Criteria**:
- [x] Add `from_user_oauth(user_id)` class method to DriveConnector
- [x] Fetch token from `oauth_tokens` table
- [x] Build credentials from stored token
- [x] Refresh token if expired
- [x] Commit: "feat(drive): add user-OAuth based Drive connector"

---

## Sprint 34: Gemini Portal Foundation ✅ COMPLETE
**Goal**: Build interactive Gemini AI portal UI integrated into CaseyOS.
**Demo**: Navigate to `/caseyos/gemini` → chat with Gemini → get response with grounding.

### Task 34.1: Create Gemini Portal Template ✅
**Description**: Build Jinja2 template for Gemini AI chat interface.
**Files**: `src/templates/gemini.html`, `src/routes/ui.py`
**Validation**: GET `/caseyos/gemini` renders chat interface
**Acceptance Criteria**:
- [x] Create `gemini.html` extending `base.html`
- [x] Add chat message container with scroll
- [x] Add input field with send button
- [x] Add model selector dropdown (Flash 2.0, Pro 1.5, etc.)
- [x] Add "Gemini" to navigation bar
- [x] Commit: "feat(ui): add Gemini portal template"

### Task 34.2: Create Gemini Chat API Endpoint ✅
**Description**: Build API endpoint for Gemini chat interactions.
**Files**: `src/routes/gemini_api.py`, `src/main.py`
**Validation**: POST `/api/gemini/chat` returns AI response
**Acceptance Criteria**:
- [x] Create `src/routes/gemini_api.py` router
- [x] Add POST `/api/gemini/chat` endpoint
- [x] Accept: `{message, model, enable_grounding}`
- [x] Return: `{response, sources, model_used}`
- [x] Register router in main.py
- [x] Commit: "feat(api): add Gemini chat API endpoint"

### Task 34.3: Implement HTMX Chat Interface ✅
**Description**: Wire up chat UI with HTMX for real-time interaction.
**Files**: `src/templates/gemini.html`, `src/routes/gemini_api.py`
**Validation**: Type message → click send → response appears without reload
**Acceptance Criteria**:
- [x] Add HTMX POST for message submission
- [x] Append response to chat container
- [x] Show typing indicator while waiting
- [x] Clear input on successful send
- [x] Commit: "feat(ui): implement HTMX Gemini chat"

### Task 34.4: Add Grounding Toggle ✅
**Description**: Allow enabling Google Search grounding for factual responses.
**Files**: `src/templates/gemini.html`, `src/routes/gemini_api.py`
**Validation**: Enable grounding → response includes source links
**Acceptance Criteria**:
- [x] Add "Enable Grounding" toggle checkbox
- [x] Pass grounding flag to Gemini API
- [x] Display sources below response when grounded
- [x] Commit: "feat(gemini): add Google Search grounding toggle"

### Task 34.5: Add Chat History Persistence ✅
**Description**: Store chat history in session/database for conversation continuity.
**Files**: `src/models/gemini_chat.py`, `src/routes/gemini_api.py`
**Validation**: Refresh page → previous messages still visible
**Acceptance Criteria**:
- [x] Create `GeminiChatSession` and `GeminiChatMessage` models
- [x] Store messages in database per user session
- [x] Load history on page load
- [x] Add "New Chat" button to clear
- [x] Commit: "feat(gemini): add chat history persistence"

### Task 34.6: Add System Prompt Configuration ✅
**Description**: Allow configuring system prompts for different use cases.
**Files**: `src/templates/gemini.html`, `src/routes/gemini_api.py`
**Validation**: Select "Sales Assistant" → Gemini responds with sales focus
**Acceptance Criteria**:
- [x] Add system prompt dropdown (Sales, Research, Writer)
- [x] Define 3 default system prompts
- [x] Pass system prompt to Gemini API
- [x] Commit: "feat(gemini): add configurable system prompts"

---

## Sprint 35: Drive Integration & File Context ✅ COMPLETE
**Goal**: Enable Gemini to access and analyze Google Drive files.
**Demo**: Ask Gemini "Summarize the Q4 proposal for Acme Corp" → retrieves file → provides summary.

### Task 35.1: Create Drive Browser Template ✅
**Description**: Build UI for browsing Google Drive files.
**Files**: `src/templates/drive.html`, `src/routes/ui.py`
**Validation**: GET `/caseyos/drive` shows file browser
**Acceptance Criteria**:
- [x] Create `drive.html` extending `base.html`
- [x] Show folder tree on left
- [x] Show file list on right
- [x] Add "Drive" to navigation
- [x] Commit: "feat(ui): add Drive browser template"

### Task 35.2: Create Drive API Endpoints ✅
**Description**: Build API endpoints for Drive file operations.
**Files**: `src/routes/drive_api.py`, `src/main.py`
**Validation**: GET `/api/drive/files` returns user's files
**Acceptance Criteria**:
- [x] Create `src/routes/drive_api.py` router
- [x] Add GET `/api/drive/folders` - list folders
- [x] Add GET `/api/drive/files?folder_id=x` - list files
- [x] Add GET `/api/drive/file/{id}/content` - get file content
- [x] Register router in main.py
- [x] Commit: "feat(api): add Drive file API endpoints"

### Task 35.3: Implement Drive File Picker ✅
**Description**: Add file picker component for selecting Drive files.
**Files**: `src/templates/components/drive_picker.html`, `src/templates/gemini.html`
**Validation**: Click "Attach File" → modal shows Drive files → select → file attached
**Acceptance Criteria**:
- [x] Create reusable file picker partial template
- [x] Add HTMX-powered folder navigation
- [x] Support multi-file selection
- [x] Show file preview thumbnail
- [x] Commit: "feat(ui): add Drive file picker component"

### Task 35.4: Add File Content Extraction ✅
**Description**: Extract text content from various file types.
**Files**: `src/connectors/drive_extractor.py`
**Validation**: PDF, Docs, Sheets return extracted text
**Acceptance Criteria**:
- [x] Extract text from Google Docs (export as plain text)
- [x] Extract text from PDFs (using existing pdf extraction)
- [x] Extract text from Google Sheets (export as CSV)
- [x] Handle errors gracefully with fallback
- [x] Commit: "feat(drive): add multi-format content extraction"

### Task 35.5: Integrate Drive Context with Gemini ✅
**Description**: Allow Gemini to reference attached Drive files in responses.
**Files**: `src/routes/gemini_api.py`, `src/connectors/gemini.py`
**Validation**: Attach file → ask question → Gemini references file content
**Acceptance Criteria**:
- [x] Accept `file_ids` in chat request
- [x] Fetch and extract file content
- [x] Include in Gemini prompt as context
- [x] Cite file in response
- [x] Commit: "feat(gemini): integrate Drive file context"

### Task 35.6: Add Drive Search in Gemini ✅
**Description**: Enable natural language Drive search from Gemini chat.
**Files**: `src/routes/gemini_api.py`, `src/connectors/drive.py`
**Validation**: Ask "Find the Acme proposal" → Gemini searches Drive → returns matches
**Acceptance Criteria**:
- [x] Detect search intent in message
- [x] Call `drive.search_assets()` with extracted query
- [x] Return file list in response
- [x] Allow clicking file to attach
- [x] Commit: "feat(gemini): add natural language Drive search"

---

## Sprint 36: Jarvis Integration & Agent Orchestration ✅ COMPLETE
**Goal**: Connect Gemini Portal and Drive to Jarvis for intelligent routing.
**Demo**: Ask "Draft an email to the CEO of Acme about our Q4 proposal" → Jarvis fetches proposal → drafts email.

### Task 36.1: Add Gemini Tool Calling Support ✅
**Description**: Implement function/tool calling for Gemini to invoke agents.
**Files**: `src/connectors/gemini.py`
**Validation**: Gemini can call defined tools and receive results
**Acceptance Criteria**:
- [x] Add tool definitions to Gemini API calls
- [x] Define tools: `search_drive`, `draft_email`, `get_contact`, `search_hubspot`
- [x] Parse tool call responses
- [x] Execute tool and return result
- [x] Commit: "feat(gemini): add function/tool calling support"

### Task 36.2: Create Jarvis-Gemini Bridge ✅
**Description**: Route Gemini tool calls to Jarvis for agent execution.
**Files**: `src/agents/jarvis.py`, `src/routes/gemini_api.py`
**Validation**: Gemini tool call → Jarvis routes to correct agent → result returned
**Acceptance Criteria**:
- [x] Add `handle_tool_call(tool_name, params)` to Jarvis
- [x] Map tool names to agent methods
- [x] Return structured results
- [x] Log all tool executions
- [x] Commit: "feat(jarvis): add Gemini tool call routing"

### Task 36.3: Add Email Draft Tool ✅
**Description**: Enable Gemini to draft emails through Jarvis.
**Files**: `src/agents/jarvis.py`, `src/connectors/gemini.py`
**Validation**: "Draft email to john@acme.com about project update" → draft created
**Acceptance Criteria**:
- [x] Define `draft_email` tool with parameters
- [x] Route to DraftWriterAgent
- [x] Create draft in command queue
- [x] Return draft preview to Gemini
- [x] Commit: "feat(jarvis): add email draft tool"

### Task 36.4: Add HubSpot Lookup Tool ✅
**Description**: Enable Gemini to query HubSpot contacts and deals.
**Files**: `src/agents/jarvis.py`, `src/connectors/hubspot.py`
**Validation**: "What's the status of Acme Corp deal?" → returns deal info
**Acceptance Criteria**:
- [x] Define `search_hubspot` tool
- [x] Search contacts by name/email
- [x] Search deals by company/stage
- [x] Return formatted results
- [x] Commit: "feat(jarvis): add HubSpot lookup tool"

### Task 36.5: Add Calendar Integration Tool ✅
**Description**: Enable Gemini to check and create calendar events.
**Files**: `src/agents/jarvis.py`, `src/connectors/calendar.py`
**Validation**: "Schedule a call with Acme Corp next Tuesday at 2pm" → event created
**Acceptance Criteria**:
- [x] Define `check_calendar` and `create_event` tools
- [x] Query free/busy for scheduling
- [x] Create events with attendees
- [x] Return confirmation
- [x] Commit: "feat(jarvis): add Calendar integration tools"

### Task 36.6: Add Multi-Step Workflow Execution ✅
**Description**: Enable Jarvis to execute multi-step workflows from Gemini.
**Files**: `src/agents/jarvis.py`, `src/routes/gemini_api.py`
**Validation**: "Research Acme, find proposal, draft follow-up email" → executes all steps
**Acceptance Criteria**:
- [x] Parse multi-step intents
- [x] Execute agents in sequence
- [x] Pass context between steps
- [x] Report progress in chat
- [x] Commit: "feat(jarvis): add multi-step workflow execution"

---

## Sprint 37: Deep Research & Workspace Intelligence
**Goal**: Enable AI-powered deep research across Drive and external sources.
**Demo**: "Research competitive landscape for enterprise CRM" → comprehensive report with citations.

### Task 37.1: Implement Deep Research Agent
**Description**: Create agent for comprehensive multi-source research.
**Files**: `src/agents/research/research_deep.py`
**Validation**: Research query → multi-source findings → structured report
**Acceptance Criteria**:
- [ ] Search Drive for internal docs
- [ ] Use Gemini grounding for web research
- [ ] Synthesize findings
- [ ] Generate formatted report
- [ ] Commit: "feat(research): implement deep research agent"

### Task 37.2: Add Research UI Component
**Description**: Build dedicated research interface in Gemini portal.
**Files**: `src/templates/gemini.html`, `src/routes/gemini_api.py`
**Validation**: Click "Deep Research" → opens research panel → shows progress
**Acceptance Criteria**:
- [ ] Add "Research Mode" toggle
- [ ] Show research progress steps
- [ ] Display sources as they're found
- [ ] Render final report with sections
- [ ] Commit: "feat(ui): add deep research interface"

### Task 37.3: Add Workspace Context Memory
**Description**: Store and recall context about workspace contents.
**Files**: `src/services/memory_service.py`, `src/connectors/drive.py`
**Validation**: "What was in the Acme proposal we discussed last week?" → recalls context
**Acceptance Criteria**:
- [ ] Index Drive files in memory store
- [ ] Store conversation context
- [ ] Implement semantic search for recall
- [ ] Update index on file changes
- [ ] Commit: "feat(memory): add workspace context memory"

### Task 37.4: Add Citation and Source Tracking
**Description**: Track and display sources for all AI-generated content.
**Files**: `src/templates/components/citations.html`, `src/routes/gemini_api.py`
**Validation**: Response with sources → clickable citation links
**Acceptance Criteria**:
- [ ] Parse Gemini grounding metadata
- [ ] Render inline citations [1], [2]
- [ ] Show source list at bottom
- [ ] Link Drive files to viewer
- [ ] Commit: "feat(ui): add citation and source tracking"

### Task 37.5: Add Research Export
**Description**: Export research results to Google Docs or download.
**Files**: `src/routes/gemini_api.py`, `src/connectors/drive.py`
**Validation**: Click "Export" → creates Google Doc with research
**Acceptance Criteria**:
- [ ] Format research as Google Doc
- [ ] Create in user's Drive
- [ ] Provide download as PDF option
- [ ] Include all citations
- [ ] Commit: "feat(research): add export to Google Docs"

---

## Sprint 38: Agent Dashboard & Orchestration UI
**Goal**: Build comprehensive agent management and monitoring UI.
**Demo**: View all agents, their status, trigger manual executions, see orchestration flow.

### Task 38.1: Create Agent Registry
**Description**: Centralized registry of all available agents.
**Files**: `src/agents/registry.py`, `src/agents/__init__.py`
**Validation**: `AgentRegistry.list_agents()` returns all agents with metadata
**Acceptance Criteria**:
- [ ] Create AgentRegistry singleton
- [ ] Auto-discover agents from `src/agents/`
- [ ] Include: name, description, capabilities, status
- [ ] Add health check method per agent
- [ ] Commit: "feat(agents): create centralized agent registry"

### Task 38.2: Create Agent Hub Template
**Description**: Build comprehensive agent management UI.
**Files**: `src/templates/agents.html`, `src/routes/ui.py`
**Validation**: GET `/caseyos/agents` shows all agents with controls
**Acceptance Criteria**:
- [ ] List all registered agents
- [ ] Show status indicators (active/idle/error)
- [ ] Display last execution time
- [ ] Add "Run Now" button per agent
- [ ] Commit: "feat(ui): create agent hub template"

### Task 38.3: Add Agent Execution History
**Description**: Track and display agent execution logs.
**Files**: `src/models/agent_execution.py`, `src/routes/agents_api.py`
**Validation**: View agent → see history of recent executions
**Acceptance Criteria**:
- [ ] Create AgentExecution model
- [ ] Log: start_time, end_time, status, input, output
- [ ] Display in agent detail view
- [ ] Add filtering by date/status
- [ ] Commit: "feat(agents): add execution history tracking"

### Task 38.4: Add Manual Agent Trigger API
**Description**: API to manually trigger agent execution.
**Files**: `src/routes/agents_api.py`
**Validation**: POST `/api/agents/{name}/execute` triggers agent
**Acceptance Criteria**:
- [ ] Create execute endpoint
- [ ] Accept context parameters
- [ ] Return execution ID
- [ ] Support async execution via Celery
- [ ] Commit: "feat(api): add manual agent trigger endpoint"

### Task 38.5: Add Orchestration Flow Visualization
**Description**: Visualize Jarvis orchestration and agent interactions.
**Files**: `src/templates/agents.html`, `src/routes/agents_api.py`
**Validation**: View shows workflow diagram of agent interactions
**Acceptance Criteria**:
- [ ] Add visual flow diagram component
- [ ] Show: Signal → Jarvis → Agent → Action
- [ ] Highlight active executions
- [ ] Log inter-agent communications
- [ ] Commit: "feat(ui): add orchestration flow visualization"

---

## Sprint 39A: Critical Hotfix - Gemini CSRF Fix
**Goal**: Fix blocking CSRF issue preventing Gemini chat from working.
**Demo**: User sends message in Gemini portal → receives AI response (no more 403 error).
**Priority**: P0 - Deploy immediately, 30-minute fix.

> **Note**: This is an emergency hotfix sprint. Complete and deploy before continuing.

### Task 39A.1: Exempt Gemini API from CSRF Middleware
**Description**: Add `/api/gemini` and `/api/drive` to CSRF exclusion list.
**Files**: `src/security/csrf.py`
**Validation**: `curl -X POST /api/gemini/chat` returns AI response, not 403
**Tests**: `tests/unit/test_csrf_exclusions.py`, `tests/e2e/test_gemini_chat_flow.py`
**Acceptance Criteria**:
- [ ] Add `/api/gemini` to `exclude_path()` function
- [ ] Add `/api/drive` to exclusion (same session-based auth)
- [ ] Add comment explaining why (HTMX sends cookies, session-auth sufficient)
- [ ] Write test: `test_gemini_excluded_from_csrf`
- [ ] Commit: "fix(csrf): exempt Gemini and Drive APIs from CSRF check"

### Task 39A.2: Add Agents Navigation Link (Quick Win)
**Description**: Add Agents link to navigation bar.
**Files**: `src/templates/base.html`
**Validation**: Navigation shows "🤖 Agents" link
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Add nav link placeholder to `/caseyos/agents`
- [ ] Use robot emoji: 🤖 Agents
- [ ] Position after Drive in nav order
- [ ] Create minimal placeholder route that returns 501 "Coming Soon"
- [ ] Commit: "feat(ui): add agents navigation placeholder"

---

## Sprint 39B: Contact Enrichment & Memory
**Goal**: Show WHO drafts are for and enable conversation memory in Gemini.
**Demo**: Queue items show "👤 John Smith (john@acme.com)". Gemini remembers previous messages.

> **Note**: Supersedes original Sprint 39 tasks 39.3-39.5

### Task 39B.1: Wire Existing MemoryService to Gemini Chat
**Description**: Replace in-memory chat_sessions dict with existing MemoryService.
**Files**: `src/routes/gemini_api.py`, `src/services/memory_service.py`
**Validation**: Chat history persists across page refreshes for same session
**Tests**: `tests/unit/test_gemini_memory.py`
**Acceptance Criteria**:
- [ ] Import and use existing `MemoryService` 
- [ ] Store messages with `add_message(session_id, message)`
- [ ] Retrieve with `get_recent_messages(session_id, limit=10)`
- [ ] Pass history to Gemini API for context
- [ ] Commit: "feat(gemini): wire existing MemoryService for conversation history"

### Task 39B.2: Add Contact Name to Queue Item Response
**Description**: Enrich queue items with HubSpot contact name and email.
**Files**: `src/routes/command_queue.py`, `src/models/command_queue.py`
**Validation**: GET `/api/command-queue/today` returns items with `contact_name`, `contact_email`
**Tests**: `tests/unit/test_queue_enrichment.py`
**Acceptance Criteria**:
- [ ] Add `contact_name` and `contact_email` to `CommandQueueItemResponse`
- [ ] Extract from `action_context` if present
- [ ] Return empty string if not available (graceful degradation)
- [ ] Commit: "feat(queue): add contact name/email to queue item response"

### Task 39B.3: Background Contact Enrichment Task
**Description**: Celery task to fetch contact details from HubSpot for queue items.
**Files**: `src/tasks/enrichment.py`, `src/celery_app.py`
**Validation**: Queue items with `contact_id` get enriched with name/email
**Tests**: `tests/unit/test_contact_enrichment_task.py`
**Acceptance Criteria**:
- [ ] Create `enrich_queue_contacts` Celery task
- [ ] Fetch contact from HubSpot by ID
- [ ] Store `firstname`, `lastname`, `email` in `action_context`
- [ ] Add to beat schedule (run every 5 minutes)
- [ ] Commit: "feat(tasks): add background contact enrichment"

### Task 39B.4: Display Contact Info in Queue UI
**Description**: Update queue template to show contact name and email.
**Files**: `src/templates/queue.html`
**Validation**: Queue items display "👤 John Smith (john@acme.com)"
**Tests**: Visual verification in production
**Acceptance Criteria**:
- [ ] Update queue-meta section to show contact_name
- [ ] Show email on hover or in parentheses
- [ ] Show company name if available
- [ ] Graceful fallback if no contact info
- [ ] Commit: "feat(ui): display contact info in queue items"

### Task 39B.5: Add HubSpot Contact Card Component
**Description**: Reusable component showing full HubSpot contact details.
**Files**: `src/templates/components/hubspot_contact.html`, `src/routes/command_queue.py`
**Validation**: Contact card shows photo, name, title, company, recent activity
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Create partial template for contact card
- [ ] Fetch contact details via HubSpot API
- [ ] Show: photo, name, title, company, email
- [ ] Show recent activity (last email, last meeting)
- [ ] Commit: "feat(ui): add HubSpot contact card component"

---

## Sprint 40: Draft Editing & Queue Detail
**Goal**: Enable editing drafts before sending, with full context view.
**Demo**: Click queue item → see full draft with HubSpot context → edit subject/body → send.

### Task 40.1: Create Queue Item Detail Template
**Description**: Build full-page detail view for queue items.
**Files**: `src/templates/queue_detail.html`, `src/routes/ui.py`
**Validation**: GET `/caseyos/queue/{id}` shows full item detail
**Tests**: Visual verification, route returns 200
**Acceptance Criteria**:
- [ ] Create `queue_detail.html` extending `base.html`
- [ ] Show full draft content (subject, body)
- [ ] Display HubSpot contact card
- [ ] Show deal stage and pipeline if linked
- [ ] Commit: "feat(ui): create queue item detail page"

### Task 40.2: Add Inline Draft Editor
**Description**: Add editable fields for draft subject and body.
**Files**: `src/templates/queue_detail.html`
**Validation**: Click edit → fields become editable → save updates draft
**Tests**: `tests/e2e/test_draft_editing.py`
**Acceptance Criteria**:
- [ ] Add edit button that toggles edit mode
- [ ] Subject becomes text input
- [ ] Body becomes textarea with markdown preview
- [ ] Save button calls PATCH endpoint
- [ ] Commit: "feat(ui): add inline draft editor"

### Task 40.3: Create Draft Update API Endpoint
**Description**: API to update draft content (subject, body).
**Files**: `src/routes/command_queue.py`
**Validation**: PATCH `/api/command-queue/{id}/draft` updates draft content
**Tests**: `tests/unit/test_draft_update.py`
**Acceptance Criteria**:
- [ ] Create `/api/command-queue/{id}/draft` PATCH endpoint
- [ ] Accept `subject` and `body` fields
- [ ] Validate body length (min 50 chars)
- [ ] Update `action_context` with new content
- [ ] Commit: "feat(api): add draft content update endpoint"

### Task 40.4: Add HubSpot Contact Card Component
**Description**: Reusable component showing full HubSpot contact details.
**Files**: `src/templates/components/hubspot_contact.html`, `src/routes/command_queue.py`
**Validation**: Contact card shows photo, name, title, company, recent activity
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Create partial template for contact card
- [ ] Fetch contact details via HubSpot API
- [ ] Show: photo, name, title, company, email
- [ ] Show recent activity (last email, last meeting)
- [ ] Commit: "feat(ui): add HubSpot contact card component"

### Task 40.5: Add Deal Context Panel
**Description**: Show linked deal information in queue detail.
**Files**: `src/templates/queue_detail.html`, `src/routes/command_queue.py`
**Validation**: If item has `deal_id`, show deal stage, amount, close date
**Tests**: `tests/unit/test_deal_context.py`
**Acceptance Criteria**:
- [ ] Add API endpoint to fetch deal details
- [ ] Display deal stage with pipeline visualization
- [ ] Show deal amount and expected close date
- [ ] Show associated contacts
- [ ] Commit: "feat(ui): add deal context panel"

### Task 40.6: Add Send with Edits Button
**Description**: Button to approve and send the edited draft.
**Files**: `src/templates/queue_detail.html`, `src/routes/command_queue.py`
**Validation**: Click "Send with Edits" → draft sent with modifications
**Tests**: `tests/e2e/test_send_edited_draft.py`
**Acceptance Criteria**:
- [ ] Add "Send with Edits" button
- [ ] Save edits before sending
- [ ] Call existing execute endpoint
- [ ] Show success/error notification
- [ ] Commit: "feat(ui): add send with edits button"

---

## Sprint 41: Agent Discovery & Surfacing
**Goal**: Expose all 38 built agents in the UI for discovery and invocation.
**Demo**: User navigates to Agents Hub → sees all agents by domain → clicks "Try" → opens in Gemini with agent selected.

### Task 41.1: Create Agent Registry
**Description**: Centralized registry that auto-discovers all agents.
**Files**: `src/agents/registry.py`
**Validation**: `AgentRegistry.list_all()` returns metadata for all 38 agents
**Tests**: `tests/unit/test_agent_registry.py`
**Acceptance Criteria**:
- [ ] Create `AgentRegistry` class with singleton pattern
- [ ] Scan `src/agents/` directories for agent classes
- [ ] Extract: name, description, domain, capabilities from docstrings
- [ ] Add `get_by_domain()` method for filtering
- [ ] Commit: "feat(agents): create centralized agent registry"

### Task 41.2: Add Agent Metadata to Existing Agents
**Description**: Add standardized metadata to all agent classes.
**Files**: All agent files in `src/agents/`
**Validation**: Each agent has `AGENT_META` dict with name, description, domain
**Tests**: `tests/unit/test_agent_metadata.py` - verify all agents have metadata
**Acceptance Criteria**:
- [ ] Define `AGENT_META` schema
- [ ] Add to all specialized agents
- [ ] Add to all content agents
- [ ] Add to all fulfillment agents
- [ ] Add to all data hygiene agents
- [ ] Commit: "feat(agents): add standardized metadata to all agents"

### Task 41.3: Create Agents Hub Template
**Description**: Build agent discovery and management UI.
**Files**: `src/templates/agents.html`, `src/routes/ui.py`
**Validation**: GET `/caseyos/agents` shows all agents grouped by domain
**Tests**: Visual verification, route returns 200
**Acceptance Criteria**:
- [ ] Create `agents.html` extending `base.html`
- [ ] Group agents by domain (Sales, Content, Fulfillment, etc.)
- [ ] Show agent card with name, description, status
- [ ] Add "Try in Gemini" button per agent
- [ ] Commit: "feat(ui): create agents hub page"

### Task 41.4: Add Agents Navigation Link
**Description**: Add Agents to main navigation bar.
**Files**: `src/templates/base.html`
**Validation**: Navigation shows "🤖 Agents" link between Gemini and Drive
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Add nav link to `/caseyos/agents`
- [ ] Use robot emoji: 🤖 Agents
- [ ] Position between Gemini and Drive
- [ ] Commit: "feat(ui): add agents to navigation"

### Task 41.5: Create Agents API Endpoints
**Description**: API to list agents and get agent details.
**Files**: `src/routes/agents_api.py`, `src/main.py`
**Validation**: GET `/api/agents` returns all agents with metadata
**Tests**: `tests/unit/test_agents_api.py`
**Acceptance Criteria**:
- [ ] Create `/api/agents` GET endpoint (list all)
- [ ] Create `/api/agents/{name}` GET endpoint (single agent)
- [ ] Create `/api/agents/domains` GET endpoint (list domains)
- [ ] Register router in main.py
- [ ] Commit: "feat(api): add agents discovery endpoints"

### Task 41.6: Add Agent Selector to Gemini Portal
**Description**: Dropdown to select specific agent in Gemini chat.
**Files**: `src/templates/gemini.html`, `src/routes/gemini_api.py`
**Validation**: Select agent → Jarvis routes to that agent specifically
**Tests**: `tests/e2e/test_agent_selection.py`
**Acceptance Criteria**:
- [ ] Add agent selector dropdown (visible when Jarvis Mode enabled)
- [ ] Group options by domain
- [ ] Pass selected agent to `/api/gemini/jarvis/chat`
- [ ] Update Jarvis to respect explicit agent selection
- [ ] Commit: "feat(ui): add agent selector to Gemini portal"

---

## Sprint 42: Agent Orchestration & Execution
**Goal**: Enable manual agent execution and track execution history.
**Demo**: Click "Run Now" on agent → see execution in progress → view results and history.

### Task 42.1: Create Agent Execution Model
**Description**: Database model to track agent executions.
**Files**: `src/models/agent_execution.py`, migration file
**Validation**: Can create and query AgentExecution records
**Tests**: `tests/unit/test_agent_execution_model.py`
**Acceptance Criteria**:
- [ ] Create `AgentExecution` model with: id, agent_name, status, input, output, duration, timestamps
- [ ] Add migration for `agent_executions` table
- [ ] Index by `agent_name` and `created_at`
- [ ] Commit: "feat(models): add agent execution tracking model"

### Task 42.2: Add Manual Agent Trigger Endpoint
**Description**: API to manually execute an agent with given context.
**Files**: `src/routes/agents_api.py`
**Validation**: POST `/api/agents/{name}/execute` triggers agent
**Tests**: `tests/unit/test_agent_trigger.py`
**Acceptance Criteria**:
- [ ] Create execute endpoint accepting context JSON
- [ ] Validate agent exists
- [ ] Create AgentExecution record
- [ ] Return execution_id for tracking
- [ ] Commit: "feat(api): add manual agent trigger endpoint"

### Task 42.3: Add Async Agent Execution via Celery
**Description**: Execute agents asynchronously via Celery task.
**Files**: `src/tasks/agent_executor.py`, `src/celery_app.py`
**Validation**: Agent execution runs in background, status updates visible
**Tests**: `tests/unit/test_agent_executor_task.py`
**Acceptance Criteria**:
- [ ] Create `execute_agent` Celery task
- [ ] Update AgentExecution status: pending → running → success/failed
- [ ] Capture output and errors
- [ ] Store execution duration
- [ ] Commit: "feat(tasks): add async agent execution task"

### Task 42.4: Add Execution History to Agent Hub
**Description**: Show recent executions for each agent.
**Files**: `src/templates/agents.html`, `src/routes/agents_api.py`
**Validation**: Agent card shows last 5 executions with status
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Add GET `/api/agents/{name}/history` endpoint
- [ ] Show mini timeline of recent executions
- [ ] Color-code by status (green=success, red=failed)
- [ ] Show execution time and duration
- [ ] Commit: "feat(ui): add execution history to agent hub"

### Task 42.5: Add Agent Detail Modal
**Description**: Modal showing full agent details and capabilities.
**Files**: `src/templates/agents.html`
**Validation**: Click agent → modal shows description, capabilities, history
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Create modal component
- [ ] Show full description
- [ ] List all capabilities/methods
- [ ] Show recent execution results
- [ ] Add "Run Now" button in modal
- [ ] Commit: "feat(ui): add agent detail modal"

### Task 42.6: Add Real-Time Execution Status
**Description**: Show execution progress in real-time via SSE or polling.
**Files**: `src/routes/agents_api.py`, `src/templates/agents.html`
**Validation**: Start execution → see status updates live
**Tests**: `tests/e2e/test_execution_status.py`
**Acceptance Criteria**:
- [ ] Add `/api/agents/executions/{id}/status` endpoint
- [ ] Poll every 2 seconds for status updates
- [ ] Show spinner while running
- [ ] Display result when complete
- [ ] Commit: "feat(ui): add real-time execution status"

---

## Sprint 43: Gemini-Agent Integration & Power Features
**Goal**: Enable Gemini to use all agents seamlessly with context awareness.
**Demo**: "Research Acme Corp, draft a proposal, and schedule a meeting" → all three agents execute in sequence.

### Task 43.1: Expand Jarvis Tool Definitions
**Description**: Add tool definitions for all exposed agents.
**Files**: `src/agents/jarvis.py`
**Validation**: `get_tool_definitions()` returns 20+ tools
**Tests**: `tests/unit/test_jarvis_tools_complete.py`
**Acceptance Criteria**:
- [ ] Add tools for content agents (repurpose, social_scheduler)
- [ ] Add tools for fulfillment agents (deliverable_tracker, approval_gateway)
- [ ] Add tools for data hygiene (duplicate_watcher, enrichment)
- [ ] Add tools for ops (competitor_watch, revenue_ops)
- [ ] Commit: "feat(jarvis): expand tool definitions for all agents"

### Task 43.2: Add Context Passing Between Agents
**Description**: Enable agents to pass context to subsequent agents in workflow.
**Files**: `src/agents/jarvis.py`, `src/services/context_service.py`
**Validation**: Research agent output flows into draft_email agent
**Tests**: `tests/unit/test_context_passing.py`
**Acceptance Criteria**:
- [ ] Create `ContextService` for workflow state
- [ ] Store intermediate results with TTL
- [ ] Pass context to next agent in chain
- [ ] Clean up context after workflow complete
- [ ] Commit: "feat(agents): add context passing between agents"

### Task 43.3: Add Workflow Templates
**Description**: Pre-defined multi-agent workflows for common tasks.
**Files**: `src/agents/workflows.py`, `src/routes/gemini_api.py`
**Validation**: "Use account research workflow" → executes 3-agent sequence
**Tests**: `tests/unit/test_workflow_templates.py`
**Acceptance Criteria**:
- [ ] Create WorkflowTemplate model
- [ ] Define: Account Research, New Deal, Content Campaign workflows
- [ ] Add `/api/gemini/workflows` endpoint
- [ ] Show workflow selector in Gemini UI
- [ ] Commit: "feat(agents): add pre-defined workflow templates"

### Task 43.4: Add Progress Reporting for Multi-Step
**Description**: Show progress as Jarvis executes multi-agent workflows.
**Files**: `src/templates/gemini.html`, `src/routes/gemini_api.py`
**Validation**: Multi-step request → shows "Step 1/3: Researching..." updates
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Add progress indicator component
- [ ] Stream status updates via SSE
- [ ] Show current agent and step number
- [ ] Display intermediate results as they complete
- [ ] Commit: "feat(ui): add multi-step progress reporting"

### Task 43.5: Add Conversation Memory
**Description**: Gemini remembers conversation context across messages.
**Files**: `src/routes/gemini_api.py`, `src/models/gemini_chat.py`
**Validation**: "What was that company's revenue?" refers to previous message
**Tests**: `tests/unit/test_conversation_memory.py`
**Acceptance Criteria**:
- [ ] Create GeminiChatSession model
- [ ] Store last 10 messages per session
- [ ] Pass history to Gemini API
- [ ] Clear on "New Chat"
- [ ] Commit: "feat(gemini): add conversation memory"

### Task 43.6: Add Quick Action Buttons
**Description**: Pre-defined quick actions for common tasks.
**Files**: `src/templates/gemini.html`
**Validation**: Click "Draft Follow-up" → pre-fills prompt template
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Add quick action bar above chat input
- [ ] Define 5 common actions: Research, Draft Email, Check Calendar, Create Proposal, Analyze Account
- [ ] Each button pre-fills prompt with template
- [ ] Style as pill buttons
- [ ] Commit: "feat(ui): add quick action buttons to Gemini"

---

## Test Strategy Per Sprint

### Sprint 39 Tests
- [ ] `tests/unit/test_csrf_exclusions.py` - Gemini/Drive paths excluded
- [ ] `tests/unit/test_csrf_cookie.py` - cookie persistence
- [ ] `tests/unit/test_queue_enrichment.py` - contact data in response
- [ ] `tests/unit/test_contact_enrichment_task.py` - background task
- [ ] `tests/e2e/test_gemini_chat.py` - full chat flow works

### Sprint 40 Tests
- [ ] `tests/unit/test_draft_update.py` - draft content update
- [ ] `tests/unit/test_deal_context.py` - deal details fetched
- [ ] `tests/e2e/test_draft_editing.py` - inline edit flow
- [ ] `tests/e2e/test_send_edited_draft.py` - send with modifications

### Sprint 41 Tests
- [ ] `tests/unit/test_agent_registry.py` - auto-discovery
- [ ] `tests/unit/test_agent_metadata.py` - all agents have metadata
- [ ] `tests/unit/test_agents_api.py` - list and get endpoints
- [ ] `tests/e2e/test_agent_selection.py` - Gemini agent routing

### Sprint 42 Tests
- [ ] `tests/unit/test_agent_execution_model.py` - model CRUD
- [ ] `tests/unit/test_agent_trigger.py` - execute endpoint
- [ ] `tests/unit/test_agent_executor_task.py` - Celery task
- [ ] `tests/e2e/test_execution_status.py` - real-time updates

### Sprint 43 Tests
- [ ] `tests/unit/test_jarvis_tools_complete.py` - 20+ tools defined
- [ ] `tests/unit/test_context_passing.py` - inter-agent context
- [ ] `tests/unit/test_workflow_templates.py` - template execution
- [ ] `tests/unit/test_conversation_memory.py` - history persistence
- [ ] `tests/e2e/test_multi_step_workflow.py` - full workflow execution

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
10. **Dual OAuth callback routes** - `/auth/callback` and `/auth/google/callback` (consolidated in Sprint 33)
11. **DriveConnector uses service account** - needs user OAuth (fixed in Sprint 33.4)
12. **Gemini API blocked by CSRF** - needs exclusion (Sprint 39.1)
13. **Queue items missing contact context** - needs enrichment (Sprint 39.3-39.5)
14. **38 agents not exposed in UI** - needs Agent Hub (Sprint 41)
15. **No draft editing capability** - needs detail page (Sprint 40)

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
| `src/connectors/drive.py` | - | Use user OAuth not service account | 33.4 |
| `src/routes/auth_routes.py` | 742 | Deprecate `/auth/google/callback` | 33.1 |
| `src/routes/gemini_api.py` | - | Create Gemini chat API | 34.2 |
| `src/agents/registry.py` | - | Create agent registry | 38.1 |

---

*Generated: 2026-01-27*
*Version: 2.2*
*Updated: Added Sprints 33-38 for OAuth fix, Gemini Portal, Drive integration, Jarvis weaving*
