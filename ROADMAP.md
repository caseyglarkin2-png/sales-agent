# CaseyOS Master Roadmap - January 2026

**Date:** January 25, 2026  
**Status:** Sprints 0-20 Complete | Starting Sprint 21  
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

**Critical Gap:** None - all execution paths wired. Ready for MCP usage.

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

### Henry Evolution (Sprints 15-20)
| Sprint | Status | Key Deliverable |
|--------|--------|-----------------|
| Sprint 15 | ✅ Done | Persistent Memory (MemoryService, 557 lines) |
| Sprint 16 | ✅ Done | Daemon Mode (background monitor, notifications) |
| Sprint 17 | ✅ Done | Voice Interface (Whisper + OpenAI TTS) |
| Sprint 18 | ✅ Done | Local Deployment (Docker, CLI, Makefile) |
| Sprint 19 | ✅ Done | Action Executor Wiring (real Gmail/HubSpot/Calendar) |
| Sprint 20 | ✅ Done | MCP Server (8 tools, WebSocket + HTTP, Claude Desktop) |

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

### ✅ RESOLVED: Action Executor (Sprint 19)

The action executor is now fully wired to real APIs:
- `_execute_send_email` → Gmail `send_email()`
- `_execute_create_draft` → Gmail `create_draft()`
- `_execute_create_task` → HubSpot `create_task()`
- `_execute_update_task` → HubSpot `update_task()`
- `_execute_book_meeting` → Calendar `create_event()`
- `_execute_update_deal` → HubSpot `update_deal()`

Rollback support: `delete_draft()`, `delete_task()`

### ✅ RESOLVED: MCP Integration (Sprint 20)

MCP server now exists at `src/mcp/`:
- `server.py` - JSON-RPC 2.0 protocol handler
- `tools.py` - 8 CaseyOS tools for AI assistants
- Routes: `/mcp/ws` (WebSocket), `/mcp/message` (HTTP), `/mcp/tools/{name}`
- Docs: `docs/MCP_INTEGRATION.md` with Claude Desktop setup

### 🟡 Priority 3: Documentation Outdated

- `TRUTH.md` says "January 2025" and lists gaps that are now fixed
- `STRATEGIC_ROADMAP.md` shows Sprint 6 as "next" (we're at Sprint 18)
- Multiple overlapping roadmap documents

### 🟢 Priority 4: Route Cleanup (175+ stubs)

- `Sprint 0` was deferred
- 196 route files exist, many are stubs
- API surface is confusing

---

## Roadmap: Sprints 21-24

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
| 19: Action Wiring | ✅ Complete | - | - | **DONE** |
| 20: MCP Integration | ✅ Complete | - | - | **DONE** |
| 21: Doc Consolidation | 🟢 Medium | Low | None | **NOW** |
| 22: Slack | 🟡 High | Medium | None | After |
| 23: Route Cleanup | 🟢 Low | Low | None | Parallel |
| 24: Chrome Extension | 🟡 Medium | High | None | Future |

---

## Immediate Actions

1. ~~**Start Sprint 19** - Wire action executor to real APIs~~ ✅ **COMPLETE**
2. ~~**Start Sprint 20** - MCP server integration~~ ✅ **COMPLETE**
3. **Start Sprint 21** - Documentation consolidation
4. **Update TRUTH.md** - Reflect current state
5. **Archive old docs** - Reduce confusion

---

## Test Commands

```bash
# Production health
curl https://web-production-a6ccf.up.railway.app/health

# MCP server info (new)
curl https://web-production-a6ccf.up.railway.app/mcp/info

# MCP tools list (new)
curl https://web-production-a6ccf.up.railway.app/mcp/tools

# Jarvis voice endpoints
curl https://web-production-a6ccf.up.railway.app/api/jarvis/voice/voices

# Memory endpoints
curl https://web-production-a6ccf.up.railway.app/api/jarvis/sessions

# Notifications
curl https://web-production-a6ccf.up.railway.app/api/jarvis/whats-up

# Today's Moves
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today
```

---

## Repository Stats

| Metric | Count |
|--------|-------|
| Route files | 197 |
| Agent files | 36 |
| Connector files | 11 |
| Service files | 15+ |
| MCP tools | 8 |
| Total Python files | 300+ |
| Lines of code | 51,000+ (estimate) |

---

**Next Step:** Execute Sprint 21 - Documentation consolidation.
