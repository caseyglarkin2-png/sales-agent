# Operator-Mode Prospecting + Nurturing Agent — Sprint Plan

**Status:** Draft (Ready for implementation)  
**Note:** Timeline estimates are intentionally omitted. Sequencing is dependency-driven, not time-based.  
**Tech Stack:** Python 3.12, FastAPI, Celery+Redis, Postgres+pgvector, GCP Cloud Run

### Validation: No Timeline Language

To verify this document contains no time estimates, run:

```bash
grep -i -E '(week|day|month|hour|duration|timeline|ETA|estimated|approximately|~\d+|4-hour|1-2|2-3|\([0-9]+ +(day|week)s?\))' docs/sprint_plan.md || echo "✓ No timeline language found"
```

## Overview

This plan builds a mini-agent system for AI-powered prospecting and nurturing:
- Monitors Gmail threads & HubSpot form submissions
- Creates threaded email drafts in a learned, personalized voice
- Proposes meeting times via Calendar freebusy
- Logs activities to HubSpot for CRM continuity
- **Default:** DRAFT_ONLY mode (human review, no auto-send)
- **Future:** SEND_ALLOWED mode with strict guardrails, quotas, approval workflows

### Architecture: Mini-Agent + Orchestrator

12 specialized agents handle discrete tasks; an orchestrator state machine choreographs them:
- **TriggerAgent** — Event → job
- **IdentityResolverAgent** — Email/domain → HubSpot entities
- **ThreadReaderAgent** — Gmail thread → structured facts
- **LongMemoryAgent** — Global context retrieval (pgvector)
- **AssetHunterAgent** — Drive file search within allowlist
- **MeetingSlotAgent** — Calendar freebusy → 2–3 slots
- **NextStepPlannerAgent** — Plan cadence + risk gating
- **DraftWriterAgent** — Compose draft in learned voice
- **CRMHygieneAgent** — Log to HubSpot
- **QualityGateAgent** — Risk/compliance gating
- **StoryPitchTargetingAgent** — Segment & rank for campaigns
- **StoryPitchWriterAgent** — Personalized campaign drafts

### Key Constraints

- **Voice Learning:** Extract patterns from historical email corpus (Gmail Sent + Drive docs), produce structured profile (phrasing patterns, tone, CTA templates, forbidden words). PII-safe (redact confidentials).
- **Drive Scope:** Index only allowlist folders (Pesti Sales root + prefixes: "CHAINge Proposals", "CP Client Reports", "CP Proposals", "Manifest 2026"; exclude "CP Closed"; plus Charlie Pesti folder via env var).
- **Gmail Scope:** Service account for read-only threads + message indexing; OAuth2 for Sent folder (voice learning) + Calendar (freebusy).
- **Draft Constraints:** Skimmable (<200 words), exactly 1 CTA, no em-dashes, no client-confidential info, must follow learned voice profile.
- **Meeting Slots:** 30-min blocks, next 1–3 business days preferred, suggest urgency ("obvious next step") without needing.
- **Safety:** Default DRAFT_ONLY, feature flags for gradual rollout, quotas (daily/weekly), per-contact frequency limits, guardrails (company stage/industry/employee range), suppression lists, kill switch, audit logging for compliance.

---

## **Revised Sprint Breakdown (20 Sprints)**

### **PHASE 1: INFRASTRUCTURE & SAFETY FOUNDATIONS (Sprints 0–5)**

---

## **SPRINT 0: Foundation ## **SPRINT 0: Foundation & Developer Experience** Developer Experience**
**Sprint Goal:** Developers can clone, run `docker compose up`, and have API responding on `localhost:8000`.

**Demo Steps:**
```bash
git clone <repo>
cd sales-agent
docker compose up --wait
curl http://localhost:8000/health  # {"status": "ok"}
```

**Tickets:**

### 0.1: Repository scaffolding, .gitignore, pyproject.toml
- **Files/Modules:** `.gitignore`, `.env.example`, `pyproject.toml`, `README.md`, `src/`, `tests/`, `docs/`, `infra/`
- **Description:** Standard Python project structure with no secrets leaked.
- **Tests/Validation:** `git status` shows only expected files; `pre-commit run --all-files` passes
- **Acceptance Criteria:** Repo is clean, linting configured, no hardcoded secrets

### 0.2: Docker Compose stack (Postgres+pgvector, Redis, minimal FastAPI service)
- **Files/Modules:** `docker-compose.yml`, `Dockerfile`, `src/main.py`
- **Description:** Multi-container: PostgreSQL 15+ (pgvector extension), Redis 7+, Python API service
- **Tests/Validation:**
  - `docker compose up --wait` succeeds
  - `curl http://localhost:8000/health` returns 200 OK
  - `psql -h localhost -U postgres -d sales_agent -c "SELECT * FROM pg_extension WHERE extname='vector';"` shows pgvector installed
  - `redis-cli -h localhost PING` returns PONG
- **Acceptance Criteria:** All services start cleanly, no timeouts, extension active

### 0.3: Config & secrets management (python-dotenv, pydantic BaseSettings)
- **Files/Modules:** `src/config.py`, `.env.example`, `src/constants.py`
- **Description:** Centralized config loader with env validation; NO hardcoded secrets.
- **Tests/Validation:** `pytest tests/unit/test_config.py::test_base_settings_validates_required_fields` passes; missing required vars raise ConfigError
- **Acceptance Criteria:** Config loads from `.env`, validates on import, all secrets externalized

### 0.4: FastAPI health check + structured logging scaffold
- **Files/Modules:** `src/main.py`, `src/logger.py`, `src/middleware.py`
- **Description:** API skeleton with JSON logging, request tracing (trace_id middleware).
- **Tests/Validation:**
  - `pytest tests/unit/test_main.py::test_health_check_returns_ok`
  - `pytest tests/unit/test_logger.py::test_logs_as_json` verifies JSON output
  - Logs include: timestamp, level, message, trace_id, service, module
- **Acceptance Criteria:** Health endpoint works, logs are valid JSON, trace_id propagates

### 0.5: Pre-commit hooks (ruff, pyright, pytest core)
- **Files/Modules:** `.pre-commit-config.yaml`, `pyproject.toml` (tool.ruff, tool.pyright)
- **Description:** Enforce code quality before commits: linting, type-checking, basic tests.
- **Tests/Validation:** `pre-commit run --all-files` passes locally
- **Acceptance Criteria:** Hooks installed, enforce Ruff + Pyright + pytest on core tests

---

## **SPRINT 1: Data Models ## **SPRINT 1: Data Models & Database Layer** Database Layer**
**Sprint Goal:** Database schema deployed, ORM models defined, migrations are repeatably reversible.

**Demo Steps:**
```bash
cd infra/migrations
alembic upgrade head
psql -h localhost -U postgres -d sales_agent -c "\dt"  # Shows all tables
```

**Tickets:**

### 1.1: SQLAlchemy ORM base + async session factory + dependency injection
- **Files/Modules:** `src/db/base.py`, `src/db/session.py`, `src/deps.py`
- **Description:** Async SQLAlchemy v2 setup with scoped sessions, FastAPI Depends injection.
- **Tests/Validation:** `pytest tests/unit/test_db.py::test_async_session_factory_works` passes; pyright has no errors
- **Acceptance Criteria:** Sessions are async, injectable, type-hinted, no blocking calls

### 1.2: Message & Thread schema (Gmail ↔ HubSpot bidirectional links)
- **Files/Modules:** `src/models/message.py`, `infra/migrations/versions/001_initial_schema.py`
- **Tables:**
  - `messages` (id, gmail_message_id UNIQUE, gmail_thread_id, sender, recipient, subject, body TEXT, embedding VECTOR(1536), gmail_metadata JSONB, created_at, updated_at)
  - `threads` (id, gmail_thread_id UNIQUE, hubspot_company_id, hubspot_contact_id, subject, last_message_at, created_at)
  - Indices: (gmail_thread_id), (hubspot_company_id), (hubspot_contact_id)
- **Tests/Validation:** Alembic migration applies cleanly; `pytest tests/unit/test_models.py::test_message_unique_key_constraint` passes
- **Acceptance Criteria:** Tables created, PKs/FKs in place, migration is reversible

### 1.3: HubSpot entities schema (company, contact, deal, form submission cache)
- **Files/Modules:** `src/models/hubspot.py`, `infra/migrations/versions/002_hubspot_schema.py`
- **Tables:**
  - `hubspot_companies` (id, hubspot_company_id UNIQUE, name, domain, industry, custom_properties JSONB, synced_at)
  - `hubspot_contacts` (id, hubspot_contact_id UNIQUE, email, firstname, lastname, company_id FK, custom_properties JSONB, synced_at)
  - `hubspot_deals` (id, hubspot_deal_id UNIQUE, dealname, company_id FK, stage, amount, synced_at)
  - `hubspot_form_submissions` (id, submission_id UNIQUE, form_id, contact_id FK, company_id FK, fields JSONB, submitted_at, created_at)
  - Indices: (hubspot_company_id), (hubspot_contact_id), (email), (form_id, submitted_at)
- **Tests/Validation:** Alembic migration, FK constraints work, cascade deletes configured
- **Acceptance Criteria:** Schemas created, cascading deletes in place

### 1.4: Task & note table (CRM activities)
- **Files/Modules:** `src/models/activity.py`, `infra/migrations/versions/003_activity_schema.py`
- **Tables:**
  - `agent_tasks` (id, hubspot_task_id, contact_id FK, company_id FK, title, body, type, due_date, status, created_at)
  - `agent_notes` (id, hubspot_note_id, contact_id FK, company_id FK, body, context_json, created_at)
- **Tests/Validation:** Alembic migration, FK constraints validated, no orphaned records possible
- **Acceptance Criteria:** Tables created, FKs enforced

### 1.5: Draft & send audit log table (immutable compliance trail)
- **Files/Modules:** `src/models/audit.py`, `infra/migrations/versions/004_audit_schema.py`
- **Tables:**
  - `draft_audit_log` (id, action, actor, draft_id, contact_id, company_id, mode (DRAFT_ONLY|SEND_ALLOWED), status (CREATED|SENT|BLOCKED|REJECTED), reason, metadata JSONB, created_at)
  - Indices: (draft_id), (contact_id), (company_id), (created_at) — for compliance queries
- **Constraint:** Immutable after insert (check constraint or application logic)
- **Tests/Validation:** Alembic migration, indices created, audit entries queryable
- **Acceptance Criteria:** Immutable, indexed for quick audit queries

### 1.6: pgvector setup + embedding tables
- **Files/Modules:** `src/models/embeddings.py`, `infra/migrations/versions/005_pgvector_schema.py`
- **Tables:**
  - `message_embeddings` (id, message_id FK UNIQUE, embedding VECTOR(1536), created_at)
  - `document_embeddings` (id, drive_file_id, chunk_index, chunk_text TEXT, embedding VECTOR(1536), metadata JSONB, created_at)
  - Indices: IVFFLAT or HNSW on embedding columns for similarity search
- **Tests/Validation:**
  - Alembic migration applies, pgvector extension active
  - `pytest tests/unit/test_embeddings.py::test_similarity_search_executes` (mock query)
- **Acceptance Criteria:** Vector tables created, similarity indices in place, queries fast (<200ms)

### 1.7: Alembic migration scaffold + repeatability test
- **Files/Modules:** `infra/migrations/env.py`, `infra/migrations/script.py.mako`, `infra/alembic.ini`, `pytest tests/integration/test_migrations.py`
- **Description:** Migrations upgrade/downgrade cleanly, database state consistent after cycle.
- **Tests/Validation:** `pytest tests/integration/test_migrations.py::test_upgrade_downgrade_cycle_idempotent` passes (upgrade → downgrade → upgrade → compare schema hashes)
- **Acceptance Criteria:** Upgrade/downgrade cycle leaves schema identical, no data loss

---

## **SPRINT 2: Resilience Framework ## **SPRINT 2: Resilience Framework & Error Handling** Error Handling**
**Sprint Goal:** All external API calls have retry logic, circuit breakers, idempotency tracking; graceful degradation.

**Demo Steps:**
```bash
python -c "from src.services.resilience import ResilienceManager; r = ResilienceManager(); print('Retry policy:', r.DEFAULT_RETRY_POLICY)"
pytest tests/unit/test_resilience.py -v
```

**Tickets:**

