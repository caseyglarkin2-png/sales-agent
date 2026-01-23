# 🚀 TOMORROW'S CAMPAIGN LAUNCH PLAN

**Date:** January 24, 2026  
**Goal:** Launch automated email campaigns from HubSpot contacts  
**Status:** ✅ AUTO-SEND READY | 📋 CONTACTS PENDING | 🎯 CAMPAIGNS QUEUED

---

## ✅ WHAT'S READY NOW (Shipped Tonight)

### Auto-Send on Approval (Sprint 15.1 - COMPLETE)
```python
# How it works:
1. Approve draft in operator dashboard
2. System checks: MODE_DRAFT_ONLY == False?
3. System checks: Rate limit OK?
4. Gmail API sends email
5. Draft marked as SENT with timestamp

# Safety features:
- ✅ Feature flag integration (MODE_DRAFT_ONLY check)
- ✅ Rate limiter integration (prevents quota exhaustion)
- ✅ Transaction-safe (approval succeeds even if send fails)
- ✅ Audit logging (every send tracked)
```

### Morning Emails (5 Prospects - QUEUED)
- ✅ 5 personalized emails generated
- ✅ Using your voice training
- ✅ Ready for approval
- ✅ Will auto-send when approved

---

## 🎯 TOMORROW MORNING WORKFLOW

### Step 1: Test Auto-Send (5 minutes)
```bash
# 1. Run queue script to load drafts
python queue_morning_emails.py

# 2. Visit operator dashboard
open https://web-production-a6ccf.up.railway.app/operator

# 3. Approve ONE draft as test
Click "Approve" on Sarah Chen email

# 4. Verify it sends
Check Gmail sent folder for email to sarah.chen@techcorp.com

# Expected: Email sent automatically!
```

### Step 2: Enable Send Mode (if in DRAFT_ONLY)
```bash
# Set environment variable in Railway dashboard:
MODE_DRAFT_ONLY=false
ALLOW_AUTO_SEND=true

# Or via CLI:
railway variables set MODE_DRAFT_ONLY=false
railway variables set ALLOW_AUTO_SEND=true
```

### Step 3: Approve Remaining 4 Emails
```
Visit /operator dashboard
Approve remaining drafts:
- Mike Rodriguez @ GrowthCo
- Jennifer Park @ Venture Sales
- David Nguyen @ Market Leaders
- Amanda Stevens @ InnovateSoft

All will auto-send!
```

---

## 📊 HUBSPOT CONTACT SYNC (Execute Tomorrow)

### Goal: Pull ALL Pesti contacts for campaigns

### Implementation Plan:
```python
# File: src/hubspot_sync.py (created, needs implementation)

class HubSpotContactSync:
    """Sync all contacts from Pesti HubSpot"""
    
    async def sync_all_contacts(self):
        """
        Pull ALL contacts with pagination
        - Uses existing HubSpotConnector (Sprint 12)
        - Handles 100 contacts/page with cursor
        - Stores in PostgreSQL contacts table
        - Returns: Total contacts synced
        """
        
    async def sync_chainge_list(self):
        """
        Pull CHAINge list specifically
        - Filter by HubSpot list membership
        - Tag with segment: "CHAINge"
        - Priority for first campaign
        """
        
    async def sync_gitte_segments(self):
        """
        Apply Gitte's custom segments
        - High Value
        - Engaged
        - Cold/Re-engagement
        - Custom list filters
        """
```

### Quick Implementation (30 minutes):
```bash
# 1. Extend existing HubSpot connector
# 2. Add pagination loop for contacts
# 3. Store in database with segments
# 4. Run sync via API endpoint

# Test:
curl -X POST /api/contacts/sync/hubspot
# Expected: {"synced": 1000+, "chainge": 50, "segments": {...}}
```

---

## 🎬 CAMPAIGN SEQUENCES (Execute Tomorrow)

### Goal: Queue campaigns from HubSpot segments

### Quick Wins (Use Existing Infrastructure):

**Option A: Manual Campaign (Fastest - 10 minutes)**
```bash
# 1. Run HubSpot sync
python -c "
from src.integrations.connectors.hubspot import HubSpotConnector
from src.config import settings
import asyncio

async def main():
    connector = HubSpotConnector(settings.hubspot_api_key)
    contacts = await connector.get_contacts(limit=100)
    
    # Print contacts for manual queue
    for c in contacts['contacts']:
        print(f\"{c['email']},{c.get('firstname')},{c.get('company')}\")
    
asyncio.run(main())
"

# 2. Create drafts from contacts
# Use existing queue_morning_emails.py as template
# Modify PROSPECTS list with HubSpot contacts

# 3. Run queue script
python queue_morning_emails.py

# 4. Approve in operator dashboard
# All emails auto-send!
```

