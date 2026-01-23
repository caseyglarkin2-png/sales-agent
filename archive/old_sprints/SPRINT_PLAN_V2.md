# Sales Agent Sprint Plan v2.0

> **Goal**: Build a team of AI wingmen that can handle outreach, proposals, and become Casey's portal to a fully autonomous GTM execution engine.

---

## Current State (Completed)
- ✅ Form-based workflow processing (HubSpot webhook → Gmail draft)
- ✅ Voice profile system (Casey Larkin default)
- ✅ Dashboard with approve/reject UI
- ✅ Admin panel with workflow retry
- ✅ Duplicate detection & throttling
- ✅ Metrics & monitoring endpoints
- ✅ Research agent (basic HubSpot + Gmail lookup)

---

## Sprint 1: Voice Training from Real Emails (Week 1)
**Goal**: Train voice profile on REAL Pesti emails from HubSpot, not placeholder content.

### 1.1 HubSpot Email Extraction Agent
**Description**: Pull sent emails from HubSpot for a specific user to train voice profile.

**Tasks**:
- [ ] **1.1.1** Create HubSpot email engagement API integration
  - File: `src/connectors/hubspot_emails.py`
  - Method: `get_sent_emails(user_email, limit=100)`
  - Returns: List of email objects with subject, body, recipient, timestamp
  - Validation: Returns at least 10 emails for casey.l@pesti.io

- [ ] **1.1.2** Build email parser to extract clean text
  - File: `src/voice_trainer.py` (extend existing)
  - Handle HTML emails, strip signatures, extract core content
  - Validation: Parse 10 sample emails, output clean text

- [ ] **1.1.3** Create voice training endpoint
  - Endpoint: `POST /api/voice/train-from-hubspot`
  - Params: `{ "email": "casey.l@pesti.io", "limit": 50 }`
  - Validation: API returns trained profile summary

- [ ] **1.1.4** Analyze email patterns for style extraction
  - Extract: Greeting style, CTA patterns, sign-off, paragraph length
  - Store in VoiceProfile object
  - Validation: Profile reflects actual email patterns

### 1.2 Improved Draft Generation
**Tasks**:
- [ ] **1.2.1** Add persona-based messaging rules
  - If job title contains "Event" → Field marketing messaging
  - If job title contains "Demand" → Lead gen/velocity messaging  
  - If job title contains "Sales" → Target account/alignment messaging
  - File: `src/agents/persona_router.py`
  - Validation: 3 test contacts get appropriate messaging

- [ ] **1.2.2** Remove freight/logistics references completely
  - Audit all prompts and templates
  - Replace with GTM/Pesti language
  - Validation: No draft contains "freight" or "logistics"

**Deliverable**: Voice profile trained on real Casey emails, persona-based messaging

---

## Sprint 2: CHAINge NA Form List Processing (Week 2)
**Goal**: Process the ~500 existing CHAINge NA form submissions.

### 2.1 Bulk Contact Import
**Tasks**:
- [ ] **2.1.1** Create HubSpot list query endpoint
  - File: `src/connectors/hubspot.py` (extend)
  - Method: `get_form_submissions(form_id, limit=500)`
  - Validation: Returns all CHAINge NA submissions

- [ ] **2.1.2** Create bulk processing queue
  - File: `src/queue/bulk_processor.py`
  - Store contacts in Redis/DB queue
  - Rate limit: 20/day, 100/week
  - Validation: Queue accepts 500 contacts, processes 20/day

- [ ] **2.1.3** Add priority scoring
  - Score based on: Job title, company size, recent activity
  - Higher priority = processed first
  - File: `src/scoring/lead_scorer.py`
  - Validation: Contacts sorted by priority score

- [ ] **2.1.4** Create bulk trigger endpoint
  - Endpoint: `POST /api/bulk/start`
  - Params: `{ "form_id": "chainge-na", "limit": 500 }`
  - Validation: Initiates processing with rate limiting

### 2.2 Processing Status Dashboard
**Tasks**:
- [ ] **2.2.1** Add bulk processing status to dashboard
  - Show: Total in queue, processed today, remaining
  - Progress bar visualization
  - Validation: Dashboard shows accurate queue status

- [ ] **2.2.2** Add pause/resume controls
  - Admin can pause bulk processing
  - Resume from where stopped
  - Validation: Pause stops processing, resume continues

**Deliverable**: Bulk processing system for existing form submissions with rate limiting

---

## Sprint 3: Contact Enrichment Engine (Week 3)
**Goal**: Enrich contacts with all available data before outreach.

### 3.1 Data Enrichment Pipeline
**Tasks**:
- [ ] **3.1.1** HubSpot contact enrichment
  - Pull: Name, title, email, phone, company, owner, deals, notes
  - File: `src/enrichment/hubspot_enricher.py`
  - Validation: Returns full contact record

- [ ] **3.1.2** Company enrichment from HubSpot
  - Pull: Website, industry, size, revenue, description
  - File: `src/enrichment/company_enricher.py`
  - Validation: Returns company details

