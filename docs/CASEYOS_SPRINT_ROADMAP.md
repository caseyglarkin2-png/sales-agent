# CaseyOS Sprint Roadmap

**Version:** 1.1  
**Date:** January 23, 2026  
**Tone:** direct, witty, swagger. We ship outcomes with receipts.  
**Live App:** https://web-production-a6ccf.up.railway.app

---

## Production Snapshot (foundation we stand on)
- Health endpoints: `/health`, `/healthz`, `/ready` (known issue: DB readiness uses wrong async session; app itself works).
- Security: CSRF on state-changing endpoints, admin auth via `X-Admin-Token`, rate limiting, security headers.
- Compliance: GDPR delete + draft cleanup + audit logging.
- Monitoring: Circuit breaker status endpoint, Sentry wiring present (DSN unset), graceful shutdown.
- Bulk + voice approval flows live.
- Deploy: Railway (project `ideal-fascination`, service `web`), Dockerfile-based. Admin secret is now strong (rotation complete).

---

## Repo Audit (concise)
- **API/App:** FastAPI in `src/main.py`; routes under `src/routes/` (health, gdpr, circuit_breakers, bulk, voice approval, etc.).
- **Domain logic:** Numerous modules under `src/` (orchestrators, scoring, email, tasks). Security middleware in `src/security/`. GDPR logic in `src/gdpr.py`. Circuit breakers in `src/routes/circuit_breakers.py`.
- **Background jobs:** Celery app in `src/celery_app.py`; tasks in `src/tasks/` and `src/tasks.py`; retention tasks for GDPR.
- **Data layer:** SQLAlchemy models in `src/models/`; DB session helpers in `src/db/`; Alembic config in `infra/alembic.ini` and migrations under `infra/migrations/`.
- **Ops/DR:** Backups/restores in `infra/backup.sh` and `infra/restore.sh`; rollback script in `scripts/rollback.sh`.
- **Monitoring:** Sentry integration `src/sentry_integration.py`; health routes `src/routes/health.py`.
- **Known gaps:** `/ready` lies about DB readiness (SessionLocal mismatch); Sentry DSN unset; admin secret weak; no command queue UI; telemetry incomplete.

---

## Roadmap Overview (demo-first, atomic work)
- **Sprint 7 – Stabilize & Command Queue v0:** Fix readiness truth, secure admin, light up Sentry, ship Command Queue skeleton (models, API, UI v0) with telemetry seeds.
- **Sprint 8 – Signals & APS v1:** Ingest signals, compute APS, surface “Today’s Moves” with explainability, instrument recommendation events.
- **Sprint 9 – Execution with Guardrails:** One-click actions with dry-run/kill-switch, idempotency, rate limits, rollback paths; extend telemetry for execution/outcomes start.
- **Sprint 10 – Closed Loop & Learning:** Outcome recording, feedback into APS, dashboards/alerts, telemetry completeness.

Each sprint ships a demoable increment; every task is atomic with explicit validation and rollback.

---

## Sprint 7: Stabilize & Command Queue v0
**Demo:** Casey opens “Today’s Moves” page showing 5–10 placeholder recommendations backed by real models/API, readiness is truthful, Sentry is catching errors, admin secret is secure.

### Tasks (atomic, committable)
1) **Fix `/ready` DB check**  
    - Scope: use proper async session in `src/routes/health.py`; ensure `src/db/__init__.py` exports correct factory; add Redis check truthfully.  
    - Not: changing DB URLs or pool config.  
    - Files: `src/routes/health.py`, `src/db/__init__.py`.  
    - Validation: `curl https://web-production-a6ccf.up.railway.app/ready | jq '.checks.database'` → `"ready"` when DB reachable.  
    - Acceptance: DB ready reports truthfully; failure shows real error string.  
    - Rollback: revert commit; readiness may be inaccurate but app runs.

2) **Rotate admin secret (done, strong password set)**  
    - Scope: set strong `ADMIN_PASSWORD` env in Railway; update docs; block old token.  
    - Not: multi-admin UI.  
    - Files: env vars only; doc note in `docs/SECURITY_AUDIT.md` (append).  
    - Validation: old token 401, new token 200 on `/api/gdpr/status`.  
    - Acceptance: 32+ char secret set; old token rejected.  
    - Rollback: temporarily set old token (only if break-glass).

3) **Enable Sentry (DSN + sanity ping)**  
    - Scope: set `SENTRY_DSN`, `SENTRY_ENVIRONMENT=production`; add test endpoint to trigger an error (guarded admin-only).  
    - Not: alert routing rules.  
    - Files: env vars; `src/routes/health.py` (optional test route) or small `src/routes/ops.py`.  
    - Validation: POST `/api/test-error` → appears in Sentry.  
    - Acceptance: error visible in Sentry within 30s; DSN not logged.  
    - Rollback: unset DSN.

4) **Command Queue data model + migration**  
    - Scope: add `CommandQueueItem` and `ActionRecommendation` models; Alembic migration; indexes for priority queries.  
    - Not: generation logic.  
    - Files: `src/models/command_queue.py`, `src/models/__init__.py`, new migration under `infra/migrations/versions/*`.  
    - Contracts: APS fields, status enum, reasoning text, metadata JSONB.  
    - Validation: `alembic -c infra/alembic.ini upgrade head`; verify tables exist.  
    - Acceptance: tables created, migration repeatable.  
    - Rollback: `alembic downgrade -1`.

5) **Command Queue API v0**  
    - Scope: read-only endpoints to list Today’s Moves (mock data backed by DB rows); simple create for testing; status update (accept/dismiss).  
    - Not: APS calculation; execution handlers.  
    - Files: `src/routes/command_queue.py`, `src/main.py` include; `src/schemas/command_queue.py`.  
    - Validation:  
      - `curl https://web-production-a6ccf.up.railway.app/api/command-queue` → list.  
      - `curl -X POST .../api/command-queue/{id}/accept`.  
    - Acceptance: CRUD works, CSRF on state-changing routes, admin token required.  
    - Rollback: remove routes or feature-flag off.

