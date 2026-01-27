# DRAFT_ONLY Mode: Complete Setup Guide

## Overview

This guide walks through setting up the sales agent for **DRAFT_ONLY mode**—the first phase where all prospecting workflows run end-to-end, but emails are created as drafts rather than sent automatically.

**Key Points:**
- ✅ No emails sent automatically
- ✅ All drafts created and waiting for approval
- ✅ Full integration with Gmail, HubSpot, Calendar
- ✅ Google OAuth for local development
- ✅ HubSpot form webhooks for lead capture
- ✅ E2E smoke test validating entire workflow

---

## What's Included

### 1. Secrets Readiness Checker (`make secrets-check`)
Validates that all required environment variables are set before deployment.

**Location:** `src/cli/secrets_check.py`  
**Docs:** [docs/SECRETS_CHECK.md](docs/SECRETS_CHECK.md)

```bash
make secrets-check           # Check critical vars
make secrets-check-strict   # Check all vars
make secrets-check-json     # JSON output for CI
```

### 2. Google OAuth Setup (`make auth-google`)
Secure authentication for Gmail, Drive, and Calendar access. Tokens stored locally, never committed.

**Location:** `src/auth/google_oauth.py` + `src/commands/auth_google.py`  
**Docs:** [docs/GOOGLE_OAUTH.md](docs/GOOGLE_OAUTH.md)

```bash
make auth-google            # Interactive setup
python -m src.commands.auth_google --info    # Check token status
python -m src.commands.auth_google --revoke  # Delete token
```

### 3. HubSpot Form Webhook (`POST /api/webhooks/hubspot/form-submission`)
Receive form submissions from HubSpot and queue prospecting workflow.

**Location:** `src/routes/webhooks.py`  
**Docs:** [docs/HUBSPOT_WEBHOOK.md](docs/HUBSPOT_WEBHOOK.md)

```bash
# Test the webhook
curl http://localhost:8000/api/webhooks/hubspot/form-submission/example-payload

# Test validation
curl -X POST http://localhost:8000/api/webhooks/hubspot/form-submission/test \
  -H "Content-Type: application/json" -d @payload.json
```

### 4. E2E Smoke Test (`make smoke-formlead`)
Complete end-to-end validation of the workflow in DRAFT_ONLY mode.

**Location:** `src/commands/smoke_formlead.py`  
**Workflow:**
1. Load form submission payload
2. Resolve HubSpot contact/company
3. Search Gmail for existing threads
4. Extract thread context
5. Query Calendar for availability
6. Create Gmail draft reply
7. Create HubSpot note & task

```bash
make smoke-formlead                              # Run with mocks
make smoke-formlead --no-gmail --no-calendar   # Skip some services
python -m src.commands.smoke_formlead --input=payload.json  # Custom payload
```

### 5. Integration Tests with Mocks
Comprehensive test suite covering webhooks and E2E workflows.

**Location:** `tests/integration/test_webhooks.py`  
**Tests:**
- Webhook validation (required fields, form ID)
- Payload extraction (email, name, company)
- E2E smoke test execution
- Security validation
- Large payload handling

```bash
make test                    # Run all tests
make test-integration       # Integration tests only
```

### 6. Manual Validation Checklist
Step-by-step checklist for validating the entire system before production.

**Location:** [docs/MANUAL_VALIDATION_CHECKLIST.md](docs/MANUAL_VALIDATION_CHECKLIST.md)

---

## Quick Start (5 Minutes)

### 1. Check Secrets
```bash
make secrets-check
```
Should show all critical vars are set (or indicate missing ones).

### 2. Setup Google OAuth
```bash
make auth-google
```
Follows you through browser login. Token saved to `.tokens/google_tokens.json`.

### 3. Run Smoke Test
```bash
make smoke-formlead
```
Should show all 7 steps completing successfully in DRAFT_ONLY mode.

---

## Detailed Setup

### Phase 1: Environment Variables

Create `.env` from template:
```bash
cp .env.example .env
```

Edit `.env` with your values:
```bash
# Critical (must be set)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/sales_agent
REDIS_URL=redis://localhost:6379/0
API_HOST=0.0.0.0
API_PORT=8000

# Required (for full functionality)
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
HUBSPOT_API_KEY=pat-na1-xxx
OPENAI_API_KEY=sk-xxx

# Optional (can leave as is)
OPERATOR_MODE_ENABLED=true
OPERATOR_APPROVAL_REQUIRED=true
```

