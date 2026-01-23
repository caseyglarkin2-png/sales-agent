# Sprint 6: Production Hardening - Execution Guide

**Created:** January 23, 2026  
**Duration:** 5 days (40 hours)  
**Philosophy:** Atomic → Observable → Shipped → Iterate  
**Build Guide:** [PROJECT_BUILD_PHILOSOPHY.md](PROJECT_BUILD_PHILOSOPHY.md)

---

## 🎯 Sprint Goal

System runs reliably in production with **visibility** (error tracking), **resilience** (circuit breakers), **security** (audit + GDPR), and **recovery** (disaster recovery plan).

**Key Metrics:**
- All errors surfaced in Sentry ✅
- External API failures don't cascade ✅
- Health checks enable auto-recovery ✅
- Disaster recovery tested + credible ✅
- Security audit complete (no bypasses) ✅

---

## 📋 Task Execution Order

### Phase 1: Foundation (Days 1-2)

**Task 6.1: Security Audit & Fixes** (8 hours)
- Priority: CRITICAL
- No dependencies
- Validates: SQL injection, CSRF, secrets leakage
- Files: `src/connectors/`, `src/routes/admin.py`, `src/config.py`

**Task 6.2: Data Retention & GDPR** (6 hours)
- Priority: HIGH
- No dependencies
- Delivers: DELETE endpoint, data cleanup automation
- Files: `src/routes/gdpr.py`, `src/tasks/retention.py`

**Task 6.3: Disaster Recovery Plan** (6 hours)
- Priority: CRITICAL
- No dependencies
- Deliverables: DR runbook, backup automation, restoration tests
- Files: `docs/DR_RUNBOOK.md`, `infra/backup_schedule.sh`

### Phase 2: Observability (Days 2-3)

**Task 6.4: Error Tracking (Sentry)** (3 hours)
- Priority: HIGH
- Dependencies: None (but enables 6.5+)
- Deliverables: Error capture, context injection, sampling
- Files: `src/observability/sentry.py`, `src/main.py`

**Task 6.5: Circuit Breaker Pattern** (4 hours)
- Priority: HIGH
- Dependencies: Task 6.4 (error tracking)
- Deliverables: Circuit breaker wrapper, graceful degradation
- Files: `src/resilience/circuit_breaker.py`, connector updates

**Task 6.6: Health Check Endpoints** (2 hours)
- Priority: MEDIUM
- Dependencies: Task 6.5 (circuit breaker shows state)
- Deliverables: Liveness, readiness, dependencies endpoints
- Files: `src/routes/health.py`, `src/main.py`

### Phase 3: Reliability (Days 3-4)

**Task 6.7: Graceful Shutdown** (3 hours)
- Priority: HIGH
- No dependencies (but benefits from 6.4+ observability)
- Deliverables: SIGTERM handler, queue draining
- Files: `src/main.py`, `src/tasks/__init__.py`

**Task 6.8: Connection Pooling** (2 hours)
- Priority: MEDIUM
- No dependencies
- Deliverables: asyncpg pool config, monitoring
- Files: `src/db/__init__.py`

**Task 6.9: Monitoring Dashboards** (6 hours)
- Priority: HIGH
- Dependencies: Task 6.4 (Sentry), Task 6.8 (metrics)
- Deliverables: Grafana dashboard, RED metrics
- Files: `infra/grafana/dashboards/`, `infra/prometheus.yml`

### Phase 4: Recovery (Day 5)

**Task 6.10: Emergency Rollback** (4 hours)
- Priority: CRITICAL
- Dependencies: Task 6.3 (DR plan provides context)
- Deliverables: Rollback runbook, procedure testing
- Files: `docs/EMERGENCY_ROLLBACK.md`, `scripts/rollback.sh`

---

## ✅ Execution Checklist (Per Task)

### Before Starting Task

- [ ] Read full task spec (in STRATEGIC_ROADMAP.md)
- [ ] Check dependencies completed
- [ ] Note all acceptance criteria
- [ ] Plan rollback strategy

### During Implementation

- [ ] Write code atomically (one thing per commit)
- [ ] Add observability (logs where things can fail)
- [ ] Create validation script (exact bash commands)
- [ ] Update docs (README, inline comments)

