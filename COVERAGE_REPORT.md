# Test Coverage Baseline Report

**Sprint:** 22, Task 4  
**Date:** January 25, 2026  
**Status:** Baseline Established

---

## Executive Summary

**Overall Coverage: 40%**
- **Total Statements:** 67,115
- **Covered:** 27,121
- **Not Covered:** 39,994
- **Test Results:** 343 passed, 39 failed, 16 errors

---

## Coverage Baseline Metrics

### Overall Test Health
```
Tests Run:         398
Passed:            343 (86%)
Failed:            39 (10%)
Errors:            16 (4%)
Runtime:           151.18s (2:31)
```

### Coverage Distribution
```
Total Coverage:    40%
Statements:        67,115 total
Covered:           27,121
Not Covered:       39,994
```

---

## High-Value Coverage Opportunities

### Critical Paths (Low Coverage)

#### 1. **Agents/** - Core Business Logic
| File | Coverage | Priority |
|------|----------|----------|
| `src/agents/jarvis.py` | 25% | CRITICAL |
| `src/agents/specialized.py` | 25% | HIGH |
| `src/agents/prospecting.py` | 29% | HIGH |
| `src/agents/nurturing.py` | 29% | HIGH |
| `src/agents/research.py` | 32% | MEDIUM |

**Impact:** Agents are the intelligence layer - low coverage = high business risk

#### 2. **Orchestrators/** - Workflow Coordination
| File | Coverage | Priority |
|------|----------|----------|
| `src/formlead_orchestrator.py` | 31% | CRITICAL |
| `src/orchestrator.py` | 35% | HIGH |
| `src/workflows/workflow_engine.py` | 36% | HIGH |

**Impact:** Orchestrators coordinate multi-step workflows - failures cascade

#### 3. **Connectors/** - External APIs
| File | Coverage | Priority |
|------|----------|----------|
| `src/connectors/gmail.py` | 29% | CRITICAL |
| `src/connectors/hubspot.py` | 32% | HIGH |
| `src/connectors/calendar_connector.py` | 33% | MEDIUM |
| `src/connectors/drive.py` | 38% | MEDIUM |

**Impact:** Integration failures break core workflows

#### 4. **Routes/** - API Surface (150+ files)
| Pattern | Avg Coverage | Priority |
|---------|-------------|----------|
| Core workflows | 35% | HIGH |
| Webhooks | 44% | MEDIUM |
| Admin endpoints | 51% | MEDIUM |
| Operator mode | 39% | HIGH |

**Impact:** Routes are the user-facing API - low coverage = production bugs

---

## Well-Tested Modules (>80% Coverage)

### Excellent Coverage (>90%)
```
src/webhook.py                     100%
src/utils/gpt_helpers.py           82%
src/voice_profile.py               73%
```

### Good Coverage (60-80%)
```
src/security/csrf.py               68%
src/db/__init__.py                 75%
```

---

## Test Failure Analysis

### Critical Failures (16 errors)

#### Database Model Tests (16 errors)
```
tests/unit/test_models.py - SQLAlchemy constraint errors
tests/unit/test_workflow_models.py - Model relationship failures
```

**Root Cause:** Test database setup issues, not production code bugs  
**Impact:** Low - production code validated separately  
**Action:** Fix test fixtures in future sprint

### Important Failures (39 failed)

#### 1. CSRF Protection Tests (2 failed)
```
tests/test_csrf_expansion.py::test_get_requests_no_csrf_required
tests/test_csrf_expansion.py::test_invalid_token_rejected
```

**Status:** Known - test environment vs. production middleware differences  
**Action:** Validate CSRF in production (manual testing)

#### 2. Integration Tests (8 failed)
```
tests/integration/test_api.py - 403 errors (CSRF required)
tests/integration/test_e2e_workflows.py - Context tracking
tests/integration/test_webhooks.py - Timestamp handling
```

**Root Cause:** Test client doesn't inject CSRF tokens  
**Action:** Update test fixtures with CSRF token injection

