# CaseyOS: Ready to Execute (v3.1)

**Date:** January 24, 2026  
**Status:** 🟢 Sprint 11-12 Complete  
**Live System:** https://web-production-a6ccf.up.railway.app  
**CaseyOS Dashboard:** https://web-production-a6ccf.up.railway.app/caseyos  
**Railway Project:** ideal-fascination (production environment)

---

## Executive Summary

Transform the Sales Agent dashboard into **CaseyOS** - a GTM command center that operates as Casey Larkin's Chief of Staff. The system proactively ingests signals, prioritizes work via Action Priority Score (APS), executes with guardrails, and closes the loop on outcomes.

**Total Sprints:** 8 → 12b (5 major sprints + 2 expansion sprints)  
**Total Atomic Tasks:** ~110 independently testable pieces of work  
**Target:** Production-ready GTM orchestration platform

---

## Design Principles

1. **Atomic Tasks:** One intent per PR, small diff, tight blast radius
2. **Testable:** Every task has validation (unit test, curl, or checklist)
3. **Demoable:** Every sprint ends with running, end-to-end software
4. **Composable:** Each sprint builds on prior work
5. **Named Specifically:** No "misc fixes" - if it matters, name it
6. **Production-First:** Error handling, monitoring, and rollback baked in

---

## Current State (January 24, 2026)

### ✅ Production Foundation (Sprints 1-6 - Complete)
- Security: CSRF protection, admin auth (`X-Admin-Token`), rate limiting
- GDPR: User deletion, draft cleanup, audit logging
- Monitoring: Health checks (`/health`, `/healthz`, `/ready`), Sentry integration ready
- Operations: Circuit breakers, graceful shutdown, emergency rollback
- Database: PostgreSQL with async SQLAlchemy, connection pooling

### ✅ Command Queue Foundation (Sprint 7 - Complete)
- [x] CommandQueueItem + ActionRecommendation models
- [x] APS calculator with unit tests (`src/services/aps_calculator.py`)
- [x] `/api/command-queue/today` endpoint with APS ranking
- [x] Static UI page (`/static/command-queue.html`)
- [x] Seed endpoint (`POST /api/command-queue/seed`)
- [x] Telemetry decorator + `log_event()`
- [x] API docs (`docs/API_COMMAND_QUEUE.md`)

### ✅ Signal Ingestion (Sprint 8 - Complete)
- [x] Signal model with SignalSource enum (FORM, HUBSPOT, GMAIL, MANUAL)
- [x] Signals migration (table created in production)
- [x] SignalProcessor ABC interface
- [x] FormSubmissionSignalProcessor + unit tests
- [x] Wire into form webhook
- [x] GET /api/signals endpoint
- [x] docs/SIGNALS.md documentation

### ✅ Execution with Guardrails (Sprint 9 - Complete)
- [x] Execute endpoint with dry-run mode
- [x] Idempotency key support
- [x] Rate limiting per action type
- [x] Audit trail logging
- [x] Execution handlers (SendEmail, CreateTask)

### ✅ Closed-Loop Outcome Tracking (Sprint 10 - Complete)
- [x] OutcomeRecord model with 18 outcome types
- [x] POST /api/outcomes/record endpoint
- [x] GET /api/outcomes/stats endpoint
- [x] GET /api/outcomes/contact/{email} endpoint
- [x] APS score adjustment based on contact history
- [x] Auto-detection endpoints (gmail-reply, deal-change, meeting)

### ✅ CaseyOS Dashboard (Sprint 11 - Complete)
- [x] Full dashboard at `/caseyos` with header, stats, widgets
- [x] Domain tabs (All/Sales/Marketing/CS)
- [x] Today's Moves widget with action buttons
- [x] Recent Signals widget
- [x] Execution History widget
- [x] Quick Actions panel
- [x] Keyboard shortcuts (A/D/E/R/j/k)
- [x] 30-second auto-refresh
- [x] Dark mode toggle
- [x] Execute modal with dry-run preview
- [x] Toast notifications

### ✅ GTM Domain Expansion (Sprint 12 - Complete)
- [x] DomainType enum (SALES, MARKETING, CS)
- [x] `domain` field on CommandQueueItem with index
- [x] Marketing action types: content_repurpose, social_post, newsletter_draft, asset_create
- [x] CS action types: cs_health_check, renewal_outreach, risk_escalation, onboarding_follow_up
- [x] `/api/command-queue/today?domain=X` filter
- [x] Domain tabs functional in dashboard

