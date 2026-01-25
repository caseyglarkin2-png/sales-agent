# CaseyOS Architecture

**Version:** 1.0  
**Date:** January 25, 2026  
**Status:** Production

---

## Overview

CaseyOS is a GTM (Go-To-Market) command center that operates like Casey's Chief of Staff. It proactively surfaces who matters, what to do next, and automates redundant work.

**This is NOT a CRM — it's a decision engine + execution system.**

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  FastAPI App (src/main.py)                                          │
│  └── 150+ route modules in src/routes/                              │
│  └── Middleware: CSRF, security headers, trace_id injection         │
├─────────────────────────────────────────────────────────────────────┤
│  Command Queue ("Today's Moves")                                     │
│  └── src/routes/command_queue.py - Priority queue API               │
│  └── src/models/command_queue.py - CommandQueueItem + APS scoring   │
│  └── APS = 40% revenue + 25% urgency + 15% effort + 20% strategic   │
├─────────────────────────────────────────────────────────────────────┤
│  Orchestrator Layer                                                  │
│  └── src/formlead_orchestrator.py - 11-step form→draft workflow     │
│  └── src/agents/{prospecting,nurturing,specialized}.py              │
│  └── src/operator_mode.py - Draft approval queue                    │
├─────────────────────────────────────────────────────────────────────┤
│  Connectors (External APIs)                                          │
│  └── src/connectors/gmail.py - OAuth, search, drafts, SEND          │
│  └── src/connectors/hubspot.py - Contacts, companies, tasks, deals  │
│  └── src/connectors/drive.py - Asset hunting                        │
│  └── src/connectors/llm.py - OpenAI GPT-4                           │
├─────────────────────────────────────────────────────────────────────┤
│  Data Layer                                                          │
│  └── PostgreSQL (asyncpg + SQLAlchemy async)                        │
│  └── Redis (Celery broker + rate limiting)                          │
│  └── Alembic migrations in infra/migrations/                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Command Queue (Today's Moves)

The heartbeat of CaseyOS. Surfaces prioritized actions ranked by APS.

**Files:**
- `src/models/command_queue.py` - Data models
- `src/routes/command_queue.py` - API endpoints
- `src/static/command-queue.html` - UI

**API Endpoints:**
```bash
GET  /api/command-queue/           # List all items
GET  /api/command-queue/today      # Today's top 10
POST /api/command-queue/{id}/accept
POST /api/command-queue/{id}/dismiss
POST /api/command-queue/{id}/snooze
```

### 2. Action Priority Score (APS)

Scoring algorithm (0-100) that determines priority:

| Component | Weight | Description |
|-----------|--------|-------------|
| Revenue Impact | 40% | Pipeline value, renewal risk, upsell potential |
| Urgency | 25% | Event deadlines, meeting windows, expiration |
| Effort | 15% | Quick wins score higher, high-friction lower |
| Strategic Value | 20% | ICP fit, logo value, ecosystem play |

### 3. Signal Ingestion

Raw events that trigger recommendations:

**Sources:**
- HubSpot webhooks (form submissions, deal changes)
- Gmail polling (reply detection)
- Manual signals (user-created)

**Files:**
- `src/models/signal.py` - Signal model
- `src/routes/signals.py` - Signal API
- `src/routes/hubspot_signals.py` - HubSpot integration

### 4. Orchestrator Layer

**FormLeadOrchestrator** (11-step workflow):
1. Validate payload
2. Resolve HubSpot contact/company
3. Search Gmail for existing threads
4. Hunt Drive for assets
5. Research prospect
6. Generate meeting slots
7. Apply voice profile
8. Draft personalized email
9. Calculate ICP fit score
10. Store in PostgreSQL
11. Return draft_id for approval

### 5. Agent Architecture

**Jarvis** - Master orchestrator that routes to domain agents:

```
src/agents/
├── jarvis.py                 # Master orchestrator
├── base.py                   # BaseAgent class
├── prospecting.py            # Lead qualification
├── nurturing.py              # Follow-up sequences
├── research.py               # Prospect enrichment
├── specialized.py            # Thread, memory, asset agents
├── content/                  # Marketing ops agents
├── fulfillment/              # Delivery tracking agents
├── contracts/                # Proposal/pricing agents
└── ops/                      # Revenue ops agents
```

---

## Security Guardrails

1. **CSRF Protection** - All POST/PUT/DELETE require token
2. **Admin Auth** - Sensitive endpoints require `X-Admin-Token`
3. **Rate Limiting** - 2/week, 20/day per contact
4. **Audit Trail** - All actions logged
5. **Kill Switch** - Emergency stop at `/api/admin/emergency-stop`
6. **GDPR Compliance** - User deletion, data retention

---

## Background Processing

**Celery Tasks:**
- `process_formlead_async` - Async form processing
- `cleanup_old_drafts` - GDPR 90-day retention
- `signal_ingest` - Periodic signal polling

**Beat Schedule:**
- Draft cleanup: 2 AM daily
- Signal polling: Every 5 minutes

---

## Monitoring

**Health Endpoints:**
- `GET /health` - Basic liveness
- `GET /healthz` - Kubernetes probe
- `GET /ready` - Readiness (DB + Redis)
- `GET /startup` - Startup probe

**Sentry Integration:**
- Error tracking (when SENTRY_DSN set)
- Performance monitoring
- Breadcrumb trails

---

## File Organization

| Directory | Purpose |
|-----------|---------|
| `src/agents/` | AI agents |
| `src/connectors/` | External APIs |
| `src/routes/` | FastAPI routers |
| `src/models/` | SQLAlchemy models |
| `src/db/` | Database session factory |
| `src/security/` | CSRF, admin auth |
| `src/tasks/` | Celery tasks |
| `infra/migrations/` | Alembic migrations |
| `scripts/` | One-off utilities |
| `docs/` | Documentation |

---

## Deployment

**Platform:** Railway  
**Project:** `ideal-fascination`  
**Service:** `web`  
**Build:** Dockerfile

**Start Script:**
1. Run Alembic migrations
2. Start uvicorn on `$PORT`

---

## Key Environment Variables

```bash
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
HUBSPOT_API_KEY=...
OPENAI_API_KEY=...
ADMIN_PASSWORD=<strong-random>
SENTRY_DSN=...
```

---

**Last Updated:** January 25, 2026