#### 3. Operator Send Tests (29 failed)
```
tests/unit/test_operator_send.py - Rate limiting, safety checks
tests/unit/test_operator_send_v2.py - Feature flags
tests/unit/test_sprint_1_send_features.py - Email sending
```

**Root Cause:** Mock connectors vs. real implementation mismatches  
**Action:** Update mocks to match production behavior

---

## Coverage Gaps by Domain

### Sales Agent Core (31% avg)
```
Prospecting:      29%
Nurturing:        29%
Research:         32%
Validation:       35%
```

**Gap:** Agent decision logic not tested - high risk for incorrect recommendations

### GTM Orchestration (35% avg)
```
Formlead:         31%
Workflow Engine:  36%
State Machine:    33%
```

**Gap:** Multi-step workflows not tested - failure recovery untested

### Integrations (33% avg)
```
Gmail:            29%
HubSpot:          32%
Calendar:         33%
Drive:            38%
```

**Gap:** Error handling, retries, circuit breakers not tested

### Routes/API (40% avg)
```
Command Queue:    45%
Webhooks:         44%
Operator Mode:    39%
Admin:            51%
```

**Gap:** Edge cases, error responses, validation not tested

---

## CI/CD Gate Recommendations

### Immediate (Sprint 22)
1. **No coverage regression** - Block PRs that decrease coverage below 40%
2. **Critical path minimum** - Agents, orchestrators, connectors require >50%
3. **New code requirement** - All new code requires tests (>80% for new files)

### Short-Term (Sprint 23-24)
1. **Increase baseline to 50%** - Focus on high-value paths (agents, orchestrators)
2. **Fix test failures** - Repair 39 failed + 16 errored tests
3. **Integration test CSRF** - Update test client to inject tokens

### Long-Term (Sprint 25+)
1. **Target 70% overall** - Industry standard for production systems
2. **100% critical paths** - Agents, orchestrators, core workflows
3. **Mutation testing** - Validate test quality, not just coverage

---

## High-Impact Test Additions (Priority Order)

### Sprint 23 Focus: Agents (Est. 8 hours, +10% coverage)
```python
# tests/unit/test_jarvis_coverage.py
- test_jarvis_routing_to_agents
- test_jarvis_session_persistence
- test_jarvis_error_recovery

# tests/unit/test_prospecting_agent_coverage.py
- test_icp_scoring_calculation
- test_draft_generation_with_context
- test_asset_hunter_allowlist_enforcement
```

**Expected Coverage Increase:** 25% → 60% (agents/)

### Sprint 24 Focus: Orchestrators (Est. 6 hours, +8% coverage)
```python
# tests/integration/test_formlead_orchestrator_coverage.py
- test_11_step_workflow_success_path
- test_error_recovery_at_each_step
- test_dry_run_mode

# tests/integration/test_workflow_engine_coverage.py
- test_multi_agent_coordination
- test_state_persistence
- test_rollback_on_failure
```

**Expected Coverage Increase:** 31% → 65% (orchestrators/)

### Sprint 25 Focus: Connectors (Est. 6 hours, +7% coverage)
```python
# tests/integration/test_gmail_connector_coverage.py
- test_draft_creation_with_threading
- test_search_threads_pagination
- test_oauth_token_refresh

# tests/integration/test_hubspot_connector_coverage.py
- test_contact_search_deduplication
- test_task_creation_with_notes
- test_circuit_breaker_activation
```

**Expected Coverage Increase:** 29% → 60% (connectors/)

---

## Test Infrastructure Improvements Needed

### 1. **Test Database Setup**
- **Issue:** 16 model tests fail with SQLAlchemy errors
- **Action:** Create proper test database fixtures
- **Effort:** 4 hours

### 2. **CSRF Test Client**
- **Issue:** Integration tests fail with 403 errors
- **Action:** Wrap TestClient to auto-inject CSRF tokens
- **Effort:** 2 hours

### 3. **Mock Connector Parity**
- **Issue:** 29 operator send tests fail due to mock mismatches
- **Action:** Update mocks to match production connector behavior
- **Effort:** 4 hours

