# CaseyOS Sprint Plan v2: Product-First

**Date:** January 24, 2026  
**Last Updated:** January 24, 2026 (incorporated subagent review feedback)  
**Philosophy:** Ship product, not infrastructure. Small atomic commits. Every sprint demos something real.  
**Auth:** Google OAuth (your accounts) - no admin password bullshit.

---

## Project Vision

CaseyOS is a **GTM command center** that operates like Casey's Chief of Staff:
- **Today's Moves** - prioritized list of what to do next
- **Proactive Signal Ingestion** - pulls from HubSpot, email, content engagement
- **Voice Profile** - writes like Casey (trained on real emails, newsletters, YouTube)
- **One-Click Execution** - draft, send, book, skip
- **Closed-Loop Learning** - tracks outcomes, improves over time

---

## Sprint Dependencies (Corrected)

```
Sprint 1 (Auth + ALL OAuth Scopes)
    ↓
Sprint 2 (Queue)
    ↓
Sprint 3 (Signals) ───┐
    ↓                 │
Sprint 4 (Voice) ─────┼──→ Sprint 6 depends on BOTH
    ↓                 │
Sprint 5 (APS) ───────┘
    ↓
Sprint 6 (Execution)
    ↓
Sprint 7 (Outcomes)
```

---

## Migration Rollback Protocol (All Sprints)

**Before any migration rollback:**
1. Stop all Celery workers: `celery -A src.celery_app control shutdown`
2. Disable signal ingestion job
3. Backup affected tables: `pg_dump -t <table_name> > backup.sql`

**Rollback:**
```bash
alembic downgrade -1
```

**After rollback:**
1. Restart workers
2. Verify app starts without migration errors
3. If needed, restore from backup

---

## Sprint 1: Auth & Dashboard Shell

**Demo:** Casey logs in with Google, sees a dashboard with navigation. Nothing else works yet, but the shell is there.

### Tasks

#### 1.1 Google OAuth Setup (with ALL required scopes)
- **Scope:** Implement Google OAuth2 login flow with all scopes needed for later sprints
- **Files:** `src/auth/google_oauth.py`, `src/routes/auth.py`, `src/main.py`
- **OAuth Scopes (request ALL upfront to avoid re-consent):**
  ```python
  SCOPES = [
      "openid",
      "email",
      "profile",
      # For Sprint 6 email execution:
      "https://www.googleapis.com/auth/gmail.send",
      "https://www.googleapis.com/auth/gmail.compose",
      # For Sprint 6 meeting booking:
      "https://www.googleapis.com/auth/calendar",
      "https://www.googleapis.com/auth/calendar.events",
  ]
  ```
- **Schema:**
  ```python
  # User model (simple)
  class User(Base):
      id: UUID
      email: str  # Google email
      name: str
      picture: str  # Google profile pic
      google_tokens: JSONB  # Store access/refresh tokens for Gmail/Calendar
      created_at: datetime
      last_login: datetime
  ```
- **Validation:**
  ```bash
  # Navigate to /login -> redirects to Google -> returns to /dashboard with session
  curl -I https://app.url/login  # 302 to Google
  curl -I https://app.url/dashboard  # 302 to /login if not authed
  ```
  ```python
  def test_oauth_scopes_include_gmail():
      # After login, verify we can call Gmail API
      response = client.get("/api/test/gmail-access")
      assert response.status_code == 200
  
  def test_oauth_scopes_include_calendar():
      # After login, verify we can call Calendar API
      response = client.get("/api/test/calendar-access")
      assert response.status_code == 200
  ```
- **Acceptance:** Can log in with casey.l@pesti.io or casey@dwtb.com, see dashboard, Gmail/Calendar APIs accessible
- **Rollback:** Remove auth routes, all routes public

#### 1.2 Session Management
- **Scope:** Cookie-based sessions with secure settings
- **Files:** `src/auth/session.py`, update `src/main.py`
- **Validation:**
  ```bash
  # After login, session cookie exists and is httponly
  curl -c cookies.txt https://app.url/auth/callback?code=xxx
  cat cookies.txt  # session cookie present
  ```
- **Acceptance:** Session persists across requests, expires after 7 days
- **Rollback:** Clear all sessions, revert to stateless

#### 1.3 Protected Route Decorator
- **Scope:** `@require_auth` decorator that checks session, returns 401 if not logged in
- **Files:** `src/auth/decorators.py`
- **Validation:**
  ```python
  # test_auth.py
  def test_protected_route_without_auth():
      response = client.get("/api/command-queue")
      assert response.status_code == 401
  
  def test_protected_route_with_auth():
      # mock session
      response = client.get("/api/command-queue", cookies={"session": valid_session})
      assert response.status_code == 200
  ```
- **Acceptance:** All `/api/*` routes protected, `/health` and `/login` public
- **Rollback:** Remove decorator usage

