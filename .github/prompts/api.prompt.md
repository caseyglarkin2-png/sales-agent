# Test API Endpoint

Test an API endpoint in production.

## Instructions

1. For GET requests:
```bash
curl https://web-production-a6ccf.up.railway.app/api/endpoint
```

2. For POST requests (need CSRF):
```bash
# Get CSRF token first
CSRF=$(curl -sI https://web-production-a6ccf.up.railway.app/health | grep -i x-csrf-token | cut -d' ' -f2 | tr -d '\r')

# Then make POST request
curl -X POST https://web-production-a6ccf.up.railway.app/api/endpoint \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"key": "value"}'
```

3. For admin endpoints:
```bash
curl -X POST https://web-production-a6ccf.up.railway.app/api/admin/endpoint \
  -H "X-Admin-Token: $ADMIN_PASSWORD" \
  -H "X-CSRF-Token: $CSRF"
```

## Key Endpoints
- `/health` - Health check
- `/ready` - Readiness (DB + Redis)
- `/api/command-queue/today` - Today's Moves
- `/api/command-queue` - All queue items
- `/api/signals/health` - Signals system
- `/api/actions/status` - Action executor
- `/api/actions/types` - Available action types
