# Campaign Launch System - Sprint Plan

**Goal:** Launch automated email campaigns from HubSpot contacts with approval workflow

**Philosophy:** Ship Ship Ship - Atomic tasks, demoable sprints, build on previous work

---

## Sprint 15: Auto-Send on Approval (Foundation)
**Goal:** Enable automatic email sending when operator approves drafts

### Tasks:
- **15.1** Add auto-send logic to approval endpoint
  - Input: Draft approval request
  - Output: Email sent via Gmail API
  - Test: Approve draft → verify email sent
  - Validation: Check Gmail sent folder

- **15.2** Update operator mode to trigger sends
  - Input: Approved draft with send flag
  - Output: Gmail message ID returned
  - Test: Mock Gmail send, verify called
  - Validation: Logs show "Message sent to {recipient}"

- **15.3** Add sent tracking to draft metadata
  - Input: Successful send
  - Output: Draft marked as SENT with timestamp
  - Test: Verify status transitions APPROVED → SENT
  - Validation: Database query shows sent_at timestamp

- **15.4** Add safety checks for auto-send
  - Input: Approval request
  - Output: Validates MODE_DRAFT_ONLY, rate limits
  - Test: Reject if MODE_DRAFT_ONLY=true
  - Validation: Returns error "Auto-send disabled in DRAFT_ONLY mode"

**Demoable Output:** Approve draft → email sends automatically → tracked in database

---

## Sprint 16: HubSpot Contact Sync Engine
**Goal:** Pull all contacts from Pesti HubSpot for campaign targeting

### Tasks:
- **16.1** Create HubSpot contact sync service
  - Input: None (uses HUBSPOT_API_KEY)
  - Output: List of all contacts with properties
  - Test: Fetch contacts, verify pagination
  - Validation: Returns 100+ contacts from HubSpot

- **16.2** Store contacts in local database
  - Input: HubSpot contacts list
  - Output: Contacts table populated
  - Test: Sync 50 contacts, verify DB inserts
  - Validation: SELECT COUNT(*) FROM contacts > 0

- **16.3** Map HubSpot properties to contact fields
  - Input: HubSpot contact object
  - Output: Normalized contact record
  - Test: Map firstname, lastname, email, company
  - Validation: All required fields populated

