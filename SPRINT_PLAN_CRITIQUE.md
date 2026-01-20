# Sprint Plan Critique: Sales Agent System

**Review Date:** January 20, 2026  
**Scope:** 15-sprint prospecting + nurturing agent system (Gmail, HubSpot, Google Drive, Calendar)  
**Tech Stack:** Python 3.12, FastAPI, Celery+Redis, Postgres+pgvector, GCP Cloud Run  
**Mode Requirement:** DRAFT_ONLY (default) → SEND_ALLOWED (gated)

---

## EXECUTIVE SUMMARY

**Overall Assessment:** The plan demonstrates solid understanding of the problem domain and reasonable sequencing for core workflows. However, it contains **significant architectural gaps, premature feature implementation, and distributed safety concerns** that create integration debt and operational risk.

**Critical Issues:** 5  
**Major Issues:** 8  
**Minor Issues:** 7

**Recommendation:** Restructure into 18-19 sprints by extracting foundational security, testing, and infrastructure work earlier. Execute dependency injection and safety gates BEFORE use case implementation.

---

## DETAILED CRITIQUE BY FOCUS AREA

---

### 1. MISSING TICKETS & ARCHITECTURAL COMPONENTS

#### 1.1 **[CRITICAL] Error Handling & Resilience Framework**
- **Severity:** HIGH
- **Issue:** No explicit sprint for API resilience patterns (retry logic, exponential backoff, circuit breakers, fallbacks). External APIs (Gmail, HubSpot, GCP) are failure points.
  - Gmail API: rate limits (429), quota errors, network timeouts
  - HubSpot: webhooks may duplicate; no deduplication strategy
  - GCP: transient outages on Cloud Run, Firestore failures
- **Current State:** Scattered across sprints; implicit in Celery task design
- **Consequence:** Production outages, data loss, infinite retry loops, cascading failures
- **Fix:** 
  - **New Sprint 0.5 (Pre-Foundation):** "Resilience & Error Handling"
    - Implement base retry decorator with exponential backoff (tenacity library)
    - Circuit breaker pattern for external services (pybreaker)
    - Define idempotency keys across all async operations
    - Document SLOs/SLAs for each external service
  - Add acceptance criteria: "All external API calls have retry logic and circuit breaker wired before Sprint 2"

---

#### 1.2 **[CRITICAL] Secrets Management & OAuth2 Token Lifecycle**
- **Severity:** HIGH
- **Issue:** No sprint for handling API keys, OAuth2 refresh tokens, service account credentials.
  - Gmail: OAuth2 tokens expire; refresh token rotation?
  - HubSpot: API key rotation policy?
  - GCP credentials: workload identity, key rotation?
- **Current State:** Assumed in config (Sprint 0), but no lifecycle management
- **Consequence:** Token expiry → all workflows break; leaked credentials → account compromise
- **Fix:**
  - **New Sprint 0.75 (Post-Foundation, Pre-Models):** "Secrets & OAuth2 Management"
    - Integrate Google Cloud Secret Manager for API keys
    - Implement OAuth2 token refresh loop with event-based triggers
    - Create credential rotation playbook (quarterly audit)
    - Wire up token cache layer (Redis) with TTL
  - Acceptance criteria: "OAuth2 refresh ≤1s latency; key rotation testable in staging"

---

#### 1.3 **[HIGH] Rate Limiting & Quota Management**
- **Severity:** HIGH
- **Issue:** Sprint 11 (Quotas) addresses *operator-defined* limits (daily email caps), but NOT:
  - Gmail API rate limits (429 backoff)
  - HubSpot API rate limits (per second/minute)
  - Google Drive quota usage tracking
  - Cascading quota exhaustion (if Celery workers all hammer Gmail at once)
- **Current State:** Assumed Celery handles fairness; no explicit quota tracking
- **Consequence:** Gmail/HubSpot may throttle or block; quality gates become unreliable
- **Fix:**
  - Expand Sprint 11 (Quotas) to include:
    - Add `external_rate_limiter` service that wraps Gmail/HubSpot clients
    - Track API quota usage (tokens per minute) in Redis
    - Implement token bucket algorithm for Gmail, sliding window for HubSpot
    - Add metrics: `gmail_rate_limit_hits`, `hubspot_rate_limit_hits`
  - New acceptance criteria: "System gracefully degrades under 80%+ Gmail quota; alerts at 70%"

---

#### 1.4 **[HIGH] Webhook Security & Event Validation**
- **Severity:** HIGH
- **Issue:** Sprint 4 mentions "form listener" (webhook from HubSpot), but no sprint covers:
  - HMAC signature validation (prevent spoofed events)
  - Replay attack prevention (nonce/timestamp validation)
  - Event ordering guarantees (out-of-order webhook delivery from HubSpot)
  - Dead letter queue for failed webhook processing
- **Current State:** Assumed in HubSpot connector; no explicit validation layer
- **Consequence:** Malicious actors trigger workflows; duplicate/out-of-order events corrupt data
- **Fix:**
  - **Expand Sprint 4 (HubSpot)** to include:
    - Add webhook signature verification (HMAC-SHA256 against HubSpot secret)
    - Implement idempotency store (PostgreSQL) to deduplicate events by `event_id`
    - Add event timestamp validation (reject events >5min old)
    - Implement dead letter queue (failed webhooks → DLQ topic → Celery retry)
  - New acceptance criteria: "100% of webhook tests include signature validation; no valid events rejected"

---

#### 1.5 **[HIGH] Data Backup & Disaster Recovery**
- **Severity:** HIGH
- **Issue:** No sprint covers backup strategy for:
  - Postgres database (daily snapshots? point-in-time recovery?)
  - Redis state (Celery task queue persistence?)
  - VoiceProfile embeddings (pgvector backups?)
  - GCP Cloud Run state (stateless, but what about Cloud Storage?)
- **Current State:** Implicit assumption of GCP managed services; untested
- **Consequence:** Data loss after infrastructure failure; RTO/RPO unknown
- **Fix:**
  - **New Sprint 15.5 (Monitoring +):** "Backup & Disaster Recovery"
    - Define RTO (recovery time objective) = 1 hour, RPO (recovery point objective) = 15 min
    - Configure automated daily Postgres snapshots (GCP Cloud SQL)
    - Implement Redis persistence (AOF + snapshots) with daily backups
    - Create runbook: "Restore from backup in <30 min"
    - Test recovery quarterly
  - Acceptance criteria: "RTO/RPO documented; restore tested from backup"

---