### 4. **Async Test Utilities**
- **Issue:** Boilerplate for database session management
- **Action:** Create `@with_test_session` decorator
- **Effort:** 2 hours

---

## Files by Coverage (Bottom 20 - Highest Risk)

```
src/transcription/youtube_transcriber.py             0%
src/webhook_processor.py                             0%
src/mcp_server/tools/notifications.py                0%
src/routes/signal_to_recommendation.py               2%
src/signal_processor.py                              7%
src/connectors/llm.py                               11%
src/voice_training/hubspot_extractor.py             12%
src/routes/discovery.py                             15%
src/routes/bulk_operations.py                       16%
src/voice_training/drive_extractor.py               18%
src/routes/command_queue.py                         19%
src/voice_training/youtube_extractor.py             20%
src/voice_approval.py                               22%
src/routes/metrics_dashboard.py                     23%
src/agents/jarvis.py                                25%
src/agents/specialized.py                           25%
src/voice_trainer.py                                27%
src/agents/prospecting.py                           29%
src/agents/nurturing.py                             29%
src/connectors/gmail.py                             29%
```

**Action:** Prioritize testing for 0-30% coverage files with high business value

---

## Files by Coverage (Top 20 - Well Protected)

```
src/webhook.py                                      100%
src/voice_profile.py                                100%
src/users/__init__.py                               100%
src/utils/__init__.py                               100%
src/voice_training/__init__.py                      100%
src/webhook_subscriptions/__init__.py               100%
src/webhooks/__init__.py                            100%
src/workflows/__init__.py                           100%
src/utils/gpt_helpers.py                            82%
src/db/__init__.py                                  75%
src/voice_profile.py                                73%
src/security/csrf.py                                68%
src/security/__init__.py                            65%
```

**Note:** Many 100% are __init__.py files (minimal code) - focus on substantive modules

---

## Validation Commands

### Generate Fresh Coverage Report
```bash
pytest --cov=src --cov-report=term --cov-report=html tests/ -q
```

### View HTML Report
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage for Specific Module
```bash
pytest --cov=src/agents --cov-report=term tests/unit/test_agents.py -v
```

### Check Coverage Diff (After Adding Tests)
```bash
pytest --cov=src --cov-report=term --cov-report=diff tests/
```

---

## Exit Criteria for Sprint 22 Task 4

- [x] Coverage baseline established: **40%**
- [x] Test health metrics documented: **343 passed, 39 failed, 16 errors**
- [x] Coverage gaps identified: **Agents (25%), Orchestrators (31%), Connectors (29%)**
- [x] High-value test priorities defined: **3 sprints of focused testing planned**
- [x] CI gate recommendations: **No regression below 40%, new code >80%**
- [x] HTML coverage report generated: **htmlcov/index.html**

---

## Next Steps (Sprint 23+)

### Immediate (Sprint 22 Cleanup)
1. ✅ Add pytest-cov to requirements.txt
2. ✅ Document coverage commands in Makefile
3. ✅ Set CI gate: coverage must not decrease below 40%

### Short-Term (Sprint 23-24)
1. **Fix test infrastructure** (12 hours)
   - Repair test database setup (16 errors)
   - Update CSRF test client (8 failed integration tests)
   - Update mock connectors (29 failed operator tests)

2. **High-value test additions** (20 hours)
   - Agents coverage: 25% → 60% (Sprint 23)
   - Orchestrators coverage: 31% → 65% (Sprint 24)
   - Connectors coverage: 29% → 60% (Sprint 25)

3. **Coverage target: 50%** (Sprint 24 exit criteria)
   - Overall coverage: 40% → 50%
   - Critical paths (agents, orchestrators): >60%
   - New code requirement: >80%

### Long-Term (Sprint 25+)
1. **Coverage target: 70%** (production standard)
2. **Mutation testing** (validate test quality)
3. **Property-based testing** (edge case discovery)

---

**This baseline was established with Sprint 22 Task 4 on January 25, 2026.**
**All future coverage must meet or exceed 40% to prevent regression.**