### 2.1: Retry logic with exponential backoff (tenacity library)
- **Files/Modules:** `src/services/resilience.py`, `src/decorators.py`
- **Description:** Configurable retry decorator for transient failures (network, rate limits).
- **Config:**
  - Max retries: 3
  - Initial delay: 100ms
  - Backoff multiplier: 2x
  - Max delay: 10s
  - Jitter: ±10%
- **Tests/Validation:**
  - `pytest tests/unit/test_resilience.py::test_retry_on_transient_failure` (mock API that fails twice, succeeds third time)
  - `pytest tests/unit/test_resilience.py::test_exponential_backoff_timing` (verify timing)
- **Acceptance Criteria:** Retries work, backoff timing correct, non-transient errors raised immediately

### 2.2: Circuit breaker (for cascading failures)
- **Files/Modules:** `src/services/resilience.py` (add circuit breaker)
- **Description:** Circuit breaker pattern to avoid hammering failing services.
- **States:** CLOSED (normal) → OPEN (fail fast) → HALF_OPEN (probe) → CLOSED
- **Thresholds:** Open after 5 failures in 60s window; probe after 30s
- **Tests/Validation:** `pytest tests/unit/test_resilience.py::test_circuit_breaker_opens_on_failures`
- **Acceptance Criteria:** Breaker prevents cascading failures, transitions work, resets after recovery

### 2.3: Idempotency tracking (prevent duplicate API calls)
- **Files/Modules:** `src/services/idempotency.py`, `infra/migrations/versions/006_idempotency_keys.py`
- **Table:** `idempotency_keys` (id, key UNIQUE, operation, status, result_data JSONB, created_at, expires_at)
- **Description:** Clients provide idempotency key; server caches result for 24h.
- **Tests/Validation:** `pytest tests/unit/test_idempotency.py::test_duplicate_requests_return_same_result`
- **Acceptance Criteria:** Idempotency keys enforced, results cached, replay returns same response

### 2.4: Dead letter queue for failed async tasks (Celery)
- **Files/Modules:** `src/workers/dead_letter.py`, `src/models/dlq.py`
- **Table:** `dead_letter_queue` (id, task_name, task_id, args, kwargs, error_message, traceback, created_at, retryable)
- **Description:** Failed Celery tasks are logged to DLQ; retryable ones are periodically re-queued.
- **Tests/Validation:** `pytest tests/integration/test_dlq.py::test_failed_task_logged_to_dlq`
- **Acceptance Criteria:** Failed tasks captured, retryable tasks eventually succeed, non-retryable ones flagged

---

## **SPRINT 3: OAuth2, Secrets Management ## **SPRINT 3: OAuth2, Secrets Management & Security** Security**
**Sprint Goal:** Secure credential handling for Gmail OAuth2, HubSpot API key, Google Drive API; no secrets in logs.

**Demo Steps:**
```bash
# Set env vars or use Secret Manager
export HUBSPOT_API_KEY="***"
python -m src.cli.test-hubspot-auth
# Output: "HubSpot auth successful"
```

**Tickets:**

### 3.1: OAuth2 flow for Gmail (user Sent folder access)
- **Files/Modules:** `src/connectors/oauth/__init__.py`, `src/connectors/oauth/gmail_oauth.py`, `src/api/auth.py`
- **Description:** OAuth2 authorization code flow for Gmail API (read Sent folder for voice learning).
- **Endpoints:**
  - `GET /auth/gmail/authorize` → redirects to Google consent screen
  - `GET /auth/gmail/callback` → handles redirect, stores refresh token
- **Storage:** Refresh token in Secret Manager or encrypted DB; access token cached in memory (TTL: 1 hour)
- **Tests/Validation:**
  - `pytest tests/unit/test_gmail_oauth.py::test_authorization_url_is_valid`
  - Mock Google OAuth endpoints
- **Acceptance Criteria:** OAuth flow works, tokens are stored securely, expiry handled

### 3.2: Service account auth for Gmail API (read threads)
- **Files/Modules:** `src/connectors/gmail/service_account.py`, `src/config.py` (add GMAIL_SERVICE_ACCOUNT_KEY env var)
- **Description:** Service account credentials for read-only thread access (no OAuth2 needed).
- **Tests/Validation:** `pytest tests/unit/test_gmail_service_account.py::test_authenticates_successfully` (with fixture key)
- **Acceptance Criteria:** Service account auth works, no user interaction needed

### 3.3: Secret Manager integration (GCP Secret Manager for production)
- **Files/Modules:** `src/services/secrets.py`, `src/config.py` (enhance)
- **Description:** Load secrets from GCP Secret Manager on startup; cache for 1 hour.
- **Secrets:**
  - HUBSPOT_API_KEY
  - GMAIL_SERVICE_ACCOUNT_KEY
  - OPENAI_API_KEY
  - Database password
  - Redis password (if applicable)
- **Fallback:** Env vars for local dev
- **Tests/Validation:** `pytest tests/unit/test_secrets.py::test_loads_from_secret_manager` (mock API)
- **Acceptance Criteria:** Secrets loaded securely, no plaintext in logs, fallback works

### 3.4: PII redaction in logs & error messages
- **Files/Modules:** `src/services/pii_redactor.py`, `src/logger.py` (filter logs)
- **Description:** Automatically redact emails, names, amounts, API keys from logs.
- **Tests/Validation:**
  - `pytest tests/unit/test_pii_redactor.py::test_redacts_email_addresses`
  - `pytest tests/unit/test_pii_redactor.py::test_redacts_api_keys`
- **Acceptance Criteria:** PII redacted, patterns are accurate, no false positives

### 3.5: Rate limiting on auth endpoints (prevent brute force)
- **Files/Modules:** `src/middleware.py` (add rate limiter)
- **Description:** Rate limit OAuth2 and API endpoints to prevent abuse.
- **Limits:**
  - Auth endpoints: 5 requests/minute per IP
  - API endpoints: 100 requests/minute per API key
- **Tests/Validation:** `pytest tests/integration/test_rate_limiting.py::test_auth_endpoint_rate_limited`
- **Acceptance Criteria:** Rate limits enforced, 429 responses returned

---

## **SPRINT 4: Feature Flags ## **SPRINT 4: Feature Flags & Mode Management** Mode Management**
**Sprint Goal:** Feature flags control rollout; MODE can switch between DRAFT_ONLY and SEND_ALLOWED; kill switch works instantly.

**Demo Steps:**
```bash
curl http://localhost:8000/api/config/mode
# {"mode": "DRAFT_ONLY", "send_allowed": false, "kill_switch": false}

curl -X POST http://localhost:8000/api/admin/set-mode \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"mode": "SEND_ALLOWED"}'
```

**Tickets:**

### 4.1: Mode enum + runtime config (DRAFT_ONLY vs SEND_ALLOWED)
- **Files/Modules:** `src/models/config.py`, `src/config.py`
- **Description:** Define system mode; expose via API; default to DRAFT_ONLY.
- **Tests/Validation:** `pytest tests/unit/test_config.py::test_mode_defaults_to_draft_only`
- **Acceptance Criteria:** Mode loadable from env, queryable via API, defaults correct

### 4.2: Kill switch (atomic, persisted in Redis)
- **Files/Modules:** `src/services/kill_switch.py`, `src/models/config.py`
- **Description:** Instant disable lever; all sends blocked when engaged.
- **Storage:** Redis key `killswitch:enabled` (single source of truth)
- **Tests/Validation:** `pytest tests/unit/test_kill_switch.py::test_toggle_is_atomic`
- **Acceptance Criteria:** Atomic toggle, Redis-backed, instant effect

### 4.3: Feature flag system (gradual rollout)
- **Files/Modules:** `src/services/feature_flags.py`, `infra/migrations/versions/007_feature_flags_schema.py`
- **Table:** `feature_flags` (id, name, enabled, rollout_percent, metadata JSONB, updated_at)
- **Flags:**
  - STORY_PITCH_ENABLED (default: false)
  - AUTO_SEND_FOLLOWUP (default: false)
  - LONG_MEMORY_ENABLED (default: true)
- **Methods:** `FeatureFlags.is_enabled(flag_name: str, user_id: str = None) -> bool` (deterministic by user)
- **Tests/Validation:** `pytest tests/unit/test_feature_flags.py::test_rollout_percent_deterministic`
- **Acceptance Criteria:** Flags deterministic, rollout % respected, admin can toggle

### 4.4: Admin API for operational controls
- **Files/Modules:** `src/api/admin.py` (FastAPI router), `src/auth.py` (admin check)
- **Endpoints:**
  - `GET /api/admin/config` (current mode, flags, kill switch status)
  - `POST /api/admin/set-mode` → {mode} (admin only, audit logged)
  - `POST /api/admin/kill-switch` → {enabled} (admin only, audit logged)
  - `POST /api/admin/set-feature-flag` → {flag_name, enabled, rollout_percent}
- **Auth:** Bearer token with admin role (from config); every change audit-logged
- **Tests/Validation:** `pytest tests/integration/test_admin_api.py::test_non_admin_rejected`
- **Acceptance Criteria:** Endpoints work, auth enforced, changes are immediate

---

## **SPRINT 5: Guardrails ## **SPRINT 5: Guardrails & Allowlists** Allowlists**
**Sprint Goal:** Define who we can contact; guardrails checked before any outreach.

**Demo Steps:**
```bash
curl http://localhost:8000/api/guardrails/check-contact?contact_id=123
# {"allowed": true, "reason": "company_stage matches GROWTH"}

curl http://localhost:8000/api/admin/guardrails
# Lists active rules
```

**Tickets:**

### 5.1: Guardrail rules schema (company stage, industry, employee count)
- **Files/Modules:** `src/models/guardrails.py`, `infra/migrations/versions/008_guardrails_schema.py`
- **Table:** `guardrail_rules` (id, name, rule_type, rule_value JSONB, active, created_at, updated_at)
- **Rule Types:**
  - ALLOWED_COMPANY_STAGE: [SEED, SERIES_A, SERIES_B, GROWTH, PUBLIC]
  - ALLOWED_INDUSTRY: [TECH, FINANCE, HEALTHCARE, ENTERPRISE, ...]
  - EMPLOYEE_RANGE: {min, max}
  - EXCLUDED_COMPANY_IDS: [list of hubspot_company_ids]
- **Tests/Validation:** Schema validation
- **Acceptance Criteria:** Rules storable, queryable, types enforced

### 5.2: GuardrailsChecker service (evaluate contact against rules)
- **Files/Modules:** `src/services/guardrails_checker.py`
- **Methods:** `GuardrailsChecker.is_allowed(contact: Contact) -> (bool, reason)` (allowed, why_not)
- **Evaluation:** Check ALL active rules; contact allowed only if matches ALL
- **Tests/Validation:**
  - `pytest tests/unit/test_guardrails.py::test_blocks_disallowed_industry`
  - `pytest tests/unit/test_guardrails.py::test_allows_matching_employee_range`
  - Golden file: 20 sample contacts → expected allow/block
- **Acceptance Criteria:** All rules enforced, reasons clear, no false positives

### 5.3: Suppression list (opt-outs, bounced, complaints)
- **Files/Modules:** `src/models/suppression.py`, `infra/migrations/versions/009_suppression_schema.py`
- **Table:** `suppression_list` (id, email, company_id, reason (OPT_OUT|BOUNCED|COMPLAINT|MANUAL), added_at, expires_at, added_by)
- **Methods:** `is_suppressed(email: str) -> (bool, reason)`
- **Cleanup:** Auto-expire entries after 1 year (unless explicitly renewed)
- **Tests/Validation:** `pytest tests/unit/test_suppression.py::test_suppresses_opted_out_contacts`
- **Acceptance Criteria:** Suppression check works, expiry handled

### 5.4: Admin API for guardrails + suppression management
- **Files/Modules:** `src/api/admin.py` (add endpoints)
- **Endpoints:**
  - `GET /api/admin/guardrails` → list active rules
  - `POST /api/admin/guardrails` → create rule (e.g., {rule_type: ALLOWED_INDUSTRY, rule_value: [TECH, FINANCE]})
  - `DELETE /api/admin/guardrails/{rule_id}` → deactivate rule
  - `POST /api/admin/suppression` → {email, reason}
  - `GET /api/admin/suppression?email=user@company.com` → check suppression status
- **Tests/Validation:** `pytest tests/integration/test_admin_api.py::test_admin_can_manage_guardrails`
- **Acceptance Criteria:** CRUD works, changes apply immediately, audit logged

