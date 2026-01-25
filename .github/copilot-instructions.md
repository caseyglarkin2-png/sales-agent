# Copilot Instructions for Sales Agent (CaseyOS)

## Project Vision

**CaseyOS** is a GTM command center that operates like Casey's Chief of Staff. It proactively surfaces who matters, what to do next, and automates redundant work. This is NOT a CRM—it's a **decision engine + execution system**.

**Production URL**: https://web-production-a6ccf.up.railway.app  
**Deploy Platform**: Railway (project `ideal-fascination`, service `web`)

---

## Architecture (4 Layers)

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
│  └── src/connectors/gmail.py - OAuth, search, drafts, SEND ✅       │
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

### Core Workflow (Form → Draft → Approval)
1. HubSpot form webhook hits `/api/webhooks/hubspot`
2. `FormleadOrchestrator.process_formlead()` runs 11 steps:
   - Validate payload, resolve HubSpot contact/company
   - Search Gmail for existing threads, hunt Drive for assets
   - Research prospect, generate meeting slots
   - Apply voice profile, draft personalized email
   - Calculate ICP fit score, store in PostgreSQL
3. Draft enters `DraftQueue` → Operator UI for approval
4. **Auto-Approval + Send**: High-confidence drafts auto-approved and sent via Gmail API

---

## Environment Setup

### Required Environment Variables

```bash
# Database (CRITICAL)
DATABASE_URL=postgresql://user:pass@host:5432/salesagent
REDIS_URL=redis://localhost:6379/0

# Celery (uses Redis)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Google OAuth (REQUIRED for Gmail/Drive/Calendar)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/google/callback

# HubSpot (REQUIRED)
HUBSPOT_API_KEY=your-hubspot-key
HUBSPOT_WEBHOOK_SECRET=your-webhook-hmac-secret

# OpenAI (REQUIRED)
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4-turbo-preview

# Security (CRITICAL in production)
SECRET_KEY=your-32-char-random-string  # NOT the default!
ADMIN_PASSWORD=your-strong-admin-password  # NOT test123!

# Sentry (for error tracking)
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_ENVIRONMENT=production

# Safety Flags
MODE_DRAFT_ONLY=true          # KEEP TRUE until email sending is implemented
ALLOW_REAL_SENDS=false        # Feature flag for email sending
REQUIRE_APPROVAL=true         # Always require human approval
AUTO_APPROVE_ENABLED=true     # Enable auto-approval rules engine
```

### Local Development Setup

```bash
# 1. Clone and install
git clone <repo>
cd sales-agent
pip install -r requirements.txt  # or poetry install

# 2. Start infrastructure
make docker-up  # Starts postgres + redis + api with hot reload

# 3. Validate secrets
make secrets-check  # Checks all required env vars

# 4. Run migrations
python run_migrations.py

# 5. Authenticate Google OAuth (opens browser)
make auth-google

# 6. Smoke test the form→draft workflow
make smoke-formlead  # Uses mocked connectors
```

### Railway Deployment

The app deploys via Dockerfile. Key files:
- `Dockerfile` - Python 3.12 slim, installs deps, runs `start.sh`
- `start.sh` - Runs Alembic migrations then uvicorn on `$PORT`
- `railway.json` - Railway-specific config

---

## Key Conventions

### Async Database Pattern (CRITICAL - Sprint 22 Enforcement)

All database operations use SQLAlchemy async. **Always use context managers**:

```python
from src.db import get_session

async def my_route():
    async with get_session() as session:
        result = await session.execute(select(Model))
        # session auto-closes
```

**CRITICAL RULES:**
1. **✅ CORRECT:** Use `from src.db import get_session` + `async with get_session()`
2. **❌ WRONG:** Use `from src.db import async_session` + `async with async_session()`
3. **Exception:** Only `src/db/` module may use `async_session()` directly

