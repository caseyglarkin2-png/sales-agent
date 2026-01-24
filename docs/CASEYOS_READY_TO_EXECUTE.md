# CaseyOS: Ready to Execute (v2.0)

**Date:** January 24, 2026  
**Status:** 🟢 Sprint 7 Nearly Complete  
**Live System:** https://web-production-a6ccf.up.railway.app  
**Railway Project:** ideal-fascination (production environment)

---

## Current State

### ✅ Production Foundation (Sprint 6 - Complete)
- Security: CSRF protection, admin auth (`X-Admin-Token`), rate limiting
- GDPR: User deletion, draft cleanup, audit logging
- Monitoring: Health checks (`/health`, `/healthz`, `/ready`), Sentry integration (code ready)
- Operations: Circuit breakers, graceful shutdown, emergency rollback

### ✅ Command Queue Foundation (Sprint 7 - 95% Complete)
- [x] 7.1 Fixed production readiness check (DB session type)
- [x] 7.2 Set strong admin password in Railway
- [x] 7.3 Sentry DSN (deferred - not blocking)
- [x] 7.4 Command queue models + migration (`CommandQueueItem`, `ActionRecommendation`)
- [x] 7.5 APS calculator with unit tests (`src/services/aps_calculator.py`)
- [x] 7.6 `/api/command-queue/today` endpoint with APS ranking
- [x] 7.7 Static UI page (`/static/command-queue.html`)
- [x] 7.8 Seed endpoint (`POST /api/command-queue/seed`)
- [x] 7.9 Telemetry decorator + `log_event()`
- [x] 7.10 API docs (`docs/API_COMMAND_QUEUE.md`)
- [x] 7.11 Fixed telemetry module conflict
- [ ] 7.12 Production deploy verification + demo

### Existing Capabilities
- Form submission → Draft generation → HubSpot task creation
- Gmail draft creation, thread search
- HubSpot contact/company resolution
- Celery background tasks (worker service)
- PostgreSQL + Redis persistence
- Voice approval (JARVIS) UI

---

## Sprint Roadmap: Sales Agent → CaseyOS Transformation

### Design Principles
1. **Atomic Tasks**: One intent per PR, small diff, tight blast radius
2. **Testable**: Every task has validation (unit test, curl, or checklist)
3. **Demoable**: Every sprint ends with running, end-to-end software
4. **Composable**: Each sprint builds on prior work
5. **Named Specifically**: No "misc fixes" - if it matters, name it

---

## Sprint 7: Command Queue Foundation (Complete Remaining)

**Goal:** "Today's Moves" page showing APS-ranked recommendations with reasoning

**Demo Script:**
```bash
# 1. Verify health
curl https://web-production-a6ccf.up.railway.app/ready | jq

# 2. Seed demo items (get CSRF token first)
CSRF=$(curl -sD - https://web-production-a6ccf.up.railway.app/health -o /dev/null | awk -F': ' '/X-CSRF-Token/{print $2}' | tr -d '\r\n')
curl -X POST https://web-production-a6ccf.up.railway.app/api/command-queue/seed \
  -H "X-Admin-Token: $ADMIN_PASSWORD" -H "X-CSRF-Token: $CSRF" | jq

# 3. View Today's Moves API
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today | jq

# 4. Open UI
open https://web-production-a6ccf.up.railway.app/static/command-queue.html
```

### Remaining Tasks

| ID | Task | Validation |
|----|------|------------|
| 7.12 | Deploy to Railway and verify no 500s | `curl /health` returns 200; `/api/command-queue/today` returns items |

---

## Sprint 8: Signal Ingestion Framework

**Goal:** Auto-detect signals (form submissions, CRM changes, email replies) and generate recommendations automatically

**Demo Script:**
```bash
# Submit a test form → signal appears → recommendation generated
curl -X POST https://web-production-a6ccf.up.railway.app/api/webhooks/form \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","name":"Test User","company":"Acme"}' | jq

# Wait 30 seconds, then check signals
curl https://web-production-a6ccf.up.railway.app/api/signals | jq

# Check command queue for new recommendation
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today | jq '.today_moves[0]'
```

### Tasks