### After Implementation

- [ ] Run validation script (prove it works)
- [ ] Write test (unit or integration)
- [ ] PR with clear description
- [ ] Merge to main
- [ ] Verify no regressions

---

## 🧪 Validation Template (Copy for Each Task)

```bash
#!/bin/bash
# Task 6.X: [Task Name] - Validation Script
# Date: January 23, 2026

set -e  # Exit on any error

echo "=== Validating Task 6.X ==="

# Check 1: Code exists
if [ ! -f "src/path/to/file.py" ]; then
  echo "❌ FAIL: File not found"
  exit 1
fi

# Check 2: Specific behavior
echo "Testing [behavior]..."
output=$(curl -X GET http://localhost:8000/health/liveness)
if echo "$output" | grep -q "alive"; then
  echo "✅ PASS: Health check working"
else
  echo "❌ FAIL: Health check not responding"
  exit 1
fi

# Check 3: Test suite
echo "Running tests..."
pytest tests/test_[feature].py -v
if [ $? -eq 0 ]; then
  echo "✅ PASS: All tests passing"
else
  echo "❌ FAIL: Tests failed"
  exit 1
fi

echo ""
echo "✅ Task 6.X validation complete!"
```

---

## 📊 Progress Tracking

| Task | Status | Hours | Owner | Merged | Notes |
|------|--------|-------|-------|--------|-------|
| 6.1 | not-started | 8 | — | — | Security audit |
| 6.2 | not-started | 6 | — | — | GDPR compliance |
| 6.3 | not-started | 6 | — | — | Disaster recovery |
| 6.4 | not-started | 3 | — | — | Error tracking |
| 6.5 | not-started | 4 | — | — | Circuit breakers |
| 6.6 | not-started | 2 | — | — | Health checks |
| 6.7 | not-started | 3 | — | — | Graceful shutdown |
| 6.8 | not-started | 2 | — | — | Connection pool |
| 6.9 | not-started | 6 | — | — | Monitoring |
| 6.10 | not-started | 4 | — | — | Rollback proc |
| **TOTAL** | — | **40** | — | — | 5 days |

---

## 🚀 Demo Script (End of Sprint)

```bash
#!/bin/bash
# Sprint 6 Complete: Production Hardening Demo

echo "=== Sprint 6: Production Hardening Demo ==="
echo ""

# 1. System is healthy
echo "1. Health Check"
curl -s http://localhost:8000/health/readiness | jq .
echo "✅ System ready for traffic"
echo ""

# 2. Inject failure (Gmail API down)
echo "2. Simulating Gmail API Failure"
export GMAIL_API_URL=http://localhost:9999  # Dead endpoint
echo "Gmail endpoint: $GMAIL_API_URL (dead)"
echo ""

# 3. System continues (circuit opens)
echo "3. Submitting Form While API Down"
response=$(curl -s -X POST http://localhost:8000/api/webhooks/hubspot/forms \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}')
echo "Response: $response"
echo "✅ Form accepted (draft queued, API call skipped)"
echo ""

# 4. Check circuit state
echo "4. Circuit Breaker State"
curl -s http://localhost:8000/health/dependencies | jq .
echo "✅ Gmail circuit OPEN (failed fast)"
echo ""

# 5. Check Sentry for error context
echo "5. Error Tracking (Sentry)"
echo "Would show in Sentry dashboard:"
echo "  - Error: Gmail API unavailable"
echo "  - Context: form_id, user_id, timestamp"
echo "  - Status: Alert sent to Slack"
echo "✅ Error tracked with full context"
echo ""

# 6. Monitoring dashboard
echo "6. Grafana Metrics"
echo "Dashboard would show:"
echo "  - Request rate: unchanged"
echo "  - Error rate: spike (but transient)"
echo "  - Gmail circuit: OPEN"
echo "  - Queue depth: 1 pending"
echo "✅ Visibility into system state"
echo ""

# 7. Restore API
echo "7. Gmail API Recovery"
export GMAIL_API_URL=https://gmail.googleapis.com
echo "Gmail endpoint: restored"
sleep 60  # Wait for circuit half-open window
echo "✅ Circuit auto-recovery: open → half-open → closed"
echo ""

# 8. Queue drains
echo "8. Queue Processing"
curl -s http://localhost:8000/api/admin/queue-status | jq .
echo "✅ Pending draft processed and sent"
echo ""

# 9. All systems green
echo "9. Final Health Check"
curl -s http://localhost:8000/health/readiness | jq .
echo "✅ System fully operational"
echo ""

echo "=== Sprint 6 Demo Complete ==="
echo ""
echo "Key Achievements:"
echo "  ✅ Security audit: No SQL injection, CSRF protected, secrets safe"
echo "  ✅ Data retention: GDPR deletion endpoint working"
echo "  ✅ Disaster recovery: Backup automation, restoration tested"
echo "  ✅ Error tracking: Sentry captures all errors with context"
echo "  ✅ Resilience: Circuit breakers prevent cascade failures"
echo "  ✅ Health checks: System state visible, auto-recovery ready"
echo "  ✅ Graceful shutdown: No data loss on SIGTERM"
echo "  ✅ Connection pool: Handles 100+ concurrent requests"
echo "  ✅ Monitoring: Grafana dashboards show RED metrics"
echo "  ✅ Rollback ready: Emergency procedure < 15 minutes"
echo ""
echo "System ready for production launch! 🚀"
```

