# CaseyOS Roadmap v3.0

> **Last Updated:** January 2026  
> **Current Sprint:** 43 (Dashboard Intelligence & Metrics)  
> **Production URL:** https://web-production-a6ccf.up.railway.app

---

## Executive Summary

CaseyOS is an autonomous B2B GTM command center with 31 agents across 7 domains (sales, content, research, fulfillment, contracts, ops, data_hygiene). This roadmap defines the next 8 sprints focused on:

1. **Agent Orchestration** - Execution tracking, manual triggers, history
2. **UX Polish** - Dashboard improvements, mobile, accessibility
3. **Bot Training** - Voice/persona refinement, context memory
4. **Deep Research** - Multi-source research with citations
5. **Data Hygiene** - Duplicate detection, enrichment, sync health
6. **Pipeline Intelligence** - Deal insights, forecasting, alerts

---

## Sprint Status Audit

### ✅ Completed Sprints (0-41)

| Phase | Sprints | Status | Key Deliverables |
|-------|---------|--------|------------------|
| Foundation | 0-6 | ✅ | Core models, API routes, Celery, Railway deploy |
| Core Platform | 7-10 | ✅ | Command queue, operator mode, HubSpot sync |
| Expansion | 11-14 | ✅ | Twitter/Grok, PWA, mobile-first design |
| Henry Evolution | 15-18 | ✅ | Persona system, voice training, MCP server |
| Action Wiring | 19-20 | ✅ | Real API execution, MCP server |
| Documentation | 21 | ✅ | Consolidated docs, removed duplicates |
| Tech Debt | 22 | ✅ | CSRF protection, test baseline (40%), route cleanup |
| Deep Research | 23 | ✅ | Slack ingestion, memory search |
| Bug Fixes | 24-25 | ✅ | SQLAlchemy indexes, SafeJSON migration |
| HubSpot Wiring | 26-27 | ✅ | Real sync, campaigns UI, CRM enrichment |
| Polish | 28-32 | ⚠️ | Partial - some auto-approval, email validation |
| OAuth/Gemini | 33-36 | ✅ | OAuth consolidation, Gemini Portal, Drive integration, Jarvis tools |
| UX Fixes | 39A | ✅ | CSRF exclusion for Gemini, Agents nav placeholder |
| Enrichment | 39B | ✅ | Contact enrichment, queue detail, draft editing |
| Agent Discovery | 41 | ✅ | Agent Registry (33 agents), Jarvis wiring (31 agents) |

### ⏭️ Skipped/Incomplete Sprints

| Sprint | Planned Goal | Status | Gap Analysis |
|--------|--------------|--------|--------------|
| 37 | Deep Research & Workspace Intelligence | ❌ Skipped | Deep research agent file exists but not wired to UI |
| 38 | Agent Dashboard & Orchestration UI | ⚠️ Partial | Registry done in Sprint 41, but no execution tracking |
| 40 | Draft Editing & Queue Detail | ⚠️ Partial | Basic detail page done in 39B, but no deal context panel |

---

## Upcoming Sprints

> **Review Notes (from subagent audit):**
> - Sprint ordering validated: 42→43 (execution before dashboard) is correct
> - Sprint 45 (Deep Research) should use Sprint 47's memory - reordered below
> - Quick wins added: keyboard shortcuts, dark mode, queue badge
> - Risk mitigations added: Celery timeouts, migration rollbacks

---

## Sprint 42: Agent Execution Infrastructure
**Goal:** Foundation for tracking all agent executions with audit trail.  
**Demo:** Click "Run" on ProspectingAgent → see "Running..." spinner → view output JSON within 5 seconds.  
**Risk Mitigation:** Add 300s Celery task timeout to prevent hung workers.

### Task 42.1: Create AgentExecution Model
**Description:** Database model to track every agent execution.  
**Files:** `src/models/agent_execution.py`, `infra/migrations/versions/xxxx_agent_execution.py`  
**Tests:** `tests/unit/test_agent_execution_model.py`  
**Rollback:** `infra/migrations/rollback/xxxx_agent_execution_down.py`  
**Acceptance Criteria:**
- [ ] Create `AgentExecution` model: id, agent_name, domain, status (pending/running/success/failed), input_json, output_json, error_message, duration_ms, created_at, completed_at
- [ ] Use SafeJSON for input/output columns
- [ ] Add migration with indexes on (agent_name, created_at)
- [ ] Create rollback script for migration
- [ ] Commit: `feat(models): add AgentExecution tracking model`

### Task 42.2: Add Execution Service
**Description:** Service layer for creating and updating executions.  
**Files:** `src/services/execution_service.py`  
**Tests:** `tests/unit/test_execution_service.py`  
**Acceptance Criteria:**
- [ ] Create `ExecutionService` with `start_execution()`, `complete_execution()`, `fail_execution()`
- [ ] Auto-calculate duration on complete
- [ ] Add `get_recent_executions(agent_name, limit)` method
- [ ] Commit: `feat(services): add agent execution service`