**Pre-commit Hook Enforces This:**
- Blocks commits with `async with async_session()` outside `src/db/`
- Blocks direct `async_session` imports outside `src/db/`

**3 Approved Session Patterns:**
```python
# Pattern 1: Route handlers (most common)
from src.db import get_session

async def my_route():
    async with get_session() as session:
        result = await session.execute(select(Model))
        return result.scalars().all()

# Pattern 2: FastAPI dependency injection
from src.db import get_db
from fastapi import Depends

@router.get("/items")
async def list_items(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Item))
    return result.scalars().all()

# Pattern 3: Background tasks (Celery)
from src.db import get_session

@celery_app.task
async def process_task(item_id: str):
    async with get_session() as session:
        item = await session.get(Item, item_id)
        # process item
```

**NEVER** store sessions globally or pass them between requests.

### Agent Pattern
Agents extend `BaseAgent` from [src/agents/base.py](src/agents/base.py):
```python
from src.agents.base import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="MyAgent", description="Does X")
    
    async def validate_input(self, context: Dict) -> bool:
        return "required_field" in context
    
    async def execute(self, context: Dict) -> Dict:
        # Agent logic here
        return {"result": "success"}
```

### Structured Logging
Use JSON logging with trace_id correlation:
```python
from src.logger import get_logger
logger = get_logger(__name__)

logger.info("Processing form", extra={"email": email, "workflow_id": wf_id})
logger.error("Failed to connect", extra={"service": "hubspot", "error": str(e)})
```
Every request gets a `trace_id` via middleware for correlation.

### Configuration
All settings via Pydantic in [src/config.py](src/config.py):
```python
from src.config import get_settings
settings = get_settings()  # Cached singleton

# Access with attribute names (lowercase)
settings.database_url
settings.google_client_id
settings.mode_draft_only
```

### Telemetry Events
Use the telemetry module for tracking:
```python
from src.telemetry import log_event

log_event("recommendation_accepted", item_id=id, user="casey")
log_event("action_executed", action_type="send_email", success=True)
```

---

## Command Queue (Today's Moves)

The Command Queue is the **heartbeat of CaseyOS**. It surfaces prioritized actions.

### API Endpoints
```bash
# List pending items
curl $BASE/api/command-queue/

# Today's Moves (ranked by APS)
curl $BASE/api/command-queue/today

# Accept/Dismiss (requires admin token + CSRF)
CSRF=$(curl -sD- $BASE/health | grep X-CSRF-Token | cut -d' ' -f2)
curl -X POST $BASE/api/command-queue/<id>/accept \
  -H "X-Admin-Token: $ADMIN_PASSWORD" \
  -H "X-CSRF-Token: $CSRF"
```

### UI
Open `/static/command-queue.html` for the Today's Moves dashboard.

### APS Scoring
Action Priority Score (0-100) computed as:
- **Revenue Impact** (40%): Pipeline value, renewal risk, upsell potential
- **Urgency** (25%): Event deadlines, meeting windows, expiration risk
- **Effort** (15%): Quick wins score higher, high-friction tasks score lower
- **Strategic Value** (20%): ICP fit, logo value, ecosystem play

---

## Developer Commands

```bash
# Development
make docker-up          # Start postgres + redis + api (hot reload)
make docker-down        # Stop services
make docker-logs        # Tail logs

# Testing
make test               # Run all tests
make test-unit          # Unit tests only
make test-integration   # Integration tests (needs Docker)
make coverage           # Tests with coverage report

# Code Quality
make lint               # ruff check + pyright
make format             # ruff format
make pre-commit         # Run all pre-commit hooks

# Validation
make secrets-check      # Validate required env vars
make smoke-formlead     # E2E test with mocked connectors
make go-live-check      # Full pre-deploy validation

# Auth
make auth-google        # OAuth flow for Gmail/Drive/Calendar
```