#### 1.6 **[MEDIUM] State Machine Management for Multi-Step Workflows**
- **Severity:** MEDIUM
- **Issue:** Sprint 7 (Use Case #1) implements: form trigger → draft → HubSpot write → (maybe) send. No explicit state machine.
  - What if draft creation fails after trigger is recorded?
  - What if HubSpot write succeeds but send is rejected?
  - How do we recover from partial failures?
- **Current State:** Assumed implicit in orchestrator; no state persistence
- **Consequence:** Orphaned workflows; audit trails break; hard to debug
- **Fix:**
  - **Add to Sprint 7 context:** Implement finite state machine (FSM) library (transitions or state-machine-cat)
    - States: `triggered` → `draft_pending` → `draft_created` → `hubspot_pending` → `sent/failed/draft_only`
    - Persist state in Postgres `workflow_state` table
    - Implement idempotent state transitions (safe to retry from any state)
  - Acceptance criteria: "All workflow state transitions logged; recovery from any failure state testable"

---

#### 1.7 **[MEDIUM] Data Lineage & Audit Trail**
- **Severity:** MEDIUM
- **Issue:** Sprint 8 mentions "audit logging" but no comprehensive data lineage:
  - Where did this email draft originate? (contact → form → trigger → draft)
  - What data was used to generate it? (VoiceProfile? AssetHunter findings?)
  - Who approved it? (future SEND_ALLOWED mode)
  - What was the decision reasoning? (TriggerAgent scored it 8.5/10)
- **Current State:** Scattered across agent outputs; no unified lineage
- **Consequence:** GDPR "right to explanation" violations; hard to debug agent decisions
- **Fix:**
  - **Expand Sprint 8 (Quality Gates)** or **add Sprint 8.5 (Data Lineage)**:
    - Create `audit_event` table: `id, timestamp, entity_type, entity_id, action, actor, old_value, new_value, reason`
    - Add lineage tracking to DraftWriter output (embed VoiceProfile ID, AssetHunter result IDs)
    - Implement lineage query endpoint: "Show me all inputs/outputs for draft_id=X"
  - Acceptance criteria: "Full lineage queryable for 100% of generated drafts; compliant with GDPR auditing"

---

---

### 2. OVERSIZED / VAGUE TICKETS

#### 2.1 **[HIGH] Sprint 4 (HubSpot) Combines Too Many Concerns**
- **Current Scope:** Entity sync + form listener + task/note writer + IdentityResolver agent
- **Issue:** This is 4 separate systems:
  1. Sync: Contacts/companies → Postgres (read-only cache or mutable state?)
  2. Webhook: Form submission → trigger workflow
  3. Writer: Create tasks/notes in HubSpot (requires authentication, error handling)
  4. Agent: IdentityResolver (fuzzy match contact across platforms)
- **Risk:** One failure (e.g., webhook HMAC broken) blocks entire sprint delivery
- **Fix:** Split into 2 sprints:
  - **Sprint 4a (HubSpot Read):** Entity sync + IdentityResolver agent only
    - Clear DoD: "Contacts synced to Postgres; IdentityResolver passes unit tests with 90%+ accuracy on test set"
  - **Sprint 4b (HubSpot Write + Webhooks):** Form listener + task/note writer
    - Depends-on Sprint 4a + Sprint 0.75 (OAuth2)
    - Clear DoD: "Form webhook validated, deduped, written to tasks within 30s; no false positives"

---

#### 2.2 **[HIGH] Sprint 5 (Google Drive) Is Underspecified**
- **Current Scope:** Allowlist indexing + document extraction + chunking + AssetHunter agent
- **Vagueness:**
  - "Allowlist indexing": How many documents? Type checking? What metadata is indexed?
  - "Document extraction": PDF? DOCX? Images? OCR required?
  - "Chunking": Fixed-size? Semantic? Overlap strategy?
  - "AssetHunter agent": What qualifies as an "asset"? How is relevance scored?
- **Risk:** Sprint might complete with incomplete extraction (e.g., OCR fails on PDF images) or poor chunking (embedding quality tanks)
- **Fix:**
  - **Add acceptance criteria:**
    - "Drive index scans N=500 test documents; extraction succeeds on 98%+ (log failures)"
    - "Chunking tested: mean chunk length 200–300 tokens; overlap=50 tokens; embedding quality >0.85 cosine sim to synthetic queries"
    - "AssetHunter recall: finds 95%+ of seeded assets in test corpus"
  - **Split if needed:**
    - Sprint 5a: Allowlist + extraction
    - Sprint 5b: Chunking + embedding + AssetHunter agent
  - Add a **dependency on Sprint 5 (or earlier)**: Vector embedding infrastructure (pgvector, embedding model, inference)

---

#### 2.3 **[MEDIUM] Sprint 7 (Use Case #1) Conflates Multiple Agents & Orchestration**
- **Current Scope:** Form trigger + TriggerAgent + NextStepPlanner + DraftWriter + CRMHygiene + orchestrator + Celery task + write to HubSpot
- **Issue:**
  - Which agent runs first? (TriggerAgent or NextStepPlanner?)
  - What if NextStepPlanner decides "no next step"? (short-circuit draft creation)
  - CRMHygiene: Does it run pre-draft or post-draft? Pre-send?
  - Orchestrator: Is it a state machine, a DAG, or imperative code?
- **Risk:** Delivery becomes nebulous; hard to tell what "done" means
- **Fix:**
  - **Clarify scope:** Create a sequence diagram:
    ```
    form_submitted
      → TriggerAgent (score contact, decide if worth pursuing)
         [score < threshold? → abort]
      → IdentityResolver (dedupe contact across systems)
      → NextStepPlanner (decide what action: email, call, etc.)
      → DraftWriter (generate email draft)
      → CRMHygiene (scrub PII, validate tone)
      → QualityGate (risk score, check guardrails)
      → [DRAFT_ONLY] store draft
      → [SEND_ALLOWED] await approval → send
    ```
  - **Split Sprint 7 into 2–3:**
    - **Sprint 7a (Agent Foundation):** TriggerAgent + NextStepPlanner (scoring & routing only)
      - DoD: "Each agent returns structured decision; inputs/outputs logged"
    - **Sprint 7b (Draft Generation):** DraftWriter + CRMHygiene
      - Depends-on Sprint 6 (VoiceProfile), Sprint 5 (AssetHunter)
      - DoD: "Draft generated in <5s; PII scrubbing 100% effective on test set"
    - **Sprint 7c (Orchestration & Celery Integration):** Glue agents together, wire Celery, add error handling
      - Depends-on all of above + Sprint 8 (QualityGate)

---

#### 2.4 **[MEDIUM] Sprint 8 (Quality Gates) Mixes Concerns**
- **Current Scope:** Risk scoring + PII detection + audit logging + suppression list + GateAgent
- **Issue:**
  - Risk scoring: Numerical model (ML-based? Rule-based?)
  - PII detection: Regex? Spacy? Transformer model?
  - Audit logging: Event sourcing? Or just DB table?
  - Suppression list: How is it populated? Who manages it?
  - GateAgent: Separate agent or function of risk scoring?
- **Risk:** Trying to deliver all simultaneously makes QA hard; if risk scoring is wrong, blocks entire sprint
- **Fix:**
  - Split into 2 sprints:
    - **Sprint 8a (Risk Scoring & Gate):** Define risk scoring model (rule-based initially); implement GateAgent; gate function
      - DoD: "Risk scorer returns 0–100 confidence; gates draft if >threshold; threshold calibrated on test set"
    - **Sprint 8b (Safety Validation & Audit):** PII detection + audit logging + suppression list management
      - Depends-on Sprint 8a
      - DoD: "PII detection >99% precision on test set; 100% of decisions logged with lineage; suppression list enforced"

---

#### 2.5 **[MEDIUM] Sprint 9 (Use Case #2: Story Pitching) Is Underspecified**
- **Current Scope:** "Segmentation, targeting, writer agents, bulk orchestrator"
- **Vagueness:**
  - What is "story pitching"? (E.g., "We use your product in X industry; here's a case study")
  - How is segmentation done? (Rule-based? ML-based clustering?)
  - Targeting: How are contacts chosen? (HubSpot list + scoring?)
  - Writer agents: Same as DraftWriter or specialized?
  - Bulk orchestrator: How many emails per day? Queue? Concurrency?
- **Risk:** Requirements churn; likely to slip or ship incomplete
- **Fix:**
  - **Add to requirements:** Concrete example: "Send 'manufacturing case study' to 500 contacts in automotive industry with >100 employees; target 10/day max; track opens in HubSpot"
  - Define acceptance criteria:
    - Segmentation: "500 test contacts correctly classified; 90%+ precision"
    - Drafts: "Generated in bulk without rate-limit errors; 95%+ success rate"
    - Orchestrator: "Publishes 10 emails/day consistently; queue backlog <100 at end of day"

---

#### 2.6 **[MEDIUM] Sprint 15 (Monitoring & Deployment) Is Too Broad**
- **Current Scope:** Structured logging + metrics + GCP Cloud Run + alerting
- **Issue:**
  - Structured logging: JSON logging? Log rotation? Retention?
  - Metrics: Prometheus? CloudMetrics? What metrics matter?
  - Cloud Run: Is it a new setup or reusing existing?
  - Alerting: On what thresholds? To whom? Runbooks?
- **Risk:** Single sprint; likely misses critical observability gaps; on-call response slow
- **Fix:**
  - **Split Sprint 15 into 2:**
    - **Sprint 15a (Observability Setup):** JSON logging + Prometheus scrape + basic dashboards
      - DoD: "All services log JSON; metrics dashboard shows request latency, error rate, queue depth"
    - **Sprint 15b (Production & Alerting):** Cloud Run deployment + alerting + runbooks
      - Depends-on 15a
      - DoD: "Deployed to staging; alerts fire on error rate >5%, latency p99 >2s; runbook exists for each alert"

---

---

### 3. WEAK VALIDATION & ACCEPTANCE CRITERIA

#### 3.1 **[HIGH] Unclear Definition of "Done" Across Sprints**
- **Issue:** Most sprints lack specific, measurable acceptance criteria (ACs)
  - Sprint 2 (Gmail): "Thread fetch" and "message sync" — what counts as success?
  - Sprint 6 (Voice learning): "Extract patterns" — quantify pattern extraction accuracy
  - Sprint 10 (Feature flags): "Safe path to SEND_ALLOWED" — what prevents accidental sends?
- **Risk:** Ambiguous scope; incomplete implementation; poor handoff to next sprint
- **Fix:**
  - **Mandate for all sprints:** Every feature has 3–5 quantified ACs
    - Example (Sprint 2 Gmail):
      - AC1: "Fetch threads for 100 test contacts; 100% correctness on sample comparison"
      - AC2: "Message sync latency <500ms per thread; 99% availability"
      - AC3: "Embeddings generated for all fetched messages; cosine similarity >0.80 to manual query intent"
      - AC4: "State persisted: restart sync picks up from last checkpoint; no duplicates"
      - AC5: "Error handling: network failure → exponential backoff; recover without data loss"

---

#### 3.2 **[HIGH] No Validation Strategy for PII Safeguards**
- **Issue:** Sprint 6 mentions "PII safeguards" but Sprint 8 includes "PII detection." How do we validate they work?
  - Precision: False positives (flag legitimate data as PII) → blocks valid drafts
  - Recall: False negatives (miss PII) → sends sensitive data
  - Test set: Do we have labeled PII dataset?
- **Risk:** Deploy PII scrubber with 70% recall → accidentally send SSNs or health data
- **Fix:**
  - **Expand Sprint 8b (Safety & Audit):**
    - Create/curate PII test dataset (500+ examples: SSN, credit card, health info, addresses)
    - Define target metrics: Precision ≥99%, Recall ≥99%
    - Implement A/B testing: Run PII detection on test set, measure F1 score
    - Acceptance criteria: "PII detector passes A/B test with F1 >0.99 before SEND_ALLOWED enabled"

---

#### 3.3 **[MEDIUM] No Validation of Agent Decision Quality**
- **Issue:** Sprint 7 (TriggerAgent, NextStepPlanner, DraftWriter) and Sprint 9 (writer agents) generate business-critical decisions/content.
  - How do we know TriggerAgent isn't scoring all contacts as "ignore"?
  - How do we measure draft quality? (Tone, grammar, relevance?)
  - How do we detect agent failure modes (e.g., generating duplicate content)?
- **Risk:** Agent produces garbage; business user trusts it; poor quality damages brand
- **Fix:**
  - **Add to Sprint 7c & Sprint 9:**
    - Create test harness: 50–100 hand-labeled contacts with expected decisions (TriggerAgent should score 7+) and draft quality ratings (grammar score, tone match)
    - Acceptance criteria:
      - TriggerAgent: "Mean absolute error between predicted & expected scores <1.0 on test set"
      - DraftWriter: "Mean grammar/tone score >0.85; 0 exact duplicates in 50-draft sample"
      - NextStepPlanner: "Route decisions consistent with contact priority; no unexpected action types"

---

#### 3.4 **[MEDIUM] Unclear Transition Criteria: DRAFT_ONLY → SEND_ALLOWED**
- **Issue:** Sprint 10 enables feature flags for SEND_ALLOWED, but no documented criteria for when it's safe to flip.
  - What metrics must pass?
  - What manual testing is required?
  - Who approves? (Legal? Business?)
- **Risk:** Premature enable → sends bad drafts; misses sales opportunities
- **Fix:**
  - **Add to Sprint 10 (Feature Flags & Mode):**
    - Create checklist: "Safe to Enable SEND_ALLOWED"
      - [ ] E2E tests pass (Sprint 14)
      - [ ] PII detector F1 > 0.99 (from Sprint 8b)
      - [ ] Draft quality A/B test: score > threshold on 100 manual ratings
      - [ ] Guardrails checker: 0 policy violations on 1000 generated drafts
      - [ ] Legal/Compliance review signed off
      - [ ] Rollback plan documented & tested
    - Acceptance criteria: "Checklist reviewed & approved by TPM + Legal before flag flip"

---

---

### 4. SEQUENCING RISKS & DEPENDENCY GAPS

#### 4.1 **[CRITICAL] Feature Flags Must Come BEFORE Use Cases**
- **Current Order:**
  - Sprint 7 (Use Case #1: form → draft)
  - Sprint 10 (Feature flags: DRAFT_ONLY vs SEND_ALLOWED)
- **Risk:** Build entire use case without safeguards; if feature flag system breaks, no way to disable in prod
- **Fix:**
  - **Move Sprint 10 to Sprint 6.5 (Post-VoiceProfile, Pre-Use Case #1):**
    - Implement feature flag service (LaunchDarkly, Unleash, or custom Redis-based)
    - Wire DRAFT_ONLY check into every send path (Gmail, HubSpot writes, async tasks)
    - Add acceptance criteria: "All send paths check flag; unit tests verify sends blocked when DRAFT_ONLY=true"
  - This ensures all subsequent work (Sprint 7+) is protected by default

---

#### 4.2 **[CRITICAL] Quality Gates Must Come BEFORE Use Case Implementation**
- **Current Order:**
  - Sprint 7 (Use Case #1 implementation)
  - Sprint 8 (Quality gates: risk scoring, PII, audit)
- **Risk:** Build entire workflow, then discover risk scoring is broken → rework entire flow
- **Fix:**
  - **Move Sprint 8a (Risk Scoring & Gate) to Sprint 6.25:**
    - Implement baseline risk scorer (rule-based: contact tier, industry, message tone)
    - Implement GateAgent that enforces minimum score before draft is created
    - Acceptance criteria: "Gate function callable; rejects 50%+ of low-quality candidates"
  - **Keep Sprint 8b (Safety Validation & Audit) as currently ordered** (post-Sprint 7, post-Use Case #1 basic flow)

---

#### 4.3 **[HIGH] Quotas Must Come BEFORE Use Cases**
- **Current Order:**
  - Sprint 7–9 (Use cases generate emails)
  - Sprint 11 (Quotas: daily/weekly limits per contact)
- **Risk:** Use case generates 1000 emails to a single contact on day 1 → user blames system
- **Fix:**
  - **Move Sprint 11 (Quotas) to Sprint 8.5:**
    - Implement quota checker (PostgreSQL table: `contact_id, email_sent_today, email_sent_week`)
    - Integrate into NextStepPlanner: "Is this contact under quota?" → skip if not
    - Acceptance criteria: "Quota enforced; contact never receives >N emails/day or >M/week"

---

#### 4.4 **[HIGH] Guardrails Must Come BEFORE Use Cases**
- **Current Order:**
  - Sprint 7–9 (Drafts generated for any contact)
  - Sprint 12 (Guardrails: allowed company stage, industry, employee range)
- **Risk:** Generate draft for fortune-500 CEO with no context → damage relationship
- **Fix:**
  - **Move Sprint 12 (Guardrails) to Sprint 8.75:**
    - Define allowed attributes: company.stage in ["Growth", "Series A+"], industry in ["Tech", "Finance"], employee_range=["10-100"]
    - Implement GuardrailsChecker in NextStepPlanner: "Is this contact within guardrails?"
    - Acceptance criteria: "0 drafts generated for contacts outside guardrails; guardrails configurable via admin API"

---

#### 4.5 **[MEDIUM] Testing Must Be Earlier & More Frequent**
- **Current Order:**
  - Sprint 14 (E2E testing, performance benchmarks, lint gates)
- **Risk:** Discover critical bugs in Sprint 14 → rework Sprints 7–13
- **Fix:**
  - **Add per-sprint testing:**
    - Sprint 0: Lint gates, Docker compose up/down, basic FastAPI health check
    - Sprint 1: ORM tests, migration rollback tests, pgvector setup validation
    - Sprint 2: Gmail API mock tests, threading tests, embedding quality tests
    - Sprint 7: Agent orchestration mock tests, Celery task success/failure paths
    - etc.
  - **Move performance benchmarks to Sprint 13 (Pre-Gmail Send):**
    - Ensure system can handle peak load (e.g., 1000 drafts/min) before enabling sends
  - Keep Sprint 14 for integration tests + smoke tests + lint gates

---

#### 4.6 **[MEDIUM] Database Schema Evolution Not Addressed**
- **Issue:** Sprint 1 (Data models) creates initial schema; Sprints 2–14 add requirements (e.g., workflow_state table for FSM, audit_event table, quota tracking table)
  - How do we evolve schema safely in production?
  - How do we handle backward compatibility?
- **Risk:** Schema migration fails → data corruption or downtime
- **Fix:**
  - **Add to Sprint 1 (Data Models):**
    - Implement versioned migration system (Alembic best practices)
    - Add schema versioning table: `schema_version, timestamp, status (pending/applied/rolled_back)`
    - Define migration review process: Every schema change → code review + staging test before prod
  - **Create runbook:** "Safe schema migration in Cloud Run"

---

---

### 5. SECURITY / COMPLIANCE / PRIVACY GAPS

#### 5.1 **[CRITICAL] PII Handling Is Scattered & Incomplete**
- **Current State:** Sprint 6 (extract patterns from emails), Sprint 8 (PII detection), but no unified policy
  - How is PII logged? (Can logs leak SSNs?)
  - Who has access to VoiceProfile (contains email content)?
  - How is PII scrubbed from VoiceProfile embeddings? (Embeddings can be inverted to recover text)
- **Risk:** GDPR/CCPA violation; user data exposure; regulatory fine
- **Fix:**
  - **Add Sprint 0.5 or Sprint 5.5: "PII Handling & Privacy Policy"**
    - Define PII scope: SSN, credit card, health, location, email, phone
    - Implement PII scrubbing before embedding:
      - Remove direct PII from text → "I use [product] in [industry]"
      - Hash/tokenize email addresses before embedding
    - Add access control: Only authorized services read VoiceProfile; audit all reads
    - Create data retention policy: "VoiceProfile deleted after 30 days if no activity"
    - Acceptance criteria: "PII audit: 100% of log lines, embeddings, and storage scrubbed; no recoverable PII"
  - Involve Legal/Privacy team

---

#### 5.2 **[HIGH] OAuth2 & Token Security Not Specified**
- **Current State:** Sprint 0 (config); Sprint 0.75 (token lifecycle — per revised plan), but gaps remain
  - Token rotation: How often? Automatic or manual?
  - Revocation: If user revokes Gmail access, how long until system detects it?
  - Scope minimization: Are Gmail scopes minimized? (default is too broad)
  - Token storage: Encrypted at rest in Postgres?
- **Risk:** Token leak → account takeover; revoked token used → system fails mysteriously
- **Fix:**
  - **Expand Sprint 0.75 (OAuth2 Management):**
    - Document all OAuth2 scopes requested (Gmail, HubSpot, GCP); justify each
    - Implement token encryption: Use `cryptography` library to encrypt refresh tokens in Postgres
    - Add token revocation check: On 401 error from Gmail/HubSpot, invalidate cached token + force re-auth
    - Acceptance criteria: "Tokens encrypted at rest; revocation detected <10s; scopes minimized per Google/HubSpot best practices"

---

#### 5.3 **[HIGH] No Explicit Access Control / RBAC**
- **Current State:** No mention of who can manage drafts, approve sends, configure agents
  - Can any Celery worker read all drafts?
  - Can any API caller access all contacts?
  - Can only admin users enable SEND_ALLOWED?
- **Risk:** Malicious insider or compromised service reads sensitive data
- **Fix:**
  - **Add Sprint 10.5 (Access Control & RBAC):**
    - Define roles: admin, operator, viewer
    - Implement tenant isolation (if multi-tenant): `user_org_id` on all tables; queries filter by user org
    - Add FastAPI middleware to enforce authorization on all endpoints
    - Acceptance criteria: "All endpoints require auth; RBAC tested (non-admin cannot access other orgs' data)"

---

#### 5.4 **[HIGH] Audit Trail & Compliance Logging**
- **Current State:** Sprint 8 mentions audit logging, but no comprehensive policy
  - What events are logged? (send, approve, modify guardrails, enable flag?)
  - How long are logs retained? (GDPR: ≥30 days for compliance audits)
  - Can logs be tampered with?
  - Are logs encrypted in transit?
- **Risk:** Cannot prove who did what; audit failure; GDPR non-compliance
- **Fix:**
  - **Expand Sprint 8b (Safety & Audit):**
    - Implement immutable audit log:
      - Schema: `id (PK), timestamp, actor, resource_type, resource_id, action, before_state, after_state, reason`
      - Append-only table; trigger prevents UPDATE/DELETE
      - Retention: 90 days in hot storage (Postgres), 7 years in cold storage (Cloud Storage)
    - Use structured logging (JSON): Include audit event ID in every log line
    - Sign audit logs (HMAC key in Secret Manager) to detect tampering
  - Acceptance criteria: "100% of business-critical actions logged; tampering detection enabled; retention policy documented"

---

#### 5.5 **[MEDIUM] No Vendor Lock-in Mitigation**
- **Current State:** GCP Cloud Run, Cloud SQL (Postgres), Pub/Sub
  - What if GCP services become unavailable or too expensive?
  - Are we using GCP-specific APIs (e.g., Cloud Tasks) that would require rewrite?
- **Risk:** Forced to pay premium or migrate system
- **Fix:**
  - **Add to Sprint 0 (Foundation):**
    - Document all GCP dependencies; note which are proprietary (Cloud Run ✓ portable, Cloud Tasks ✗ proprietary)
    - Replace Cloud Tasks with Celery (already planned ✓)
    - Use standard Postgres (no Cloud SQL-specific features)
    - Document migration path: "To migrate to AWS, replace Cloud Run with ECS, Cloud SQL with RDS, Pub/Sub with SNS (≥2 weeks effort)"

---

#### 5.6 **[MEDIUM] No Data Backup & Disaster Recovery Plan**
- **Issue:** Already covered in Section 1.5, but security-critical component
- **Fix:** (See 1.5) Add Sprint 15.5 for backup/recovery

---

---

### 6. TEST STRATEGY SUFFICIENCY

#### 6.1 **[HIGH] Testing Is Concentrated at End; Insufficient Unit Tests**
- **Current State:** Sprint 14 only sprint dedicated to testing
- **Issue:**
  - No mention of unit tests per sprint
  - No mention of integration tests until Sprint 14
  - No mention of contract tests with Gmail/HubSpot APIs
  - No mention of load testing
- **Risk:** Late discovery of bugs; high rework cost; poor confidence in production
- **Fix:**
  - **Mandate for all feature sprints:**
    - Unit test coverage ≥80% (enforced by pytest in CI)
    - Integration tests for external API calls (using mocks like responses library)
    - Acceptance criteria: "All code PR requires >80% coverage; CI blocks merge on coverage drop"
  - **Add Sprint 9.5 (Integration Testing):**
    - Contract tests: Mock Gmail API; HubSpot API; verify request/response formats match real API
    - Integration tests: E2E flow from form trigger → draft creation (with mocked Gmail/HubSpot)
    - Acceptance criteria: "Contract tests pass; mock failures caught before hitting real APIs"
  - **Add to Sprint 13 (Pre-Send Integration):**
    - Load testing: Simulate 1000 draft requests/min; measure latency p99, error rate
    - Acceptance criteria: "p99 latency <2s; error rate <1%; no crashes"

---

#### 6.2 **[MEDIUM] No UAT (User Acceptance Testing) Plan**
- **Issue:** Business users (sales operators) not involved until production
- **Risk:** Shipped feature doesn't match user expectations; rework required
- **Fix:**
  - **Add to Sprint 14 (E2E Testing):**
    - Create UAT test plan: 5–10 realistic scenarios (e.g., "form submission for high-value contact → draft generated in 5s → user can edit → save to draft")
    - Set up staging environment for business user testing (Sprint 14)
    - Acceptance criteria: "2–3 sales operators complete UAT; 0 blocker issues; non-blockers logged for future sprints"

---

#### 6.3 **[MEDIUM] No Chaos Engineering / Resilience Testing**
- **Issue:** What if Redis crashes? Gmail rate-limits? HubSpot webhook delivery fails?
- **Risk:** Single point of failure causes cascading outages
- **Fix:**
  - **Add to Sprint 14 (E2E Testing) or Sprint 15a (Observability):**
    - Implement chaos tests:
      - Kill Redis → verify tasks retry and succeed when Redis restarts
      - Rate-limit Gmail API responses (429) → verify exponential backoff, eventual success
      - Delay HubSpot responses (>30s) → verify timeouts handled, no task hangs
    - Tool: Chaos Toolkit or custom pytest fixtures
  - Acceptance criteria: "All major failure modes tested; system recovers without data loss"

---

---

### 7. SCALING & PERFORMANCE BOTTLENECKS

#### 7.1 **[HIGH] pgvector Scaling Not Addressed**
- **Current State:** Sprint 2 (Gmail embeddings), Sprint 5 (Drive embeddings), but no mention of:
  - Embedding model size & cost (OpenAI Ada? Local Sentence-Transformers?)
  - Batch size for embedding generation (time & cost implications)
  - Index strategy (HNSW? IVFFlat? Index size?)
  - How many embeddings can we store? (1M? 10M?)
  - Query latency: How fast is semantic search on 1M embeddings?
- **Risk:** Embeddings become slow/expensive; searches timeout; cannot scale beyond small contact base
- **Fix:**
  - **Add to Sprint 1.5 (Pre-ORM) or Sprint 2 (Gmail):**
    - Choose embedding model: Recommend Sentence-Transformers (open-source, <100MB, cheap to run)
    - Benchmark embedding time: Goal <100ms per embedding
    - Benchmark pgvector search: Goal <500ms for 1M embeddings with HNSW index
    - Document scaling assumptions: "Supports 1M embeddings; refresh cadence = weekly"
    - Acceptance criteria: "Embedding latency <100ms; search latency <500ms on 1M embeddings; index size <5GB"
  - Use Cloud SQL machine tuning to optimize pgvector queries (add `shared_buffers`, `effective_cache_size`)

---

#### 7.2 **[HIGH] Redis Scaling Not Specified**
- **Current State:** Redis for Celery queue + OAuth2 token cache (per revised plan)
- **Issue:**
  - Single Redis instance or cluster?
  - Memory limits? (If token cache grows unbounded, Redis evicts Celery tasks)
  - Persistence: AOF or RDB?
  - Replication/failover: What happens if Redis crashes?
- **Risk:** Redis memory exhausted → Celery tasks lost → workflows disappear
- **Fix:**
  - **Add to Sprint 0 (Foundation):**
    - Document Redis deployment: Recommend Redis Cluster for HA or Google Memorystore for managed service
    - Define memory limits: Reserve 70% for Celery, 20% for tokens, 10% buffer
    - Configure persistence: AOF (durability over RDB for task queue)
    - Acceptance criteria: "Redis configured for HA; memory limits enforced; persistence tested"
  - **Add monitoring (Sprint 15a):**
    - Alert if Redis memory >80%
    - Alert if Celery queue depth >10,000

---

#### 7.3 **[HIGH] Celery Worker Scaling & Concurrency Not Specified**
- **Current State:** Sprint 0 mentions Celery, but no scaling plan
- **Issue:**
  - How many Celery workers on Cloud Run?
  - Task concurrency per worker? (If all 10 workers fetch Gmail in parallel, will hit Gmail rate limits)
  - Task priorities: Are draft writes higher priority than analytics?
  - Dead letter queue: Where do failed tasks go?
- **Risk:** Uncontrolled concurrency → API rate limits → cascading failures
- **Fix:**
  - **Add to Sprint 0 or Sprint 0.75:**
    - Configure Celery:
      - Task routing: Separate queues for high-priority (drafts) vs. low-priority (analytics)
      - Concurrency: 5–10 workers; 4 tasks per worker (tune based on load testing)
      - Rate limiting: `task_rate_limit` to throttle Gmail/HubSpot calls
      - Dead letter queue: Celery Beat task that processes DLQ every 5 min
    - Acceptance criteria: "Celery workers survive 10x spike in form submissions; no rate limit errors"
  - Use Cloud Run autoscaling (CPU-based) to scale workers up/down

---

#### 7.4 **[MEDIUM] Bulk Email Orchestration Not Specified (Sprint 9)**
- **Issue:** Use Case #2 (story pitching): "Send 1000 emails to segmented contacts; 10/day max"
  - How do we queue 1000 tasks in Celery without overwhelming?
  - How do we enforce 10/day limit across Celery workers?
  - How do we distribute across multiple Cloud Run instances?
- **Risk:** Queue explodes; system crashes; quota hits
- **Fix:**
  - **Add to Sprint 9 (Use Case #2):**
    - Implement distributed rate limiter using Redis:
      - Key: `email_send_rate:2026-01-20` (daily bucket)
      - Value: counter (incremented per send; TTL=24h)
      - Rate limit check: `GET counter; if <10 && age<1min, publish task`
    - Use task batching: Create 1000 draft tasks, prioritize by contact value, release 10/day
    - Acceptance criteria: "Bulk sends never exceed limit; backlog visible in admin UI; no data loss on worker crash"

---

#### 7.5 **[MEDIUM] No Data Archival / Cleanup Strategy**
- **Issue:** Gmail threads accumulate over time; VoiceProfile embeddings grow; audit logs fill disk
  - How long do we keep email data?
  - Do we archive old emails to cold storage (Cloud Storage)?
  - Do we prune audit logs after 90 days (per compliance)?
- **Risk:** Database grows unbounded; queries slow; storage costs spike
- **Fix:**
  - **Add to Sprint 11 (Quotas) or Sprint 15b (Production):**
    - Define retention policy:
      - Gmail threads: Hot for 30 days, archive after 1 year, delete after 7 years
      - VoiceProfile: Delete after 90 days if no activity
      - Audit logs: Hot for 90 days, archive to Cloud Storage
    - Implement Celery task: `cleanup_old_data` (runs nightly)
    - Acceptance criteria: "Cleanup job runs successfully; no data loss; disk usage stays flat over time"

---

#### 7.6 **[MEDIUM] No Multi-Tenancy or Workload Isolation**
- **Issue:** If building for multiple orgs/teams, current architecture doesn't isolate data
  - One org's Celery tasks could monopolize workers
  - One org's bulk send could be rate-limited by another's
  - Data leakage: Queries missing org filter → cross-org data visible
- **Risk:** If supporting multiple customers, compliance/security nightmare
- **Fix:**
  - **Add to Sprint 0 or Sprint 10.5:**
    - Add `org_id` column to all data tables; enforce in queries via SQLAlchemy custom `@declared_attr` or query middleware
    - Isolate Celery queues by org: `tasks:org:123` (requires explicit org_id routing)
    - Implement per-org rate limits (in Redis): `org:123:email_send_rate`
  - Acceptance criteria: "No cross-org data visible; queries fail if org_id missing; Celery routing tests pass"

---

---

### 8. DOCUMENTATION & OPERATIONAL DEBT

#### 8.1 **[HIGH] No API Documentation Plan**
- **Issue:** FastAPI endpoints created across Sprints 4, 10, 15, but no plan for:
  - OpenAPI schema generation (automatic with FastAPI, but needs tweaking)
  - Endpoint documentation (description, examples, error codes)
  - Webhook documentation (HubSpot, Pub/Sub events)
  - Admin API documentation (feature flags, guardrails configuration)
- **Risk:** Operations team cannot call APIs; new developers confused; support costs high
- **Fix:**
  - **Add to Sprint 15b (Production & Deployment):**
    - Generate OpenAPI schema (FastAPI automatic)
    - Document all endpoints: `/api/v1/docs` (Swagger UI)
    - Document webhooks: Expected request body, signature validation, error handling
    - Document admin APIs: Feature flag toggle, guardrails update, quota override
    - Acceptance criteria: "All endpoints documented; Swagger UI accessible; 0 undocumented endpoints"

---

#### 8.2 **[HIGH] No Runbooks / Operational Procedures**
- **Issue:** System goes live; what if Redis crashes? Gmail quota exhausted? Agent hangs?
- **Risk:** On-call engineer confused; MTTR high; customer impact extended
- **Fix:**
  - **Add to Sprint 15b (Production) or Sprint 16 (Post-Launch):**
    - Create runbooks (markdown in repo) for:
      - "Redis crashed: How to recover Celery queue"
      - "Gmail rate-limited: What to do; how to resume"
      - "Agent decision quality degraded: Debug steps; rollback procedure"
      - "Feature flag flipped accidentally: How to revert; impact assessment"
      - "Audit log full: How to archive; how to query"
    - Each runbook includes: symptoms, root cause, mitigation, prevention
  - Acceptance criteria: "5–10 critical runbooks written; tested by on-call engineer; on-call oncall guide updated"

---

#### 8.3 **[MEDIUM] No Architecture Decision Records (ADRs)**
- **Issue:** Why did we choose Celery over AWS Lambda? Why pgvector and not Pinecone?
- **Risk:** Future decisions made without context; technical debt accumulates
- **Fix:**
  - **Add to Sprint 0 or Sprint 15b:**
    - Create ADRs (1-pager each) documenting major decisions:
      - ADR-001: "Use Celery + Redis for task queue (not AWS Lambda)" — Cost, latency, control
      - ADR-002: "Use pgvector in Postgres (not Pinecone)" — Cost, latency, compliance
      - ADR-003: "DRAFT_ONLY default mode (not SEND_ALLOWED)" — Safety, reversibility
    - Store in `docs/adr/` directory
  - Acceptance criteria: "5+ ADRs written; team reviewed; rationale clear"

---

#### 8.4 **[MEDIUM] No Troubleshooting / Debugging Guide**
- **Issue:** Agent produces garbage draft; how do we debug?
  - What logs to check?
  - How to trace decision through TriggerAgent → NextStepPlanner → DraftWriter?
  - How to replay Celery task with debug logging?
- **Risk:** Debugging slow; team frustrated; hard to learn system
- **Fix:**
  - **Add to Sprint 15b or post-launch:**
    - Create troubleshooting guide with worked examples:
      - "Draft quality low: Check VoiceProfile embeddings (cosine sim to contact industry), check DraftWriter prompt, check risk scorer decision"
      - "Email not sent: Check quota, check PII detection, check SEND_ALLOWED flag"
      - "Celery task hanging: Check Redis, check Cloud Run logs, check task timeout"
    - Include tooling: How to query Postgres for lineage, how to inspect Redis queue, how to replay task
  - Acceptance criteria: "Troubleshooting guide covers 3+ common issues; team trained"

---

#### 8.5 **[MEDIUM] No Onboarding Documentation for New Developers**
- **Issue:** New engineer joins team in Sprint 12; how to get productive?
- **Risk:** Months of ramp-up; inefficient knowledge transfer
- **Fix:**
  - **Add to Sprint 0 or Sprint 15b:**
    - Create `/docs/ONBOARDING.md`:
      - "Local setup: Docker compose up; run tests; start FastAPI dev server" (5 min)
      - "Tour of architecture: Agent flow, data models, Celery tasks" (30 min)
      - "First task: Add logging to DraftWriter agent" (2–4 hours)
      - "Key files to know: `agents/`, `models/`, `tasks.py`, `config.py`"
    - Create video walkthrough (15 min): System demo in staging
  - Acceptance criteria: "New developer completes onboarding in <1 day; can run tests and modify an agent"

---

#### 8.6 **[MEDIUM] No Data Governance / Schema Documentation**
- **Issue:** Tables created across Sprints 1–12; purpose and relationships unclear
- **Risk:** New queries miss relationships; data inconsistency; poor schema design discovered late
- **Fix:**
  - **Add to Sprint 1 (Data Models):**
    - Create schema documentation:
      - Table: `contact`: id, email, company_id, created_at, updated_at
      - Table: `draft`: id, contact_id, content, risk_score, created_at
      - Table: `audit_event`: id, resource_type, resource_id, action, actor, timestamp
      - Include ER diagram (Mermaid syntax)
    - Maintain as schema evolves (update in every sprint)
  - Acceptance criteria: "Schema fully documented; ER diagram up-to-date; new tables documented before PR merge"

---

---

## PRIORITY MATRIX & TOP RECOMMENDATIONS

### Issues by Severity

| Severity | Count | Issues |
|----------|-------|--------|
| CRITICAL | 5 | Error handling framework, OAuth2/Secrets, Feature flags pre-UC, Quality gates pre-UC, Webhook security |
| HIGH | 8 | Rate limiting, Backup/DR, Sprint 4/5/7/8 scope, Testing strategy, pgvector scaling, Redis scaling |
| MEDIUM | 10 | State machine, Audit lineage, Sprint 6/9/15 scope, Sequencing (DB, Celery), PII handling, RBAC, Vendors, Chaos testing, Email orchestration, Data governance |
| LOW | 3 | Onboarding docs, ADRs (nice-to-have), Troubleshooting guide |

---

### TOP 5 HIGHEST-PRIORITY IMPROVEMENTS

#### 1. **Restructure Sprint Sequencing: Move Safety Layers BEFORE Use Cases**
   - **Impact:** Prevents building features without guardrails; reduces rework by 30–40%
   - **Changes:**
     - Move Sprint 10 (Feature flags) → Sprint 6.5
     - Move Sprint 8a (Risk scoring gate) → Sprint 6.25
     - Move Sprint 11 (Quotas) → Sprint 8.5
     - Move Sprint 12 (Guardrails) → Sprint 8.75
   - **Effort:** 0 sprints (reorder only); **Timeline:** Move 4 sprints up 3–5 positions

---

#### 2. **Add Infrastructure Sprints for Resilience, Security, Testing**
   - **Impact:** Prevents production outages; ensures security by design; catches bugs early
   - **New Sprints:**
     - Sprint 0.5: Error handling + resilience patterns (retry, circuit breaker)
     - Sprint 0.75: OAuth2 + secrets management + token lifecycle
     - Sprint 5.5 or 6: PII handling + privacy policy + data governance
     - Sprint 9.5: Integration testing + contract tests
     - Sprint 15.5: Backup & disaster recovery + runbooks
   - **Effort:** 5 new sprints; **New Total:** 20 sprints; **Timeline Impact:** +5 weeks

---

#### 3. **Split Oversized Sprints into Focused, Atomic Stories**
   - **Impact:** Clear DoD; easier QA; reduce integration risk
   - **Changes:**
     - Sprint 4 → Sprint 4a (HubSpot read) + Sprint 4b (HubSpot write + webhooks)
     - Sprint 5 → Sprint 5a (indexing + extraction) + Sprint 5b (chunking + AssetHunter)
     - Sprint 7 → Sprint 7a (agents) + Sprint 7b (draft gen) + Sprint 7c (orchestration)
     - Sprint 8 → Sprint 8a (risk scoring) + Sprint 8b (safety validation)
     - Sprint 15 → Sprint 15a (observability) + Sprint 15b (deployment)
   - **Effort:** Reshuffling (no new work); **Timeline Impact:** +3 weeks (better parallelization)

---

#### 4. **Define Quantified Acceptance Criteria for All Sprints**
   - **Impact:** Eliminates scope ambiguity; improves handoff quality; enables objective completion
   - **Examples:**
     - Sprint 2 (Gmail): "Embedding latency <100ms; sync state persists; no duplicates on restart"
     - Sprint 7b (DraftWriter): "Draft generation <5s; grammar score >0.85; zero PII in output"
     - Sprint 9 (Bulk send): "Rate limit enforced; 10 emails/day max; queue depth <100 EOD"
   - **Effort:** 2–3 days; **Timeline:** Parallel (Sprint planning)

---

#### 5. **Add Testing & Observability Infrastructure Early (not last)**
   - **Impact:** Catches bugs as code is written; confident production launches; fast incident response
   - **Changes:**
     - Add per-sprint unit tests + coverage enforcement (80%+ threshold) in Sprint 0
     - Add integration tests in Sprint 9.5 (contract tests with mocked APIs)
     - Add load testing in Sprint 13 (pre-send verification)
     - Move structured logging + metrics dashboard to Sprint 15a (not 15b)
   - **Effort:** Distributed across sprints; **Timeline Impact:** Net zero (faster catch of bugs saves rework)

---

## SOLID AREAS (No Changes Needed)

✓ **Sprint 0 (Foundation):** Docker Compose + config + FastAPI scaffold + logging is right place/time  
✓ **Sprint 1 (Data Models):** ORM + pgvector + migrations are prerequisite for all connectors  
✓ **Sprint 2–5 (Connectors):** Logical order: Gmail, Calendar, HubSpot, Google Drive (dependency chain)  
✓ **Sprint 6 (Voice Learning):** Good placement after connectors; depends on email/interaction history  
✓ **Sprint 13 (Gmail Send):** Correct placement late in project; only enable after all safety checks  
✓ **Sprint 14 (E2E Testing):** Broad testing sprint is appropriate; should include UAT + performance  

---

## REVISED SPRINT BREAKDOWN (20 sprints)

```
Sprint 0:     Foundation (Docker, config, FastAPI, logging)
Sprint 0.5:   Resilience (retry, circuit breaker, idempotency)
Sprint 0.75:  Secrets & OAuth2 (token lifecycle, Secret Manager)
Sprint 1:     Data Models (ORM, pgvector, migrations, schema versioning)
Sprint 1.5:   Embedding infrastructure (model choice, benchmarking)
Sprint 2:     Gmail connector (thread fetch, sync, embeddings)
Sprint 3:     Calendar (freebusy, slot proposal)
Sprint 4a:    HubSpot read (entity sync, IdentityResolver)
Sprint 4b:    HubSpot write + webhooks (tasks, notes, webhook validation)
Sprint 5a:    Drive indexing & extraction
Sprint 5b:    Chunking, embeddings, AssetHunter agent
Sprint 5.5:   PII handling & privacy policy
Sprint 6:     Voice learning (extract patterns, safeguards, storage)
Sprint 6.25:  Risk scoring & gate (baseline scorer, GateAgent)
Sprint 6.5:   Feature flags (DRAFT_ONLY vs SEND_ALLOWED, kill switch)
Sprint 7a:    Agents foundation (TriggerAgent, NextStepPlanner scoring)
Sprint 7b:    Draft generation (DraftWriter, CRMHygiene)
Sprint 7c:    Orchestration & Celery integration (FSM, state persistence)
Sprint 8a:    Safety validation (PII detection, risk gates, audit)
Sprint 8.5:   Quotas (daily/weekly limits, enforcement)
Sprint 8.75:  Guardrails (company stage, industry, employee range)
Sprint 9:     Use Case #2 (story pitching, segmentation, bulk orchestrator)
Sprint 9.5:   Integration testing (contract tests, mocked APIs)
Sprint 10:    Admin API (feature flag toggle, guardrails, quota override, RBAC)
Sprint 11:    Performance & scaling (Celery tuning, pgvector benchmarks, load tests)
Sprint 12:    Gmail send (safe send path, approval, delivery tracking, Pub/Sub)
Sprint 13:    E2E & UAT (full flow tests, performance validation, business UAT)
Sprint 14:    Monitoring & observability (structured logging, metrics, dashboards)
Sprint 15:    Backup, DR & runbooks (backup strategy, recovery testing, operational procedures)
Sprint 16:    Deployment & hardening (Cloud Run setup, alerting, gradual rollout)
Sprint 17:    Documentation & onboarding (API docs, troubleshooting, ADRs, schema docs)
```

---

## CONCLUSION

The original 15-sprint plan is **70% sound** in sequencing but has **material gaps** in:
1. **Safety-first architecture** (feature flags, gates, quotas should precede use cases)
2. **Resilience & error handling** (missing dedicated sprint for retry/circuit breaker)
3. **Operational readiness** (testing, monitoring, runbooks are afterthoughts)
4. **Scope clarity** (oversized sprints lack quantified DoD)

**Recommended action:** Expand to **20 sprints** (5 weeks additional) by extracting foundational infrastructure and safety layers early. This reduces integration risk, improves code quality, and enables confident production launch.

**Timeline:** ~24 weeks (vs. 15 weeks original) is realistic and sustainable for a system handling high-stakes business communication.