### Task 42.3: Add Manual Trigger API Endpoint
**Description:** API to manually trigger any agent with custom context.  
**Files:** `src/routes/agents_api.py`  
**Tests:** `tests/unit/test_agent_trigger_api.py`  
**Acceptance Criteria:**
- [ ] Add `POST /api/agents/{name}/execute` endpoint
- [ ] Accept `context` JSON body
- [ ] Validate agent exists in registry
- [ ] Return `execution_id` for tracking
- [ ] Commit: `feat(api): add manual agent trigger endpoint`

### Task 42.4: Create Async Execution Celery Task
**Description:** Execute agents asynchronously via Celery with timeout protection.  
**Files:** `src/tasks/agent_executor.py`, `src/celery_app.py`  
**Tests:** `tests/unit/test_agent_executor_task.py`  
**Acceptance Criteria:**
- [ ] Create `execute_agent_async` Celery task with `soft_time_limit=300`
- [ ] Update execution status: pending → running → success/failed
- [ ] Capture agent output or exception
- [ ] Store in `agent_executions` table
- [ ] Handle timeout gracefully with "timed_out" status
- [ ] Commit: `feat(tasks): add async agent execution task`

### Task 42.5: Add Execution History to Agents UI
**Description:** Show recent executions on agent cards.  
**Files:** `src/templates/agents.html`, `src/routes/agents_api.py`  
**Tests:** Visual verification, `tests/e2e/test_agent_execution_flow.py`  
**Acceptance Criteria:**
- [ ] Add `GET /api/agents/{name}/history` endpoint (last 10)
- [ ] Show mini timeline on agent card
- [ ] Color-code by status (green=success, yellow=running, red=failed)
- [ ] Show timestamp and duration
- [ ] Commit: `feat(ui): add execution history to agent hub`

### Task 42.6: Add "Run Now" Button to Agent Cards
**Description:** Button to manually trigger agent from UI.  
**Files:** `src/templates/agents.html`  
**Tests:** `tests/e2e/test_agent_manual_trigger.py`  
**Acceptance Criteria:**
- [ ] Add "▶ Run" button on each agent card
- [ ] HTMX POST to `/api/agents/{name}/execute`
- [ ] Show spinner while running
- [ ] Replace with result badge on complete
- [ ] Commit: `feat(ui): add Run Now button to agent cards`

### Task 42.7: Add Execution Failure View (Quick Win from Review)
**Description:** View and retry failed agent executions.  
**Files:** `src/templates/agents.html`, `src/routes/agents_api.py`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add modal showing error message and input context
- [ ] Add "Retry" button to re-run with same context
- [ ] Add "Dismiss" button to clear from history
- [ ] Commit: `feat(ui): add execution failure view with retry`

---

## Sprint 43: Dashboard Intelligence & Metrics
**Goal:** Transform dashboard from status display to actionable intelligence center.  
**Demo:** Dashboard shows today's priority items, agent performance, pipeline health, OAuth status at a glance.

### Task 43.1: Create Dashboard Metrics Service
**Description:** Aggregate key metrics for dashboard display.  
**Files:** `src/services/dashboard_metrics.py`  
**Tests:** `tests/unit/test_dashboard_metrics.py`  
**Acceptance Criteria:**
- [ ] Create `DashboardMetricsService` with `get_today_metrics()`
- [ ] Return: pending_actions, completed_today, failed_today, agent_executions_24h
- [ ] Cache with 5-minute TTL (Redis)
- [ ] Commit: `feat(services): add dashboard metrics aggregation`

### Task 43.2: Add Priority Queue Widget
**Description:** Show top 5 priority items on dashboard.  
**Files:** `src/templates/dashboard.html`, `src/routes/dashboard_api.py`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add `GET /api/dashboard/priority-queue` endpoint
- [ ] Return top 5 by APS score with contact name
- [ ] Add widget card to dashboard
- [ ] Quick-approve buttons inline
- [ ] Add queue count badge to nav (Quick Win)
- [ ] Commit: `feat(ui): add priority queue widget to dashboard`

### Task 43.3: Add Agent Performance Widget
**Description:** Show agent success rates and activity.  
**Files:** `src/templates/dashboard.html`, `src/routes/dashboard_api.py`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add `GET /api/dashboard/agent-performance` endpoint
- [ ] Return: most_active, highest_success_rate, most_failed (last 24h)
- [ ] Add widget with mini bar charts
- [ ] Commit: `feat(ui): add agent performance widget`

