# Runbook: Go-Live Tonight (DRAFT_ONLY Mode)

**Mode**: DRAFT_ONLY (hard-enforced, no auto-send possible)

---

## Preconditions

### Required Environment Variables

The following must be set. Do not log or print values.

| Variable | Purpose | Validation |
|----------|---------|------------|
| `GOOGLE_CREDENTIALS_FILE` | Path to service account JSON | File exists, valid JSON |
| `HUBSPOT_API_KEY` | HubSpot private app token | Starts with `pat-` |
| `OPENAI_API_KEY` | OpenAI API key | Starts with `sk-` |
| `DATABASE_URL` | PostgreSQL connection string | Starts with `postgresql://` |
| `EXPECTED_HUBSPOT_FORM_ID` | Form ID to validate | Exact match required |

### Required Configuration Values

| Config | Value | Purpose |
|--------|-------|---------|
| HubSpot Form ID | `db8b22de-c3d4-4fc6-9a16-011fe322e82c` | Form allowlist validation |
| Pesti Sales Drive Folder | `0ACIUuJIAAt4IUk9PVA` | Asset hunting root |
| Charlie Pesti Drive Folder | `0AB_H1WFgMn8uUk9PVA` | Asset hunting root |

### Drive Folder Allowlist Rules

**Pesti Sales folder** (`0ACIUuJIAAt4IUk9PVA`):
- Include prefixes: `CHAINge Proposals`, `CP Client Reports`, `CP Proposals`, `Manifest 2026`
- Exclude: `CP Closed`

**Charlie Pesti folder** (`0AB_H1WFgMn8uUk9PVA`):
- Include: All descendants

### Meeting Slot Requirements

- Propose exactly 2-3 options
- 30-minute blocks
- Near-term availability
- Tone: urgent but not needy

---

## Commands

### Step 1: Verify Secrets

```bash
source .venv/bin/activate
set -a && source .env && set +a
make check-secrets
```

**Success**: All 5 critical/required secrets show `✓ PRESENT`

### Step 2: Verify Database Connection

```bash
source .venv/bin/activate
set -a && source .env && set +a
python -c "from sqlalchemy import create_engine; import os; e=create_engine(os.environ['DATABASE_URL']); c=e.connect(); print('✓ Database connected'); c.close()"
```

**Success**: Prints `✓ Database connected`

### Step 3: Verify Google APIs

```bash
source .venv/bin/activate
set -a && source .env && set +a
python -c "
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os, json

creds = service_account.Credentials.from_service_account_file(
    os.path.expanduser(os.environ['GOOGLE_CREDENTIALS_FILE']),
    scopes=['https://www.googleapis.com/auth/gmail.readonly']
)
gmail = build('gmail', 'v1', credentials=creds)
print('✓ Gmail API accessible')
"
```

**Success**: Prints `✓ Gmail API accessible`

### Step 4: Verify HubSpot API

```bash
source .venv/bin/activate
set -a && source .env && set +a
python -c "
import httpx, os
r = httpx.get(
    'https://api.hubapi.com/crm/v3/objects/contacts?limit=1',
    headers={'Authorization': f'Bearer {os.environ[\"HUBSPOT_API_KEY\"]}'}
)
assert r.status_code == 200, f'HubSpot API failed: {r.status_code}'
print('✓ HubSpot API accessible')
"
```

**Success**: Prints `✓ HubSpot API accessible`

### Step 5: Run Mock Smoke Test

```bash
source .venv/bin/activate
set -a && source .env && set +a
make smoke-formlead
```

**Success**: Output shows `✅ Status: SUCCESS` and `DRAFT_ONLY mode enforced`

### Step 6: Run Live Smoke Test (DRAFT_ONLY)

```bash
source .venv/bin/activate
set -a && source .env && set +a
WORKFLOW_MODE=DRAFT_ONLY python -m src.commands.smoke_formlead_formlead --live
```

**Success**:
- All 12 workflow steps show `✓ SUCCESS`
- Draft Email ID present (not sent)
- HubSpot Task ID present
- Mode confirms `DRAFT_ONLY`

### Step 7: Verify DRAFT_ONLY Enforcement

