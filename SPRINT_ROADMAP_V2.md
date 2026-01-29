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

## Sprint 44: Voice Training UI & Missing Route Wiring ✅ COMPLETE
**Goal**: Wire Voice Training UI and surface all unregistered routes.
**Demo**: `/caseyos/voice-training` and `/caseyos/voice-profiles` show functional UI.
**Status**: Completed 2026-01-28

### Task 44.1: Wire Unregistered Routes ✅
**Files**: `src/main.py`
**Wired**: content_repurpose_routes, customer_health_routes, pricing_engine_routes, proposal_generator_routes

### Task 44.2: Voice Training UI ✅
**Files**: `src/templates/voice_training.html`, `src/routes/ui.py`
**Features**: Multi-source upload (File, Drive, HubSpot, YouTube)

### Task 44.3: Voice Profiles UI ✅
**Files**: `src/templates/voice_profiles.html`, `src/routes/ui.py`
**Features**: Profile CRUD, active profile selector, settings modal

### Task 44.4: Navigation Update ✅
**Files**: `src/templates/base.html`
**Added**: 🎭 Voice tab pointing to voice-training

---

## Sprint 45: Memory & Context Visibility
**Goal**: Surface Jarvis memory system in CaseyOS UI for debugging and insight.
**Demo**: `/caseyos/memory` shows conversation sessions, context, and search.

### Task 45.1: Memory Sessions List Page
**Description**: Create UI to view all memory sessions with metadata.
**Files**: `src/templates/memory.html`, `src/routes/ui.py`
**Validation**: `/caseyos/memory` shows paginated session list
**Tests**: `tests/unit/test_memory_ui.py`
**Acceptance Criteria**:
- [ ] Create `memory.html` extending base.html
- [ ] Show session ID, created_at, message count, last_updated
- [ ] Filter by date range
- [ ] Add route `/caseyos/memory` with `active_tab="memory"`
- [ ] Commit: "feat(ui): add memory sessions list page"

### Task 45.2: Memory Session Detail View
**Description**: Drill into a session to see all stored context and messages.
**Files**: `src/templates/memory_detail.html`, `src/routes/ui.py`
**Validation**: Click session → see full context tree
**Tests**: `tests/unit/test_memory_detail.py`
**Acceptance Criteria**:
- [ ] Create detail template with JSON tree view
- [ ] Show all messages in session
- [ ] Display context variables
- [ ] Add route `/caseyos/memory/{session_id}`
- [ ] Commit: "feat(ui): add memory session detail view"

### Task 45.3: Memory Search UI
**Description**: Search across all memory for specific context/keywords.
**Files**: `src/templates/memory.html`
**Validation**: Type query → see matching context entries
**Tests**: `tests/unit/test_memory_search_ui.py`
**Acceptance Criteria**:
- [ ] Add search input with HTMX
- [ ] Call `/api/memory/search` endpoint
- [ ] Display results with session links
- [ ] Highlight matched terms
- [ ] Commit: "feat(ui): add memory search functionality"

### Task 45.4: Navigation Update - Memory Tab
**Description**: Add Memory tab to CaseyOS navigation.
**Files**: `src/templates/base.html`
**Validation**: 🧠 Memory tab visible in nav
**Acceptance Criteria**:
- [ ] Add Memory tab between Overview and Voice
- [ ] Set active_tab="memory" styling
- [ ] Commit: "feat(ui): add Memory tab to navigation"

---

## Sprint 46: Integrations Hub UI
**Goal**: Surface integration status and connection management in CaseyOS.
**Demo**: `/caseyos/integrations` shows all connected apps with health status.

### Task 46.1: Integrations Status Page
**Description**: Create UI showing all integration connection statuses.
**Files**: `src/templates/integrations.html`, `src/routes/ui.py`
**Validation**: `/caseyos/integrations` shows Gmail, HubSpot, Drive status
**Tests**: `tests/unit/test_integrations_ui.py`
**Acceptance Criteria**:
- [ ] Create `integrations.html` extending base.html
- [ ] Call `/api/integrations/status` for data
- [ ] Show connection status with icons (✅/❌/⚠️)
- [ ] Display last sync time per integration
- [ ] Add route `/caseyos/integrations`
- [ ] Commit: "feat(ui): add integrations status page"

### Task 46.2: Integration Connect/Disconnect Actions
**Description**: Enable connecting/disconnecting integrations via UI.
**Files**: `src/templates/integrations.html`
**Validation**: Click Connect → OAuth flow → returns with connected status
**Tests**: `tests/unit/test_integration_actions.py`
**Acceptance Criteria**:
- [ ] Add Connect button for disconnected integrations
- [ ] Add Disconnect button with confirmation modal
- [ ] Show spinner during OAuth redirect
- [ ] Update status after action
- [ ] Commit: "feat(ui): add integration connect/disconnect actions"

### Task 46.3: Integration Detail Cards
**Description**: Expandable cards showing integration-specific details.
**Files**: `src/templates/integrations.html`
**Validation**: Click card → see contacts synced, emails sent, etc.
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] HubSpot: show contacts, deals, last sync
- [ ] Gmail: show sent count, quota remaining
- [ ] Drive: show connected folders
- [ ] Add collapsible detail sections
- [ ] Commit: "feat(ui): add integration detail cards"

### Task 46.4: Navigation Update - Integrations Tab
**Description**: Add Integrations tab to CaseyOS navigation.
**Files**: `src/templates/base.html`
**Validation**: 🔌 Integrations tab visible in nav
**Acceptance Criteria**:
- [ ] Add Integrations tab after Voice
- [ ] Set active_tab="integrations" styling
- [ ] Commit: "feat(ui): add Integrations tab to navigation"

---

## Sprint 47: Notifications Center
**Goal**: Surface in-app notifications with read/unread and action capabilities.
**Demo**: Bell icon shows notification count, click opens notification panel.

### Task 47.1: Notification Bell Component
**Description**: Add notification bell to global nav with unread count badge.
**Files**: `src/templates/base.html`
**Validation**: Bell shows count, updates via polling
**Tests**: `tests/unit/test_notification_badge.py`
**Acceptance Criteria**:
- [ ] Add bell icon to nav header
- [ ] Show unread count badge
- [ ] Poll `/api/jarvis/notifications` every 30s
- [ ] Animate on new notifications
- [ ] Commit: "feat(ui): add notification bell with badge"

### Task 47.2: Notification Dropdown Panel
**Description**: Dropdown showing recent notifications with quick actions.
**Files**: `src/templates/base.html`, `src/static/notifications.js`
**Validation**: Click bell → dropdown with last 10 notifications
**Tests**: `tests/unit/test_notification_dropdown.py`
**Acceptance Criteria**:
- [ ] Create dropdown component
- [ ] Show notification title, time, type icon
- [ ] Mark as read on click
- [ ] "View All" link to full page
- [ ] Commit: "feat(ui): add notification dropdown panel"

### Task 47.3: Full Notifications Page
**Description**: Dedicated page for viewing and managing all notifications.
**Files**: `src/templates/notifications.html`, `src/routes/ui.py`
**Validation**: `/caseyos/notifications` shows all with filters
**Tests**: `tests/unit/test_notifications_page.py`
**Acceptance Criteria**:
- [ ] Create `notifications.html` extending base.html
- [ ] Filter by read/unread, type
- [ ] Bulk mark as read
- [ ] Delete old notifications
- [ ] Add route `/caseyos/notifications`
- [ ] Commit: "feat(ui): add full notifications page"

### Task 47.4: Notification Actions
**Description**: Enable action buttons directly from notifications.
**Files**: `src/templates/notifications.html`
**Validation**: "Approve" button on approval notification → executes approval
**Tests**: `tests/unit/test_notification_actions.py`
**Acceptance Criteria**:
- [ ] Render action buttons based on notification type
- [ ] Call appropriate API on click
- [ ] Update notification status after action
- [ ] Show success/error toast
- [ ] Commit: "feat(ui): add notification action buttons"

---

## Sprint 48: Analytics Dashboard
**Goal**: Surface system analytics and performance metrics in CaseyOS.
**Demo**: `/caseyos/analytics` shows send metrics, error rates, recovery stats.

### Task 48.1: Analytics Overview Page
**Description**: Create analytics dashboard with key system metrics.
**Files**: `src/templates/analytics.html`, `src/routes/ui.py`
**Validation**: `/caseyos/analytics` shows charts and KPIs
**Tests**: `tests/unit/test_analytics_ui.py`
**Acceptance Criteria**:
- [ ] Create `analytics.html` extending base.html
- [ ] Call `/api/analytics/metrics` for data
- [ ] Show: emails sent, approval rate, avg response time
- [ ] Add Chart.js or similar for visualizations
- [ ] Add route `/caseyos/analytics`
- [ ] Commit: "feat(ui): add analytics overview page"

### Task 48.2: Error Tracking Panel
**Description**: Show recent errors and failure patterns.
**Files**: `src/templates/analytics.html`
**Validation**: Errors section shows last 24h failures
**Tests**: `tests/unit/test_error_tracking_ui.py`
**Acceptance Criteria**:
- [ ] Call `/api/analytics/errors` endpoint
- [ ] Show error count by type
- [ ] List recent errors with stack trace preview
- [ ] Link to recovery actions
- [ ] Commit: "feat(ui): add error tracking panel"

