# CaseyOS Signals Framework

**Version:** 1.0  
**Sprint:** 8  
**Status:** ✅ Production Ready

---

## Overview

Signals are the input layer of CaseyOS. They represent detected events from various sources that may warrant action recommendations in the command queue.

## Signal Sources

| Source | Description | Event Types |
|--------|-------------|-------------|
| `form` | HubSpot form submissions | `form_submitted` |
| `hubspot` | HubSpot CRM changes | `deal_stage_changed`, `contact_created` |
| `gmail` | Gmail thread updates | `reply_received`, `thread_created` |
| `manual` | User-initiated signals | `manual_entry` |

## Signal Model

```python
class Signal:
    id: str                    # UUID
    source: SignalSource       # Enum: form, hubspot, gmail, manual
    event_type: str            # Specific event (e.g. "form_submitted")
    payload: dict              # Raw event data from source
    processed_at: datetime     # When signal was processed (null if pending)
    recommendation_id: str     # FK to command_queue_items if generated
    source_id: str             # External ID (e.g. HubSpot contact ID)
    created_at: datetime       # When signal was received
```

## API Endpoints

### List Signals

```bash
GET /api/signals
```

**Query Parameters:**
- `source`: Filter by source (form, hubspot, gmail, manual)
- `processed`: Filter by processed status (true/false)
- `limit`: Max results (default: 20, max: 100)
- `offset`: Pagination offset

**Example:**
```bash
curl https://your-domain.com/api/signals?source=form&processed=false
```

**Response:**
```json
{
  "signals": [
    {
      "id": "abc-123",
      "source": "form",
      "event_type": "form_submitted",
      "payload": {"email": "lead@example.com", "company": "Acme"},
      "processed_at": null,
      "recommendation_id": null,
      "source_id": "hubspot-sub-456",
      "created_at": "2026-01-24T00:30:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

### Get Signal by ID

```bash
GET /api/signals/{signal_id}
```

### Signal Statistics

```bash
GET /api/signals/stats/summary
```

**Response:**
```json
{
  "total": 150,
  "processed": 120,
  "unprocessed": 30,
  "by_source": {
    "form": 80,
    "hubspot": 50,
    "gmail": 15,
    "manual": 5
  }
}
```

### Health Check

```bash
GET /api/signals/health
```

## Signal Processing Flow

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│  Source     │────▶│   Signal    │────▶│  Signal          │
│  (HubSpot,  │     │   Created   │     │  Processor       │
│  Gmail, etc)│     │             │     │                  │
└─────────────┘     └─────────────┘     └────────┬─────────┘
                                                 │
                                                 ▼
                    ┌─────────────┐     ┌──────────────────┐
                    │  Command    │◀────│  Recommendation  │
                    │  Queue      │     │  Generated       │
                    └─────────────┘     └──────────────────┘
```

## Signal Processors

### FormSubmissionSignalProcessor

Handles form submissions and creates `email_follow_up` recommendations.

**Trigger:** `source=form`, `event_type=form_submitted`

**Context Required:**
- `email` (required)
- `name` (optional)
- `company` (optional)

**APS Weights:**
- Revenue potential: 60% (default)
- Urgency: 90% (hot lead)
- Strategic value: 50% (default)
- Effort: 20% (low - template email)

### HubSpotDealSignalProcessor (Sprint 8.5)

*Coming soon*

### GmailReplySignalProcessor (Sprint 8.7)

*Coming soon*

## Telemetry Events

| Event | When | Data |
|-------|------|------|
| `signal_received` | Signal created | signal_id, source, event_type |
| `signal_processed` | Processor finished | signal_id, recommendation_generated |
| `recommendation_generated` | CQ item created | signal_id, recommendation_id, action_type |

## Database Schema

```sql
CREATE TABLE signals (
    id VARCHAR(36) PRIMARY KEY,
    source signal_source_enum NOT NULL,  -- enum: form, hubspot, gmail, manual
    event_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    processed_at TIMESTAMP,
    recommendation_id VARCHAR(36),
    source_id VARCHAR(128),
    created_at TIMESTAMP NOT NULL
);

-- Indexes
CREATE INDEX ix_signals_source ON signals(source);
CREATE INDEX ix_signals_event_type ON signals(event_type);
CREATE INDEX ix_signals_processed_at ON signals(processed_at);
CREATE INDEX ix_signals_created_at ON signals(created_at);
```

## Adding a New Signal Source

1. Add source to `SignalSource` enum in `src/models/signal.py`
2. Create processor class extending `SignalProcessor` in `src/services/signal_processors/`
3. Register processor in `SignalService.__init__`
4. Add migration if enum needs updating
5. Add unit tests in `tests/test_{source}_signal_processor.py`

---

**Last Updated:** 2026-01-24  
**Author:** CaseyOS Sprint 8
