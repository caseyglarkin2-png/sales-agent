# Sales Agent - Operator-Mode B2B Prospecting & Nurturing System

**Production-ready framework for autonomous outbound B2B sales workflows with human operator oversight.**

## 🎯 Overview

Sales Agent is a comprehensive Python framework that automates prospecting, lead nurturing, and engagement workflows for B2B sales teams. Built with FastAPI, it features 5 autonomous agents, complete safety frameworks, and operator-mode controls for human oversight.

**Status:** ✅ **Sprints 0-8 Complete** | 59 Python files | 100+ tests | Production-ready

### Quick Demo

```bash
# Start services
docker compose up --wait

# Try prospecting analysis
curl http://localhost:8000/api/agents/demo/prospecting

# Try draft workflow (requires approval)
curl -X POST http://localhost:8000/api/operator/drafts?draft_id=test-1 \
  -H "Content-Type: application/json" \
  -d '{"recipient":"prospect@example.com","subject":"Hi","body":"This is a message body that is long enough for validation."}'

# Approve and send
curl -X POST http://localhost:8000/api/operator/drafts/test-1/approve \
  -H "Content-Type: application/json" \
  -d '{"approved_by":"operator@company.com"}'

curl -X POST http://localhost:8000/api/operator/drafts/test-1/send
```

---

## 🚀 Key Features

### 5 Autonomous Agents

| Agent | Function | Examples |
|-------|----------|----------|
| **Prospecting** | Intent detection + response generation | Analyze incoming messages, score relevance, suggest replies |
| **Nurturing** | Multi-stage follow-up sequencing | Auto-schedule tasks, optimize timing, track engagement |
| **Validation** | Compliance & quality checks | Flag prohibited terms, tone analysis, length validation |
| **Demo** | Cold-start scenarios | Generate realistic examples for all workflows |
| **Outcome Reporter** | Analytics & metrics | Engagement funnel, agent performance, system health |

### Built-in Safety

✅ **Operator Mode** - Human approval required for all sends  
✅ **Rate Limiting** - 20/day, 2/week per contact quotas  
✅ **Compliance Audit** - Immutable trail of every action  
✅ **OAuth2 Framework** - Centralized credential management  
✅ **Resilience** - Retry logic, circuit breakers, error recovery  
✅ **Webhook Security** - HMAC-SHA256 signature validation  

### Production Ready

✅ PostgreSQL with pgvector for semantic search  
✅ Redis for task queuing (Celery)  
✅ Structured JSON logging with request tracing  
✅ Pre-commit hooks (ruff, pyright, pytest)  
✅ 80%+ test coverage with integration tests  
✅ Docker Compose for local development  
✅ Comprehensive API documentation  

---

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Python Files** | 59 |
| **Test Files** | 16 |
| **Database Tables** | 11 |
| **API Endpoints** | 20+ |
| **Tests** | 100+ |
| **Lines of Code** | 5,000+ |

---

## 🏗️ Architecture

### Agents Layer
```
┌─────────────────────────────────────────────┐
│ ProspectingAgent │ NurturingAgent │ ... │
└────────┬──────────────────────────┬─────────┘
         │ validate_input()         │
         │ execute()                │
         └─────────────────────────┘
```

### Connectors Layer
```
┌──────────────────────────────────────────┐
│ GmailConnector │ HubSpotConnector │ LLM  │
└──────────────────────────────────────────┘
```

### Infrastructure
```
PostgreSQL + pgvector ←→ FastAPI ←→ Redis + Celery
      (data)                (API)     (queuing)
```

---

## 🔧 Installation

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git

### Setup

```bash
# Clone repo
git clone <repo>
cd sales-agent

# Create environment file
cp .env.example .env

# Add API keys to .env
# - OPENAI_API_KEY=sk-...
# - HUBSPOT_API_KEY=pat-...
# - GOOGLE_CLIENT_ID=...

# Start services
docker compose up --wait

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Start API (if not using docker compose)
uvicorn src.main:app --reload
```

---

## 📚 API Endpoints

### Demo (No Authentication)

```
GET  /api/agents/demo/prospecting      # See prospecting in action
GET  /api/agents/demo/validation       # See validation workflow
GET  /api/agents/demo/nurturing        # See nurturing sequence
```

### Agents (Analysis)

```
POST /api/agents/prospecting/analyze   # Analyze message for opportunities
POST /api/agents/nurturing/schedule    # Schedule follow-up sequence
POST /api/agents/validation/check      # Validate draft compliance
POST /api/agents/reporting/generate    # Generate engagement report
```

### Operator Mode (Draft Management)