```bash
source .venv/bin/activate
set -a && source .env && set +a
python -c "
from src.config.feature_flags import FeatureFlagManager, WorkflowMode
mode = FeatureFlagManager.get_workflow_mode()
assert mode == WorkflowMode.DRAFT_ONLY, f'UNSAFE: Mode is {mode}'
print('✓ DRAFT_ONLY mode hard-enforced')
"
```

**Success**: Prints `✓ DRAFT_ONLY mode hard-enforced`

---

## Validation Checklist

After running the live smoke test, verify each item:

### Gmail Draft Validation

- [ ] Draft exists in Gmail drafts folder
- [ ] Draft is NOT in sent folder
- [ ] Subject line is personalized (contains prospect name/company)
- [ ] Body contains meeting slot options (2-3 options, 30-min blocks)
- [ ] Body contains Drive asset link (if assets found)
- [ ] Draft is threaded to existing conversation (if prior thread exists)
- [ ] No em-dashes in body text

### HubSpot Validation

- [ ] Note created on contact record
- [ ] Note contains workflow summary
- [ ] Follow-up task created
- [ ] Task due date is set (2 business days)
- [ ] Task assigned to correct owner

### Calendar Validation

- [ ] Meeting slots are from freebusy lookup
- [ ] Slots are 30-minute blocks
- [ ] Slots are near-term (not past)
- [ ] 2-3 options provided

### Drive Asset Validation

- [ ] Asset link is from allowlisted folder
- [ ] Asset matches prospect company/industry
- [ ] Link is shareable (permissions correct)
- [ ] Excluded folders not searched (`CP Closed`)

### Audit Trail Validation

- [ ] Workflow ID generated
- [ ] All 12 steps logged
- [ ] No errors in log output
- [ ] Final status is `success`

---

## Troubleshooting

### 1. OAuth Scopes Error

**Symptom**: `Insufficient Permission` or `403 Forbidden` from Google APIs

**Fix**:
```bash
# Verify service account has required scopes enabled
# Required scopes:
# - https://www.googleapis.com/auth/gmail.readonly
# - https://www.googleapis.com/auth/gmail.modify
# - https://www.googleapis.com/auth/gmail.compose
# - https://www.googleapis.com/auth/drive.readonly
# - https://www.googleapis.com/auth/calendar.readonly

# Check scopes in credentials file:
cat $GOOGLE_CREDENTIALS_FILE | jq '.client_email'
# Then verify in Google Cloud Console that domain-wide delegation is enabled
```

### 2. Drive Permissions Error

**Symptom**: `File not found` or `404` when searching Drive folders

**Fix**:
```bash
# Verify service account has access to Drive folders
# Share folders with the service account email (from credentials JSON)

# Test folder access:
python -c "
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

creds = service_account.Credentials.from_service_account_file(
    os.path.expanduser(os.environ['GOOGLE_CREDENTIALS_FILE']),
    scopes=['https://www.googleapis.com/auth/drive.readonly']
)
drive = build('drive', 'v3', credentials=creds)
# Test Pesti Sales folder
result = drive.files().list(q=\"'0ACIUuJIAAt4IUk9PVA' in parents\", pageSize=5).execute()
print(f'Found {len(result.get(\"files\", []))} files')
"
```

### 3. HubSpot Auth Error

**Symptom**: `401 Unauthorized` from HubSpot API

**Fix**:
```bash
# Verify API key format (should start with pat-na1-)
# Check scopes in HubSpot private app settings
# Required scopes: crm.objects.contacts.read, crm.objects.contacts.write

# Test auth:
curl -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  "https://api.hubapi.com/crm/v3/objects/contacts?limit=1"
```

### 4. Form ID Mismatch

**Symptom**: `Form ID not in allowlist` warning

**Fix**:
```bash
# Verify EXPECTED_HUBSPOT_FORM_ID matches exactly:
echo $EXPECTED_HUBSPOT_FORM_ID
# Should be: db8b22de-c3d4-4fc6-9a16-011fe322e82c

# Check orchestrator allowlist in src/formlead_orchestrator.py
grep -n "allowed_form_ids" src/formlead_orchestrator.py
```