- [ ] **3.1.3** LinkedIn description extraction (if available)
  - Check HubSpot for LinkedIn URL
  - Parse public profile data
  - File: `src/enrichment/linkedin_enricher.py`
  - Validation: Returns LinkedIn summary if URL exists

- [ ] **3.1.4** Past deals & activity aggregation
  - Pull deal history, meeting notes, past emails
  - Summarize relationship status
  - File: `src/enrichment/history_enricher.py`
  - Validation: Returns relationship summary

### 3.2 Enrichment Storage
**Tasks**:
- [ ] **3.2.1** Create enriched_contacts table
  - Schema: contact_id, enrichment_data (JSONB), enriched_at
  - Migrate existing contacts
  - Validation: Table created, accepts JSON

- [ ] **3.2.2** Cache enrichment results
  - TTL: 7 days before re-enrichment
  - Validation: Cache hit returns stored data

**Deliverable**: Full contact enrichment with company, history, and activity data

---

## Sprint 4: Account-Based Prioritization (Week 4)
**Goal**: Implement account-based approach to prioritize outreach.

### 4.1 Account Analysis Agent
**Tasks**:
- [ ] **4.1.1** Company existence checker
  - Verify company exists and is viable target
  - Check website accessibility, company size
  - File: `src/agents/account_analyzer.py`
  - Validation: Returns company viability score

- [ ] **4.1.2** Decision maker identification
  - Find best contacts at each account
  - Score by title/role relevance
  - Validation: Returns ranked contact list per account

- [ ] **4.1.3** Pain point hypothesis generator
  - Based on role + industry, generate likely pain points
  - Map to Pesti solutions
  - Validation: Returns 3-5 relevant pain points

- [ ] **4.1.4** Value proposition matcher
  - Match contact persona to Pesti value props
  - Events → Field marketing
  - Demand Gen → Lead velocity
  - Sales → Marketing alignment
  - Validation: Returns tailored value prop

### 4.2 Priority Queue System
**Tasks**:
- [ ] **4.2.1** Account scoring model
  - Factors: Company size, role fit, past engagement, deal potential
  - Store score with each contact
  - Validation: All contacts have priority score

- [ ] **4.2.2** Priority-based processing
  - Process highest priority first
  - Re-score after each engagement
  - Validation: Processing follows priority order

**Deliverable**: Account-based prioritization with persona-matched messaging

---

## Sprint 5: Proposal Generation Agent (Week 5-6)
**Goal**: Agents can draft proposals in Google Docs.

### 5.1 Google Docs Integration
**Tasks**:
- [ ] **5.1.1** Google Docs API connector
  - Create, read, update documents
  - File: `src/connectors/google_docs.py`
  - Validation: Can create a test document

- [ ] **5.1.2** Proposal template system
  - Store templates in Google Drive folder
  - Clone template for new proposals
  - Validation: Template cloned successfully

- [ ] **5.1.3** Dynamic content insertion
  - Replace placeholders with contact/company data
  - Handle tables, pricing, custom sections
  - Validation: Placeholders replaced correctly

### 5.2 Proposal Agent
**Tasks**:
- [ ] **5.2.1** Proposal generation agent
  - Takes: Contact, enrichment, conversation history
  - Produces: Draft proposal document
  - File: `src/agents/proposal_writer.py`
  - Validation: Generates complete proposal

- [ ] **5.2.2** Proposal approval workflow
  - Create proposal → Review in dashboard → Send
  - Track proposal status
  - Validation: Proposal appears in dashboard

- [ ] **5.2.3** Proposal email wrapper
  - Generate email to accompany proposal
  - Include link to Google Doc
  - Validation: Email + proposal linked correctly

**Deliverable**: AI-generated proposals in Google Docs with approval workflow

---

## Sprint 6: Call Intelligence Integration (Week 7)
**Goal**: Agents have access to call recordings and notes.

### 6.1 Call Recording Access
**Tasks**:
- [ ] **6.1.1** Call recording platform integration
  - Connect to Gong/Chorus/HubSpot calls (TBD which platform)
  - File: `src/connectors/call_recordings.py`
  - Validation: Can retrieve recent call list

- [ ] **6.1.2** Call transcript parser
  - Extract key topics, action items, objections
  - Summarize call in structured format
  - Validation: Returns call summary

- [ ] **6.1.3** Call context for drafts
  - Include relevant call notes in email drafts
  - Reference specific discussions
  - Validation: Draft references call topics

### 6.2 Meeting Notes Integration
**Tasks**:
- [ ] **6.2.1** HubSpot meeting notes puller
  - Get all meeting notes for contact
  - Summarize relationship history
  - Validation: Returns meeting summaries

- [ ] **6.2.2** Action item tracker
  - Track open action items per contact
  - Flag items for follow-up
  - Validation: Action items visible in dashboard

**Deliverable**: Agents can access and leverage call/meeting context

---

## Sprint 7: Multi-Channel Outreach (Week 8)
**Goal**: Expand beyond email to multi-channel sequences.

### 7.1 Sequence Builder
**Tasks**:
- [ ] **7.1.1** Sequence definition model
  - Define: Steps, timing, channels (email, LinkedIn, call)
  - File: `src/sequences/sequence_model.py`
  - Validation: Can define 5-step sequence

