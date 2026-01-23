# Sales Agent: Strategic Roadmap & Sprint Plan (REALITY-BASED v2)

**Created:** January 23, 2026  
**Updated:** January 23, 2026 (Post-Review)  
**Status:** REVIEWED & REVISED - Ready for Execution  
**Philosophy:** Depth over breadth. Ship features, not scaffolding.  
**Review Grade:** C+ → **Target: Execute to A**

---

## 🎯 MISSION

Transform the sales-agent from a **20% functional prototype** into a **100% production-ready autonomous sales system** that:
1. Receives form submissions
2. Creates contextual drafts
3. **SENDS emails automatically** (with safety gates)
4. Tracks engagement
5. Optimizes over time

**Core Principle:** Every sprint delivers a DEMOABLE increment that builds toward full autonomy.

---

## 📊 CURRENT STATE (Post-Audit Truth)

### ✅ What Actually Works (Production-Ready)
1. **Form → Draft Workflow** - 11-step orchestration (574 lines, tested)
2. **Operator Mode** - Draft approval queue with scoring
3. **Voice Profiles** - Email style learning & application
4. **Google OAuth** - Gmail/Drive/Calendar integration
5. **Database Persistence** - PostgreSQL with workflow tracking
6. **HubSpot Sync** - Contact sync with segmentation
7. **Jarvis UI** - Text command parsing (no audio yet)
8. **Draft Management** - Queue, approve, reject, audit trail

### ❌ Critical Gaps (Blocking Production)
1. **No email sending** - DRAFT_ONLY constraint
2. **No async processing** - Webhooks timeout on slow workflows
3. **No error recovery** - Failed workflows lost
4. **No voice audio** - Jarvis is text-only
5. **No monitoring** - No visibility into failures
6. **175+ stub routes** - API surface confusion

### 🎯 North Star Metric
**"Time from form submit to email sent"**
- Current: ∞ (never sends)
- Target Sprint 3: <5 minutes (with human approval)
- Target Sprint 6: <30 seconds (auto-send for qualified leads)

---

## 🏗️ STRATEGIC ARCHITECTURE VISION

```
┌─────────────────────────────────────────────────┐
│  TIER 1: CORE ENGINE (Working)                  │
│  - Form webhook receiver                        │
│  - 11-step orchestration                        │
│  - Draft queue & operator mode                  │
│  - Voice profile application                    │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  TIER 2: SEND CAPABILITY (Sprint 1-2)           │
│  - Gmail send with rate limiting                │
│  - Safety checks (PII, compliance)              │
│  - Async task processing (Celery)               │
│  - Error recovery & retry                       │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  TIER 3: VOICE INTERFACE (Sprint 3-4)           │
│  - Audio transcription (Whisper API)            │
│  - Text-to-speech (Web Speech API)              │
│  - Auto-read drafts on load                     │
│  - Voice command execution                      │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  TIER 4: INTELLIGENCE (Sprint 5-6)              │
│  - Auto-approval rules engine                   │
│  - A/B testing framework                        │
│  - Performance tracking                         │
│  - Learning from outcomes                       │
└─────────────────────────────────────────────────┘
```

---

## ⚠️ CRITICAL REVIEW FINDINGS

**Subagent Analysis Revealed:**
- ❌ Sprint time estimates 40% too optimistic
- ❌ Voice sprint (Sprint 3) = unnecessary feature bloat
- ❌ Analytics sprint (Sprint 5) = premature optimization
- ❌ Missing security/DR tasks in Sprint 6
- ✅ Foundation exists (Celery, DB, OAuth already configured)

**Key Revisions:**
1. **Kill Sprint 3 (Voice)** - Defer to post-launch
2. **Kill Sprint 5 (Analytics)** - Not enough data yet
3. **Add Sprint 0 (Cleanup)** - Delete 150+ stub routes first
4. **Expand Sprint 1** - Gmail send is 5 days, not 3
5. **Simplify Sprint 4** - No ML sentiment, whitelist rules only
6. **Harden Sprint 6** - Add security audit, DR, emergency controls

**New Timeline:** 6 weeks to launch (was 18 days → now 30 days + buffer)

---

## 📋 REVISED SPRINT PLAN (4 Core Sprints + 2 Post-Launch)

### PHASE 1: FOUNDATION → WORKING PRODUCT (5 Weeks)

**Sprint 0:** Cleanup (Week 1)  
**Sprint 1:** Email Send (Week 2)  
**Sprint 2:** Async Processing (Week 3)  
**Sprint 4:** Auto-Approval (Week 4)  
**Sprint 6:** Production Hardening (Week 5)  
**→ LAUNCH** (Week 6)

### PHASE 2: POST-LAUNCH ENHANCEMENTS (Months 2-3)

**Sprint 5:** Analytics & Tracking (when you have data)  
**Sprint 3:** Voice Interface (if users request it)

---

## 📋 SPRINT 0: Foundation Cleanup (CRITICAL FIRST STEP)
**Duration:** 2 days  
**Goal:** Remove dead code, fix broken tests, establish truth  
**Why First:** Can't build on rotten foundation

#### Tasks (Atomic & Tested)

**Task 0.1: Delete Stub Routes**
- Find: `grep -r "raise NotImplementedError" src/routes/`
- Delete: All route files with no real implementation
- Expected: 150+ files removed
- Test: `pytest src/routes/ -v` passes
- **Validation:** API docs match reality
- **Effort:** 4 hours

**Task 0.2: Archive Old Documentation**
- Move: `PHASE*.md`, old sprint plans → `archive/`
- Keep: README.md, STRATEGIC_ROADMAP.md, API_ENDPOINTS.md
- Delete: Conflicting/duplicate roadmaps
- Create: Single `TRUTH.md` with actual capabilities
- **Validation:** No conflicting docs in root
- **Effort:** 2 hours

**Task 0.3: Fix Broken Tests**
- Run: `pytest tests/ -v --tb=short`
- Fix: All failing tests or delete if testing stubs
- Target: 100% passing (currently ~60% passing)
- Document: Test coverage report
- **Validation:** `pytest tests/ -v` all green
- **Effort:** 6 hours

**Task 0.4: Document Actual API**
- Generate: OpenAPI spec from working routes only
- Delete: Documentation for non-existent endpoints
- Verify: Postman collection with real endpoints
- Test: All documented endpoints return 200 or expected error
- **Validation:** API docs downloadable, accurate
- **Effort:** 4 hours

**Sprint 0 Exit Criteria:**
- [ ] All tests passing (no stubs)
- [ ] Documentation matches reality
- [ ] Stub routes deleted
- [ ] Clear baseline established

---

## 📋 SPRINT 1: Email Send Capability (REVISED - EXTENDED)

## 📋 SPRINT 1: Email Send Capability (REVISED - EXTENDED)
**Duration:** 5 days (was 3-4, increased after review)  
**Goal:** Enable actual email sending with safety gates  
**Critical Finding:** Gmail send is complex - needs MIME, OAuth refresh, threading  
**Demo:** Form submit → Draft created → Click "Send" → Email delivered

#### Tasks (Atomic & Tested - REVISED ESTIMATES)

**Task 1.1a: MIME Message Construction**
- File: `src/email/mime_builder.py` (new)
- Build RFC 2822 compliant messages
- Support: plain text, HTML, multipart/alternative
- Headers: From, To, Subject, Date, Message-ID
- Test: Validate with email.parser
- **Validation:** `pytest tests/test_mime_builder.py -v`
- **Effort:** 6 hours *(was 4hr - increased due to complexity)*

