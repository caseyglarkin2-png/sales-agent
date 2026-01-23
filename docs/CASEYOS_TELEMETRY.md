# CaseyOS Telemetry & Events

**Version:** 1.0  
**Last Updated:** January 23, 2026  
**Purpose:** Track system behavior, user actions, and outcomes for CaseyOS command center

---

## Telemetry Philosophy

**Why We Track:**
- Measure recommendation acceptance rate (are we surfacing the right things?)
- Track outcome conversion funnel (draft → sent → reply → meeting → deal)
- Monitor system health (latency, error rates, integration uptime)
- Feed data back into APS scoring (learn what works)

**What We Don't Track:**
- PII beyond what's necessary (email address, name, company only)
- User behavior outside the command queue
- Personally identifiable browsing patterns

---

## Event Taxonomy

### **Recommendation Events**

#### `recommendation_generated`
**When:** APS score calculated for a new action.

**Properties:**
```json
{
  "event": "recommendation_generated",
  "recommendation_id": "uuid",
  "aps_score": 87.5,
  "action_type": "send_email",
  "revenue_impact": 50000,
  "urgency_days": 1,
  "effort_minutes": 15,
  "icp_score": 0.9,
  "reasoning": "High pipeline value ($50k ARR), demo tomorrow (urgent), strong ICP fit",
  "signal_source": "hubspot",  // What triggered this recommendation
  "signal_type": "form_submitted",
  "timestamp": "2026-01-23T14:30:00Z"
}
```

**Usage:** Track how many recommendations we generate per day, distribution of APS scores.

---

#### `recommendation_viewed`
**When:** User views "Today's Moves" page or hits `/api/command-queue/today`.

**Properties:**
```json
{
  "event": "recommendation_viewed",
  "user_id": "casey",
  "recommendations_shown": 10,
  "top_score": 87.5,
  "bottom_score": 42.3,
  "timestamp": "2026-01-23T14:35:00Z"
}
```

**Usage:** Track engagement with command queue.

---

#### `recommendation_accepted`
**When:** User clicks "Execute" on a recommendation.

**Properties:**
```json
{
  "event": "recommendation_accepted",
  "recommendation_id": "uuid",
  "queue_item_id": "uuid",
  "aps_score": 87.5,
  "action_type": "send_email",
  "user_id": "casey",
  "time_to_decision_seconds": 15,  // How long user took to decide
  "timestamp": "2026-01-23T14:36:00Z"
}
```

**Usage:** Calculate acceptance rate, identify which score ranges get accepted.

---

#### `recommendation_dismissed`
**When:** User clicks "Skip" on a recommendation.

**Properties:**
```json
{
  "event": "recommendation_dismissed",
  "recommendation_id": "uuid",
  "queue_item_id": "uuid",
  "aps_score": 87.5,
  "action_type": "send_email",
  "user_id": "casey",
  "dismiss_reason": "not_relevant",  // Optional user feedback
  "timestamp": "2026-01-23T14:37:00Z"
}
```

**Usage:** Learn what recommendations are not helpful, tune APS scoring.

---

### **Action Execution Events**

#### `action_executed`
**When:** Automated action performed (email sent, task created, etc.).

**Properties:**
```json
{
  "event": "action_executed",
  "action_id": "uuid",
  "action_type": "send_email",
  "execution_mode": "automated",  // "automated" | "manual" | "dry_run"
  "success": true,
  "error": null,
  "duration_ms": 450,
  "metadata": {
    "recipient": "john@acmecorp.com",
    "subject": "Follow up: Demo tomorrow",
    "gmail_message_id": "msg_123"
  },
  "timestamp": "2026-01-23T14:38:00Z"
}
```

**Usage:** Track execution success rate, identify failing actions.

---

#### `action_failed`
**When:** Automated action fails (API error, validation error, etc.).

**Properties:**
```json
{
  "event": "action_failed",
  "action_id": "uuid",
  "action_type": "send_email",
  "error_type": "api_error",  // "api_error" | "validation_error" | "rate_limit"
  "error_message": "Gmail API: Daily sending limit exceeded",
  "retryable": false,
  "timestamp": "2026-01-23T14:39:00Z"
}
```

**Usage:** Alert on failure spikes, improve error handling.

---

#### `action_rolled_back`
**When:** Action is undone (delete draft, cancel task, etc.).

**Properties:**
```json
{
  "event": "action_rolled_back",
  "action_id": "uuid",
  "action_type": "send_email",
  "rollback_reason": "user_requested",  // "user_requested" | "failed_validation" | "duplicate_detected"
  "rollback_success": true,
  "timestamp": "2026-01-23T14:40:00Z"
}
```

