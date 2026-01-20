# Secrets Readiness Checker

## Overview

The secrets readiness checker validates that all required environment variables are set before deployment. It's designed to fail CI/CD pipelines if any critical secrets are missing.

**Location:** `src/cli/secrets_check.py`  
**Usage:** `make secrets-check` or `python -m src.cli.secrets_check`

---

## Environment Variable Categories

### CRITICAL (Must Be Set)
These variables must be set in all environments:
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `API_HOST` — FastAPI host (default: 0.0.0.0)
- `API_PORT` — FastAPI port (default: 8000)

### REQUIRED (Should Be Set)
These variables are required for full functionality:
- `GOOGLE_CLIENT_ID` — Google OAuth 2.0 Client ID
- `GOOGLE_CLIENT_SECRET` — Google OAuth 2.0 Client Secret
- `GOOGLE_REDIRECT_URI` — Google OAuth 2.0 Redirect URI
- `HUBSPOT_API_KEY` — HubSpot API key
- `OPENAI_API_KEY` — OpenAI API key

In CI/CD, missing REQUIRED variables fail the check unless `DEV_MODE=1` is set.

### OPTIONAL (Can Be Omitted)
These variables are optional:
- `HUBSPOT_APP_ID` — HubSpot app ID (for private app)
- `OPENAI_MODEL` — OpenAI model name (default: gpt-4-turbo-preview)
- Feature flags (`FEATURE_*`)
- `OPERATOR_MODE_ENABLED` — Enable operator mode

---

## Usage

### Check Critical Vars Only (Default)
```bash
make secrets-check
# or
python -m src.cli.secrets_check
```

Output (pass):
```
======================================================================
SECRETS READINESS CHECK
======================================================================
Status: PASS
Timestamp: 2026-01-20T12:34:56Z

SUMMARY
----------------------------------------------------------------------
  ✓ Present: 9 | ✗ Missing: 0 | ⚠ Invalid: 0

DETAILS
----------------------------------------------------------------------
  ✓ DATABASE_URL                 [critical ] OK
  ✓ REDIS_URL                    [critical ] OK
  ...

======================================================================
✅ PASSED - All required secrets are set
======================================================================
```

Output (fail):
```
======================================================================
SECRETS READINESS CHECK
======================================================================
Status: FAIL
Timestamp: 2026-01-20T12:34:56Z

SUMMARY
----------------------------------------------------------------------
  ✓ Present: 5 | ✗ Missing: 4 | ⚠ Invalid: 0

CRITICAL (Must be set):
  ✗ GOOGLE_CLIENT_ID
  ✗ GOOGLE_CLIENT_SECRET
  ✗ HUBSPOT_API_KEY

...

======================================================================
❌ FAILED - See critical issues above
This check is enforced in CI. Set missing variables before merging.
======================================================================
```

### Check All Vars (Including Optional)
```bash
make secrets-check-strict
# or
python -m src.cli.secrets_check --strict
```

### Output as JSON
For CI/CD pipeline integration:
```bash
make secrets-check-json
# or
python -m src.cli.secrets_check --json

# Output:
# {
#   "timestamp": "2026-01-20T12:34:56Z",
#   "strict_mode": false,
#   "status": "pass",
#   "summary": {"present": 9, "missing": 0, "invalid": 0},
#   "critical_missing": [],
#   "required_missing": [],
#   "exit_code": 0,
#   "results": { ... }
# }
```

### Development Mode
In local development, missing REQUIRED vars are tolerated:
```bash
DEV_MODE=1 make secrets-check
```

### Exit Codes
- `0` — All required secrets present
- `1` — Critical or required secrets missing, or invalid value detected

---

## CI/CD Integration

### GitHub Actions
```yaml
name: Secrets Readiness

on: [push, pull_request]

jobs:
  secrets-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install poetry
      - run: poetry install
      - run: make secrets-check
      - run: make secrets-check-json > secrets-report.json
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: secrets-report
          path: secrets-report.json
```

### Cloud Build
```dockerfile
# In Dockerfile or Cloud Build config
RUN python -m src.cli.secrets_check
```

### Before Deployment
```bash
# In deployment script
python -m src.cli.secrets_check || exit 1
docker build -t sales-agent:latest .
docker push gcr.io/project/sales-agent:latest
```

---

## Environment Variable Reference

### Database
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/sales_agent
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

### Cache
```bash
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### API
```bash
API_HOST=0.0.0.0
API_PORT=8000
API_ENV=development  # or production
API_LOG_LEVEL=INFO
```

### Google Integration
```bash
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxx
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

### HubSpot Integration
```bash
HUBSPOT_API_KEY=pat-na1-xxxxxxxxxxxxxxxxxxxx
HUBSPOT_APP_ID=123456  # optional, for private app
```

### OpenAI Integration
```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4-turbo-preview  # optional
```

### Feature Flags
```bash
FEATURE_COLD_START_DEMO=true
FEATURE_VALIDATION_AGENT=false
FEATURE_OUTCOME_REPORTER=false
```

### Operator Mode
```bash
OPERATOR_MODE_ENABLED=true
OPERATOR_APPROVAL_REQUIRED=true
MAX_EMAILS_PER_DAY=20
MAX_EMAILS_PER_WEEK=2
```

---

## Setup Instructions

### 1. Copy Example Env File
```bash
cp .env.example .env
```

### 2. Populate Required Variables
```bash
# Edit .env with actual values
GOOGLE_CLIENT_ID=your-actual-client-id
GOOGLE_CLIENT_SECRET=your-actual-secret
# ... etc
```

### 3. Run Check
```bash
make secrets-check
```

### 4. Add to Git Hooks (Optional)
To check secrets before every commit:

```bash
# Add to .git/hooks/pre-commit
#!/bin/bash
python -m src.cli.secrets_check || exit 1
```

Or use pre-commit framework:
```bash
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: secrets-check
      name: Secrets Readiness Check
      entry: python -m src.cli.secrets_check
      language: system
      stages: [commit]
```

---

## Troubleshooting

### "Missing CRITICAL: GOOGLE_CLIENT_ID"

**Cause:** You haven't set Google OAuth credentials.

**Fix:**
1. Create OAuth app in [Google Cloud Console](https://console.cloud.google.com/)
2. Get Client ID and Secret
3. Add to `.env`:
   ```bash
   GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-xxx
   ```
4. Re-run: `make secrets-check`

### "Invalid: API_PORT - Port must be numeric"

**Cause:** API_PORT is not a valid number.

**Fix:**
```bash
# In .env
API_PORT=8000  # Must be numeric
```

### "Check passes locally but fails in CI"

**Cause:** .env file not loaded in CI environment.

**Fix:**
1. Set env vars directly in CI secrets
2. Export before running:
   ```bash
   export GOOGLE_CLIENT_ID=...
   export GOOGLE_CLIENT_SECRET=...
   make secrets-check
   ```
3. Or use a secrets management tool (Google Secret Manager, GitHub Secrets, etc.)

---

## Implementation Notes

- The checker is **non-destructive** — it only reads env vars, doesn't modify anything
- All checks are **validation-only** — doesn't connect to external services
- Exit code is **shell-standard** — 0 for success, 1 for failure
- Output is **human and machine-readable** — use `--json` for CI/CD
- Validation is **extensible** — add new rules in `validate_var()` function

---

## Next Steps

After passing secrets check:
1. Run integration tests: `make test`
2. Start services: `make docker-up`
3. Verify health: `curl http://localhost:8000/health`
4. Try demo endpoints: `curl http://localhost:8000/api/agents/demo/prospecting`