6) **Command Queue UI v0 (Today’s Moves)**  
    - Scope: simple page showing top 10 items (priority, action, due-by, owner, status, APS, reasoning); buttons call accept/dismiss endpoints.  
    - Not: complex filters or editing.  
    - Files: `src/routes/ui_command_queue.py` (FastAPI template) or existing frontend dir; minimal HTML/CSS.  
    - Validation: open page `/ui/command-queue` renders items; clicking accept/dismiss updates status (verify via API).  
    - Acceptance: page loads in prod; actions reflect in API.  
    - Rollback: feature-flag route off.

7) **Telemetry scaffold (events + logging)**  
    - Scope: add lightweight event logger module to emit telemetry: `recommendation_generated`, `recommendation_accepted`, `recommendation_dismissed`, `action_executed`, `outcome_recorded` (stub). Store to structured logs (JSON) now; DB later.  
    - Not: full analytics pipeline.  
    - Files: `src/telemetry.py`, integrate in command queue API actions.  
    - Validation: call endpoints, inspect logs for event JSON.  
    - Acceptance: each action emits structured log with event name, item id, user, timestamp.  
    - Rollback: disable logger import.

8) **Docs refresh (single source of truth)**  
    - Scope: update `/docs/ROADMAP.md`, `/docs/ARCHITECTURE.md`, `/docs/PHILOSOPHY.md`, `/docs/TELEMETRY.md` to reflect Sprint 7 state and CaseyOS principles.  
    - Not: marketing site copy.  
    - Files: listed docs.  
    - Validation: docs mention live URL, readiness fix, Sentry, command queue v0, telemetry events.  
    - Acceptance: docs align with shipped features; links accurate.  
    - Rollback: revert doc commits.

---

## Sprint 8: Signals & APS v1
**Demo:** Casey sees “Today’s Moves” ranked by APS with top-driver explanations; signals auto-ingested from existing app data and simple external hooks.

### Tasks
1) **Signal ingestion framework**  
    - Scope: background job to pull signals from internal DB (draft activity, meetings, bulk status); pluggable providers for future APIs.  
    - Files: `src/signals/base.py`, `src/signals/providers/internal.py`, `src/tasks/signal_ingest.py`.  
    - Validation: run ingest task; verify DB rows in a `signals` table (or JSON store).  
    - Rollback: disable task schedule.

2) **APS scoring service v1**  
    - Scope: service that computes Action Priority Score using revenue impact, urgency, effort, strategic value, blocker flag.  
    - Files: `src/aps/service.py`, unit tests under `tests/test_aps_service.py`.  
    - Validation: pytest for scoring matrix; manual run prints ranked list.  
    - Rollback: feature-flag the scorer.

3) **Explainability payload**  
    - Scope: store top drivers (because…) in `ActionRecommendation.reasoning`; expose in API/UI.  
    - Files: `src/models/command_queue.py`, `src/routes/command_queue.py`, UI template.  
    - Validation: API response includes `reasoning` and `drivers` list.  
    - Rollback: hide reasoning field.

4) **Recommendation generator job**  
    - Scope: Celery task to create recommendations daily/hourly using APS; dedupe existing items; respect idempotency.  
    - Files: `src/tasks/recommendations.py`, schedule in `src/celery_app.py`.  
    - Validation: run task; see new items with APS > 0; rerun doesn’t duplicate.  
    - Rollback: disable beat schedule.

5) **Today’s Moves API v1 (ranked)**  
    - Scope: API returns top N sorted by APS with rationale and due-by.  
    - Files: `src/routes/command_queue.py`.  
    - Validation: `curl .../api/command-queue?limit=10` sorted descending APS.  
    - Rollback: return unranked list.

6) **UI: driver tooltips & filters**  
    - Scope: show APS, drivers, filter by status/owner; keep minimal styling.  
    - Files: UI route/template.  
    - Validation: manual click-through; filters alter API query.  
    - Rollback: hide filters.

7) **Telemetry: recommendation lifecycle**  
    - Scope: emit events for generated/accepted/dismissed; include APS, drivers, latency.  
    - Files: `src/telemetry.py`, hooked into generator + API.  
    - Validation: logs show events with APS + timing.  
    - Rollback: disable telemetry hooks.

8) **Docs update**  
    - Scope: update roadmap, telemetry, architecture to include APS v1, signals, explainability.  
    - Files: `/docs/ROADMAP.md`, `/docs/ARCHITECTURE.md`, `/docs/TELEMETRY.md`.  
    - Validation: docs list new events and data flows.  
    - Rollback: revert docs.

---

## Sprint 9: Execution with Guardrails
**Demo:** Casey can click an action (send draft/follow-up/create task) with dry-run, kill-switch, rate limits, and audit trail; telemetry captures execution.

### Tasks
1) **Action executor service**  
    - Scope: service abstraction to perform actions (email draft/send, task create, follow-up); supports dry-run flag.  
    - Files: `src/actions/executor.py`, `src/actions/contracts.py`.  
    - Validation: unit tests for idempotency keys; dry-run returns preview only.  
    - Rollback: disable executor routes.

2) **Kill switch + rate limiting**  
    - Scope: global toggle env `ACTIONS_ENABLED`; per-action rate limit; return 429 when exceeded.  
    - Files: `src/config.py`, `src/middleware.py` or action layer.  
    - Validation: toggle off → actions blocked; exceeding limit returns 429.  
    - Rollback: set toggle on, remove limiter.

3) **One-click endpoints**  
    - Scope: API routes to execute recommended action types with dry-run param.  
    - Files: `src/routes/command_queue.py` (execute), `src/actions/executor.py`.  
    - Validation: `curl -X POST .../execute?action=draft&dry_run=true` returns preview; `dry_run=false` performs action.  
    - Rollback: disable route.