**Usage:** Track how often we need to undo actions.

---

### **Outcome Events**

#### `outcome_reply_received`
**When:** Email reply detected for a sent draft.

**Properties:**
```json
{
  "event": "outcome_reply_received",
  "draft_id": "uuid",
  "action_id": "uuid",
  "recommendation_id": "uuid",
  "recipient": "john@acmecorp.com",
  "time_to_reply_hours": 4.5,
  "reply_sentiment": "positive",  // Optional: "positive" | "neutral" | "negative"
  "timestamp": "2026-01-23T18:30:00Z"
}
```

**Usage:** Calculate reply rate by ICP tier, subject line, time of day.

---

#### `outcome_meeting_booked`
**When:** Meeting scheduled (detected via calendar API or CRM update).

**Properties:**
```json
{
  "event": "outcome_meeting_booked",
  "draft_id": "uuid",
  "action_id": "uuid",
  "recommendation_id": "uuid",
  "attendee": "john@acmecorp.com",
  "meeting_time": "2026-01-24T14:00:00Z",
  "time_to_book_hours": 24,
  "timestamp": "2026-01-23T20:00:00Z"
}
```

**Usage:** Track meeting booking rate, optimize call-to-action.

---

#### `outcome_deal_advanced`
**When:** Deal moves to next stage in CRM.

**Properties:**
```json
{
  "event": "outcome_deal_advanced",
  "deal_id": "hs_deal_123",
  "recommendation_id": "uuid",  // Which recommendation led to this
  "old_stage": "SQL",
  "new_stage": "Opportunity",
  "pipeline_value": 50000,
  "timestamp": "2026-01-24T10:00:00Z"
}
```

**Usage:** Attribute revenue to specific recommendations, calculate ROI of CaseyOS.

---

#### `outcome_deliverable_shipped`
**When:** Client deliverable marked as complete.

**Properties:**
```json
{
  "event": "outcome_deliverable_shipped",
  "deliverable_id": "uuid",
  "client": "Acme Corp",
  "deliverable_type": "onboarding_doc",
  "on_time": true,
  "timestamp": "2026-01-24T12:00:00Z"
}
```

**Usage:** Track fulfillment velocity, identify bottlenecks.

---

### **Signal Ingestion Events**

#### `signal_received`
**When:** New signal captured (form submission, CRM update, email reply).

**Properties:**
```json
{
  "event": "signal_received",
  "signal_id": "uuid",
  "source": "hubspot",  // "hubspot" | "gmail" | "calendar" | "webhook"
  "signal_type": "deal_stage_changed",
  "processed": false,
  "timestamp": "2026-01-23T14:25:00Z"
}
```

**Usage:** Monitor signal ingestion rate, detect polling failures.

---

#### `signal_processed`
**When:** Signal processed by SignalProcessor.

**Properties:**
```json
{
  "event": "signal_processed",
  "signal_id": "uuid",
  "source": "hubspot",
  "signal_type": "deal_stage_changed",
  "recommendation_generated": true,
  "processing_duration_ms": 850,
  "timestamp": "2026-01-23T14:26:00Z"
}
```

**Usage:** Track signal processing latency, identify bottlenecks.

---

### **Integration Health Events**

#### `integration_call_success`
**When:** API call to integration succeeds.

**Properties:**
```json
{
  "event": "integration_call_success",
  "integration": "hubspot",  // "hubspot" | "gmail" | "calendar"
  "endpoint": "/crm/v3/objects/deals",
  "method": "GET",
  "status_code": 200,
  "duration_ms": 350,
  "timestamp": "2026-01-23T14:30:00Z"
}
```

**Usage:** Monitor integration latency p50/p95/p99.

---

#### `integration_call_failed`
**When:** API call to integration fails.

**Properties:**
```json
{
  "event": "integration_call_failed",
  "integration": "hubspot",
  "endpoint": "/crm/v3/objects/deals",
  "method": "GET",
  "status_code": 429,  // Rate limit
  "error_message": "Rate limit exceeded",
  "retryable": true,
  "timestamp": "2026-01-23T14:31:00Z"
}
```

**Usage:** Alert on integration failures, track error rate.

---

#### `circuit_breaker_opened`
**When:** Circuit breaker opens due to failures.

**Properties:**
```json
{
  "event": "circuit_breaker_opened",
  "service": "hubspot",
  "failure_count": 5,
  "threshold": 5,
  "timestamp": "2026-01-23T14:32:00Z"
}
```

**Usage:** Alert ops team, prevent cascading failures.