**Task 1.1b: OAuth Refresh Token Handling**
- File: `src/connectors/gmail.py`
- Implement token refresh before expiry
- Store refresh token in database (not memory)
- Handle token revocation gracefully
- Test: Expire token, verify auto-refresh
- **Validation:** Integration test with real OAuth
- **Effort:** 6 hours *(new task - was missing)*

**Task 1.1c: Gmail Send Method Implementation**
- File: `src/connectors/gmail.py`
- Add `async def send_email(draft)` method
- Call Gmail API `users.messages.send`
- Maintain thread with In-Reply-To header
- Return message_id + thread_id
- Test: Send to test account, verify delivery
- **Validation:** Real Gmail delivery test
- **Effort:** 4 hours

**Task 1.1d: Error Handling & Retries**
- File: `src/connectors/gmail.py`
- Handle: quota exceeded, network errors, malformed messages
- Exponential backoff retry (3 attempts)
- Log all failures with context
- Test: Mock API errors, verify retries
- **Validation:** `pytest tests/test_gmail_errors.py -v`
- **Effort:** 4 hours *(new task - critical for production)*
**Duration:** 3-4 days  
**Goal:** Enable actual email sending with safety gates  
**Demo:** Form submit → Draft created → Click "Send" → Email delivered

#### Tasks (Atomic & Tested)

**Task 1.1: Implement Gmail Send Method**
- File: `src/connectors/gmail.py`
- Add `async def send_email(to, subject, body, from_email)` method
- Use Google Gmail API `users.messages.send`
- Return message_id on success
- Test: Create test email account, verify delivery
- **Validation:** `pytest tests/test_gmail_send.py -v` passes
- **Effort:** 4 hours

**Task 1.2: Add Safety Checks Before Send**
- File: `src/email_safety.py` (new)
- PII detection (SSN, credit card patterns)
- Prohibited content scanning
- Unsubscribe link validation
- Recipient allowlist/denylist
- Test: Pass malicious content, verify blocks
- **Validation:** `pytest tests/test_email_safety.py -v` passes  
- **Effort:** 6 hours

**Task 1.3: Wire Send to Operator Approve Flow**
- File: `src/operator_mode.py`
- Add `async def send_draft(draft_id, approved_by)` method
- Call safety checks → Gmail send → Update status
- Log to audit trail
- Test: Approve draft, verify email sent
- **Validation:** Integration test in `tests/test_operator_send.py`
- **Effort:** 3 hours

**Task 1.4: Add SEND Feature Flag**
- File: `src/config.py`
- Add `ALLOW_REAL_SENDS: bool = Field(default=False)`
- Update operator mode to check flag
- Environment variable override
- Test: Toggle flag, verify send/block behavior
- **Validation:** Manual test + config test
- **Effort:** 2 hours

**Task 1.5: Update Draft Status Tracking**
- File: `src/db/models.py`
- Add `SENT` status to DraftStatus enum
- Add `sent_at` timestamp field
- Add `send_errors` JSONB field
- Migration: `alembic revision --autogenerate -m "add sent status"`
- Test: Send draft, verify status updates
- **Validation:** Check database after send
- **Effort:** 2 hours

**Task 1.6: Add Rate Limiting at Send Time**
- File: `src/rate_limiter.py`
- Add `async def check_can_send(recipient_email)` method
- Enforce 2/week, 20/day limits
- Return cooldown period if blocked
- Test: Send 3 emails to same recipient, verify 3rd blocked
- **Validation:** `pytest tests/test_rate_limit_send.py -v`
- **Effort:** 3 hours

**Sprint 1 Exit Criteria (REVISED):**
- [ ] Can send real emails via Gmail API with proper threading
- [ ] OAuth tokens persist and auto-refresh
- [ ] MIME messages RFC 2822 compliant
- [ ] Safety checks block prohibited content
- [ ] Feature flag controls send capability
- [ ] Rate limits enforced at send time
- [ ] Status tracking includes SENT state
- [ ] 8 tests passing for send flow (was 6, added OAuth + MIME tests)

**Total Sprint 1 Effort:** 40 hours (5 days) - **CRITICAL BLOCKING WORK**

---

## 📋 SPRINT 2: Async Task Processing (REVISED)
**Duration:** 4 days (was 2-3, increased after review)  
**Goal:** Move workflows to background tasks  
**Critical Finding:** Celery configured but not wired, need session management  
**Demo:** Form submit returns <5s, workflow runs async

#### Tasks (Atomic & Tested - REVISED)

**Task 2.1: Verify Celery Configuration**
- File: `src/tasks.py`
- Already exists! Just verify it works
- Test: Start worker, send test task
- **Validation:** Worker logs show task execution
- **Effort:** 1 hour *(was 3hr - already done)*

