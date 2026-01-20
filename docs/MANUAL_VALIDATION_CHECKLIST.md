# Manual Validation Checklist for DRAFT_ONLY Mode

## Overview

This checklist validates that the entire end-to-end sales agent workflow works correctly in **DRAFT_ONLY mode**. Follow these steps to verify the system is ready for testing with real data.

**Important:** No emails are sent during this validation. All drafts are created but remain unsent.

---

## Pre-Flight Checklist

- [ ] All environment variables set: `make secrets-check`
- [ ] Docker services running: `make docker-up`
- [ ] API health check: `curl http://localhost:8000/health`
- [ ] Python tests pass: `make test-unit`

---

## Phase 1: Google OAuth Setup

### Step 1.1: Generate OAuth Credentials
- [ ] Create OAuth 2.0 app in [Google Cloud Console](https://console.cloud.google.com/)
- [ ] Enable Gmail, Drive, Calendar APIs
- [ ] Create Desktop app credentials
- [ ] Download as `client_secret.json` (project root)
- [ ] Verify file exists: `ls client_secret.json`

### Step 1.2: Run OAuth Authorization
```bash
make auth-google
```

- [ ] Browser opens to Google login
- [ ] You log in with your test account
- [ ] Permission screen appears for Gmail, Drive, Calendar
- [ ] You click "Allow"
- [ ] CLI shows: "✓ All authorizations successful!"
- [ ] Token cached: `ls .tokens/google_tokens.json`
- [ ] Token file not in git: `git status | grep .tokens` (should not appear)

### Step 1.3: Verify Token
```bash
python -m src.commands.auth_google --info
```

- [ ] Status shows "VALID"
- [ ] Expires in > 1 hour
- [ ] Scopes include: Gmail, Drive, Calendar

---

## Phase 2: HubSpot Webhook Setup

### Step 2.1: Configure Webhook in HubSpot

**In HubSpot:**
1. [ ] Go to Settings → Integrations → Webhooks
2. [ ] Click "+ Create webhook"
3. [ ] Set webhook URL to test endpoint:
   - Local: `http://localhost:8000/api/webhooks/hubspot/form-submission/test`
   - Or use ngrok: `https://your-ngrok-url/api/webhooks/hubspot/form-submission/test`
4. [ ] Select form (or create test form)
5. [ ] Click "Test" button
6. [ ] Verify HubSpot shows "success"

### Step 2.2: Test Webhook Locally
```bash
# Get example payload
curl http://localhost:8000/api/webhooks/hubspot/form-submission/example-payload

# Test webhook validation
curl -X POST http://localhost:8000/api/webhooks/hubspot/form-submission/test \
  -H "Content-Type: application/json" \
  -d '{
    "portalId": 12345,
    "formId": "lead-interest-form",
    "formSubmissionId": "submission-test-001",
    "pageTitle": "Demo",
    "pageUri": "https://example.com",
    "timestamp": '$(date +%s)'000,
    "fieldValues": [
      {"name": "firstname", "value": "John"},
      {"name": "lastname", "value": "Doe"},
      {"name": "email", "value": "test@example.com"},
      {"name": "company", "value": "Test Corp"}
    ]
  }'
```

- [ ] Response status: 200 OK
- [ ] Response includes: `"status": "ok"`
- [ ] Extracted email: `test@example.com`
- [ ] Extracted company: `Test Corp`

### Step 2.3: Configure Form ID Validation

**In `src/routes/webhooks.py`:**
```python
EXPECTED_FORM_IDS = [
    "your-actual-form-id",  # Add your HubSpot form ID here
    "lead-interest-form",
]
```

- [ ] Form ID updated with your actual HubSpot form ID
- [ ] File saved and committed

---

## Phase 3: E2E Smoke Test

### Step 3.1: Run Mocked Smoke Test
```bash
make smoke-formlead
```

- [ ] All 7 steps complete successfully:
  1. [ ] Load form submission payload
  2. [ ] Resolve HubSpot contact/company
  3. [ ] Search Gmail for existing threads
  4. [ ] Extract thread context
  5. [ ] Check Calendar and propose slots
  6. [ ] Create Gmail draft reply
  7. [ ] Create HubSpot note & task

- [ ] Output shows:
  - [ ] Draft ID: `draft-xxxxxxxx`
  - [ ] Task ID: `task-xxxxxxxx`
  - [ ] Status: `SUCCESS`
  - [ ] Mode: `DRAFT_ONLY`

### Step 3.2: Verify Smoke Test Output
```bash
make smoke-formlead --json > smoke-test-results.json
```

- [ ] File created: `smoke-test-results.json`
- [ ] All steps have `"status": "success"`
- [ ] `"final_status": "success"`
- [ ] No errors in output

### Step 3.3: Test with Custom Payload
```bash
# Create custom payload
cat > test-payload.json << 'EOF'
{
  "portalId": 12345,
  "formId": "lead-interest-form",
  "formSubmissionId": "submission-custom-001",
  "pageTitle": "Custom Test",
  "pageUri": "https://example.com",
  "timestamp": $(date +%s)000,
  "fieldValues": [
    {"name": "firstname", "value": "Alice"},
    {"name": "lastname", "value": "Smith"},
    {"name": "email", "value": "alice@company.com"},
    {"name": "company", "value": "Custom Corp"}
  ]
}
EOF

# Run with custom payload
python -m src.commands.smoke_formlead --mock --input=test-payload.json
```

- [ ] Custom payload processed successfully
- [ ] Email correctly extracted: `alice@company.com`
- [ ] Company correctly extracted: `Custom Corp`

---

## Phase 4: API Integration Tests

### Step 4.1: Run Integration Tests
```bash
make test-integration
```

- [ ] All webhook tests pass
- [ ] Test results:
  ```
  test_webhooks.py::TestHubSpotWebhook::test_get_example_payload PASSED
  test_webhooks.py::TestHubSpotWebhook::test_webhook_test_endpoint_valid_payload PASSED
  test_webhooks.py::TestHubSpotWebhook::test_webhook_test_endpoint_missing_email PASSED
  test_webhooks.py::TestSmokeTestIntegration::test_smoke_test_mock_mode PASSED
  test_webhooks.py::TestWebhookEndpointIntegration::test_health_check_before_webhook PASSED
  ```

### Step 4.2: Run All Tests
```bash
make test
```

- [ ] All tests pass (100+ test cases)
- [ ] No failures or errors
- [ ] Coverage report available

---

## Phase 5: Live Workflow Test (Optional)

**Note:** This phase tests with real APIs but still in DRAFT_ONLY mode.

### Step 5.1: Send Real Form Submission (If HubSpot Webhook Configured)

**In HubSpot:**
1. [ ] Navigate to your form
2. [ ] Click "Preview & test" or use live form
3. [ ] Fill out form with test data:
   - First Name: `[Your Name]`
   - Last Name: `[Test]`
   - Email: `[Your real email]`
   - Company: `[Your company]`
4. [ ] Click Submit

**Monitor API:**
```bash
# Watch logs while form is submitted
docker compose logs -f api | grep -i "form submission"
```

- [ ] Logs show: `Received HubSpot form submission`
- [ ] Form submission accepted (202 status)
- [ ] Email extracted correctly
- [ ] Contact resolved in HubSpot

### Step 5.2: Verify Draft Created (Optional)

If workflow is fully implemented with real APIs:

```bash
# Check HubSpot for new task
curl -H "Authorization: Bearer $HUBSPOT_API_KEY" \
  https://api.hubapi.com/crm/v3/objects/tasks
```

- [ ] New task created with correct contact
- [ ] Task status: Draft created (not sent)
- [ ] Email draft visible in Gmail (Drafts folder)

### Step 5.3: Verify DRAFT_ONLY Mode Enforced

- [ ] Email NOT sent (should be in Drafts, not Sent)
- [ ] HubSpot task NOT marked as complete
- [ ] Operator approval still required
- [ ] System ready for: `OPERATOR_MODE_ENABLED=true`

---

## Phase 6: Security Verification

### Step 6.1: Validate Secrets Management
```bash
# Verify secrets not in git
git status | grep -i "secret\|token\|key"
git log --all --oneline -- .env .tokens/ | head
```

- [ ] `.tokens/` not in repository
- [ ] No `.env` in git history
- [ ] `.env.example` is template only (no real values)

### Step 6.2: Check Token Permissions
```bash
ls -la .tokens/
```

- [ ] Token file permissions: `-rw-------` (0600)
- [ ] Only owner can read: `stat -c "%A" .tokens/google_tokens.json`

### Step 6.3: Verify Webhook Validation
```bash
# Test with invalid form ID
curl -X POST http://localhost:8000/api/webhooks/hubspot/form-submission/test \
  -H "Content-Type: application/json" \
  -d '{
    "portalId": 12345,
    "formId": "invalid-form-id",
    "formSubmissionId": "test",
    "timestamp": 123,
    "fieldValues": [{"name": "email", "value": "test@example.com"}]
  }'
```

- [ ] Response includes validation error (or warning)
- [ ] Request logged for audit
- [ ] No crashes or unexpected errors

---

## Phase 7: Documentation Verification

- [ ] `docs/SECRETS_CHECK.md` exists and is current
- [ ] `docs/GOOGLE_OAUTH.md` exists and is current
- [ ] `docs/HUBSPOT_WEBHOOK.md` exists and is current
- [ ] All docs link to relevant source files
- [ ] Examples in docs match actual implementation

---

## Phase 8: Makefile Commands Verification

```bash
# Test all Makefile commands
make help                  # Shows help text
make secrets-check        # Validates env vars
make auth-google          # OAuth setup (skip if already done)
make test                 # Runs all tests
make smoke-formlead       # Smoke test
make docker-up            # Starts services
make docker-down          # Stops services
```

- [ ] All commands work without errors
- [ ] Help text is clear and complete
- [ ] Commands are idempotent (can run multiple times)

---

## Phase 9: Readiness for Production

### Step 9.1: Production Configuration Checklist
- [ ] API running with `API_ENV=production` (if applicable)
- [ ] Logging level set to `INFO` (not `DEBUG`)
- [ ] Database connections pooled (`DATABASE_POOL_SIZE=20`)
- [ ] Redis configured for Celery tasks
- [ ] All required env vars present in production environment

### Step 9.2: Deployment Checklist
- [ ] All code committed to git
- [ ] Tests passing in CI/CD pipeline
- [ ] Secrets stored in Secret Manager (not in env vars)
- [ ] Docker image builds without errors: `make docker-build`
- [ ] Deployment procedure documented and tested

### Step 9.3: Monitoring & Alerting (Optional)
- [ ] Logging aggregation configured (e.g., Cloud Logging)
- [ ] Error alerts configured
- [ ] Health check endpoint monitored
- [ ] Webhook failure rate tracked

---

## Troubleshooting Guide

### "OAuth token not found" Error

**Fix:**
```bash
make auth-google --force
```

Then re-run smoke test.

### "HubSpot form validation failed" Error

**Fix:**
1. Verify form ID in `EXPECTED_FORM_IDS`
2. Confirm form exists in HubSpot
3. Check HubSpot account ID (portalId) matches

### "Gmail search returned no results" (Expected in Mock Mode)

**Fix:**
Mock mode returns 1 thread by default. In live mode, adjust Gmail search query.

### "Calendar availability returned empty slots" (Expected in Mock Mode)

**Fix:**
Mock mode returns 3 slots. In live mode, verify Calendar has events configured.

### Tests Failing

**Fix:**
```bash
# Check environment
make secrets-check

# Ensure services running
make docker-up

# Run tests with verbose output
make test
```

---

## Sign-Off

When all phases are complete:

```bash
echo "✓ DRAFT_ONLY mode validation complete" > VALIDATION_COMPLETE.txt
git add VALIDATION_COMPLETE.txt
git commit -m "feat: Complete DRAFT_ONLY mode end-to-end validation"
git push
```

- [ ] All phases completed
- [ ] All tests passing
- [ ] No outstanding issues
- [ ] Ready to proceed to next phase

---

## Next Steps

### If Validation Passes ✓
1. Prepare for `SEND_ALLOWED` mode:
   - Implement real email send logic
   - Add rate limiting enforcement
   - Configure production quotas
   - Set up approval workflow

2. Additional testing:
   - Load testing (1000+ leads/day)
   - Voice profile learning validation
   - PII redaction verification
   - Compliance audit

3. Deployment:
   - Set up monitoring and alerting
   - Configure backup/disaster recovery
   - Run security audit
   - Deploy to production

### If Validation Fails ✗
1. Review error logs: `docker compose logs api`
2. Check secrets: `make secrets-check`
3. Re-run failing phase
4. Open GitHub issue with detailed error message

---

## Approval & Handoff

**Validated By:** _______________  
**Date:** _______________  
**Sign-Off:** _______________  

System is ready for next phase.
