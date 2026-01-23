# Project Build Philosophy (Execution Operating System)

**Owner:** Casey Larkin — Founder, *Dude, What's The Bid??!* LLC  
**Applies To:** Any repo / build Casey runs  
**Version:** 1.0  
**Last Updated:** January 23, 2026

---

## The Law

**Atomic tasks. Clear validation. Demoable sprints. No drama.**

If your plan violates this, it's not "close." It's **wrong**.

---

## Non-Negotiables

### 1) Atomic Means Atomic

Every task/ticket must be:

* ✅ **Independently committable** (mergeable in isolation)
* ✅ **Scope-limited** (one intent, small diff, tight blast radius)
* ✅ **Testable** (automated tests OR explicit manual verification)
* ✅ **Reversible** (rollback plan or obvious reversion)
* ✅ **Readable** (future-us understands it fast)

**Good vs Bad**

```
✅ "Add email validation to contact form + unit tests for edge cases"
❌ "Improve the form"

✅ "Implement circuit breaker for Gmail API + fallback behavior"
❌ "Make external calls more resilient"

✅ "Add Sentry error tracking with context sampling + manual verification"
❌ "Better error handling"
```

---

### 2) Validation First, Then Code

Define success **before** you write code.

**Validation options:**

* **Automated:** unit / integration / E2E (when worth it)
* **Manual:** curl commands, SQL queries, screenshots/recordings, console checks, perf benchmarks

**Rule:** If you can't explain how we verify it, you can't ship it.

---

### 3) Demoable Sprints Only

Every sprint ships something that is:

* ✅ **Runnable**
* ✅ **Visible** (end-to-end, not scaffolding)
* ✅ **Extends prior work** (builds on Sprints 1-4)
* ✅ **Production-grade** (no half-features, no commented-out code, no TODOs left behind)

**Sprint Demo Gate Checklist**

- [ ] Code deploys/builds in standard environment
- [ ] New capability works end-to-end (demo script runs)
- [ ] Regression checks complete (prior functionality intact)
- [ ] No unowned performance regressions
- [ ] Docs updated (README, inline, commit messages)
- [ ] All tests passing (no skips, no flakes)

---

### 4) Big Goal, Small Tasks

Sprint goals are **big**. Individual tasks are **small**.

**Allowed sprint goals (examples):**

* "Production Hardening: Monitoring, Security, Disaster Recovery"
* "Email Send: OAuth, rate limiting, safety checks"
* "Integration: Google Workspace sync"
* "Async Processing: Celery, queues, error recovery"

**Required task behavior:**

* Each task maps clearly to sprint goal
* No "misc" buckets
* No "various fixes"
* If it matters, name it explicitly. If you can't name it, it's not ready.

---

## Definitions (So We Don't Argue About Words)

### Definition of Ready (DoR)

A task is ready when:

* [ ] Scope boundaries are explicit ("does" and "does NOT")
* [ ] Validation is defined (how we know it works)
* [ ] Contracts are written (API endpoints, schemas, error codes)
* [ ] Rollback path exists (revert or disable or migrate back)
* [ ] Dependencies are listed (explicit or "none")
* [ ] Estimated effort is realistic (includes complexity buffer)

### Definition of Done (DoD)

A task is done when:

* [ ] Code merged to main (PR with clear description)
* [ ] Validation completed and documented (test results or manual proof)
* [ ] Observability added (logs/metrics where failure can hide)
* [ ] Docs updated (README, /docs, inline comments for tricky logic)
* [ ] Rollback is credible and documented (reversible or has safe fallback)
* [ ] No TODOs or commented-out code left behind

---

## Task Spec Template (Use This Every Time)

````markdown
### Task X.Y: [Atomic Task Name]

**Priority:** CRITICAL/HIGH/MEDIUM/LOW  
**Dependencies:** [Task IDs] or "None"  
**Effort:** X hours

**One-liner:** What this does in one sentence.

**Scope Boundaries:**

Does include:
- bullet 1
- bullet 2

Does NOT include:
- exclusion 1
- exclusion 2

**Files:**
- Create: `path/to/new-file.py`
- Modify: `path/to/existing.py` (specific sections or functions)

**Contracts:**
- Endpoint: `POST /api/admin/emergency-stop`
- Request: `{"password": "string"}`
- Response: `{"status": "stopped", "timestamp": "ISO8601"}`
- Error codes: 401 (bad password), 500 (system error)

**DB Changes (if any):**
```sql
-- exact migration
ALTER TABLE auto_approval_rules ADD COLUMN emergency_stop BOOLEAN DEFAULT false;
```

**Implementation Notes:**

* Key decisions and why
* Edge cases to handle
* Failure modes to prevent
* Example of success

**Validation:**

```bash
# Exact commands to verify success

# Example 1: Manual curl test
curl -X POST http://localhost:8000/api/admin/emergency-stop \
  -H "Content-Type: application/json" \
  -d '{"password":"test123"}'

# Example 2: Check database state
psql -c "SELECT auto_approve_enabled FROM config LIMIT 1;"

# Example 3: Run automated test
pytest tests/test_emergency_stop.py -v
```

**Acceptance Criteria:**

- [ ] Endpoint responds with 401 on bad password
- [ ] Endpoint responds with 200 on correct password
- [ ] AUTO_APPROVE_ENABLED flag set to false in database
- [ ] All auto-approval rules disabled immediately
- [ ] Log entry created with timestamp and operator ID
- [ ] Email alert sent to team (if configured)

**Rollback:**