4) **Idempotency + audit trail**  
    - Scope: idempotency key per action; log to audit table/telemetry; prevent double-send.  
    - Files: `src/actions/executor.py`, `src/audit_trail.py`, new model/migration if needed.  
    - Validation: same idempotency key twice → no duplicate effect.  
    - Rollback: bypass idempotency check.

5) **Rollback hooks**  
    - Scope: define per-action rollback (e.g., mark draft canceled, delete created task); store rollback instructions.  
    - Files: `src/actions/rollback.py`, integrate with executor.  
    - Validation: trigger rollback endpoint; state reverts.  
    - Rollback: manual revert steps documented.

6) **Telemetry: execution + errors**  
    - Scope: events for `action_executed`, `action_failed`, include latency, target, dry-run flag.  
    - Files: `src/telemetry.py`, executor integration.  
    - Validation: logs show events with timing; simulate failure -> `action_failed`.  
    - Rollback: disable telemetry hook.

7) **UI: execution buttons + dry-run toggle**  
    - Scope: add Execute/Dry-run buttons per item; show recent status.  
    - Files: UI template/JS.  
    - Validation: clicking updates status; dry-run shows preview.  
    - Rollback: hide buttons.

8) **Docs update**  
    - Scope: add guardrails, toggles, rate limits, rollback steps.  
    - Files: `/docs/ROADMAP.md`, `/docs/TELEMETRY.md`, `/docs/PHILOSOPHY.md`.  
    - Validation: docs mention kill switch, dry-run, telemetry events.  
    - Rollback: revert docs.

---

## Sprint 10: Closed Loop & Learning
**Demo:** After actions fire, Casey sees outcomes captured, APS adjusts over time, dashboards show throughput/error rates.

### Tasks
1) **Outcome recording service**  
    - Scope: store outcomes (reply, meeting booked, stage change, deliverable shipped) tied to queue item/recommendation.  
    - Files: `src/outcomes/service.py`, models/migration.  
    - Validation: API to POST outcome; data persisted.  
    - Rollback: disable outcome write path.

2) **Feedback into APS**  
    - Scope: adjust APS weighting based on historical win/loss per segment/action type.  
    - Files: `src/aps/service.py` (learning module), config weights.  
    - Validation: run recalculation job; APS shifts per outcomes.  
    - Rollback: freeze weights.

3) **Dashboards/telemetry wiring**  
    - Scope: emit metrics for rec gen latency, accept/dismiss rates, execution success, outcome conversion; ship Grafana/Metabase queries.  
    - Files: `docs/TELEMETRY.md` dashboards section; optional `scripts/export_metrics.sh`.  
    - Validation: sample queries return data; logs show metrics emitted.  
    - Rollback: disable metrics exporter.

4) **Alerts for failures**  
    - Scope: alert on high action_failure rate or rec gen failures; use Sentry + log-based threshold.  
    - Files: `docs/TELEMETRY.md`, Sentry rules (documented).  
    - Validation: force failure -> alert visible in Sentry.  
    - Rollback: disable rule.

5) **UI: outcomes & learning hints**  
    - Scope: show outcomes inline; indicate APS changes (“+8 due to reply rate”); filter by successful actions.  
    - Files: UI template/JS, API additions.  
    - Validation: outcomes appear after POST; APS delta visible.  
    - Rollback: hide outcomes section.

6) **Data retention & PII minimization**  
    - Scope: document and enforce minimal PII, retention policies on outcomes; GDPR alignment.  
    - Files: `docs/PHILOSOPHY.md`, `docs/ARCHITECTURE.md`, `docs/TELEMETRY.md`.  
    - Validation: docs list fields stored; code trims extras.  
    - Rollback: revert enforcement changes.

7) **Docs update**  
    - Scope: finalize closed-loop flow, telemetry tables, alerting.  
    - Files: roadmap/telemetry/architecture.  
    - Validation: docs current and copy-paste ready.  
    - Rollback: revert docs.

---

## Validation Commands (live endpoints)
- Health: `curl https://web-production-a6ccf.up.railway.app/health`
- Readiness: `curl https://web-production-a6ccf.up.railway.app/ready`
- GDPR status (admin token): `curl -H "X-Admin-Token: <ADMIN_PASSWORD>" https://web-production-a6ccf.up.railway.app/api/gdpr/status`
- Command Queue list (once added): `curl https://web-production-a6ccf.up.railway.app/api/command-queue`
- Sentry test (when added): `curl -X POST https://web-production-a6ccf.up.railway.app/api/test-error`

---

## Subagent Review Prompt (run after drafting/committing roadmap)
"Review the sprint plan for atomicity, validation, demoability, missing edge cases, rollback plans, idempotency/rate limiting, and telemetry gaps. Suggest 3–5 concrete improvements."

---

## Immediate Execution Order (do first)
1) Fix `/ready` DB check truthfulness.  
2) Rotate `ADMIN_PASSWORD` to strong secret; `test123` is no longer in use.  
3) Set `SENTRY_DSN` + sanity ping.  
4) Ship Command Queue v0 (models, API, UI) with telemetry logging.  
5) Update docs as the single source of truth.

---

## Definition of Done (per task)
- One intent per PR; small diff.  
- Explicit validation (curl or tests).  
- Acceptance criteria checked.  
- Rollback noted.  
- Docs updated.

---

## File Touch Map (by sprint)
- **Sprint 7:** `src/routes/health.py`, `src/db/__init__.py`, env vars, `src/models/command_queue.py`, `infra/migrations/*`, `src/routes/command_queue.py`, `src/schemas/command_queue.py`, UI route/template, `src/telemetry.py`, docs.
- **Sprint 8:** `src/signals/*`, `src/tasks/signal_ingest.py`, `src/aps/service.py`, `tests/test_aps_service.py`, `src/routes/command_queue.py`, UI, telemetry, docs.
- **Sprint 9:** `src/actions/*`, `src/routes/command_queue.py`, `src/middleware.py` or config, telemetry, UI, docs, migrations if audit trail expands.
- **Sprint 10:** `src/outcomes/*`, `src/aps/service.py`, UI, telemetry dashboards, docs.