| ID | Task | Validation |
|----|------|------------|
| 8.1 | Create Signal model with fields: `id`, `source` (enum: FORM, HUBSPOT, GMAIL, MANUAL), `event_type`, `payload` (JSONB), `processed_at`, `created_at` | `python -c "from src.models.signal import Signal; print('OK')"` |
| 8.2 | Create signals migration (`infra/migrations/versions/20260124_signals.py`) | `alembic upgrade head` succeeds locally |
| 8.3 | Create SignalProcessor ABC with `process(signal: Signal) -> Optional[CommandQueueItem]` interface | Unit test: `test_signal_processor_interface.py` |
| 8.4 | Implement FormSubmissionSignalProcessor | Unit test: form payload → Signal created |
| 8.4.1 | Wire FormSubmissionSignalProcessor into existing form webhook (`src/webhook.py`) | `curl POST /webhooks/form` → signal row in DB |
| 8.4.2 | Unit tests for FormSubmissionSignalProcessor | `pytest tests/test_form_signal_processor.py` |
| 8.5 | Implement HubSpotDealSignalProcessor (use HubSpot recent deals API + store `last_checked` timestamp) | Unit test with mocked HubSpot response |
| 8.5.1 | Unit tests for HubSpotDealSignalProcessor | `pytest tests/test_hubspot_deal_signal_processor.py` |
| 8.6 | Verify Gmail readonly scope for thread polling (OAuth scopes check) | Document current scopes in code comment |
| 8.7 | Implement GmailReplySignalProcessor (query threads where `last_message_id != our_sent_message_id`) | Unit test with mocked Gmail response |
| 8.7.1 | Unit tests for GmailReplySignalProcessor | `pytest tests/test_gmail_reply_signal_processor.py` |
| 8.8 | Implement SignalToRecommendationService.convert() with action_type mapping | Unit test: signal → recommendation with correct action_type |
| 8.9 | Add Celery beat task: `poll_hubspot_signals` (every 5 min) | `celery -A src.celery_app beat --loglevel=info` shows scheduled task |
| 8.10 | Add Celery beat task: `poll_gmail_signals` (every 5 min) | Same as above |
| 8.11 | Add GET `/api/signals` endpoint (list recent signals with pagination) | `curl /api/signals?limit=10` returns JSON array |
| 8.12 | Add telemetry events: `signal_received`, `signal_processed`, `recommendation_generated` | Check structured logs after form submit |
| 8.13 | Document signal sources and event_type values in `docs/SIGNALS.md` | File exists with examples |
| 8.14 | Smoke test: Deploy to Railway + verify no 500s | `/api/signals` returns 200 |

---

## Sprint 9: One-Click Execution with Guardrails

**Goal:** Click "Execute" → action performed with audit trail, dry-run mode, and rollback capability

**Demo Script:**
```bash
# Get an item ID
ITEM_ID=$(curl -s https://web-production-a6ccf.up.railway.app/api/command-queue/today | jq -r '.today_moves[0].id')

# Dry-run execution (no side effects)
CSRF=$(curl -sD - https://web-production-a6ccf.up.railway.app/health -o /dev/null | awk -F': ' '/X-CSRF-Token/{print $2}' | tr -d '\r\n')
curl -X POST "https://web-production-a6ccf.up.railway.app/api/command-queue/$ITEM_ID/execute?dry_run=true" \
  -H "X-Admin-Token: $ADMIN_PASSWORD" -H "X-CSRF-Token: $CSRF" | jq

# Real execution
curl -X POST "https://web-production-a6ccf.up.railway.app/api/command-queue/$ITEM_ID/execute" \
  -H "X-Admin-Token: $ADMIN_PASSWORD" -H "X-CSRF-Token: $CSRF" \
  -H "X-Idempotency-Key: $(uuidgen)" | jq

# Check Gmail for created draft
```

### Tasks