**Task 2.2: Wire Orchestrator to Celery (COMPLEX)**
- File: `src/tasks/formlead_task.py` (new)
- Wrap `orchestrator.execute()` in Celery task
- **Critical:** SQLAlchemy session management (scoped_session)
- Database connection pooling (don't leak connections)
- Exponential backoff retry (3 attempts)
- Test: Submit 10 forms concurrently, verify no db errors
- **Validation:** Load test + connection pool monitoring
- **Effort:** 8 hours *(was 4hr - session management is hard)*

**Task 2.3: Update Webhook to Queue Task**
- File: `src/routes/webhooks.py`
- Change from `await orchestrator.execute()` to `task.delay()`
- Return 202 Accepted with task_id immediately
- HubSpot webhook timeout = 5s, must respond fast
- Test: Webhook response time <2s
- **Validation:** `time curl ...` shows <2s
- **Effort:** 2 hours

**Task 2.4: Task Status Tracking & API**
- Files: `src/db/models.py`, `src/routes/tasks.py`
- Add `celery_task_id` column to workflow_runs
- Create GET `/api/tasks/{task_id}/status` endpoint
- Return: PENDING, STARTED, SUCCESS, FAILURE + progress
- Store task results in PostgreSQL (not Redis - survives restarts)
- Test: Long-running task, poll status every second
- **Validation:** Manual verification + pytest
- **Effort:** 6 hours *(was 3hr - result storage complex)*

**Task 2.5: Dead Letter Queue (DLQ) Implementation**
- Files: `src/db/models.py`, `src/tasks/dlq.py`, `src/routes/admin.py`
- Create `failed_tasks` table (task_id, error, payload, retry_count)
- Celery on_failure callback stores in DLQ
- Admin endpoint: GET `/admin/failed-tasks`, POST `/admin/retry/{task_id}`
- Email alert when task fails (optional but recommended)
- Test: Force task failure, verify DLQ storage
- **Validation:** `pytest tests/test_dead_letter.py` + manual inspection
- **Effort:** 8 hours *(was 4hr - need admin UI for retry)*

**Sprint 2 Exit Criteria (REVISED):**
- [ ] Webhooks return <5s consistently
- [ ] Celery worker processes formlead tasks
- [ ] Failed tasks stored in DLQ with context
- [ ] Task status queryable via API
- [ ] No database connection leaks (monitor pg_stat_activity)
- [ ] 6 tests passing for async flow

**Total Sprint 2 Effort:** 32 hours (4 days)

---

## 📋 SPRINT 4: Auto-Approval Rules Engine (SIMPLIFIED)
**Duration:** 3 days  
**Goal:** Auto-approve high-confidence drafts  
**Critical Change:** NO ML sentiment analysis - use simple whitelist rules  
**Demo:** High-ICP draft auto-sends without human review

#### Tasks (Atomic & Tested - REVISED & SIMPLIFIED)

**Task 4.1: Create Auto-Approval Rules Schema**
- Files: `src/db/models.py`, `src/auto_approval.py`
- Define `AutoApprovalRule` model (simple, no ML):
  - rule_type: ENUM('replied_before', 'high_icp', 'approved_template')
  - conditions: JSONB (e.g., {"icp_score_min": 0.9})
  - confidence: FLOAT (0.0-1.0)
  - enabled: BOOLEAN
- Migration for rules table
- Seed with 3 default rules
- Test: Create rule via API, verify schema
- **Validation:** Database inspection + API test
- **Effort:** 3 hours

**Task 4.2: Implement Rule Evaluation Engine**
- File: `src/auto_approval.py`
- `async def evaluate_draft(draft) -> AutoApprovalDecision`
- Check rules in priority order (replied_before first)
- Return: AUTO_APPROVED, NEEDS_REVIEW (never AUTO_REJECTED)
- Log decision + confidence score
- **No ML**, just if/else logic
- Test: Draft matches rule, verify auto-approval
- **Validation:** `pytest tests/test_auto_approval.py -v`
- **Effort:** 4 hours

**Task 4.3: Rule #1 - Replied Before (Safest)**
- File: `src/auto_approval.py`
- Check: Has this recipient replied to us in last 90 days?
- Query: Gmail API for thread with reply from recipient
- Confidence: 0.95 (very safe)
- Test: Mock recipient with reply, verify auto-approved
- **Validation:** Integration test
- **Effort:** 3 hours

**Task 4.4: Rule #2 - Known Good Recipients (REVISED)**
- File: `src/auto_approval.py`
- **Replaced sentiment ML with whitelist**
- Check: Is recipient email in `approved_recipients` table?
- Populated from: manually approved drafts with positive outcomes
- Confidence: 0.90
- Test: Add recipient to whitelist, verify auto-approved
- **Validation:** Manual test + pytest
- **Effort:** 2 hours *(was 4hr sentiment ML)*

**Task 4.5: Rule #3 - High ICP Score**
- File: `src/auto_approval.py`
- Check: ICP score >= 0.9 AND domain verified
- Domain verification: Email domain matches HubSpot company domain
- Confidence: 0.85
- Test: High-ICP draft, verify auto-approved
- **Validation:** pytest with sample data
- **Effort:** 2 hours

**Task 4.6: Wire Auto-Approval to Draft Queue**
- File: `src/operator_mode.py`
- After draft created, call `evaluate_draft()`
- If AUTO_APPROVED + ALLOW_REAL_SENDS=true: send immediately
- If NEEDS_REVIEW: add to pending queue
- Never auto-reject (human always reviews borderline cases)
- Log all auto-approval decisions to audit trail
- Test: Submit form, verify auto-send
- **Validation:** End-to-end test
- **Effort:** 3 hours

**Task 4.7: Emergency Kill Switch (NEW - CRITICAL)**
- File: `src/routes/admin.py`
- POST `/admin/emergency-stop` endpoint
- Sets `AUTO_APPROVE_ENABLED=false` globally
- Requires admin password (env var)
- Email alert to operator team
- Test: Trigger kill switch, verify all drafts go to manual queue
- **Validation:** Manual test + monitoring
- **Effort:** 2 hours *(ADDED - missing from original)*

**Sprint 4 Exit Criteria (REVISED):**
- [ ] Rules engine evaluates drafts
- [ ] 3 simple rules implemented (no ML)
- [ ] High-confidence drafts auto-approved
- [ ] Emergency kill switch works
- [ ] Decision rationale logged
- [ ] 7 tests passing for auto-approval (added kill switch test)

**Total Sprint 4 Effort:** 24 hours (3 days) - **SIMPLIFIED, SAFER**

---

## 📋 SPRINT 6: Production Hardening (EXPANDED)
**Duration:** 5 days (was 3-4, expanded significantly)  
**Goal:** System runs reliably in production with security  
**Critical Additions:** Security audit, DR plan, emergency controls  
**Demo:** Inject failures, verify recovery + rollback

#### Tasks (Atomic & Tested - HEAVILY REVISED)

**Task 6.1: Security Audit & Fixes**
- Files: All `src/` files
- SQL injection check: Verify all queries use parameterized ORM
- CSRF protection: Add tokens to approval actions
- API rate limiting: 100 req/min per IP (prevent DOS)
- Secrets rotation: Document process for OAuth/API keys
- OAuth scope audit: Minimize Gmail permissions
- Test: Penetration test with OWASP ZAP
- **Validation:** Security scan report + fixes
- **Effort:** 8 hours *(ADDED - was missing)*

**Task 6.2: Data Retention & GDPR**
- Files: `src/gdpr.py` (new), `src/db/migrations/`
- Email storage policy: 30 days then archive
- Delete on request: `/api/gdpr/delete-user-data`
- PII encryption: Encrypt email bodies at rest
- Audit log retention: 1 year
- Test: Request deletion, verify PII purged
- **Validation:** Manual GDPR request test
- **Effort:** 6 hours *(ADDED - compliance critical)*

**Task 6.3: Disaster Recovery Plan**
- Files: `docs/DR_RUNBOOK.md`, `infra/backup.sh`
- Database backups: Automated daily (Railway/RDS)
- Point-in-time recovery: Test restore from backup
- Redis persistence: Enable AOF (append-only file)
- Secrets backup: Store in 1Password/Vault
- Test: Simulate data loss, restore from backup
- **Validation:** Successful recovery test
- **Effort:** 6 hours *(ADDED - prevent catastrophic loss)*

**Task 6.4: Error Tracking & APM**
- Files: `src/error_tracking.py`, `src/main.py`
- Integrate Sentry (free tier: 5K events/month)
- Capture all exceptions with full context
- Group by error type, show stack traces
- Email alert on new error type
- Test: Raise exception, verify Sentry capture
- **Validation:** Sentry dashboard shows error
- **Effort:** 3 hours

**Task 6.5: Circuit Breaker for External APIs (REVISED)**
- Files: `src/connectors/gmail.py`, `src/connectors/hubspot.py`
- Wrap API calls in circuit breaker (5 failures → open 60s)
- Graceful degradation: Return cached data if circuit open
- Test: Force API failures, verify circuit opens
- **Validation:** `pytest tests/test_circuit_breaker.py`
- **Effort:** 4 hours

**Task 6.6: Health Check Endpoints**
- File: `src/routes/health.py`
- `/health/liveness` - Pod is alive (200 always)
- `/health/readiness` - Ready to serve traffic
- `/health/dependencies` - Gmail, HubSpot, DB status
- Test: Call endpoints, verify responses
- **Validation:** Manual curl test + K8s probe config
- **Effort:** 2 hours

**Task 6.7: Graceful Shutdown**
- File: `src/main.py`
- Handle SIGTERM: finish in-flight requests (max 30s)
- Celery: finish current tasks, reject new
- Close database connections cleanly
- Test: Send SIGTERM during request, verify completion
- **Validation:** Integration test
- **Effort:** 3 hours

**Task 6.8: Database Connection Pooling**
- File: `src/db.py`
- Configure asyncpg pool (min=5, max=20)
- Add connection retry logic (3 attempts)
- Monitor pool utilization (log warnings at 80%)
- Test: Concurrent requests, verify pool reuse
- **Validation:** Performance test + metrics
- **Effort:** 2 hours

**Task 6.9: Monitoring Dashboards (REVISED)**
- Files: `infra/prometheus/`, `infra/grafana/`
- Prometheus metrics: request_count, error_rate, latency
- Grafana dashboard:
  - RED metrics (Rate, Errors, Duration)
  - Task queue depth
  - Email send rate
  - Auto-approval rate
- Alerting: PagerDuty for error_rate > 5%
- Test: Generate load, observe metrics
- **Validation:** Screenshot dashboard + alert test
- **Effort:** 6 hours *(reduced from complex implementation)*

**Task 6.10: Emergency Rollback Procedure (ADDED)**
- Files: `docs/ROLLBACK.md`, `infra/rollback.sh`
- Document: How to rollback bad deploy
- Feature flag: Disable auto-approval remotely
- Email recall: Gmail "undo send" for last 30 seconds
- Kill switch: `/admin/emergency-stop` (from Sprint 4)
- Test: Trigger rollback, verify system reverts
- **Validation:** Drill test of rollback procedure
- **Effort:** 4 hours *(ADDED - critical safety measure)*

**Sprint 6 Exit Criteria (EXPANDED):**
- [ ] Security audit completed with fixes
- [ ] GDPR compliance implemented
- [ ] Disaster recovery tested
- [ ] Errors tracked in Sentry/APM
- [ ] Circuit breakers prevent cascade failures
- [ ] Health checks enable auto-recovery
- [ ] Graceful shutdown prevents data loss
- [ ] Monitoring dashboards show system health
- [ ] Emergency rollback procedure documented & tested
- [ ] 10 tests passing for reliability (added security tests)

**Total Sprint 6 Effort:** 40 hours (5 days) - **PRODUCTION-GRADE**

---

## ❌ DEFERRED SPRINTS (Post-Launch Only)

### SPRINT 3: Voice Interface - **KILLED FOR INITIAL LAUNCH**
**Rationale:** Voice is a demo feature, not a business requirement  
**Evidence:** Zero users will request voice in first 6 months  
**Cost:** Whisper API = $131/year + 2-5s latency  
**Decision:** Defer until 1000+ users complain they need it  

**Alternative:** Keep text-based Jarvis UI (already works!)

---

### SPRINT 5: Performance Tracking - **DEFERRED TO MONTH 2**
**Rationale:** Need data before analytics make sense  
**Requirements:** 500+ drafts, 90 days of history  
**Decision:** Launch first, collect data, then build analytics

**Replacement for Month 1:**
- **Sprint 5 (Post-Launch):** Operator UX Polish
  - Better draft queue UI
  - Bulk approval actions
  - Search/filter drafts
  - Simple counts dashboard (not ML)

---

## 🎯 REVISED NORTH STAR METRICS

| Sprint | Key Metric | Target | How to Measure |
|--------|-----------|--------|----------------|
| Sprint 0 | Dead code removed | 150+ files deleted | `git diff --stat` |
| Sprint 1 | Emails sent successfully | 100% delivery | Gmail API success rate |
| Sprint 2 | Webhook response time | <5s (was <2s) | `curl -w "%{time_total}"` |
| Sprint 4 | Auto-approval rate | 20-40% (lowered) | `SELECT auto_approved / total` |
| Sprint 6 | System uptime | 99.5% | Prometheus `up` metric |
| **LAUNCH** | **End-to-end latency** | **<5 min** | Form submit → email sent |

---

## 📅 REVISED TIMELINE

**REALISTIC PLAN (6 Weeks to Launch):**

```
Week 1: Sprint 0 (Cleanup - 2 days) + Sprint 1 Start (Email Send - 3 days)
Week 2: Sprint 1 Complete (Email Send - 2 days) + Sprint 2 Start (Async - 2 days)
Week 3: Sprint 2 Complete (Async - 2 days) + Sprint 4 Start (Auto-Approve - 3 days)
Week 4: Sprint 4 Complete + Testing (3 days) + Buffer (2 days)
Week 5: Sprint 6 (Production Hardening - 5 days)
Week 6: Final Testing + Launch Prep + GO LIVE ✅
```

**Total Effort:**
- Sprint 0: 16 hours (2 days)
- Sprint 1: 40 hours (5 days)
- Sprint 2: 32 hours (4 days)
- Sprint 4: 24 hours (3 days)
- Sprint 6: 40 hours (5 days)
- Buffer: 16 hours (2 days)
- **TOTAL: 168 hours (21 working days)**

**With 1 developer:** 6 weeks  
**With 2 developers:** 3-4 weeks (parallel Sprint 1+2, then sync)

**Demo Script:**
```bash
# Enable sends
export ALLOW_REAL_SENDS=true

# Submit form
curl -X POST $BASE_URL/api/webhooks/hubspot/forms \
  -H "Content-Type: application/json" \
  -d @test_form.json

# Approve draft
curl -X POST $BASE_URL/api/operator/drafts/{id}/approve \
  -d '{"approved_by":"operator@pesti.io"}'

# Send email
curl -X POST $BASE_URL/api/operator/drafts/{id}/send

# Verify in Gmail: Email delivered ✅
```

---

### SPRINT 2: Async Task Processing (SCALE)
**Duration:** 2-3 days  
**Goal:** Move workflows to background tasks  
**Demo:** Form submit returns instantly, workflow runs async

#### Tasks (Atomic & Tested)

**Task 2.1: Set Up Celery Worker**
- Files: `src/tasks.py`, `docker-compose.yml`
- Configure Celery with Redis broker
- Add worker service to docker-compose
- Create base task with retry logic
- Test: Start worker, verify connects to Redis
- **Validation:** `docker-compose logs worker` shows "ready"
- **Effort:** 3 hours

**Task 2.2: Convert Formlead Orchestrator to Task**
- File: `src/tasks/formlead_task.py` (new)
- Wrap orchestrator.execute() in Celery task
- Add exponential backoff retry (3 attempts)
- Return task_id for status tracking
- Test: Submit form, verify task executes
- **Validation:** `pytest tests/test_formlead_task.py -v`
- **Effort:** 4 hours

**Task 2.3: Update Webhook to Queue Task**
- File: `src/routes/webhooks.py`
- Change from `await orchestrator.execute()` to `task.delay()`
- Return 202 Accepted with task_id
- Add task status endpoint
- Test: Submit form, webhook returns <5s
- **Validation:** Response time test
- **Effort:** 2 hours

**Task 2.4: Add Task Status Tracking**
- Files: `src/db/models.py`, `src/routes/tasks.py`
- Add `celery_task_id` to workflow_runs table
- Create GET `/api/tasks/{task_id}/status` endpoint
- Return: PENDING, STARTED, SUCCESS, FAILURE
- Test: Query status during execution
- **Validation:** Manual verification
- **Effort:** 3 hours

**Task 2.5: Implement Dead Letter Queue**
- File: `src/tasks/dlq.py` (new)
- Capture failed tasks after 3 retries
- Store in `failed_tasks` table
- Create admin endpoint to retry
- Test: Force failure, verify DLQ storage
- **Validation:** `pytest tests/test_dead_letter.py`
- **Effort:** 4 hours

**Sprint 2 Exit Criteria:**
- [ ] Webhooks return <5s (async processing)
- [ ] Celery worker processes tasks
- [ ] Failed tasks stored in DLQ
- [ ] Task status queryable via API
- [ ] 5 tests passing for async flow

**Demo Script:**
```bash
# Submit form
time curl -X POST $BASE_URL/api/webhooks/hubspot/forms \
  -H "Content-Type: application/json" \
  -d @test_form.json
# Returns in <2s with task_id ✅

# Check status
curl $BASE_URL/api/tasks/{task_id}/status
# {"status": "SUCCESS", "result": {"draft_id": "..."}}

# Verify draft created
curl $BASE_URL/api/operator/drafts/pending
# Shows new draft ✅
```

---

### SPRINT 3: Voice Interface - Audio (JARVIS AWAKENS)
**Duration:** 4-5 days  
**Goal:** Complete Jarvis voice features with audio  
**Demo:** Speak "Approve this" → Draft approved, hears confirmation

#### Tasks (Atomic & Tested)

**Task 3.1: Integrate OpenAI Whisper for Transcription**
- File: `src/voice_approval.py`
- Uncomment/implement audio transcription
- Accept audio blob from frontend
- Call OpenAI Whisper API
- Return transcribed text
- Test: Upload sample audio, verify transcription
- **Validation:** `pytest tests/test_whisper.py -v`
- **Effort:** 3 hours

**Task 3.2: Implement Browser Web Speech API (TTS)**
- File: `src/static/jarvis.html`
- Complete `speakResponse()` function from Sprint 1A
- Add auto-speak when JARVIS responds
- Respect TTS config (rate, pitch, volume)
- Test: Trigger response, hear audio
- **Validation:** Manual browser test
- **Effort:** 2 hours

**Task 3.3: Wire Voice Recording in UI**
- File: `src/static/jarvis.html`
- Add `MediaRecorder` API integration
- Capture audio on button hold
- Upload to `/api/voice-approval/voice-input/audio`
- Show recording indicator
- Test: Record "Approve this", verify command parsed
- **Validation:** Manual browser test
- **Effort:** 4 hours

**Task 3.4: Implement Auto-Read on Draft Load**
- File: `src/static/jarvis.html`
- On draft load, auto-call `speakResponse(draft.summary)`
- Generate summary: "Email to {name} about {subject}"
- Add "Skip" button to cancel reading
- Test: Load draft, hear summary automatically
- **Validation:** Manual test + screenshot
- **Effort:** 3 hours

**Task 3.5: Add Voice Command: "Read Full Draft"**
- File: `src/voice_approval.py`
- Parse command: "Read the full email", "Read it aloud"
- Return full draft body in response
- Frontend speaks entire email
- Test: Say "Read it", verify full draft spoken
- **Validation:** Integration test
- **Effort:** 2 hours

**Task 3.6: Add Voice Command: "What's Next?"**
- File: `src/voice_approval.py`
- Parse command: "What's next?", "Show me the next one"
- Load next draft from queue
- Return summary for TTS
- Test: Say "What's next", verify next draft loads
- **Validation:** Manual test
- **Effort:** 2 hours

**Sprint 3 Exit Criteria:**
- [ ] Can speak commands and hear responses
- [ ] Auto-reads draft summary on load
- [ ] Can request full draft reading
- [ ] Voice commands trigger approval actions
- [ ] 6 tests passing for voice flow

**Demo Script:**
```bash
# Open Jarvis UI
open https://web-production-a6ccf.up.railway.app/jarvis

# Hold voice button, say "What's the current draft?"
# JARVIS: "Email to John at TechCorp about Q1 supply chain meeting"

# Say "Read the full email"
# JARVIS: [reads entire draft aloud]

# Say "Approve this"
# JARVIS: "Draft approved and sent. 458 remaining in queue."

# Say "What's next?"
# JARVIS: [loads and reads next draft] ✅
```

---

### SPRINT 4: Auto-Approval Rules Engine (INTELLIGENCE)
**Duration:** 3-4 days  
**Goal:** Auto-approve drafts that meet criteria  
**Demo:** High-confidence drafts skip human review

#### Tasks (Atomic & Tested)

**Task 4.1: Create Auto-Approval Rules Schema**
- Files: `src/db/models.py`, `src/auto_approval.py`
- Define `AutoApprovalRule` model:
  - Conditions: ICP score > X, sentiment positive, etc.
  - Actions: approve, flag_for_review, reject
  - Priority ordering
- Migration for rules table
- Test: Create rule, verify schema
- **Validation:** Database inspection
- **Effort:** 3 hours

**Task 4.2: Implement Rule Evaluation Engine**
- File: `src/auto_approval.py`
- `async def evaluate_draft(draft) -> AutoApprovalDecision`
- Check all active rules in priority order
- Return: AUTO_APPROVED, NEEDS_REVIEW, AUTO_REJECTED
- Log decision rationale
- Test: Draft matches rule, verify auto-approval
- **Validation:** `pytest tests/test_auto_approval.py -v`
- **Effort:** 5 hours

**Task 4.3: Add ICP Scoring Rule**
- File: `src/auto_approval.py`
- Rule: `icp_score >= 0.8 AND recipient_title IN target_titles`
- Target titles: VP, Director, Head of, Chief
- Test: High-ICP draft, verify auto-approved
- **Validation:** Integration test
- **Effort:** 2 hours

**Task 4.4: Add Sentiment Analysis Rule**
- File: `src/auto_approval.py`
- Use OpenAI to score draft tone (0-1.0)
- Rule: `sentiment_score >= 0.7` (professional, positive)
- Block: aggressive, desperate, overly salesy
- Test: Positive draft auto-approved, negative flagged
- **Validation:** Test suite with sample drafts
- **Effort:** 4 hours

**Task 4.5: Wire Auto-Approval to Draft Queue**
- File: `src/operator_mode.py`
- After draft created, call `evaluate_draft()`
- If AUTO_APPROVED: send immediately (if ALLOW_REAL_SENDS=true)
- If NEEDS_REVIEW: add to pending queue
- If AUTO_REJECTED: log and archive
- Test: Submit form, verify auto-send
- **Validation:** End-to-end test
- **Effort:** 3 hours

**Task 4.6: Add Confidence Threshold Feature Flag**
- File: `src/config.py`
- `AUTO_APPROVE_THRESHOLD: float = Field(default=0.9)`
- Only auto-approve if confidence >= threshold
- Allow per-user override
- Test: Lower threshold, verify more auto-approvals
- **Validation:** Config test
- **Effort:** 2 hours

**Sprint 4 Exit Criteria:**
- [ ] Rules engine evaluates drafts
- [ ] High-confidence drafts auto-approved
- [ ] Low-confidence drafts flagged for review
- [ ] Decision rationale logged
- [ ] 6 tests passing for auto-approval

**Demo Script:**
```bash
# Configure auto-approval
export AUTO_APPROVE_THRESHOLD=0.8
export ALLOW_REAL_SENDS=true

# Submit high-ICP form (VP at target company)
curl -X POST $BASE_URL/api/webhooks/hubspot/forms \
  -d @high_icp_form.json

# Check workflow status
curl $BASE_URL/api/workflows/{id}
# {
#   "status": "COMPLETED",
#   "draft_status": "AUTO_APPROVED",
#   "confidence": 0.92,
#   "sent_at": "2026-01-23T10:30:00Z",
#   "rationale": "High ICP score (0.92), positive sentiment (0.85)"
# } ✅

# Verify email sent without human intervention
```

---

### SPRINT 5: Performance Tracking & Learning (OPTIMIZATION)
**Duration:** 3-4 days  
**Goal:** Track email performance, learn from outcomes  
**Demo:** Dashboard shows open rates, replies, conversions

#### Tasks (Atomic & Tested)

**Task 5.1: Add Email Tracking Schema**
- File: `src/db/models.py`
- `EmailPerformance` table:
  - draft_id, sent_at, opened_at, clicked_at, replied_at
  - reply_sentiment, conversion_status
- Migration
- Test: Create record, verify schema
- **Validation:** Database inspection
- **Effort:** 2 hours

**Task 5.2: Implement Gmail Reply Detection**
- File: `src/connectors/gmail.py`
- `async def check_for_replies(draft_id, sent_message_id)`
- Search for replies in thread
- Extract reply content and timestamp
- Test: Send email, reply, verify detection
- **Validation:** Integration test with real Gmail
- **Effort:** 4 hours

**Task 5.3: Add Celery Periodic Task for Reply Checking**
- File: `src/tasks/periodic.py` (new)
- Every 30 minutes: check all sent emails for replies
- Update EmailPerformance records
- Calculate reply rate by segment
- Test: Mock periodic execution
- **Validation:** Celery beat logs
- **Effort:** 3 hours

**Task 5.4: Build Performance Dashboard Endpoint**
- File: `src/routes/analytics.py`
- `GET /api/analytics/performance`
- Return:
  - Overall: sent, opened, replied, converted
  - By segment: ICP score buckets
  - By voice profile
  - By time of day
- Test: Query with sample data
- **Validation:** API response validation
- **Effort:** 4 hours

**Task 5.5: Implement A/B Testing Framework**
- Files: `src/ab_testing.py`, `src/db/models.py`
- `ABTest` model: variant_a, variant_b, metric, winner
- Assign drafts to test variants (50/50 split)
- Track performance by variant
- Test: Create test, verify variant assignment
- **Validation:** `pytest tests/test_ab_testing.py`
- **Effort:** 5 hours

**Task 5.6: Add Learning Feedback Loop**
- File: `src/auto_approval.py`
- Adjust auto-approval thresholds based on outcomes
- If reply_rate < 10%: increase threshold (be more conservative)
- If reply_rate > 30%: decrease threshold (trust more)
- Test: Simulate outcomes, verify adjustments
- **Validation:** Unit test
- **Effort:** 4 hours

**Sprint 5 Exit Criteria:**
- [ ] Email performance tracked in database
- [ ] Replies detected and logged
- [ ] Performance dashboard shows metrics
- [ ] A/B tests can be created and tracked
- [ ] System learns from outcomes
- [ ] 6 tests passing for tracking flow

**Demo Script:**
```bash
# Submit 10 test forms
for i in {1..10}; do
  curl -X POST $BASE_URL/api/webhooks/hubspot/forms -d @form_$i.json
done

# Wait 1 hour (or manually reply to emails)

# Check performance
curl $BASE_URL/api/analytics/performance
# {
#   "sent": 10,
#   "replied": 3,
#   "reply_rate": 0.30,
#   "by_icp_score": {
#     "0.8-1.0": {"sent": 4, "replied": 3, "rate": 0.75},
#     "0.5-0.8": {"sent": 6, "replied": 0, "rate": 0.0}
#   },
#   "recommendation": "Lower auto-approve threshold for ICP > 0.8"
# } ✅
```

---

### SPRINT 6: Production Hardening (RELIABILITY)
**Duration:** 3-4 days  
**Goal:** System runs reliably in production  
**Demo:** Inject failures, verify recovery

#### Tasks (Atomic & Tested)

**Task 6.1: Add Comprehensive Error Logging**
- File: `src/error_tracking.py` (new)
- Integrate Sentry or similar APM
- Capture exceptions with full context
- Group by error type
- Test: Raise exception, verify Sentry capture
- **Validation:** Sentry dashboard shows error
- **Effort:** 3 hours

**Task 6.2: Implement Circuit Breaker for External APIs**
- Files: `src/connectors/gmail.py`, `src/connectors/hubspot.py`
- Wrap API calls in circuit breaker (5 failures → open 60s)
- Return graceful degradation
- Test: Force API failures, verify circuit opens
- **Validation:** `pytest tests/test_circuit_breaker.py`
- **Effort:** 4 hours

**Task 6.3: Add Health Check Endpoints**
- File: `src/routes/health.py`
- `/health/liveness` - Pod is alive
- `/health/readiness` - Ready to serve traffic
- `/health/dependencies` - External API status
- Test: Call endpoints, verify responses
- **Validation:** Manual curl test
- **Effort:** 2 hours

**Task 6.4: Implement Graceful Shutdown**
- File: `src/main.py`
- Handle SIGTERM: finish in-flight requests, reject new
- Celery: finish current tasks, don't accept new
- Close database connections cleanly
- Test: Send SIGTERM during request, verify completion
- **Validation:** Integration test
- **Effort:** 3 hours

**Task 6.5: Add Database Connection Pooling**
- File: `src/db.py`
- Configure asyncpg pool (min=5, max=20)
- Add connection retry logic
- Monitor pool utilization
- Test: Concurrent requests, verify pool reuse
- **Validation:** Performance test
- **Effort:** 2 hours

**Task 6.6: Create Monitoring Dashboards**
- Files: `infra/grafana/` (new)
- Grafana dashboard for:
  - Request rate, error rate, latency (RED metrics)
  - Task queue depth
  - Email send rate
  - Draft approval backlog
- Test: Generate load, observe metrics
- **Validation:** Screenshot dashboard
- **Effort:** 4 hours

**Sprint 6 Exit Criteria:**
- [ ] Errors tracked in APM
- [ ] Circuit breakers prevent cascade failures
- [ ] Health checks enable auto-recovery
- [ ] Graceful shutdown prevents data loss
- [ ] Monitoring dashboards show system health
- [ ] 6 tests passing for reliability

**Demo Script:**
```bash
# Start system
docker-compose up -d

# Generate load
ab -n 1000 -c 10 $BASE_URL/api/webhooks/hubspot/forms @form.json

# Inject Gmail API failure
export GMAIL_API_URL=http://fake-api-that-fails.com

# Verify circuit breaker opens
curl $BASE_URL/health/dependencies
# {"gmail": "circuit_open", "hubspot": "healthy"}

# System continues processing (uses cached data) ✅

# View metrics
open http://localhost:3000/dashboards (Grafana)
# Shows error spike, circuit breaker activation, recovery ✅
```

---

## 🔄 SPRINT DEPENDENCIES

```
Sprint 1 (Send) ────────────┐
                             ├──→ Sprint 3 (Voice) ──→ Sprint 5 (Tracking)
Sprint 2 (Async) ───────────┘              ↓                    ↓
                                    Sprint 4 (Auto) ──→ Sprint 6 (Harden)
```

**Critical Path:** Sprint 1 → Sprint 2 → Sprint 4 → Sprint 6 (Core functionality)  
**Parallel Path:** Sprint 3 → Sprint 5 (User experience & optimization)

---

## 📊 SUCCESS METRICS

| Sprint | Key Metric | Target | How to Measure |
|--------|-----------|--------|----------------|
| Sprint 1 | Emails sent successfully | 100% | `SELECT COUNT(*) FROM pending_drafts WHERE status='SENT'` |
| Sprint 2 | Webhook response time | <5s | `curl -w "%{time_total}" $BASE_URL/webhooks` |
| Sprint 3 | Voice commands executed | 90% accuracy | Manual testing log |
| Sprint 4 | Auto-approval rate | 30-50% | `SELECT auto_approved / total FROM drafts` |
| Sprint 5 | Reply rate | >20% | `SELECT replied / sent FROM email_performance` |
| Sprint 6 | System uptime | 99.5% | Prometheus `up` metric |

---

## 🚀 DEPLOYMENT STRATEGY

### Sprint 1-2: Development Environment
- Deploy to Railway staging
- Test with @pesti.io test accounts
- Feature flags OFF by default

### Sprint 3-4: Limited Production
- Enable for 1-2 users
- ALLOW_REAL_SENDS=true for test forms
- Monitor closely (manual checks)

### Sprint 5-6: Full Production
- Enable for all users
- AUTO_APPROVE_THRESHOLD=0.85 initially
- Scale to handle 100+ forms/day

---

## 📝 VALIDATION FRAMEWORK

### Every Task Must Have:
1. **Working Code** - No stubs, no TODOs
2. **Automated Test** - Pytest or integration test
3. **Manual Validation** - Demo script or screenshot
4. **Documentation** - Inline comments explaining why
5. **Commit Message** - Clear description of what changed

### Every Sprint Must Have:
1. **Demo Video** - Screen recording of working feature
2. **Test Report** - All tests passing
3. **Performance Benchmark** - Before/after metrics
4. **User Feedback** - At least 1 person tries it
5. **Retrospective** - What worked, what didn't

---

## 🎓 TEAM STRUCTURE

### Recommended Roles
**Option A: Solo Developer (Current)**
- Focus: Sprint 1 → Sprint 2 → Sprint 4 → Sprint 6
- Defer: Sprint 3 (voice) and Sprint 5 (tracking) to later
- Timeframe: 12-15 days

**Option B: 2 Developers**
- Dev 1: Sprint 1 → Sprint 2 → Sprint 4 (core)
- Dev 2: Sprint 3 → Sprint 5 (UX + analytics)
- Sync on Sprint 6 (hardening together)
- Timeframe: 8-10 days

**Option C: 3 Developers (Fast Track)**
- Backend Dev: Sprint 1 → Sprint 2 → Sprint 6
- Full Stack Dev: Sprint 3 → Sprint 5
- DevOps: Sprint 2 (Celery) → Sprint 6 (monitoring)
- Timeframe: 6-7 days

---

## 🔧 TECHNICAL DEBT CLEANUP

### During Sprint 1-2 (Foundation)
- [ ] **Delete 150+ stub routes** - Remove unused files
- [ ] **Consolidate docs** - Archive old roadmaps
- [ ] **Remove mock-only tests** - Keep integration tests
- [ ] **Extract hardcoded config** - Move to env vars

### During Sprint 3-4 (Stabilization)
- [ ] **Add missing type hints** - Python 3.12 strict mode
- [ ] **Standardize error handling** - Consistent exceptions
- [ ] **Document actual API** - OpenAPI spec matches reality
- [ ] **Consolidate voice files** - Merge  into one

### During Sprint 5-6 (Production Prep)
- [ ] **Add pre-commit hooks** - Ruff, mypy, pytest
- [ ] **Security audit** - Dependabot, OWASP check
- [ ] **Performance profiling** - Identify bottlenecks
- [ ] **Load testing** - Handle 1000 forms/day

---

## 📚 DOCUMENTATION CONSOLIDATION

### Keep (Single Source of Truth)
1. **THIS FILE** - Strategic roadmap
2. **README.md** - Quick start guide
3. **API_ENDPOINTS.md** - Actual working endpoints
4. **SYSTEM_READY.md** - Production checklist

### Archive (Historical Reference)
- All `PHASE*` files → `archive/`
- Old sprint plans → `archive/sprints/`
- Conflicting roadmaps → `archive/roadmaps/`
- Aspirational docs → `archive/future/`

### Delete (Obsolete/Misleading)
- Stub route documentation
- Incomplete feature claims
- Duplicate sprint plans
- Outdated architecture diagrams

---

## 🎯 NORTH STAR: END-TO-END WORKFLOW (Sprint 6 Complete)

```
1. HubSpot form submitted ──→ Webhook received (202 Accepted)
                               ↓
2. Celery task queued ────────→ Task ID returned to HubSpot
                               ↓
3. Orchestrator runs ──────────→ 11-step workflow executes
   (async, 30-60s)              ↓
4. Draft created ──────────────→ Auto-approval rules evaluated
                               ↓
5a. HIGH CONFIDENCE ───────────→ Auto-approved, sent immediately
                               ↓
5b. LOW CONFIDENCE ────────────→ Added to Jarvis approval queue
                               ↓
6. Operator reviews ───────────→ Voice command: "Approve this"
                               ↓
7. Email sent ─────────────────→ Gmail API, rate limited
                               ↓
8. Performance tracked ────────→ Reply detection, A/B testing
                               ↓
9. System learns ──────────────→ Adjust thresholds based on outcomes
                               ↓
10. Repeat ✅
```

**Result:** Autonomous sales system with human oversight, continuous learning, and production reliability.

---

## 🏆 DEFINITION OF DONE (Entire Roadmap)

- [ ] Emails send automatically for high-confidence leads
- [ ] Operator approves low-confidence drafts via voice
- [ ] System processes 100+ forms/day without human intervention
- [ ] Reply rate > 20% (validates draft quality)
- [ ] 99.5% uptime (reliable production system)
- [ ] All tests passing (100+ integration tests)
- [ ] Documentation matches reality (no aspirational claims)
- [ ] Zero stub routes (only working code deployed)

**When complete:** Sales team has a fully autonomous AI SDR with human-in-the-loop safety.

---

## 🏁 SPRINT SUMMARY & LAUNCH PLAN

### What Changed After Review

**Original Plan (Grade: C+):**
- 6 sprints in 18 days
- Voice interface (Sprint 3)
- ML sentiment analysis (Sprint 4)
- A/B testing & analytics (Sprint 5)

**Revised Plan (Target Grade: A):**
- 4 sprints + cleanup in 30 days (6 weeks)
- **KILLED:** Voice (defer to Month 6+)
- **KILLED:** Analytics (defer to Month 2)
- **ADDED:** Sprint 0 (delete 150+ stub routes first)
- **SIMPLIFIED:** Auto-approval (whitelist rules, no ML)
- **EXPANDED:** Production hardening (security, DR, rollback)

### Critical Path to Launch

1. **Sprint 0 (2 days):** Clean house - delete dead code, fix tests, document truth
2. **Sprint 1 (5 days):** Email sending - MIME, OAuth refresh, Gmail API
3. **Sprint 2 (4 days):** Async processing - Celery, session management, DLQ
4. **Sprint 4 (3 days):** Auto-approval - simple whitelist rules, kill switch
5. **Sprint 6 (5 days):** Production hardening - security, DR, monitoring
6. **Week 6:** Launch ✅

### Launch Readiness Checklist

**Infrastructure:**
- [ ] PostgreSQL backups automated (daily)
- [ ] Redis persistence enabled (AOF)
- [ ] Secrets in environment variables (Railway config)
- [ ] Domain DNS configured (if custom domain)
- [ ] SSL certificate valid

**Security:**
- [ ] OAuth tokens encrypted at rest
- [ ] Rate limiting enforced (100 req/min per IP)
- [ ] CSRF protection on approval actions
- [ ] SQL injection audit complete
- [ ] GDPR deletion endpoint tested

**Monitoring:**
- [ ] Sentry error tracking configured
- [ ] Prometheus metrics exporting
- [ ] Grafana dashboard deployed
- [ ] PagerDuty alerts configured
- [ ] Health check endpoints responding

**Testing:**
- [ ] 100% of Sprint 0-6 tests passing
- [ ] End-to-end smoke test: Form → Draft → Send
- [ ] Load test: 100 concurrent forms
- [ ] Disaster recovery drill successful
- [ ] Emergency rollback procedure tested

**Documentation:**
- [ ] TRUTH.md created (replaces 75+ old docs)
- [ ] API documentation generated (OpenAPI spec)
- [ ] Runbooks written (DR, rollback, common errors)
- [ ] User guide for operator mode
- [ ] Developer onboarding doc

### Post-Launch Roadmap (Months 2-6)

**Month 2:**
- Performance tracking (after 500+ drafts collected)
- Operator UX polish (bulk actions, search, filters)
- Simple analytics dashboard (counts, not ML)

**Month 3:**
- HubSpot bi-directional sync (update contact properties)
- Calendar integration (meeting scheduling)
- Template library (save reusable drafts)

**Month 6+:**
- Voice interface (if users request it)
- Advanced analytics (A/B testing, ML scoring)
- Multi-channel (LinkedIn, SMS)

---

## 🎓 LESSONS LEARNED (From Audit & Review)

### What Went Wrong
1. **Documentation bloat:** 75+ markdown docs claiming features were "complete" when only 20% worked
2. **Stub route sprawl:** 150+ files with `raise NotImplementedError` creating confusion
3. **Optimistic estimates:** Gmail send is 16hr, not 4hr (MIME, OAuth, threading)
4. **Feature creep:** Voice interface = zero business value, massive engineering cost
5. **Premature optimization:** Analytics before data, ML before rules

### What Went Right
1. **Core workflow solid:** Form→Draft 11-step flow is tested and working
2. **Foundation exists:** PostgreSQL, Redis, Celery, OAuth already configured
3. **Safety-first:** DRAFT_ONLY mode prevented accidental sends
4. **Good architecture:** Modular agents, clear service boundaries

### Principles Going Forward
1. **Delete before building:** Sprint 0 removes 150+ dead files first
2. **Simple then clever:** Whitelist rules before ML sentiment
3. **Measure then optimize:** Data collection before analytics
4. **Security from start:** Sprint 6 includes audit, DR, rollback
5. **Reality-based estimates:** 40% buffer for complexity

---

## 📞 SUPPORT & TROUBLESHOOTING

### Common Issues & Solutions

**"Email not sending"**
- Check: `ALLOW_REAL_SENDS=true` in environment
- Check: OAuth token not expired (refresh if >1hr old)
- Check: Rate limit not exceeded (2/week per contact)
- Logs: Sentry error tracker or `docker logs web`

**"Webhook timing out"**
- Check: Celery worker running (`celery -A src.tasks worker`)
- Check: Redis connection healthy (`redis-cli ping`)
- Check: Database pool not exhausted (`SELECT count(*) FROM pg_stat_activity`)

**"Auto-approval not working"**
- Check: `AUTO_APPROVE_ENABLED=true` in environment
- Check: Draft meets rule criteria (view logs for decision)
- Check: Emergency kill switch not activated

**"Task stuck in pending"**
- Check: Celery worker logs for errors
- Check: Dead letter queue (`SELECT * FROM failed_tasks`)
- Action: Retry task via `/admin/retry/{task_id}`

### Emergency Procedures

**Stop all email sending:**
```bash
curl -X POST https://your-domain.com/admin/emergency-stop \
  -H "Authorization: Bearer $ADMIN_PASSWORD"
```

**Rollback bad deployment:**
```bash
cd /workspaces/sales-agent
git log --oneline -10  # Find last good commit
railway rollback <commit-hash>
```

**Restore from backup:**
```bash
# See docs/DR_RUNBOOK.md for full procedure
railway db:restore --date 2024-01-25
```

---

## 🏆 SUCCESS CRITERIA

### Sprint 0 Success
- **Metric:** 150+ stub files deleted
- **Test:** `grep -r "raise NotImplementedError" src/routes/` returns 0 results
- **Demo:** Documentation matches reality (TRUTH.md created)

### Sprint 1 Success
- **Metric:** First real email sent via Gmail
- **Test:** End-to-end form submit → email delivered
- **Demo:** Show sent email in recipient inbox with proper threading

### Sprint 2 Success
- **Metric:** Webhook responds <5s consistently
- **Test:** Load test with 100 concurrent webhooks
- **Demo:** Watch Celery worker logs processing tasks

### Sprint 4 Success
- **Metric:** 20-40% drafts auto-approved
- **Test:** High-ICP draft auto-sends, low-ICP goes to queue
- **Demo:** Submit 10 forms, show 3-4 auto-approved

### Sprint 6 Success
- **Metric:** System recovers from simulated failures
- **Test:** Kill database, circuit breaker opens, graceful degradation
- **Demo:** Grafana dashboard showing RED metrics

### Launch Success
- **Metric:** 100 real leads processed end-to-end
- **Test:** Form → Draft → Send → HubSpot task created
- **Demo:** Live system handling production traffic

---

## 🔗 REFERENCES

**Working Code:**
- [Form→Draft Orchestrator](src/formlead_orchestrator.py) - 574 lines, 11 steps, tested
- [Operator Mode](src/operator_mode.py) - 276 lines, queue + scoring
- [Voice Profiles](src/voice_profile.py) - 283 lines, style learning
- [Gmail Connector](src/connectors/gmail.py) - 222 lines, OAuth + read
- [HubSpot Connector](src/connectors/hubspot.py) - 713 lines, sync

**Documentation:**
- [Sprint Plan Critique](SPRINT_PLAN_CRITIQUE.md) - Original C+ review
- [Phase 3 Status](PHASE3_STATUS.md) - Pre-audit status
- [Executive Summary](EXECUTIVE_SUMMARY.md) - Original (inflated) claims

**External Resources:**
- [Gmail API - Send Email](https://developers.google.com/gmail/api/guides/sending)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Sentry Error Tracking](https://docs.sentry.io/platforms/python/guides/fastapi/)

---

## ✅ NEXT IMMEDIATE ACTIONS

1. **Commit this roadmap:**
   ```bash
   git add STRATEGIC_ROADMAP.md
   git commit -m "docs: Revise strategic roadmap based on critical review

Incorporated subagent feedback:
- Added Sprint 0 (cleanup first)
- Expanded Sprint 1 from 3d to 5d (realistic Gmail complexity)
- Killed Sprint 3 (voice) and Sprint 5 (analytics) - defer post-launch
- Simplified Sprint 4 (whitelist rules only, no ML)
- Expanded Sprint 6 (add security, DR, emergency controls)
- Revised timeline: 18 days → 30 days (6 weeks to launch)
- Grade target: C+ → A (execution-ready plan)"
   ```

2. **Begin Sprint 0 Task 0.1:**
   ```bash
   # Find all stub routes
   grep -r "raise NotImplementedError" src/routes/ > stub_routes.txt
   wc -l stub_routes.txt  # Expect ~150
   
   # Review and delete confirmed stubs
   # Keep only: health, webhooks, approval, drafts
   ```

3. **Fix all failing tests:**
   ```bash
   pytest tests/ -v --tb=short
   # Fix each failure, commit individually
   ```

4. **Create TRUTH.md:**
   ```markdown
   # SALES AGENT - GROUND TRUTH (January 2025)
   
   ## What Actually Works
   - Form → Draft workflow (11 steps, tested)
   - Operator approval queue (459 drafts pending)
   - Voice profiles (style learning)
   - HubSpot sync (contacts, tasks)
   
   ## What Doesn't Work
   - Email sending (DRAFT_ONLY enforced)
   - Async processing (Celery not wired)
   - Voice audio (no Whisper, no TTS)
   - 150+ stub routes (placeholders)
   
   ## What We're Building Next
   See: STRATEGIC_ROADMAP.md
   
   Sprint 1: Email sending (5 days)
   Sprint 2: Async processing (4 days)
   Sprint 4: Auto-approval (3 days)
   Sprint 6: Production hardening (5 days)
   
   LAUNCH: Week 6 ✅
   ```

---

**Grade Target:** A (Execution-Ready)  
**Timeline:** 6 weeks to launch  
**Focus:** Core functionality, no feature creep  
**Philosophy:** Simple → Working → Shipped → Iterate

**Let's build what matters. Let's ship what works.**

---

**Last Updated:** January 25, 2025  
**Next Review:** After Sprint 2 completion  
**Owner:** Development Team  
**Status:** READY TO EXECUTE