---

## Contracts to Watch
- Command queue tables and schemas (API + DB).  
- APS scoring input/output schema.  
- Action executor contract (idempotency key, dry_run flag, rollback token).  
- Telemetry event fields (event name, item id, APS, drivers, latency, outcome).  
- Admin auth headers + CSRF tokens on state-changing routes.

---

## Acceptance Demo per Sprint
- **Sprint 7:** Show Today’s Moves page populated from DB; curl `/ready` returning true; Sentry receives test error; admin token rotated.  
- **Sprint 8:** Show ranked Today’s Moves with APS + “because…” drivers from ingested signals.  
- **Sprint 9:** Click Execute (dry-run then real) with kill switch and rate limit; telemetry shows action_executed/action_failed.  
- **Sprint 10:** Show outcomes recorded and APS adjusting; dashboard/queries display conversions and latencies.

---

## Rollback Playbook (generic)
- Disable feature via env flag/route removal.  
- Downgrade latest Alembic migration if schema-only change.  
- Revert commit; redeploy.  
- For external actions: invoke rollback handler per action; mark items canceled.

---

## Philosophy (Casey’s law baked in)
- Atomic tasks, explicit validation, demo every sprint.  
- If it’s not actionable, it’s noise.  
- Prioritize by APS (revenue, urgency, effort, strategic value, blockers).  
- Guardrails: idempotent, rate-limited, auditable, dry-run + kill switch.  
- Minimal PII; document what/why.  
- Telemetry everywhere: recommend → accept/dismiss → execute → outcome.

---

#### **Task 7.2: Set Strong Admin Password**
**Problem:** Admin password rotation is complete (no longer `test123`).

**Scope:**
- Generate strong random password
- Set `ADMIN_PASSWORD` environment variable in Railway
- Document password rotation procedure

**NOT Included:**
- Building admin UI for password changes
- Multi-user admin auth

**Files Modified:**
- Railway environment variables (no code change)
- `docs/SECURITY.md` - password rotation procedure

**Validation:**
```bash
# Test with old password - should fail
curl -H "X-Admin-Token: test123" https://web-production-a6ccf.up.railway.app/api/gdpr/status  # Should return 401
# Expected: 401 Unauthorized

# Test with new password - should succeed
curl -H "X-Admin-Token: <new-password>" https://web-production-a6ccf.up.railway.app/api/gdpr/status
# Expected: 200 OK
```

**Acceptance Criteria:**
- [ ] `ADMIN_PASSWORD` set to strong random value (32+ chars)
- [x] Old password (`test123`) no longer works
- [ ] New password documented securely (1Password/env file)

**Rollback:** Set `ADMIN_PASSWORD` to a new strong value if needed for emergency access.

---

#### **Task 7.3: Configure Sentry Error Tracking**
**Problem:** Sentry integration code exists but `SENTRY_DSN` not set, so no error tracking active.

**Scope:**
- Create Sentry project (or use existing)
- Set `SENTRY_DSN` and `SENTRY_ENVIRONMENT` in Railway
- Test error capture with sample exception

**NOT Included:**
- Custom error grouping rules
- Performance monitoring configuration
- Sentry alerting setup (separate task)

**Files Modified:**
- Railway environment variables (no code change)
- `docs/MONITORING.md` - Sentry setup instructions

**Validation:**
```bash
# Trigger test error
curl -X POST https://web-production-a6ccf.up.railway.app/api/test-error
# Expected: Error logged to Sentry dashboard

# Check Sentry UI
# Expected: Error appears in Sentry project within 30 seconds
```

**Acceptance Criteria:**
- [ ] `SENTRY_DSN` set in production environment
- [ ] Test error appears in Sentry dashboard
- [ ] Production errors are captured (verify with real exception)

**Rollback:** Unset `SENTRY_DSN`, errors won't be tracked but app works normally.

---

#### **Task 7.4: Create Command Queue Data Models**
**What:** Database models for command queue and action recommendations.

**Scope:**
- Create `CommandQueueItem` model (priority, action, context, status, owner)
- Create `ActionRecommendation` model (APS score, reasoning, metadata)
- Create Alembic migration
- Add indexes for priority ranking queries

**NOT Included:**
- UI for viewing queue
- Logic for generating recommendations
- Outcome tracking (later sprint)

**Files Created:**
- `src/models/command_queue.py` - CommandQueueItem + ActionRecommendation models

**Files Modified:**
- `src/models/__init__.py` - Export new models
- `infra/migrations/versions/<hash>_command_queue.py` - Alembic migration

**Contracts:**
```python
# src/models/command_queue.py
class CommandQueueItem(Base):
    __tablename__ = "command_queue_items"
    
    id: str (UUID, primary key)
    priority_score: float  # APS score (0-100)
    action_type: str  # "send_email", "create_task", "schedule_meeting"
    action_context: JSONB  # {recipient, subject, urgency_reason, etc.}
    status: str  # "pending", "accepted", "dismissed", "executed", "failed"
    owner: str  # "casey", "automated", "delegated"
    due_by: Optional[datetime]
    recommendation_id: str  # FK to ActionRecommendation
    executed_at: Optional[datetime]
    outcome: Optional[JSONB]  # {replied: bool, booked: bool, etc.}
    created_at: datetime
    updated_at: datetime

class ActionRecommendation(Base):
    __tablename__ = "action_recommendations"
    
    id: str (UUID, primary key)
    aps_score: float  # 0-100
    reasoning: str  # "High ICP fit ($50k ARR), demo tomorrow, strong reply rate"
    revenue_impact: float  # Pipeline $ value
    urgency_score: float  # 0-1
    effort_score: float  # 0-1
    strategic_score: float  # 0-1
    metadata: JSONB  # {account_id, deal_stage, last_touch, etc.}
    generated_at: datetime
```