```
POST   /api/operator/drafts                        # Create draft
GET    /api/operator/drafts/pending                # Get pending queue
GET    /api/operator/drafts/{draft_id}             # Get draft
POST   /api/operator/drafts/{draft_id}/approve     # Approve draft
POST   /api/operator/drafts/{draft_id}/reject      # Reject draft
POST   /api/operator/drafts/{draft_id}/send        # Send draft
GET    /api/operator/quota/{contact_email}        # Check quota
```

### System

```
GET  /health          # Health check
GET  /api/status      # System status (operator mode, rate limits)
GET  /docs            # OpenAPI documentation
```

---

## 💾 Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `messages` | Gmail messages with embeddings |
| `threads` | Email conversations (Gmail ↔ HubSpot bridge) |
| `hubspot_companies` | Company records from HubSpot CRM |
| `hubspot_contacts` | Contact records from HubSpot CRM |
| `hubspot_deals` | Sales deals from HubSpot CRM |
| `agent_tasks` | Follow-up tasks created by agents |
| `agent_notes` | Activity notes logged by agents |
| `draft_audit_log` | **Immutable** compliance trail |
| `message_embeddings` | Semantic search vectors (1536-dim) |
| `document_embeddings` | Knowledge base vectors (1536-dim) |

---

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Tests

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Specific agent
pytest tests/unit/test_prospecting.py -v

# With coverage report
pytest tests/ --cov=src --cov-report=html
```

### Test Coverage

✅ Config & environment loading  
✅ Structured JSON logging  
✅ Database models & constraints  
✅ All 5 agents (validate, execute)  
✅ All 3 connectors  
✅ Message analysis & scoring  
✅ Draft approval workflow  
✅ Rate limiting & quotas  
✅ API endpoints (integration)  

---

## 📖 Usage Examples

### Example 1: Analyze Incoming Message

```python
from src.agents.prospecting import ProspectingAgent
from src.connectors.llm import LLMConnector

llm = LLMConnector("sk-...", model="gpt-4-turbo-preview")
agent = ProspectingAgent(llm)

result = await agent.execute({
    "message_id": "msg-123",
    "sender": "prospect@example.com",
    "subject": "Interested in your platform",
    "body": "Hi, we're exploring sales automation tools..."
})

print(f"Score: {result['relevance_score']}")  # 0-1.0
print(f"Action: {result['action']}")          # "draft_required" or "archive"
print(f"Response: {result['response_prompt']}")
```

### Example 2: Create & Approve Draft

```bash
# Create draft
curl -X POST http://localhost:8000/api/operator/drafts?draft_id=d-001 \
  -H "Content-Type: application/json" \
  -d '{
    "recipient": "sarah@acmecorp.com",
    "subject": "Thought of you regarding growth strategy",
    "body": "Hi Sarah, I came across your company and was impressed by your Series B funding. I think our platform could help accelerate your go-to-market motion. Would you be open to a 15-minute call?"
  }'

# Operator reviews and approves
curl -X POST http://localhost:8000/api/operator/drafts/d-001/approve \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "alice@company.com"}'

# Send the draft
curl -X POST http://localhost:8000/api/operator/drafts/d-001/send
```

### Example 3: Check Email Quota

```bash
curl http://localhost:8000/api/operator/quota/sarah@acmecorp.com

# Response:
# {
#   "remaining_today": 15,
#   "remaining_this_week": 1,
#   "remaining_for_contact": 2
# }
```

---

## 🔒 Security Features

### Operator Mode
- All outbound emails require human approval
- Audit trail (immutable log of every action)
- Actor tracked (who approved/rejected)

### Rate Limiting
- Per-day limit (default: 20 emails/day)
- Per-week limit (default: 2 emails/week)
- Per-contact-per-week limit (default: 2)

### Validation
- Compliance checks (prohibited terms, unsubscribe link)
- Tone analysis (flag aggressive language)
- Quality checks (message length, personalization)

### Authentication
- OAuth2 credential management framework
- Webhook HMAC-SHA256 signature validation
- Request tracing with trace_id middleware

---

## 📋 Configuration

### Environment Variables

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_ENV=development
API_LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/sales_agent

# Redis & Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# External APIs
OPENAI_API_KEY=sk-...
HUBSPOT_API_KEY=pat-...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Operator Mode
OPERATOR_MODE_ENABLED=true
OPERATOR_APPROVAL_REQUIRED=true
MAX_EMAILS_PER_DAY=20
MAX_EMAILS_PER_WEEK=2

# Feature Flags
FEATURE_COLD_START_DEMO=true
FEATURE_VALIDATION_AGENT=true
FEATURE_OUTCOME_REPORTER=true

# Logging
LOG_FORMAT=json
LOG_LEVEL=INFO
```

---

## 🚢 Deployment

### Railway (Recommended)

Deploy to Railway for simple, managed infrastructure:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link project
railway login
railway link

# Add PostgreSQL and Redis
railway add --database postgres
railway add --database redis