### Running Tests
```python
# Tests use pytest-asyncio
@pytest.mark.asyncio
async def test_workflow():
    async with get_session() as session:
        # test logic
```
Run specific tests: `pytest tests/test_rate_limiting.py -v -s`

---

## File Organization

| Directory | Purpose |
|-----------|---------|
| `src/agents/` | AI agents: prospecting, nurturing, specialized, research |
| `src/connectors/` | External APIs: Gmail, HubSpot, Drive, Calendar, LLM |
| `src/routes/` | FastAPI routers (150+ modules) - register in `main.py` |
| `src/models/` | SQLAlchemy models: command_queue, workflow, draft, user |
| `src/db/` | Database session factory and queries |
| `src/security/` | CSRF middleware, admin auth, security headers |
| `src/tasks/` | Celery background tasks |
| `infra/migrations/` | Alembic migrations |
| `scripts/` | One-off utilities: import, seed, test |
| `docs/` | Architecture, philosophy, API docs |

---

## Critical Safety Guardrails

1. **Email Sending**: `send_email()` implemented with MIME, threading, retries. Controlled by feature flags.
2. **Auto-Approval**: Rules engine evaluates drafts; high-confidence auto-sends, borderline goes to review
3. **Rate Limiting**: 2/week, 20/day per contact via [src/rate_limiter.py](src/rate_limiter.py)
4. **Webhook Security**: HMAC-SHA256 validation in [src/webhook.py](src/webhook.py)
5. **CSRF Protection**: 99.6% coverage (1,177/1,182 endpoints) - see CSRF section below
6. **Admin Auth**: Sensitive endpoints require `X-Admin-Token` header
7. **Audit Trail**: All actions logged via [src/audit_trail.py](src/audit_trail.py)
8. **Kill Switch**: Emergency stop at `/api/admin/emergency-stop`

---

## CSRF Protection (Sprint 22 - 99.6% Coverage)

### Auto-Injection Pattern

All HTML files include `csrf-helper.js` which automatically:
- Fetches CSRF tokens from `/health` endpoint
- Wraps native `fetch()` to inject `X-CSRF-Token` header
- Auto-refreshes tokens on 403 errors
- **Zero code changes required** in application JavaScript

```html
<!-- All HTML files include this -->
<script src="/static/csrf-helper.js"></script>
```

### Whitelist Pattern

CSRF validation is **skipped** for:
- `/api/webhooks/*` - External webhooks with HMAC-SHA256 signature validation
- `/mcp/*` - MCP server (trusted Claude Desktop integration)
- `/health`, `/healthz`, `/ready` - Health checks (monitoring)
- `/auth/*` - OAuth callbacks (state validation via OAuth protocol)
- `/docs`, `/redoc`, `/openapi.json` - API documentation (read-only)

**File:** `src/security/csrf.py` - `exclude_path()` function

### Manual CSRF Testing

```bash
# 1. Get token from any endpoint
curl -I https://web-production-a6ccf.up.railway.app/health | grep X-CSRF-Token

# 2. Test POST without token (should fail 403)
curl -X POST $BASE/api/command-queue/test/accept
# Expected: {"detail":"CSRF token missing"}

# 3. Test POST with token (should pass CSRF check)
curl -X POST $BASE/api/command-queue/test/accept \
  -H "X-CSRF-Token: <token>"
# Expected: NOT 403 CSRF error (may fail for other reasons)

# 4. Validate with script
python validate_csrf.py
```

### Coverage Achieved

- **Before Sprint 22:** 1.4% (17/1,196 endpoints)
- **After Sprint 22:** 99.6% (1,177/1,182 endpoints)
- **Files Updated:** 16 files (11 HTML + csrf-helper.js + config)
- **Validation:** `validate_csrf.py` - 6 automated checks

---

## Common Pitfalls