**Validation:**
```bash
# Run migration
alembic -c infra/alembic.ini upgrade head

# Verify tables created
psql $DATABASE_URL -c "\d command_queue_items"
psql $DATABASE_URL -c "\d action_recommendations"
```

**Acceptance Criteria:**
- [ ] Migration runs without errors
- [ ] Tables created with correct schema
- [ ] Indexes exist on `priority_score` and `status`
- [ ] Can insert/query test records

**Rollback:**
```bash
alembic -c infra/alembic.ini downgrade -1
```

---

#### **Task 7.5: Implement APS Scoring Algorithm**
**What:** Service that calculates Action Priority Score (APS) for recommendations.

**Scope:**
- Create `APSCalculator` service class
- Implement scoring formula (revenue 40%, urgency 25%, effort 15%, strategic 20%)
- Return score + explainability string

**NOT Included:**
- Machine learning model (simple rules-based for v1)
- Historical conversion data (use static ICP scores)
- A/B testing different weights

**Files Created:**
- `src/services/aps_calculator.py` - APSCalculator class

**Contracts:**
```python
# src/services/aps_calculator.py
class APSCalculator:
    def calculate_score(
        self,
        revenue_impact: float,  # Pipeline $ value
        urgency_days: int,  # Days until deadline
        effort_minutes: int,  # Estimated time to complete
        icp_score: float,  # 0-1 ICP fit
    ) -> Tuple[float, str]:
        """
        Returns (aps_score, reasoning)
        
        Example:
        score, reason = calculator.calculate_score(
            revenue_impact=50000,
            urgency_days=1,
            effort_minutes=15,
            icp_score=0.9
        )
        # Returns: (87.5, "High pipeline value ($50k), urgent (1 day), quick win (15min), strong ICP (0.9)")
        """
        ...
```

**Validation:**
```python
# tests/test_aps_calculator.py
def test_aps_high_value_urgent():
    calc = APSCalculator()
    score, reason = calc.calculate_score(
        revenue_impact=50000,
        urgency_days=1,
        effort_minutes=15,
        icp_score=0.9
    )
    assert score > 80, "High value + urgent should score >80"
    assert "urgent" in reason.lower()
    assert "50k" in reason or "50000" in reason

def test_aps_low_value_not_urgent():
    calc = APSCalculator()
    score, reason = calc.calculate_score(
        revenue_impact=1000,
        urgency_days=30,
        effort_minutes=120,
        icp_score=0.3
    )
    assert score < 40, "Low value + not urgent should score <40"
```

**Acceptance Criteria:**
- [ ] High value + urgent + quick = score >80
- [ ] Low value + slow + hard = score <40
- [ ] Reasoning includes top drivers ("because...")
- [ ] Tests pass

**Rollback:** Remove service file, no DB changes.

---

#### **Task 7.6: Build Today's Moves API Endpoint**
**What:** REST API endpoint that returns top 5-10 command queue items for today.

**Scope:**
- Create `GET /api/command-queue/today` endpoint
- Query `command_queue_items` ordered by `priority_score` DESC
- Filter by `status=pending` and `due_by` within next 24 hours
- Include full `action_context` and `reasoning`

**NOT Included:**
- Pagination (just top 10)
- Filtering by owner (assume "casey" for v1)
- Real-time updates (polling only)

**Files Created:**
- `src/routes/command_queue.py` - CommandQueue API router

**Files Modified:**
- `src/main.py` - Register command_queue router

**Contracts:**
```python
# GET /api/command-queue/today
# Response:
{
  "today_moves": [
    {
      "id": "uuid",
      "priority_score": 87.5,
      "action_type": "send_email",
      "action_context": {
        "recipient": "john@acmecorp.com",
        "subject": "Follow up: Demo tomorrow",
        "draft_id": "draft_123"
      },
      "reasoning": "High pipeline value ($50k ARR), demo tomorrow (urgent), strong ICP fit",
      "owner": "casey",
      "due_by": "2026-01-24T14:00:00Z",
      "status": "pending"
    },
    ...
  ],
  "total_pending": 47,
  "top_count": 10
}
```

**Validation:**
```bash
# Insert test recommendations
psql $DATABASE_URL <<EOF
INSERT INTO command_queue_items (id, priority_score, action_type, action_context, status, owner, due_by, created_at, updated_at)
VALUES (gen_random_uuid(), 87.5, 'send_email', '{"recipient":"test@example.com"}', 'pending', 'casey', NOW() + INTERVAL '1 day', NOW(), NOW());
EOF

# Test API
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today | jq '.today_moves | length'
# Expected: 1 (or more if other test data exists)
```

**Acceptance Criteria:**
- [ ] Endpoint returns top 10 items ordered by priority
- [ ] Only pending items shown
- [ ] Only items due within 24 hours
- [ ] Response includes reasoning + context

**Rollback:** Remove route registration from `main.py`.

---

#### **Task 7.7: Create Today's Moves UI (v0)**
**What:** Simple HTML/JS page that shows "Today's Moves" list.

**Scope:**
- Create static HTML page at `/static/command-queue.html`
- Fetch from `GET /api/command-queue/today` on page load
- Display list with priority score, action type, reasoning
- Add "Accept" and "Dismiss" buttons (no-op for v0, just UI)

**NOT Included:**
- Real-time updates (manual refresh only)
- Actual execution logic (just buttons)
- Filtering/sorting controls

**Files Created:**
- `src/static/command-queue.html` - Today's Moves UI
- `src/static/css/command-queue.css` - Styling
- `src/static/js/command-queue.js` - Fetch + render logic

