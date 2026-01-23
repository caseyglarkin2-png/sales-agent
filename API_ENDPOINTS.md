# API Endpoints Reference

**Production URL**: https://web-production-a6ccf.up.railway.app

Quick reference for all API endpoints in the Sales Agent platform.

---

## Health & Status

```bash
GET /health
# Response: {"status": "ok"}
```

---

## Voice Training

### Ingest Content from URL
```bash
POST /api/voice/training/ingest/url
Content-Type: application/json

{
    "source_type": "youtube" | "drive" | "hubspot",
    "source_url": "https://...",
    "user_id": "uuid",
    "title": "optional"
}

# Response: TrainingSample object
```

### Upload File
```bash
POST /api/voice/training/ingest/upload
Content-Type: multipart/form-data

file: <file>
user_id: "uuid"
title: "optional"

# Response: TrainingSample object
```

### List Training Samples
```bash
GET /api/voice/training/samples?user_id={uuid}&limit={int}

# Response: Array of TrainingSample
```

### Get Training Stats
```bash
GET /api/voice/training/stats?user_id={uuid}

# Response:
{
    "total_samples": int,
    "total_content_length": int,
    "sources": {"youtube": int, "drive": int, ...},
    "embedding_coverage": float
}
```

### Delete Sample
```bash
DELETE /api/voice/training/samples/{sample_id}

# Response: {"message": "Sample deleted"}
```

---

## PII Detection & Safety

### Detect PII
```bash
POST /api/safety/detect-pii
Content-Type: application/json

{
    "content": "text to scan",
    "include_positions": false,
    "redact": false
}

# Response:
{
    "pii_detected": {
        "email": ["user@example.com"],
        "phone": ["555-1234"],
        ...
    },
    "has_pii": bool,
    "redacted_content": "optional",
    "redaction_map": {}
}
```

### Validate Safety
```bash
POST /api/safety/validate-safety
Content-Type: application/json

{
    "content": "text to validate",
    "context": "email",
    "strict_mode": false
}

# Response:
{
    "safe": bool,
    "warnings": ["..."],
    "pii_detected": {},
    "risk_score": float,
    "recommendation": "SAFE | REVIEW | BLOCK"
}
```

---

## Rate Limiting & Quotas

### Get Rate Limit Status
```bash
GET /api/quotas/rate-limits/{service}?user_id={uuid}

# Services: gmail, hubspot, openai, drive, calendar

# Response:
{
    "service": "gmail",
    "status": {
        "tokens_available": float,
        "capacity": int,
        "refill_rate": int,
        "utilization": float,
        "reset_at": timestamp
    }
}
```

### Get Quota Usage
```bash
GET /api/quotas/usage/{user_id}/{quota_type}?period={daily|weekly|monthly}

# Quota types: emails_sent, workflows_triggered, api_calls

# Response:
{
    "used": int,
    "period": "daily",
    "resets_at": "ISO datetime"
}
```

### Get Quota Dashboard
```bash
GET /api/quotas/dashboard/{user_id}

# Response:
{
    "user_id": "uuid",
    "rate_limits": {
        "gmail": {...},
        "hubspot": {...}
    },
    "quotas": {
        "emails_sent": {
            "daily": {...},
            "weekly": {...}
        }
    }
}
```

---

## Webhooks (Phase 4)

### HubSpot Form Webhook
```bash
POST /api/webhooks/hubspot/forms
Content-Type: application/json
X-HubSpot-Signature: <hmac-sha256>

# HubSpot form submission payload
```

---

## Dashboard (Phase 4)

### Get Dashboard Stats
```bash
GET /api/dashboard/stats

# Response:
{
    "total_workflows": int,
    "active_workflows": int,
    "completed_today": int,
    "error_rate": float
}
```

### List Workflows
```bash
GET /api/dashboard/workflows?limit={int}&status={status}

# Response: Array of workflow objects
```

---

## Analytics & Insights

