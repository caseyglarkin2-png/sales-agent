# HubSpot Form Webhook Setup

## Overview

The sales agent listens for form submissions from HubSpot and automatically:
1. Extracts contact information
2. Searches Gmail for existing threads with that email
3. Pulls thread context if found
4. Queries Calendar for availability
5. Creates a Gmail draft reply
6. Creates a HubSpot note and follow-up task

This guide walks through webhook configuration and local testing.

---

## Quick Start

### 1. Configure Webhook in HubSpot

**Portal URL:** `https://app.hubspot.com/` → Select your account

**Step 1: Go to Webhooks**
```
Settings → Integrations → Webhooks
```

**Step 2: Create New Webhook**
```
Click "+ Create webhook"
```

**Step 3: Webhook Configuration**
```
Trigger Type:       Form submission
Webhook URL:        https://your-domain.com/api/webhooks/hubspot/form-submission
Max concurrent:     5
Retry on failure:   Yes
HTTP method:        POST
```

**Step 4: Save & Test**
```
Click "Create"
Click "Test" to send test payload
```

### 2. Find Your Form ID

In HubSpot:
```
Marketing → Lead capture → Forms
Click your form
Note the form ID in URL: hubspot.com/contacts/forms/.../{FORM_ID}
```

Then add to `EXPECTED_FORM_IDS` in [src/routes/webhooks.py](../../src/routes/webhooks.py):

```python
EXPECTED_FORM_IDS = [
    "your-form-id",     # Add your actual form ID here
    "lead-interest-form",
]
```

---

## Local Testing

### 1. Start the API

```bash
make docker-up
# or
make secrets-check && python src/main.py
```

### 2. Test with Example Payload

```bash
# Get example payload
curl http://localhost:8000/api/webhooks/hubspot/form-submission/example-payload

# Test the webhook
curl -X POST http://localhost:8000/api/webhooks/hubspot/form-submission/test \
  -H "Content-Type: application/json" \
  -d '{
    "portalId": 12345,
    "formId": "lead-interest-form",
    "formSubmissionId": "submission-abc123",
    "pageTitle": "Sales Demo",
    "pageUri": "https://company.com/demo",
    "timestamp": 1674150000000,
    "submitText": "Request Demo",
    "userMessage": null,
    "fieldValues": [
      {"name": "firstname", "value": "John"},
      {"name": "lastname", "value": "Doe"},
      {"name": "email", "value": "john@company.com"},
      {"name": "company", "value": "Company Inc"}
    ]
  }'

# Response:
# {
#   "status": "ok",
#   "message": "Form validation successful",
#   "email": "john@company.com",
#   "company": "Company Inc",
#   "first_name": "John",
#   "received_fields": 5
# }
```

### 3. Use ngrok for Local Testing

To receive webhooks from HubSpot on your local machine:

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000