```bash
# Option 1: Revert PR
git revert <commit-hash>

# Option 2: Manual flag reset
curl -X POST http://localhost:8000/api/admin/emergency-resume \
  -H "Content-Type: application/json" \
  -d '{"password":"test123"}'

# Option 3: Direct database (emergency only)
psql -c "UPDATE config SET auto_approve_enabled = true;"
```
````

---

## Automation Safety Rails (Critical for Features That Send/Write/Trigger)

If your feature touches **messaging, scheduling, enrichment, workflows, billing, external APIs, or data writes**:

- **Idempotency:** Repeat requests don't duplicate outcomes
- **Rate limits:** Protect APIs and sender reputation
- **Dry-run mode:** Simulate without executing (when possible)
- **Kill switch:** Quick disable path (for safety)
- **Audit trail:** Who/what/why for every action (compliance + debugging)
- **Circuit breaker:** Fail gracefully if external APIs are down

**Rule:** Silent failure is a future incident. Design like you hate incidents.

---

## Observability Is a Feature

Add logs/metrics where problems hide:

- Outbound messages + delivery callbacks
- Scheduling flows and trigger timing
- Retries/backoff paths (which ones, why, recovery)
- Writes + deduplication logic
- Auth/token refresh (expiry, rotation, failures)
- Background jobs/queues (processing time, errors, backlog)
- Rate limit checks (hits, blocks, resets)
- External API calls (latency, errors, circuit state)

**Rule:** If we can't see it, we can't trust it.

---

## Sprint Planning Process

### Step 1: Write the Sprint Goal (Big Picture)

```
Sprint 6: Production Hardening

Objective: System runs reliably in production with visibility, security, and recovery paths.

Key Metrics:
- Error tracking working (all errors surfaced in Sentry)
- Circuit breakers active (external API failures don't cascade)
- Health checks passing (Kubernetes/Railway auto-recovery ready)
- Disaster recovery tested (rollback plan validated)
- Security audit complete (no SQL injection, CSRF, auth bypasses)

Duration: 5 days (40 hours)
```

### Step 2: Break Into Atomic Tasks

Write each task using the Task Spec Template (above).

Checklist for each task:

- [ ] Scope is one thing (not "and also...")
- [ ] Validation is explicit (how do we know it works?)
- [ ] Rollback path exists
- [ ] Estimated effort is realistic
- [ ] Priority is clear
- [ ] Dependencies listed

### Step 3: Subagent Review (Mandatory)

```
Review this sprint plan for:

* Are all tasks atomic and independently committable?
* Does each task include explicit validation?
* Is the sprint demoable and production-grade?
* Are scope boundaries explicit?
* Any missing edge cases, failure modes, rollback plans, or observability?
* Suggest 3-5 concrete improvements.
```

### Step 4: Update Source of Truth

Update the repo's main strategic document (e.g., STRATEGIC_ROADMAP.md) with:
- Sprint goal
- All tasks with full spec templates
- Exit criteria
- Demo script

### Step 5: Execute Task by Task

For each task:

1. Create a branch: `task/6-1-security-audit`
2. Implement atomic change
3. Write/update validation
4. Document rollback
5. PR with clear description
6. Merge to main
7. Mark task done

### Step 6: Sprint Completion

A sprint is complete when:

- ✅ All tasks meet DoD (definition of done)
- ✅ Tests/manual validation documented
- ✅ All PRs merged to main
- ✅ Code deployed or runnable for demo
- ✅ Sprint summary created (what shipped + notable changes)
- ✅ Demo artifact captured (screenshots/recording/written notes)

---

## Observability Checklist (Every Feature)

When shipping new capability:

- [ ] Error cases have clear log messages (timestamp, context, remediation hint)
- [ ] Success paths have counters/metrics
- [ ] Async/background jobs have monitoring (processing time, queue depth, errors)
- [ ] External API calls have latency + error tracking
- [ ] Database queries have slow query logging
- [ ] Feature flags have toggle audit trail
- [ ] Rate limits have hit/block metrics
- [ ] Retries have backoff tracking
- [ ] Circuit breakers have state changes logged

---

## Casey's Operating Vibe (Yes, This Matters)

We build like closers:

- **No vagueness.** Atomic tasks with clear validation.
- **No fragile hacks.** Production-grade code, not scaffolding.
- **No "we'll circle back."** Feature complete or not shipped.
- **Crisp execution, auditable results.** Every task is reversible and observable.

You're working for **Casey Larkin**, Founder of **Dude, What's The Bid??! LLC**.

That means we ship **clean**, we ship **real**, and we ship **with receipts**.

---

## Quick Checklist (Before Shipping)

```
□ Atomic task (one thing, small diff)
□ Explicit validation (how we know it works)
□ Rollback path (reversible or safe fallback)
□ Demoable sprint output (runnable, visible, production-grade)
□ Observable (logs/metrics where failure can hide)
□ Auditable (who/what/why trail)
□ Subagent review done
□ Repo .md updated (source of truth)
□ All tests passing (no skips, no flakes)
```

**If all checked → ship it.**  
**If not → refine first.**

---

## References

- **Source of Truth:** [STRATEGIC_ROADMAP.md](STRATEGIC_ROADMAP.md)
- **Implementation Index:** [IMPLEMENTATION_INDEX.md](IMPLEMENTATION_INDEX.md)
- **This Philosophy:** [PROJECT_BUILD_PHILOSOPHY.md](PROJECT_BUILD_PHILOSOPHY.md)