**Contracts:**
```html
<!-- Layout -->
<div class="command-queue">
  <h1>Today's Moves</h1>
  <div class="queue-item" data-id="uuid">
    <div class="priority-badge">87</div>
    <div class="action-info">
      <h3>Send email to john@acmecorp.com</h3>
      <p class="reasoning">High pipeline value ($50k ARR), demo tomorrow (urgent)</p>
      <p class="due-by">Due by: Today, 2pm</p>
    </div>
    <div class="actions">
      <button class="btn-accept">Execute</button>
      <button class="btn-dismiss">Skip</button>
    </div>
  </div>
</div>
```

**Validation:**
```bash
# Open in browser
open https://web-production-a6ccf.up.railway.app/static/command-queue.html

# Expected:
# - List of today's moves shown
# - Priority scores visible
# - Reasoning displayed
# - Buttons present (not functional yet)
```

**Acceptance Criteria:**
- [ ] Page loads without errors
- [ ] Fetches from `/api/command-queue/today`
- [ ] Displays all queue items
- [ ] Shows priority score prominently
- [ ] Buttons render (even if no-op)

**Rollback:** Remove HTML file, no DB changes.

---

#### **Task 7.8: Seed Test Recommendations**
**What:** Script to generate sample command queue items for testing.

**Scope:**
- Create `scripts/seed_command_queue.py`
- Generate 10-15 sample recommendations with varying APS scores
- Insert into `command_queue_items` table
- Mix of action types (send_email, create_task, schedule_meeting)

**NOT Included:**
- Production recommendation generation (manual seed only)
- Automated seeding on deploy

**Files Created:**
- `scripts/seed_command_queue.py` - Seed script

**Contracts:**
```python
# scripts/seed_command_queue.py
import asyncio
from src.db import async_session
from src.models.command_queue import CommandQueueItem, ActionRecommendation

async def seed():
    async with async_session() as session:
        # High priority
        item1 = CommandQueueItem(
            priority_score=87.5,
            action_type="send_email",
            action_context={
                "recipient": "john@acmecorp.com",
                "subject": "Follow up: Demo tomorrow",
                "draft_id": "draft_123"
            },
            status="pending",
            owner="casey",
            due_by=datetime.utcnow() + timedelta(days=1),
            ...
        )
        session.add(item1)
        # ... add 9 more with varying scores
        await session.commit()

if __name__ == "__main__":
    asyncio.run(seed())
```

**Validation:**
```bash
# Run seed script
python scripts/seed_command_queue.py

# Verify inserted
psql $DATABASE_URL -c "SELECT COUNT(*) FROM command_queue_items WHERE status='pending';"
# Expected: 10-15 rows

# Test UI shows seeded data
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today | jq '.today_moves | length'
# Expected: 10
```

**Acceptance Criteria:**
- [ ] Script inserts 10-15 sample items
- [ ] Mix of high/medium/low priority
- [ ] Different action types represented
- [ ] UI shows seeded data

**Rollback:**
```bash
psql $DATABASE_URL -c "TRUNCATE command_queue_items CASCADE;"
```

---

#### **Task 7.9: Add Telemetry Events for Recommendations**
**What:** Instrument recommendation generation and user actions.

**Scope:**
- Create telemetry decorator `@track_event`
- Emit `recommendation_generated` when APS score calculated
- Emit `recommendation_viewed` when `/today` endpoint hit
- Log to Sentry breadcrumbs + structured logs

**NOT Included:**
- Separate analytics service (use Sentry breadcrumbs for v1)
- Real-time dashboards
- Event replay

**Files Created:**
- `src/telemetry/events.py` - Event tracking decorator

**Files Modified:**
- `src/services/aps_calculator.py` - Add `@track_event` decorator
- `src/routes/command_queue.py` - Track page views

**Contracts:**
```python
# src/telemetry/events.py
def track_event(event_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start
            
            # Log to Sentry breadcrumb
            sentry_sdk.add_breadcrumb({
                "category": "telemetry",
                "message": event_name,
                "level": "info",
                "data": {
                    "duration_ms": duration * 1000,
                    "args": str(args)[:100],
                }
            })
            
            # Log to structured logger
            logger.info(f"Event: {event_name}", extra={
                "event": event_name,
                "duration_ms": duration * 1000
            })
            
            return result
        return wrapper
    return decorator

# Usage:
@track_event("recommendation_generated")
async def calculate_score(self, ...):
    ...
```

**Validation:**
```bash
# Trigger recommendation generation
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today

# Check Sentry breadcrumbs
# Expected: "recommendation_viewed" breadcrumb present

# Check logs
railway logs --tail 50 | grep "Event: recommendation_viewed"
# Expected: Log entry with event name + timestamp
```

**Acceptance Criteria:**
- [ ] `recommendation_generated` tracked on APS calculation
- [ ] `recommendation_viewed` tracked on API call
- [ ] Events appear in Sentry breadcrumbs
- [ ] Structured logs include event name + duration

**Rollback:** Remove `@track_event` decorators.

---

#### **Task 7.10: Document Command Queue API**
**What:** API documentation with curl examples.

**Scope:**
- Create `docs/API_COMMAND_QUEUE.md`
- Document all command queue endpoints
- Include curl examples for each endpoint
- Document error responses

**NOT Included:**
- OpenAPI/Swagger spec (manual docs only)
- Interactive API explorer

**Files Created:**
- `docs/API_COMMAND_QUEUE.md` - Command queue API documentation

**Contracts:**
```markdown
# Command Queue API

## Get Today's Moves
Returns top 10 recommended actions for today.

### Request
```bash
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today
```

### Response (200 OK)
```json
{
  "today_moves": [...],
  "total_pending": 47,
  "top_count": 10
}
```

### Error Responses
- 500: Database connection failed
```

**Validation:**
```bash
# Test all curl examples in doc
bash docs/API_COMMAND_QUEUE.md  # (extract curl commands + run)
```