**Option B: Automated Sequence (1-2 hours - Best long-term)**
```bash
# Implement sequence engine:
# 1. Contact enrolled in sequence
# 2. Day 0: Welcome email (queued immediately)
# 3. Day 3: Follow-up email (scheduled via Celery)
# 4. Day 7: Re-engagement email (scheduled via Celery)

# Uses existing:
- src/campaigns/campaign_manager.py (already exists!)
- src/tasks.py (Celery tasks already configured)
- src/operator_mode.py (draft queue system)
```

---

## 📋 EXECUTION CHECKLIST

### Morning (30 minutes):
- [ ] Test auto-send with 1 draft
- [ ] Approve remaining 4 morning emails
- [ ] Verify all 5 sent successfully
- [ ] Check Gmail sent folder

### Mid-Morning (1 hour):
- [ ] Run HubSpot contact sync
- [ ] Verify CHAINge list pulled correctly
- [ ] Check contact count (expect 100+)
- [ ] Verify segments applied

### Afternoon (2 hours):
- [ ] Generate drafts for CHAINge list (50 contacts)
- [ ] Queue for approval
- [ ] Review drafts
- [ ] Approve batch (10-20 at a time)
- [ ] Monitor sends

### End of Day:
- [ ] Review campaign stats
- [ ] Check response rates
- [ ] Plan tomorrow's campaigns
- [ ] Document what worked

---

## 🛡️ SAFETY FEATURES

### Rate Limiting:
```
Gmail API Limits:
- 100 emails per burst
- 60 emails per minute
- 2000 emails per day (GSuite)

Our rate limiter handles this automatically!
```

### Approval Required:
```
Nothing sends without your explicit approval.
Each draft reviewed before sending.
Bulk approve available for campaigns.
```

### MODE_DRAFT_ONLY Toggle:
```
Production safety switch:
- MODE_DRAFT_ONLY=true → No emails send (safe mode)
- MODE_DRAFT_ONLY=false → Emails send after approval

Switch back anytime to pause all sends.
```

---

## 📊 EXPECTED RESULTS

### Morning Test (5 emails):
- ✅ 5 sent within 10 minutes
- ✅ All from casey.l@pesti.io
- ✅ All personalized with company research
- ✅ All tracked in operator dashboard

### CHAINge Campaign (50 emails):
- 📧 50 drafts generated
- 👀 Review and approve (30 minutes)
- 🚀 All auto-send after approval
- 📊 Track in campaign dashboard

### Full Database (1000+ contacts):
- 🔄 Sync from HubSpot (5 minutes)
- 🎯 Segment by priority (10 minutes)
- 📝 Generate drafts in batches (20 minutes)
- ✅ Approve high-priority segments first
- 📈 Scale over next week

---

## 🚀 QUICK START COMMANDS

```bash
# Morning routine:
cd /workspaces/sales-agent

# 1. Queue morning emails
python queue_morning_emails.py

# 2. Sync HubSpot contacts (implement first)
python -m src.hubspot_sync

# 3. Generate CHAINge campaign
python -m src.campaigns.generate_chainge_campaign

# 4. Launch operator dashboard
open https://web-production-a6ccf.up.railway.app/operator

# 5. Approve and watch them send! 🚀
```

---

## 📞 SUPPORT

If anything fails:
1. Check Railway logs: `railway logs --tail 100`
2. Check feature flags: MODE_DRAFT_ONLY status
3. Check rate limiter: Gmail quota remaining
4. Check operator dashboard: Draft statuses

Everything is transaction-safe - approvals always succeed even if sends fail temporarily.

---

## 🎯 SUCCESS CRITERIA

**Tomorrow is successful if:**
- ✅ 5 morning emails sent
- ✅ HubSpot contacts synced (100+)
- ✅ CHAINge campaign queued (50 drafts)
- ✅ Auto-send working reliably
- ✅ No manual Gmail needed

**Ship Ship Ship!** 🚢

---

*Last Updated: January 23, 2026 - Ready for launch!*