- **DB Sessions**: Always use `async with` context managers—never store sessions globally
- **OAuth Tokens**: Currently stored in memory only; tokens expire after 1hr
- **Route Imports**: New routes must be registered in [src/main.py](src/main.py) explicitly
- **Migrations**: Run via `python run_migrations.py`, not raw alembic commands
- **CSRF**: Automatically handled by `csrf-helper.js` - just include the script in HTML
- **Admin endpoints**: Require both `X-Admin-Token` AND CSRF token
- **Pre-commit hooks**: Database session patterns enforced automatically

---

## CaseyOS Philosophy

Follow these principles from [PROJECT_BUILD_PHILOSOPHY.md](../PROJECT_BUILD_PHILOSOPHY.md):

1. **Atomic Tasks**: One intent per commit, small diffs, tight blast radius
2. **Validation First**: Define success criteria before coding
3. **Demoable Sprints**: Every sprint ships something that works end-to-end
4. **No Noise, Only Signal**: If it's not actionable, it doesn't belong in the UI
5. **Closed-Loop Learning**: Record outcomes, feed back into scoring

---

## Signal Framework

Signals are raw events that trigger recommendations in the Command Queue.

### Signal Sources (`src/models/signal.py`)
```python
class SignalSource(str, Enum):
    FORM = "form"       # HubSpot form submissions
    HUBSPOT = "hubspot" # Deal stage changes, contact updates
    GMAIL = "gmail"     # Reply detection, thread activity
    MANUAL = "manual"   # Manually created signals
```

### Signal → Recommendation Flow
1. **Signal ingested** from source (webhook, polling, manual)
2. **Deduplication** via `payload_hash` (SHA-256 of JSON payload)
3. **Signal processor** converts to `CommandQueueItem` with APS score
4. **Recommendation surfaces** in Today's Moves UI

### API Endpoints
```bash
# List signals
curl $BASE/api/signals

# HubSpot signal ingestion status
curl $BASE/api/hubspot/signals/status

# Manual refresh (pulls new HubSpot signals)
curl -X POST $BASE/api/hubspot/signals/refresh
```

---

## Agent Architecture (Jarvis-Orchestrated)

CaseyOS uses a **domain-organized agent architecture** with **Jarvis** as the master orchestrator. All specialized agents are coordinated through Jarvis for unified decision-making.

### Jarvis - Master Orchestrator

**File:** `src/agents/jarvis.py`

Jarvis is the "Chief of Staff" AI that:
- Routes queries to the correct domain agents
- Synthesizes answers from multiple agents
- Maintains context across conversations
- Provides a single interface for all CaseyOS capabilities

```python
from src.agents.jarvis import get_jarvis

# Singleton access
jarvis = get_jarvis()

# Route to any domain agent
result = await jarvis.ask("What's the status of the Acme Corp proposal?")

# Direct domain access
result = await jarvis.execute({
    "action": "route",
    "domain": "contracts",
    "query": "Generate a proposal for Acme Corp",
})
```

### Agent Domains

```
src/agents/
├── jarvis.py                    # Master orchestrator (routes to all domains)
├── base.py                      # BaseAgent class all agents extend
├── prospecting.py               # Lead qualification + outreach
├── nurturing.py                 # Follow-up sequences
├── research.py                  # Prospect enrichment
├── specialized.py               # Thread, memory, asset, meeting, draft agents
├── validation.py                # Compliance + tone checking
├── persona_router.py            # Persona-based routing
│
├── content/                     # Content Operations Domain
│   ├── repurpose.py            # ContentRepurposeAgent
│   ├── social_scheduler.py     # SocialSchedulerAgent
│   └── graphics_request.py     # GraphicsRequestAgent
│
├── fulfillment/                 # Fulfillment Domain
│   ├── deliverable_tracker.py  # DeliverableTrackerAgent
│   ├── approval_gateway.py     # ApprovalGatewayAgent
│   └── client_health.py        # ClientHealthAgent
│
├── contracts/                   # Contracts Domain
│   ├── proposal_generator.py   # ProposalGeneratorAgent
│   ├── contract_review.py      # ContractReviewAgent
│   └── pricing_calculator.py   # PricingCalculatorAgent
│
└── ops/                         # Operations Domain
    ├── competitor_watch.py      # CompetitorWatchAgent
    ├── revenue_ops.py           # RevenueOpsAgent
    └── partner_coordinator.py   # PartnerCoordinatorAgent
```