### Task 43.4: Add Pipeline Health Widget
**Description:** Show deal pipeline summary with stage counts.  
**Files:** `src/templates/dashboard.html`, `src/connectors/hubspot.py`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add `GET /api/dashboard/pipeline` endpoint
- [ ] Fetch pipeline stages from HubSpot
- [ ] Show deal count per stage with total value
- [ ] Highlight at-risk deals (stale > 30 days)
- [ ] Commit: `feat(ui): add pipeline health widget`

### Task 43.5: Add Quick Stats Bar
**Description:** Compact stats bar at top of dashboard.  
**Files:** `src/templates/dashboard.html`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add horizontal stats bar below nav
- [ ] Show: Pending (count), Sent Today (count), Success Rate (%), Active Agents (count)
- [ ] Auto-refresh every 60 seconds via HTMX
- [ ] Commit: `feat(ui): add quick stats bar`

### Task 43.6: Add Recent Activity Feed
**Description:** Live feed of recent actions and executions.  
**Files:** `src/templates/dashboard.html`, `src/routes/dashboard_api.py`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add `GET /api/dashboard/activity` endpoint (last 20 events)
- [ ] Combine: queue approvals, agent executions, errors
- [ ] Add scrollable feed widget
- [ ] Include actor (agent/user) and timestamp
- [ ] Commit: `feat(ui): add recent activity feed`

### Task 43.7: Add OAuth Token Expiry Alerts (from Review)
**Description:** Warn users when OAuth tokens are expiring soon.  
**Files:** `src/templates/dashboard.html`, `src/routes/dashboard_api.py`  
**Tests:** `tests/unit/test_oauth_expiry_alert.py`  
**Acceptance Criteria:**
- [ ] Add `GET /api/dashboard/oauth-status` endpoint
- [ ] Check Gmail and HubSpot token expiry times
- [ ] Show warning banner if token expires in < 24 hours
- [ ] Link to re-authorization flow
- [ ] Commit: `feat(dashboard): add OAuth token expiry alerts`

### Task 43.8: Add Standard Error Classes (Tech Debt)
**Description:** Create consistent error handling patterns.  
**Files:** `src/exceptions.py`  
**Tests:** `tests/unit/test_exceptions.py`  
**Acceptance Criteria:**
- [ ] Create `CaseyOSException` base class
- [ ] Add: `AgentExecutionError`, `ConnectorError`, `ValidationError`
- [ ] Include error codes for API responses
- [ ] Update existing error handling to use new classes
- [ ] Commit: `feat(core): add standard exception classes`

---

## Sprint 44: Voice Training & Quick Wins
**Goal:** Enable voice/persona training plus high-value UX improvements.  
**Demo:** Navigate to Settings → Voice Training → rate samples. Use Cmd+Enter to send in Gemini.

### Task 44.0: Mobile Responsiveness Fixes (Moved from Sprint 48)
**Description:** Fix critical mobile layout issues before other features.  
**Files:** All templates  
**Tests:** Manual testing on 375px viewport  
**Acceptance Criteria:**
- [ ] Dashboard responsive at 375px width
- [ ] Navigation hamburger menu works
- [ ] Queue page scrollable, buttons tappable (44x44px minimum)
- [ ] Commit: `fix(ui): mobile responsiveness quick fixes`

### Task 44.1: Create Voice Sample Model
**Description:** Store voice training samples with ratings.  
**Files:** `src/models/voice_sample.py`, migration  
**Tests:** `tests/unit/test_voice_sample_model.py`  
**Acceptance Criteria:**
- [ ] Create `VoiceSample` model: id, content, source (email/draft/manual), rating (1-5), feedback, created_at
- [ ] Add migration
- [ ] Commit: `feat(models): add voice sample model for training`

### Task 44.2: Create Voice Training Service
**Description:** Service to collect and process voice samples.  
**Files:** `src/services/voice_training_service.py`  
**Tests:** `tests/unit/test_voice_training_service.py`  
**Acceptance Criteria:**
- [ ] Create `VoiceTrainingService`
- [ ] Add `collect_samples_from_sent()` to gather approved emails
- [ ] Add `rate_sample(id, rating, feedback)` method
- [ ] Add `get_training_corpus()` for LLM context
- [ ] Commit: `feat(services): add voice training service`

### Task 44.3: Create Voice Training UI Page
**Description:** UI page for reviewing and rating voice samples.  
**Files:** `src/templates/voice_training.html`, `src/routes/ui.py`  
**Tests:** Visual verification, `tests/e2e/test_voice_training.py`  
**Acceptance Criteria:**
- [ ] Create `GET /caseyos/settings/voice` route
- [ ] Show samples in cards with full text
- [ ] Add 1-5 star rating component
- [ ] Add feedback textarea
- [ ] Commit: `feat(ui): add voice training page`