| ID | Task | Validation |
|----|------|------------|
| 9.1 | Add status enum to CommandQueueItem: PENDING, EXECUTING, COMPLETED, FAILED, ROLLED_BACK | Model imports without error |
| 9.2 | Create ExecutionResult model: `id`, `item_id`, `action`, `status`, `result` (JSONB), `error`, `executed_at`, `dry_run` (bool) | Migration runs; model imports |
| 9.3 | Create ExecutionHandler ABC with `execute(item, dry_run) -> ExecutionResult` and `rollback(execution_id) -> bool` | Unit test for interface |
| 9.4 | Add dry-run mode infrastructure to execute endpoint (handler respects `dry_run` param) | `curl ?dry_run=true` returns result without side effects |
| 9.5 | Add idempotency key checking (X-Idempotency-Key header → store in Redis → return cached result) | Second call with same key returns 200 with cached result |
| 9.6 | Add rate limit tracking (Redis key: `rate_limit:{action_type}:{hour}`) | Unit test: 11th email in hour returns 429 |
| 9.7 | Implement SendEmailHandler (create Gmail draft using existing Gmail connector) | Integration test: execution → draft visible in Gmail |
| 9.8 | Implement CreateHubSpotTaskHandler (create HubSpot task using existing connector) | Integration test: execution → task visible in HubSpot |
| 9.9 | Implement BookMeetingHandler (Google Calendar API, create event with attendee) | Integration test: execution → event visible in Calendar |
| 9.9.1 | Manual test: Book meeting with real Google Calendar | Screenshot of created event |
| 9.10 | Add POST `/api/command-queue/{id}/execute` endpoint with dry_run query param | `curl -X POST /execute?dry_run=true` works |
| 9.11 | Add audit trail logging for all executions (who, when, what, result) | Check audit log after execution |
| 9.12 | Add rollback endpoint POST `/api/executions/{id}/rollback` | `curl -X POST /rollback` updates status |
| 9.13 | Add GET `/api/executions/{id}/status` endpoint for polling | Returns current execution state |
| 9.14 | Add Execute button to command-queue.html UI | Button visible, click triggers POST |
| 9.15 | Add confirmation modal before execution | Modal appears on click |
| 9.16 | Add execution failure UI state (error message display) | Error shown when execution fails |
| 9.17 | Add telemetry: `execution_started`, `execution_completed`, `execution_failed`, `dry_run_completed` | Logs appear after execution |
| 9.18 | Document execution handlers and rollback in `docs/EXECUTION.md` | File exists |
| 9.19 | Smoke test: Deploy to Railway + verify no 500s | All new endpoints return expected status codes |

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

| ID | Task | Validation |
|----|------|------------|
| 10.1 | Create OutcomeEvent model: `id`, `recommendation_id` (FK), `outcome_type` (enum: REPLY, MEETING_BOOKED, DEAL_PROGRESSED, NO_RESPONSE), `detected_at`, `metadata` (JSONB) | Migration runs; model imports |
| 10.2 | Create outcomes migration with FK to command_queue_items | `alembic upgrade head` |
| 10.3 | Implement ReplyDetector: poll Gmail threads, check for replies to our sent emails (24h lookback) | Unit test with mocked Gmail |
| 10.4 | Implement MeetingDetector: poll Calendar for events created after our BookMeeting execution | Unit test with mocked Calendar |
| 10.5 | Implement DealProgressionDetector: poll HubSpot for deal stage changes | Unit test with mocked HubSpot |
| 10.6 | Implement OutcomeRecorder.record(rec_id, outcome_type, metadata) service | Unit test: creates OutcomeEvent row |
| 10.7 | Add Celery beat task: `detect_outcomes` (every 10 min) | Beat log shows scheduled task |
| 10.8 | Add `get_outcome_success_rate(action_type)` query function | Unit test: returns float 0-1 |
| 10.9 | Update APS calculator: `aps_boost = base_aps * (1 + outcome_success_rate * 0.3)` | Unit test: historical success increases score |
| 10.10 | Add GET `/api/outcomes` endpoint (list recent outcomes) | `curl /api/outcomes` returns array |
| 10.11 | Add GET `/api/analytics/conversion-funnel` endpoint | Returns: total_sent, replies, meetings, deals |
| 10.12 | Add outcome stats to Today's Moves UI (success rate badge per action type) | Badge visible in UI |
| 10.13 | Add telemetry: `outcome_detected`, `outcome_recorded` | Logs appear after detection |
| 10.14 | Document outcome types and detection windows in `docs/OUTCOMES.md` | File exists |
| 10.15 | Smoke test: Deploy to Railway + verify no 500s | All endpoints 200 |

---

## Sprint 11: CaseyOS Dashboard Transformation

**Goal:** Replace sales-agent dashboard with unified CaseyOS command center

**Demo Script:**
```bash
# Visit root URL
open https://web-production-a6ccf.up.railway.app/

# Should redirect to /caseyos with full dashboard
# Test keyboard shortcuts: A, D, E, R
```

### Tasks