### 5. Calendar Timezone Error

**Symptom**: Meeting slots in wrong timezone or past times

**Fix**:
```bash
# Verify TZ environment variable
echo $TZ

# Set to correct timezone:
export TZ=America/New_York

# Test calendar freebusy:
python -c "
from datetime import datetime, timedelta
import pytz
tz = pytz.timezone('America/New_York')
now = datetime.now(tz)
print(f'Current time: {now}')
"
```

### 6. Database Connection Error

**Symptom**: `Connection refused` or `could not connect to server`

**Fix**:
```bash
# Test connection string directly:
psql "$DATABASE_URL" -c "SELECT 1"

# Check if database is running:
# For Supabase: Check dashboard status
# For local: docker compose up postgres -d
```

### 7. OpenAI API Error

**Symptom**: `RateLimitError` or `AuthenticationError`

**Fix**:
```bash
# Verify API key:
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | head -c 100

# Check rate limits in OpenAI dashboard
```

### 8. Gmail Draft Not Created

**Symptom**: Workflow succeeds but no draft visible

**Fix**:
```bash
# Verify Gmail API can create drafts:
# Check service account has gmail.compose scope
# Verify domain-wide delegation includes Gmail

# Check drafts folder:
python -c "
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

creds = service_account.Credentials.from_service_account_file(
    os.path.expanduser(os.environ['GOOGLE_CREDENTIALS_FILE']),
    scopes=['https://www.googleapis.com/auth/gmail.readonly']
)
gmail = build('gmail', 'v1', credentials=creds)
drafts = gmail.users().drafts().list(userId='me', maxResults=5).execute()
print(f'Found {len(drafts.get(\"drafts\", []))} drafts')
"
```

### 9. HubSpot Task Not Created

**Symptom**: Draft created but no HubSpot task

**Fix**:
```bash
# Verify HubSpot API scopes include:
# - crm.objects.contacts.write
# - crm.objects.deals.write (if using deals)

# Check API response:
python -c "
import httpx, os
r = httpx.get(
    'https://api.hubapi.com/crm/v3/objects/tasks?limit=1',
    headers={'Authorization': f'Bearer {os.environ[\"HUBSPOT_API_KEY\"]}'}
)
print(f'Status: {r.status_code}')
print(r.text[:200])
"
```

### 10. Workflow Hangs or Timeouts

**Symptom**: Command hangs, no output for >60 seconds

**Fix**:
```bash
# Check for network issues:
curl -I https://api.hubapi.com
curl -I https://www.googleapis.com

# Run with verbose logging:
LOG_LEVEL=DEBUG python -m src.commands.smoke_formlead_formlead --live

# Check for async issues:
python -c "import asyncio; print(asyncio.get_event_loop())"
```

---

## Quick Reference Commands

```bash
# Full go-live validation sequence:
source .venv/bin/activate && set -a && source .env && set +a

# 1. Check secrets
make check-secrets

# 2. Mock test
make smoke-formlead

# 3. Live test (DRAFT_ONLY)
WORKFLOW_MODE=DRAFT_ONLY python -m src.commands.smoke_formlead_formlead --live

# 4. Verify DRAFT_ONLY enforcement
python -c "from src.config.feature_flags import FeatureFlagManager, WorkflowMode; assert FeatureFlagManager.get_workflow_mode() == WorkflowMode.DRAFT_ONLY"
```

---

## Success Criteria

Go-live is successful when ALL of the following are true:

1. `make check-secrets` exits 0
2. `make smoke-formlead` exits 0 with `SUCCESS` status
3. Live smoke test shows all 12 steps `SUCCESS`
4. Gmail draft exists (verified manually or via API)
5. HubSpot note exists on contact
6. HubSpot task created with correct due date
7. Drive asset link is from allowlisted folder
8. Calendar slots are valid 30-min near-term blocks
9. Mode is confirmed `DRAFT_ONLY` (no send capability)
10. No errors in workflow log output

---

## Rollback

If go-live validation fails:

1. Do not proceed with production traffic
2. Check troubleshooting section for specific error
3. Fix issue and re-run validation sequence
4. All 10 success criteria must pass before proceeding