### Task 44.4: Add Persona Preview Panel
**Description:** Show current persona summary derived from training.  
**Files:** `src/templates/voice_training.html`, `src/services/voice_training_service.py`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add `get_persona_summary()` method using LLM
- [ ] Display: tone, style, common phrases, word frequency
- [ ] Show "Update Persona" button
- [ ] Commit: `feat(ui): add persona preview panel`

### Task 44.5: Add Manual Sample Entry
**Description:** Allow users to paste exemplary emails for training.  
**Files:** `src/templates/voice_training.html`, `src/routes/voice_training_api.py`  
**Tests:** `tests/unit/test_voice_sample_submission.py`  
**Acceptance Criteria:**
- [ ] Add `POST /api/voice/samples` endpoint
- [ ] Accept content text and optional source URL
- [ ] Validate minimum length (100 chars)
- [ ] Add to training corpus
- [ ] Commit: `feat(api): add manual voice sample submission`

### Task 44.6: Integrate Training with Draft Generation
**Description:** Use training corpus when generating drafts.  
**Files:** `src/agents/content/draft_writer.py`, `src/connectors/llm.py`  
**Tests:** `tests/unit/test_draft_uses_voice_training.py`  
**Acceptance Criteria:**
- [ ] Fetch top-rated samples (rating ≥ 4)
- [ ] Include in system prompt as examples
- [ ] Add A/B toggle for "trained" vs "default" voice
- [ ] Commit: `feat(agents): integrate voice training into drafts`

### Task 44.7: Add Keyboard Shortcuts (Quick Win)
**Description:** Add keyboard shortcuts for common actions.  
**Files:** `src/templates/base.html`, `src/static/js/keyboard.js`  
**Tests:** Manual testing  
**Acceptance Criteria:**
- [ ] Cmd/Ctrl+Enter to send message in Gemini
- [ ] Cmd/Ctrl+K for command palette (search agents)
- [ ] Escape to close modals
- [ ] Add keyboard shortcut help (press ?)
- [ ] Commit: `feat(ui): add keyboard shortcuts`

### Task 44.8: Add Dark Mode Toggle (Quick Win)
**Description:** Add dark mode support with toggle in nav.  
**Files:** `src/templates/base.html`, `src/static/css/dark-mode.css`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add dark mode toggle (🌙/☀️) in nav
- [ ] Use Tailwind `dark:` classes
- [ ] Store preference in localStorage
- [ ] Respect system preference by default
- [ ] Commit: `feat(ui): add dark mode toggle`

---

## Sprint 45: Gemini Conversation Memory
**Goal:** Gemini remembers conversation context and user preferences across sessions.  
**Demo:** Ask "What's Acme's revenue?" → later ask "And their employee count?" → Gemini understands "their" refers to Acme.

> **Note:** Moved before Deep Research (was Sprint 47) because research needs memory for follow-up questions.

### Task 45.1: Create Chat Session Model
**Description:** Persistent storage for Gemini chat sessions.  
**Files:** `src/models/chat_session.py`, migration  
**Tests:** `tests/unit/test_chat_session_model.py`  
**Rollback:** Migration rollback script included  
**Acceptance Criteria:**
- [ ] Create `ChatSession` model: id, user_id, title, created_at, last_message_at
- [ ] Create `ChatMessage` model: id, session_id, role (user/assistant), content, tool_calls (SafeJSON), created_at
- [ ] Add migration with rollback script
- [ ] Commit: `feat(models): add chat session persistence`

### Task 45.2: Wire Chat Sessions to Gemini API
**Description:** Store and retrieve messages from database.  
**Files:** `src/routes/gemini_api.py`, `src/services/chat_service.py`  
**Tests:** `tests/unit/test_chat_persistence.py`, `tests/integration/test_gemini_memory_persistence.py`  
**Acceptance Criteria:**
- [ ] Create `ChatService` for CRUD operations
- [ ] Store each message after Gemini response
- [ ] Load last 10 messages on session resume
- [ ] Pass history to Gemini API
- [ ] Commit: `feat(gemini): wire persistent chat sessions`

### Task 45.3: Add Chat History Sidebar
**Description:** Show past conversations in Gemini portal.  
**Files:** `src/templates/gemini.html`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add collapsible sidebar with session list
- [ ] Show session title (auto-generated from first message)
- [ ] Click to load session
- [ ] Add "New Chat" button
- [ ] Commit: `feat(ui): add chat history sidebar`

### Task 45.4: Add Context Window Management
**Description:** Manage context window to avoid token limits.  
**Files:** `src/services/chat_service.py`  
**Tests:** `tests/unit/test_context_window.py`  
**Acceptance Criteria:**
- [ ] Count tokens in message history
- [ ] Summarize older messages when approaching limit
- [ ] Keep recent 5 messages verbatim
- [ ] Store summary as system message
- [ ] Commit: `feat(gemini): add context window management`