### Task 48.3: Mode Distribution Chart
**Description**: Show breakdown of system modes over time.
**Files**: `src/templates/analytics.html`
**Validation**: Pie chart shows draft-only vs live send percentages
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Call `/api/analytics/mode-distribution`
- [ ] Render pie chart with draft-only, live, paused
- [ ] Show historical trend line
- [ ] Commit: "feat(ui): add mode distribution chart"

### Task 48.4: Recovery Dashboard
**Description**: Show auto-recovery stats and manual retry options.
**Files**: `src/templates/analytics.html`
**Validation**: Recovery section shows success rate, pending retries
**Tests**: `tests/unit/test_recovery_ui.py`
**Acceptance Criteria**:
- [ ] Call `/api/analytics/recovery/stats`
- [ ] Show auto-recovery success rate
- [ ] List failed items eligible for retry
- [ ] Add "Retry All" button
- [ ] Commit: "feat(ui): add recovery dashboard"

---

## Sprint 49: Gemini Workflow UI
**Goal**: Surface workflow templates and execution UI in Gemini portal.
**Demo**: Select "Account Research" workflow → see step progress → get results.

### Task 49.1: Workflow Selector Dropdown
**Description**: Add workflow template selector to Gemini UI.
**Files**: `src/templates/gemini.html`
**Validation**: Dropdown shows 6 workflow templates
**Tests**: `tests/unit/test_workflow_selector.py`
**Acceptance Criteria**:
- [ ] Fetch workflows from `/api/gemini/workflows`
- [ ] Add dropdown next to model selector
- [ ] Show workflow name and description
- [ ] Enable quick-start from selector
- [ ] Commit: "feat(ui): add workflow selector to Gemini"

### Task 49.2: Workflow Execution Modal
**Description**: Modal to configure and start workflow execution.
**Files**: `src/templates/gemini.html`
**Validation**: Click workflow → modal with input fields → execute
**Tests**: `tests/unit/test_workflow_modal.py`
**Acceptance Criteria**:
- [ ] Create modal component
- [ ] Render input fields based on workflow.required_context
- [ ] Validate inputs before submit
- [ ] Call `/api/gemini/workflows/{id}/execute`
- [ ] Commit: "feat(ui): add workflow execution modal"

### Task 49.3: Multi-Step Progress Display
**Description**: Show step-by-step progress during workflow execution.
**Files**: `src/templates/gemini.html`
**Validation**: "Step 2/4: Researching competitors..." updates live
**Tests**: `tests/unit/test_workflow_progress.py`
**Acceptance Criteria**:
- [ ] Add progress bar component
- [ ] Poll for execution status
- [ ] Show current step name and number
- [ ] Display intermediate results as they complete
- [ ] Commit: "feat(ui): add workflow progress display"

### Task 49.4: Workflow History Panel
**Description**: Show recent workflow executions in sidebar.
**Files**: `src/templates/gemini.html`
**Validation**: Sidebar shows last 10 workflow runs
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Add collapsible history panel
- [ ] Show workflow name, status, timestamp
- [ ] Click to view results
- [ ] Re-run button for completed workflows
- [ ] Commit: "feat(ui): add workflow history panel"

---

## Sprint 50: Settings & Configuration UI
**Goal**: Surface system settings and user preferences in CaseyOS.
**Demo**: `/caseyos/settings` allows toggling features and viewing config.

### Task 50.1: Settings Page Layout
**Description**: Create settings page with tabbed sections.
**Files**: `src/templates/settings.html`, `src/routes/ui.py`
**Validation**: `/caseyos/settings` shows organized settings
**Tests**: `tests/unit/test_settings_ui.py`
**Acceptance Criteria**:
- [ ] Create `settings.html` extending base.html
- [ ] Add tabs: General, Notifications, Integrations, Advanced
- [ ] Add route `/caseyos/settings`
- [ ] Commit: "feat(ui): add settings page layout"

### Task 50.2: Feature Flags Toggle
**Description**: Enable toggling feature flags from UI.
**Files**: `src/templates/settings.html`
**Validation**: Toggle switch → feature enabled/disabled
**Tests**: `tests/unit/test_feature_toggle_ui.py`
**Acceptance Criteria**:
- [ ] Fetch flags from `/api/admin/flags`
- [ ] Render toggle switches
- [ ] POST to update flag state
- [ ] Show success toast
- [ ] Commit: "feat(ui): add feature flags toggle"

### Task 50.3: System Mode Selector
**Description**: UI to switch between draft-only, review, and live modes.
**Files**: `src/templates/settings.html`
**Validation**: Select mode → system behavior changes
**Tests**: `tests/unit/test_mode_selector_ui.py`
**Acceptance Criteria**:
- [ ] Show current mode prominently
- [ ] Radio buttons for mode selection
- [ ] Warning modal for live mode
- [ ] Update via `/api/admin/mode`
- [ ] Commit: "feat(ui): add system mode selector"

### Task 50.4: Notification Preferences
**Description**: User preferences for notification channels and frequency.
**Files**: `src/templates/settings.html`
**Validation**: Toggle email notifications → preference saved
**Tests**: `tests/unit/test_notification_prefs_ui.py`
**Acceptance Criteria**:
- [ ] Fetch prefs from `/api/notification-prefs`
- [ ] Checkboxes for email, in-app, Slack
- [ ] Frequency selector (immediate, hourly, daily)
- [ ] Save preferences
- [ ] Commit: "feat(ui): add notification preferences"

---

## Sprint 51: Admin & Ops Dashboard
**Goal**: Surface admin controls and operations visibility.
**Demo**: `/caseyos/admin` shows system health, kill switch, and audit log.

### Task 51.1: Admin Dashboard Page
**Description**: Create admin-only dashboard with system controls.
**Files**: `src/templates/admin.html`, `src/routes/ui.py`
**Validation**: `/caseyos/admin` shows health and controls
**Tests**: `tests/unit/test_admin_ui.py`
**Acceptance Criteria**:
- [ ] Create `admin.html` extending base.html
- [ ] Require admin role (or show warning)
- [ ] Show Celery worker status, Redis connection, DB health
- [ ] Add route `/caseyos/admin`
- [ ] Commit: "feat(ui): add admin dashboard page"

### Task 51.2: Emergency Kill Switch
**Description**: Big red button to pause all outbound sends.
**Files**: `src/templates/admin.html`
**Validation**: Click kill switch → all sends paused
**Tests**: `tests/unit/test_kill_switch_ui.py`
**Acceptance Criteria**:
- [ ] Large prominent kill switch button
- [ ] Confirmation modal with warning
- [ ] Call `/api/admin/emergency-stop`
- [ ] Show resume button after activation
- [ ] Commit: "feat(ui): add emergency kill switch"

### Task 51.3: Audit Log Viewer
**Description**: View recent audit log entries for compliance.
**Files**: `src/templates/admin.html`
**Validation**: Audit section shows last 50 actions
**Tests**: `tests/unit/test_audit_log_ui.py`
**Acceptance Criteria**:
- [ ] Fetch from `/api/audit/logs`
- [ ] Show action, user, timestamp, details
- [ ] Filter by action type
- [ ] Export button for CSV
- [ ] Commit: "feat(ui): add audit log viewer"

### Task 51.4: Circuit Breaker Status
**Description**: Show circuit breaker states for external services.
**Files**: `src/templates/admin.html`
**Validation**: Cards show Gmail, HubSpot, LLM circuit states
**Tests**: `tests/unit/test_circuit_breaker_ui.py`
**Acceptance Criteria**:
- [ ] Fetch from `/api/circuit-breakers`
- [ ] Show state (closed/open/half-open) per service
- [ ] Show failure count and last failure time
- [ ] Reset button for manual recovery
- [ ] Commit: "feat(ui): add circuit breaker status"

---

## Sprint 52: Legacy Cleanup & Polish ✅ COMPLETE
**Goal**: Remove deprecated files, fix UI inconsistencies, update versions.
**Demo**: Clean codebase, no legacy static HTML, consistent UI.
**Status**: Completed 2026-01-28 (commit `0a15b61`)

### Task 52.1: Remove Legacy Static HTML ✅
### Task 52.2: Remove Deprecated Route Files ✅
### Task 52.3: Update Version Numbers ✅
### Task 52.4: Navigation Polish ✅

---

## Sprint 53: User Profile & Email Signature System
**Goal**: Ensure user profile data (name, title, signature) flows into draft generation - no placeholders!
**Demo**: Generate draft → signature shows "Casey Larkin, CEO, Pesti" with calendar link, not placeholders.
**Depends On**: Sprint 44 (Voice Profiles)