# Copy HTTPS URL (e.g., https://1234-56-78-90-12.ngrok.io)
# Use in HubSpot webhook: https://1234-56-78-90-12.ngrok.io/api/webhooks/hubspot/form-submission
```

Monitor requests:
```bash
# View webhook requests in ngrok dashboard
http://localhost:4040
```

---

## Webhook Payload Format

HubSpot sends this JSON to your webhook endpoint:

```json
{
  "portalId": 12345,
  "formId": "lead-interest-form",
  "formSubmissionId": "submission-xxxxxxxxxxxxxxxxxxxxxxxx",
  "pageTitle": "Sales Demo Request",
  "pageUri": "https://company.com/demo",
  "timestamp": 1674150000000,
  "submitText": "Request Demo",
  "userMessage": null,
  "fieldValues": [
    {
      "name": "firstname",
      "value": "John"
    },
    {
      "name": "lastname",
      "value": "Doe"
    },
    {
      "name": "email",
      "value": "john@company.com"
    },
    {
      "name": "company",
      "value": "Company Inc"
    },
    {
      "name": "phone",
      "value": "+1-555-123-4567"
    }
  ]
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `portalId` | int | Your HubSpot account ID |
| `formId` | string | Form identifier (validate against `EXPECTED_FORM_IDS`) |
| `formSubmissionId` | string | Unique ID for this submission |
| `pageTitle` | string | HTML title of page where form was submitted |
| `pageUri` | string | URL of page |
| `timestamp` | int | Unix timestamp (milliseconds) |
| `submitText` | string | Button text that was clicked |
| `userMessage` | string | Optional message from user |
| `fieldValues` | array | Array of `{name, value}` for each form field |

### Standard Fields

HubSpot provides these fields by default:
- `firstname` — First name
- `lastname` — Last name
- `email` — Email address
- `company` — Company name
- `phone` — Phone number
- `lifecyclestage` — Lead status (lead, marketingqualifiedlead, etc.)
- `message` — Text message (if text area in form)

---

## Validation Rules

The webhook validates incoming requests:

### Required Fields
- `portalId` — Your account ID
- `formId` — Must match `EXPECTED_FORM_IDS`
- `formSubmissionId` — Unique ID
- `fieldValues` — Must include at least email

### Email Required
```python
email = payload.get_email()
if not email:
    raise HTTPException(400, "Email is required")
```

### Form ID Validation
```python
if payload.formId not in EXPECTED_FORM_IDS:
    raise HTTPException(400, f"Form {payload.formId} not configured")
```

---

## Endpoint Reference

### Test Webhook

**Method:** `POST`  
**URL:** `/api/webhooks/hubspot/form-submission/test`  
**Purpose:** Validate webhook structure (no side effects)

**Example:**
```bash
curl -X POST http://localhost:8000/api/webhooks/hubspot/form-submission/test \
  -H "Content-Type: application/json" \
  -d @payload.json
```

**Response (Success):**
```json
{
  "status": "ok",
  "message": "Form validation successful",
  "email": "john@company.com",
  "company": "Company Inc",
  "first_name": "John",
  "received_fields": 5
}
```

**Response (Validation Error):**
```json
{
  "detail": "Form submission must include email address"
}
```

### Receive Webhook (Live)

**Method:** `POST`  
**URL:** `/api/webhooks/hubspot/form-submission`  
**Purpose:** Process actual form submissions (queues workflow)

**Status Codes:**
- `202 Accepted` — Form queued for processing
- `400 Bad Request` — Invalid form ID or missing email
- `500 Internal Server Error` — Processing error

**Response (Success):**
```json
{
  "status": "accepted",
  "submission_id": "submission-abc123",
  "email": "john@company.com",
  "message": "Form submission queued for processing"
}
```

### Get Example Payload

**Method:** `GET`  
**URL:** `/api/webhooks/hubspot/form-submission/example-payload`  
**Purpose:** Retrieve example payload for testing

**Response:**
```json
{
  "portalId": 12345,
  "formId": "lead-interest-form",
  "formSubmissionId": "submission-...",
  ...
}
```

---

## Integration with Workflows

When a form is submitted:

```
HubSpot Form Submission
  ↓
/api/webhooks/hubspot/form-submission
  ↓
Email extracted: john@company.com
  ↓
Gmail search for existing threads
  ↓
If found: Extract thread context
  ↓
Calendar: Check availability
  ↓
Generate draft reply
  ↓
Create HubSpot note + task
  ↓
Status: DRAFT_ONLY (no auto-send)
```

---

## Troubleshooting

### "Form {formId} not configured for webhooks"

**Cause:** Form ID not in `EXPECTED_FORM_IDS`

**Fix:**
1. Get actual form ID from HubSpot
2. Update [src/routes/webhooks.py](../../src/routes/webhooks.py):
   ```python
   EXPECTED_FORM_IDS = [
       "your-actual-form-id",
   ]
   ```
3. Redeploy

---

### Webhook not being called by HubSpot

**Causes:**
1. Webhook URL incorrect
2. Form ID wrong
3. Firewall blocking requests
4. HubSpot webhook not enabled

**Fix:**
1. Verify webhook URL in HubSpot settings (Settings → Webhooks)
2. Check form ID matches `EXPECTED_FORM_IDS`
3. Use ngrok to test locally: `ngrok http 8000`
4. Check logs: `docker compose logs api`

---

### "Request to webhook URL failed" (HubSpot error)

**Causes:**
- URL unreachable
- API returning 5xx error
- Request timeout (>30s)
- TLS certificate issue

**Fix:**
1. Test endpoint directly:
   ```bash
   curl http://localhost:8000/api/webhooks/hubspot/form-submission/test -d @payload.json
   ```
2. Check logs for errors
3. Verify URL is publicly accessible
4. Check SSL certificate if using HTTPS

---

### "Form submission missing email"

**Cause:** Email field not included in form

**Fix:**
1. Edit form in HubSpot
2. Add email field (required)
3. Re-submit

---

## Production Deployment

### 1. Set Production URL

In HubSpot:
```
Settings → Webhooks
Edit webhook URL: https://your-domain.com/api/webhooks/hubspot/form-submission
```

### 2. Add Form ID Validation

Update webhook validation to check against real form data:

```python
from src.connectors.hubspot import get_hubspot_connector

async def validate_form_id(form_id: str) -> bool:
    """Validate against actual HubSpot forms."""
    hubspot = get_hubspot_connector()
    forms = await hubspot.get_forms()
    return any(f["id"] == form_id for f in forms)
```

### 3. Enable Retry Logic

In HubSpot webhook settings:
```
Retry on failure: Yes
Max retries: 3
Backoff: Exponential
```

### 4. Monitor Webhook Health

```bash
# Check HubSpot webhook dashboard
Settings → Webhooks → [Your Webhook]
Success rate: Should be 95%+
Latest requests: Should show 2xx responses
```

---

## Architecture

```
┌─────────────────────────────────┐
│   HubSpot Form                  │
│   (submitted by user)           │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│   POST /api/webhooks/hubspot/   │
│        form-submission          │
└──────────────┬──────────────────┘
               │
        ┌──────┴──────────┐
        │                 │
        ▼                 ▼
   Validate          Extract
   Form ID           Contact
        │                 │
        └──────┬──────────┘
               │
               ▼
        Queue Prospecting
        Workflow
               │
        ┌──────┴──────┬──────────┬───────────┐
        ▼             ▼          ▼           ▼
      Gmail      HubSpot     Calendar     Draft
     Search     Resolve    Check Avail   Reply
        │             │          │           │
        └──────┬──────┴──────────┴───────────┘
               │
               ▼
        Create Draft
        + Note + Task
               │
        STATUS: DRAFT_ONLY
```

---

## Next Steps

1. **Configure webhook** in HubSpot (Settings → Webhooks)
2. **Add form ID** to `EXPECTED_FORM_IDS`
3. **Test locally** with ngrok or test endpoint
4. **Monitor logs** for submission events
5. **Deploy** to production
6. **Verify** first submission is processed
7. **Adjust** form validation rules as needed

---

## Reference

- [HubSpot Webhooks Documentation](https://developers.hubspot.com/docs/api/webhooks)
- [Form Submission Webhooks](https://developers.hubspot.com/docs/api/webhooks/form-submissions)
- [HubSpot API Reference](https://developers.hubspot.com/docs/api/overview)
- [ngrok Documentation](https://ngrok.com/docs)