### Task 45.5: Add User Preference Memory
**Description:** Remember user preferences (timezone, format, etc).  
**Files:** `src/services/memory_service.py`, `src/models/user_preference.py`  
**Tests:** `tests/unit/test_user_preferences.py`  
**Acceptance Criteria:**
- [ ] Create `UserPreference` model: user_id, key, value, updated_at
- [ ] Extract preferences from conversations ("I prefer bullet points")
- [ ] Apply to future responses
- [ ] Commit: `feat(memory): add user preference extraction`

### Task 45.6: Add Session Export
**Description:** Export chat sessions to Markdown or PDF.  
**Files:** `src/routes/gemini_api.py`  
**Tests:** `tests/unit/test_session_export.py`  
**Acceptance Criteria:**
- [ ] Add `GET /api/gemini/sessions/{id}/export` endpoint
- [ ] Support `format=md` or `format=pdf`
- [ ] Include all messages with timestamps
- [ ] Return download link
- [ ] Commit: `feat(gemini): add session export`

---

## Sprint 46: Deep Research Agent & Citations
**Goal:** Enable AI-powered deep research across internal docs and web with source citations.  
**Demo:** "Research enterprise CRM competitive landscape" → report with 10+ sources, inline [1] [2] citations, clickable links.  
**Depends On:** Sprint 45 (Memory) for follow-up questions about research.  
**Risk Mitigation:** Add backoff/retry for Gemini API rate limits.

### Task 46.1: Enhance Deep Research Agent
**Description:** Upgrade research_deep.py with multi-source capability.  
**Files:** `src/agents/research/research_deep.py`  
**Tests:** `tests/unit/test_deep_research_agent.py`  
**Acceptance Criteria:**
- [ ] Add Drive file search via existing connector
- [ ] Add Gemini grounding for web search
- [ ] Structure output as sections with citations
- [ ] Return source metadata (title, URL, snippet)
- [ ] Add exponential backoff for rate limits
- [ ] Commit: `feat(research): enhance deep research with citations`

### Task 46.2: Create Research Session Model
**Description:** Store research sessions with results.  
**Files:** `src/models/research_session.py`, migration  
**Tests:** `tests/unit/test_research_session_model.py`  
**Acceptance Criteria:**
- [ ] Create `ResearchSession` model: id, query, status, results (SafeJSON), sources (SafeJSON), created_at
- [ ] Add migration
- [ ] Commit: `feat(models): add research session model`

### Task 46.3: Add Research Mode to Gemini Portal
**Description:** Toggle for "Research Mode" in Gemini chat.  
**Files:** `src/templates/gemini.html`, `src/routes/gemini_api.py`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add "🔍 Research Mode" toggle button
- [ ] When enabled, route to DeepResearchAgent
- [ ] Show progress: "Searching Drive... Searching web... Synthesizing..."
- [ ] Commit: `feat(ui): add research mode toggle to Gemini`

### Task 46.4: Add Citation Rendering Component
**Description:** Render inline citations with source links.  
**Files:** `src/templates/components/citations.html`, `src/templates/gemini.html`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Create citation partial template
- [ ] Render [1], [2] as superscript links
- [ ] Show source list at bottom of response
- [ ] Drive files link to `/caseyos/drive?file=X`
- [ ] Commit: `feat(ui): add citation rendering component`

### Task 46.5: Add Research Export
**Description:** Export research results to Google Docs or Markdown.  
**Files:** `src/routes/gemini_api.py`, `src/connectors/drive.py`  
**Tests:** `tests/unit/test_research_export.py`  
**Acceptance Criteria:**
- [ ] Add `POST /api/research/{id}/export` endpoint
- [ ] Support `format=gdoc` or `format=md`
- [ ] For gdoc, create in user's Drive
- [ ] Return download URL or file ID
- [ ] Commit: `feat(research): add export to Google Docs`

### Task 46.6: Add Research History
**Description:** Store and display past research sessions.  
**Files:** `src/templates/gemini.html`, `src/routes/gemini_api.py`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add sidebar panel for research history
- [ ] Show last 10 research queries with timestamps
- [ ] Click to reload results (no re-execution)
- [ ] Add "Delete" option per session
- [ ] Commit: `feat(ui): add research history sidebar`

---

## Sprint 47: Data Hygiene Activation
**Goal:** Activate all 5 data hygiene agents with scheduled execution and alerts.  
**Demo:** Daily hygiene report shows: 3 duplicates found, 12 contacts enriched, 2 stale records.  
**Depends On:** Sprint 42 (Agent Execution) for execution infrastructure.