### Task 53.1: User Model Profile Extension
**Description**: Add profile fields to User model for signature data.
**Files**: `src/models/user.py`, `infra/migrations/`
**Validation**: `User.display_name`, `job_title`, `signature_html` columns exist
**Tests**: `tests/unit/test_user_model.py::test_profile_fields`
**Acceptance Criteria**:
- [ ] Add `display_name: Mapped[str] = mapped_column(String(255), nullable=True)` to User
- [ ] Add `job_title: Mapped[str] = mapped_column(String(255), nullable=True)` to User
- [ ] Add `signature_html: Mapped[str] = mapped_column(Text, nullable=True)` to User
- [ ] Add `calendar_link: Mapped[str] = mapped_column(String(500), nullable=True)` to User
- [ ] Add `default_voice_profile_id: Mapped[UUID] = mapped_column(ForeignKey("voice_profiles.id"), nullable=True)`
- [ ] Create Alembic migration: `alembic revision --autogenerate -m "add_user_profile_fields"`
- [ ] Run migration: `alembic upgrade head`
- [ ] Commit: "feat(models): add user profile fields for signature"

### Task 53.2: User Profile API Endpoints
**Description**: REST API for reading and updating user profile.
**Files**: `src/routes/users.py`
**Validation**: `GET /api/users/me/profile` returns profile, `PUT` updates it
**Tests**: `tests/unit/test_user_profile_api.py`
**Acceptance Criteria**:
- [ ] Create `ProfileResponse` Pydantic model with all profile fields
- [ ] Create `ProfileUpdate` Pydantic model for updates
- [ ] Add `GET /api/users/me/profile` endpoint
- [ ] Add `PUT /api/users/me/profile` endpoint
- [ ] Return 401 if not authenticated
- [ ] Test: Get profile returns display_name, job_title, signature_html, calendar_link
- [ ] Test: Update profile persists changes
- [ ] Commit: "feat(api): add user profile GET/PUT endpoints"

### Task 53.3: Profile Settings UI Tab
**Description**: Add Profile tab to Settings page with signature editor.
**Files**: `src/templates/settings.html`, `src/routes/ui.py`
**Validation**: `/caseyos/settings` → Profile tab shows form with current values
**Tests**: `tests/unit/test_profile_settings_ui.py`
**Acceptance Criteria**:
- [ ] Add "Profile" tab to Settings page (first tab)
- [ ] Form fields: Display Name, Job Title, Calendar Link, Email Signature (textarea)
- [ ] Pre-populate with current user values
- [ ] HTMX PUT to `/api/users/me/profile` on save
- [ ] Show success toast on save
- [ ] Test: Profile tab renders with form
- [ ] Test: Form submission updates profile
- [ ] Commit: "feat(ui): add profile tab to settings page"

### Task 53.4: Signature Preview Component
**Description**: Live preview of signature as user edits.
**Files**: `src/templates/settings.html`
**Validation**: Type in signature textarea → preview updates in real-time
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Add signature preview div next to textarea
- [ ] JavaScript to update preview on input
- [ ] Show formatted signature with name, title, calendar link
- [ ] Support basic HTML formatting in preview
- [ ] Commit: "feat(ui): add live signature preview in settings"

### Task 53.5: Voice Profile Linkage to User
**Description**: Link user's default voice profile and sync signature from it.
**Files**: `src/models/user.py`, `src/voice_profile.py`
**Validation**: User's default voice profile signature flows to profile
**Tests**: `tests/unit/test_voice_profile_linkage.py`
**Acceptance Criteria**:
- [ ] Add relationship `default_voice_profile` to User model
- [ ] Add dropdown in Profile settings to select default voice profile
- [ ] When voice profile selected, optionally sync signature_style to User
- [ ] Test: User with voice profile gets signature from profile
- [ ] Commit: "feat(models): link user to default voice profile"

### Task 53.6: Draft Generator Context Injection
**Description**: Inject user profile data into draft generation context.
**Files**: `src/draft_generator.py`, `src/email_generator/generator_service.py`
**Validation**: Draft generated with proper sender_name, sender_title
**Tests**: `tests/unit/test_draft_signature_injection.py`
**Depends On**: Task 53.1, Task 53.2
**Acceptance Criteria**:
- [ ] Modify `generate_draft()` to accept `user: User` parameter
- [ ] Inject `sender_name=user.display_name`, `sender_title=user.job_title`
- [ ] Use `user.signature_html` if set, else `user.default_voice_profile.signature_style`
- [ ] Include `user.calendar_link` in context
- [ ] Test: Draft with user has proper signature
- [ ] Test: Draft without user uses fallback
- [ ] Commit: "feat(drafts): inject user profile into draft context"

### Task 53.7: Queue Item Signature Display
**Description**: Show properly formatted signature in queue detail view.
**Files**: `src/templates/queue_detail.html`
**Validation**: View draft in queue → signature block is formatted correctly
**Tests**: `tests/unit/test_queue_signature_display.py`
**Acceptance Criteria**:
- [ ] Parse signature block from draft body
- [ ] Display signature in styled block (different background)
- [ ] Show calendar link as clickable button
- [ ] Test: Queue detail shows signature block
- [ ] Commit: "feat(ui): display formatted signature in queue detail"

---

## Sprint 54: OAuth Token Health & Persistence UI
**Goal**: Keep Google account connected with visible status and automatic refresh.
**Demo**: Login with Google → stay connected for days → see connection status in UI → auto-refresh works.
**Depends On**: Sprint 33 (OAuth Consolidation)

### Task 54.1: OAuth Token Status API
**Description**: API endpoint to check OAuth token health per service.
**Files**: `src/routes/integrations_api.py`, `src/oauth_manager.py`
**Validation**: `GET /api/oauth/status` returns token health for each service
**Tests**: `tests/unit/test_oauth_status_api.py`
**Acceptance Criteria**:
- [ ] Create `OAuthStatusResponse` with `service`, `connected`, `expires_at`, `scopes`, `needs_refresh`
- [ ] Add `GET /api/oauth/status` endpoint
- [ ] Query `oauth_tokens` table for current user
- [ ] Return list of connected services with expiry
- [ ] Include `needs_refresh: bool` if expires < 1 hour
- [ ] Test: Returns connected services
- [ ] Test: Returns needs_refresh=true when expiring
- [ ] Commit: "feat(api): add OAuth token status endpoint"

### Task 54.2: Integrations Page Status Cards
**Description**: Show OAuth connection status with expiry on Integrations page.
**Files**: `src/templates/integrations.html`
**Validation**: `/caseyos/integrations` shows Gmail/HubSpot/Drive with connection status
**Tests**: `tests/unit/test_integrations_status_cards.py`
**Acceptance Criteria**:
- [ ] Fetch status from `/api/oauth/status`
- [ ] Display card per service: Gmail, HubSpot, Google Drive
- [ ] Show ✅ Connected / ❌ Not Connected / ⚠️ Expiring Soon
- [ ] Display `expires_at` in human-readable format ("in 2 hours")
- [ ] Test: Cards render with correct status
- [ ] Commit: "feat(ui): add OAuth status cards to integrations page"

### Task 54.3: Reconnect Flow Button
**Description**: "Reconnect" button appears when token needs refresh or is expired.
**Files**: `src/templates/integrations.html`, `src/routes/auth_routes.py`
**Validation**: Expired token → Reconnect button → OAuth flow → connected
**Tests**: `tests/unit/test_reconnect_flow.py`
**Acceptance Criteria**:
- [ ] Show "Reconnect" button when `needs_refresh=true` or `connected=false`
- [ ] Button triggers OAuth flow: `/api/auth/google/authorize`
- [ ] After successful OAuth, update status card
- [ ] Test: Reconnect button triggers OAuth
- [ ] Commit: "feat(ui): add OAuth reconnect button"

### Task 54.4: Token Expiry Notification
**Description**: Send in-app notification when token is about to expire.
**Files**: `src/tasks/oauth_refresh.py`, `src/services/notification_service.py`
**Validation**: Token expiring in < 1 hour → notification appears
**Tests**: `tests/unit/test_token_expiry_notification.py`
**Acceptance Criteria**:
- [ ] Modify existing `refresh-expiring-oauth-tokens` Celery task
- [ ] If refresh fails, create notification: "Google connection expiring - reconnect"
- [ ] Use `NotificationService.create()` with type="oauth_expiring"
- [ ] Test: Failed refresh creates notification
- [ ] Commit: "feat(notifications): notify on OAuth token expiry"

### Task 54.5: Header Connection Status Indicator
**Description**: Small indicator in header showing OAuth health.
**Files**: `src/templates/base.html`
**Validation**: Header shows 🟢/🟡/🔴 based on OAuth status
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Add connection status icon next to notification bell
- [ ] 🟢 = All connected, 🟡 = Expiring soon, 🔴 = Disconnected
- [ ] Tooltip shows details on hover
- [ ] Poll `/api/oauth/status` every 5 minutes
- [ ] Commit: "feat(ui): add OAuth status indicator to header"

---

## Sprint 55: Draft Editing & Queue Polish
**Goal**: Complete draft approval workflow with inline editing and proper formatting.
**Demo**: View draft → edit subject/body → preview signature → approve → send with edits.
**Depends On**: Sprint 53 (Signature System)