---

## **PHASE 2: CONNECTORS & DATA RETRIEVAL (Sprints 6–10)**

---

## **SPRINT 6: Gmail Connector & Thread Indexing**
**Sprint Goal:** Can fetch Gmail threads, index messages into DB, retrieve thread context.

**Demo Steps:**
```bash
python -m src.cli.gmail --sync-thread <thread_id> --verbose
# Verify:
psql -c "SELECT COUNT(*) FROM messages WHERE gmail_thread_id='<id>';"
```

**Tickets:**

### 6.1: Gmail API client (service account auth)
- **Files/Modules:** `src/connectors/gmail/__init__.py`, `src/connectors/gmail/client.py`
- **Description:** Authenticated Gmail API client; read threads, list messages.
- **Tests/Validation:** `pytest tests/unit/test_gmail_client.py::test_service_account_auth` (mock Google API)
- **Acceptance Criteria:** Client instantiates, auth token obtained, API calls work

### 6.2: Fetch & parse Gmail threads (headers, labels, body)
- **Files/Modules:** `src/connectors/gmail/thread_fetcher.py`
- **Methods:**
  - `fetch_thread(thread_id: str) -> ThreadPayload` (messages, metadata)
  - `parse_email_headers(message) -> EmailHeader` (from, to, subject, date)
- **Tests/Validation:**
  - `pytest tests/unit/test_thread_fetcher.py::test_parses_headers_correctly` (fixture emails)
  - Sender/recipient extracted correctly; dates parsed in UTC
- **Acceptance Criteria:** Can fetch & parse arbitrary threads, no data loss

### 6.3: Upsert messages into DB (idempotent by gmail_message_id)
- **Files/Modules:** `src/connectors/gmail/message_syncer.py`
- **Methods:** `sync_messages_from_thread(thread_id: str) -> int` (count of new messages)
- **Deduplication:** Use gmail_message_id as natural key; skip if exists
- **Tests/Validation:** `pytest tests/integration/test_message_sync.py::test_idempotent_message_sync` (sync same thread twice → count is 0)
- **Acceptance Criteria:** Idempotent, no duplicates, all fields populated

### 6.4: Generate embeddings for message bodies (OpenAI API, batch)
- **Files/Modules:** `src/services/embeddings.py`
- **Methods:**
  - `embed_text(text: str) -> List[float]` (1536-dim)
  - `batch_embed_messages(message_ids: List[int]) -> int` (count embedded; batches of 10)
- **Model:** OpenAI text-embedding-3-small (1536 dims)
- **Tests/Validation:**
  - `pytest tests/unit/test_embeddings.py::test_embedding_dimension_is_1536` (mock OpenAI)
  - `pytest tests/unit/test_embeddings.py::test_batching_is_efficient` (10 msgs per batch)
- **Acceptance Criteria:** Dimension correct, batching works, no duplicates

### 6.5: ThreadReaderAgent (extract thread context: summary, last sender, key topics, sentiment)
- **Files/Modules:** `src/agents/thread_reader.py`
- **Methods:** `ThreadReaderAgent.read_thread(thread_id: str) -> ThreadContext`
- **Output:**
  ```python
  ThreadContext(
    summary: str (1–2 sentences),
    last_sender: str (email),
    key_topics: List[str] (3–5 topics),
    sentiment: str (positive|neutral|negative),
    last_message_at: datetime
  )
  ```
- **Tests/Validation:**
  - `pytest tests/unit/test_thread_reader.py::test_extracts_key_topics` (fixture threads vs. golden JSON)
  - Golden file fixtures for before/after outputs
- **Acceptance Criteria:** Output matches golden file within token-distance tolerance

### 6.6: CLI for manual thread sync
- **Files/Modules:** `src/cli/gmail.py`
- **Command:** `python -m src.cli.gmail --sync-thread <id> --verbose`
- **Output:** Job ID, message count, embedding status
- **Tests/Validation:** `pytest tests/integration/test_cli_gmail.py::test_sync_command_creates_messages`
- **Acceptance Criteria:** CLI runs, messages appear in DB

---

## **SPRINT 7: HubSpot Connector & Entity Resolution**
**Sprint Goal:** Can read/write to HubSpot, resolve email to contact/company, listen for form submissions.

**Demo Steps:**
```bash
python -m src.cli.hubspot --query-email "user@company.com" --verbose
# Output: Contact ID, Company, Deal stage, etc.
```

**Tickets:**

### 7.1: HubSpot API client (read contacts, companies, deals, forms)
- **Files/Modules:** `src/connectors/hubspot/__init__.py`, `src/connectors/hubspot/client.py`
- **Methods:**
  - `get_contact_by_email(email: str) -> HubSpotContact | None`
  - `get_company_by_domain(domain: str) -> HubSpotCompany | None`
  - `get_deal(deal_id: int) -> HubSpotDeal`
  - `list_form_submissions(form_id: str, limit=100) -> List[Submission]`
- **Tests/Validation:** `pytest tests/unit/test_hubspot_client.py` with fixture responses
- **Acceptance Criteria:** API calls work, pagination handled, null-safe

### 7.2: Entity sync into local DB (companies, contacts, deals)
- **Files/Modules:** `src/connectors/hubspot/entity_syncer.py`
- **Methods:**
  - `sync_contact_by_email(email: str) -> int | None` (local contact ID or None)
  - `sync_company_by_domain(domain: str) -> int | None`
- **Deduplication:** Use HubSpot IDs as keys; upsert custom_properties
- **Tests/Validation:** `pytest tests/integration/test_hubspot_sync.py::test_sync_contact_idempotent`
- **Acceptance Criteria:** Idempotent, custom properties captured

### 7.3: IdentityResolverAgent (email/domain → HubSpot contact + company)
- **Files/Modules:** `src/agents/identity_resolver.py`
- **Methods:** `IdentityResolverAgent.resolve(email: str) -> ResolvedIdentity`
- **Output:**
  ```python
  ResolvedIdentity(
    contact_id: int | None,
    company_id: int | None,
    found_in_hubspot: bool,
    email: str,
    company_name: str | None,
    industry: str | None
  )
  ```
- **Logic:** Lookup by email → contact; extract domain → company lookup
- **Tests/Validation:**
  - `pytest tests/unit/test_identity_resolver.py::test_resolves_known_email`
  - `pytest tests/unit/test_identity_resolver.py::test_returns_none_for_unknown_domain`
  - Golden file: 10 emails → expected resolutions
- **Acceptance Criteria:** Resolver works, fallbacks correct

### 7.4: Form submission listener (poll HubSpot form for new submissions)
- **Files/Modules:** `src/connectors/hubspot/form_poller.py`, `src/models/form_submission.py`
- **Methods:** `FormPoller.poll(form_id: str) -> List[FormSubmission]` (new since last poll)
- **Polling:** Store last_submission_time in DB; only fetch newer
- **Tests/Validation:** `pytest tests/integration/test_form_poller.py::test_detects_new_submission`
- **Acceptance Criteria:** Detects new submissions, no duplicates

### 7.5: Write tasks + notes to HubSpot (safe property updates)
- **Files/Modules:** `src/connectors/hubspot/writer.py`
- **Methods:**
  - `create_task(contact_id: int, title: str, due_date: date) -> int` (HubSpot task_id)
  - `create_note(contact_id: int, body: str) -> int` (HubSpot note_id)
  - `update_contact_property(contact_id: int, property_name: str, value: any) -> bool`
- **Safety:** Only write whitelisted properties; log all updates
- **Tests/Validation:** `pytest tests/unit/test_hubspot_writer.py` (mock API calls)
- **Acceptance Criteria:** Task/note created with correct fields

### 7.6: CLI for HubSpot entity lookup
- **Files/Modules:** `src/cli/hubspot.py`
- **Commands:**
  - `python -m src.cli.hubspot --query-email user@company.com`
  - `python -m src.cli.hubspot --query-domain company.com`
- **Output:** Entity info in table format
- **Tests/Validation:** `pytest tests/integration/test_cli_hubspot.py`
- **Acceptance Criteria:** CLI returns correct info

---

## **SPRINT 8: Google Drive Indexing (Allowlist + Asset Retrieval)**
**Sprint Goal:** Index Drive docs within allowlist, retrieve for drafting context.

**Demo Steps:**
```bash
python -m src.cli.drive --index-folder --folder-id "0ACIUuJIAAt4IUk9PVA"
# Wait for indexing...
python -c "from src.agents.asset_hunter import AssetHunterAgent; a = AssetHunterAgent(); print(a.find_assets('proposal', asset_type='proposal'))"
```

**Tickets:**

### 8.1: Drive API client + allowlist enforcement
- **Files/Modules:** `src/connectors/drive/__init__.py`, `src/connectors/drive/client.py`
- **Methods:** `list_files_in_folder(folder_id: str, recursive=True) -> List[DriveFile]`
- **Allowlist:**
  - Root: `0ACIUuJIAAt4IUk9PVA`
  - Include subfolders by prefix: ["CHAINge Proposals", "CP Client Reports", "CP Proposals", "Manifest 2026"]
  - Exclude folders: ["CP Closed*"]
  - Plus: `CHARLIE_PESTI_FOLDER_ID` (all descendants)
- **Tests/Validation:**
  - `pytest tests/unit/test_drive_client.py::test_allowlist_filter_blocks_excluded` (fixture folder structure)
  - Verify "CP Closed" is excluded
- **Acceptance Criteria:** Only allowlist folders indexed, exclusions respected

### 8.2: Download & extract text from Drive docs (Google Docs → text, PDF → text)
- **Files/Modules:** `src/connectors/drive/document_extractor.py`
- **Methods:** `extract_text_from_doc(file_id: str, mime_type: str) -> str`
- **Formats:**
  - Google Docs: export as plaintext
  - PDFs: OCR or text extraction (e.g., pdfplumber)
  - Sheets: export as CSV, parse headers + first few rows
- **Tests/Validation:**
  - `pytest tests/integration/test_document_extractor.py::test_extracts_text_from_google_doc` (mock download)
  - Verify no corruption
- **Acceptance Criteria:** Multiple formats handled, text quality high

### 8.3: Chunk & embed Drive documents (store in document_embeddings)
- **Files/Modules:** `src/services/document_chunker.py`, use existing `src/services/embeddings.py`
- **Methods:**
  - `chunk_document(text: str, chunk_size=1000, overlap=200) -> List[Chunk]`
  - `embed_and_store_chunks(file_id: str, chunks: List[Chunk])`
- **Chunking:** Preserve paragraph boundaries, overlap for context
- **Tests/Validation:**
  - `pytest tests/unit/test_document_chunker.py::test_chunks_respect_overlap`
  - Verify chunks overlap correctly
- **Acceptance Criteria:** Chunks stored with metadata, embeddings in pgvector

### 8.4: Drive index worker (Celery task, idempotent)
- **Files/Modules:** `src/workers/drive_indexer.py`
- **Task:** `index_drive_folder(folder_id: str) -> dict` (stats: files_indexed, chunks_created, embeddings_generated)
- **Idempotency:** Skip files already indexed; re-embed if Drive file updated
- **Tests/Validation:** `pytest tests/integration/test_drive_indexer.py::test_reindex_updates_only_changed_files`
- **Acceptance Criteria:** Idempotent, stats accurate

### 8.5: AssetHunterAgent (semantic search for proposals/reports)
- **Files/Modules:** `src/agents/asset_hunter.py`
- **Methods:** `AssetHunterAgent.find_assets(query: str, asset_type: str = None, limit: int = 5) -> List[Asset]`
- **Output:**
  ```python
  Asset(
    file_id: str,
    filename: str,
    chunk_preview: str (first 200 chars of matched chunk),
    relevance_score: float (0–1),
    asset_type: str (proposal|report|case_study)
  )
  ```
- **Logic:** Embed query, search pgvector, rank by similarity
- **Tests/Validation:**
  - `pytest tests/unit/test_asset_hunter.py::test_finds_relevant_proposals` (golden file: query → expected results)
- **Acceptance Criteria:** Top-K results are relevant, scores meaningful

### 8.6: CLI for Drive indexing & search
- **Files/Modules:** `src/cli/drive.py`
- **Commands:**
  - `python -m src.cli.drive --index-folder --folder-id <id> --verbose`
  - `python -m src.cli.drive --search "customer X proposal" --limit 10`