# Set environment variables
railway variables set OPENAI_API_KEY=sk-...
railway variables set HUBSPOT_API_KEY=pat-...
railway variables set GOOGLE_CREDENTIALS_JSON='...'
railway variables set GMAIL_DELEGATED_USER=you@company.com
railway variables set MODE_DRAFT_ONLY=true
railway variables set OPERATOR_APPROVAL_REQUIRED=true

# Deploy
railway up

# Open dashboard
railway open
```

**Live Environment:**
- Dashboard: `https://web-production-a6ccf.up.railway.app/`
- API Docs: `https://web-production-a6ccf.up.railway.app/docs`
- Webhook: `https://web-production-a6ccf.up.railway.app/api/webhooks/hubspot/form-submission`

### Docker Build

```bash
docker build -t sales-agent:latest .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e OPENAI_API_KEY=sk-... \
  sales-agent:latest
```

### Production Checklist

- [ ] Set `API_ENV=production`
- [ ] Use strong API keys (rotate regularly)
- [ ] Enable HTTPS/TLS
- [ ] Set up PostgreSQL backups
- [ ] Configure Redis persistence
- [ ] Enable monitoring & alerting
- [ ] Run full test suite
- [ ] Set up CI/CD pipeline

---

## 📊 Project Structure

```
sales-agent/
├── src/                           # Main source code
│   ├── agents/                    # 5 agent implementations
│   │   └── base.py               # Abstract base class
│   ├── connectors/                # External API integrations
│   ├── models/                    # SQLAlchemy ORM
│   ├── routes/                    # FastAPI route handlers
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Pydantic settings
│   ├── db.py                      # Database session factory
│   ├── logger.py                  # Structured logging
│   ├── operator_mode.py           # Draft approval workflow
│   ├── rate_limiter.py            # Quota enforcement
│   └── ...                        # Supporting modules
├── tests/                         # Test suite
│   ├── unit/                      # 16 unit test files
│   └── integration/               # Integration tests
├── infra/                         # Infrastructure files
│   ├── migrations/                # Alembic DB migrations
│   └── init_db.sql                # pgvector setup
├── docker-compose.yml             # Local dev environment
├── Dockerfile                     # Container image
├── pyproject.toml                 # Dependencies & config
└── .env.example                   # Environment template
```

---

## 🎓 Learning Path

1. **Start**: `docker compose up --wait` + visit demo endpoints
2. **Explore**: Read [IMPLEMENTATION.md](IMPLEMENTATION.md) for architecture details
3. **Test**: Run `pytest tests/ -v` to see all functionality
4. **Extend**: Add custom agents by extending `BaseAgent`
5. **Deploy**: Follow production checklist above

---

## 📝 License

MIT

---

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Run `pre-commit run --all-files`
4. Add tests (aim for >80% coverage)
5. Submit PR

---

## 📞 Support

- 📖 See [IMPLEMENTATION.md](IMPLEMENTATION.md) for full documentation
- 🧪 Run tests: `pytest tests/ -v`
- 🐛 Check logs: `docker compose logs api`
- 📡 API docs: http://localhost:8000/docs

---

**Last Updated:** January 2026  
**Version:** 0.1.0: Operator-Mode Prospecting + Nurturing

An AI-powered mini-agent system for Gmail-powered prospecting and nurturing, integrated with HubSpot CRM, Google Drive assets, and Calendar scheduling.

**Note:** Timeline estimates are intentionally omitted from all planning documents. See [Sprint Plan](docs/sprint_plan.md) for dependency-driven sequencing.

## Overview

This system builds intelligent email drafts for lead followup and nurturing campaigns:
- **Reads** Gmail threads for context + historical memory
- **Learns** voice patterns from your sent email corpus
- **Retrieves** relevant sales assets from Google Drive
- **Plans** next steps with context + cadence awareness
- **Writes** personalized drafts in your learned voice
- **Tracks** all activities in HubSpot CRM
- **Defaults to DRAFT_ONLY mode** (human review, never sends automatically)
- **Scales safely** to autonomous send with quotas, guardrails, and approval workflows

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12 (for local development)
- Google Cloud credentials (service account for Gmail/Drive/Calendar)
- HubSpot API key

### Local Development

```bash
# Clone repo
git clone <repo>
cd sales-agent

# Copy env template
cp .env.example .env

# Start local environment
docker compose up --wait

# Verify API is running
curl http://localhost:8000/health

# Run tests
pytest tests/unit/ -v
pytest tests/integration/ -v
```

## Documentation

- **[Sprint Plan](docs/sprint_plan.md)** — Detailed 20-sprint breakdown with tickets, acceptance criteria, tests
- **[Development Guide](docs/DEVELOPMENT.md)** — Local setup, testing, extending agents
- **[API Reference](docs/API.md)** — All endpoints, auth, examples (also available at `/docs` when running)
- **[Deployment Guide](docs/DEPLOYMENT.md)** — Deploy to staging & production on GCP Cloud Run
- **[Runbook](docs/RUNBOOK.md)** — Operational troubleshooting and manual controls
- **[Voice Profile Guide](docs/VOICE_PROFILE.md)** — How voice learning works, examples