| ID | Task | Validation |
|----|------|------------|
| 11.1 | Create `src/static/caseyos/` folder structure: `index.html`, `styles.css`, `app.js` | Folder exists |
| 11.2 | Create `/caseyos` route serving dashboard HTML | `curl /caseyos` returns HTML |
| 11.3 | Build header component: logo ("CaseyOS"), nav links, API health indicator | Visual check |
| 11.4 | Build TodaysMoves widget: fetch `/api/command-queue/today`, render top 10 with APS, action buttons | Widget loads data |
| 11.5 | Build Signals widget: fetch `/api/signals`, show recent signals feed | Widget loads data |
| 11.6 | Build ExecutionHistory widget: fetch `/api/executions`, show recent actions | Widget loads data |
| 11.7 | Build OutcomeStats widget: fetch `/api/analytics/conversion-funnel`, show rates | Widget loads data |
| 11.8 | Build QuickActions panel: Seed, Refresh, Emergency Stop buttons | Buttons functional |
| 11.9 | Add keyboard shortcut: A = Accept selected item | Pressing A triggers accept |
| 11.10 | Add keyboard shortcut: D = Dismiss selected item | Pressing D triggers dismiss |
| 11.11 | Add keyboard shortcut: E = Execute selected item | Pressing E triggers execute modal |
| 11.12 | Add keyboard shortcut: R = Refresh all widgets | Pressing R refreshes data |
| 11.13 | Add real-time updates via polling (30s refresh) | Widgets update automatically |
| 11.14 | Add error boundary/fallback UI for widget failures | Error state visible when API fails |
| 11.15 | Add dark mode toggle (localStorage preference) | Toggle works, preference persisted |
| 11.16 | E2E test: Playwright script that loads dashboard, verifies all widgets | `npx playwright test` passes |
| 11.17 | Update `/` route to redirect to `/caseyos` | `curl -L /` ends at `/caseyos` |
| 11.18 | Update README with CaseyOS architecture diagram | Diagram in README |
| 11.19 | Smoke test: Deploy to Railway + verify no 500s | Dashboard loads fully |

---

## Sprint 12a: GTM Expansion - Marketing Ops

**Goal:** CaseyOS orchestrates marketing content repurposing and distribution

**Demo Script:**
```bash
# Filter by Marketing domain
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=marketing | jq

# View marketing-specific actions
```

### Tasks

| ID | Task | Validation |
|----|------|------------|
| 12a.1 | Add `domain` field (enum: SALES, MARKETING, CS) to CommandQueueItem model | Migration runs |
| 12a.2 | Add action_type: `content_repurpose` with ContentRepurposeHandler (generate 3 social post drafts from blog using OpenAI) | Handler returns drafts |
| 12a.3 | Add action_type: `distribution_checklist` with DistributionChecklistHandler (create task list for content distribution) | Handler returns checklist |
| 12a.4 | Create MarketingSignalProcessor (detect: blog published, webinar scheduled, campaign launched) | Unit test with mock events |
| 12a.5 | Add marketing-specific APS weights (higher urgency for time-sensitive content) | Unit test: blog post gets higher urgency |
| 12a.6 | Add `?domain=marketing` filter to `/api/command-queue/today` | Filter works |
| 12a.7 | Add Marketing tab to CaseyOS dashboard | Tab visible, filters work |
| 12a.8 | Integration tests for marketing workflows | Tests pass |
| 12a.9 | Smoke test: Deploy + verify | Marketing actions visible |

---

## Sprint 12b: GTM Expansion - Customer Success

**Goal:** CaseyOS orchestrates CS workflows: health checks, renewals, risk flags

**Demo Script:**
```bash
# Filter by CS domain
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=cs | jq
```

### Tasks

| ID | Task | Validation |
|----|------|------------|
| 12b.1 | Add action_type: `cs_health_check` with CSHealthCheckHandler (review customer activity, flag risks) | Handler returns health report |
| 12b.2 | Add action_type: `renewal_outreach` with RenewalOutreachHandler (generate renewal email draft) | Handler returns email draft |
| 12b.3 | Create CSSignalProcessor (detect: support ticket, usage drop, upcoming renewal date) | Unit test with mock events |
| 12b.4 | Add CS-specific APS weights (higher urgency for at-risk customers) | Unit test |
| 12b.5 | Add `?domain=cs` filter to `/api/command-queue/today` | Filter works |
| 12b.6 | Add CS tab to CaseyOS dashboard | Tab visible |
| 12b.7 | Integration tests for CS workflows | Tests pass |
| 12b.8 | Smoke test: Deploy + verify | CS actions visible |

---

## Success Metrics

### Sprint 7 (Command Queue):
- [x] "Today's Moves" page loads with recommendations
- [x] APS scores 0-100 with reasoning displayed
- [x] Telemetry events in logs
- [ ] Production deploy verified