- **Output:** Index progress, search results with preview
- **Tests/Validation:** `pytest tests/integration/test_cli_drive.py`
- **Acceptance Criteria:** CLI works, shows progress

---

## **SPRINT 9: Google Calendar & Meeting Slot Proposal**
**Sprint Goal:** Query calendar freebusy, propose 2–3 near-term meeting slots.

**Demo Steps:**
```bash
python -c "from src.agents.meeting_slot import MeetingSlotAgent; m = MeetingSlotAgent(); slots = m.propose_slots('user@company.com'); print(slots)"
```

**Tickets:**

### 9.1: Calendar API client + freebusy query
- **Files/Modules:** `src/connectors/calendar/__init__.py`, `src/connectors/calendar/client.py`
- **Methods:** `get_freebusy(email: str, start: datetime, end: datetime) -> List[TimeSlot]`
- **Output:** List of free 30-min blocks within date range
- **Tests/Validation:** `pytest tests/unit/test_calendar_client.py` (mocked responses)
- **Acceptance Criteria:** Returns free slots correctly, handles no-availability cases

### 9.2: Business day logic (9am–5pm UTC, skip weekends/holidays)
- **Files/Modules:** `src/utils/calendar_utils.py`
- **Methods:**
  - `next_business_days(num_days: int = 3) -> List[date]` (skip weekends)
  - `business_hours_in_day(date: date) -> List[TimeSlot]` (9am–5pm UTC)
- **Holidays:** Load from config or hardcoded list (US federal holidays)
- **Tests/Validation:**
  - `pytest tests/unit/test_calendar_utils.py::test_next_business_days_skips_weekends`
  - Verify holidays respected
- **Acceptance Criteria:** Business days computed correctly

### 9.3: MeetingSlotAgent (propose 2–3 slots, rank by preference)
- **Files/Modules:** `src/agents/meeting_slot.py`
- **Methods:** `MeetingSlotAgent.propose_slots(email: str, urgency: str = 'normal') -> List[ProposedSlot]`
- **Output:**
  ```python
  ProposedSlot(
    start: datetime,
    end: datetime (30-min from start),
    rank: int (1–3),
    day_of_week: str,
    reason: str (e.g., "Wednesday morning, highest availability")
  )
  ```
- **Ranking:** Prefer earlier in week, earlier in day
- **Tests/Validation:**
  - `pytest tests/unit/test_meeting_slot.py::test_proposes_three_slots`
  - Verify slots are non-overlapping, all 30-min, all in next 3 business days, all in 9am–5pm
- **Acceptance Criteria:** Exactly 3 slots returned, all valid, ranked correctly

---

## **SPRINT 10: Long Memory & Voice Learning Pipeline**
**Sprint Goal:** Extract historical email patterns, build voice profile (phrasing, tone, CTAs), enable LongMemoryAgent.

**Demo Steps:**
```bash
python -m src.cli.voice --learn-from-sent-folder --limit 100 --output-profile voice_profile.json
# Output: Profile with phrasing patterns, tone, CTA templates, forbidden words
cat voice_profile.json | jq '.phrasing_patterns | .[0:3]'

# Test retrieval:
python -c "from src.agents.long_memory import LongMemoryAgent; lm = LongMemoryAgent(); print(lm.retrieve_context('customer pain point'))"
```

**Tickets:**

### 10.1: LongMemoryAgent (retrieve similar messages by semantic similarity)
- **Files/Modules:** `src/agents/long_memory.py`
- **Methods:** `LongMemoryAgent.retrieve_context(query: str, top_k: int = 5) -> List[MemoryContext]`
- **Output:**
  ```python
  MemoryContext(
    message_preview: str (first 150 chars),
    sender: str,
    timestamp: datetime,
    relevance_score: float,
    thread_id: str
  )
  ```
- **Logic:** Embed query, search pgvector, return top-K
- **Tests/Validation:**
  - `pytest tests/unit/test_long_memory.py::test_retrieves_similar_messages` (golden file)
  - Verify recall/precision metrics
- **Acceptance Criteria:** Retrieves semantically similar messages, scores meaningful

### 10.2: Gmail Sent folder connector (fetch user's sent emails)
- **Files/Modules:** `src/connectors/gmail/sent_folder_fetcher.py`
- **Methods:** `fetch_sent_emails(limit: int = 500, after_date: date = None) -> List[EmailMessage]`
- **Auth:** OAuth2 (requires user consent to access Sent folder)
- **Tests/Validation:** `pytest tests/unit/test_sent_folder_fetcher.py` (mocked API)
- **Acceptance Criteria:** Fetches Sent folder, respects date filters

### 10.3: Voice Learning pipeline (extract patterns from corpus)
- **Files/Modules:** `src/services/voice_learner.py`
- **Methods:** `VoiceLearner.learn_from_emails(emails: List[EmailMessage]) -> VoiceProfile`
- **Analysis:**
  - **Phrasing patterns:** Common phrases via n-gram extraction (bigrams, trigrams with freq > 2)
  - **Tone:** Classify as formal|conversational|urgent (keyword-based or ML classifier)
  - **Common CTAs:** Extract calls-to-action (regex: "Let's talk", "I'd love to", "Happy to", etc.)
  - **Do/Don't rules:** Extract patterns from email structure (e.g., "always signs with first name", "never uses exclamation marks")
  - **Forbidden words:** Identify words never used (for quality gate)
  - **Average length:** Median word count per email
  - **Signature style:** Extract signature block pattern
- **Tests/Validation:**
  - `pytest tests/unit/test_voice_learner.py::test_extracts_phrasing_patterns` (golden file: 10 emails → expected patterns)
  - Verify pattern accuracy (f1-score > 0.8 on held-out test set)
- **Acceptance Criteria:** Patterns extracted, coverage > 90% of sent emails

### 10.4: PII redaction in voice learning (privacy safeguards)
- **Files/Modules:** `src/services/pii_redactor.py` (enhance)
- **Redaction:**
  - Email addresses → `[EMAIL]`
  - Company names → `[COMPANY]` (maintain signal: "company X" or "customer Y")
  - Amounts ($1M, $50k) → `[AMOUNT]`
  - Names (John, Jane, etc.) → `[NAME]` (preserve signal: "John", "Jane" become generic)
  - Domains → `[DOMAIN]`
- **Methods:** `redact_pii(text: str) -> str`
- **Tests/Validation:**
  - `pytest tests/unit/test_pii_redactor.py::test_redacts_emails_and_companies` (golden file)
  - Verify learned patterns contain no client-specific info
- **Acceptance Criteria:** All PII redacted, patterns remain useful

### 10.5: VoiceProfile schema + persistence (DB + JSON export)
- **Files/Modules:** `src/models/voice.py`, `infra/migrations/versions/010_voice_schema.py`
- **Table:** `voice_profiles` (id, name, phrasing_patterns JSONB, tone, common_ctas JSONB, do_dont_rules JSONB, forbidden_words LIST, avg_words INT, signature_style TEXT, learned_at, version)
- **Structure:**
  ```python
  VoiceProfile(
    name: str (e.g., "sales_voice_v1"),
    phrasing_patterns: List[Dict] ([{phrase: "Let's talk", frequency: 12, percentile: 0.85}, ...]),
    tone: str,
    common_ctas: List[str] (["Let's talk", "Happy to help", ...]),
    do_dont_rules: List[Dict] ([{type: "always", rule: "sign with first name"}, ...]),
    forbidden_words: List[str] (["perhaps", "unfortunately", ...]),
    avg_words: int,
    signature_style: str,
    learned_at: datetime,
    version: int
  )
  ```
- **Export:** Save to JSON file at `docs/voice_profile.json` for version control
- **Tests/Validation:** `pytest tests/unit/test_voice_profile.py::test_profile_schema_validates`
- **Acceptance Criteria:** Profile stored in DB, exported to JSON, schema valid

### 10.6: CLI for voice learning + validation
- **Files/Modules:** `src/cli/voice.py`
- **Commands:**
  - `python -m src.cli.voice --learn-from-sent-folder --limit 100 --output-profile voice_profile.json`
  - `python -m src.cli.voice --validate-profile docs/voice_profile.json`
  - `python -m src.cli.voice --stats` (show current profile stats)
- **Output:** Profile generated, validation report (PII check, pattern confidence)
- **Tests/Validation:** `pytest tests/integration/test_cli_voice.py`
- **Acceptance Criteria:** CLI works, profile files created, validation passes

### 10.7: Offline eval harness for voice profile (similarity, compliance)
- **Files/Modules:** `tests/eval/voice_eval.py`
- **Metrics:**
  - % of generated CTAs matching common_ctas (target: >80%)
  - % of forbidden_words NOT in generated draft (target: 100%)
  - Tone consistency (manual review: 3 generated drafts vs. profile tone — flag if inconsistent)
  - PII leakage: 0 (automated check)
- **Test:** `pytest tests/eval/voice_eval.py` runs offline with golden files (5–10 sample drafts)
- **Tests/Validation:** Eval produces metrics, passes thresholds
- **Acceptance Criteria:** All metrics pass, eval runs in <5s

---

## **PHASE 3: USE CASES & ORCHESTRATION (Sprints 11–13)**

---

## **SPRINT 11: Use Case #1 — Lead Followup (Form → Draft) — Part A**
**Sprint Goal:** Agents are wired; form submission triggers planning + drafting pipeline. Drafts created, not sent.

**Demo Steps:**
```bash
python -m src.cli.test-form-submission --contact-email "newlead@company.com" --company-name "Acme Corp" --verbose
# Output: Job ID, plan, draft preview
curl http://localhost:8000/api/drafts?status=pending | jq '.[0]'
# {draft_id, subject, body_preview, contact_id, company_id, status: "pending"}
```

**Tickets:**

### 11.1: TriggerAgent (form submission → job creation)
- **Files/Modules:** `src/agents/trigger.py`
- **Methods:** `TriggerAgent.on_form_submission(submission: FormSubmission) -> FollowupJob`
- **Output:**
  ```python
  FollowupJob(
    id: int,
    contact_id: int,
    company_id: int,
    job_type: str (FOLLOWUP | NURTURE),
    context: Dict (subject, form_data, prior_touches),
    priority: str (URGENT | NORMAL | LOW),
    created_at: datetime
  )
  ```
- **Logic:** Extract contact + company from submission; enrich with context
- **Tests/Validation:** `pytest tests/unit/test_trigger_agent.py::test_creates_followup_job_on_form`
- **Acceptance Criteria:** Job created with all fields, context enriched

### 11.2: NextStepPlannerAgent (plan cadence, risk gating, tone)
- **Files/Modules:** `src/agents/next_step_planner.py`
- **Methods:** `NextStepPlannerAgent.plan(job: FollowupJob) -> NextStepPlan`
- **Output:**
  ```python
  NextStepPlan(
    action: str (SEND_FOLLOWUP | PROPOSE_CALL | SEND_ASSET | NO_ACTION),
    urgency: str (URGENT | NORMAL | LOW),
    risk_score: float (0–100),
    tone: str (formal|conversational|urgent),
    reason: str (e.g., "High-fit company, recent form submission"),
    suggested_cta: str (e.g., "propose_call"),
    delay_hours: int (min delay before send)
  )
  ```
- **Logic:**
  - Risk gating: Check guardrails + suppression → NO_ACTION if blocked
  - Priority: Form = URGENT; nurture = NORMAL
  - Tone: Formal for enterprise, conversational for startup
- **Tests/Validation:**
  - `pytest tests/unit/test_next_step_planner.py` with fixture jobs
  - Golden file: 10 jobs → expected plans
  - Risk scores calibrated (test high-risk, low-risk scenarios)
- **Acceptance Criteria:** Plans make business sense, risk scores realistic

### 11.3: DraftWriterAgent (compose draft in learned voice)
- **Files/Modules:** `src/agents/draft_writer.py`
- **Methods:**
  - `DraftWriterAgent.write_draft(job: FollowupJob, plan: NextStepPlan, voice_profile: VoiceProfile) -> Draft`
  - Internal: `_compose_subject()`, `_compose_body()`, `_validate_draft()`
- **Draft Output:**
  ```python
  Draft(
    subject: str,
    body: str,
    proposed_from: str (email),
    proposed_to: str (email),
    proposed_cc: List[str] | None,
    attachments: List[Dict] | None
  )
  ```
