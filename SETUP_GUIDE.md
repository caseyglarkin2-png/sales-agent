# Setup Guide: Credentials & Secrets (Safe & Secure)

## Quick Summary

You need 5 things to test Phase 3:

| # | What | Source | Status |
|---|------|--------|--------|
| 1 | GOOGLE_CREDENTIALS_FILE | Google Cloud Console | ⏳ Get JSON file |
| 2 | HUBSPOT_API_KEY | HubSpot Settings | ✅ You have this |
| 3 | DATABASE_URL | Docker or Supabase | ⏳ Setup local DB |
| 4 | OPENAI_API_KEY | OpenAI Platform | ✅ You have this |
| 5 | EXPECTED_HUBSPOT_FORM_ID | Your form ID | ⏳ Extract from form |

---

## ⏳ STEP-BY-STEP: GET YOUR GOOGLE JSON FILE

### Prerequisites
- ✅ You have Google Cloud project: `lucid-parser-484902-k9` (from your screenshot)
- ✅ You have OAuth configured (seen in screenshot)
- ✅ You have APIs enabled (Gmail, Drive, Calendar)

### The 5-Minute Process

#### Step 1: Go to Google Cloud Console
```
URL: https://console.cloud.google.com
Project: lucid-parser-484902-k9
```

#### Step 2: Find Service Account Credentials
```
Left sidebar → APIs & Services → Credentials
Look for a service account (usually named "sales-agent-sa" or "default")
```

#### Step 3: Download JSON Key
```
Click on the service account name
Go to "Keys" tab
"Add Key" button → "Create new key"
Select: JSON format
Click "Create"

File automatically downloads as:
  lucid-parser-484902-k9-abc123def456.json
```

#### Step 4: Store Safely (NOT in git)
```bash
# On your LOCAL machine (not in dev container):
mkdir -p ~/.secrets
mv ~/Downloads/lucid-parser-484902-k9-*.json ~/.secrets/google-creds.json
chmod 600 ~/.secrets/google-creds.json

# Verify it's there:
ls -la ~/.secrets/google-creds.json
# Output should show: -rw------- (600 permissions)
```

#### Step 5: Export to Environment
```bash
# Terminal before running tests:
export GOOGLE_CREDENTIALS_FILE=~/.secrets/google-creds.json

# Verify it's loaded:
echo $GOOGLE_CREDENTIALS_FILE
# Should print: /Users/yourname/.secrets/google-creds.json

# Verify file contents:
cat ~/.secrets/google-creds.json | head -5
# Should see JSON starting with: {
```

### ✅ Verification
```bash
# Check if file exists and is readable:
test -f ~/.secrets/google-creds.json && echo "✓ File exists"

# Check permissions (must be 600):
ls -la ~/.secrets/google-creds.json | grep "rw-------" && echo "✓ Permissions correct"

# Check it's valid JSON:
python3 -c "import json; json.load(open('~/.secrets/google-creds.json'))" && echo "✓ Valid JSON"
```

---

## ⏳ STEP-BY-STEP: SETUP DATABASE

### What is it?
The database stores:
- Cached Gmail threads (avoid repeated API calls)
- Contact information (faster lookups)
- Voice profile patterns (learned from your emails)
- Audit logs (compliance/debugging)

### Option A: Local Docker (Recommended for Testing)

**Setup (2 minutes):**
```bash
cd /workspaces/sales-agent

# Start PostgreSQL container:
docker compose up postgres -d

# Wait 10 seconds for it to start
sleep 10

# Verify it's running:
docker compose ps postgres
# Should show: postgres ... Up

# Get the connection string:
export DATABASE_URL="postgresql://sales_agent:password@localhost:5432/sales_agent"

# Test connection:
docker compose exec postgres psql -U sales_agent -d sales_agent -c "SELECT 1"
# Should output: 1
```

**Pros:**
- ✅ Free
- ✅ Instant setup
- ✅ Perfect for testing
- ✅ No external dependencies

**Cons:**
- ✗ Only works while container running
- ✗ Not persistent (dies on reboot)
- ✗ Can't access from outside laptop

### Option B: Google Cloud SQL (Recommended for Production)

**Setup (15 minutes):**
```
1. Go to: https://console.cloud.google.com
2. SQL → Create Instance
3. Engine: PostgreSQL 15
4. Instance name: sales-agent-db
5. Password: (generate strong)
6. Machine type: db-f1-micro (free tier)
7. Connectivity: Private IP (default)
8. Create

Once created:
9. Instance details → Connections
10. Copy "Private IP"
11. Create database:
    - gcloud sql databases create sales_agent \
        --instance=sales-agent-db
12. Get connection string:
    DATABASE_URL=postgresql://postgres:PASSWORD@PRIVATE_IP:5432/sales_agent
13. Export:
    export DATABASE_URL="postgresql://..."
```

**Pros:**
- ✅ Always on
- ✅ Secure (private IP in VPC)
- ✅ Automatic backups
- ✅ Production ready

**Cons:**
- ✗ Costs ~$15-30/month
- ✗ Requires GCP project (you have this)
- ✗ Takes 5-10 minutes to provision

### Option C: Supabase (Easiest for Production)