---

## 🔄 Daily Standup Template

**Daily at [time]:**

```markdown
## Sprint 6 Standup - [Date]

### Completed Today
- [ ] Task 6.X: [What was done]
  - Files: [list]
  - Tests: [passing/pending]
  - Status: [on-track/blocked]

### In Progress
- [ ] Task 6.Y: [Current focus]
  - Blocker: [if any]
  - Help needed: [if any]

### Blockers
- [ ] None / [describe]

### Tomorrow
- [ ] Start Task 6.Z
- [ ] Complete Task 6.Y
```

---

## 🛑 Decision Tree: When Stuck?

**"My task is blocked"**
→ Check dependencies completed first  
→ If dependency issue: escalate to swap order  
→ If missing context: review STRATEGIC_ROADMAP.md task spec  
→ If validation unclear: ask "how do we know this works?"

**"My test is failing"**
→ Read test error carefully (stack trace)  
→ Isolate to single assertion  
→ Verify validation script (proves intent)  
→ Consider: test too strict? code incomplete?

**"I'm not sure if I'm done"**
→ Check acceptance criteria (task spec)  
→ Run validation script (all checks pass?)  
→ Can you demo it in 60 seconds?  
→ Can someone else review your PR?  
→ If yes → done. If no → continue.

---

## 📚 Reference Materials

**Build Philosophy:**
- [PROJECT_BUILD_PHILOSOPHY.md](PROJECT_BUILD_PHILOSOPHY.md) - Execution OS for all builds

**Strategic Planning:**
- [STRATEGIC_ROADMAP.md](STRATEGIC_ROADMAP.md) - Full task specs + Sprint 6 details

**Prior Sprints:**
- [SPRINT_1_IMPLEMENTATION_COMPLETE.md](SPRINT_1_IMPLEMENTATION_COMPLETE.md)
- [SPRINT_2_IMPLEMENTATION_COMPLETE.md](SPRINT_2_IMPLEMENTATION_COMPLETE.md)
- [SPRINT_4_IMPLEMENTATION_COMPLETE.md](SPRINT_4_IMPLEMENTATION_COMPLETE.md)

**Documentation Hub:**
- [IMPLEMENTATION_INDEX.md](IMPLEMENTATION_INDEX.md)

---

## 🎓 Sprint 6 Success = Production Ready

**When Sprint 6 is complete, the system:**

✅ Has **visibility** (Sentry + Grafana)  
✅ Has **resilience** (circuit breakers, graceful degradation)  
✅ Has **security** (no injection, CSRF protected, secrets safe)  
✅ Has **recovery** (DR tested, rollback procedure credible)  
✅ Has **compliance** (GDPR deletion, data retention)  
✅ Handles **failure** (external APIs, database, overload)  
✅ Scales **safely** (connection pooling, queue management)  

**Result:** Production-ready autonomous sales system 🚀

---

**Last Updated:** January 23, 2026  
**Status:** READY TO EXECUTE  
**Owner:** Development Team  
**Next:** Begin Task 6.1 (Security Audit)