### Task 55.1: Draft Subject Editing
**Description**: Allow editing email subject in queue detail before approval.
**Files**: `src/templates/queue_detail.html`, `src/routes/queue.py`
**Validation**: Edit subject → save → subject updated in database
**Tests**: `tests/unit/test_draft_subject_edit.py`
**Acceptance Criteria**:
- [ ] Make subject field editable (input instead of static text)
- [ ] Add "Save" button that PUTs to `/api/command-queue/{id}/update`
- [ ] Create `PUT /api/command-queue/{id}/update` endpoint
- [ ] Accept `subject` and `body` in request body
- [ ] Test: Subject edit persists
- [ ] Commit: "feat(queue): enable draft subject editing"

### Task 55.2: Draft Body Editing
**Description**: Allow editing email body with rich text editor.
**Files**: `src/templates/queue_detail.html`
**Validation**: Edit body → preserve formatting → save → body updated
**Tests**: `tests/unit/test_draft_body_edit.py`
**Acceptance Criteria**:
- [ ] Replace textarea with contenteditable div or simple markdown editor
- [ ] Preserve line breaks and basic formatting
- [ ] Save button updates body via API
- [ ] Test: Body edit persists with formatting
- [ ] Commit: "feat(queue): enable draft body editing"

### Task 55.3: Preview vs Edit Mode Toggle
**Description**: Toggle between preview mode (rendered) and edit mode (raw).
**Files**: `src/templates/queue_detail.html`
**Validation**: Click "Edit" → shows editable, click "Preview" → shows rendered
**Tests**: `tests/unit/test_preview_edit_toggle.py`
**Acceptance Criteria**:
- [ ] Add "Edit" / "Preview" toggle buttons
- [ ] Preview mode shows HTML-rendered email
- [ ] Edit mode shows editable fields
- [ ] Unsaved changes warning when leaving edit mode
- [ ] Test: Toggle switches modes correctly
- [ ] Commit: "feat(ui): add preview/edit mode toggle for drafts"

### Task 55.4: Signature Block Formatting
**Description**: Visually separate signature from email body.
**Files**: `src/templates/queue_detail.html`
**Validation**: Signature appears in distinct block at bottom of preview
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Parse signature block from body (after "Best," or "Best regards,")
- [ ] Display in styled signature box
- [ ] Include calendar link as button
- [ ] Don't allow editing signature (comes from profile)
- [ ] Commit: "feat(ui): format signature block in draft preview"

### Task 55.5: Draft Send Confirmation Modal
**Description**: Confirmation modal before sending approved draft.
**Files**: `src/templates/queue_detail.html`
**Validation**: Click "Send" → modal shows recipient, subject → confirm → sent
**Tests**: `tests/unit/test_send_confirmation_modal.py`
**Acceptance Criteria**:
- [ ] Create confirmation modal component
- [ ] Show: To, Subject, Preview of first 100 chars
- [ ] "Cancel" and "Send Now" buttons
- [ ] Send Now calls `/api/command-queue/{id}/send`
- [ ] Test: Modal prevents accidental sends
- [ ] Commit: "feat(ui): add draft send confirmation modal"

### Task 55.6: Queue Sorting & Filtering
**Description**: Sort and filter queue items for easier management.
**Files**: `src/templates/queue.html`, `src/routes/queue.py`
**Validation**: Sort by priority/date, filter by status/recipient
**Tests**: `tests/unit/test_queue_sorting.py`
**Acceptance Criteria**:
- [ ] Add sort dropdown: Priority (high first), Date (newest), Date (oldest)
- [ ] Add status filter: All, Pending, Approved, Sent, Rejected
- [ ] Add search input for recipient email/name
- [ ] Update API to accept `sort`, `status`, `search` params
- [ ] Test: Sorting changes order
- [ ] Test: Filtering reduces results
- [ ] Commit: "feat(queue): add sorting and filtering"

### Task 55.7: Bulk Queue Actions
**Description**: Select multiple items for bulk approve/reject.
**Files**: `src/templates/queue.html`, `src/routes/queue.py`
**Validation**: Select 3 items → click "Approve Selected" → all approved
**Tests**: `tests/unit/test_bulk_actions.py`
**Acceptance Criteria**:
- [ ] Add checkbox to each queue item
- [ ] Add "Select All" checkbox in header
- [ ] Show bulk action bar when items selected
- [ ] "Approve Selected" and "Reject Selected" buttons
- [ ] Create `POST /api/command-queue/bulk-action` endpoint
- [ ] Test: Bulk approve updates all selected items
- [ ] Commit: "feat(queue): add bulk approve/reject actions"

---

## Sprint 56: Data Hygiene Dashboard
**Goal**: Surface existing data hygiene agents and quality metrics in CaseyOS UI.
**Demo**: View duplicate contacts → merge → see data quality score improve.
**Depends On**: Existing data hygiene agents at `src/agents/enrichment/`

### Task 56.1: Data Quality API Endpoints
**Description**: API to expose data quality metrics and duplicates.
**Files**: `src/routes/data_hygiene.py` (new), `src/main.py`
**Validation**: `GET /api/data-hygiene/quality` returns quality scores
**Tests**: `tests/unit/test_data_hygiene_api.py`
**Acceptance Criteria**:
- [ ] Create `src/routes/data_hygiene.py`
- [ ] Add `GET /api/data-hygiene/quality` - overall quality score
- [ ] Add `GET /api/data-hygiene/duplicates` - list of potential duplicates
- [ ] Add `POST /api/data-hygiene/merge` - merge two contacts
- [ ] Register routes in `main.py`
- [ ] Test: Quality endpoint returns score
- [ ] Commit: "feat(api): add data hygiene endpoints"

### Task 56.2: Data Hygiene Dashboard Page
**Description**: Create dedicated page for data quality and hygiene.
**Files**: `src/templates/data_hygiene.html`, `src/routes/ui.py`
**Validation**: `/caseyos/data-hygiene` shows quality metrics and duplicates
**Tests**: `tests/unit/test_data_hygiene_ui.py`
**Acceptance Criteria**:
- [ ] Create `data_hygiene.html` extending base.html
- [ ] Add route `/caseyos/data-hygiene`
- [ ] Show overall data quality score (0-100)
- [ ] Show completeness metrics: % with email, phone, title
- [ ] Add to navigation: 🧹 Data Hygiene
- [ ] Test: Page renders with quality metrics
- [ ] Commit: "feat(ui): add data hygiene dashboard page"

### Task 56.3: Duplicate Detection Panel
**Description**: Show potential duplicate contacts for review.
**Files**: `src/templates/data_hygiene.html`
**Validation**: List of duplicate groups with match confidence
**Tests**: `tests/unit/test_duplicate_panel.py`
**Acceptance Criteria**:
- [ ] Fetch duplicates from `/api/data-hygiene/duplicates`
- [ ] Display as grouped cards (2+ contacts per group)
- [ ] Show match reason: "Same email", "Similar name at same company"
- [ ] Show match confidence percentage
- [ ] Test: Duplicates displayed with groups
- [ ] Commit: "feat(ui): add duplicate detection panel"

### Task 56.4: Merge Duplicates UI
**Description**: UI to review and merge duplicate contacts.
**Files**: `src/templates/data_hygiene.html`
**Validation**: Select master record → merge → duplicates removed
**Tests**: `tests/unit/test_merge_ui.py`
**Acceptance Criteria**:
- [ ] Expand duplicate group to see all fields
- [ ] Radio buttons to select "master" record
- [ ] "Merge" button calls `/api/data-hygiene/merge`
- [ ] Show merged result before confirming
- [ ] Update list after successful merge
- [ ] Test: Merge combines records correctly
- [ ] Commit: "feat(ui): add duplicate merge functionality"

### Task 56.5: Data Quality Improvement Suggestions
**Description**: Show actionable suggestions to improve data quality.
**Files**: `src/templates/data_hygiene.html`
**Validation**: List of suggestions: "Add phone to 47 contacts"
**Tests**: `tests/unit/test_quality_suggestions.py`
**Acceptance Criteria**:
- [ ] Add suggestions panel
- [ ] Analyze missing fields and suggest actions
- [ ] Prioritize by impact (phone, title, company)
- [ ] Show count of records affected
- [ ] Commit: "feat(ui): add data quality suggestions"

### Task 56.6: External Hygiene API Connector (Optional)
**Description**: If user has external hygiene repo, create connector.
**Files**: `src/connectors/hygiene.py` (new)
**Validation**: Call external API for hygiene checks
**Tests**: `tests/unit/test_hygiene_connector.py`
**Acceptance Criteria**:
- [ ] Create `HygieneConnector` class
- [ ] Accept `HYGIENE_API_URL` environment variable
- [ ] Implement `check_quality()` method
- [ ] Implement `find_duplicates()` method
- [ ] Use in data hygiene routes if configured
- [ ] Test: Connector calls external API
- [ ] Commit: "feat(connectors): add external hygiene API connector"

---

## Sprint 57: Operator Experience Enhancement
**Goal**: Make daily operator workflow smooth and efficient.
**Demo**: Login → see pending count → keyboard navigate → approve → see confirmation toast.
**Depends On**: Sprint 55 (Queue Polish)