### Domain Agent Inventory

#### Sales Domain (Original Agents)

| Agent | File | Purpose |
|-------|------|---------|
| **ProspectingAgent** | `prospecting.py` | Analyzes messages for intent, scores relevance, generates response prompts |
| **NurturingAgent** | `nurturing.py` | Multi-stage follow-up sequences, creates HubSpot tasks by engagement stage |
| **ResearchAgent** | `research.py` | Enriches prospects with HubSpot + Gmail history, generates talking points |
| **ThreadReaderAgent** | `specialized.py` | Summarizes Gmail threads, extracts key context from conversations |
| **LongMemoryAgent** | `specialized.py` | Finds similar patterns from sent mail history |
| **AssetHunterAgent** | `specialized.py` | Searches Drive for relevant proposals/docs with **allowlist enforcement** |
| **MeetingSlotAgent** | `specialized.py` | Proposes 2-3 meeting slots via Calendar freebusy |
| **NextStepPlannerAgent** | `specialized.py` | Selects primary CTA (defaults to 30-min working session) |
| **DraftWriterAgent** | `specialized.py` | Creates personalized draft using voice profile + research context |
| **ValidationAgent** | `validation.py` | Compliance checks, tone analysis, prohibited terms |
| **PersonaRouter** | `persona_router.py` | Routes to specialized agents based on prospect persona |

#### Content Domain

| Agent | File | Purpose |
|-------|------|---------|
| **ContentRepurposeAgent** | `content/repurpose.py` | Transforms content into LinkedIn posts, Twitter threads, email snippets, newsletters |
| **SocialSchedulerAgent** | `content/social_scheduler.py` | Schedules posts, tracks optimal posting times, monitors engagement |
| **GraphicsRequestAgent** | `content/graphics_request.py` | Creates design briefs, queues graphics requests, generates AI prompts |

#### Fulfillment Domain

| Agent | File | Purpose |
|-------|------|---------|
| **DeliverableTrackerAgent** | `fulfillment/deliverable_tracker.py` | Tracks client deliverables, milestones, progress, and at-risk items |
| **ApprovalGatewayAgent** | `fulfillment/approval_gateway.py` | Manages multi-stakeholder approval workflows with escalation |
| **ClientHealthAgent** | `fulfillment/client_health.py` | Monitors client health scores, identifies at-risk accounts |

#### Contracts Domain

| Agent | File | Purpose |
|-------|------|---------|
| **ProposalGeneratorAgent** | `contracts/proposal_generator.py` | Generates proposals from templates, auto-discounting, LLM summaries |
| **ContractReviewAgent** | `contracts/contract_review.py` | Reviews contracts for red flags, missing clauses, suggests redlines |
| **PricingCalculatorAgent** | `contracts/pricing_calculator.py` | Calculates pricing, volume/loyalty discounts, generates quotes |

#### Operations Domain

| Agent | File | Purpose |
|-------|------|---------|
| **CompetitorWatchAgent** | `ops/competitor_watch.py` | Tracks competitor activity, generates battle cards, win/loss tracking |
| **RevenueOpsAgent** | `ops/revenue_ops.py` | Pipeline health, forecasting, deal velocity, at-risk deals |
| **PartnerCoordinatorAgent** | `ops/partner_coordinator.py` | Partner program management, referral tracking, commission calculation |

### Creating a New Agent