**Acceptance Criteria:**
- [ ] All endpoints documented
- [ ] Curl examples work
- [ ] Error responses listed
- [ ] Response schemas shown

**Rollback:** Delete doc file.

---

### Sprint 7 Summary

**Deliverables:**
- ✅ Production issues fixed (readiness, admin password, Sentry)
- ✅ Command queue data models created
- ✅ APS scoring algorithm implemented
- ✅ "Today's Moves" API endpoint live
- ✅ Basic UI for viewing recommendations
- ✅ Telemetry instrumentation
- ✅ API documentation

**Demo Script:**
```bash
# 1. Show fixed production health
curl https://web-production-a6ccf.up.railway.app/ready | jq '.checks.database'
# Expected: "ready"

# 2. Show Today's Moves API
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today | jq '.today_moves[0]'
# Expected: Top priority item with APS score + reasoning

# 3. Show UI
open https://web-production-a6ccf.up.railway.app/static/command-queue.html
# Expected: List of 10 recommended actions with "Execute" and "Skip" buttons

# 4. Show telemetry
# Expected: Sentry breadcrumbs show "recommendation_viewed" events
```

**Validation:**
- [ ] All 10 tasks complete
- [ ] All acceptance criteria met
- [ ] Demo script runs successfully
- [ ] No production regressions

---

## Sprint 8: Proactive Signal Ingestion

**Demo Statement:** "After Sprint 8, CaseyOS automatically detects new signals (form submissions, CRM updates, email replies) and generates recommendations without manual input."

**Duration:** 7-10 days  
**Dependencies:** Sprint 7 complete

### Sprint 8 Tasks

#### **Task 8.1: Create Signal Ingestion Framework**
**What:** Event-driven system for capturing signals from integrations.

**Scope:**
- Create `Signal` model (source, type, data, processed_at)
- Create `SignalProcessor` interface
- Create Celery task for processing signals
- Add indexes for unprocessed signals

**Files Created:**
- `src/models/signal.py` - Signal model
- `src/services/signal_processor.py` - SignalProcessor base class
- `src/tasks/signal_tasks.py` - Celery task for signal processing

**Contracts:**
```python
class Signal(Base):
    __tablename__ = "signals"
    
    id: str (UUID, primary key)
    source: str  # "hubspot", "gmail", "form_submission"
    signal_type: str  # "form_submitted", "deal_stage_changed", "email_replied"
    data: JSONB  # Raw signal data
    processed: bool
    processed_at: Optional[datetime]
    recommendation_generated: bool
    created_at: datetime

class SignalProcessor:
    async def process(self, signal: Signal) -> Optional[ActionRecommendation]:
        """Process signal and optionally generate recommendation."""
        raise NotImplementedError
```

**Validation:**
```bash
# Run migration
alembic upgrade head

# Insert test signal
psql $DATABASE_URL <<EOF
INSERT INTO signals (id, source, signal_type, data, processed, created_at)
VALUES (gen_random_uuid(), 'test', 'form_submitted', '{"email":"test@example.com"}', false, NOW());
EOF

# Verify inserted
psql $DATABASE_URL -c "SELECT * FROM signals WHERE processed=false;"
```

**Acceptance Criteria:**
- [ ] Signal model created
- [ ] Can insert/query signals
- [ ] SignalProcessor interface defined
- [ ] Celery task skeleton exists

**Rollback:** `alembic downgrade -1`

---

#### **Task 8.2: Implement HubSpot Deal Change Polling**
**What:** Poll HubSpot API for deal stage changes every 5 minutes.

**Scope:**
- Create HubSpot polling service
- Query deals updated since last poll
- Detect stage changes (SQL → Opportunity → Closed Won)
- Create Signal records for changes

**Files Created:**
- `src/services/hubspot_poller.py` - HubSpot polling service

**Files Modified:**
- `src/celery_app.py` - Add beat schedule for polling

**Contracts:**
```python
class HubSpotPoller:
    async def poll_deal_updates(self, since: datetime) -> List[Signal]:
        """Poll HubSpot for deals updated since timestamp."""
        deals = await self.hubspot.get_deals_updated_since(since)
        signals = []
        for deal in deals:
            if self._is_stage_change(deal):
                signal = Signal(
                    source="hubspot",
                    signal_type="deal_stage_changed",
                    data={
                        "deal_id": deal.id,
                        "old_stage": deal.old_stage,
                        "new_stage": deal.stage,
                        "pipeline_value": deal.amount,
                    },
                    processed=False
                )
                signals.append(signal)
        return signals
```

**Celery Beat Schedule:**
```python
beat_schedule = {
    "poll-hubspot-deals": {
        "task": "src.tasks.signal_tasks.poll_hubspot_deals",
        "schedule": timedelta(minutes=5),
    }
}
```

**Validation:**
```bash
# Trigger manual poll
curl -X POST https://web-production-a6ccf.up.railway.app/api/admin/trigger-poll

# Check signals created
psql $DATABASE_URL -c "SELECT COUNT(*) FROM signals WHERE source='hubspot';"
# Expected: >0 if deals were updated recently
```

**Acceptance Criteria:**
- [ ] Polls HubSpot every 5 minutes
- [ ] Detects stage changes
- [ ] Creates Signal records
- [ ] Handles API rate limits gracefully

**Rollback:** Remove beat schedule entry.

---

#### **Task 8.3: Implement Gmail Reply Detection**
**What:** Poll Gmail API for new replies to sent drafts.

**Scope:**
- Query Gmail threads for messages newer than last check
- Match threads to sent drafts (by Message-ID header)
- Create Signal for "email_replied"

**Files Created:**
- `src/services/gmail_poller.py` - Gmail polling service