- [ ] **7.1.2** Sequence execution engine
  - Execute steps at correct timing
  - Track responses, skip if replied
  - Validation: Sequence executes correctly

### 7.2 LinkedIn Integration (Optional)
**Tasks**:
- [ ] **7.2.1** LinkedIn connection request drafts
  - Generate personalized connection messages
  - Store for manual send (or API if available)
  - Validation: Generates connection message

**Deliverable**: Multi-step sequences with timing and channel mix

---

## Sprint 8: Full Agent Dashboard (Week 9-10)
**Goal**: Dashboard becomes the command center for all agents.

### 8.1 Agent Visibility
**Tasks**:
- [ ] **8.1.1** Real-time agent activity feed
  - Show what each agent is doing
  - Success/failure indicators
  - Validation: Activity updates in real-time

- [ ] **8.1.2** Agent chat interface
  - Ask agents questions about contacts
  - Get summaries, recommendations
  - Validation: Chat returns useful responses

### 8.2 Comprehensive Dashboard
**Tasks**:
- [ ] **8.2.1** Contact pipeline view
  - Stage: New, Researched, Outreached, Responded, Meeting, Proposal
  - Drag-and-drop stage changes
  - Validation: Pipeline visualization works

- [ ] **8.2.2** Daily agenda generation
  - Each day: Show priority contacts, pending approvals, follow-ups
  - Validation: Daily agenda auto-generated

- [ ] **8.2.3** Performance metrics
  - Response rates, meeting conversion, proposal win rate
  - Trend charts over time
  - Validation: Metrics displayed accurately

**Deliverable**: Full command center dashboard with agent visibility

---

## Technical Architecture Notes

### Database Schema (Additions)
```sql
-- Enriched contact data
CREATE TABLE enriched_contacts (
    id SERIAL PRIMARY KEY,
    hubspot_contact_id VARCHAR(255) UNIQUE,
    email VARCHAR(255),
    enrichment_data JSONB,
    priority_score DECIMAL(5,2),
    enriched_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bulk processing queue
CREATE TABLE bulk_queue (
    id SERIAL PRIMARY KEY,
    contact_id VARCHAR(255),
    queue_name VARCHAR(100),
    status VARCHAR(50), -- pending, processing, completed, failed
    priority INTEGER,
    scheduled_at TIMESTAMP,
    processed_at TIMESTAMP
);

-- Proposals
CREATE TABLE proposals (
    id SERIAL PRIMARY KEY,
    contact_id VARCHAR(255),
    google_doc_id VARCHAR(255),
    status VARCHAR(50), -- draft, pending_review, approved, sent
    created_by VARCHAR(255),
    approved_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sequences
CREATE TABLE sequences (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    steps JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sequence_enrollments (
    id SERIAL PRIMARY KEY,
    contact_id VARCHAR(255),
    sequence_id INTEGER REFERENCES sequences(id),
    current_step INTEGER,
    status VARCHAR(50),
    next_step_at TIMESTAMP
);
```

### Agent Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    Operator Dashboard                    │
├─────────────────────────────────────────────────────────┤
│  Approve/Reject  │  Priority Queue  │  Agent Chat       │
└────────┬─────────┴────────┬─────────┴────────┬──────────┘
         │                  │                  │
    ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
    │  Draft   │       │ Enrich  │       │Research │
    │ Writer   │       │ Agent   │       │ Agent   │
    └────┬────┘       └────┬────┘       └────┬────┘
         │                  │                  │
    ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
    │Proposal │       │ Account │       │Persona  │
    │ Writer  │       │Analyzer │       │ Router  │
    └────┬────┘       └────┬────┘       └────┬────┘
         │                  │                  │
    ┌────▼──────────────────▼──────────────────▼────┐
    │              Connectors Layer                  │
    │  HubSpot │ Gmail │ Calendar │ Drive │ Docs   │
    └────────────────────────────────────────────────┘
```

---

## Success Metrics per Sprint

| Sprint | Metric | Target |
|--------|--------|--------|
| 1 | Voice accuracy | 90% match to real email style |
| 2 | Bulk processing | 500 contacts queued, 20/day rate |
| 3 | Enrichment coverage | 95% contacts fully enriched |
| 4 | Priority accuracy | High-priority → higher response rate |
| 5 | Proposals generated | 10 proposals/week |
| 6 | Call context usage | 80% of drafts reference past calls |
| 7 | Multi-channel | 3-step sequences live |
| 8 | Dashboard usage | 100% of approvals through dashboard |

---

## Immediate Next Actions (This Session)

1. ✅ Fix voice profile (remove freight references)
2. 🔄 Add HubSpot email training endpoint
3. 🔄 Update dashboard with better approve/reject UI
4. 📋 Deploy and test

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| HubSpot API rate limits | Implement backoff, cache aggressively |
| Email deliverability | Warm up slowly, monitor bounce rates |
| Data quality | Validate before outreach, flag issues |
| Agent hallucination | Human review required, prompt guardrails |
| Scale issues | Start with 20/day, increase gradually |