### Task 57.1: Dashboard Real Metrics
**Description**: Ensure all dashboard numbers are real, not mocked.
**Files**: `src/routes/dashboard_api.py`, `src/templates/dashboard.html`
**Validation**: Dashboard shows actual pending count, sent today, etc.
**Tests**: `tests/unit/test_dashboard_metrics_real.py`
**Acceptance Criteria**:
- [ ] Audit `/api/dashboard/stats` endpoint
- [ ] Query `command_queue` table for real pending count
- [ ] Query `drafts` table for real sent_today count
- [ ] Remove any hardcoded/mock values
- [ ] Test: Metrics change when data changes
- [ ] Commit: "fix(dashboard): use real metrics not mocks"

### Task 57.2: Keyboard Navigation
**Description**: J/K to navigate queue, A to approve, R to reject.
**Files**: `src/templates/queue.html`, `src/templates/queue_detail.html`
**Validation**: Press J → next item selected, A → approve dialog
**Tests**: `tests/unit/test_keyboard_nav.py`
**Acceptance Criteria**:
- [ ] Add keyboard event listeners
- [ ] J = next item, K = previous item
- [ ] Enter = open detail view
- [ ] A = approve (in detail view)
- [ ] R = reject (in detail view)
- [ ] Escape = close modals
- [ ] Show keyboard shortcuts hint in footer
- [ ] Test: Keyboard events trigger actions
- [ ] Commit: "feat(ui): add keyboard navigation shortcuts"

### Task 57.3: Quick Actions from Queue
**Description**: Approve/reject directly from queue list without opening detail.
**Files**: `src/templates/queue.html`
**Validation**: Click ✓ on queue item → approved without page change
**Tests**: `tests/unit/test_quick_actions.py`
**Acceptance Criteria**:
- [ ] Add ✓ and ✗ icons to each queue row
- [ ] Click ✓ → HTMX POST to approve → update row status
- [ ] Click ✗ → show reason input → reject
- [ ] No page reload needed
- [ ] Test: Quick approve updates status inline
- [ ] Commit: "feat(queue): add quick approve/reject buttons"

### Task 57.4: Action Confirmation Toasts
**Description**: Show toast notifications for all actions.
**Files**: `src/templates/base.html`
**Validation**: Approve → green toast "Email approved", Reject → orange toast
**Tests**: Visual verification
**Acceptance Criteria**:
- [ ] Create toast component in base.html
- [ ] JavaScript `showToast(message, type)` function
- [ ] Types: success (green), error (red), warning (orange), info (blue)
- [ ] Auto-dismiss after 3 seconds
- [ ] Trigger from HTMX response headers
- [ ] Commit: "feat(ui): add action confirmation toasts"

### Task 57.5: Pending Items Badge
**Description**: Show pending count badge on Command Queue nav item.
**Files**: `src/templates/base.html`
**Validation**: 5 pending → "Command Queue (5)" in nav
**Tests**: `tests/unit/test_pending_badge.py`
**Acceptance Criteria**:
- [ ] Fetch pending count on page load
- [ ] Display badge next to Command Queue nav
- [ ] Update via polling every 30 seconds
- [ ] Hide badge when count is 0
- [ ] Test: Badge shows correct count
- [ ] Commit: "feat(ui): add pending items badge to nav"

### Task 57.6: Daily Summary Email
**Description**: Morning email summarizing pending items and yesterday's activity.
**Files**: `src/tasks/daily_summary.py` (new), `src/celery_app.py`
**Validation**: 8am daily → email with summary arrives
**Tests**: `tests/unit/test_daily_summary.py`
**Acceptance Criteria**:
- [ ] Create Celery beat task `send_daily_summary`
- [ ] Schedule for 8am daily
- [ ] Include: pending count, approved yesterday, sent yesterday, errors
- [ ] Send via Gmail connector to operator email
- [ ] Add setting to enable/disable
- [ ] Test: Task generates correct summary
- [ ] Commit: "feat(tasks): add daily summary email"

---

## Sprint 58: Resilience & Error Recovery
**Goal**: Handle failures gracefully with clear recovery paths.
**Demo**: Gmail API fails → see error in UI → click retry → success.
**Depends On**: Sprint 30 (Observability)

### Task 58.1: Error State UI Components
**Description**: Consistent error state display across all pages.
**Files**: `src/templates/base.html`, `src/templates/_partials/error.html`
**Validation**: API error → shows error box with retry button
**Tests**: `tests/unit/test_error_state_ui.py`
**Acceptance Criteria**:
- [ ] Create `_partials/error.html` component
- [ ] Accept `message`, `details`, `retry_url` parameters
- [ ] Show error icon, message, optional details toggle
- [ ] "Retry" button makes HTMX request to retry_url
- [ ] Include in all data-fetching templates
- [ ] Test: Error component renders correctly
- [ ] Commit: "feat(ui): add reusable error state component"

### Task 58.2: Retry Queue for Failed Items
**Description**: Failed sends go to retry queue with exponential backoff.
**Files**: `src/models/retry_queue.py` (new), `src/services/retry_service.py` (new)
**Validation**: Send fails → item in retry queue → retries 3x with backoff
**Tests**: `tests/unit/test_retry_queue.py`
**Acceptance Criteria**:
- [ ] Create `RetryItem` model: id, original_id, type, payload, attempts, next_retry_at
- [ ] Create migration
- [ ] Create `RetryService` with `add_to_retry()`, `process_retries()`
- [ ] Exponential backoff: 1min, 5min, 30min
- [ ] Max 3 retries before permanent failure
- [ ] Test: Failed item added to retry queue
- [ ] Test: Backoff timing is correct
- [ ] Commit: "feat(resilience): add retry queue with backoff"

### Task 58.3: Retry Processing Task
**Description**: Background task to process retry queue.
**Files**: `src/tasks/retry_processor.py` (new), `src/celery_app.py`
**Validation**: Items in retry queue processed on schedule
**Tests**: `tests/unit/test_retry_processor.py`
**Acceptance Criteria**:
- [ ] Create Celery task `process_retry_queue`
- [ ] Run every 1 minute
- [ ] Process items where `next_retry_at < now()`
- [ ] Update attempt count and next_retry_at on failure
- [ ] Move to permanent failure after max attempts
- [ ] Test: Task processes due items
- [ ] Commit: "feat(tasks): add retry queue processor"

### Task 58.4: Recovery Dashboard Panel
**Description**: View items in recovery state with manual retry option.
**Files**: `src/templates/admin.html`
**Validation**: Admin page shows retry queue with "Retry Now" buttons
**Tests**: `tests/unit/test_recovery_panel.py`
**Acceptance Criteria**:
- [ ] Add "Recovery Queue" section to admin page
- [ ] List items: type, original action, attempts, next retry
- [ ] "Retry Now" button to force immediate retry
- [ ] "Abandon" button to mark as permanently failed
- [ ] Filter by type (email, sync, etc.)
- [ ] Test: Recovery panel shows retry items
- [ ] Commit: "feat(ui): add recovery dashboard panel"

### Task 58.5: Idempotency Keys for Sends
**Description**: Prevent duplicate sends with idempotency keys.
**Files**: `src/services/email_sender.py`, `src/models/idempotency.py`
**Validation**: Same send request twice → only one email sent
**Tests**: `tests/unit/test_idempotency.py`
**Acceptance Criteria**:
- [ ] Create `IdempotencyKey` model: key, resource_type, resource_id, created_at
- [ ] Generate key from: user_id + recipient + subject + timestamp_bucket
- [ ] Check key exists before send
- [ ] Store key after successful send
- [ ] TTL of 24 hours
- [ ] Test: Duplicate request returns success without re-sending
- [ ] Commit: "feat(resilience): add idempotency keys for email sends"

### Task 58.6: Circuit Breaker for Gmail
**Description**: Circuit breaker pattern for Gmail API calls.
**Files**: `src/connectors/gmail.py`, `src/resilience.py`
**Validation**: Gmail API fails 5x → circuit opens → fast-fail for 30s
**Tests**: `tests/unit/test_gmail_circuit_breaker.py`
**Acceptance Criteria**:
- [ ] Implement circuit breaker: closed → open → half-open states
- [ ] Open after 5 failures in 1 minute
- [ ] Stay open for 30 seconds
- [ ] Half-open: allow 1 request to test
- [ ] Expose state via `/api/circuit-breakers`
- [ ] Test: Circuit opens after failures
- [ ] Test: Circuit closes after success in half-open
- [ ] Commit: "feat(resilience): add circuit breaker for Gmail"

### Task 58.7: Error Details Modal (Admin)
**Description**: Click error to see full stack trace and context.
**Files**: `src/templates/admin.html`
**Validation**: Click failed item → modal with stack trace
**Tests**: `tests/unit/test_error_details_modal.py`
**Acceptance Criteria**:
- [ ] Add "Details" link to failed items
- [ ] Modal shows: timestamp, error type, message, stack trace
- [ ] Show context: recipient, subject, attempt number
- [ ] Copy button for error details
- [ ] Test: Modal shows full error info
- [ ] Commit: "feat(ui): add error details modal"

---