- **Constraints:**
  - Max 200 words (skimmable)
  - Exactly 1 CTA
  - No em-dashes (use hyphens)
  - No client-confidential info
  - Must use 2+ phrasing patterns from voice profile
  - Tone must match plan.tone
- **Logic:**
  - Retrieve context via LongMemoryAgent (similar past emails)
  - Get suggested assets via AssetHunterAgent
  - Retrieve meeting slots via MeetingSlotAgent
  - Compose draft using template (subject, body, CTA) + personalization
  - Validate against voice profile + guardrails
- **Tests/Validation:**
  - `pytest tests/unit/test_draft_writer.py::test_draft_follows_voice_profile` (word count, em-dash check, CTA count, PII check)
  - Golden file: 5 jobs → expected drafts (check subject, body, CTA)
  - Validation: draft must pass all checks
- **Acceptance Criteria:** Draft produced, all validation passes

### 11.4: Draft storage + DB schema update
- **Files/Modules:** `src/models/draft.py`, `infra/migrations/versions/011_draft_schema.py`
- **Table:** `drafts` (id, job_id FK, contact_id FK, company_id FK, subject, body, status (PENDING|SENT|REJECTED|EXPIRED), mode, created_at, sent_at, rejection_reason TEXT, metadata JSONB)
- **Fields:**
  - subject, body: draft text
  - status: current state
  - mode: which mode was active when created (for audit)
  - rejection_reason: if rejected by gate, why
- **Tests/Validation:** Schema validation, migration reversible
- **Acceptance Criteria:** Table created, indices on job_id + contact_id

### 11.5: Drafts API endpoint (list + preview)
- **Files/Modules:** `src/api/drafts.py` (FastAPI router)
- **Endpoints:**
  - `GET /api/drafts?status=PENDING&contact_id=123` → list drafts
  - `GET /api/drafts/{draft_id}` → full preview with parsed body + metadata
- **Response:**
  ```json
  {
    "draft_id": 1,
    "subject": "...",
    "body": "...",
    "contact_id": 123,
    "company_id": 456,
    "status": "PENDING",
    "created_at": "2026-01-23T...",
    "meeting_slots": [...],
    "suggested_assets": [...]
  }
  ```
- **Tests/Validation:** `pytest tests/integration/test_draft_api.py::test_list_pending_drafts`
- **Acceptance Criteria:** Endpoints work, paginated, response time < 500ms

### 11.6: CRMHygieneAgent (log draft creation to HubSpot)
- **Files/Modules:** `src/agents/crm_hygiene.py`
- **Methods:** `CRMHygieneAgent.log_draft_to_crm(draft: Draft) -> int` (HubSpot note_id)
- **Logging:**
  - Create HubSpot note with draft summary + preview (first 200 chars)
  - Create HubSpot task: "Follow up on form submission" due in 24h
  - Link to draft preview URL (if deployable)
- **Tests/Validation:** `pytest tests/unit/test_crm_hygiene.py` (mock HubSpot calls)
- **Acceptance Criteria:** Note + task created, correct fields

### 11.7: Orchestrator state machine (TriggerAgent → NextStepPlanner → DraftWriter → CRMHygiene)
- **Files/Modules:** `src/orchestration/followup_orchestrator.py`, `src/models/orchestration.py`
- **Methods:** `FollowupOrchestrator.execute(job: FollowupJob) -> Result`
- **State Transitions:**
  ```
  JOB_CREATED → [guardrails check] → PLAN_CREATED → DRAFT_CREATED → CRM_LOGGED → COMPLETED (or ERROR at any step)
  ```
- **Error Handling:**
  - Transient failures: retry with backoff (via resilience framework)
  - Non-retryable errors: mark job as FAILED, log reason
- **Tests/Validation:**
  - `pytest tests/integration/test_followup_orchestrator.py::test_full_followup_chain` (mock all agents)
  - State transitions verified
  - Error cases tested (guardrail block, API failure, etc.)
- **Acceptance Criteria:** State machine executes correctly, error handling works

### 11.8: Celery task for followup orchestration (async job)
- **Files/Modules:** `src/workers/followup_worker.py`
- **Task:** `followup_workflow(job_id: int) -> dict` (result: {draft_id, crm_note_id, status, error_reason?})
- **Execution:** Async Celery task; calls orchestrator; logs result to DB
- **Tests/Validation:** `pytest tests/integration/test_followup_worker.py` (mock Celery)
- **Acceptance Criteria:** Task executes async, result logged

### 11.9: CLI for test form submission (end-to-end smoke test)
- **Files/Modules:** `src/cli/test_form.py`
- **Command:** `python -m src.cli.test-form-submission --contact-email user@company.com --company-name "Acme" --verbose`
- **Output:** Job ID, plan, draft preview, HubSpot note URL, status
- **Tests/Validation:** `pytest tests/integration/test_cli_test_form.py`
- **Acceptance Criteria:** CLI runs end-to-end, outputs all steps

---

## **SPRINT 12: Use Case #1 — Lead Followup — Part B**
**Sprint Goal:** Quality gates, approval workflow, audit logging complete. Drafts can be blocked if risky.

**Demo Steps:**
```bash
# Trigger draft with PII (should be blocked):
python -m src.cli.test-risky-draft --pii-in-draft
# Check draft status:
curl http://localhost:8000/api/drafts/999 | jq '.status, .rejection_reason'
# Output: "REJECTED", "PII detected: email addresses in body"

# Check audit log:
curl http://localhost:8000/api/audit?draft_id=999 | jq '.'
```

**Tickets:**

### 12.1: QualityGateAgent (risk scoring + blocking)
- **Files/Modules:** `src/agents/quality_gate.py`
- **Methods:** `QualityGateAgent.evaluate(draft: Draft, contact: Contact) -> GateResult`
- **Output:**
  ```python
  GateResult(
    status: str (PASS | WARN | FAIL),
    risk_score: float (0–100),
    violations: List[Dict] ([{check: "pii_leak", severity: "high", message: "..."}, ...]),
    reason: str,
    send_allowed: bool,
    approval_required: bool
  )
  ```
- **Checks:**
  1. **PII Leak:** Scan draft for emails, company names, amounts → FAIL if found
  2. **Forbidden Words:** Check draft against voice profile forbidden list → WARN if found
  3. **CTA Clarity:** Exactly 1 CTA, clear, actionable → FAIL if not
  4. **Tone Consistency:** Compare draft tone to profile tone (simple keyword match) → WARN if misaligned
  5. **Suppression:** Is contact suppressed? → FAIL if yes
  6. **Guardrails:** Does contact pass company stage/industry/employee checks? → FAIL if not
  7. **Mode Check:** If MODE == DRAFT_ONLY → FAIL for send (allow drafting only)
  8. **Quota Check:** Has contact received email in last 7 days? → WARN if yes (but allow followup)
- **Risk Score:** Composite of violations (HIGH=50 pts, MEDIUM=20 pts, LOW=10 pts; max 100)
- **Tests/Validation:**
  - `pytest tests/unit/test_quality_gate.py::test_blocks_draft_with_pii` (fixture drafts: good, bad, risky)
  - Golden file: 10 drafts → expected gateresult
  - Risk scores are calibrated (test boundary cases)
- **Acceptance Criteria:** All checks implemented, scores calibrated, no false positives

### 12.2: Risk scoring function (multi-factor, tunable)
- **Files/Modules:** `src/services/risk_scorer.py`
- **Methods:** `risk_score = sum([weight * signal_value for weight, signal_value in factors])`
- **Factors:**
  - PII leak severity (high=50, medium=25, low=10)
  - Tone inconsistency (20 pts)
  - Forbidden word count (10 pts per word, capped at 40)
  - Contact unresponsive (prior email opened: no penalty; bounced: 30 pts)
  - Guardrail violation type (stage mismatch: 40 pts, industry: 30 pts)
- **Final Score:** min(100, total)
- **Tests/Validation:** `pytest tests/unit/test_risk_scorer.py::test_risk_score_aggregates_signals` (verify weighting)
- **Acceptance Criteria:** Scores are reproducible, weights tunable via config

### 12.3: Audit logging for draft lifecycle
- **Files/Modules:** `src/services/audit_logger.py`
- **Methods:**
  - `AuditLogger.log_action(action: str, actor: str, resource_id: int, status: str, reason: str, metadata: dict) -> int` (audit_id)
- **Log Entry Schema:**
  ```python
  {
    action: str (DRAFT_CREATED | DRAFT_REJECTED | DRAFT_APPROVED | DRAFT_SENT),
    actor: str (system | user_id),
    resource_type: str (DRAFT),
    resource_id: int,
    contact_id: int,
    company_id: int,
    status_before: str,
    status_after: str,
    reason: str,
    metadata: Dict (violations, risk_score, approver, etc.),
    timestamp: datetime
  }
  ```
- **Persistence:** Immutable; stored in draft_audit_log table
- **Tests/Validation:** `pytest tests/integration/test_audit_logger.py::test_logs_all_draft_lifecycle_events`
- **Acceptance Criteria:** All entries immutable, queryable, timestamps correct

### 12.4: Audit API endpoint (query logs, export)
- **Files/Modules:** `src/api/audit.py` (FastAPI router)
- **Endpoints:**
  - `GET /api/audit?contact_id=123&date_from=2026-01-01&date_to=2026-01-31` → list entries (paginated)
  - `GET /api/audit?company_id=456` → entries for company
  - `GET /api/audit/export?company_id=456` → CSV export
- **Response:**
  ```json
  {
    "entries": [...],
    "total": 42,
    "page": 1,
    "page_size": 10
  }
  ```
- **Tests/Validation:** `pytest tests/integration/test_audit_api.py` (pagination, filtering)
- **Acceptance Criteria:** Endpoints work, exports valid CSV

### 12.5: Draft rejection + reason display (API)
- **Files/Modules:** `src/api/drafts.py` (add endpoint)
- **Endpoint:** `GET /api/drafts/{draft_id}/rejection` → {reason, violations, suggestions}
- **Response:**
  ```json
  {
    "reason": "Draft contains PII",
    "violations": [
      {"check": "pii_leak", "message": "Email found: user@example.com", "severity": "high"}
    ],
    "suggestions": ["Remove email address", "Use placeholder instead"]
  }
  ```
- **Tests/Validation:** `pytest tests/integration/test_draft_rejection_api.py`
- **Acceptance Criteria:** Reasons clear, user understands why blocked

### 12.6: Draft approval workflow (manual review → send)
- **Files/Modules:** `src/models/draft.py` (add fields), `src/api/drafts.py` (add endpoints)
- **Fields:** `approved_by: str | None, approved_at: datetime | None, approval_notes: str | None`
- **Endpoints:**
  - `POST /api/drafts/{draft_id}/approve` → {approval_notes?} (user-only endpoint, auth required)
  - `POST /api/drafts/{draft_id}/reject` → {reason} (user-only endpoint, audit logged)
- **Logic:** Only approved drafts can be sent; rejections block send
- **Tests/Validation:**
  - `pytest tests/integration/test_draft_approval.py::test_draft_can_be_approved_and_queued_for_send`
  - `pytest tests/integration/test_draft_approval.py::test_rejected_draft_cannot_be_sent`
- **Acceptance Criteria:** Approval workflow works, state transitions correct

---

## **SPRINT 13: Use Case #2 — Story Pitching (Segmentation + Bulk Targeting)**
**Sprint Goal:** Can segment contacts, generate targeted story pitches, bulk-create drafts with rate limiting.

**Demo Steps:**
```bash
python -m src.cli.story-pitch --segment "high-growth-tech" --limit 5 --dry-run
# Output: 5 contacts ranked by fit, pitch preview for each

# Actually create (with --create):
python -m src.cli.story-pitch --segment "high-growth-tech" --limit 5 --create --verbose
# Output: Created 5 drafts
```

**Tickets:**

### 13.1: Segmentation model (persona, industry, company fit)
- **Files/Modules:** `src/models/segment.py`, `src/services/segmentation.py`
- **Methods:** `segment_contact(contact: Contact) -> Segment`
- **Segment Structure:**
  ```python
  Segment(
    persona: str (BUYER | INFLUENCER | TECHNICAL | FINANCIAL),
    industry: str (TECH | FINANCE | HEALTHCARE | ENTERPRISE | RETAIL | ...),
    company_fit: str (HIGH | MEDIUM | LOW),
    reason: str
  )
  ```