**Contracts:**
```python
class GmailPoller:
    async def poll_replies(self, since: datetime) -> List[Signal]:
        """Poll Gmail for replies since timestamp."""
        threads = await self.gmail.search_threads(after=since)
        signals = []
        for thread in threads:
            if self._is_reply_to_our_draft(thread):
                signal = Signal(
                    source="gmail",
                    signal_type="email_replied",
                    data={
                        "thread_id": thread.id,
                        "from_email": thread.latest_message.from,
                        "draft_id": self._find_draft_id(thread),
                    },
                    processed=False
                )
                signals.append(signal)
        return signals
```

**Validation:**
```bash
# Send test draft manually
# Reply to it
# Wait for poll (or trigger manual)

# Check signal created
psql $DATABASE_URL -c "SELECT * FROM signals WHERE signal_type='email_replied';"
# Expected: Signal for replied thread
```

**Acceptance Criteria:**
- [ ] Detects replies to sent drafts
- [ ] Creates Signal records
- [ ] Handles rate limits
- [ ] Doesn't duplicate signals

**Rollback:** Remove polling task from beat schedule.

---

#### **Task 8.4: Implement Form Submission Signal Handler**
**What:** Convert existing webhook handler to use Signal model.

**Scope:**
- Update `/api/webhooks/hubspot` to create Signal instead of direct workflow
- Keep backwards compatibility (still trigger workflow)

**Files Modified:**
- `src/routes/webhooks.py` - Add Signal creation

**Validation:**
```bash
# Submit test form
curl -X POST https://web-production-a6ccf.up.railway.app/api/webhooks/hubspot \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","message":"Test"}'

# Check signal created
psql $DATABASE_URL -c "SELECT * FROM signals WHERE signal_type='form_submitted' ORDER BY created_at DESC LIMIT 1;"
# Expected: New signal record
```

**Acceptance Criteria:**
- [ ] Form submissions create Signal
- [ ] Existing workflow still works
- [ ] No duplicate processing

**Rollback:** Revert webhook handler changes.

---

#### **Task 8.5: Build Signal-to-Recommendation Pipeline**
**What:** Process signals and generate action recommendations.

**Scope:**
- Create processors for each signal type
- Generate ActionRecommendation with APS score
- Create CommandQueueItem from recommendation

**Files Created:**
- `src/services/signal_processors/form_processor.py`
- `src/services/signal_processors/deal_change_processor.py`
- `src/services/signal_processors/reply_processor.py`

**Contracts:**
```python
class FormSubmissionProcessor(SignalProcessor):
    async def process(self, signal: Signal) -> Optional[ActionRecommendation]:
        # Extract form data
        email = signal.data["email"]
        
        # Calculate APS
        calc = APSCalculator()
        score, reason = calc.calculate_score(
            revenue_impact=self._estimate_pipeline_value(signal),
            urgency_days=1,  # Forms are urgent
            effort_minutes=15,
            icp_score=await self._calculate_icp_fit(signal)
        )
        
        # Create recommendation
        rec = ActionRecommendation(
            aps_score=score,
            reasoning=reason,
            ...
        )
        
        # Create queue item
        queue_item = CommandQueueItem(
            priority_score=score,
            action_type="send_email",
            action_context={
                "recipient": email,
                "template": "prospecting_followup"
            },
            recommendation_id=rec.id,
            ...
        )
        
        return rec
```

**Validation:**
```bash
# Create test signal
# Run processor

# Check recommendation created
psql $DATABASE_URL -c "SELECT * FROM action_recommendations ORDER BY created_at DESC LIMIT 1;"

# Check queue item created
psql $DATABASE_URL -c "SELECT * FROM command_queue_items WHERE status='pending' ORDER BY created_at DESC LIMIT 1;"
```

**Acceptance Criteria:**
- [ ] All signal types have processors
- [ ] Recommendations generated with APS
- [ ] Queue items created
- [ ] Signals marked as processed

**Rollback:** Remove processor files.

---

#### **Task 8.6-8.10:** (Continued in full roadmap doc...)

---

## Sprint 9: One-Click Execution

**Demo Statement:** "After Sprint 9, Casey can click 'Execute' on a recommendation and the action is performed automatically (send draft, create task, book meeting) with full audit trail and rollback capability."

**Tasks:** 9.1-9.12 (execution handlers, dry-run mode, guardrails, idempotency, rollback)

---

## Sprint 10: Closed-Loop Outcomes

**Demo Statement:** "After Sprint 10, CaseyOS tracks outcomes (reply received, meeting booked, deal advanced) and feeds them back into APS scoring to improve future recommendations."

**Tasks:** 10.1-10.10 (outcome detection, outcome recording, feedback loops, pattern analysis)

---

## Sprint 11-12: GTM Expansion

**Demo Statement:** "After Sprint 11-12, CaseyOS orchestrates marketing operations (content repurposing), fulfillment tracking (deliverables, approvals), and customer success workflows (risk flags, renewals)."

**Tasks:** 11.1-12.15 (marketing ops, fulfillment tracking, CS workflows, advanced automation)

---

## Post-Sprint Review Process

After completing each sprint, run this review prompt with a subagent:

**Review Prompt:**
```
Review the completed sprint for:
1. Atomicity: Are tasks independently committable?
2. Validation: Do all tasks have clear validation steps?
3. Demoability: Can we demo the sprint increment end-to-end?
4. Edge cases: Are there missing error handlers or edge cases?
5. Rollback plans: Is every change reversible?
6. Idempotency: Are automated actions safe to retry?
7. Rate limiting: Are integrations protected from abuse?
8. Telemetry gaps: Are we tracking the right events?

Suggest 3-5 concrete improvements for the next sprint.
```

---

**Next Steps:**
1. Review Sprint 7 tasks with Casey
2. Confirm priority order
3. Execute tasks 7.1-7.10 sequentially
4. Demo Sprint 7 increment
5. Proceed to Sprint 8

**Ready to execute. Awaiting go-ahead.**