**Setup (5 minutes):**
```
1. Go to: https://supabase.com
2. Sign up
3. Create new project
4. Project name: sales-agent
5. Database password: (strong)
6. Region: (closest to you)
7. Click "Create new project"

Once created:
8. Settings → Database
9. Connection string shown at bottom:
   postgresql://postgres:PASSWORD@host:5432/postgres
10. Export:
    export DATABASE_URL="postgresql://postgres:PASSWORD@..."
```

**Pros:**
- ✅ Simplest setup
- ✅ Free tier available
- ✅ Built-in backups/monitoring
- ✅ No DevOps needed

**Cons:**
- ✗ ~$10/month for production tier
- ✗ External service

### 🎯 Recommendation
**For testing right now:** Use Option A (Docker)
**For production later:** Use Option B (Cloud SQL) or C (Supabase)

---

## ⏳ STEP-BY-STEP: FIND YOUR HUBSPOT FORM ID

### Option 1: From Your Form Page (Easiest)
```
1. Go to: https://share.hsforms.com/124si3sPUT8aaFgEf4yLoLAe8nok
2. Right-click on form → Inspect (or press F12)
3. Look for: data-form-id="..."
4. That's your form ID!

Example: data-form-id="a1b2c3d4-e5f6-7890"
Then set:
export EXPECTED_HUBSPOT_FORM_ID=a1b2c3d4-e5f6-7890
```

### Option 2: From HubSpot UI
```
1. Go to: HubSpot → Forms
2. Find your form → Click it
3. Settings tab
4. Form ID shown at top
5. Copy and export:
export EXPECTED_HUBSPOT_FORM_ID=<the-id>
```

### 🎯 Your Form Info
```
Portal ID: 23918564 (confirmed from your code)
Form URL: https://share.hsforms.com/124si3sPUT8aaFgEf4yLoLAe8nok
Form ID: (⏳ find using Option 1 or 2 above)
```

---

## 7️⃣ SENTRY (OPTIONAL)

Error tracking - completely optional for testing.

**Skip for now.** If needed later:

```bash
# Go to: https://sentry.io
# Sign up → Create Python project → Copy DSN
# Then:
export SENTRY_DSN=https://abc123@o456.ingest.sentry.io/789
```

---

## 🚀 COMPLETE TESTING SETUP

Once you have everything, run this:

```bash
# 1. Ensure database is running
docker compose up postgres -d

# 2. Set all environment variables
export GOOGLE_CREDENTIALS_FILE=~/.secrets/google-creds.json
export HUBSPOT_API_KEY=pat-na1-... (your key)
export OPENAI_API_KEY=sk-... (your key)
export DATABASE_URL=postgresql://sales_agent:password@localhost:5432/sales_agent
export EXPECTED_HUBSPOT_FORM_ID=... (your form ID)

# 3. Verify everything
make check-secrets

# Expected output:
# ✓ GOOGLE_CREDENTIALS_FILE: PRESENT
# ✓ HUBSPOT_API_KEY: PRESENT
# ✓ DATABASE_URL: PRESENT
# ✓ OPENAI_API_KEY: PRESENT
# ✓ EXPECTED_HUBSPOT_FORM_ID: PRESENT

# 4. Run smoke test
make smoke-formlead

# Expected output:
# ✅ Status: SUCCESS
# (... workflow steps ...)
```

---

## 🔐 Security Checklist

- [ ] Google JSON stored in `~/.secrets/` (NOT in git repo)
- [ ] Google JSON permissions set to 600: `chmod 600 ~/.secrets/google-creds.json`
- [ ] .gitignore has `.env` (prevents accidental commits)
- [ ] Never pasted keys in chat/email
- [ ] Using export/env vars (not hardcoded)
- [ ] Database not publicly accessible (if using Cloud SQL: Private IP only)

---

## ❓ Troubleshooting

### "Google credentials file not found"
```bash
# Check file exists:
ls -la ~/.secrets/google-creds.json

# Check env var is set:
echo $GOOGLE_CREDENTIALS_FILE

# If not set, run:
export GOOGLE_CREDENTIALS_FILE=~/.secrets/google-creds.json
```

### "Database connection refused"
```bash
# Check container is running:
docker compose ps postgres

# If not running:
docker compose up postgres -d

# Check logs:
docker compose logs postgres

# Check connection string is correct:
echo $DATABASE_URL
```

### "Invalid JSON credentials"
```bash
# Verify JSON syntax:
python3 -c "import json; json.load(open(os.environ['GOOGLE_CREDENTIALS_FILE']))"

# If error, re-download JSON from Google Cloud Console
```

### "Form ID not found"
```bash
# Check form page:
curl -s https://share.hsforms.com/124si3sPUT8aaFgEf4yLoLAe8nok | grep "data-form-id"

# Or manually inspect page and look for data-form-id attribute
```

---

## 📞 Need Help?

When setting up, record:
1. ✅ Google credentials file location
2. ✅ Database connection string
3. ✅ Form ID
4. ✅ Output of `make check-secrets`

Once all are green in `make check-secrets`, you're ready to:
```bash
make smoke-formlead
```

---

**Next: Tell me when you're ready, and we'll run the full end-to-end test! 🚀**