### Task 47.1: Wire Data Hygiene Agents to Beat Schedule
**Description:** Add Celery beat tasks for all hygiene agents.  
**Files:** `src/celery_app.py`, `src/tasks/data_hygiene.py`  
**Tests:** `tests/unit/test_data_hygiene_tasks.py`  
**Acceptance Criteria:**
- [ ] Create `src/tasks/data_hygiene.py` with wrapper tasks
- [ ] Add `run_duplicate_watcher` (daily at 6 AM)
- [ ] Add `run_contact_validation` (daily at 6:30 AM)
- [ ] Add `run_enrichment_orchestrator` (hourly for new contacts)
- [ ] Commit: `feat(tasks): add data hygiene beat schedule`

### Task 47.2: Create Hygiene Report Model
**Description:** Store daily hygiene run results.  
**Files:** `src/models/hygiene_report.py`, migration  
**Tests:** `tests/unit/test_hygiene_report_model.py`  
**Acceptance Criteria:**
- [ ] Create `HygieneReport` model: id, report_date, duplicates_found, duplicates_merged, contacts_enriched, contacts_validated, stale_records, created_at
- [ ] Add migration with unique constraint on report_date
- [ ] Commit: `feat(models): add daily hygiene report model`

### Task 46.3: Add Hygiene Dashboard Widget
**Description:** Show hygiene health on main dashboard.  
**Files:** `src/templates/dashboard.html`, `src/routes/dashboard_api.py`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add `GET /api/dashboard/hygiene` endpoint
- [ ] Return latest HygieneReport data
- [ ] Show card with: duplicates, enrichment rate, stale count
- [ ] Color-code health (green/yellow/red)
- [ ] Commit: `feat(ui): add data hygiene dashboard widget`

### Task 47.4: Add Duplicate Review Queue
**Description:** UI to review and merge duplicate contacts.  
**Files:** `src/templates/hygiene_duplicates.html`, `src/routes/ui.py`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Create `GET /caseyos/hygiene/duplicates` route
- [ ] Show pairs of potential duplicates side-by-side
- [ ] Add "Merge", "Not Duplicate", "Ignore" buttons
- [ ] Update HubSpot via connector on merge
- [ ] Commit: `feat(ui): add duplicate review queue`

### Task 47.5: Add Stale Record Alerts
**Description:** Alert when contacts haven't been contacted in 90+ days.  
**Files:** `src/agents/data_hygiene/data_decay.py`, `src/models/alert.py`  
**Tests:** `tests/unit/test_stale_record_alerts.py`  
**Acceptance Criteria:**
- [ ] Create `Alert` model: id, type, severity, message, entity_type, entity_id, created_at, dismissed_at
- [ ] DataDecayAgent creates alerts for stale records
- [ ] Show alert badge on dashboard
- [ ] Commit: `feat(hygiene): add stale record alerts`

### Task 47.6: Add Sync Health Monitor
**Description:** Monitor HubSpot sync health and alert on issues.  
**Files:** `src/agents/data_hygiene/sync_health.py`, `src/routes/dashboard_api.py`  
**Tests:** `tests/unit/test_sync_health_monitor.py`  
**Acceptance Criteria:**
- [ ] SyncHealthAgent checks last sync timestamps
- [ ] Alert if no sync in 1+ hour
- [ ] Alert if sync error rate > 5%
- [ ] Add sync status to dashboard
- [ ] Commit: `feat(hygiene): add sync health monitoring`

### Task 47.7: Add Bulk CSV Import/Export (from Review)
**Description:** Enable bulk contact import and queue export.  
**Files:** `src/routes/bulk_api.py`  
**Tests:** `tests/unit/test_bulk_import.py`  
**Acceptance Criteria:**
- [ ] Add `POST /api/contacts/import` for CSV upload
- [ ] Add `GET /api/queue/export` for CSV download
- [ ] Validate CSV format and headers
- [ ] Show import progress and errors
- [ ] Commit: `feat(data): add bulk CSV import/export`

---

## Sprint 48: Mobile UX & Accessibility
**Goal:** Optimize CaseyOS for mobile devices and accessibility standards.  
**Demo:** Use CaseyOS on phone → queue approval works → screen reader navigable.  
**Test Matrix:** Test on Safari iOS, Chrome Android, BrowserStack.

### Task 48.1: Advanced Touch Controls
**Description:** Add swipe gestures for queue actions.  
**Files:** `src/templates/queue.html`, `src/static/js/mobile.js`  
**Tests:** Manual testing on iOS/Android  
**Acceptance Criteria:**
- [ ] Swipe left to reject, right to approve on queue items
- [ ] Add visual swipe indicators
- [ ] Haptic feedback on action (if supported)
- [ ] Commit: `feat(ui): add swipe gestures for queue`