---

## Instrumentation Strategy

### **Where to Track Events**

1. **Sentry Breadcrumbs** (all events)
   - Automatically captured with stack traces
   - 100% retention for errors
   - 10% sampling for successful events

2. **Structured Logs** (all events)
   - JSON format for easy parsing
   - Stored in Railway logs
   - 7-day retention (free tier)

3. **Database (outcomes only)**
   - Store outcomes in `outcome_events` table
   - Enables SQL queries for analysis
   - Unlimited retention

### **Event Decorator Pattern**

```python
# src/telemetry/events.py
import time
import sentry_sdk
from functools import wraps
from src.logger import get_logger

logger = get_logger(__name__)

def track_event(event_name: str, properties: dict = None):
    """Decorator to track events."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                
                # Build event payload
                event_data = {
                    "event": event_name,
                    "duration_ms": duration_ms,
                    "timestamp": datetime.utcnow().isoformat(),
                    **(properties or {})
                }
                
                # Log to Sentry breadcrumb
                sentry_sdk.add_breadcrumb({
                    "category": "telemetry",
                    "message": event_name,
                    "level": "info",
                    "data": event_data
                })
                
                # Log to structured logger
                logger.info(f"Event: {event_name}", extra=event_data)
                
                return result
                
            except Exception as e:
                # Track failure event
                error_data = {
                    "event": f"{event_name}_failed",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                logger.error(f"Event failed: {event_name}", extra=error_data)
                sentry_sdk.capture_exception(e)
                raise
                
        return wrapper
    return decorator

# Usage:
@track_event("recommendation_generated")
async def calculate_aps_score(revenue, urgency, effort, icp):
    ...
```

---

## Dashboards (Sentry)

### **Command Queue Health Dashboard**

**Metrics:**
- Recommendations generated per day
- Acceptance rate (% of recommendations executed)
- Average APS score of accepted vs dismissed
- Time to decision (how long users take to accept/dismiss)

**Queries:**
```sql
-- Acceptance rate
SELECT 
  COUNT(*) FILTER (WHERE event='recommendation_accepted') / 
  COUNT(*) FILTER (WHERE event='recommendation_generated') AS acceptance_rate
FROM events
WHERE timestamp > NOW() - INTERVAL '7 days';
```

---

### **Outcome Conversion Funnel**

**Metrics:**
- Draft → Sent (execution rate)
- Sent → Replied (reply rate)
- Replied → Meeting Booked (booking rate)
- Meeting → Deal Advanced (conversion rate)

**Visualization:**
```
Recommendations Generated: 100
    ↓ 70% accepted
Actions Executed: 70
    ↓ 40% replied
Replies Received: 28
    ↓ 60% booked
Meetings Booked: 17
    ↓ 50% advanced
Deals Advanced: 8
```

---

### **Integration Health Dashboard**

**Metrics:**
- API call latency (p50, p95, p99)
- Error rate by integration
- Circuit breaker status
- Rate limit hits per day

**Alerts:**
- Error rate > 5% → Page on-call
- Latency p99 > 2s → Warning
- Circuit breaker open → Immediate alert

---

## Privacy & Compliance

### **PII Handling**
- **Stored:** email address, name, company (necessary for functionality)
- **Not Stored:** Full email body content (only subject + metadata)
- **Retention:** 90 days for events, 1 year for outcomes

### **GDPR Compliance**
- `DELETE /api/gdpr/user/{email}` deletes all events for user
- Event data anonymized after 90 days (email → hash)
- User can request export of all tracked events

### **Data Minimization**
- Only track events necessary for functionality
- No tracking of user behavior outside command queue
- No third-party analytics (Sentry only)

---

## Implementation Checklist

### Sprint 7 (Foundation)
- [ ] Create `@track_event` decorator
- [ ] Track `recommendation_generated`
- [ ] Track `recommendation_viewed`
- [ ] Wire events to Sentry breadcrumbs
- [ ] Wire events to structured logs

### Sprint 8 (Signals)
- [ ] Track `signal_received`
- [ ] Track `signal_processed`
- [ ] Track integration health events

### Sprint 9 (Execution)
- [ ] Track `action_executed`
- [ ] Track `action_failed`
- [ ] Track `recommendation_accepted/dismissed`

### Sprint 10 (Outcomes)
- [ ] Track `outcome_reply_received`
- [ ] Track `outcome_meeting_booked`
- [ ] Track `outcome_deal_advanced`
- [ ] Create outcome analysis queries

---

**Telemetry is required, not optional. If we can't measure it, we can't improve it.**
