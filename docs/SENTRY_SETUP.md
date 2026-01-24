# Sentry Setup Guide

**Status:** ⚠️ Integration code ready, DSN not configured

## Current State
- Sentry SDK integration: ✅ Complete (`src/sentry_integration.py`)
- Test endpoint: ✅ Available (`POST /api/test-error`)
- DSN configured: ❌ Not set in Railway

## Setup Steps

### Step 1: Create Sentry Project (if needed)
1. Go to https://sentry.io
2. Create new project for "Python" + "FastAPI"
3. Copy the DSN from project settings

### Step 2: Configure Railway Environment
Add these environment variables in Railway:

```
SENTRY_DSN=https://xxxx@xxxx.ingest.sentry.io/xxxx
SENTRY_ENVIRONMENT=production
```

Optional (defaults shown):
```
SENTRY_TRACES_SAMPLE_RATE=0.1   # 10% of transactions
```

### Step 3: Verify Setup
After deploy, test with:

```bash
# Trigger a test error
curl -X POST https://web-production-a6ccf.up.railway.app/api/test-error

# Expected: Error should appear in Sentry within 30 seconds
```

### Step 4: Check Sentry Dashboard
- Go to Sentry project → Issues
- Look for "Test error for Sentry verification"

## What Gets Tracked

### Errors
- All unhandled exceptions
- Explicit error captures via `sentry_sdk.capture_exception()`
- HTTP 5xx responses

### Performance
- API endpoint latencies
- Database query durations
- Redis operations
- Celery task execution times

### Context
- Request path, method, headers (sanitized)
- User ID (if authenticated)
- Database and Redis connection status
- Custom tags for workflow IDs

## Integrations Enabled
- FastAPI (automatic transaction tracking)
- SQLAlchemy (query performance)
- Redis (cache operations)
- Celery (background tasks)
- Logging (captures warning+ logs)

## Security Notes
- PII is NOT sent by default (`send_default_pii=False`)
- Passwords and tokens are scrubbed from request data
- Stack traces are captured with context

## Files
- `src/sentry_integration.py` - SDK initialization
- `src/routes/ops.py` - Test error endpoint
- `src/config.py` - Environment variable loading

---
**Last Updated:** 2026-01-24
**Sprint:** 7.3
