# CaseyOS Master Roadmap - January 2026

**Date:** January 25, 2026  
**Status:** Sprints 0-18 Complete | Starting Sprint 19  
**Production:** https://web-production-a6ccf.up.railway.app

---

## Executive Summary

CaseyOS has evolved from a basic sales-agent into a comprehensive GTM Command Center with:
- ✅ 36 AI agents across 5 domains
- ✅ 196 API route files
- ✅ Persistent memory with semantic search
- ✅ Daemon mode with proactive notifications
- ✅ Voice interface (Whisper + TTS)
- ✅ Local deployment support

**Critical Gap:** Action executor has 8 TODOs - "Execute" button doesn't perform real actions.

---

## Completed Sprints Inventory

### Foundation (Sprints 0-6)
| Sprint | Status | Key Deliverable |
|--------|--------|-----------------|
| Sprint 0 | ✅ Done | Route cleanup (deferred, routes still exist) |
| Sprint 1 | ✅ Done | Email send capability (Gmail API) |
| Sprint 2 | ✅ Done | Async processing (Celery + DLQ) |
| Sprint 4 | ✅ Done | Auto-approval rules engine |
| Sprint 6 | ✅ Done | Production hardening (CSRF, admin auth, Sentry) |

### Core Platform (Sprints 7-10)
| Sprint | Status | Key Deliverable |
|--------|--------|-----------------|
| Sprint 7 | ✅ Done | Command Queue (Today's Moves, APS scoring) |
| Sprint 8 | ✅ Done | Signal Framework (5 sources, auto-ingest) |
| Sprint 9 | ✅ Done | Action Executor (dry-run, guardrails) |
| Sprint 10 | ✅ Done | Outcome Tracking (18 types, closed-loop) |

### Expansion (Sprints 11-14)
| Sprint | Status | Key Deliverable |
|--------|--------|-----------------|
| Sprint 11-12 | ✅ Done | CaseyOS Dashboard + GTM Domain Expansion |
| Sprint 13 | ✅ Done | Twitter/Grok integration |
| Sprint 14 | ✅ Done | Mobile PWA support |

### Henry Evolution (Sprints 15-18)
| Sprint | Status | Key Deliverable |
|--------|--------|-----------------|
| Sprint 15 | ✅ Done | Persistent Memory (MemoryService, 557 lines) |
| Sprint 16 | ✅ Done | Daemon Mode (background monitor, notifications) |
| Sprint 17 | ✅ Done | Voice Interface (Whisper + OpenAI TTS) |
| Sprint 18 | ✅ Done | Local Deployment (Docker, CLI, Makefile) |

---

## Current Capabilities

### Agents (36 files across 5 domains)

**Sales Domain:**
- ProspectingAgent, NurturingAgent, ResearchAgent
- ValidationAgent, PersonaRouter, AccountAnalyzer
- AgendaGenerator, OutcomeReporter

**Content Domain (`src/agents/content/`):**
- ContentRepurposeAgent, SocialSchedulerAgent

**Fulfillment Domain (`src/agents/fulfillment/`):**
- DeliverableTrackerAgent, ApprovalGatewayAgent, ClientHealthAgent

**Contracts Domain (`src/agents/contracts/`):**
- ProposalGeneratorAgent, ContractReviewAgent, PricingCalculatorAgent

**Operations Domain (`src/agents/ops/`):**
- CompetitorWatchAgent, RevenueOpsAgent, PartnerCoordinatorAgent

**Data Hygiene Domain (`src/agents/data_hygiene/`):**
- SyncHealthAgent, ContactValidationAgent, EnrichmentOrchestrator
- DataDecayAgent, DuplicateWatcherAgent

**Master Orchestrator:**
- Jarvis (`src/agents/jarvis.py`) - Routes to all domain agents

### Connectors (11 integrations)

| Connector | File | Status |
|-----------|------|--------|
| Gmail | `gmail.py` | ✅ Read/write/send |
| HubSpot | `hubspot.py` | ✅ Full CRM sync |
| Calendar | `calendar_connector.py` | ✅ Availability checking |
| Drive | `drive.py` | ✅ Asset hunting |
| OpenAI | `llm.py` | ✅ GPT-4 integration |
| Gemini | `gemini.py` | ✅ Alternative LLM |
| Grok | `grok.py` | ✅ Twitter AI |
| Twitter | `twitter.py` | ✅ Social posting |
| Google Docs | `google_docs.py` | ⚠️ Partial |

### Services (New in Sprints 15-18)

| Service | File | Purpose |
|---------|------|---------|
| MemoryService | `memory_service.py` | Persistent conversation memory |
| NotificationService | `notification_service.py` | Proactive alerts |
| VoiceService | `voice_service.py` | Whisper + TTS |

### API Surface (196 route files)

Key endpoint groups:
- `/api/jarvis/*` - AI gateway + voice + memory
- `/api/command-queue/*` - Today's Moves + APS
- `/api/signals/*` - Signal ingestion
- `/api/actions/*` - Action execution
- `/api/outcomes/*` - Outcome tracking
- `/caseyos/*` - Dashboard UI

---

## Critical Gaps

### 🔴 Priority 1: Action Executor TODOs

**File:** `src/actions/executor.py`

| Line | TODO | Impact |
|------|------|--------|
| 335 | `_execute_send_email` | Can't actually send emails |
| 364 | `_execute_create_draft` | Can't create Gmail drafts |
| 393 | `_execute_create_task` | Can't create HubSpot tasks |
| 423 | `_execute_update_task` | Can't update tasks |
| 439 | `_execute_book_meeting` | Can't book calendar events |
| 473 | `_execute_update_deal` | Can't update HubSpot deals |
| 237 | Rollback: Gmail draft deletion | Can't rollback drafts |
| 243 | Rollback: HubSpot task deletion | Can't rollback tasks |

**Impact:** "Execute" button in CaseyOS dashboard does nothing real.

### 🟡 Priority 2: MCP Integration (Not Started)

Per `docs/CASEYOS_HENRY_EVOLUTION.md` Sprint 19-20:
- No `src/mcp/` directory exists
- CaseyOS can't be used as Claude MCP server
- Blocks desktop AI assistant use case

### 🟡 Priority 3: Documentation Outdated

- `TRUTH.md` says "January 2025" and lists gaps that are now fixed
- `STRATEGIC_ROADMAP.md` shows Sprint 6 as "next" (we're at Sprint 18)
- Multiple overlapping roadmap documents

### 🟢 Priority 4: Route Cleanup (175+ stubs)

- `Sprint 0` was deferred
- 196 route files exist, many are stubs
- API surface is confusing

---

## Roadmap: Sprints 19-24

### Sprint 19: Action Executor Wiring (5 days)
**Goal:** "Execute" button performs real actions

**Tasks:**
1. Wire `_execute_send_email` to `gmail.py` `send_message()`
2. Wire `_execute_create_draft` to `gmail.py` `create_draft()`
3. Wire `_execute_create_task` to `hubspot.py` task creation
4. Wire `_execute_update_task` to `hubspot.py` task update
5. Wire `_execute_book_meeting` to `calendar_connector.py` event creation
6. Wire `_execute_update_deal` to `hubspot.py` deal update
7. Implement rollback handlers (draft deletion, task deletion)
8. Add execution audit to database (persistent log)
9. E2E test: Execute → verify action in external system

**Validation:**
```bash
# Create test queue item, execute, verify in Gmail/HubSpot
curl -X POST .../api/actions/execute?action_id=xxx
# Verify email appears in Gmail Sent folder
```

**Acceptance:**
- [ ] Send email action creates real Gmail message
- [ ] Create task action creates real HubSpot task
- [ ] Book meeting action creates real Calendar event
- [ ] Rollback reverses actions
- [ ] Audit trail persists to database

---

### Sprint 20: MCP Server Integration (5 days)
**Goal:** CaseyOS usable as Claude MCP tool server

**Tasks:**
1. Create `src/mcp/__init__.py`
2. Create `src/mcp/server.py` - MCP protocol handler
3. Create `src/mcp/tools.py` - Tool definitions
4. Expose tools:
   - `read_queue` - Get Today's Moves
   - `execute_action` - Perform action
   - `search_contacts` - Find HubSpot contacts
   - `create_draft` - Create email draft
   - `get_notifications` - Get proactive alerts
5. Add MCP endpoint to FastAPI (`/mcp`)
6. Test with MCP Inspector
7. Document Claude Desktop setup

**Validation:**
```bash
# Start MCP server
python -m src.mcp.server

# Use MCP Inspector to test
npx @anthropics/mcp-inspector http://localhost:8000/mcp
```

**Acceptance:**
- [ ] MCP server starts without errors
- [ ] Claude Desktop can connect
- [ ] Tools execute correctly
- [ ] Responses follow MCP protocol

---

### Sprint 21: Documentation Consolidation (3 days)
**Goal:** Single source of truth

**Tasks:**
1. Update `TRUTH.md` with January 2026 reality
2. Archive outdated docs to `archive/old_docs/`
3. Create single `ROADMAP.md` (consolidate 5+ roadmap files)
4. Update `IMPLEMENTATION_INDEX.md` to Sprint 18+
5. Delete redundant sprint completion docs
6. Create `CHANGELOG.md` with all sprints

**Deliverable:**
- `TRUTH.md` - What works NOW
- `ROADMAP.md` - Future plans
- `CHANGELOG.md` - History
- `archive/` - Old documentation

---

### Sprint 22: Slack Integration (4 days)
**Goal:** CaseyOS notifications in Slack

**Tasks:**
1. Create `src/connectors/slack.py`
2. Add Slack OAuth flow
3. Add notification channel to NotificationService
4. Create Slack commands:
   - `/caseyos status` - Today's Moves summary
   - `/caseyos execute [id]` - Execute action
   - `/caseyos voice [query]` - Ask Jarvis
5. Add Slack webhook for incoming signals

**Acceptance:**
- [ ] Slack app installed in workspace
- [ ] Notifications post to channel
- [ ] Slash commands work
- [ ] Bidirectional communication

---

### Sprint 23: Route Cleanup (Sprint 0 Redux) (3 days)
**Goal:** Clean API surface

**Tasks:**
1. Audit 196 route files for functionality
2. Delete files with only `raise NotImplementedError`
3. Consolidate related routes
4. Update OpenAPI docs
5. Create route inventory document

**Expected:**
- Reduce from 196 to ~50 essential routes
- Clear API documentation
- No dead code

---

### Sprint 24: Chrome Extension (5 days)
**Goal:** CaseyOS in browser

**Tasks:**
1. Create `chrome-extension/` directory
2. Build manifest v3 extension
3. Add sidebar panel with Today's Moves
4. Add page context injection (email compose assist)
5. Add keyboard shortcuts
6. Publish to Chrome Web Store (unlisted)

**Acceptance:**
- [ ] Extension installs
- [ ] Shows Today's Moves
- [ ] Can execute actions
- [ ] Works on Gmail pages

---

## Priority Matrix

| Sprint | Business Impact | Effort | Dependencies | Priority |
|--------|----------------|--------|--------------|----------|
| 19: Action Wiring | 🔴 Critical | Medium | None | **NOW** |
| 20: MCP Integration | 🟡 High | Medium | Sprint 19 | Next |
| 21: Doc Consolidation | 🟢 Medium | Low | None | Parallel |
| 22: Slack | 🟡 High | Medium | Sprint 19 | After |
| 23: Route Cleanup | 🟢 Low | Low | None | Parallel |
| 24: Chrome Extension | 🟡 Medium | High | Sprint 19 | Future |

---

## Immediate Actions

1. **Start Sprint 19** - Wire action executor to real APIs
2. **Update TRUTH.md** - Reflect current state
3. **Archive old docs** - Reduce confusion
4. **Verify production** - Test new voice endpoints

---

## Test Commands

```bash
# Production health
curl https://web-production-a6ccf.up.railway.app/health

# Jarvis voice endpoints (new)
curl https://web-production-a6ccf.up.railway.app/api/jarvis/voice/voices

# Memory endpoints (new)
curl https://web-production-a6ccf.up.railway.app/api/jarvis/sessions

# Notifications (new)
curl https://web-production-a6ccf.up.railway.app/api/jarvis/whats-up

# Today's Moves
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today
```

---

## Repository Stats

| Metric | Count |
|--------|-------|
| Route files | 196 |
| Agent files | 36 |
| Connector files | 11 |
| Service files | 15+ |
| Total Python files | 300+ |
| Lines of code | 50,000+ (estimate) |

---

**Next Step:** Execute Sprint 19 Task 1 - Wire `_execute_send_email` to Gmail API.