### Existing UI Pages (`src/static/`)
- `caseyos/index.html` - **CaseyOS Command Center** (NEW - Primary UI)
- `index.html` - Legacy dashboard with JARVIS voice/text
- `agents.html` - Agent activity
- `command-queue.html` - Original Today's Moves
- `jarvis.html` - Voice approval interface
- `voice-profiles.html` - Voice profile management
- `admin.html` - Admin panel
- `integrations.html` - Integration settings

---

## Sprint 8: Signal Ingestion Framework (Complete Remaining)

**Goal:** Auto-detect signals (form submissions, CRM changes, email replies) and generate recommendations automatically

**Demo Script:**
```bash
# Submit a test form → signal appears → recommendation generated
curl -X POST https://web-production-a6ccf.up.railway.app/api/webhooks/hubspot/form-submission \
  -H "Content-Type: application/json" \
  -d '{"form_name":"Test","fields":{"email":"test@example.com","firstname":"Test","company":"Acme"}}' | jq

# Check signals
curl https://web-production-a6ccf.up.railway.app/api/signals | jq

# Check command queue for new recommendation
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today | jq '.today_moves[0]'
```

### Remaining Tasks

| ID | Task | Validation | Priority |
|----|------|------------|----------|
| 8.5 | Create HubSpotDealSignalProcessor (poll recent deals API + store `last_checked` timestamp) | Unit test with mocked HubSpot response | HIGH |
| 8.5.1 | Handle OAuth token expiration in HubSpotDealSignalProcessor (trigger refresh, retry) | Unit test: expired token → refresh → retry succeeds | HIGH |
| 8.6 | Verify Gmail readonly scope for thread polling (document current scopes in code comment) | Comment in `src/connectors/gmail.py` listing scopes | MEDIUM |
| 8.7 | Create GmailReplySignalProcessor (query threads where `last_message_id != our_sent_message_id`) | Unit test with mocked Gmail response | HIGH |
| 8.7.1 | Handle Gmail threading edge cases (forwarded, BCC'd messages) | Unit test for edge cases | MEDIUM |
| 8.8 | Create SignalToRecommendationService.convert() with action_type mapping | Unit test: signal → recommendation with correct action_type | HIGH |
| 8.9 | Add Celery beat task: `poll_hubspot_signals` (every 5 min) in central config | `celery -A src.celery_app beat` shows scheduled task | HIGH |
| 8.10 | Add Celery beat task: `poll_gmail_signals` (every 5 min) in central config | Same as above | HIGH |
| 8.12 | Add telemetry events: `signal_received`, `signal_processed`, `recommendation_generated` | Check structured logs after form submit | MEDIUM |
| 8.14 | Smoke test: Deploy to Railway + verify no 500s | `/api/signals` returns 200 | HIGH |
| 8.15 | Add composite index `idx_signals_source_processed` on (source, processed_at) | `EXPLAIN ANALYZE` shows index scan | HIGH |
| 8.16 | Add rate limiting to signal processors (max 100 signals/batch) | Unit test: batch size capped; logs show "batch truncated" | MEDIUM |
| 8.17 | Add signal deduplication by payload hash within 5-minute window | Unit test: same hash in 5m → skipped with log | MEDIUM |
| 8.18 | Add health check endpoint for Celery beat (`/health/beat`) | `curl /health/beat` returns last-run timestamps | MEDIUM |

---

## Sprint 9: One-Click Execution with Guardrails

**Goal:** Click "Execute" → action performed with audit trail, dry-run mode, and rollback capability

**Split:** This sprint is large. Consider splitting into 9a (Core) and 9b (Handlers + UI).

**Demo Script:**
```bash
# Get an item ID
ITEM_ID=$(curl -s https://web-production-a6ccf.up.railway.app/api/command-queue/today | jq -r '.today_moves[0].id')

# Dry-run execution (no side effects)
curl -X POST "https://web-production-a6ccf.up.railway.app/api/command-queue/$ITEM_ID/execute?dry_run=true" \
  -H "X-Admin-Token: $ADMIN_PASSWORD" | jq

# Real execution
curl -X POST "https://web-production-a6ccf.up.railway.app/api/command-queue/$ITEM_ID/execute" \
  -H "X-Admin-Token: $ADMIN_PASSWORD" \
  -H "X-Idempotency-Key: $(uuidgen)" | jq

# Check Gmail for created draft
```

### Sprint 9a: Core Execution Infrastructure

| ID | Task | Validation | Priority |
|----|------|------------|----------|
| 9.0 | Add composite index `idx_executions_item_status` on (item_id, status) | Migration includes index; query plan uses index | HIGH |
| 9.1 | Add status enum to CommandQueueItem: PENDING, EXECUTING, COMPLETED, FAILED, ROLLED_BACK | Model imports without error | HIGH |
| 9.2 | Create ExecutionResult model: `id`, `item_id`, `action`, `status`, `result` (JSONB), `error`, `executed_at`, `dry_run` (bool) | Migration runs; model imports | HIGH |
| 9.3 | Create ExecutionHandler ABC with `execute(item, dry_run) -> ExecutionResult` and `rollback(execution_id) -> bool` | Unit test for interface | HIGH |
| 9.4 | Add dry-run mode infrastructure to execute endpoint (handler respects `dry_run` param) | `curl ?dry_run=true` returns result without side effects | HIGH |
| 9.5 | Add idempotency key checking (X-Idempotency-Key header → store in Redis with 24h TTL) | Second call with same key returns 200 with cached result | HIGH |
| 9.5.1 | Add key collision detection (409 Conflict for in-flight keys) | Unit test: concurrent same-key requests return 409 | HIGH |
| 9.6 | Add rate limit tracking (Redis key: `rate_limit:{action_type}:{hour}`) | Unit test: 11th email in hour returns 429 | HIGH |
| 9.10 | Add POST `/api/command-queue/{id}/execute` endpoint with dry_run query param | `curl -X POST /execute?dry_run=true` works | HIGH |
| 9.11 | Add audit trail logging for all executions (who, when, what, result) | Check audit log after execution | HIGH |
| 9.12 | Add rollback endpoint POST `/api/executions/{id}/rollback` | `curl -X POST /rollback` updates status | MEDIUM |
| 9.13 | Add GET `/api/executions/{id}/status` endpoint for polling | Returns current execution state | MEDIUM |
| 9.17 | Add telemetry: `execution_started`, `execution_completed`, `execution_failed`, `dry_run_completed` | Logs appear after execution | HIGH |
| 9.20 | Add transaction isolation (`SELECT FOR UPDATE`) for execute endpoint | Unit test: concurrent requests → only one executes | HIGH |
| 9.21 | Add execution timeout (30s) with asyncio.wait_for and graceful cancellation | Unit test: slow handler → timeout → status=FAILED | HIGH |
| 9.22 | Add circuit breaker wrapping for each ExecutionHandler | Unit test: 5 failures → circuit opens → fast-fail 60s | HIGH |
| 9.24 | Add `X-Execution-ID` and `X-Request-ID` response headers for traceability | Response includes headers; can grep logs by ID | MEDIUM |
| 9.25 | Add execution retry logic (3 retries with exponential backoff for transient failures) | Unit test: 503 → retry → success on attempt 2 | MEDIUM |

### Sprint 9b: Execution Handlers + UI

| ID | Task | Validation | Priority |
|----|------|------------|----------|
| 9.7a | Create SendEmailHandler skeleton with interface compliance | Handler class exists, implements ABC | HIGH |
| 9.7b | Implement Gmail API draft creation in SendEmailHandler | Integration test: execution → draft visible in Gmail | HIGH |
| 9.7c | Add rollback (delete draft) support to SendEmailHandler | Rollback deletes draft | MEDIUM |
| 9.8 | Implement CreateHubSpotTaskHandler (create HubSpot task using existing connector) | Integration test: execution → task visible in HubSpot | HIGH |
| 9.9.0 | Add Google Calendar OAuth scope (`calendar.events`) and document re-consent flow | Scope added; doc updated | HIGH |
| 9.9a | Create BookMeetingHandler skeleton | Handler class exists | MEDIUM |
| 9.9b | Implement Calendar event creation with attendee | Integration test: execution → event visible | MEDIUM |
| 9.9c | Add rollback (cancel event) support to BookMeetingHandler | Rollback cancels event | MEDIUM |
| 9.14 | Add Execute button to command-queue.html UI | Button visible, click triggers POST | HIGH |
| 9.15 | Add confirmation modal before execution | Modal appears on click | MEDIUM |
| 9.16 | Add execution failure UI state (error message display) | Error shown when execution fails | MEDIUM |
| 9.18 | Document execution handlers and rollback in `docs/EXECUTION.md` | File exists | MEDIUM |
| 9.19 | Smoke test: Deploy to Railway + verify no 500s | All new endpoints return expected status codes | HIGH |
| 9.23 | Add execution queueing for rate-limited actions (queue instead of 429) | Integration test: 11th email queued, processed next hour | LOW |
| 9.26 | Load test execute endpoint (100 concurrent requests with k6/locust) | p99 latency < 500ms under load | HIGH |

---

## Sprint 10: Closed-Loop Outcome Tracking

**Goal:** Track outcomes (reply, meeting, deal progression) → improve APS scoring

**Demo Script:**
```bash
# Check outcomes
curl https://web-production-a6ccf.up.railway.app/api/outcomes | jq

# Check conversion funnel
curl https://web-production-a6ccf.up.railway.app/api/analytics/conversion-funnel | jq

# View Today's Moves with outcome-boosted APS
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today | jq '.today_moves[0].aps'
```

### Tasks

| ID | Task | Validation | Priority |
|----|------|------------|----------|
| 10.1 | Create OutcomeEvent model: `id`, `recommendation_id` (FK), `outcome_type` (enum), `detected_at`, `metadata` (JSONB) | Migration runs; model imports | HIGH |
| 10.2 | Create outcomes migration with FK to command_queue_items and index on (recommendation_id, detected_at DESC) | `alembic upgrade head` | HIGH |
| 10.3a | Implement ReplyDetector: query Gmail for threads with sent messages | Unit test with mocked Gmail | HIGH |
| 10.3b | Detect reply by comparing message IDs | Unit test: new message → reply detected | HIGH |
| 10.3c | Handle threading edge cases (forwarded, BCC'd) | Unit test for edge cases | MEDIUM |
| 10.4 | Implement MeetingDetector: poll Calendar for events created after BookMeeting execution | Unit test with mocked Calendar | HIGH |
| 10.5 | Implement DealProgressionDetector: poll HubSpot for deal stage changes | Unit test with mocked HubSpot | HIGH |
| 10.6 | Implement OutcomeRecorder.record(rec_id, outcome_type, metadata) service | Unit test: creates OutcomeEvent row | HIGH |
| 10.7 | Add Celery beat task: `detect_outcomes` (every 10 min) | Beat log shows scheduled task | HIGH |
| 10.8 | Add `get_outcome_success_rate(action_type)` query function | Unit test: returns float 0-1 | HIGH |
| 10.9 | Update APS calculator: `aps_boost = base_aps * (1 + outcome_success_rate * 0.3)` | Unit test: historical success increases score | HIGH |
| 10.10 | Add GET `/api/outcomes` endpoint (list recent outcomes) | `curl /api/outcomes` returns array | HIGH |
| 10.11 | Add GET `/api/analytics/conversion-funnel` endpoint | Returns: total_sent, replies, meetings, deals | HIGH |
| 10.12 | Add outcome stats to Today's Moves UI (success rate badge per action type) | Badge visible in UI | MEDIUM |
| 10.13 | Add telemetry: `outcome_detected`, `outcome_recorded` | Logs appear after detection | MEDIUM |
| 10.14 | Document outcome types and detection windows in `docs/OUTCOMES.md` | File exists | MEDIUM |
| 10.15 | Smoke test: Deploy to Railway + verify no 500s | All endpoints 200 | HIGH |
| 10.16 | Add dead-letter queue for failed outcome detection | Unit test: API error → event in DLQ → retried | MEDIUM |
| 10.17 | Add NO_RESPONSE detection after 72h timeout | Unit test: old recommendation without reply → NO_RESPONSE | MEDIUM |
| 10.18 | Add outcome attribution window config (env var: `OUTCOME_ATTRIBUTION_WINDOW_HOURS=72`) | Config loaded; detection respects window | LOW |

---

## Sprint 11: CaseyOS Dashboard Transformation ✅ COMPLETE

**Status:** ✅ Complete (January 24, 2026)  
**Commits:** `97fa05e`, `2ac8aae`  
**Documentation:** [docs/SPRINT_11_12_COMPLETE.md](SPRINT_11_12_COMPLETE.md)

**Goal:** Replace sales-agent dashboard with unified CaseyOS command center

**Live URLs:**
- Dashboard: https://web-production-a6ccf.up.railway.app/caseyos
- Health: https://web-production-a6ccf.up.railway.app/caseyos/health

**Files Created:**
- `src/static/caseyos/index.html` - Full dashboard with widgets
- `src/static/caseyos/styles.css` - CSS with dark mode
- `src/static/caseyos/app.js` - JavaScript with keyboard shortcuts
- `src/routes/caseyos_ui.py` - FastAPI routes

**Features Delivered:**
- [x] Header with domain tabs (All/Sales/Marketing/CS)
- [x] Health indicator
- [x] Stats row (Pending, Completed, Reply Rate, Net Impact, Signals)
- [x] Today's Moves widget with action buttons
- [x] Recent Signals widget
- [x] Execution History widget
- [x] Quick Actions panel
- [x] Execute modal with dry-run preview
- [x] Keyboard shortcuts (A/D/E/R/j/k navigation)
- [x] 30-second auto-refresh
- [x] Dark mode toggle
- [x] Toast notifications
- [x] Responsive design

### Sprint 11a: Dashboard Foundation ✅

| ID | Task | Validation | Priority | Status |
|----|------|------------|----------|--------|
| 11.0 | Add API version header (`X-API-Version: v1`) to all responses | All API responses include header | HIGH | ✅ |
| 11.1 | Create `src/static/caseyos/` folder structure: `index.html`, `styles.css`, `app.js` | Folder exists | HIGH | ✅ |
| 11.2 | Create `/caseyos` route serving dashboard HTML | `curl /caseyos` returns HTML | HIGH | ✅ |
| 11.3 | Build header component: logo ("CaseyOS"), nav links, API health indicator | Visual check | HIGH | ✅ |
| 11.20 | Add loading skeleton states for each widget | Visual: skeleton visible before data | HIGH | ✅ |
| 11.14 | Add error boundary/fallback UI for widget failures | Error state visible when API fails | HIGH | ✅ |

### Sprint 11b: Dashboard Widgets ✅

| ID | Task | Validation | Priority | Status |
|----|------|------------|----------|--------|
| 11.4a | Create TodaysMoves widget container with loading/error states | Widget shell renders | HIGH | ✅ |
| 11.4b | Implement TodaysMoves fetch + render logic | Widget loads data from `/api/command-queue/today` | HIGH | ✅ |
| 11.4c | Add action buttons (Accept, Dismiss, Execute) to TodaysMoves | Buttons visible, API calls work | HIGH | ✅ |
| 11.4d | Add item selection/focus state for keyboard navigation | Arrow keys move selection | MEDIUM | ✅ |
| 11.5 | Build Signals widget: fetch `/api/signals`, show recent signals feed | Widget loads data | HIGH | ✅ |
| 11.6 | Build ExecutionHistory widget: fetch `/api/executions`, show recent actions | Widget loads data | HIGH | ✅ |
| 11.7 | Build OutcomeStats widget: fetch `/api/analytics/conversion-funnel`, show rates | Widget loads data | HIGH | ✅ |
| 11.8 | Build QuickActions panel: Seed, Refresh, Emergency Stop buttons | Buttons functional | MEDIUM | ✅ |

### Sprint 11c: Dashboard Interactivity ✅

| ID | Task | Validation | Priority | Status |
|----|------|------------|----------|--------|
| 11.9 | Add keyboard shortcut: A = Accept selected item | Pressing A triggers accept | MEDIUM | ✅ |
| 11.10 | Add keyboard shortcut: D = Dismiss selected item | Pressing D triggers dismiss | MEDIUM | ✅ |
| 11.11 | Add keyboard shortcut: E = Execute selected item | Pressing E triggers execute modal | MEDIUM | ✅ |
| 11.12 | Add keyboard shortcut: R = Refresh all widgets | Pressing R refreshes data | MEDIUM | ✅ |
| 11.13 | Add real-time updates via polling (30s refresh) | Widgets update automatically | HIGH | ✅ |
| 11.15 | Add dark mode toggle (localStorage preference) | Toggle works, preference persisted | LOW | ✅ |
| 11.21 | Add browser notification for high-APS recommendations (>0.9) | Notification API permission; alert appears | LOW | Deferred |
| 11.22 | Add widget collapse/expand state persistence (localStorage) | Refresh → state preserved | LOW | Deferred |

### Sprint 11d: Dashboard Polish + Launch ✅

| ID | Task | Validation | Priority | Status |
|----|------|------------|----------|--------|
| 11.16 | E2E test: Playwright script that loads dashboard, verifies all widgets | `npx playwright test` passes | HIGH | Deferred |
| 11.17 | Update `/` route to redirect to `/caseyos` (with deprecation warning header) | `curl -L /` ends at `/caseyos` | HIGH | Deferred |
| 11.18 | Update README with CaseyOS architecture diagram | Diagram in README | MEDIUM | Deferred |
| 11.19 | Smoke test: Deploy to Railway + verify no 500s | Dashboard loads fully | HIGH | ✅ |

---

## Sprint 12: GTM Expansion ✅ COMPLETE

**Status:** ✅ Complete (January 24, 2026)  
**Commits:** `97fa05e`, `2ac8aae`  
**Documentation:** [docs/SPRINT_11_12_COMPLETE.md](SPRINT_11_12_COMPLETE.md)

**Goal:** Add Marketing Ops and Customer Success action types to CaseyOS

**Live URLs:**
- All domains: https://web-production-a6ccf.up.railway.app/api/command-queue/today
- Sales: https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=sales
- Marketing: https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=marketing
- CS: https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=cs

**Files Changed:**
- `src/models/command_queue.py` - Added DomainType enum, domain field
- `src/routes/command_queue.py` - Added /today endpoint with domain filter
- `infra/migrations/versions/20260124_*` - Domain migration

### Sprint 12a: GTM Expansion - Marketing Ops ✅

| ID | Task | Validation | Priority | Status |
|----|------|------------|----------|--------|
| 12a.1 | Add `domain` field (enum: SALES, MARKETING, CS) to CommandQueueItem model | Migration runs | HIGH | ✅ |
| 12a.2 | Add action_type: `content_repurpose` | Handler returns drafts | HIGH | ✅ |
| 12a.3 | Add action_type: `social_post` | Handler available | MEDIUM | ✅ |
| 12a.4 | Add action_type: `newsletter_draft` | Handler available | MEDIUM | ✅ |
| 12a.5 | Add action_type: `asset_create` | Handler available | MEDIUM | ✅ |
| 12a.6 | Add `?domain=marketing` filter to `/api/command-queue/today` | Filter works | HIGH | ✅ |
| 12a.7 | Add Marketing tab to CaseyOS dashboard | Tab visible, filters work | HIGH | ✅ |
| 12a.8 | Integration tests for marketing workflows | Tests pass | HIGH | Deferred |
| 12a.9 | Smoke test: Deploy + verify | Marketing actions visible | HIGH | ✅ |
| 12a.10 | Add content repurpose preview modal | Preview modal works | MEDIUM | Deferred |

### Sprint 12b: GTM Expansion - Customer Success ✅

| ID | Task | Validation | Priority | Status |
|----|------|------------|----------|--------|
| 12b.1 | Add action_type: `cs_health_check` | Handler returns health report | HIGH | ✅ |
| 12b.2 | Add action_type: `renewal_outreach` | Handler returns email draft | HIGH | ✅ |
| 12b.3 | Add action_type: `risk_escalation` | Handler available | HIGH | ✅ |
| 12b.4 | Add action_type: `onboarding_follow_up` | Handler available | HIGH | ✅ |
| 12b.5 | Add `?domain=cs` filter to `/api/command-queue/today` | Filter works | HIGH | ✅ |
| 12b.6 | Add CS tab to CaseyOS dashboard | Tab visible | HIGH | ✅ |
| 12b.7 | Integration tests for CS workflows | Tests pass | HIGH | Deferred |
| 12b.8 | Smoke test: Deploy + verify | CS actions visible | HIGH | ✅ |
| 12b.9 | Add CS risk score calculation | Unit test: score 0-100 | MEDIUM | Deferred |

---

## Demo Script (Sprint 11-12)

```bash
# 1. Open CaseyOS Dashboard
open https://web-production-a6ccf.up.railway.app/caseyos

# 2. Check dashboard health
curl -s https://web-production-a6ccf.up.railway.app/caseyos/health | jq
# {"status": "ok", "dashboard": "caseyos"}

# 3. Get Today's Moves (all domains)
curl -s https://web-production-a6ccf.up.railway.app/api/command-queue/today | jq '.today_moves | length'

# 4. Filter by Sales domain
curl -s "https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=sales" | jq

# 5. Filter by Marketing domain
curl -s "https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=marketing" | jq

# 6. Filter by CS domain
curl -s "https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=cs" | jq

# 7. Test keyboard shortcuts in browser:
# - Press 'j' to select next item
# - Press 'k' to select previous item
# - Press 'A' to accept
# - Press 'D' to dismiss
# - Press 'E' to open execute modal
# - Press 'R' to refresh
# - Press '?' to see shortcuts

# 8. Toggle dark mode
# - Click sun/moon icon in header
```

---

## Technical Debt Backlog

Address these items before or alongside feature sprints:

| Item | Description | Priority | Sprint to Address |
|------|-------------|----------|-------------------|
| TD-1 | Consolidate duplicate CircuitBreaker implementations (`resilience.py` vs `retry.py`) | HIGH | Before Sprint 9 |
| TD-2 | Add FK constraints to `lead_id` and `contact_id` fields | MEDIUM | Sprint 9 migration |
| TD-3 | Standardize async patterns (`get_db()` vs `get_async_db()`) | MEDIUM | Sprint 8 |
| TD-4 | Add database connection pool monitoring (`pool_pre_ping=True`) | HIGH | Sprint 8 |
| TD-5 | Centralize Celery beat schedule (not scattered across modules) | HIGH | Sprint 8 |
| TD-6 | Add `X-Request-ID` middleware for log correlation | HIGH | Sprint 9 |
| TD-7 | Add integration tests for command queue endpoints | HIGH | Sprint 8 |
| TD-8 | Consider CDN/nginx for static file serving in Sprint 11 | LOW | Sprint 11 |

---

## Production Readiness Checklist

| Category | Current | Required | Sprint |
|----------|---------|----------|--------|
| **Alerting** | None | PagerDuty/Slack for: circuit breaker open, execution failures >10%, 5xx rate >1% | Pre-Sprint 9 |
| **Database Backups** | `init_db.sql` exists | Daily automated backups with 30-day retention | Document in runbook |
| **Secrets Rotation** | OAuth auto-refresh | Add rotation SOP for API keys (HubSpot, OpenAI) | Pre-Sprint 12 |
| **Load Testing** | None | k6/locust on execute endpoint (100 concurrent) | Sprint 9 |
| **Error Budget** | Not defined | SLO: 99.9% uptime, <500ms p99 latency | Pre-Sprint 11 |
| **Rollback Testing** | Documented | Test rollback for each migration in staging | Each sprint |

---

## Success Metrics

### Sprint 8 (Signals)
- [ ] Form submission → recommendation in <30 seconds
- [ ] HubSpot deal change → recommendation in <5 minutes
- [ ] Gmail reply → recommendation in <5 minutes
- [ ] Signal deduplication prevents duplicates within 5-minute window

### Sprint 9 (Execution)
- [ ] Execute → email draft in Gmail in <3 seconds
- [ ] Execute → task in HubSpot in <3 seconds
- [ ] Dry-run shows "would do" without side effects
- [ ] Duplicate idempotency key returns cached result
- [ ] Concurrent executions on same item → only one executes
- [ ] p99 latency < 500ms under 100 concurrent requests

### Sprint 10 (Outcomes) ✅
- [x] Reply rate tracked (% replies within 24h)
- [x] Meeting booking rate tracked
- [x] APS increases for high-success action types
- [x] Outcome types and stats API

### Sprint 11 (Dashboard) ✅
- [x] CaseyOS dashboard at `/caseyos`
- [x] All widgets load data successfully
- [x] Keyboard shortcuts work (A, D, E, R, j, k)
- [x] Dark mode toggle works
- [ ] `/` redirects to CaseyOS dashboard (deferred)
- [ ] Playwright E2E tests (deferred)

### Sprint 12a/12b (GTM) ✅
- [x] Marketing domain filter shows content tasks
- [x] CS domain filter shows renewal/health tasks
- [x] Domain tabs functional in dashboard
- [x] New action types for Marketing and CS
- [ ] Domain-specific APS weights (deferred)

---

## Rollback Plans

| Component | Rollback Method | Time |
|-----------|-----------------|------|
| Code changes | `git revert <commit>` | <2 min |
| Migrations | `alembic downgrade -1` | <2 min |
| Environment vars | Railway dashboard | <1 min |
| UI changes | Delete static file, redeploy | <3 min |
| Feature flag | Set env var `FEATURE_X=false` | <1 min |

---

## File Structure (After Sprint 12)

```
/workspaces/sales-agent/
├── docs/
│   ├── CASEYOS_READY_TO_EXECUTE.md    ← This file
│   ├── SPRINT_11_12_COMPLETE.md       ✅ Sprint 11-12 docs
│   ├── API_COMMAND_QUEUE.md           ✅ Sprint 7
│   ├── SIGNALS.md                     ✅ Sprint 8
│   ├── EXECUTION.md                   🔨 Future
│   ├── OUTCOMES.md                    🔨 Future
│   └── API_VERSIONING.md              🔨 Future
│
├── src/
│   ├── models/
│   │   ├── command_queue.py           ✅ Sprint 7 + 12 (domain field)
│   │   ├── signal.py                  ✅ Sprint 8
│   │   ├── execution.py               ✅ Sprint 9
│   │   └── outcome.py                 ✅ Sprint 10
│   │
│   ├── outcomes/                      ✅ Sprint 10
│   │   ├── __init__.py
│   │   ├── service.py
│   │   └── detector.py
│   │
│   ├── services/
│   │   ├── aps_calculator.py          ✅ Sprint 7
│   │   ├── signal_service.py          ✅ Sprint 8
│   │   ├── signal_processors/         ✅ Sprint 8
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── form.py
│   │   │   ├── hubspot.py             🔨
│   │   │   └── gmail.py               🔨
│   │   ├── execution_handlers/        ✅ Sprint 9
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── send_email.py
│   │   │   └── create_task.py
│   │   └── signal_to_recommendation.py ✅ Sprint 8
│   │
│   ├── routes/
│   │   ├── command_queue.py           ✅ Sprint 7 + 12 (/today, domain filter)
│   │   ├── signals.py                 ✅ Sprint 8
│   │   ├── executions.py              ✅ Sprint 9
│   │   ├── outcomes.py                ✅ Sprint 10
│   │   └── caseyos_ui.py              ✅ Sprint 11
│   │
│   └── static/
│       └── caseyos/                   ✅ Sprint 11
│           ├── index.html
│           ├── styles.css
│           └── app.js
│
│   ├── static/
│   │   ├── command-queue.html         ✅ Sprint 7
│   │   └── caseyos/                   🔨 Sprint 11
│   │       ├── index.html
│   │       ├── styles.css
│   │       └── app.js
│   │
│   ├── tasks/
│   │   ├── signal_polling.py          🔨 Sprint 8
│   │   └── outcome_detection.py       🔨 Sprint 10
│   │
│   └── telemetry.py                   ✅ Sprint 7
│
├── tests/
│   ├── test_aps_calculator.py         ✅ Sprint 7
│   ├── test_form_signal_processor.py  ✅ Sprint 8 (12 tests)
│   ├── test_hubspot_signal_processor.py 🔨 Sprint 8
│   ├── test_gmail_signal_processor.py  🔨 Sprint 8
│   ├── test_execution_handlers/       🔨 Sprint 9
│   └── test_outcome_detectors/        🔨 Sprint 10
│
└── infra/migrations/versions/
    ├── 20260123_command_queue.py      ✅ Sprint 7
    ├── 20260124_signals.py            ✅ Sprint 8
    ├── 20260125_executions.py         🔨 Sprint 9
    └── 20260126_outcomes.py           🔨 Sprint 10
```

---

## Dependency Graph

```
Sprint 7 (Command Queue) ──┬──> Sprint 8 (Signals) ──> Sprint 9 (Execution) ──> Sprint 10 (Outcomes)
                           │                                    │                       │
                           │                                    v                       v
                           └──────────────────────> Sprint 11 (Dashboard) <────────────┘
                                                           │
                                                           v
                                            ┌──────────────┴──────────────┐
                                            │                             │
                                            v                             v
                                    Sprint 12a (Marketing)      Sprint 12b (CS)
```

---

## Quick Reference: Current Sprint Tasks

### Sprint 8 Remaining (Signal Ingestion)

**High Priority:**
1. 8.5 - HubSpotDealSignalProcessor
2. 8.7 - GmailReplySignalProcessor  
3. 8.8 - SignalToRecommendationService.convert()
4. 8.9 - Celery beat: poll_hubspot_signals
5. 8.10 - Celery beat: poll_gmail_signals
6. 8.14 - Smoke test: Deploy + verify
7. 8.15 - Add composite index for signals

**Medium Priority:**
1. 8.5.1 - Handle OAuth token expiration
2. 8.6 - Verify Gmail scopes
3. 8.7.1 - Handle threading edge cases
4. 8.12 - Telemetry events
5. 8.16 - Rate limiting for processors
6. 8.17 - Signal deduplication
7. 8.18 - Celery beat health check

---

## Immediate Next Actions

1. **Verify Signal Fix Deployed:** Test form webhook creates signals in production
2. **Complete Sprint 8.5:** Implement HubSpotDealSignalProcessor
3. **Complete Sprint 8.7:** Implement GmailReplySignalProcessor
4. **Wire Celery Beat:** Add polling tasks to central schedule

---

**Last Updated:** 2026-01-24T19:00:00Z  
**Railway Project:** ideal-fascination  
**Live URL:** https://web-production-a6ccf.up.railway.app  
**Total Atomic Tasks:** ~110