1. **Choose the domain** (content, fulfillment, contracts, ops, or create new)
2. **Extend BaseAgent**:
```python
from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)

class MyNewAgent(BaseAgent):
    def __init__(self, connectors=None):
        super().__init__(
            name="My New Agent",
            description="Does something useful"
        )
        # Add connectors (gmail, hubspot, etc.)
    
    async def validate_input(self, context: Dict) -> bool:
        action = context.get("action")
        if action == "create":
            return "name" in context
        return True
    
    async def execute(self, context: Dict) -> Dict:
        action = context.get("action", "default")
        
        if action == "create":
            return await self._create(context)
        elif action == "list":
            return await self._list(context)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}
```

3. **Register in Jarvis** (`src/agents/jarvis.py`):
```python
# Add import
from src.agents.mydomain.my_agent import MyNewAgent

# Add to _load_agents()
self._agents["my_new"] = MyNewAgent()

# Add domain routing in _route_to_agent()
```

4. **Export from domain __init__.py**

### Agent Usage Patterns

#### Via Jarvis (Recommended)
```python
from src.agents.jarvis import get_jarvis

jarvis = get_jarvis()

# Natural language query - Jarvis routes to correct agent(s)
result = await jarvis.ask("What's the pipeline health looking like?")

# Direct domain routing
result = await jarvis.execute({
    "action": "route",
    "domain": "fulfillment",
    "agent": "deliverable_tracker",
    "context": {"action": "list", "client_id": "acme-123"},
})
```

#### Direct Agent Access (For Orchestrators)
```python
# Formlead orchestration still uses direct agents
orchestrator = FormleadOrchestrator(
    gmail_connector=gmail,
    hubspot_connector=hubspot,
    calendar_connector=calendar,
    drive_connector=drive,
)
result = await orchestrator.process_formlead(form_submission)

# Direct agent use when needed
from src.agents.ops.revenue_ops import RevenueOpsAgent

agent = RevenueOpsAgent(hubspot_connector=hubspot)
result = await agent.execute({"action": "pipeline_health"})
```

### AssetHunter Allowlist
The `AssetHunterAgent` enforces an allowlist to prevent leaking client data:
```python
ALLOWLIST = {
    "pesti_sales": {
        "root_id": "0ACIUuJIAAt4IUk9PVA",
        "include_prefixes": ["CHAINge Proposals", "CP Client Reports"],
        "exclude_prefixes": ["CP Closed"],
    },
    "charlie_pesti": {
        "root_id": "...",
        "include_all": True,  # All files allowed
    },
}
```

---

## Testing Patterns

### Test Directory Structure
```
tests/
├── fixtures/
│   └── seed_data.py       # Sample prospects, forms, threads, drafts
├── unit/
│   ├── test_agents.py     # Agent unit tests
│   ├── test_connectors.py # Connector mocks
│   ├── test_operator_mode.py
│   └── ...
├── integration/
│   ├── test_formlead_orchestration.py  # Full 11-step workflow
│   ├── test_webhooks.py
│   └── test_api.py
├── test_signal_*.py       # Signal framework tests
└── test_aps_calculator.py # APS scoring tests
```

### Test Fixtures (`tests/fixtures/seed_data.py`)
Pre-built test data for common scenarios:
```python
from tests.fixtures.seed_data import (
    SAMPLE_PROSPECTS,           # 3 sample prospects with emails/companies
    SAMPLE_FORM_SUBMISSIONS,    # HubSpot form payloads
    SAMPLE_GMAIL_THREADS,       # Mock Gmail thread data
    SAMPLE_CALENDAR_SLOTS,      # Meeting availability slots
    SAMPLE_DRAFTS,              # Pre-generated draft emails
    SAMPLE_HUBSPOT_TASKS,       # Task objects
    get_sample_form_submission, # Helper to get random form
)
```