### Get Workflow Metrics
```bash
GET /api/analytics/metrics?time_window={hour|day|week|month|all_time}

# Response:
{
    "total_workflows": int,
    "completed": int,
    "failed": int,
    "processing": int,
    "completion_rate": float,
    "avg_duration_seconds": float,
    "throughput_per_hour": float
}
```

### Get Mode Distribution
```bash
GET /api/analytics/mode-distribution?time_window={day}

# Response:
{
    "draft_only": int,
    "send": int,
    "draft_only_pct": float,
    "send_pct": float
}
```

### Get Error Analysis
```bash
GET /api/analytics/errors?time_window={day}&limit={10}

# Response:
{
    "error_rate": float,
    "top_errors": [{"message": str, "count": int}],
    "retry_stats": {"avg_retries": float, "max_retries": int}
}
```

### Get Performance Trends
```bash
GET /api/analytics/trends/{metric}?granularity={hour}&points={24}

# Metrics: completion_rate, throughput, error_rate
# Response: Time-series data points
```

### Get Comprehensive Dashboard
```bash
GET /api/analytics/dashboard?time_window={day}

# Response: All metrics + trends + error analysis
```

### Get Recovery Stats
```bash
GET /api/analytics/recovery/stats

# Response:
{
    "by_status": {"completed": int, "failed": int},
    "stuck_workflows": int,
    "eligible_for_retry": int
}
```

### Auto-Recover Stuck Workflows
```bash
POST /api/analytics/recovery/auto-recover?timeout_minutes={10}&max_to_recover={50}

# Response: {"recovered": int}
```

### Retry Failed Workflows
```bash
POST /api/analytics/recovery/retry-failed?max_retries={3}&max_to_retry={50}

# Response: {"retried": int}
```

---

## Admin (Feature Flags)

### List Feature Flags
```bash
GET /api/admin/flags

# Response: Array of feature flags
```

### Toggle Feature Flag
```bash
POST /api/admin/flags/{flag_name}/toggle
Content-Type: application/json

{
    "enabled": bool,
    "reason": "optional"
}
```

### Kill Switch
```bash
POST /api/admin/kill-switch
Content-Type: application/json

{
    "activate": bool,
    "reason": "emergency stop"
}
```

---

## UI Pages

- **/voice-training.html** - Voice training upload interface
- **/operator-dashboard.html** - Workflow monitoring dashboard

---

## Authentication Headers

Most endpoints require authentication (to be implemented):
```
Authorization: Bearer <token>
```

For now, using demo user IDs for testing.

---

## Error Responses

Standard error format:
```json
{
    "detail": "Error message",
    "status_code": 400
}
```

HTTP Status Codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error
- `503` - Service Unavailable

---

## Rate Limits

| Service | Burst Capacity | Refill Rate | Notes |
|---------|----------------|-------------|-------|
| Gmail | 100 tokens | 60/min | Google API limits |
| HubSpot | 150 tokens | 600/min | 10/second sustained |
| OpenAI | 60 tokens | 60/min | Tier-dependent |
| Drive | 100 tokens | 100/min | - |
| Calendar | 50 tokens | 50/min | - |

---

## Quick Test Commands

```bash
# Health check
curl https://web-production-a6ccf.up.railway.app/health

# Ingest YouTube video
curl -X POST https://web-production-a6ccf.up.railway.app/api/voice/training/ingest/url \
  -H "Content-Type: application/json" \
  -d '{"source_type":"youtube","source_url":"https://youtube.com/watch?v=dQw4w9WgXcQ","user_id":"demo-123"}'

# Check PII
curl -X POST https://web-production-a6ccf.up.railway.app/api/safety/detect-pii \
  -H "Content-Type: application/json" \
  -d '{"content":"Email me at test@example.com or call 555-1234"}'

# Rate limit status
curl https://web-production-a6ccf.up.railway.app/api/quotas/rate-limits/gmail
```

---

**Last Updated**: January 23, 2026  
**Version**: Phase 4 Complete