- **16.4** Create segment filters (CHAINge list, Gitte's segments)
  - Input: Contact with HubSpot lists
  - Output: Segment tags applied
  - Test: Contact in "CHAINge" list → tagged
  - Validation: GET /api/contacts?segment=chainge returns filtered list

**Demoable Output:** HubSpot contacts synced to database with segments

---

## Sprint 17: Campaign Sequence Builder
**Goal:** Create reusable campaign sequences for email automation

### Tasks:
- **17.1** Create Sequence model and database schema
  - Input: Sequence definition (name, steps, delays)
  - Output: Database table with sequences
  - Test: Create sequence with 3 emails
  - Validation: Sequence persists with correct step order

- **17.2** Build sequence step engine
  - Input: Contact enrolled in sequence
  - Output: Emails scheduled at intervals
  - Test: Enroll contact → verify 3 drafts created
  - Validation: Drafts scheduled at Day 0, Day 3, Day 7

- **17.3** Add sequence enrollment API
  - Input: POST /api/sequences/{id}/enroll with contact_ids
  - Output: Contacts enrolled, first email drafted
  - Test: Enroll 5 contacts → 5 drafts created
  - Validation: Database shows enrollment records

- **17.4** Create default sequences (Welcome, Follow-up, Re-engagement)
  - Input: Sequence template
  - Output: Pre-built sequences ready to use
  - Test: Load Welcome sequence, verify 3 steps
  - Validation: GET /api/sequences returns 3 templates

**Demoable Output:** Campaign sequences running with scheduled emails

---

## Sprint 18: CHAINge List Campaign
**Goal:** Launch first campaign to CHAINge list contacts

### Tasks:
- **18.1** Pull CHAINge list from HubSpot
  - Input: HubSpot list ID for CHAINge
  - Output: Filtered contact list
  - Test: Fetch CHAINge contacts
  - Validation: Returns contacts tagged with CHAINge segment

- **18.2** Generate personalized emails for CHAINge contacts
  - Input: CHAINge contact list
  - Output: Draft per contact with personalization
  - Test: Generate 10 drafts, verify unique
  - Validation: Each draft mentions contact's company

- **18.3** Queue CHAINge campaign for approval
  - Input: Generated drafts
  - Output: Batch queued in operator dashboard
  - Test: Queue 50 drafts
  - Validation: GET /api/operator/drafts shows CHAINge campaign

- **18.4** Create campaign dashboard view
  - Input: Campaign ID
  - Output: Campaign stats (sent, pending, responses)
  - Test: View campaign progress
  - Validation: Dashboard shows 50 emails, 10 approved, 40 pending

**Demoable Output:** CHAINge campaign live with tracking dashboard

---

## Sprint 19: Pesti Full Database Campaign
**Goal:** Scale to entire Pesti HubSpot database

### Tasks:
- **19.1** Sync entire HubSpot contact database
  - Input: All contacts from Pesti HubSpot
  - Output: 1000+ contacts in database
  - Test: Run full sync, verify pagination
  - Validation: Database shows all contacts from HubSpot

- **19.2** Apply Gitte's segments and filters
  - Input: Contact properties
  - Output: Segments applied (High Value, Engaged, Cold)
  - Test: Segment 100 contacts
  - Validation: Each contact has segment tags

- **19.3** Create segment-specific campaigns
  - Input: Segment (e.g., "High Value")
  - Output: Tailored campaign sequence
  - Test: High Value → 5-email nurture sequence
  - Validation: Sequence templates per segment

- **19.4** Batch queue system for large campaigns
  - Input: 500+ contact campaign
  - Output: Drafts queued in batches of 50
  - Test: Queue 500 drafts without timeout
  - Validation: All 500 drafts created within 5 minutes

**Demoable Output:** Full database campaigns with segment targeting

---

## Sprint 20: Campaign Management Dashboard
**Goal:** Monitor and manage campaigns from operator UI

### Tasks:
- **20.1** Add campaign listing page
  - Input: GET /api/campaigns
  - Output: All active campaigns with stats
  - Test: List 5 campaigns
  - Validation: Shows name, status, sent count, response rate

- **20.2** Campaign detail view with drill-down
  - Input: Campaign ID
  - Output: Individual email statuses, responses
  - Test: Click campaign → see all emails
  - Validation: Shows which emails sent, pending, replied

- **20.3** Bulk approve/reject for campaigns
  - Input: Select 20 drafts, approve all
  - Output: Batch approval processed
  - Test: Approve 20 drafts at once
  - Validation: All 20 marked approved in <2 seconds

- **20.4** Campaign pause/resume controls
  - Input: Pause campaign button
  - Output: No new emails sent from campaign
  - Test: Pause → verify sends stop
  - Validation: Campaign status = PAUSED

**Demoable Output:** Full campaign management from web UI

---

## Validation Criteria (Per Sprint)

### Sprint 15 Success:
```bash
# Test: Approve draft and verify send
curl -X POST /api/operator/drafts/{id}/approve
# Expected: Email sent, draft status = SENT
```

### Sprint 16 Success:
```bash
# Test: Sync HubSpot contacts
curl /api/contacts/sync/hubspot
# Expected: 100+ contacts in database
```

### Sprint 17 Success:
```bash
# Test: Enroll in sequence
curl -X POST /api/sequences/welcome/enroll -d '{"contact_ids": ["123"]}'
# Expected: 3 drafts created at Day 0, 3, 7
```

### Sprint 18 Success:
```bash
# Test: Launch CHAINge campaign
curl -X POST /api/campaigns/chainge/launch
# Expected: Dashboard shows campaign progress
```

### Sprint 19 Success:
```bash
# Test: Full database sync
curl /api/contacts/sync/hubspot?full=true
# Expected: 1000+ contacts with segments
```

### Sprint 20 Success:
```bash
# Test: Campaign dashboard loads
curl /api/campaigns
# Expected: JSON with all campaigns and stats
```

---

## Technical Stack

- **HubSpot API:** Contact sync, list management
- **Gmail API:** Email sending (via service account)
- **PostgreSQL:** Contact storage, campaign tracking
- **Celery:** Background jobs for batch operations
- **FastAPI:** Campaign management endpoints
- **SQLAlchemy:** ORM for sequences and campaigns

---

## Risk Mitigation

- **Rate Limits:** Batch sends with delays between emails
- **Gmail API Quota:** Monitor daily send limit (2000/day for GSuite)
- **HubSpot Sync:** Cache contacts, sync incrementally
- **Database Load:** Index on contact_id, campaign_id
- **Approval Bottleneck:** Bulk approve feature for campaigns

---

## Success Metrics

- ✅ Auto-send works: Approve → email sent within 5 seconds
- ✅ HubSpot sync: All contacts synced in <2 minutes
- ✅ Campaign launch: 100 emails queued in <1 minute
- ✅ Segment filtering: Correct contacts in each segment
- ✅ Dashboard loads: Campaign view renders in <1 second

---

## Dependencies

- Sprint 15 depends on: Gmail connector with send capability
- Sprint 16 depends on: HubSpot connector (Sprint 12)
- Sprint 17 depends on: Draft queue system (Sprint 10)
- Sprint 18 depends on: Sprints 15, 16, 17
- Sprint 19 depends on: Sprint 18 completion
- Sprint 20 depends on: All previous sprints

---

**Total Scope:** 24 atomic tasks across 6 sprints  
**Estimated Lines:** ~2000 lines of code  
**Ship Ship Ship:** Each task commits independently, each sprint demos live
