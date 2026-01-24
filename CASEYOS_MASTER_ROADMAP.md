# CaseyOS Master Roadmap

**Version:** 2.0  
**Date:** January 24, 2026  
**Status:** Living Document - Single Source of Truth

---

## Executive Summary

CaseyOS is a **production-ready GTM command center** with:
- ✅ 150+ API endpoints
- ✅ 25+ AI agents
- ✅ Full HubSpot, Gmail, Calendar integration
- ✅ Twitter/X + xAI Grok integration
- ✅ Today's Moves command queue with APS scoring
- ✅ Form → Draft → Approval workflow

**Current State:** Core platform complete. Ready for distribution expansion.

**Next Phase:** Multi-platform presence (Mobile, Slack, Chrome, Gmail Add-on)

---

## Sprint History (Completed)

| Sprint | Status | Description |
|--------|--------|-------------|
| **Sprint 0** | ✅ Complete | Database schema, base infrastructure |
| **Sprint 1** | ✅ Complete | Email send capability (MIME, threading) |
| **Sprint 2** | ✅ Complete | Async processing (Celery, webhooks) |
| **Sprint 4** | ✅ Complete | Auto-approval rules engine |
| **Sprint 6** | ✅ Complete | Production hardening (security, CSRF, rate limits) |
| **Sprint 7** | ✅ Complete | Command queue v1, APS scoring |
| **Sprint 8** | ✅ Complete | Signal framework, HubSpot polling |
| **Sprint 9** | ✅ Complete | Action execution with guardrails |
| **Sprint 10** | ✅ Complete | Outcome tracking, closed-loop learning |
| **Sprint 11-12** | ✅ Complete | GTM agents, domain expansion |
| **Sprint 13** | ✅ Complete | Twitter/X + Grok integration |

---

## Current Platform Inventory

### UI Pages (12)

| Page | URL | Mobile Ready | Status |
|------|-----|--------------|--------|
| CaseyOS Dashboard | `/caseyos` | 🟡 Partial | Working |
| Today's Moves | `/static/command-queue.html` | 🟡 Partial | Working |
| Jarvis Voice | `/static/jarvis.html` | 🟡 Partial | Text only (no audio) |
| Agent Hub | `/static/agent-hub.html` | 🔴 No | Working |
| Operator Dashboard | `/static/operator-dashboard.html` | 🔴 No | Working |
| Voice Training | `/static/voice-training.html` | 🔴 No | Working |
| Voice Profiles | `/static/voice-profiles.html` | 🔴 No | Working |
| Integrations | `/static/integrations.html` | 🔴 No | Working |
| Queue Item Detail | `/static/queue-item-detail.html` | 🔴 No | Working |
| Admin | `/static/admin.html` | 🔴 No | Working |
| Agents | `/static/agents.html` | 🔴 No | Working |
| Index | `/static/index.html` | 🔴 No | Landing page |

### Connectors (10)

| Connector | File | Status |
|-----------|------|--------|
| Gmail | `src/connectors/gmail.py` | ✅ Full (OAuth, drafts, send) |
| HubSpot | `src/connectors/hubspot.py` | ✅ Full (CRM sync, webhooks) |
| Calendar | `src/connectors/calendar.py` | ✅ Working (availability) |
| Drive | `src/connectors/drive.py` | ✅ Working (asset search) |
| LLM (OpenAI) | `src/connectors/llm.py` | ✅ Working |
| Gemini | `src/connectors/gemini.py` | ✅ Working |
| Grok (xAI) | `src/connectors/grok.py` | ✅ Working |
| Twitter | `src/connectors/twitter.py` | ✅ Working |
| Google Docs | `src/connectors/google_docs.py` | ✅ Working |
| **Slack** | `src/connectors/slack.py` | 🔴 **MISSING** |

### Agents (25+)

| Domain | Agents | Status |
|--------|--------|--------|
| **Core** | Jarvis (orchestrator), ProspectingAgent, NurturingAgent, ResearchAgent | ✅ Working |
| **Specialized** | ThreadReaderAgent, LongMemoryAgent, AssetHunterAgent, MeetingSlotAgent, NextStepPlannerAgent, DraftWriterAgent | ✅ Working |
| **Content** | ContentRepurposeAgent, SocialSchedulerAgent, GraphicsRequestAgent | ✅ Working |
| **Fulfillment** | DeliverableTrackerAgent, ApprovalGatewayAgent, ClientHealthAgent | ✅ Working |
| **Contracts** | ProposalGeneratorAgent, ContractReviewAgent, PricingCalculatorAgent | ✅ Working |
| **Ops** | CompetitorWatchAgent, RevenueOpsAgent, PartnerCoordinatorAgent, MarketTrendMonitorAgent | ✅ Working |
| **Data Hygiene** | ContactValidationAgent, DuplicateWatcherAgent, DataDecayAgent, EnrichmentOrchestratorAgent, SyncHealthAgent | ✅ Working |
| **Validation** | ValidationAgent, PersonaRouter | ✅ Working |