## Sprint 59: Mobile & Responsive Polish
**Goal**: CaseyOS works well on tablet and mobile for on-the-go approvals.
**Demo**: Open on phone → review queue → approve draft → smooth experience.

### Task 59.1: Responsive Navigation
**Description**: Hamburger menu for mobile, collapsible sidebar.
**Files**: `src/templates/base.html`
**Validation**: < 768px → hamburger menu, sidebar collapses
**Tests**: Visual verification at various breakpoints
**Acceptance Criteria**:
- [ ] Add hamburger icon for mobile
- [ ] Sidebar becomes overlay on mobile
- [ ] Close sidebar when item selected
- [ ] Smooth animation
- [ ] Commit: "feat(ui): add responsive navigation"

### Task 59.2: Touch-Friendly Queue Actions
**Description**: Larger touch targets, swipe gestures.
**Files**: `src/templates/queue.html`
**Validation**: Swipe right → approve, swipe left → reject
**Tests**: Manual testing on touch device
**Acceptance Criteria**:
- [ ] Increase button sizes on mobile
- [ ] Add touch-action swipe handlers
- [ ] Swipe right reveals approve button
- [ ] Swipe left reveals reject button
- [ ] Haptic feedback if available
- [ ] Commit: "feat(ui): add touch-friendly queue actions"

### Task 59.3: Mobile-Optimized Forms
**Description**: Forms work well on mobile with proper keyboard types.
**Files**: `src/templates/settings.html`, `src/templates/queue_detail.html`
**Validation**: Email fields show email keyboard, proper spacing
**Tests**: Manual testing on mobile device
**Acceptance Criteria**:
- [ ] Add `inputmode="email"` for email fields
- [ ] Add `inputmode="url"` for URL fields
- [ ] Increase form field heights on mobile
- [ ] Add proper labels with `for` attributes
- [ ] Commit: "feat(ui): optimize forms for mobile"

### Task 59.4: Offline Indicator
**Description**: Show when offline, queue actions for when online.
**Files**: `src/templates/base.html`
**Validation**: Go offline → see indicator → actions queued
**Tests**: Manual testing with network throttling
**Acceptance Criteria**:
- [ ] Detect offline state with navigator.onLine
- [ ] Show "Offline" banner when disconnected
- [ ] Disable send actions when offline
- [ ] Show "Back Online" toast when reconnected
- [ ] Commit: "feat(ui): add offline indicator"

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

### Sprint 44 Tests ✅ COMPLETE
- [x] Voice training UI visual verification
- [x] Voice profiles CRUD flow
- [x] Route wiring verification

### Sprint 45 Tests
- [ ] `tests/unit/test_memory_ui.py` - session list rendering
- [ ] `tests/unit/test_memory_detail.py` - detail view with context
- [ ] `tests/unit/test_memory_search_ui.py` - search functionality

### Sprint 46 Tests
- [ ] `tests/unit/test_integrations_ui.py` - status page rendering
- [ ] `tests/unit/test_integration_actions.py` - connect/disconnect flow
- [ ] Visual verification of integration cards

### Sprint 47 Tests
- [ ] `tests/unit/test_notification_badge.py` - badge count updates
- [ ] `tests/unit/test_notification_dropdown.py` - dropdown rendering
- [ ] `tests/unit/test_notifications_page.py` - full page with filters
- [ ] `tests/unit/test_notification_actions.py` - action execution

### Sprint 48 Tests
- [ ] `tests/unit/test_analytics_ui.py` - dashboard rendering
- [ ] `tests/unit/test_error_tracking_ui.py` - error list display
- [ ] `tests/unit/test_recovery_ui.py` - recovery stats and retry

### Sprint 49 Tests
- [ ] `tests/unit/test_workflow_selector.py` - dropdown population
- [ ] `tests/unit/test_workflow_modal.py` - input validation
- [ ] `tests/unit/test_workflow_progress.py` - step progress updates

### Sprint 50 Tests
- [ ] `tests/unit/test_settings_ui.py` - settings page layout
- [ ] `tests/unit/test_feature_toggle_ui.py` - flag toggling
- [ ] `tests/unit/test_mode_selector_ui.py` - mode switching
- [ ] `tests/unit/test_notification_prefs_ui.py` - preference saving

### Sprint 51 Tests
- [ ] `tests/unit/test_admin_ui.py` - admin dashboard rendering
- [ ] `tests/unit/test_kill_switch_ui.py` - emergency stop
- [ ] `tests/unit/test_audit_log_ui.py` - log viewing and export
- [ ] `tests/unit/test_circuit_breaker_ui.py` - status display

### Sprint 52 Tests ✅ COMPLETE
- [x] Verify app starts after file removal
- [x] Verify all nav tabs work
- [x] Visual regression testing

### Sprint 53 Tests
- [ ] `tests/unit/test_user_model.py::test_profile_fields` - new profile fields exist
- [ ] `tests/unit/test_user_profile_api.py` - GET/PUT profile endpoints
- [ ] `tests/unit/test_profile_settings_ui.py` - Profile tab in settings
- [ ] `tests/unit/test_voice_profile_linkage.py` - User-VoiceProfile relationship
- [ ] `tests/unit/test_draft_signature_injection.py` - Signature in drafts
- [ ] `tests/unit/test_queue_signature_display.py` - Signature formatting in queue

### Sprint 54 Tests
- [ ] `tests/unit/test_oauth_status_api.py` - OAuth status endpoint
- [ ] `tests/unit/test_integrations_status_cards.py` - Status cards rendering
- [ ] `tests/unit/test_reconnect_flow.py` - OAuth reconnect button
- [ ] `tests/unit/test_token_expiry_notification.py` - Expiry notification creation

### Sprint 55 Tests
- [ ] `tests/unit/test_draft_subject_edit.py` - Subject editing
- [ ] `tests/unit/test_draft_body_edit.py` - Body editing
- [ ] `tests/unit/test_preview_edit_toggle.py` - Mode toggle
- [ ] `tests/unit/test_send_confirmation_modal.py` - Confirmation modal
- [ ] `tests/unit/test_queue_sorting.py` - Sort and filter
- [ ] `tests/unit/test_bulk_actions.py` - Bulk approve/reject

### Sprint 56 Tests
- [ ] `tests/unit/test_data_hygiene_api.py` - Hygiene API endpoints
- [ ] `tests/unit/test_data_hygiene_ui.py` - Dashboard page
- [ ] `tests/unit/test_duplicate_panel.py` - Duplicate detection display
- [ ] `tests/unit/test_merge_ui.py` - Merge functionality
- [ ] `tests/unit/test_quality_suggestions.py` - Suggestion panel
- [ ] `tests/unit/test_hygiene_connector.py` - External API connector

### Sprint 57 Tests
- [ ] `tests/unit/test_dashboard_metrics_real.py` - Real metrics not mocks
- [ ] `tests/unit/test_keyboard_nav.py` - Keyboard shortcuts
- [ ] `tests/unit/test_quick_actions.py` - Inline approve/reject
- [ ] `tests/unit/test_pending_badge.py` - Badge count
- [ ] `tests/unit/test_daily_summary.py` - Daily email task

### Sprint 58 Tests
- [ ] `tests/unit/test_error_state_ui.py` - Error component
- [ ] `tests/unit/test_retry_queue.py` - Retry queue model and service
- [ ] `tests/unit/test_retry_processor.py` - Background processor
- [ ] `tests/unit/test_recovery_panel.py` - Admin recovery UI
- [ ] `tests/unit/test_idempotency.py` - Idempotency keys
- [ ] `tests/unit/test_gmail_circuit_breaker.py` - Circuit breaker pattern
- [ ] `tests/unit/test_error_details_modal.py` - Error details modal

### Sprint 59 Tests
- [ ] Visual testing on mobile breakpoints
- [ ] Touch gesture testing
- [ ] Offline mode testing

---

## Appendix: Gap Analysis Summary (2026-01-28)

### API Endpoints Without UI (High Priority)