- **Segmentation Logic:**
  - Persona: Inferred from job title (VP Sales → BUYER, CTO → TECHNICAL, CFO → FINANCIAL)
  - Industry: From hubspot_companies.industry
  - Fit: Based on employee count (10–500 = HIGH, 500–5000 = MEDIUM, etc.) + industry match
- **Tests/Validation:**
  - `pytest tests/unit/test_segmentation.py::test_assigns_correct_segment` (golden file: 10 contacts → segments)
  - Coverage > 95%
- **Acceptance Criteria:** Segments computed, deterministic, coverage high

### 13.2: StoryPitchTargetingAgent (rank contacts by relevance + recency)
- **Files/Modules:** `src/agents/story_pitch_targeting.py`
- **Methods:** `StoryPitchTargetingAgent.rank_for_story(story_id: str, segment: Segment, limit: int = 20) -> List[RankedContact]`
- **Output:**
  ```python
  RankedContact(
    contact_id: int,
    email: str,
    company_name: str,
    rank: int,
    fit_score: float (0–1),
    recency_days: int,
    prior_engagements: int,
    reason: str
  )
  ```
- **Ranking Factors:**
  1. Segment fit (exact match = +0.4)
  2. Engagement history (opened email in last 30d = +0.2, clicked = +0.3)
  3. Recency (last contact > 90d ago = +0.2; recent contact < 7d = -0.3)
  4. Prior story touches (first story = +0.1; already sent story = -0.5)
- **Final Score:** sum of factors, capped at 1.0
- **Tests/Validation:**
  - `pytest tests/unit/test_story_targeting.py::test_ranks_relevant_contacts_first` (golden file)
  - Top-ranked contacts make business sense
- **Acceptance Criteria:** Ranking logic correct, scores calibrated

### 13.3: Story campaign definition + metadata
- **Files/Modules:** `src/models/story.py`, `infra/migrations/versions/012_story_schema.py`
- **Table:**
  - `story_campaigns` (id, name, theme, target_persona, target_industry, key_message TEXT, cta TEXT, asset_ids JSONB, active, created_at, updated_at)
  - Example: {name: "AI Productivity", theme: "ai_tools", target_persona: "BUYER", target_industry: "TECH", key_message: "How we increased productivity 40%", cta: "See our playbook", asset_ids: [drive_file_id1, drive_file_id2]}
- **Tests/Validation:** Schema validation, foreign keys
- **Acceptance Criteria:** Stories storable, queryable

### 13.4: StoryPitchWriterAgent (personalized story pitch draft)
- **Files/Modules:** `src/agents/story_pitch_writer.py`
- **Methods:** `StoryPitchWriterAgent.write_pitch(contact: Contact, story: StoryCampaign, voice_profile: VoiceProfile) -> Draft`
- **Personalization:**
  - Reference company/industry specifics (e.g., "As a [INDUSTRY] company...")
  - Retrieve contact's recent activity via LongMemoryAgent (if any prior threads)
  - Find relevant asset via AssetHunterAgent (matching story theme + industry)
  - Include meeting slots via MeetingSlotAgent
- **Constraints:** Same as DraftWriterAgent (voice profile, <200 words, 1 CTA, no em-dashes, no PII)
- **Tests/Validation:**
  - `pytest tests/unit/test_story_pitch_writer.py::test_personalizes_pitch_for_industry` (golden file: contact + story → expected pitch)
  - Verify personalization details are correct
- **Acceptance Criteria:** Pitch personalized, voice-compliant, assets attached

### 13.5: Story pitch orchestrator (bulk create with rate limiting)
- **Files/Modules:** `src/orchestration/story_pitch_orchestrator.py`
- **Methods:** `StoryPitchOrchestrator.execute(story_id: str, segment: Segment, dry_run: bool = True) -> Result`
- **Rate Limiting:**
  - Max 20 story pitches per day (global quota)
  - No more than 1 story per contact per 14 days
  - Respect suppression list
  - Max 50 drafts per execution
- **Dry Run:** Generate drafts but don't persist; return count + previews
- **Execution:**
  - Fetch ranked contacts for segment
  - For each contact: write pitch, validate, store draft
  - Log stats: created, skipped (reason: suppressed, quota, guardrail)
  - Update contact last_story_touch timestamp
- **Tests/Validation:**
  - `pytest tests/integration/test_story_orchestrator.py::test_respects_rate_limits`
  - `pytest tests/integration/test_story_orchestrator.py::test_dry_run_produces_no_side_effects`
- **Acceptance Criteria:** Rate limits enforced, dry-run works, stats accurate

### 13.6: Celery task for story pitch bulk generation
- **Files/Modules:** `src/workers/story_pitch_worker.py`
- **Task:** `generate_story_pitches(story_id: str, segment: str, dry_run: bool = False) -> dict` (stats: {created, skipped, errors, error_reasons})
- **Execution:** Async task; calls orchestrator; logs results
- **Tests/Validation:** `pytest tests/integration/test_story_pitch_worker.py` (mock Celery)
- **Acceptance Criteria:** Task executes, stats logged

### 13.7: CLI for story pitch generation + dry-run preview
- **Files/Modules:** `src/cli/story_pitch.py`
- **Commands:**
  - `python -m src.cli.story-pitch --story-id <id> --segment <seg> --limit 5 --dry-run`
  - `python -m src.cli.story-pitch --story-id <id> --segment <seg> --limit 5 --create --verbose`
- **Output (dry-run):** Contact list, pitch preview for first 3, stats
- **Tests/Validation:** `pytest tests/integration/test_cli_story_pitch.py`
- **Acceptance Criteria:** CLI works, dry-run safe, create verified

---

## **PHASE 4: SAFE SEND PATHWAY & ADVANCED FEATURES (Sprints 14–16)**

---

## **SPRINT 14: Quotas & Rate Limiting (Prevent Runaway Sends)**
**Sprint Goal:** Daily/weekly send quotas, per-contact frequency limits, graceful enforcement.

**Demo Steps:**
```bash
curl http://localhost:8000/api/quotas/status
# {"daily_limit": 50, "daily_sent": 23, "remaining": 27}

# Try to exceed quota:
python -m src.cli.test-overquota
# Output: "quota exceeded for today"
```

**Tickets:**

### 14.1: Quota definitions + config (daily, weekly, per-contact)
- **Files/Modules:** `src/models/quota.py`, `src/config.py` (add quota settings)
- **Quotas:**
  - Daily send limit (e.g., 50)
  - Weekly send limit (e.g., 200)
  - Per-contact frequency (no more than 1 email per 7 days)
  - Per-contact weekly (no more than 2 emails per week)
- **Tests/Validation:** Schema validation
- **Acceptance Criteria:** Quotas loadable, configurable

### 14.2: QuotaTracker service (check + record)
- **Files/Modules:** `src/services/quota_tracker.py`
- **Methods:**
  - `QuotaTracker.check_quota(contact_id: int, count: int = 1) -> (bool, reason)` (can_send, why_not)
  - `QuotaTracker.record_send(contact_id: int) -> None` (increment counters)
- **Storage:** Redis counters (reset daily/weekly via scheduled task)
- **Keys:**
  - `quota:daily:sends` (integer, reset daily at midnight UTC)
  - `quota:weekly:sends` (integer, reset weekly Monday)
  - `quota:contact:{contact_id}:last_send` (timestamp)
  - `quota:contact:{contact_id}:weekly_count` (integer)
- **Tests/Validation:**
  - `pytest tests/unit/test_quota_tracker.py::test_enforces_daily_limit`
  - `pytest tests/unit/test_quota_tracker.py::test_enforces_per_contact_frequency`
  - Test counter resets
- **Acceptance Criteria:** Limits enforced, counters reset correctly

### 14.3: QuotaExceededError exception
- **Files/Modules:** `src/exceptions.py`, `src/agents/quality_gate.py` (integrate)
- **Exception:** `QuotaExceededError(quota_type: str, limit: int, current: int, reset_at: datetime)`
- **Integration:** QualityGateAgent calls `quota_tracker.check_quota()`, raises error if fails
- **Tests/Validation:** `pytest tests/unit/test_exceptions.py::test_quota_exceeded_raised`
- **Acceptance Criteria:** Exception caught, draft blocked, reason logged

### 14.4: Quota API endpoint (status + admin override)
- **Files/Modules:** `src/api/quotas.py` (FastAPI router)
- **Endpoints:**
  - `GET /api/quotas/status` → {daily_limit, daily_sent, remaining, weekly_limit, weekly_sent, weekly_remaining}
  - `POST /api/admin/quotas/reset` → reset counters (admin only)
  - `POST /api/admin/quotas/set-limits` → {daily_limit, weekly_limit} (admin only)
- **Tests/Validation:** `pytest tests/integration/test_quota_api.py`
- **Acceptance Criteria:** Endpoints work, admin can override

---

## **SPRINT 15: Gmail Send Integration (Safe Path)**
**Sprint Goal:** Drafts can be sent programmatically; delivery tracked; respects DRAFT_ONLY mode.

**Demo Steps:**
```bash
# In SEND_ALLOWED mode:
python -m src.cli.test-followup --contact-email "user@company.com" --mode SEND_ALLOWED
# Verify draft was sent:
curl http://localhost:8000/api/drafts/{draft_id}
# {"status": "sent", "gmail_message_id": "...", "sent_at": "2026-01-23T..."}

# Check delivery status:
curl http://localhost:8000/api/email-events?draft_id={draft_id}
# {"status": "delivered", "opened": false, "clicked": false}
```

**Tickets:**

### 15.1: Gmail send API client (draft → message)
- **Files/Modules:** `src/connectors/gmail/sender.py`
- **Methods:** `GmailSender.send_draft(draft: Draft) -> SendResult` (gmail_message_id, timestamp)
- **Steps:**
  1. Build MIME message from draft (to, cc, subject, body, attachments)
  2. Call Gmail API `users.messages.send()`
  3. Return message ID + timestamp
- **Tests/Validation:** `pytest tests/unit/test_gmail_sender.py` (mock Gmail API)
- **Acceptance Criteria:** Sends work, message IDs returned

### 15.2: Draft → Gmail message mapping (track sent emails)
- **Files/Modules:** `src/models/draft.py` (add fields)
- **Fields:**
  - `gmail_message_id: str | None` (set when sent)
  - `sent_at: datetime | None`
  - `delivered_at: datetime | None` (updated via webhook)
  - `opened_at: datetime | None` (updated via webhook)
- **Tests/Validation:** Schema validation
- **Acceptance Criteria:** Fields stored, queryable

### 15.3: Send workflow integration (respects MODE + guardrails)
- **Files/Modules:** `src/orchestration/followup_orchestrator.py` (add send step), `src/agents/quality_gate.py` (update)
- **Logic:**
  - If MODE == DRAFT_ONLY → draft.status = PENDING, no send
  - If MODE == SEND_ALLOWED + approval (if required) + quota OK → call GmailSender.send_draft()
  - Catch exceptions: log to audit, update draft status
- **Tests/Validation:**
  - `pytest tests/integration/test_followup_orchestrator.py::test_respects_mode_on_send`
  - `pytest tests/integration/test_followup_orchestrator.py::test_sends_approved_draft_only`
- **Acceptance Criteria:** Respects mode, sends only when allowed

### 15.4: Deferred send task (background send with delay)
- **Files/Modules:** `src/workers/send_worker.py`
- **Task:** `send_draft_deferred(draft_id: int, delay_seconds: int = 0) -> dict` (success, gmail_message_id or error)
- **Execution:** Sleep delay, then call send; log result
- **Tests/Validation:** `pytest tests/integration/test_send_worker.py::test_send_with_delay` (mock Celery)
- **Acceptance Criteria:** Task executes, honors delay

### 15.5: Email event tracking (sent, delivered, opened, clicked)
- **Files/Modules:** `src/models/email_event.py`, `infra/migrations/versions/013_email_events.py`
- **Table:** `email_events` (id, draft_id FK, gmail_message_id, event_type (SENT|DELIVERED|OPENED|CLICKED), user_agent, ip_address, timestamp)
- **Tests/Validation:** Schema validation, indices
- **Acceptance Criteria:** Events queryable, timestamps correct

### 15.6: Google Pub/Sub webhook for delivery + open tracking
- **Files/Modules:** `src/connectors/pubsub/__init__.py`, `src/connectors/pubsub/listener.py`, `src/api/webhooks.py`
- **Setup:** Google Pub/Sub subscriptions configured for email events
- **Endpoint:** `POST /webhooks/gmail-events` (Pub/Sub push subscription)
- **Payload:** Pub/Sub message with event details (Gmail message ID, event type, timestamp)
- **Logic:**
  1. Validate Pub/Sub message signature (JWT)
  2. Parse event
  3. Upsert email_events row
  4. Update draft.delivered_at / opened_at as needed