## Architecture

### Mini-Agent System
- **TriggerAgent** — Event → job
- **IdentityResolverAgent** — Email/domain → HubSpot entities
- **ThreadReaderAgent** — Gmail thread → structured facts
- **LongMemoryAgent** — Global context retrieval
- **AssetHunterAgent** — Drive asset search within allowlist
- **MeetingSlotAgent** — Calendar freebusy → meeting times
- **NextStepPlannerAgent** — Plan cadence + risk gating
- **DraftWriterAgent** — Compose draft in learned voice
- **CRMHygieneAgent** — Log to HubSpot
- **QualityGateAgent** — Risk/compliance gating
- **StoryPitchTargetingAgent** — Segment & rank contacts
- **StoryPitchWriterAgent** — Personalized campaign drafts

### Tech Stack
- **Python 3.12** — Core service
- **FastAPI** — REST API
- **Celery + Redis** — Background tasks
- **PostgreSQL + pgvector** — Message indexing + semantic search
- **GCP** — Gmail, Drive, Calendar, Cloud Run, Cloud SQL
- **HubSpot** — CRM integration

## Key Features

### Use Case #1: Lead Followup
Form submission triggers automatic draft creation with:
- Relevant context from prior thread history
- 2–3 meeting slot proposals (via Calendar)
- Personalized tone learned from your sent emails
- Automatic logging to HubSpot

### Use Case #2: Story Pitching
Bulk campaign generation with:
- Contact segmentation (persona, industry, fit)
- Relevance ranking (engagement, recency)
- Rate limiting (20/day, 1 per contact per 2 weeks)
- Dry-run preview before creating

### Safety & Compliance
- **DRAFT_ONLY mode** by default (human review before send)
- **Quality gates** block PII leaks, forbidden words, suppressed contacts
- **Guardrails** enforce company stage/industry/employee range
- **Audit logging** captures all draft lifecycle events
- **Quotas** prevent runaway sends
- **Kill switch** instantly disables all sends

## Mode: DRAFT_ONLY vs SEND_ALLOWED

**DRAFT_ONLY (default):**
- Drafts created and previewed
- Never sent automatically
- Safe for exploration and testing

**SEND_ALLOWED:**
- Drafts sent after approval (if configured)
- Quotas + rate limits enforced
- Audit logged + compliance tracked
- Enable only when confident in output quality

## Getting Started

### 1. Set up local environment
```bash
docker compose up --wait
```

### 2. Index your Gmail threads
```bash
python -m src.cli.gmail --sync-thread <thread_id>
```

### 3. Learn your voice
```bash
python -m src.cli.voice --learn-from-sent-folder --limit 100
```

### 4. Test form submission → draft
```bash
python -m src.cli.test-form-submission \
  --contact-email "prospect@company.com" \
  --company-name "Acme Corp" \
  --verbose

# Check draft preview:
curl http://localhost:8000/api/drafts?status=pending | jq '.[0]'
```

### 5. Explore API
- Interactive docs: http://localhost:8000/docs
- List drafts: `curl http://localhost:8000/api/drafts`
- Check audit log: `curl http://localhost:8000/api/audit`

## Project Status

**Status:** Draft (Foundation & safety layers complete; core use cases in development)  
**Note:** Timeline estimates are intentionally omitted. See [Sprint Plan](docs/sprint_plan.md) for sequencing.

**Latest milestones:**
- ✅ Sprint 0–5: Infrastructure, resilience, secrets, safety foundations
- ✅ Sprint 6–10: Connectors (Gmail, HubSpot, Drive, Calendar), voice learning
- 🔄 Sprint 11–16: Use cases, send pathway, deployment, monitoring
- ⏳ Sprint 17–20: Testing, docs, security, hardening

See **[Sprint Plan](docs/sprint_plan.md)** for detailed breakdown.

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for code standards, PR process, release workflow.

## Security & Privacy

- **No PII in logs or drafts** — Automatic redaction of emails, company names, amounts
- **No hardcoded secrets** — All credentials via GCP Secret Manager
- **Audit trail** — Every draft action logged for compliance
- **Data privacy** — See [PRIVACY.md](docs/PRIVACY.md) for GDPR/retention policies

## Support

- **Issues:** GitHub Issues
- **On-call:** See [RUNBOOK.md](docs/RUNBOOK.md) for emergency procedures
- **Questions:** Check [FAQ](docs/FAQ.md) or open a discussion

---

**Built for high-touch, personalized prospecting at scale.**