| API Route File | Endpoints | Gap Status |
|----------------|-----------|------------|
| `memory.py` | /sessions, /memory/{id}, /memory/search | Sprint 45 |
| `integrations_api.py` | /status, /available, /{app_name}/connect | Sprint 46 |
| `notifications.py` | /notifications, /mark-read | Sprint 47 |
| `analytics_api.py` | /metrics, /errors, /trends, /recovery/* | Sprint 48 |
| `admin.py` | /flags, /mode, /emergency-stop | Sprint 50-51 |

### Jinja2 Templates Status

| Template | Route | Status |
|----------|-------|--------|
| `base.html` | - | ✅ Active |
| `dashboard.html` | /caseyos | ✅ Active |
| `queue.html` | /caseyos/queue | ✅ Active |
| `queue_detail.html` | /caseyos/queue/{id} | ✅ Active |
| `gemini.html` | /caseyos/gemini | ✅ Active |
| `drive.html` | /caseyos/drive | ✅ Active |
| `agents.html` | /caseyos/agents | ✅ Active |
| `executions.html` | /caseyos/executions | ✅ Active |
| `signals.html` | /caseyos/signals | ✅ Active |
| `overview.html` | /caseyos/overview | ✅ Active |
| `voice_training.html` | /caseyos/voice-training | ✅ Active |
| `voice_profiles.html` | /caseyos/voice-profiles | ✅ Active |
| `memory.html` | /caseyos/memory | 🔲 Sprint 45 |
| `integrations.html` | /caseyos/integrations | 🔲 Sprint 46 |
| `notifications.html` | /caseyos/notifications | 🔲 Sprint 47 |
| `analytics.html` | /caseyos/analytics | 🔲 Sprint 48 |
| `settings.html` | /caseyos/settings | 🔲 Sprint 50 |
| `admin.html` | /caseyos/admin | 🔲 Sprint 51 |

### Legacy Static HTML (To Remove in Sprint 52)

| File | Replacement |
|------|-------------|
| `admin.html` | `admin.html` (Jinja2) |
| `agent-hub.html` | `agents.html` (Jinja2) |
| `agents.html` | `agents.html` (Jinja2) |
| `index.html` | `dashboard.html` (Jinja2) |
| `integrations.html` | `integrations.html` (Jinja2) |
| `operator-dashboard.html` | `overview.html` (Jinja2) |
| `queue-item-detail.html` | `queue_detail.html` (Jinja2) |
| `voice-profiles.html` | `voice_profiles.html` (Jinja2) |
| `voice-training.html` | `voice_training.html` (Jinja2) |

### Navigation Tabs Status

| Tab | Icon | Route | Status |
|-----|------|-------|--------|
| Dashboard | - | /caseyos | ✅ |
| Command Queue | - | /caseyos/queue | ✅ |
| Gemini | ✨ | /caseyos/gemini | ✅ |
| Drive | 📁 | /caseyos/drive | ✅ |
| Agents | 🤖 | /caseyos/agents | ✅ |
| Executions | ⚡ | /caseyos/executions | ✅ |
| Signals | 📡 | /caseyos/signals | ✅ |
| Overview | 📊 | /caseyos/overview | ✅ |
| Voice | 🎭 | /caseyos/voice-training | ✅ |
| Memory | 🧠 | /caseyos/memory | 🔲 Sprint 45 |
| Integrations | 🔌 | /caseyos/integrations | 🔲 Sprint 46 |
| Analytics | 📈 | /caseyos/analytics | 🔲 Sprint 48 |
| Settings | ⚙️ | /caseyos/settings | 🔲 Sprint 50 |
| Admin | 🔒 | /caseyos/admin | 🔲 Sprint 51 |

### Services & Agents Visibility

| Component | API Exposed | UI Surfaced |
|-----------|-------------|-------------|
| DashboardMetricsService | ✅ Sprint 43 | ✅ Overview |
| ContextService | ✅ Sprint 43 | 🔲 Gemini workflows |
| MemoryService | ✅ Sprint 15 | 🔲 Sprint 45 |
| NotificationService | ✅ Present | 🔲 Sprint 47 |
| ExecutionService | ✅ Sprint 42 | ✅ Executions page |
| SignalService | ✅ Sprint 8 | ✅ Signals page |
| VoiceService | ✅ Present | ✅ Voice Training |
| APSCalculator | ✅ Internal | ✅ Queue display |

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
*Version: 2.4*
*Updated: 2026-01-29 - Added Sprints 53-59 for signature system, OAuth health, queue polish, data hygiene, operator UX, resilience, and mobile*

## Appendix: Answer to User Questions (2026-01-29)

### Q1: Will placeholders in email signature go out when approved?
**Answer**: Currently YES - placeholders like `{sender_name}` could go out if the draft context wasn't properly populated. 

**Solution (Sprint 53)**: 
- Task 53.1-53.2: Add profile fields to User model and API
- Task 53.6: Inject user profile into draft context so `sender_name=user.display_name`
- Task 53.7: Display formatted signature in queue detail so operator can verify before send

### Q2: How to keep Google Account connected?
**Answer**: OAuth tokens are already stored encrypted in `oauth_tokens` table with auto-refresh via Celery task. However, the UI doesn't show connection status or handle refresh failures well.

**Solution (Sprint 54)**:
- Task 54.1-54.2: OAuth status API and UI cards showing connection health
- Task 54.3: Reconnect button when token expires or refresh fails
- Task 54.4: Notification when token is about to expire
- Task 54.5: Header indicator showing overall OAuth health

### Q3: What UI/UX gaps exist?
**Answer**: Key gaps identified:
1. **Draft Editing**: Can't edit subject/body before send (Sprint 55)
2. **Data Visibility**: No data quality metrics or duplicate detection (Sprint 56)
3. **Operator Efficiency**: No keyboard shortcuts, bulk actions, real metrics (Sprint 57)
4. **Error Recovery**: No visible retry queue or recovery options (Sprint 58)
5. **Mobile**: No responsive design for on-the-go approvals (Sprint 59)

### Q4: Integrate external hygiene repo or build native?
**Answer**: CaseyOS already has data hygiene agents at `src/agents/enrichment/`:
- `duplicate_watcher.py`
- `email_validator.py`
- `enrichment.py`

**Recommendation**: 
- Sprint 56.1-56.5: Surface existing agents via UI (primary)
- Sprint 56.6: Optional connector to external hygiene API if needed

---

## Appendix: Sprint Dependency Graph

```
Sprint 44 (Voice Profiles) ✅
    ↓
Sprint 53 (User Profile & Signature)
    ↓
Sprint 55 (Draft Editing & Queue Polish)
    ↓
Sprint 57 (Operator Experience)

Sprint 33 (OAuth Consolidation) ✅
    ↓
Sprint 54 (OAuth Token Health)

Sprint 30 (Observability) ✅
    ↓
Sprint 58 (Resilience & Recovery)

Existing Hygiene Agents
    ↓
Sprint 56 (Data Hygiene Dashboard)

Sprint 55-58
    ↓
Sprint 59 (Mobile & Responsive)
```

---

## Appendix: New Technical Debt Items (2026-01-29)

16. **User model missing profile fields** - display_name, job_title, signature_html (Sprint 53.1)
17. **Draft generator doesn't use user profile** - hardcoded fallback signature (Sprint 53.6)
18. **No OAuth status visibility** - users can't see if tokens are expired (Sprint 54.1-54.2)
19. **Queue items not editable** - no inline subject/body editing (Sprint 55.1-55.2)
20. **Data hygiene agents not surfaced** - no UI for duplicate detection (Sprint 56)
21. **Dashboard uses mock metrics** - hardcoded values instead of real queries (Sprint 57.1)
22. **No retry queue** - failed sends just fail, no automatic retry (Sprint 58.2-58.3)
23. **No idempotency protection** - duplicate requests could send duplicate emails (Sprint 58.5)
24. **Not mobile-responsive** - poor experience on phone/tablet (Sprint 59)
25. **OAuth redirect broken** - integrations page redirected to wrong URL (Sprint 60.1) ✅ FIXED
26. **send_draft doesn't actually send** - marked sent without Gmail API call (Sprint 60.3) ✅ FIXED
27. **No ABM campaign support** - can't do account-based burst campaigns (Sprint 62)
28. **No sequence automation** - manual follow-up only (Sprint 63)
29. **No SendGrid integration** - Gmail only, quota limits apply (Sprint 64)

---

## Sprint 60: Integration OAuth Fix & Real Send Enable ✅ COMPLETE
**Goal**: Fix broken OAuth redirect and enable real email sending from the UI.
**Demo**: Click "Connect Google Drive" → redirects to Google OAuth → returns connected. Send email from queue → actually arrives in recipient inbox.
**Status**: Completed 2026-01-29

### Task 60.1: Fix OAuth Redirect in Integrations API ✅
**Description**: The integrations API redirected to `/api/auth/google/authorize` which doesn't exist.
**Files**: `src/routes/integrations_api.py`
**Fix Applied**: Changed line 330 from `/api/auth/google/authorize` to `/auth/google?redirect=/caseyos/integrations`

### Task 60.3: Fix Send Draft Endpoint to Actually Send ✅
**Description**: The `/drafts/{id}/send` endpoint only marked drafts as sent without calling Gmail API.
**Files**: `src/routes/operator.py`
**Fix Applied**: Updated `send_draft` endpoint (lines 253-334) to:
- Check rate limits before sending
- Check `ALLOW_REAL_SENDS` setting
- Call `GmailConnector.send_email()` via Gmail API
- Return `gmail_message_id` and `gmail_thread_id` on success
- Proper error handling with status preservation on failure

---

## Sprint 61: Contact Data Enrichment Pipeline
**Goal**: Leverage existing contact data for automated personalization.
**Demo**: Import contact → auto-enrich with company/title data → personalization score visible in queue.

### Task 61.1: Create Contact Enrichment Celery Task
**Files**: `src/tasks/contact_enrichment_task.py`
**Validation**: New contact created → Celery task runs → contact has enrichment data
- [ ] Create `enrich_contact` Celery task
- [ ] Call `ContactEnrichmentService.enrich()`
- [ ] Store results in `custom_properties` JSONB
- [ ] Add to Celery beat schedule
- [ ] Commit: "feat(tasks): add contact enrichment background task"

### Task 61.2: Display Enrichment Data in Queue Detail
**Files**: `src/templates/queue_detail.html`, `src/routes/operator.py`
**Validation**: View queue item → see company, title, seniority, industry
- [ ] Fetch contact enrichment when loading queue item
- [ ] Display company info card
- [ ] Display contact info card
- [ ] Show personalization score
- [ ] Commit: "feat(ui): display contact enrichment in queue detail"

### Task 61.3: Calculate Personalization Score
**Files**: `src/services/personalization_scorer.py`
**Validation**: Draft with full context scores 80+, empty context scores <20
- [ ] Score: first_name (10), company_name (15), title (10), industry (10), pain_point (20), trigger_event (20)
- [ ] Return score 0-100 and missing data points
- [ ] Commit: "feat(services): personalization score calculator"

### Task 61.4: Show Personalization Score Badge in Queue
**Files**: `src/templates/queue.html`
**Validation**: Queue shows personalization badge (green 70+, yellow 40-69, red <40)
- [ ] Add `personalization_score` to queue item response
- [ ] Display score badge with tooltip
- [ ] Commit: "feat(ui): personalization score badge in queue"

### Task 61.5: Unit Tests for Enrichment Pipeline
**Files**: `tests/unit/test_contact_enrichment_task.py`, `tests/unit/test_personalization_scorer.py`
- [ ] Test enrichment task calls service
- [ ] Test scoring with full/missing context
- [ ] Commit: "test: add enrichment pipeline tests"

---

## Sprint 62: Account-Based Campaign Engine
**Goal**: Enable account-based burst campaigns with persona-based individual emails.
**Demo**: Create ABM campaign targeting 10 accounts × 3 personas = 30 personalized emails queued.

### Task 62.1: Create ABM Campaign Model
**Files**: `src/models/abm_campaign.py`
- [ ] `ABMCampaign` model with target_accounts, personas, sequence_id
- [ ] `ABMCampaignAccount` linking campaign to companies
- [ ] `ABMPersonaTarget` defining persona types
- [ ] Create Alembic migration
- [ ] Commit: "feat(models): add ABM campaign data model"

### Task 62.2: Build Campaign Email Generator
**Files**: `src/campaigns/abm_email_generator.py`
- [ ] Accept account context and persona context
- [ ] Use email_generator service with context injection
- [ ] Return subject, body, personalization score
- [ ] Commit: "feat(campaigns): ABM email generator"

### Task 62.3: Create ABM Campaign API Endpoints
**Files**: `src/routes/abm_campaigns.py`
- [ ] POST/GET `/api/abm-campaigns` - create/list
- [ ] GET `/api/abm-campaigns/{id}` - details
- [ ] POST `/api/abm-campaigns/{id}/generate` - generate emails
- [ ] POST `/api/abm-campaigns/{id}/launch` - queue for approval
- [ ] Commit: "feat(api): ABM campaign endpoints"

### Task 62.4: ABM Campaign UI - List and Create
**Files**: `src/templates/abm_campaigns.html`, `src/templates/abm_campaign_create.html`
- [ ] Campaign list with status badges
- [ ] Multi-step creation wizard
- [ ] Commit: "feat(ui): ABM campaigns list and create"

### Task 62.5: ABM Campaign UI - Detail View
**Files**: `src/templates/abm_campaign_detail.html`
- [ ] Campaign overview stats
- [ ] Account-by-account breakdown with email previews
- [ ] Generate All and Launch buttons
- [ ] Commit: "feat(ui): ABM campaign detail page"

### Task 62.6: Unit Tests for ABM Campaign
**Files**: `tests/unit/test_abm_campaign.py`
- [ ] Test model CRUD, email generation, bulk queuing
- [ ] Commit: "test: ABM campaign tests"

---

## Sprint 63: Email Sequence Automation
**Goal**: Multi-step email sequences with automatic follow-ups.
**Demo**: Create 3-step sequence → enroll contact → automatic follow-ups sent on schedule.

### Task 63.1: Persist Sequence Enrollments to Database
**Files**: `src/models/sequence.py`, `infra/migrations/`
- [ ] `Sequence` SQLAlchemy model
- [ ] `SequenceEnrollment` model with step tracking
- [ ] `SequenceStep` model
- [ ] Create Alembic migration
- [ ] Commit: "feat(models): sequence database models"

### Task 63.2: Sequence Step Executor Celery Task
**Files**: `src/tasks/sequence_executor.py`
- [ ] Query enrollments with due steps
- [ ] Generate and queue email for each
- [ ] Update step status
- [ ] Add to Celery beat (every 15 mins)
- [ ] Commit: "feat(tasks): sequence step executor"

### Task 63.3: Sequence Dashboard UI
**Files**: `src/templates/sequences.html`
- [ ] List all sequences with enrollee counts
- [ ] Quick actions: pause, resume, stop
- [ ] Commit: "feat(ui): sequence dashboard"

### Task 63.4: Reply Detection for Auto-Pause
**Files**: `src/webhooks/gmail_reply_detector.py`
- [ ] Poll Gmail for replies to sent emails
- [ ] Pause sequence on reply
- [ ] Log as signal
- [ ] Commit: "feat(webhooks): reply detection for sequences"

### Task 63.5: Unit Tests for Sequence Automation
**Files**: `tests/unit/test_sequence_executor.py`, `tests/unit/test_reply_detection.py`
- [ ] Commit: "test: sequence automation tests"

---

## Sprint 64: SendGrid Integration (High Volume)
**Goal**: Add SendGrid as email provider for high-volume campaigns.
**Demo**: Send 100 emails → routed through SendGrid → delivery tracking.

### Task 64.1: Create SendGrid Connector
**Files**: `src/connectors/sendgrid.py`
- [ ] Use `sendgrid` Python SDK
- [ ] Implement `send_email()` matching Gmail interface
- [ ] Commit: "feat(connectors): add SendGrid connector"

### Task 64.2: Add SendGrid Configuration
**Files**: `src/config.py`
- [ ] Add `SENDGRID_API_KEY`, `SENDGRID_SENDER_EMAIL` env vars
- [ ] Add `EMAIL_PROVIDER` enum (gmail, sendgrid, auto)
- [ ] Commit: "feat(config): add SendGrid configuration"

### Task 64.3: Create Email Router Service
**Files**: `src/services/email_router.py`
- [ ] Route emails based on config and volume
- [ ] Commit: "feat(services): email provider router"

### Task 64.4: SendGrid Webhook for Tracking
**Files**: `src/webhooks/sendgrid_webhook.py`
- [ ] Handle delivered, opened, clicked, bounced events
- [ ] Update email status in database
- [ ] Commit: "feat(webhooks): SendGrid delivery tracking"

### Task 64.5: Unit Tests for SendGrid Integration
**Files**: `tests/unit/test_sendgrid_connector.py`, `tests/unit/test_email_router.py`
- [ ] Commit: "test: SendGrid integration tests"

---

## Sprint 65: HubSpot Integration Enhancement
**Goal**: Better leverage HubSpot contact/company data for targeting.
**Demo**: View contact in CaseyOS → see full HubSpot history, deals, activities.

### Task 65.1: HubSpot Contact Deep Sync
**Files**: `src/connectors/hubspot.py`, `src/tasks/hubspot_sync.py`
- [ ] Sync: lifecycle_stage, lead_status, recent_deal_amount
- [ ] Sync: num_contacted_times, analytics_source
- [ ] Commit: "feat(hubspot): enhanced contact property sync"

### Task 65.2: Contact Activity Timeline API
**Files**: `src/routes/hubspot_routes.py`
- [ ] GET `/api/hubspot/contacts/{id}/timeline` returns activities
- [ ] Commit: "feat(api): contact activity timeline"

### Task 65.3: Contact and Company Profile Pages
**Files**: `src/templates/contact_profile.html`, `src/templates/company_profile.html`
- [ ] Full profile with HubSpot data, activity timeline, deals
- [ ] Commit: "feat(ui): contact and company profile pages"

### Task 65.4: Smart Contact List Builder
**Files**: `src/routes/contact_lists.py`, `src/templates/contact_list_builder.html`
- [ ] Filter by title, company size, industry, lifecycle stage
- [ ] Save as Smart List, export CSV, Add to Campaign
- [ ] Commit: "feat(ui): smart contact list builder"

### Task 65.5: Unit Tests for HubSpot Enhancements
**Files**: `tests/unit/test_hubspot_deep_sync.py`
- [ ] Commit: "test: HubSpot enhancement tests"

---

## Sprint 60-65 Dependency Graph

```
Sprint 60 (OAuth Fix + Real Send) ✅ COMPLETE
    ↓
Sprint 61 (Contact Enrichment)
    ↓
Sprint 62 (ABM Campaigns) ← Sprint 64 (SendGrid - optional)
    ↓
Sprint 63 (Sequence Automation)

Sprint 65 (HubSpot Enhancement) ← Can run parallel
```

---

*Updated: 2026-01-29 - Added Sprints 60-65 for integration fixes, ABM campaigns, sequences, SendGrid, and HubSpot enhancements*
*Version: 2.6*