- **Tests/Validation:**
  - `pytest tests/integration/test_gmail_webhook.py::test_receives_delivery_event` (fixture Pub/Sub messages)
  - Signature validation tested
- **Acceptance Criteria:** Webhook receives events, stores them, updates drafts

### 15.7: Email metrics API (delivery rate, open rate, click rate)
- **Files/Modules:** `src/api/metrics.py` (add endpoints)
- **Endpoints:**
  - `GET /api/metrics/email-performance` → {sent_count, delivered_count, opened_count, clicked_count, delivery_rate, open_rate, click_rate}
  - `GET /api/metrics/email-performance?company_id=456` → stats by company
- **Tests/Validation:** `pytest tests/integration/test_metrics_api.py`
- **Acceptance Criteria:** Endpoints work, metrics computed correctly

---

## **SPRINT 16: Monitoring, Observability & Deployment**
**Sprint Goal:** Structured logging, metrics, alerting, deployment to GCP Cloud Run.

**Demo Steps:**
```bash
# Check logs:
curl http://localhost:8000/api/metrics
# {"requests": 1234, "errors": 5, "avg_latency_ms": 245}

# Deploy to staging:
./infra/deploy.sh staging
# Verify in Cloud Run console
```

**Tickets:**

### 16.1: Structured logging (JSON format, trace IDs)
- **Files/Modules:** `src/logger.py` (enhance), middleware + all agents/services (add logging)
- **Format:**
  ```json
  {
    "timestamp": "2026-01-23T10:30:45.123Z",
    "level": "INFO",
    "trace_id": "...",
    "service": "sales-agent",
    "module": "agents.draft_writer",
    "function": "write_draft",
    "message": "Draft created for contact 123",
    "data": {
      "draft_id": 1,
      "contact_id": 123,
      "duration_ms": 2150,
      "status": "pending"
    }
  }
  ```
- **Trace IDs:** Generated per request, propagated through all calls
- **Tests/Validation:** `pytest tests/unit/test_logging.py::test_logs_are_valid_json`
- **Acceptance Criteria:** All logs are valid JSON, trace_id flows correctly

### 16.2: Metrics collection (request count, latency, errors)
- **Files/Modules:** `src/middleware.py` (request metrics), `src/services/metrics.py`
- **Metrics:**
  - request_count (by endpoint, method)
  - request_latency (p50, p95, p99 ms)
  - error_count (by type)
  - draft_created_count
  - draft_sent_count
  - draft_rejected_count
  - email_delivery_count
- **Export:** Prometheus format at `/metrics`
- **Tests/Validation:** `pytest tests/unit/test_metrics.py`
- **Acceptance Criteria:** Metrics queryable, format correct

### 16.3: Metrics API endpoint (statistics)
- **Files/Modules:** `src/api/metrics.py` (FastAPI router)
- **Endpoints:**
  - `GET /api/metrics` → Prometheus format
  - `GET /api/stats/daily` → {drafts_created, drafts_sent, drafts_rejected, emails_delivered, errors}
  - `GET /api/stats/contacts?company_id=456` → top active contacts by company
- **Tests/Validation:** `pytest tests/integration/test_metrics_api.py`
- **Acceptance Criteria:** Endpoints return correct data

### 16.4: Health check + readiness endpoints (Kubernetes-ready)
- **Files/Modules:** `src/api/health.py`, `src/main.py`
- **Endpoints:**
  - `GET /health` → simple 200 OK
  - `GET /ready` → checks DB, Redis, external services; returns 200 or 503
- **Tests/Validation:** `pytest tests/integration/test_health_checks.py`
- **Acceptance Criteria:** Endpoints work, ready detects failures

### 16.5: GCP Secret Manager integration (secure credential loading)
- **Files/Modules:** `src/config.py` (add secret loading), `src/connectors/` (use secrets)
- **Logic:**
  - On startup, fetch secrets from GCP Secret Manager (if env = production)
  - Cache in memory (TTL: 1 hour) with refresh task
  - Fall back to env vars for local dev
- **Secrets:** HUBSPOT_API_KEY, GMAIL_SERVICE_ACCOUNT_KEY, OPENAI_API_KEY, DB_PASSWORD, REDIS_PASSWORD
- **Tests/Validation:** `pytest tests/unit/test_gcp_secrets.py` (mock API)
- **Acceptance Criteria:** Secrets loaded securely, no hardcoding

### 16.6: Docker image build + publish (GCR)
- **Files/Modules:** `Dockerfile`, `Dockerfile.worker`, `.dockerignore`, `infra/build.sh`
- **Images:**
  - `gcr.io/PROJECT/sales-agent-api:latest` (API service)
  - `gcr.io/PROJECT/sales-agent-worker:latest` (Celery worker)
- **Build Steps:**
  - Multi-stage: build stage (pip install) + runtime stage (slim base)
  - Size < 500MB each
- **Tests/Validation:**
  - `docker build -t sales-agent-api:test .` builds cleanly
  - `docker run --rm sales-agent-api:test --version` verifies image
- **Acceptance Criteria:** Images build, run, < 500MB

### 16.7: Cloud Run deployment (API + Worker)
- **Files/Modules:** `infra/deploy.sh`, `infra/cloud-run-config.yaml`, `infra/terraform/` (optional)
- **Deployment:**
  - API service: Cloud Run (auto-scaling, concurrency=50)
  - Worker service: Cloud Run (no HTTP, concurrency=1, idle timeout=300s)
  - Environment: staging + production
  - Env vars loaded from Secret Manager
- **Deploy Steps:**
  ```bash
  ./infra/deploy.sh staging
  ./infra/deploy.sh production
  ```
- **Tests/Validation:**
  - Deploy to staging
  - Verify endpoints respond: `curl https://staging-api.example.com/health`
  - Verify logs flow to Cloud Logging
- **Acceptance Criteria:** Services deploy, accessible, healthy

### 16.8: Cloud SQL (Postgres + backups, connection pooling)
- **Files/Modules:** `infra/cloud-sql-config.yaml`, `src/db/session.py` (connection pooling)
- **Setup:**
  - Cloud SQL instance: Postgres 15+, pgvector extension
  - Cloud SQL Auth Proxy for secure connections
  - Automated backups: daily, 30-day retention
  - Connection pooling: pgBouncer or SQLAlchemy pool_pre_ping
- **Tests/Validation:**
  - Connect from local via Cloud SQL Proxy
  - Run migrations successfully
  - Backup job scheduled
- **Acceptance Criteria:** DB accessible, backups configured

### 16.9: Alert rules (error rate, latency, failures)
- **Files/Modules:** `infra/alerts.yaml` or Cloud Monitoring setup doc
- **Alerts:**
  - Error rate > 1% (send to Slack)
  - Response time p99 > 5s (warning)
  - Worker task failures > 10/hour (critical)
  - DB connection pool exhausted (critical)
  - Kill switch engaged (critical)
- **Channels:** Slack, PagerDuty (if applicable)
- **Tests/Validation:** Manual trigger, verify alert fires
- **Acceptance Criteria:** Alerts configured, notification channels work

### 16.10: Runbook (troubleshooting, manual overrides, escalation)
- **Files/Modules:** `docs/RUNBOOK.md`
- **Sections:**
  - Enable/disable kill switch (command)
  - Manually block a contact (command)
  - Override quota for a contact (command)
  - Inspect draft audit log (query)
  - Roll back deployment (steps)
  - Emergency contacts (names + phone)
- **Tests/Validation:** Peer review for clarity
- **Acceptance Criteria:** Runbook is clear, on-call engineer can follow steps

---

## **SPRINT 17: Integration & E2E Testing**
**Sprint Goal:** Full e2e tests, performance baselines, docker compose smoke test, CI/CD gates.

**Demo Steps:**
```bash
docker compose up --wait
pytest tests/e2e/test_full_followup_flow.py -v
# Output: All tests pass

docker compose logs api | grep ERROR
# Should be empty
```

**Tickets:**

### 17.1: E2E test: form submission → draft creation
- **Files/Modules:** `tests/e2e/test_full_followup_flow.py`
- **Test:** `test_form_to_draft_end_to_end`
  1. Simulate form submission
  2. Verify job created in DB
  3. Verify draft created (check subject, body, contact_id)
  4. Verify HubSpot note created
  5. Verify audit log entry
- **Timing:** < 10 sec
- **Tests/Validation:** `pytest tests/e2e/test_full_followup_flow.py::test_form_to_draft_end_to_end`
- **Acceptance Criteria:** Test passes, timing acceptable

### 17.2: E2E test: story pitch generation → bulk create
- **Files/Modules:** `tests/e2e/test_story_pitch_flow.py`
- **Test:** `test_story_pitch_end_to_end`
  1. Create story campaign
  2. Trigger story pitch generation for segment
  3. Verify N drafts created
  4. Verify rate limits respected (no > 20 per day)
  5. Verify no duplicate contacts
- **Tests/Validation:** `pytest tests/e2e/test_story_pitch_flow.py`
- **Acceptance Criteria:** Test passes

### 17.3: E2E test: draft rejection by quality gate
- **Files/Modules:** `tests/e2e/test_quality_gate_flow.py`
- **Tests:**
  - Draft with PII → REJECTED
  - Draft with forbidden word → REJECTED or WARN
  - Clean draft from trusted company → APPROVED
  - Suppressed contact → REJECTED
  - Guardrail violation → REJECTED
- **Tests/Validation:** `pytest tests/e2e/test_quality_gate_flow.py`
- **Acceptance Criteria:** Test passes

### 17.4: Performance benchmark (query latency, throughput)
- **Files/Modules:** `tests/bench/bench_latency.py`
- **Benchmarks:**
  - ThreadReaderAgent.read_thread() < 500ms
  - LongMemoryAgent.retrieve_context() < 1s
  - QualityGateAgent.evaluate() < 200ms
  - AssetHunterAgent.find_assets() < 500ms
  - Draft creation end-to-end < 5s
- **Execution:** `pytest tests/bench/bench_latency.py -v` (separate from unit tests)
- **Recording:** Store results in `docs/BENCHMARKS.md`
- **Tests/Validation:** All latencies under thresholds
- **Acceptance Criteria:** Benchmarks pass, results recorded

### 17.5: Docker Compose smoke test (all services healthy)
- **Files/Modules:** `tests/integration/test_docker_compose_health.py`
- **Test:**
  1. `docker compose up --wait`
  2. Verify Postgres is healthy (query count)
  3. Verify Redis is healthy (PING)
  4. Verify API health check (GET /health)
  5. Verify migrations applied
  6. Verify no hanging processes
- **Tests/Validation:** `pytest tests/integration/test_docker_compose_health.py`
- **Acceptance Criteria:** Test passes, no hanging services

### 17.6: Lint + type check gates (ruff, pyright)
- **Files/Modules:** `.pre-commit-config.yaml`, CI config
- **Gates:**
  - `ruff check src/ tests/` (no errors)
  - `pyright src/ tests/` (no type errors)
  - `pytest tests/unit/ -q` (core unit tests)
- **Tests/Validation:** Run locally + in CI
- **Acceptance Criteria:** No lint/type errors, gates pass in CI

### 17.7: CI/CD pipeline (GitHub Actions or GCP Cloud Build)
- **Files/Modules:** `.github/workflows/ci.yml` or `cloudbuild.yaml`
- **Steps:**
  1. Checkout code
  2. Lint (ruff)
  3. Type check (pyright)
  4. Unit tests
  5. Integration tests (with Docker Compose)
  6. Build Docker images
  7. Push to GCR (if main branch)
  8. Deploy to staging (if main branch)
- **Tests/Validation:** CI workflow executes successfully
- **Acceptance Criteria:** Pipeline works, gates enforced

---

## **SPRINT 18: Documentation & Knowledge Transfer**
**Sprint Goal:** Comprehensive docs for developers, operators, users.

**Demo Steps:**
```bash
# Follow README to set up locally:
cat README.md
# Follow DEVELOPMENT guide:
cat docs/DEVELOPMENT.md
# Check API docs:
curl http://localhost:8000/docs
# Interactive Swagger UI with all endpoints
```

**Tickets:**