### Signal Sources (5)

| Source | Processor | Status |
|--------|-----------|--------|
| Form Submissions | FormSubmissionSignalProcessor | ✅ Working |
| HubSpot | HubSpotDealSignalProcessor | ✅ Working |
| Gmail | GmailReplySignalProcessor | ✅ Working |
| Twitter | SocialSignalProcessor | ✅ Working |
| Manual | - | ✅ Working |

---

## Roadmap: Sprints 14-24

### Phase 1: Multi-Platform Distribution (Sprints 14-17)

#### Sprint 14: Mobile-First PWA
**Goal:** CaseyOS works beautifully on mobile devices  
**Duration:** 5 days

| Task | Description | Effort |
|------|-------------|--------|
| 14.1 | Add PWA manifest + service worker | 2h |
| 14.2 | Add install prompt and splash screen | 1h |
| 14.3 | Redesign CaseyOS dashboard for mobile | 4h |
| 14.4 | Add bottom navigation (mobile) | 2h |
| 14.5 | Implement touch-friendly action buttons | 2h |
| 14.6 | Add pull-to-refresh on Today's Moves | 1h |
| 14.7 | Optimize queue cards for thumb zones | 2h |
| 14.8 | Add offline support (cache Today's Moves) | 3h |
| 14.9 | Test on iOS Safari, Android Chrome | 2h |
| 14.10 | Add push notification support | 3h |

**Deliverable:** Install CaseyOS as app on phone, use Today's Moves with one thumb

---

#### Sprint 15: Slack Integration
**Goal:** CaseyOS notifications and actions in Slack  
**Duration:** 5 days

| Task | Description | Effort |
|------|-------------|--------|
| 15.1 | Create `src/connectors/slack.py` - OAuth 2.0 | 3h |
| 15.2 | Add `/api/slack/oauth/callback` route | 1h |
| 15.3 | Create `/api/slack/events` webhook handler | 2h |
| 15.4 | Implement `/api/slack/commands` for slash commands | 2h |
| 15.5 | Add `/todays-moves` slash command | 2h |
| 15.6 | Add `/queue-add` slash command | 2h |
| 15.7 | Implement daily digest bot message | 3h |
| 15.8 | Add interactive buttons (Accept/Dismiss from Slack) | 4h |
| 15.9 | Create Slack App manifest for easy install | 1h |
| 15.10 | Add `SlackNotificationSignalProcessor` | 2h |
| 15.11 | Test end-to-end Slack workflow | 2h |

**Deliverable:** `/todays-moves` in Slack shows top 5, click to Accept/Dismiss

---

#### Sprint 16: Chrome Extension MVP
**Goal:** Access CaseyOS from any webpage  
**Duration:** 7 days

| Task | Description | Effort |
|------|-------------|--------|
| 16.1 | Create `chrome-extension/` directory structure | 1h |
| 16.2 | Write manifest.json (Manifest V3) | 1h |
| 16.3 | Build popup UI (Today's Moves top 5) | 4h |
| 16.4 | Add "Add to Queue" context menu | 2h |
| 16.5 | Implement background service worker | 3h |
| 16.6 | Add badge counter for pending items | 1h |
| 16.7 | Build options page for API key config | 2h |
| 16.8 | Add CORS headers to required API endpoints | 1h |
| 16.9 | Implement notification clicks → open queue item | 2h |
| 16.10 | Add LinkedIn profile scraper (context menu) | 3h |
| 16.11 | Package for Chrome Web Store (unlisted) | 2h |
| 16.12 | Create extension documentation | 1h |

**Deliverable:** Chrome extension installed, right-click any email/page → "Add to CaseyOS"

---

#### Sprint 17: Gmail Add-on
**Goal:** CaseyOS sidebar in Gmail  
**Duration:** 5 days

| Task | Description | Effort |
|------|-------------|--------|
| 17.1 | Create `gmail-addon/` directory with Apps Script | 2h |
| 17.2 | Build Gmail sidebar card UI | 3h |
| 17.3 | Show related queue items when viewing email | 3h |
| 17.4 | Add "Add to Queue" button in compose | 2h |
| 17.5 | Create "Quick Draft" from email context | 3h |
| 17.6 | Sync sent emails back to CaseyOS | 2h |
| 17.7 | Add contact lookup from HubSpot | 2h |
| 17.8 | Implement "Snooze" action | 1h |
| 17.9 | Create Google Workspace Marketplace listing | 2h |
| 17.10 | Write addon documentation | 1h |

**Deliverable:** Open email in Gmail, see CaseyOS sidebar with queue items + actions

---

### Phase 2: Voice & Intelligence (Sprints 18-20)

#### Sprint 18: Jarvis Voice Activation
**Goal:** Hands-free CaseyOS with voice commands  
**Duration:** 5 days

| Task | Description | Effort |
|------|-------------|--------|
| 18.1 | Implement Whisper API for speech-to-text | 3h |
| 18.2 | Add browser MediaRecorder for audio capture | 3h |
| 18.3 | Create voice command parser | 2h |
| 18.4 | Implement TTS for Jarvis responses | 3h |
| 18.5 | Add wake word detection ("Hey Jarvis") | 4h |
| 18.6 | Enable voice approval flow | 2h |
| 18.7 | Add voice feedback for actions | 2h |
| 18.8 | Create voice command reference | 1h |
| 18.9 | Test on mobile browsers | 2h |
| 18.10 | Add voice recording indicator UI | 1h |

**Deliverable:** Say "Hey Jarvis, what's my top move?" and hear the response

---

#### Sprint 19: Enhanced Intelligence
**Goal:** Smarter recommendations and automation  
**Duration:** 5 days

| Task | Description | Effort |
|------|-------------|--------|
| 19.1 | Implement learning from outcomes | 4h |
| 19.2 | Add personalized APS adjustments | 3h |
| 19.3 | Create "pattern detected" notifications | 2h |
| 19.4 | Add auto-scheduling for recurring actions | 3h |
| 19.5 | Implement smart snoozing (ML-based) | 4h |
| 19.6 | Add competitor alert rules | 2h |
| 19.7 | Create weekly performance report | 3h |
| 19.8 | Add goal tracking dashboard | 3h |

**Deliverable:** CaseyOS learns which actions work and adjusts recommendations

---

#### Sprint 20: Action Executor Wiring
**Goal:** All actions execute real operations  
**Duration:** 3 days

| Task | Description | Effort |
|------|-------------|--------|
| 20.1 | Wire `_execute_send_email` to Gmail API | 2h |
| 20.2 | Wire `_execute_create_task` to HubSpot | 2h |
| 20.3 | Wire `_execute_book_meeting` to Calendar | 3h |
| 20.4 | Wire `_execute_update_contact` to HubSpot | 2h |
| 20.5 | Add execution status tracking | 2h |
| 20.6 | Create execution audit log | 1h |
| 20.7 | Add rollback capability | 2h |
| 20.8 | Test all action types end-to-end | 3h |

**Deliverable:** Click "Execute" → action actually happens (email sent, task created, etc.)

---

### Phase 3: Enterprise Features (Sprints 21-24)

#### Sprint 21: Team Collaboration
**Goal:** Multi-user support with team features  
**Duration:** 5 days

| Task | Description | Effort |
|------|-------------|--------|
| 21.1 | Add user authentication (OAuth/SSO) | 4h |
| 21.2 | Create user roles (admin, member, viewer) | 3h |
| 21.3 | Add team dashboard | 4h |
| 21.4 | Implement task assignment | 3h |
| 21.5 | Add activity feed | 3h |
| 21.6 | Create team leaderboard | 2h |
| 21.7 | Add @mentions in queue items | 2h |
| 21.8 | Implement shared queue views | 2h |

---

#### Sprint 22: Advanced Analytics
**Goal:** Deep insights into GTM performance  
**Duration:** 5 days

| Task | Description | Effort |
|------|-------------|--------|
| 22.1 | Build pipeline velocity dashboard | 4h |
| 22.2 | Add cohort analysis | 3h |
| 22.3 | Create conversion funnel visualization | 4h |
| 22.4 | Implement A/B testing for email templates | 4h |
| 22.5 | Add revenue forecasting | 3h |
| 22.6 | Create exportable reports | 2h |
| 22.7 | Add Looker/Tableau integration | 3h |

---

#### Sprint 23: API & Webhooks
**Goal:** CaseyOS as a platform  
**Duration:** 5 days

| Task | Description | Effort |
|------|-------------|--------|
| 23.1 | Create public API documentation (OpenAPI) | 3h |
| 23.2 | Add API key management | 2h |
| 23.3 | Implement rate limiting per key | 2h |
| 23.4 | Create webhook delivery system | 4h |
| 23.5 | Add event subscriptions | 3h |
| 23.6 | Build developer portal | 4h |
| 23.7 | Create integration templates | 2h |

---

#### Sprint 24: Production Polish
**Goal:** Enterprise-ready platform  
**Duration:** 5 days

| Task | Description | Effort |
|------|-------------|--------|
| 24.1 | Achieve 95%+ test coverage | 8h |
| 24.2 | Complete security audit | 4h |
| 24.3 | Performance optimization | 4h |
| 24.4 | Accessibility audit (WCAG 2.1) | 3h |
| 24.5 | Documentation overhaul | 4h |
| 24.6 | Create onboarding flow | 3h |
| 24.7 | Add help/support system | 2h |
| 24.8 | Final QA and bug bash | 4h |

---

## Quick Wins (Do Now)

| Fix | File(s) | Effort | Priority |
|-----|---------|--------|----------|
| Add viewport meta to all HTML pages | `src/static/*.html` | 30min | HIGH |
| Fix TRUTH.md to show email sending works | `TRUTH.md` | 15min | MEDIUM |
| Create empty Slack connector scaffold | `src/connectors/slack.py` | 20min | MEDIUM |
| Add mobile CSS to command-queue.html | `src/static/command-queue.html` | 1h | HIGH |
| Remove admin password from docs | Various | 10min | HIGH |

---

## Known Issues & Technical Debt

| Issue | Severity | Location | Fix Effort |
|-------|----------|----------|------------|
| OAuth tokens in memory only | HIGH | `src/connectors/gmail.py` | 2h |
| 13 TODOs in action executor | MEDIUM | `src/services/action_executor.py` | 4h |
| No Slack connector | MEDIUM | Missing file | Sprint 15 |
| Voice has no audio | LOW | `src/voice_approval.py` | Sprint 18 |
| Admin password in old docs | LOW | Various .md files | 10min |

---

## Success Metrics

### Platform Health
- [ ] API uptime > 99.5%
- [ ] Avg response time < 200ms
- [ ] Error rate < 0.5%

### User Engagement
- [ ] Daily Active Users
- [ ] Actions executed per day
- [ ] Reply rate on emails
- [ ] Meeting booking rate

### Business Impact
- [ ] Pipeline influenced
- [ ] Deals closed
- [ ] Time saved per week

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           DISTRIBUTION LAYER                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Mobile  │  │  Slack   │  │  Chrome  │  │  Gmail   │  │   Web    │   │
│  │   PWA    │  │   Bot    │  │  Ext.    │  │  Addon   │  │   App    │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │              │        │
└───────┼──────────────┼──────────────┼──────────────┼──────────────┼────────┘
        │              │              │              │              │
        └──────────────┴──────────────┼──────────────┴──────────────┘
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                    │
│  FastAPI App • 150+ Routes • CSRF • Rate Limiting • Auth                 │
│  /api/command-queue • /api/signals • /api/jarvis • /api/outcomes         │
└──────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────┐            ┌───────────────┐            ┌───────────────┐
│  COMMAND      │            │   SIGNAL      │            │   AGENT       │
│  QUEUE        │            │   FRAMEWORK   │            │   ORCHESTRA   │
│               │            │               │            │               │
│  Today's Moves│◄──────────│  Form         │            │  Jarvis       │
│  APS Scoring  │            │  HubSpot      │            │  25+ Agents   │
│  Execution    │            │  Gmail        │            │  Domain Routing│
│               │            │  Twitter      │            │               │
└───────────────┘            └───────────────┘            └───────────────┘
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           CONNECTOR LAYER                                 │
│  Gmail • HubSpot • Calendar • Drive • OpenAI • Grok • Twitter • Gemini  │
└──────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                   │
│  PostgreSQL (asyncpg) • Redis (Celery) • Alembic migrations              │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-24 | 2.0 | Comprehensive audit, added Sprints 14-24, mobile/Slack/Chrome/Gmail |
| 2026-01-24 | 1.1 | Added Sprint 13 (Twitter/Grok) |
| 2026-01-23 | 1.0 | Initial roadmap through Sprint 12 |

---

**This is the single source of truth for CaseyOS development.**

_"Build the command center. Ship the outcomes. Measure the receipts."_