### Task 48.2: Add ARIA Labels and Roles
**Description:** Add accessibility attributes for screen readers.  
**Files:** All templates  
**Tests:** Lighthouse accessibility audit  
**Acceptance Criteria:**
- [ ] All images have alt text
- [ ] All buttons have aria-label
- [ ] Form inputs have labels
- [ ] Modals have aria-modal and focus trap
- [ ] Commit: `feat(a11y): add ARIA labels throughout`

### Task 48.4: Add Keyboard Navigation
**Description:** Enable full keyboard navigation.  
**Files:** `src/static/js/keyboard.js`, templates  
**Tests:** Manual testing  
**Acceptance Criteria:**
- [ ] Tab order is logical
- [ ] Enter/Space activates buttons
- [ ] Escape closes modals
- [ ] Arrow keys navigate lists
- [ ] Commit: `feat(a11y): add keyboard navigation`

### Task 48.5: Add High Contrast Mode
**Description:** Toggle for high contrast color scheme.  
**Files:** `src/static/css/high-contrast.css`, `src/templates/base.html`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add contrast toggle in nav
- [ ] Store preference in localStorage
- [ ] Meet WCAG AA contrast ratios
- [ ] Commit: `feat(a11y): add high contrast mode`

### Task 48.6: Add Loading States & Skeletons
**Description:** Add loading indicators for async content.  
**Files:** All templates with HTMX  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] All HTMX requests show spinner
- [ ] Skeleton loaders for cards during load
- [ ] Disable buttons while loading
- [ ] Show error state on failure
- [ ] Commit: `feat(ui): add loading states and skeletons`

---

## Sprint 49: Pipeline Intelligence & Forecasting
**Goal:** AI-powered pipeline insights, deal scoring, and revenue forecasting.  
**Demo:** Dashboard shows: "$120K at risk this month", top deals to prioritize, win probability.

### Task 49.1: Create Deal Scoring Model
**Description:** ML model for deal win probability.  
**Files:** `src/services/deal_scoring_service.py`, `src/models/deal_score.py`  
**Tests:** `tests/unit/test_deal_scoring.py`  
**Acceptance Criteria:**
- [ ] Create `DealScore` model: deal_id, score (0-100), factors (SafeJSON), calculated_at
- [ ] Implement rule-based scoring (engagement, stage, age, amount)
- [ ] Add `calculate_score(deal_id)` method
- [ ] Commit: `feat(pipeline): add deal scoring model`

### Task 49.2: Add Deal Risk Indicators
**Description:** Identify at-risk deals based on activity.  
**Files:** `src/agents/ops/deal_risk_analyzer.py`  
**Tests:** `tests/unit/test_deal_risk.py`  
**Acceptance Criteria:**
- [ ] Create `DealRiskAnalyzer` agent
- [ ] Flag deals with no activity > 14 days
- [ ] Flag deals past expected close date
- [ ] Flag deals with declining engagement
- [ ] Commit: `feat(pipeline): add deal risk analysis`

### Task 49.3: Create Forecast Model
**Description:** Monthly/quarterly revenue forecasting.  
**Files:** `src/services/forecast_service.py`, `src/models/forecast.py`  
**Tests:** `tests/unit/test_forecast.py`  
**Acceptance Criteria:**
- [ ] Create `Forecast` model: period, predicted_revenue, weighted_pipeline, confidence
- [ ] Calculate weighted pipeline (amount × probability)
- [ ] Compare to quota if available
- [ ] Commit: `feat(pipeline): add revenue forecasting`

### Task 49.4: Add Pipeline Dashboard Widget
**Description:** Visual pipeline funnel with intelligence.  
**Files:** `src/templates/dashboard.html`  
**Tests:** Visual verification  
**Acceptance Criteria:**
- [ ] Add funnel visualization by stage
- [ ] Show deal count and value per stage
- [ ] Highlight at-risk deals in red
- [ ] Show forecast vs quota
- [ ] Commit: `feat(ui): add pipeline intelligence widget`

### Task 49.5: Add Deal Recommendations
**Description:** AI-generated next actions for deals.  
**Files:** `src/agents/ops/deal_advisor.py`  
**Tests:** `tests/unit/test_deal_recommendations.py`  
**Acceptance Criteria:**
- [ ] Create `DealAdvisor` agent
- [ ] Analyze deal context and history
- [ ] Generate 2-3 recommended actions
- [ ] Integrate with command queue
- [ ] Commit: `feat(pipeline): add deal recommendations`

### Task 49.6: Add Weekly Pipeline Digest
**Description:** Weekly email summary of pipeline health.  
**Files:** `src/tasks/pipeline_digest.py`  
**Tests:** `tests/unit/test_pipeline_digest.py`  
**Acceptance Criteria:**
- [ ] Create Celery task for weekly digest
- [ ] Summarize: new deals, closed won/lost, at-risk, forecast
- [ ] Send via Gmail connector
- [ ] Schedule Sunday 8 PM
- [ ] Commit: `feat(pipeline): add weekly digest email`