### Sprint 8 (Signals):
- [ ] Form submission → recommendation in <30 seconds
- [ ] HubSpot deal change → recommendation in <5 minutes
- [ ] Gmail reply → recommendation in <5 minutes

### Sprint 9 (Execution):
- [ ] Execute → email draft in Gmail
- [ ] Execute → task in HubSpot
- [ ] Dry-run shows "would do" without side effects
- [ ] Duplicate idempotency key returns cached result

### Sprint 10 (Outcomes):
- [ ] Reply rate tracked (% replies within 24h)
- [ ] Meeting booking rate tracked
- [ ] APS increases for high-success action types

### Sprint 11 (Dashboard):
- [ ] `/` redirects to CaseyOS dashboard
- [ ] All widgets load data successfully
- [ ] Keyboard shortcuts work
- [ ] Dark mode toggle works

### Sprint 12a/12b (GTM):
- [ ] Marketing domain filter shows content tasks
- [ ] CS domain filter shows renewal/health tasks
- [ ] Domain-specific APS weights applied

---

## Rollback Plans

| Component | Rollback Method | Time |
|-----------|-----------------|------|
| Code changes | `git revert <commit>` | <2 min |
| Migrations | `alembic downgrade -1` | <2 min |
| Environment vars | Railway dashboard or `railway variable delete` | <1 min |
| UI changes | Delete static file, redeploy | <3 min |
| Feature flag | Set env var `FEATURE_X=false` | <1 min |

---

## File Structure (After Sprint 12)

```
/workspaces/sales-agent/
├── docs/
│   ├── CASEYOS_READY_TO_EXECUTE.md    ← This file
│   ├── API_COMMAND_QUEUE.md           ✅ Sprint 7
│   ├── SIGNALS.md                     🔨 Sprint 8
│   ├── EXECUTION.md                   🔨 Sprint 9
│   └── OUTCOMES.md                    🔨 Sprint 10
│
├── src/
│   ├── models/
│   │   ├── command_queue.py           ✅ Sprint 7
│   │   ├── signal.py                  🔨 Sprint 8
│   │   ├── execution.py               🔨 Sprint 9
│   │   └── outcome.py                 🔨 Sprint 10
│   │
│   ├── services/
│   │   ├── aps_calculator.py          ✅ Sprint 7
│   │   ├── signal_processors/         🔨 Sprint 8
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── form.py
│   │   │   ├── hubspot.py
│   │   │   └── gmail.py
│   │   ├── execution_handlers/        🔨 Sprint 9
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── send_email.py
│   │   │   ├── create_task.py
│   │   │   └── book_meeting.py
│   │   ├── outcome_detectors/         🔨 Sprint 10
│   │   │   ├── __init__.py
│   │   │   ├── reply.py
│   │   │   ├── meeting.py
│   │   │   └── deal.py
│   │   └── signal_to_recommendation.py 🔨 Sprint 8
│   │
│   ├── routes/
│   │   ├── command_queue.py           ✅ Sprint 7
│   │   ├── signals.py                 🔨 Sprint 8
│   │   ├── executions.py              🔨 Sprint 9
│   │   ├── outcomes.py                🔨 Sprint 10
│   │   └── caseyos.py                 🔨 Sprint 11
│   │
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
│   ├── test_signal_processors/        🔨 Sprint 8
│   ├── test_execution_handlers/       🔨 Sprint 9
│   └── test_outcome_detectors/        🔨 Sprint 10
│
└── infra/migrations/versions/
    ├── 20260123_command_queue.py      ✅ Sprint 7
    ├── 20260124_signals.py            🔨 Sprint 8
    ├── 20260125_executions.py         🔨 Sprint 9
    └── 20260126_outcomes.py           🔨 Sprint 10
```

---

## Ready to Execute

**Current Status:** Sprint 7 nearly complete. Awaiting production deploy verification.

**Next Action:** 
1. Verify Sprint 7.12 (production deploy) 
2. Begin Sprint 8.1 (Signal model)

**Estimated Effort:**
- Sprint 8: ~15 atomic tasks
- Sprint 9: ~19 atomic tasks  
- Sprint 10: ~15 atomic tasks
- Sprint 11: ~19 atomic tasks
- Sprint 12a: ~9 atomic tasks
- Sprint 12b: ~8 atomic tasks

**Total:** ~85 atomic, independently testable tasks

---

**Last Updated:** 2026-01-24  
**Railway Project:** ideal-fascination  
**Live URL:** https://web-production-a6ccf.up.railway.app