### Mock Connectors Pattern
```python
class MockGmailConnector:
    async def search_threads(self, *args, **kwargs):
        return [{"id": "thread-123", "snippet": "Previous conversation..."}]
    
    async def create_draft(self, to: str, subject: str, body: str):
        return f"draft-{datetime.utcnow().isoformat()}"

class MockHubSpotConnector:
    async def search_contacts(self, email: str):
        return {"id": "contact-123", "email": email}

# Use in tests
orchestrator = FormleadOrchestrator(
    gmail_connector=MockGmailConnector(),
    hubspot_connector=MockHubSpotConnector(),
)
```

### Running Tests
```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests (needs Docker)
make test-integration

# Specific file
pytest tests/test_signal_to_recommendation.py -v

# With coverage
make coverage
```

### Validation Scripts (Sprint 22 Pattern)

For quick validation without network dependencies, create Python validation scripts:

```python
#!/usr/bin/env python3
"""Validation script pattern - no network, fast feedback."""
from pathlib import Path

def check_pattern():
    """Check that code follows expected pattern."""
    file = Path("src/security/csrf.py")
    content = file.read_text()
    
    required_items = ["/api/webhooks", "/mcp", "/health"]
    for item in required_items:
        if item in content:
            print(f"✓ {item}")
        else:
            print(f"❌ Missing: {item}")
            return False
    return True

if __name__ == "__main__":
    exit(0 if check_pattern() else 1)
```

**Examples:**
- `validate_csrf.py` - CSRF protection validation (6 checks)
- `python validate_csrf.py` - Run before deployment
- Faster than pytest for structural checks
- Good for CI/CD pre-checks

### Key Test Files
- `test_formlead_orchestration.py` - Full 11-step workflow integration
- `test_signal_to_recommendation.py` - Signal → recommendation conversion
- `test_aps_calculator.py` - APS scoring logic
- `test_rate_limiting.py` - Rate limiter behavior
- `test_operator_mode.py` - Draft approval flow

---

## Error Handling Patterns

### Standard Exception Handling
```python
from src.logger import get_logger
from fastapi import HTTPException

logger = get_logger(__name__)

async def my_endpoint():
    try:
        result = await risky_operation()
        return {"status": "success", "data": result}
    except ValueError as e:
        logger.warning("Validation failed", extra={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))
    except ExternalAPIError as e:
        logger.error("External API failed", extra={"service": e.service, "error": str(e)})
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except Exception as e:
        logger.exception("Unexpected error", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Circuit Breaker Pattern
External API calls should use circuit breakers to prevent cascade failures:
```python
from src.circuit_breaker import circuit_breaker

@circuit_breaker(failure_threshold=5, recovery_timeout=60)
async def call_hubspot_api():
    # API call here
    pass
```

### Retry with Exponential Backoff
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def resilient_api_call():
    # Retries 3 times with 2s, 4s, 8s delays
    pass
```

---

## Code Review Guidelines

### PR Checklist (Mandatory)
- [ ] **Atomic**: Single intent, small diff, tight blast radius
- [ ] **Tested**: Unit tests for new logic, integration tests for workflows
- [ ] **Validated**: Clear acceptance criteria met
- [ ] **Reversible**: Rollback plan documented or obvious
- [ ] **Observable**: Logging added where failures can hide
- [ ] **Secure**: No secrets in code, CSRF/auth on state-changing endpoints

### Code Style
- **Type hints**: Required on all function signatures
- **Docstrings**: Required on all public functions/classes
- **Imports**: Use absolute imports (`from src.agents.base import BaseAgent`)
- **Async**: Prefer `async def` for I/O operations
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes

### Common Review Feedback
| Issue | Fix |
|-------|-----|
| Missing type hints | Add `-> Dict[str, Any]` return types |
| Bare `except:` | Catch specific exceptions |
| Global DB session | Use `async with get_session()` |
| Hardcoded values | Move to `src/config.py` |
| Missing logging | Add `logger.info/error` with context |
| No validation | Add `validate_input()` in agents |

---

## Quick Reference Cheat Sheet

