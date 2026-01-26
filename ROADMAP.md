# CaseyOS Roadmap 2026

**Version:** 3.0 (Post-Sprint 23)
**Vision:** Autonomous GTM Command Center ("Dude What's The Bid?!")

---

## 🟢 Operational State (Current)
- **Deployment:** Railway (Production)
- **Core Engine:** FastAPI + Postgres + Redis/Celery
- **Agents Active:**
    - `SalesAgent` (Prospecting/Nurturing)
    - `ContentRepurposeAgent` (YouTube/Slack -> Content)
    - `DeepResearchAgent` (Drive/Docs context injection)
- **Integrations:** Gmail, HubSpot, Calendar, Slack (Ingest), YouTube.

---

## 📅 Sprint Schedule

### ✅ Sprint 23: Content Engine & Deep Research
**Status:** COMPLETE
- **Delivered:** Slack Ingestion, Deep Research with Drive Context, Content Repurposing pipeline.

---

### [You Are Here]
### 🚧 Sprint 24: UI/UX Modernization (The "Face")
**Goal:** Unified Architecture & Technical Debt Payment.
**Focus:** Jinja2 Templating, Shared Components, Design System.
1.  **Architecture:** Implement `Jinja2Templates` for Server-Side Rendering.
2.  **Unification:** Merge `static/jarvis.html` and `static/command-queue.html` into a shared `base.html` shell.
3.  **Cleanup:** Remove legacy Python-generated HTML routes.
4.  **UX:** Standardize Navigation and "Toast" notifications.

---

### Sprint 25: API Refactoring (The "Spine")
**Goal:** Massive reduction of technical debt.
**Focus:** Route Cleanup, Security, Documentation.
1.  **Route Audit:** Review 197+ route files. Delete ~100 stub/scaffolding files.
2.  **Consolidation:** Merge scattered domain logic (e.g., 5 scheduling files -> 1 resource).
3.  **Security:** Ensure CSRF and Auth checks on all remaining endpoints.
4.  **Docs:** Generate fresh OpenAPI specs and `API_INTERFACE.md`.

---

### Sprint 26: Proactive Command Center (The "Voice")
**Goal:** Mobile access & Push notifications.
**Focus:** Twilio, SMS, PWA Polish.
1.  **Twilio Integration:** SMS send/receive webhooks.
2.  **Morning Briefing V2:** Push "Today's Moves" via SMS at 8 AM.
3.  **Action Approvals:** "Reply 'Y' to send draft" via SMS.
4.  **Mobile View:** Polish `base.html` responsive classes for valid PWA feel.

---

### Sprint 27: Business Domain Activation (The "Hands")
**Goal:** Deep workflow integration for Pesti/Yardflow.
**Focus:** Slack Ops, Client Agents.
1.  **Slack Ops:** `/caseyos` slash commands for status/execution.
2.  **Client Agents:** Specialized logic for `PestiOpsAgent` and `YardflowOpsAgent`.
3.  **Reporting:** Automated weekly summaries via Email/Slack.

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