### 18.1: README (project overview, quick start, architecture)
- **Files/Modules:** `README.md`
- **Sections:**
  - Project overview (what it does, key features)
  - Quick start (clone, docker compose up, curl examples)
  - Architecture diagram (agents, orchestrator, connectors)
  - Directory structure
  - Links to docs (DEVELOPMENT, DEPLOYMENT, RUNBOOK, API)
- **Tests/Validation:** Follow README steps locally; verify they work
- **Acceptance Criteria:** README is clear, setup works as written

### 18.2: DEVELOPMENT guide (local setup, testing, extending)
- **Files/Modules:** `docs/DEVELOPMENT.md`
- **Sections:**
  - Prerequisites (Python 3.12, Docker, etc.)
  - Local development setup
  - Running tests (unit, integration, e2e)
  - Adding new agents (template + example)
  - Debugging (logs, breakpoints, etc.)
  - Pre-commit workflow
- **Tests/Validation:** Peer review for clarity
- **Acceptance Criteria:** Guide is comprehensive, clear

### 18.3: API documentation (auto-generated Swagger + manual)
- **Files/Modules:** `src/main.py` (FastAPI docstrings), `docs/API.md` (manual)
- **Auto-generated:** FastAPI Swagger at `/docs` with all endpoints
- **Manual:** Markdown guide with examples, auth, rate limits
- **Tests/Validation:** Visit `/docs` locally, verify endpoints listed
- **Acceptance Criteria:** API docs complete, examples correct

### 18.4: Deployment guide (local, staging, production)
- **Files/Modules:** `docs/DEPLOYMENT.md`
- **Sections:**
  - Prerequisites (GCP project, Secret Manager, etc.)
  - Deploying to staging
  - Deploying to production (checklist, rollback)
  - Monitoring (logs, metrics, alerts)
  - Troubleshooting
- **Tests/Validation:** Deploy to staging following guide
- **Acceptance Criteria:** Guide works end-to-end

### 18.5: Voice profile documentation (how it works, examples)
- **Files/Modules:** `docs/VOICE_PROFILE.md`, example `docs/voice_profile.json`
- **Sections:**
  - What is voice profile (purpose, use)
  - How to learn it (command, parameters)
  - How to validate it (checklist)
  - Example profile (annotated JSON)
  - Extending/customizing
- **Tests/Validation:** Example profile is valid
- **Acceptance Criteria:** Docs clear, example works

### 18.6: Operator runbook (troubleshooting, manual controls)
- **Files/Modules:** `docs/RUNBOOK.md`
- **Sections:**
  - Quick facts (SLO, contacts limit, quota, kill switch)
  - Common issues (high error rate, slow drafts, failed sends) + fixes
  - Manual controls (enable/disable features, override quota, block contact)
  - Emergency escalation
- **Tests/Validation:** Peer review
- **Acceptance Criteria:** Runbook is actionable, clear

### 18.7: CONTRIBUTING guide (how to submit PRs, code review, release process)
- **Files/Modules:** `docs/CONTRIBUTING.md`
- **Sections:**
  - Commit message convention
  - Code review process
  - Testing requirements (min coverage)
  - Release process (versioning, tags, deployment)
- **Tests/Validation:** Peer review
- **Acceptance Criteria:** Guide is clear, aligns with team practices

---

## **SPRINT 19: Demo & Feedback (Optional, Real-World Feedback)**
**Sprint Goal:** Demo full system end-to-end to stakeholders, gather feedback, iterate.

**Demo Steps:**
```bash
# Deploy to staging
./infra/deploy.sh staging

# Live demo:
# 1. Show form submission trigger → draft creation (DRAFT_ONLY mode)
# 2. Show draft approval workflow
# 3. Switch to SEND_ALLOWED mode
# 4. Show draft send + delivery tracking
# 5. Show story pitch bulk generation (dry-run first)
# 6. Show audit logs + metrics dashboard
```

**Tickets:**

### 19.1: Demo script + talking points
- **Files/Modules:** `docs/DEMO.md`, demo script
- **Content:**
  - Setup checklist (ensure staging is clean)
  - Step-by-step narrative with timing
  - Talking points (safety, voice learning, integrations)
  - Q&A prepared responses
- **Tests/Validation:** Run demo script locally, time it
- **Acceptance Criteria:** Demo runs smoothly, <15 minutes

### 19.2: Feedback collection + documentation
- **Files/Modules:** `docs/FEEDBACK.md`, GitHub Issues
- **Process:**
  - Collect feedback on demo
  - Open GitHub Issues for requested features
  - Prioritize for future sprints
- **Tests/Validation:** Document findings
- **Acceptance Criteria:** Feedback documented, prioritized

---

## **SPRINT 20: Hardening & Security Review**
**Sprint Goal:** Security audit, data privacy review, compliance checks.

**Demo Steps:**
```bash
# Security checks:
pytest tests/security/test_pii_redaction.py -v
pytest tests/security/test_auth.py -v
pytest tests/security/test_sql_injection.py -v

# Dependency audit:
pip audit

# Check logs for secrets:
grep -r "password\|api_key\|secret" src/ tests/ || echo "No secrets found"
```

**Tickets:**

### 20.1: PII redaction security test
- **Files/Modules:** `tests/security/test_pii_redaction.py`
- **Tests:**
  - PII cannot leak into drafts
  - PII cannot leak into logs
  - PII cannot leak into voice profile
  - PII cannot leak into audit logs
- **Tests/Validation:** `pytest tests/security/test_pii_redaction.py`
- **Acceptance Criteria:** No PII leakage detected

### 20.2: Authentication & authorization test
- **Files/Modules:** `tests/security/test_auth.py`
- **Tests:**
  - Non-authenticated users cannot access protected endpoints
  - Non-admin users cannot access admin endpoints
  - Token expiry handled correctly
  - Rate limiting on auth endpoints
- **Tests/Validation:** `pytest tests/security/test_auth.py`
- **Acceptance Criteria:** Auth/authz working correctly

### 20.3: SQL injection test
- **Files/Modules:** `tests/security/test_sql_injection.py`
- **Tests:**
  - Query parameters sanitized
  - ORM prevents direct SQL injection
  - Prepared statements used
- **Tests/Validation:** `pytest tests/security/test_sql_injection.py`
- **Acceptance Criteria:** No injection vulnerabilities

### 20.4: Dependency audit
- **Files/Modules:** `pyproject.toml`, requirements scanning
- **Process:**
  - Run `pip audit`
  - Review high-severity vulnerabilities
  - Update dependencies if needed
- **Tests/Validation:** `pip audit` passes with no critical issues
- **Acceptance Criteria:** No high-severity dependencies

### 20.5: Secrets audit
- **Files/Modules:** Grep scan for hardcoded secrets
- **Process:**
  - Scan codebase for patterns (password, api_key, secret, token)
  - Verify all secrets are externalized
- **Tests/Validation:** `grep -r "password\|api_key\|secret" src/` returns no matches
- **Acceptance Criteria:** No hardcoded secrets found

### 20.6: Data privacy review & GDPR compliance checklist
- **Files/Modules:** `docs/PRIVACY.md`
- **Topics:**
  - PII handling & storage
  - Retention policies
  - User consent & opt-out
  - Right to deletion (how to purge data)
  - Data breach incident plan
- **Tests/Validation:** Peer review by legal/privacy team
- **Acceptance Criteria:** Compliance checklist signed off

---

## **Summary: Sprints at a Glance**

| Sprint | Phase | Focus | Key Deliverable |
|--------|-------|-------|-----------------|
| 0 | Infrastructure | Foundation | Docker Compose, API scaffold |
| 1 | Infrastructure | Data Models | DB schema, ORM, migrations |
| 2 | Infrastructure | Resilience | Retry, circuit breaker, idempotency |
| 3 | Infrastructure | Auth & Secrets | OAuth2, Secret Manager, PII redaction |
| 4 | Safety | Feature Flags | MODE, kill switch, feature flags |
| 5 | Safety | Guardrails | Suppression list, allowlists, rules |
| 6 | Connectors | Gmail | Thread fetch, message indexing, embeddings |
| 7 | Connectors | HubSpot | Entity sync, form listener, IdentityResolver |
| 8 | Connectors | Drive | Allowlist indexing, asset retrieval |
| 9 | Connectors | Calendar | Freebusy query, meeting slot proposal |
| 10 | Data Retrieval | Voice Learning | Pattern extraction, profile storage, eval harness |
| 11 | Use Cases | Lead Followup (Part A) | Trigger → Draft pipeline, orchestrator |
| 12 | Use Cases | Lead Followup (Part B) | Quality gates, audit logging, approval workflow |
| 13 | Use Cases | Story Pitching | Segmentation, targeting, bulk generation |
| 14 | Scaling | Quotas | Daily/weekly limits, per-contact frequency |
| 15 | Scaling | Gmail Send | Safe send path, delivery tracking, Pub/Sub |
| 16 | Deployment | Monitoring & Deploy | Structured logging, metrics, GCP Cloud Run |
| 17 | Quality | E2E & Testing | Full flow tests, benchmarks, CI/CD |
| 18 | Docs | Documentation | README, API docs, runbook, guides |
| 19 | Real-world | Demo & Feedback | Live demo, gather feedback |
| 20 | Quality | Security Review | PII audit, auth test, secrets scan |

---

## **Definition of Done (Universal)**

Every ticket must satisfy ALL of the following:

1. **Code is written** in the specified files/modules
2. **Tests pass** (unit, integration, or other validation as specified)
3. **Type hints** pass Pyright with no errors
4. **Lint passes** Ruff with no errors
5. **Documentation** is updated (docstrings, README, guides)
6. **Git commit** is atomic and has clear message
7. **PR is reviewed** by at least one peer
8. **PR is merged** to main branch

---

## **Key Architectural Principles**

1. **Safety First:** DRAFT_ONLY mode by default; safe path to auto-send later
2. **Composability:** Mini-agents are independent; orchestrator choreographs
3. **Auditability:** Every action logged; compliance trail maintained
4. **Resilience:** Retry logic, circuit breakers, graceful degradation
5. **Voice Authenticity:** Learn from data, not descriptors; PII-safe
6. **Guardrails:** Multi-layer checks (guardrails → suppression → quality gate → quota)
7. **Observability:** Structured logs, metrics, tracing for debugging

---

## **Success Criteria (Project-Level)**

- ✅ DRAFT_ONLY mode works end-to-end (form → draft → HubSpot note)
- ✅ Voice profile learned from historical emails; no PII leakage
- ✅ All major agents functional and tested (12 agents)
- ✅ Orchestrator state machine handles happy path + error cases
- ✅ Quality gates block unsafe drafts (PII, suppression, guardrails)
- ✅ Quotas & rate limiting prevent runaway sends
- ✅ Audit log captures all draft lifecycle events
- ✅ E2E tests cover form→draft, story pitch, quality gate flows
- ✅ Deployment to GCP Cloud Run works smoothly
- ✅ All code is type-hinted, linted, tested, documented
- ✅ Runbook is clear and operational

---

## **Risk Mitigation**

| Risk | Mitigation |
|------|-----------|
| API rate limits (Gmail, HubSpot) | Batch requests, exponential backoff, circuit breaker |
| PII leakage into drafts/logs | Redaction service, tests, security audit |
| Runaway sends in SEND_ALLOWED | Kill switch, quotas, per-contact frequency, approval workflow |
| Database scaling | pgvector indexing, connection pooling, Cloud SQL backups |
| Agent hallucinations (LLM) | Golden file fixtures, eval harness, voice profile constraints |
| Webhook delivery failures | Dead letter queue, retry logic, manual reconciliation |
| Team onboarding | Comprehensive docs, runbook, demo script |

---

## **Next Steps**

1. **Kickoff:** Review plan with team; adjust sprints if needed
2. **Sprint 0:** Set up repo, docker compose, basic CI/CD pipeline
3. **Sprint 1–5:** Infrastructure & safety foundations (foundation before features)
4. **Sprint 6–10:** Connectors & data retrieval (connectors before use cases)
5. **Sprint 11–13:** Use cases & orchestration (core product)
6. **Sprint 14–16:** Scaling, sending, deployment (safe path to production)
7. **Sprint 17–20:** Testing, docs, security, hardening (quality & compliance)

---

**Plan Status:** ✅ Ready for Implementation  
**Last Updated:** 2026-01-20  
**Prepared for:** Sales-agent Team