---

## Test Strategy

### Unit Test Requirements
- Every model: CRUD operations, validations
- Every service: Core methods with mocks
- Every agent: Input validation, happy path execution

### Integration Test Requirements
- API endpoints with real database
- Celery tasks with Redis
- External connectors with mocked responses

### E2E Test Requirements
- Critical user flows (queue approval, draft editing, agent execution)
- Mobile viewport testing (Sprint 44, 48)
- Accessibility compliance (Sprint 48)

### Coverage Requirements
- Maintain 40% baseline
- New code must have 80%+ coverage
- Critical paths (auth, data sync) 100%
- Target: 45% by Sprint 43 (tech debt task)

---

## Risk Factors & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gemini API rate limits | Sprint 46 (Research) blocked | Add exponential backoff, request batching |
| OAuth token key rotation | All users lose access | Document key rotation procedure in Sprint 47 |
| Mobile Safari HTMX bugs | Sprint 48 delays | Test on BrowserStack early, add Safari to E2E |
| Migration failures in prod | Data corruption | Add rollback scripts to every migration |
| Agent execution timeouts | Hung Celery workers | 300s soft_time_limit on all agent tasks |
| Test suite duration | CI > 10 minutes | Parallelize tests, split E2E to separate job |

---

## Technical Debt Backlog

| ID | Description | Effort | Priority | Target Sprint |
|----|-------------|--------|----------|---------------|
| TD-1 | Migrate remaining inline HTML to templates | M | Medium | Backlog |
| TD-2 | Add type hints to `src/campaigns.py` | S | Low | Backlog |
| TD-3 | Consolidate duplicate HubSpot API calls | M | Medium | 47 |
| TD-4 | Add request ID tracing for debugging | S | Medium | 43 |
| TD-5 | Upgrade to Pydantic v2 | L | Low | Backlog |
| TD-6 | Add database query logging for slow queries | S | High | 43 |
| TD-7 | Implement proper connection pooling limits | S | High | 42 |
| TD-8 | Add API rate limiting per user | M | Medium | 48 |
| TD-9 | Add mypy to CI (prevent new type errors) | S | Medium | 42 |
| TD-10 | Standard exception classes | S | High | 43 |

---

## Appendix: Agent Inventory (31 Wired)

### Sales Domain (13)
- ProspectingAgent, NurturingAgent, AccountAnalyzerAgent, ValidationAgent
- PersonaRouterAgent, AgendaGeneratorAgent, DemoAgent
- PricingCalculatorAgent, ProposalGeneratorAgent, ContractReviewAgent
- CompetitorWatchAgent, RevenueOpsAgent, PartnerCoordinatorAgent

### Content Domain (4)
- RepurposeAgent, RepurposeV2Agent, SocialSchedulerAgent, GraphicsRequestAgent

### Research Domain (2)
- StandardResearchAgent, DeepResearchAgent

### Fulfillment Domain (3)
- ClientHealthAgent, DeliverableTrackerAgent, ApprovalGatewayAgent

### Contracts Domain (3)
- PricingCalculatorAgent, ProposalGeneratorAgent, ContractReviewAgent

### Ops Domain (3)
- CompetitorWatchAgent, RevenueOpsAgent, PartnerCoordinatorAgent

### Data Hygiene Domain (5)
- ContactValidationAgent, DuplicateWatcherAgent, EnrichmentOrchestratorAgent
- DataDecayAgent, SyncHealthAgent

---

## 🏗️ Architecture Pillars

### 1. The Brain (Orchestrator)
- **Jarvis (`src/agents/jarvis.py`)**: Master router.
- **Memory (`src/models/content.py`)**: Vector store for contextual recall.

### 2. The Body (API & Tasks)
- **FastAPI**: Async first.
- **Celery**: Long-running research/analysis tasks.
- **Postgres**: Application state + `pgvector` for memory.

### 3. The Face (UI)
- **Jinja2**: Server-side layout composition.
- **Tailwind**: Utility-first styling.
- **HTMX**: Hypermedia interactions (low-JS).

---

## 🛠️ Definition of Done (Global)
1.  **Tested:** Unit tests pass, Integration tests pass.
2.  **Verified:** `scripts/verify_ui.py` returns 200 OK.
3.  **Documented:** Sprint Completion Doc updated.
4.  **Deployed:** Pushed to `main` and healthy on Railway.

---

*Generated: January 2026*  
*Version: 3.0*  
*Supersedes: SPRINT_ROADMAP_V2.md (legacy)*