### Common Imports
```python
# Database
from src.db import get_session
from sqlalchemy import select, and_, or_

# Models
from src.models.command_queue import CommandQueueItem
from src.models.workflow import Workflow
from src.models.signal import Signal

# Agents
from src.agents.jarvis import get_jarvis
from src.agents.base import BaseAgent

# Config & Logging
from src.config import get_settings
from src.logger import get_logger

# FastAPI
from fastapi import APIRouter, HTTPException, Depends
```

### Common Patterns
```python
# Get settings
settings = get_settings()

# Get logger
logger = get_logger(__name__)

# Database query
async with get_session() as session:
    result = await session.execute(
        select(Model).where(Model.status == "active")
    )
    items = result.scalars().all()

# Jarvis query
jarvis = get_jarvis()
result = await jarvis.ask("What deals are at risk?")

# Agent execution
agent = MyAgent(connector=my_connector)
result = await agent.execute({"action": "list"})
```

### Environment Quick Check
```bash
# Is it running?
curl https://web-production-a6ccf.up.railway.app/health

# Check readiness
curl https://web-production-a6ccf.up.railway.app/ready

# Today's Moves
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today
```

---

## Bulk Refactoring Best Practices (Sprint 22 Lessons)

### Mechanical String Replacement Pattern

For systematic code changes (imports, patterns, etc.), use `sed` scripts:

```bash
#!/bin/bash
# Bulk fix pattern - mechanical, fast, auditable

echo "=== Fixing Pattern Violations ==="

for file in src/routes/*.py; do
  echo "Fixing $file..."
  # Replace import
  sed -i 's/from src\.db import async_session/from src.db import get_session/g' "$file"
  # Replace usage
  sed -i 's/async with async_session()/async with get_session()/g' "$file"
  echo "  ✓ Fixed"
done

echo "Files fixed: $(ls src/routes/*.py | wc -l)"
```

**Benefits:**
- **Fast:** Processes 100+ files in seconds
- **Auditable:** `git diff` shows exactly what changed
- **Reversible:** `git revert` undoes entire batch
- **Testable:** Run validation script after

**Sprint 22 Example:**
- Fixed 15 files with database session anti-patterns
- Created 2 bash scripts for P0 and remaining files
- Validated with `grep` to confirm zero violations
- Added pre-commit hooks to prevent regression

### Pre-commit Hook Pattern

Enforce patterns automatically:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-async-session-usage
        name: Check for async_session() anti-pattern
        entry: bash -c 'if grep -rn "async with async_session()" src/; then exit 1; fi'
        language: system
        pass_filenames: false
```

**Result:** Impossible to commit anti-patterns

---

## Reference Files

- [TRUTH.md](../TRUTH.md) - What actually works vs. known gaps
- [PROJECT_BUILD_PHILOSOPHY.md](../PROJECT_BUILD_PHILOSOPHY.md) - "Atomic tasks, clear validation"
- [API_ENDPOINTS.md](../API_ENDPOINTS.md) - Endpoint reference with curl examples
- [docs/CASEYOS_PHILOSOPHY.md](../docs/CASEYOS_PHILOSOPHY.md) - CaseyOS vision and principles
- [docs/CASEYOS_SPRINT_ROADMAP.md](../docs/CASEYOS_SPRINT_ROADMAP.md) - Sprint plans and tasks
- [docs/CASEYOS_ARCHITECTURE_AUDIT.md](../docs/CASEYOS_ARCHITECTURE_AUDIT.md) - Detailed architecture analysis
- [SPRINT_22_TASK_2_COMPLETION_REPORT.md](../SPRINT_22_TASK_2_COMPLETION_REPORT.md) - Database session cleanup
- [SPRINT_22_TASK_3_COMPLETION_REPORT.md](../SPRINT_22_TASK_3_COMPLETION_REPORT.md) - CSRF expansion (99.6%)