Validate:
```bash
make secrets-check
```

### Phase 2: Google OAuth Setup

**Prerequisites:**
1. [Google Cloud Console](https://console.cloud.google.com/) account
2. Create OAuth 2.0 Desktop app
3. Download credentials as `client_secret.json`

**Setup:**
```bash
make auth-google
```

Follow the interactive prompts. Browser opens → You log in → Grant permissions → Token saved.

**Verify:**
```bash
python -m src.commands.auth_google --info
# Should show: Status: VALID, Expires in: 700+ hours
```

### Phase 3: HubSpot Form Webhook

**In HubSpot:**
1. Go to Settings → Integrations → Webhooks
2. Create webhook:
   - URL: `http://localhost:8000/api/webhooks/hubspot/form-submission/test`
   - Trigger: Form submission
   - Form: Your lead capture form
3. Click "Test" to validate

**Verify Locally:**
```bash
curl http://localhost:8000/api/webhooks/hubspot/form-submission/example-payload
```

### Phase 4: Run E2E Test

```bash
make smoke-formlead
```

Should output:
```
SMOKE TEST COMPLETE ✓
======================================================================
Results:
  Draft ID:  draft-20260120013746
  Task ID:   task-20260120013746
  Status:    SUCCESS

Mode: DRAFT_ONLY
  → Draft created but NOT sent
  → Task created in HubSpot
  → Operator review required before send
```

---

## Workflow Diagram

```
┌─────────────────────────────────────┐
│  HubSpot Form Submission            │
│  (Lead fills out demo request)      │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  POST /api/webhooks/hubspot/...     │
│  (Webhook triggered)                │
└─────────────┬───────────────────────┘
              │
        ┌─────┴──────────────┬──────────────────┬──────────────┐
        ▼                    ▼                  ▼              ▼
    ┌──────────┐        ┌────────────┐  ┌─────────────┐  ┌────────┐
    │ HubSpot  │        │   Gmail    │  │  Calendar   │  │ Draft  │
    │ Resolve  │        │   Search   │  │  Check      │  │ Reply  │
    │ Contact  │        │ Existing   │  │ Availability│  │ Created│
    └──────────┘        │ Threads    │  └─────────────┘  └────────┘
        │                └────────────┘         │              │
        │                      │                │              │
        └──────────┬───────────┴────────────────┴──────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Create HubSpot Task  │
        │ + Note               │
        │ + Follow-up Date     │
        └──────────┬───────────┘
                   │
         ┌─────────┴─────────┐
         │                   ▼
    DRAFT_ONLY          Operator
     (Not sent)          Review
         │              Required
         │                   │
         └────────┬──────────┘
                  ▼
         Ready for Approval
        (Operator can send manually)
```

---

## File Structure

```
.
├── Makefile                                # Build & command shortcuts
├── .env.example                            # Environment variables template
├── .env                                    # (gitignored) Your actual secrets
├── .tokens/                                # (gitignored) Google OAuth tokens
│
├── src/
│   ├── cli/
│   │   └── secrets_check.py               # Secrets validation CLI
│   ├── commands/
│   │   ├── auth_google.py                 # Google OAuth command
│   │   └── smoke_formlead.py              # E2E smoke test
│   ├── auth/
│   │   └── google_oauth.py                # OAuth2 manager
│   ├── routes/
│   │   ├── webhooks.py                    # HubSpot webhook route
│   │   ├── agents.py                      # Agent endpoints
│   │   └── operator.py                    # Operator mode endpoints
│   └── main.py                             # FastAPI app
│
├── tests/
│   ├── unit/
│   │   └── [existing unit tests]
│   └── integration/
│       └── test_webhooks.py               # Webhook & smoke tests
│
├── docs/
│   ├── SECRETS_CHECK.md                   # Secrets checker guide
│   ├── GOOGLE_OAUTH.md                    # OAuth setup guide
│   ├── HUBSPOT_WEBHOOK.md                 # Webhook configuration
│   ├── MANUAL_VALIDATION_CHECKLIST.md    # Full validation steps
│   └── [other docs]
│
└── README.md                               # Project overview
```

---

## Commands Reference

### Validation & Setup
```bash
make help                   # Show all commands
make secrets-check         # Validate environment variables
make auth-google           # Set up Google OAuth
```

### Docker & Services
```bash
make docker-build          # Build image
make docker-up             # Start services
make docker-down           # Stop services
make docker-logs           # View logs
```

### Testing & Validation
```bash
make test                  # Run all tests
make test-unit             # Unit tests only
make test-integration      # Integration tests
make test-smoke            # Smoke tests
make smoke-formlead        # E2E workflow test
make coverage              # Test coverage report
```

### Development
```bash
make install               # Install dependencies
make dev                   # Install dev dependencies
make lint                  # Lint code
make format                # Format code
make pre-commit            # Run pre-commit hooks
```

### Cleanup
```bash
make clean                 # Remove artifacts
make clean-all             # Clean + remove venv
```

---

## Troubleshooting

### API Not Starting
```bash
# Check secrets
make secrets-check

# Start Docker services
make docker-up

# Check logs
docker compose logs api
```

### Google OAuth Error
```bash
# Check token is valid
python -m src.commands.auth_google --info

# Re-authorize
python -m src.commands.auth_google --revoke
make auth-google
```

### Webhook Validation Failed
```bash
# Check example payload
curl http://localhost:8000/api/webhooks/hubspot/form-submission/example-payload

# Validate your form ID is in EXPECTED_FORM_IDS
grep -n "EXPECTED_FORM_IDS" src/routes/webhooks.py

# Test with example payload
curl -X POST http://localhost:8000/api/webhooks/hubspot/form-submission/test \
  -H "Content-Type: application/json" \
  -d @example-payload.json
```

### Smoke Test Failed
```bash
# Run with mock services
make smoke-formlead

# Check if all secrets are set
make secrets-check

# Run tests to check dependencies
make test
```

---

## Architecture Overview

### Security Model
- **Google OAuth tokens:** Stored securely in `.tokens/` (0600 permissions, gitignored)
- **HubSpot API key:** In environment variables (never in code)
- **OpenAI API key:** In environment variables (never in code)
- **Database credentials:** In environment variables
- **Webhook validation:** Form ID checking, email required

### Integration Points
- **Gmail API:** Read threads, create drafts (no send in DRAFT_ONLY)
- **Google Calendar API:** Check availability, propose slots
- **Google Drive API:** Search for proposals (not used in basic workflow)
- **HubSpot API:** Resolve contacts, create tasks & notes
- **OpenAI API:** Generate response suggestions

### Mode: DRAFT_ONLY
- Emails created as drafts
- Not sent automatically
- Operator approval required
- HubSpot task created for follow-up
- Ready for manual operator send

---

## Next Phase: SEND_ALLOWED

After validating DRAFT_ONLY mode, next steps:

1. **Rate Limiting:** Enforce quota checks before send
2. **Send Pipeline:** Implement Gmail send via API
3. **Approval Workflow:** Optional operator review
4. **Delivery Tracking:** Monitor open/click/reply events
5. **Production Hardening:** Monitoring, alerting, backups

---

## Documentation

Complete documentation available:
- [docs/SECRETS_CHECK.md](docs/SECRETS_CHECK.md) — Secrets validation
- [docs/GOOGLE_OAUTH.md](docs/GOOGLE_OAUTH.md) — OAuth setup
- [docs/HUBSPOT_WEBHOOK.md](docs/HUBSPOT_WEBHOOK.md) — Webhook configuration
- [docs/MANUAL_VALIDATION_CHECKLIST.md](docs/MANUAL_VALIDATION_CHECKLIST.md) — Full validation
- [README.md](README.md) — Project overview
- [IMPLEMENTATION.md](IMPLEMENTATION.md) — Technical architecture

---

## Support

If you encounter issues:

1. Check logs: `docker compose logs -f api`
2. Validate secrets: `make secrets-check`
3. Run tests: `make test`
4. Review docs: See documentation links above
5. Open GitHub issue with error details

---

## Status

**Current Phase:** DRAFT_ONLY mode ✅  
**Features Working:**
- ✅ Form submission capture via webhooks
- ✅ Google OAuth for local development
- ✅ HubSpot contact resolution
- ✅ Gmail thread search
- ✅ Calendar availability check
- ✅ Gmail draft creation
- ✅ HubSpot task creation
- ✅ E2E smoke test

**Next Phase:** SEND_ALLOWED (coming soon)

---

**Last Updated:** January 20, 2026  
**Version:** 0.1.0  
**Status:** Ready for DRAFT_ONLY mode validation