#### 1.4 Dashboard Shell UI
- **Scope:** Basic HTML dashboard with sidebar nav (Today's Moves, Signals, Voice, Settings)
- **Files:** `src/templates/dashboard.html`, `src/templates/base.html`, `src/static/css/dashboard.css`
- **Validation:** Manual - load /dashboard, see nav, user avatar in corner
- **Acceptance:** Responsive, shows user name/pic from Google, nav links exist (can be dead)
- **Rollback:** Revert template files

#### 1.5 Logout Flow
- **Scope:** `/logout` clears session, redirects to /login
- **Files:** `src/routes/auth.py`
- **Validation:**
  ```bash
  curl -X POST https://app.url/logout -b cookies.txt -c cookies.txt
  # Session cookie cleared
  ```
- **Acceptance:** After logout, /dashboard redirects to /login
- **Rollback:** N/A

#### 1.6 Allowed Users List
- **Scope:** Only allow specific Google emails (casey.l@pesti.io, casey@dwtb.com, etc.)
- **Files:** `src/auth/allowed_users.py` or env var `ALLOWED_EMAILS`
- **Validation:**
  ```python
  def test_unauthorized_email_rejected():
      # Mock Google returning random@gmail.com
      response = client.get("/auth/callback?code=xxx")
      assert response.status_code == 403
  ```
- **Acceptance:** Only allowed emails can access; others get "Access Denied" page
- **Rollback:** Remove check, allow all Google accounts

---

## Sprint 2: Command Queue Foundation

**Demo:** Casey sees "Today's Moves" with 10 sample priorities. Can mark them done or skip. Data persists.

### Tasks

#### 2.1 Command Queue Data Model
- **Scope:** Database models for queue items
- **Files:** `src/models/command_queue.py`, migration
- **Schema:**
  ```python
  class CommandQueueItem(Base):
      id: UUID
      title: str  # "Follow up with John at Acme"
      description: str  # More context
      action_type: str  # "send_email", "book_meeting", "review_deal", etc.
      priority_score: float  # 0-100, computed by APS
      status: str  # "pending", "completed", "skipped", "snoozed"
      due_date: Optional[datetime]
      
      # Context links
      contact_id: Optional[str]  # HubSpot contact ID
      deal_id: Optional[str]  # HubSpot deal ID
      company_id: Optional[str]  # HubSpot company ID
      
      # Metadata
      reasoning: str  # "Because they opened your email 3x this week"
      drivers: JSONB  # {"urgency": 8, "revenue": 9, "effort": 3}
      
      created_at: datetime
      updated_at: datetime
      completed_at: Optional[datetime]
  ```
- **Validation:**
  ```bash
  alembic upgrade head
  # Tables exist
  psql -c "SELECT * FROM command_queue_items LIMIT 1;"
  ```
- **Acceptance:** Migration runs, tables exist, can insert/query
- **Rollback:** `alembic downgrade -1`

#### 2.2 Command Queue CRUD API
- **Scope:** REST endpoints for queue items
- **Files:** `src/routes/command_queue.py`, `src/schemas/command_queue.py`
- **Endpoints:**
  ```
  GET  /api/command-queue          # List items (default: pending, sorted by priority)
  GET  /api/command-queue/:id      # Get single item
  POST /api/command-queue          # Create item (for testing/seeding)
  PATCH /api/command-queue/:id     # Update status, snooze, etc.
  ```
- **Validation:**
  ```python
  def test_list_command_queue():
      response = client.get("/api/command-queue")
      assert response.status_code == 200
      assert "items" in response.json()
  
  def test_complete_item():
      response = client.patch(f"/api/command-queue/{item_id}", json={"status": "completed"})
      assert response.status_code == 200
      assert response.json()["status"] == "completed"
  ```
- **Acceptance:** All CRUD operations work, proper error handling
- **Rollback:** Remove routes

#### 2.3 Today's Moves UI
- **Scope:** Dashboard page showing top 10 queue items with actions
- **Files:** `src/templates/todays_moves.html`, `src/static/js/todays_moves.js`
- **UI Elements:**
  - Priority badge (color-coded)
  - Title + description
  - Action type icon
  - "Complete" and "Skip" buttons
  - "Snooze" dropdown (1 hour, tomorrow, next week)
  - Reasoning tooltip on hover
- **Validation:** Manual click-through + screenshot
- **Acceptance:** Items render, buttons work, status updates persist on refresh
- **Rollback:** Revert template

#### 2.4 Seed Test Data (Development Only)
- **Scope:** Development-only script to populate queue with realistic test items
- **Files:** `scripts/seed_command_queue.py`
- **Data:** 15-20 items across different types:
  - 5x follow-up emails
  - 3x meeting prep
  - 3x deal review
  - 2x proposal send
  - 2x check-in calls
- **Production Guard:**
  ```python
  if settings.ENVIRONMENT == "production":
      raise RuntimeError("Seeds disabled in production - use signal ingestion instead")
  ```
- **Validation:**
  ```bash
  python scripts/seed_command_queue.py --clear  # Clear first
  python scripts/seed_command_queue.py
  curl https://app.url/api/command-queue | jq '.items | length'
  # Should return 15-20
  
  # Running again WITHOUT --clear should warn
  python scripts/seed_command_queue.py
  # "Queue not empty, use --clear first"
  ```
- **Acceptance:** Seed runs in dev only, requires --clear to re-run
- **Rollback:** `python scripts/seed_command_queue.py --clear`

#### 2.5 Queue Filtering & Sorting
- **Scope:** API query params for filtering/sorting
- **Files:** `src/routes/command_queue.py`
- **Params:**
  ```
  ?status=pending,completed,skipped
  ?action_type=send_email,book_meeting
  ?sort=priority_score,-created_at
  ?limit=10&offset=0
  ```
- **Validation:**
  ```python
  def test_filter_by_status():
      response = client.get("/api/command-queue?status=completed")
      for item in response.json()["items"]:
          assert item["status"] == "completed"
  ```
- **Acceptance:** All filters work, proper pagination
- **Rollback:** Remove filter logic, return all

#### 2.6 Queue Item Detail View
- **Scope:** Click item to see full context (contact info, deal info, history)
- **Files:** `src/templates/queue_item_detail.html`
- **Validation:** Manual - click item, see expanded view with all fields
- **Acceptance:** All item fields visible, back button works
- **Rollback:** Remove detail route

---

## Sprint 3: HubSpot Signal Ingestion

**Demo:** Queue automatically populates with real priorities from HubSpot data. No more test data.

### Tasks

#### 3.1a HubSpot Service Layer with Rate Limiting
- **Scope:** Clean abstraction for HubSpot API calls with rate limiting
- **Files:** `src/integrations/hubspot/client.py`, `src/integrations/hubspot/models.py`
- **Rate Limiting (HubSpot limits: 100 req/10 sec, 150k/day):**
  ```python
  class HubSpotClient:
      def __init__(self):
          self.rate_limiter = TokenBucket(
              tokens_per_second=10,  # 100 per 10 seconds
              max_tokens=100
          )
      
      async def _request(self, endpoint: str) -> dict:
          await self.rate_limiter.acquire()
          response = await httpx.get(endpoint, headers=self.headers)
          if response.status_code == 429:
              # Exponential backoff
              await asyncio.sleep(self._backoff_delay())
              return await self._request(endpoint)
          return response.json()
  ```
- **Methods:**
  ```python
  class HubSpotClient:
      def get_contacts(self, limit=100, after=None) -> List[Contact]
      def get_deals(self, limit=100, after=None) -> List[Deal]
      def get_companies(self, limit=100, after=None) -> List[Company]
      def get_emails(self, owner_email: str, limit=100) -> List[Email]
      def get_meetings(self, owner_email: str) -> List[Meeting]
      def get_deal_pipeline(self) -> List[Stage]
      def get_closed_deals(self, outcome: str = "won") -> List[Deal]  # For APS learning
  ```
- **Validation:**
  ```python
  def test_hubspot_contacts():
      client = HubSpotClient(api_key=os.getenv("HUBSPOT_API_KEY"))
      contacts = client.get_contacts(limit=5)
      assert len(contacts) <= 5
      assert all(hasattr(c, "email") for c in contacts)
  
  def test_rate_limit_respected():
      # Make 15 rapid requests
      start = time.time()
      for _ in range(15):
          client.get_contacts(limit=1)
      elapsed = time.time() - start
      # Should take at least 1.5 seconds (15 requests at 10/sec)
      assert elapsed >= 1.5
  ```
- **Acceptance:** All methods work with real HubSpot data, respects rate limits
- **Rollback:** Use mock data

#### 3.1b HubSpot Response Caching
- **Scope:** Cache HubSpot responses to reduce API calls
- **Files:** `src/integrations/hubspot/cache.py`
- **Caching Strategy:**
  ```python
  CACHE_TTL = {
      "contacts": 300,      # 5 minutes
      "deals": 300,         # 5 minutes
      "deal_pipeline": 3600, # 1 hour (rarely changes)
      "companies": 600,     # 10 minutes
  }
  ```
- **Validation:**
  ```python
  def test_cache_hit():
      client.get_contacts(limit=5)  # Cache miss
      client.get_contacts(limit=5)  # Cache hit
      # Verify only 1 API call made
  ```
- **Acceptance:** Repeated calls within TTL don't hit HubSpot API
- **Rollback:** Disable cache, always fetch fresh

#### 3.2 Signal Detection Rules
- **Scope:** Rules that detect actionable signals from HubSpot data
- **Files:** `src/signals/detectors.py`, `src/signals/rules.py`
- **Signals to Detect:**
  ```python
  SIGNAL_RULES = [
      # High priority
      "deal_stalled_7_days",      # Deal hasn't moved stages in 7+ days
      "proposal_sent_no_response", # Proposal sent, no activity in 3+ days
      "meeting_scheduled_today",   # Prep for today's meetings
      "contract_expiring_30_days", # Renewal due
      
      # Medium priority
      "new_lead_uncontacted",      # New contact, no outreach yet
      "email_opened_no_reply",     # They opened 3x but didn't reply
      "deal_close_date_passed",    # Close date was yesterday
      
      # Low priority
      "inactive_contact_90_days",  # Haven't talked in 90 days
      "company_news_trigger",      # Company in the news (future)
  ]
  ```
- **Validation:**
  ```python
  def test_stalled_deal_detection():
      deal = Deal(last_modified=datetime.now() - timedelta(days=10), stage="proposal")
      signals = detect_signals(deal)
      assert "deal_stalled_7_days" in [s.type for s in signals]
  ```
- **Acceptance:** Each rule fires correctly on test data
- **Rollback:** Disable individual rules

#### 3.3 Signal to Queue Item Mapper
- **Scope:** Convert detected signals into queue items with idempotency key
- **Files:** `src/signals/mapper.py`
- **Idempotency Strategy:**
  ```python
  def signal_to_queue_item(signal: Signal) -> CommandQueueItem:
      # Generate idempotency hash to prevent duplicates
      # Date bucket = daily for high-frequency, weekly for low-frequency
      date_bucket = signal.detected_at.strftime("%Y-%m-%d")  # Daily bucket
      signal_hash = hashlib.sha256(
          f"{signal.type}:{signal.entity_id}:{date_bucket}".encode()
      ).hexdigest()[:16]
      
      return CommandQueueItem(
          signal_hash=signal_hash,  # Unique constraint on this field
          title=generate_title(signal),
          action_type=map_action_type(signal),
          ...
      )
  ```
- **Validation:**
  ```python
  def test_signal_mapping():
      signal = Signal(type="deal_stalled_7_days", deal_id="123", deal_name="Acme")
      item = signal_to_queue_item(signal)
      assert item.title == "Follow up on stalled deal: Acme"
      assert item.action_type == "send_email"
      assert item.deal_id == "123"
      assert item.signal_hash is not None
  ```
- **Acceptance:** All signal types map to appropriate queue items with unique hash
- **Rollback:** Return empty items

#### 3.4 Signal Ingestion Job (Idempotent)
- **Scope:** Background job that runs hourly to ingest signals
- **Files:** `src/tasks/signal_ingest.py`, `src/celery_app.py`
- **Idempotency (Critical):**
  ```python
  async def ingest_signals():
      signals = detect_all_signals()
      items = [signal_to_queue_item(s) for s in signals]
      
      # Upsert with conflict handling
      for item in items:
          await db.execute(
              insert(CommandQueueItem)
              .values(**item.dict())
              .on_conflict_do_nothing(index_elements=['signal_hash'])
          )
  ```
- **Logic:**
  1. Fetch recent HubSpot data (deals, contacts, emails)
  2. Run signal detection rules
  3. Generate queue items with signal_hash
  4. Upsert with ON CONFLICT DO NOTHING
  5. Log ingestion stats
- **Validation:**
  ```python
  def test_signal_ingestion_idempotent():
      ingest_signals()
      count_before = get_queue_count()
      ingest_signals()  # Run again immediately
      count_after = get_queue_count()
      assert count_before == count_after  # No duplicates
  ```
  ```bash
  # Manual trigger
  python -c "from src.tasks.signal_ingest import ingest_signals; ingest_signals()"
  # Check queue
  curl https://app.url/api/command-queue | jq '.items | length'
  ```
- **Acceptance:** Job runs without error, creates real queue items, no duplicates on re-run
- **Rollback:** Disable celery beat schedule

#### 3.5 Ingestion Status Endpoint
- **Scope:** API to check last ingestion status and stats
- **Files:** `src/routes/signals.py`
- **Response:**
  ```json
  {
    "last_run": "2026-01-24T10:00:00Z",
    "status": "success",
    "deals_processed": 45,
    "contacts_processed": 230,
    "signals_detected": 12,
    "queue_items_created": 8,
    "errors": []
  }
  ```
- **Validation:**
  ```python
  def test_ingestion_status():
      response = client.get("/api/signals/status")
      assert "last_run" in response.json()
  ```
- **Acceptance:** Shows accurate ingestion stats
- **Rollback:** Return empty stats

#### 3.6 Manual Refresh Button
- **Scope:** UI button to trigger signal ingestion on demand
- **Files:** `src/templates/todays_moves.html`, `src/routes/signals.py`
- **Validation:** Click button, see loading spinner, queue updates
- **Acceptance:** Refresh completes within 30 seconds, shows new items
- **Rollback:** Hide button

---

## Sprint 4: Voice Profile & Knowledge Training

**Demo:** Casey can generate a draft email that sounds like him. Voice is trained on real HubSpot emails and Freight Marketer newsletters.

### Tasks

#### 4.0 Voice Training Content Audit (DO FIRST)
- **Scope:** Verify access to all training sources BEFORE writing code
- **Files:** None (audit only)
- **Checklist:**
  - [ ] Freight Marketer newsletter access method confirmed:
    - IMAP access to newsletter inbox? OR
    - Archive URL available? OR
    - Manual export to files?
  - [ ] YouTube API credentials provisioned in Google Cloud Console
  - [ ] DWTB channel ID confirmed, transcripts verified available
  - [ ] Minimum viable training confirmed: 50+ HubSpot sent emails exist
- **Fallback Plan:**
  - If newsletters unavailable → proceed with HubSpot emails only
  - If YouTube unavailable → proceed with emails + newsletters only
  - If all else fails → manual voice samples (Casey provides 10-20 example emails)
- **Validation:** Document access method for each source
- **Acceptance:** Clear path to at least ONE training source confirmed
- **Rollback:** N/A (audit only)

#### 4.1 Voice Profile Data Model
- **Scope:** Store voice profile configuration and training data
- **Files:** `src/models/voice_profile.py`, migration
- **Schema:**
  ```python
  class VoiceProfile(Base):
      id: UUID
      name: str  # "casey_default"
      tone: str  # "professional", "casual", "witty"
      
      # Training sources
      email_samples: JSONB  # List of training emails
      newsletter_samples: JSONB  # Freight Marketer articles
      youtube_transcripts: JSONB  # DWTB transcripts
      
      # Extracted patterns
      signature_phrases: List[str]
      greeting_style: str
      closing_style: str
      emoji_usage: str  # "none", "minimal", "frequent"
      
      created_at: datetime
      updated_at: datetime
  ```
- **Validation:** Migration runs, can insert profile
- **Acceptance:** Profile persists with all fields
- **Rollback:** Downgrade migration

#### 4.2 Email Training Pipeline
- **Scope:** Extract voice patterns from HubSpot sent emails
- **Files:** `src/voice/trainers/email_trainer.py`
- **Logic:**
  1. Fetch sent emails from HubSpot (already works)
  2. Extract: greetings, closings, sentence patterns, vocabulary
  3. Store in voice profile
- **Validation:**
  ```python
  def test_email_training():
      trainer = EmailTrainer(hubspot_client)
      profile = trainer.train(owner_email="casey.l@pesti.io", sample_count=50)
      assert len(profile.signature_phrases) > 0
      assert profile.greeting_style is not None
  ```
- **Acceptance:** Training extracts meaningful patterns from 50+ emails
- **Rollback:** Clear training data

#### 4.3 Newsletter Ingestion
- **Scope:** Fetch and parse Freight Marketer newsletters
- **Files:** `src/voice/trainers/newsletter_trainer.py`, `src/integrations/newsletter.py`
- **Sources:**
  - Freight Marketer email archives (provide access)
  - Or: RSS feed if available
  - Or: Manual upload of newsletter HTML/text
- **Validation:**
  ```python
  def test_newsletter_fetch():
      newsletters = fetch_newsletters(source="freight_marketer", limit=10)
      assert len(newsletters) == 10
      assert all(n.content for n in newsletters)
  ```
- **Acceptance:** Can fetch and parse 10+ newsletters
- **Rollback:** Skip newsletter training

#### 4.4 YouTube Transcript Ingestion
- **Scope:** Fetch transcripts from "Dude, What's the Bid?!" videos
- **Files:** `src/voice/trainers/youtube_trainer.py`, `src/integrations/youtube.py`
- **Logic:**
  1. Use YouTube API or youtube-transcript-api
  2. Fetch transcripts for DWTB playlist/channel
  3. Extract Casey's speaking patterns (if identifiable)
- **Validation:**
  ```python
  def test_youtube_transcripts():
      transcripts = fetch_youtube_transcripts(channel="dwtb", limit=5)
      assert len(transcripts) == 5
      assert all(t.text for t in transcripts)
  ```
- **Acceptance:** Can fetch 5+ video transcripts
- **Rollback:** Skip YouTube training

#### 4.5 Voice Generation Service
- **Scope:** Generate text in Casey's voice using trained profile
- **Files:** `src/voice/generator.py`
- **Methods:**
  ```python
  class VoiceGenerator:
      def generate_email(self, context: EmailContext, profile: VoiceProfile) -> str
      def generate_followup(self, context: FollowupContext, profile: VoiceProfile) -> str
      def generate_linkedin_message(self, context: LinkedInContext, profile: VoiceProfile) -> str
  ```
- **Validation:**
  ```python
  def test_email_generation():
      generator = VoiceGenerator()
      email = generator.generate_email(
          context=EmailContext(recipient="John", company="Acme", topic="demo followup"),
          profile=casey_profile
      )
      assert len(email) > 100
      # Check for Casey's patterns
      assert any(phrase in email for phrase in casey_profile.signature_phrases)
  ```
- **Acceptance:** Generated emails pass "sounds like Casey" test
- **Rollback:** Use generic templates

#### 4.6 Draft Preview UI
- **Scope:** UI to preview and edit generated drafts before sending
- **Files:** `src/templates/draft_preview.html`
- **Features:**
  - Show generated draft
  - Edit inline
  - Regenerate button
  - Send button (wired to HubSpot)
  - Cancel button
- **Validation:** Manual - generate draft, edit, send
- **Acceptance:** Full flow works end-to-end
- **Rollback:** Hide draft preview

#### 4.7 Training Status Dashboard
- **Scope:** Show what the voice profile has been trained on
- **Files:** `src/templates/voice_settings.html`
- **Shows:**
  - Emails analyzed: 100
  - Newsletters ingested: 15
  - YouTube videos: 8
  - Last trained: 2026-01-24
  - Sample phrases extracted
- **Validation:** Manual - view dashboard
- **Acceptance:** Accurate stats displayed
- **Rollback:** Hide dashboard

---

## Sprint 5: Action Priority Score (APS)

**Demo:** Queue items are ranked by a real priority score. Casey can see WHY each item is ranked.

### Tasks

#### 5.0 Win/Loss Data Model (Prerequisite for APS Learning)
- **Scope:** Create model to track historical deal outcomes for learning
- **Files:** `src/models/deal_outcome.py`, migration
- **Schema:**
  ```python
  class DealOutcome(Base):
      id: UUID
      deal_id: str  # HubSpot deal ID
      deal_name: str
      outcome: str  # "won", "lost", "churned"
      
      # Segmentation for learning
      segment: str  # e.g., "enterprise_logistics", "smb_freight"
      industry: str
      company_size: str  # "1-10", "11-50", "51-200", etc.
      
      # Outcome data
      deal_value: float
      sales_cycle_days: int
      close_reason: Optional[str]  # "price", "competitor", "timing", etc.
      
      won_at: Optional[datetime]
      lost_at: Optional[datetime]
      created_at: datetime
  ```
- **Data Source:** Backfill from HubSpot closed deals via Task 3.1a (`get_closed_deals`)
- **Validation:**
  ```python
  def test_win_rate_by_segment():
      outcomes = DealOutcome.query.filter_by(segment="enterprise_logistics").all()
      win_rate = len([o for o in outcomes if o.outcome == "won"]) / len(outcomes)
      assert 0 <= win_rate <= 1
  ```
- **Acceptance:** Can calculate win rate by segment, migration runs
- **Rollback:** Downgrade migration

#### 5.0b Backfill Historical Outcomes
- **Scope:** One-time job to backfill deal outcomes from HubSpot
- **Files:** `scripts/backfill_outcomes.py`
- **Logic:**
  1. Fetch all closed deals from HubSpot (won + lost)
  2. Derive segment from company industry + size
  3. Insert into DealOutcome table
- **Validation:**
  ```bash
  python scripts/backfill_outcomes.py
  psql -c "SELECT outcome, COUNT(*) FROM deal_outcomes GROUP BY outcome;"
  ```
- **Acceptance:** Historical outcomes populated, stats make sense
- **Rollback:** Truncate deal_outcomes table

#### 5.1 APS Calculation Service
- **Scope:** Calculate priority score for each queue item
- **Files:** `src/aps/calculator.py`
- **Formula:**
  ```python
  def calculate_aps(item: CommandQueueItem, context: APSContext) -> float:
      score = 0.0
      
      # Revenue Impact (40%)
      score += 0.4 * calculate_revenue_score(item, context)
      
      # Urgency (25%)
      score += 0.25 * calculate_urgency_score(item, context)
      
      # Effort to Complete (15%) - inverted, easy = higher
      score += 0.15 * (100 - calculate_effort_score(item, context))
      
      # Strategic Value (20%)
      score += 0.20 * calculate_strategic_score(item, context)
      
      return min(100, max(0, score))
  ```
- **Validation:**
  ```python
  def test_aps_high_revenue_high_urgency():
      item = CommandQueueItem(deal_value=50000, due_date=tomorrow)
      score = calculate_aps(item, context)
      assert score > 80
  
  def test_aps_low_priority():
      item = CommandQueueItem(deal_value=1000, due_date=next_month)
      score = calculate_aps(item, context)
      assert score < 40
  ```
- **Acceptance:** Scores range 0-100, high-value urgent items rank highest
- **Rollback:** Use static priority

#### 5.2 Revenue Score Component
- **Scope:** Score based on deal value, pipeline stage, customer LTV, historical win rate
- **Files:** `src/aps/components/revenue.py`
- **Factors:**
  - Deal amount (higher = better)
  - Pipeline stage (closer to close = better)
  - Existing customer (expansion = bonus)
  - **Historical win rate for segment** (from DealOutcome table)
- **Validation:** Unit tests for each factor
- **Acceptance:** Revenue score correlates with actual revenue potential
- **Rollback:** Use flat revenue score

#### 5.3 Urgency Score Component
- **Scope:** Score based on time sensitivity
- **Files:** `src/aps/components/urgency.py`
- **Factors:**
  - Due date proximity (closer = higher)
  - SLA requirements
  - Event deadlines (conferences, demos)
  - Stale duration (longer = higher urgency to act)
- **Validation:** Unit tests for time-based scenarios
- **Acceptance:** Overdue items score highest urgency
- **Rollback:** Use flat urgency score

#### 5.4 Effort Score Component
- **Scope:** Score based on how hard the action is
- **Files:** `src/aps/components/effort.py`
- **Factors:**
  - Action type (email = low, research = high)
  - Required prep time
  - Dependencies on others
  - Information completeness
- **Validation:** Unit tests for effort types
- **Acceptance:** Quick wins score low effort (high priority boost)
- **Rollback:** Use flat effort score

#### 5.5 Strategic Score Component
- **Scope:** Score based on strategic fit
- **Files:** `src/aps/components/strategic.py`
- **Factors:**
  - ICP fit (industry, size, use case)
  - Logo value (big name = bonus)
  - Expansion potential
  - Reference potential
- **Validation:** Unit tests for ICP matching
- **Acceptance:** High-ICP accounts score higher
- **Rollback:** Use flat strategic score

#### 5.6 APS Explainability
- **Scope:** Generate human-readable reasoning for scores
- **Files:** `src/aps/explainer.py`
- **Output:**
  ```json
  {
    "score": 87,
    "reasoning": "High priority because $50k deal closing this week",
    "drivers": [
      {"factor": "revenue", "score": 95, "reason": "$50k ARR potential"},
      {"factor": "urgency", "score": 90, "reason": "Close date in 3 days"},
      {"factor": "effort", "score": 20, "reason": "Just need to send proposal"},
      {"factor": "strategic", "score": 75, "reason": "Target industry, mid-market"}
    ]
  }
  ```
- **Validation:**
  ```python
  def test_explainability():
      explanation = explain_aps(item, score=87)
      assert "reasoning" in explanation
      assert len(explanation["drivers"]) == 4
  ```
- **Acceptance:** Every score has readable explanation
- **Rollback:** Hide explanation

#### 5.7 APS Recalculation Job
- **Scope:** Background job to recalculate APS for all pending items
- **Files:** `src/tasks/aps_recalc.py`
- **Logic:** Run hourly, update scores, re-sort queue
- **Validation:**
  ```bash
  python -c "from src.tasks.aps_recalc import recalculate_all; recalculate_all()"
  # Verify scores updated
  ```
- **Acceptance:** All items have fresh scores, sorted correctly
- **Rollback:** Disable job

#### 5.8 UI: Score Display & Drivers
- **Scope:** Show APS score and reasoning in queue UI
- **Files:** `src/templates/todays_moves.html`
- **Features:**
  - Score badge (color: red >80, yellow 50-80, green <50)
  - Hover tooltip with drivers
  - "Why?" link to full explanation
- **Validation:** Manual - hover items, see explanations
- **Acceptance:** All items show score and reasoning
- **Rollback:** Hide score details

---

## Sprint 6: One-Click Execution

**Demo:** Casey can click "Execute" on a queue item and it drafts/sends the email or books the meeting.

### Tasks

#### 6.1 Action Executor Framework
- **Scope:** Base framework for executing actions
- **Files:** `src/actions/executor.py`, `src/actions/base.py`
- **Interface:**
  ```python
  class ActionExecutor:
      def execute(self, item: CommandQueueItem, dry_run: bool = False) -> ActionResult
      def preview(self, item: CommandQueueItem) -> ActionPreview
      def rollback(self, execution_id: str) -> bool
  ```
- **Validation:**
  ```python
  def test_dry_run():
      result = executor.execute(item, dry_run=True)
      assert result.executed == False
      assert result.preview is not None
  ```
- **Acceptance:** Framework supports multiple action types
- **Rollback:** Disable executor

#### 6.2 Email Action Handler (Draft vs Send Explicit)
- **Scope:** Execute "send_email" actions with explicit mode selection
- **Files:** `src/actions/handlers/email.py`
- **Execution Modes (user chooses, draft is default):**
  1. **Draft mode (default):** Create Gmail draft, log to HubSpot as "drafted"
  2. **Send mode:** Send via Gmail SMTP, log to HubSpot as "sent"
- **Schema:**
  ```python
  class EmailExecuteRequest(BaseModel):
      queue_item_id: UUID
      execution_mode: Literal["draft", "send"] = "draft"  # Default to DRAFT
  ```
- **Logic:**
  1. Generate draft using voice profile
  2. Preview draft
  3. On confirm:
     - If mode="draft": Create Gmail draft, return draft_id
     - If mode="send": Send via Gmail, log to HubSpot
  4. Mark queue item complete
- **Validation:**
  ```python
  def test_email_draft_mode():
      result = executor.execute(item, mode="draft")
      assert result.gmail_draft_id is not None
      assert result.sent == False
  
  def test_email_send_mode():
      result = executor.execute(item, mode="send")
      assert result.sent == True
      assert result.hubspot_logged == True
  ```
- **Acceptance:** Default is DRAFT (never auto-send), user must explicitly choose "send"
- **Rollback:** Delete created draft

#### 6.3 Meeting Action Handler
- **Scope:** Execute "book_meeting" actions
- **Files:** `src/actions/handlers/meeting.py`
- **Logic:**
  1. Check calendar availability
  2. Suggest times
  3. Create meeting in HubSpot/Calendar
  4. Send invite
- **Validation:**
  ```python
  def test_meeting_booking():
      item = CommandQueueItem(action_type="book_meeting", contact_id="123")
      result = executor.execute(item)
      assert result.meeting_link is not None
  ```
- **Acceptance:** Meetings booked in calendar
- **Rollback:** Cancel meeting

#### 6.4 Task Creation Handler
- **Scope:** Execute "create_task" actions
- **Files:** `src/actions/handlers/task.py`
- **Logic:** Create HubSpot task for follow-up
- **Validation:** Task appears in HubSpot
- **Acceptance:** Tasks created with correct properties
- **Rollback:** Delete task

#### 6.5 Execution Confirmation UI
- **Scope:** Modal to confirm action before executing
- **Files:** `src/templates/components/confirm_modal.html`
- **Features:**
  - Show preview of action
  - Dry-run toggle
  - Confirm/Cancel buttons
  - Loading state
  - Success/Error state
- **Validation:** Manual flow test
- **Acceptance:** Confirmation required before any action
- **Rollback:** Auto-execute (not recommended)

#### 6.6 Execution History
- **Scope:** Track all executed actions
- **Files:** `src/models/execution_log.py`, `src/routes/executions.py`
- **Schema:**
  ```python
  class ExecutionLog(Base):
      id: UUID
      queue_item_id: UUID
      action_type: str
      status: str  # "success", "failed", "rolled_back"
      result: JSONB
      executed_at: datetime
      executed_by: UUID  # User ID
  ```
- **Validation:**
  ```python
  def test_execution_logged():
      executor.execute(item)
      logs = get_execution_logs(item_id=item.id)
      assert len(logs) == 1
  ```
- **Acceptance:** All executions logged with full context
- **Rollback:** Clear logs

#### 6.7 Rate Limiting (Extend Existing)
- **Scope:** Extend existing rate limiter to cover action execution
- **Files:** `src/rate_limiter.py` (EXTEND existing, don't create new file)
- **Changes:**
  ```python
  class RateLimiter:
      # Existing email rate limits...
      
      # Add action-type limits
      ACTION_LIMITS = {
          "send_email": 20,    # per hour
          "book_meeting": 10,  # per hour
          "create_task": 30,   # per hour
      }
      TOTAL_ACTIONS_PER_HOUR = 50
      
      async def check_can_execute(self, action_type: str) -> tuple[bool, str]:
          """Returns (allowed, reason_if_blocked)"""
  ```
- **Validation:**
  ```python
  def test_rate_limit():
      for i in range(25):
          result = executor.execute(email_item)
      assert result.error == "Rate limit exceeded: 20 emails per hour"
  ```
- **Acceptance:** Limits enforced, clear error message with limit info
- **Rollback:** Set limits to very high values

---

## Sprint 7: Closed-Loop Outcomes

**Demo:** Casey sees which actions led to responses. APS learns from outcomes.

### Tasks

#### 7.0 HubSpot Webhooks for Real-Time Outcomes (DO FIRST)
- **Scope:** Subscribe to HubSpot webhooks for instant outcome detection
- **Files:** `src/webhooks/hubspot_outcomes.py`, `src/routes/webhooks.py`
- **Events to Subscribe:**
  ```python
  HUBSPOT_WEBHOOK_EVENTS = [
      "email.replied",           # Immediate reply detection
      "deal.propertyChange",     # Deal stage movement (filter: dealstage)
      "meeting.completed",       # Meeting was held
      "contact.propertyChange",  # Contact activity
  ]
  ```
- **Webhook Handler:**
  ```python
  @router.post("/webhooks/hubspot")
  async def hubspot_webhook(request: Request):
      payload = await request.json()
      # Verify signature
      if not verify_hubspot_signature(request):
          raise HTTPException(401)
      
      # Process based on event type
      for event in payload:
          await process_outcome_event(event)
  ```
- **Validation:**
  ```python
  def test_webhook_reply_detection():
      payload = {"eventType": "email.replied", "objectId": "123", ...}
      response = client.post("/webhooks/hubspot", json=[payload])
      assert response.status_code == 200
      
      # Outcome created immediately
      outcome = get_outcome_by_email_id("123")
      assert outcome is not None
      assert outcome.detection_method == "webhook"
  ```
- **Acceptance:** Outcomes detected within seconds via webhook
- **Rollback:** Fall back to polling (Tasks 7.2-7.4)

#### 7.1 Outcome Data Model
- **Scope:** Track what happened after actions
- **Files:** `src/models/outcome.py`, migration
- **Schema:**
  ```python
  class Outcome(Base):
      id: UUID
      execution_id: UUID
      queue_item_id: UUID
      
      outcome_type: str  # "reply", "meeting_booked", "deal_advanced", "no_response"
      outcome_data: JSONB
      
      detected_at: datetime
      detection_method: str  # "webhook", "poll", "manual"
  ```
- **Validation:** Migration runs, can insert outcomes
- **Acceptance:** Outcomes linked to executions
- **Rollback:** Downgrade migration

#### 7.2 Outcome Detection - Email Replies (Polling Fallback)
- **Scope:** Polling fallback for when webhooks miss events
- **Files:** `src/outcomes/detectors/email_reply.py`
- **Logic:**
  1. Poll HubSpot for email activity (every 15 min)
  2. Match to sent emails
  3. Create outcome record if not already exists (idempotent)
- **Validation:**
  ```python
  def test_reply_detection():
      # After sending email, simulate reply
      outcomes = detect_email_replies(since=one_hour_ago)
      assert any(o.outcome_type == "reply" for o in outcomes)
  
  def test_polling_doesnt_duplicate_webhook():
      # Webhook already created outcome
      create_outcome(email_id="123", method="webhook")
      # Polling runs
      detect_email_replies()
      # Should NOT create duplicate
      outcomes = get_outcomes_by_email_id("123")
      assert len(outcomes) == 1
  ```
- **Acceptance:** Polling is backup, doesn't duplicate webhook outcomes
- **Rollback:** Disable detector

#### 7.3 Outcome Detection - Deal Movement (Polling Fallback)
- **Scope:** Polling fallback for deal stage changes
- **Files:** `src/outcomes/detectors/deal_stage.py`
- **Logic:** Compare deal stages to previous state, dedupe with webhooks
- **Validation:** Unit tests for stage transitions
- **Acceptance:** Stage changes linked to prior actions, no duplicates
- **Rollback:** Disable detector

#### 7.4 Outcome Detection - Meetings Held (Polling Fallback)
- **Scope:** Polling fallback for completed meetings
- **Files:** `src/outcomes/detectors/meeting.py`
- **Logic:** Check calendar for completed meetings, dedupe with webhooks
- **Validation:** Completed meetings detected
- **Acceptance:** Meeting outcomes recorded, no duplicates
- **Rollback:** Disable detector

#### 7.5 Outcome Feedback into APS
- **Scope:** Adjust APS based on what works
- **Files:** `src/aps/learner.py`
- **Logic:**
  ```python
  def update_weights_from_outcomes():
      # Actions that got replies -> boost similar actions
      # Actions with no response -> reduce similar actions
      # Patterns: time of day, action type, segment
  ```
- **Validation:**
  ```python
  def test_learning():
      # Record 10 successful email outcomes
      update_weights_from_outcomes()
      # New similar email should have higher APS
      new_score = calculate_aps(similar_email_item)
      assert new_score > original_score
  ```
- **Acceptance:** APS improves based on outcomes
- **Rollback:** Freeze weights

#### 7.6 Outcomes UI
- **Scope:** Show outcomes on queue items and execution history
- **Files:** `src/templates/outcomes.html`
- **Features:**
  - Outcome badge on completed items (✓ replied, ✗ no response)
  - Outcome timeline
  - Conversion metrics
- **Validation:** Manual - view outcomes in UI
- **Acceptance:** All outcomes visible with context
- **Rollback:** Hide outcomes

#### 7.7 Weekly Digest
- **Scope:** Email digest of weekly outcomes
- **Files:** `src/tasks/weekly_digest.py`, `src/templates/emails/digest.html`
- **Content:**
  - Actions taken: 45
  - Replies received: 12
  - Meetings booked: 5
  - Deals advanced: 3
  - Top performing action types
- **Validation:** Trigger digest manually, check email
- **Acceptance:** Digest arrives with accurate stats
- **Rollback:** Disable digest

---

## Validation Strategy

### Per-Task Validation
Every task has one of:
1. **Automated test** - pytest, runs in CI
2. **Curl command** - manual API validation
3. **Manual checklist** - for UI tasks

### Per-Sprint Validation
- **Demo script** - step-by-step to show sprint works
- **Regression tests** - previous sprint features still work
- **Production smoke test** - deploy and verify

### Acceptance Criteria Format
```
Given: [precondition]
When: [action]
Then: [expected result]
```

---

## File Touch Map

| Sprint | New Files | Modified Files |
|--------|-----------|----------------|
| 1 | `src/auth/*`, `src/templates/base.html`, `src/templates/dashboard.html` | `src/main.py` |
| 2 | `src/models/command_queue.py`, `src/routes/command_queue.py`, `src/templates/todays_moves.html` | `src/main.py` |
| 3 | `src/integrations/hubspot/*`, `src/signals/*`, `src/tasks/signal_ingest.py` | `src/routes/command_queue.py` |
| 4 | `src/voice/*`, `src/integrations/newsletter.py`, `src/integrations/youtube.py` | `src/models/voice_profile.py` |
| 5 | `src/aps/*` | `src/models/command_queue.py`, `src/routes/command_queue.py` |
| 6 | `src/actions/*`, `src/models/execution_log.py` | `src/routes/command_queue.py` |
| 7 | `src/outcomes/*`, `src/aps/learner.py`, `src/tasks/weekly_digest.py` | `src/aps/calculator.py` |

---

## Dependencies Between Sprints

```
Sprint 1 (Auth) 
    ↓
Sprint 2 (Queue) ←──────────────────┐
    ↓                               │
Sprint 3 (Signals) ─────────────────┤
    ↓                               │
Sprint 4 (Voice) ───────────────────┤
    ↓                               │
Sprint 5 (APS) ←────────────────────┤
    ↓                               │
Sprint 6 (Execution) ←──────────────┘
    ↓
Sprint 7 (Outcomes)
```

Each sprint builds on previous but can be tested independently with mocks.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| HubSpot API limits | Token bucket rate limiter (10 req/sec), cache with TTL, batch requests |
| Voice quality | Multiple training sources (emails + newsletters + YouTube), human review |
| APS accuracy | Start simple, iterate based on outcomes, DealOutcome model for learning |
| Execution errors | Default to DRAFT mode, confirmation required, dry-run toggle |
| Data loss | Execution logs, rollback handlers, migration backups |
| Missing training content | Content audit (Task 4.0) before coding, fallback to HubSpot emails only |
| OAuth scope issues | Request all scopes upfront (Task 1.1) to avoid re-consent |
| Duplicate queue items | Signal hash + ON CONFLICT DO NOTHING (Task 3.4) |
| Webhook reliability | Polling fallback (Tasks 7.2-7.4) for missed webhooks |

---

## Subagent Review Incorporated

This plan was reviewed by a subagent with the following improvements incorporated:

1. ✅ **Task 3.4 Idempotency** - Added signal_hash with unique constraint, ON CONFLICT DO NOTHING
2. ✅ **Task 3.1 Rate Limiting** - Added token bucket (10 req/sec) and response caching (Task 3.1b)
3. ✅ **Task 2.4 Seed Script** - Changed from idempotent to dev-only with production guard
4. ✅ **Task 4.0 Content Audit** - Added prerequisite task to verify training source access
5. ✅ **Task 5.0 Win/Loss Model** - Added DealOutcome model for APS learning
6. ✅ **Task 6.2 Email Handler** - Explicit draft vs send modes, default to DRAFT
7. ✅ **Task 6.7 Rate Limiting** - Extend existing rate_limiter.py, don't create new
8. ✅ **Task 7.0 Webhooks** - Added real-time webhook handling before polling fallback
9. ✅ **Task 1.1 OAuth Scopes** - Request Gmail + Calendar scopes upfront
10. ✅ **Migration Rollback Protocol** - Added worker shutdown + backup steps

---

## Quick Reference: Task Count by Sprint

| Sprint | Tasks | Focus |
|--------|-------|-------|
| **Sprint 1** | 6 tasks | Auth + Dashboard Shell |
| **Sprint 2** | 6 tasks | Command Queue Foundation |
| **Sprint 3** | 8 tasks | HubSpot Signal Ingestion |
| **Sprint 4** | 8 tasks | Voice Profile & Training |
| **Sprint 5** | 10 tasks | Action Priority Score (APS) |
| **Sprint 6** | 7 tasks | One-Click Execution |
| **Sprint 7** | 8 tasks | Closed-Loop Outcomes |
| **TOTAL** | **53 tasks** | Full CaseyOS |

---

## Definition of Done

For each task:
- [ ] Code committed (atomic, single purpose)
- [ ] Tests pass (or manual validation documented)
- [ ] PR reviewed (or self-reviewed with checklist)
- [ ] Deployed to staging
- [ ] Demo'd to Casey (or demo script written)

For each sprint:
- [ ] All tasks complete
- [ ] Sprint demo successful
- [ ] No regressions
- [ ] Deployed to production
- [ ] Docs updated
