# Changelog

All notable changes to CaseyOS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Slack Integration (Sprint 21)
- Route Cleanup (Sprint 23)
- Chrome Extension (Sprint 24)

---

## [2.0.0] - 2026-01-25 - "Henry Evolution Complete"

**Major Version:** CaseyOS is now a fully autonomous GTM command center with MCP integration, persistent memory, voice capabilities, and real action execution.

### Summary: Sprints 15-20 (Henry Evolution Phase)

This release transforms CaseyOS from a cloud API into an autonomous AI agent inspired by Alex Finn's "Henry" pattern. Key achievements:
- Persistent conversation memory with semantic search
- Proactive daemon monitoring with notifications
- Full voice capabilities (Whisper STT + OpenAI TTS)
- Local deployment ready (Docker Compose + CLI)
- Real action execution wired to Gmail/HubSpot/Calendar APIs
- MCP server integration with 8 tools for Claude Desktop

---

### Sprint 20: MCP Server Integration (2026-01-25)

**Goal:** Expose CaseyOS capabilities via Model Context Protocol for AI assistants like Claude Desktop

#### Added
- **MCP Server Implementation** (`src/mcp/`)
  - `server.py` - Full MCP protocol server with WebSocket + HTTP transports
  - `tools.py` - 8 MCP tools: read_command_queue, execute_action, search_contacts, create_email_draft, get_notifications, record_outcome, get_deal_pipeline, schedule_followup
  - `routes.py` - 5 API endpoints: `/mcp/info`, `/mcp/tools`, `/mcp/ws`, `/mcp/message`, `/mcp/tools/{name}`
- **Documentation**
  - [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md) - Complete MCP setup guide for Claude Desktop

#### Changed
- Registered MCP routes in `src/main.py`
- Added MCP tools to TRUTH.md

#### Technical Details
- **Protocol:** JSON-RPC 2.0 over WebSocket and HTTP
- **Transports:** Both WebSocket (`/mcp/ws`) and HTTP (`/mcp/message`) supported
- **Security:** Read-only by default for queue/notifications, actions require kill switch OFF
- **Integration:** Works with Claude Desktop via `@anthropics/mcp-remote`

#### Validation
```bash
# MCP server info
curl https://web-production-a6ccf.up.railway.app/mcp/info

# List available tools
curl https://web-production-a6ccf.up.railway.app/mcp/tools

# Execute tool directly
curl -X POST https://web-production-a6ccf.up.railway.app/mcp/tools/read_command_queue \
  -H "Content-Type: application/json" -d '{"limit": 5}'
```

**References:**
- [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md)
- [src/mcp/server.py](src/mcp/server.py)
- [src/mcp/tools.py](src/mcp/tools.py)

---

### Sprint 19: Action Executor Wiring (2026-01-25)

**Goal:** Wire all action executors to real APIs (Gmail, HubSpot, Calendar) instead of mock returns

#### Changed
- **ActionExecutor** (`src/actions/executor.py`)
  - `_execute_send_email()` - Now sends real emails via Gmail API with MIME, threading, rate limiting
  - `_execute_create_draft()` - Creates real Gmail drafts with voice profile
  - `_execute_create_task()` - Creates real HubSpot tasks with contact association
  - `_execute_complete_task()` - Completes HubSpot tasks via API
  - `_execute_book_meeting()` - Books real Calendar events with invites
  - `_execute_update_deal()` - Updates HubSpot deal stages via API

#### Added
- **Execution Telemetry**
  - Duration tracking for all API calls
  - Success/failure metrics
  - Rate limit tracking
- **Error Handling**
  - Graceful degradation on API failures
  - Detailed error messages with remediation hints
  - Automatic retry for transient failures

#### Fixed
- Mock implementations replaced with real API calls
- Idempotency enforcement on all actions
- Audit trail for all executions

#### Breaking Changes
- ⚠️ **Real API Calls:** Actions now perform real operations (emails sent, tasks created, meetings booked)
- ⚠️ **Rate Limits Enforced:** Gmail sends now respect 20/day, 2/week/contact limits
- ⚠️ **OAuth Required:** All actions require valid OAuth tokens for Gmail/Calendar

#### Validation
```bash
# Execute action with dry-run
curl -X POST https://web-production-a6ccf.up.railway.app/api/actions/execute \
  -H "Content-Type: application/json" \
  -d '{"queue_item_id":"test","dry_run":true}'

# Real execution (requires auth + kill switch OFF)
curl -X POST https://web-production-a6ccf.up.railway.app/api/actions/execute/{id}
```

**References:**
- [src/actions/executor.py](src/actions/executor.py)
- [TRUTH.md](TRUTH.md) - Action Execution section

---

### Sprint 18: Local Deployment (2026-01-24)

**Goal:** Enable CaseyOS to run locally like Alex Finn's "Henry" (Mac Mini, always-on)

#### Added
- **Docker Compose** (`docker-compose.yml`)
  - Full stack: API, Celery worker, Celery beat, PostgreSQL, Redis
  - Shared `.env.local` configuration
  - Service health checks
- **CLI Entrypoint** (`src/__main__.py`)
  - `python -m src run` - Start full local stack
  - `python -m src api` - Start API server only
  - `python -m src worker` - Start Celery worker
  - `python -m src beat` - Start Celery beat (daemon mode)
  - `python -m src shell` - Interactive Python shell with app context
  - `python -m src health` - Check system health
  - `python -m src migrate` - Run database migrations
- **Local Environment Template** (`.env.local.template`)
  - All required variables documented
  - Safe defaults for development
- **Makefile Targets**
  - `make local-up` - Start full stack
  - `make local-down` - Stop stack
  - `make local-logs` - Tail logs
  - `make local-shell` - Python shell
  - `make local-health` - Health check

#### Changed
- Celery worker and beat now run as separate Docker services
- Environment configuration unified via `.env.local`

#### Technical Details
- **Architecture:** API + Worker + Beat + PostgreSQL + Redis
- **Daemon Mode:** Celery beat runs continuously for monitoring
- **Hot Reload:** uvicorn auto-reload on code changes
- **Database:** PostgreSQL 15 with persistent volume

#### Validation
```bash
# Start local stack
make local-up

# Check health
make local-health

# View logs
make local-logs
```

**References:**
- [docker-compose.yml](docker-compose.yml)
- [src/__main__.py](src/__main__.py)
- [Makefile](Makefile)
- [docs/CASEYOS_HENRY_EVOLUTION.md](docs/CASEYOS_HENRY_EVOLUTION.md)

---

### Sprint 17: Voice Capabilities (2026-01-24)

**Goal:** Add voice input/output for hands-free CaseyOS interaction

#### Added
- **VoiceService** (`src/services/voice_service.py`)
  - `transcribe()` - Audio → text via OpenAI Whisper API
  - `speak()` - Text → audio via OpenAI TTS API
  - `speak_streaming()` - Streaming TTS for real-time playback
  - Wake word detection: "Hey Jarvis", "Jarvis", "Hey Casey", "Casey"
  - 6 voice options: alloy, echo, fable, onyx, nova (default), shimmer
- **Voice API Endpoints** (`src/routes/jarvis_api.py`)
  - `POST /api/jarvis/voice/transcribe-file` - Upload audio file → get transcription
  - `POST /api/jarvis/voice/speak` - Text → get base64 MP3 audio
  - `POST /api/jarvis/voice/conversation` - Full voice loop (audio in → Jarvis response → audio out)
  - `GET /api/jarvis/voice/voices` - List available TTS voices

#### Changed
- **Jarvis Integration**
  - Voice conversations wired to Jarvis with persistent memory
  - Wake word detection strips trigger words before processing
  - Response synthesized with configurable voice profile

#### Technical Details
- **Speech-to-Text:** OpenAI Whisper API
- **Text-to-Speech:** OpenAI TTS API
- **Supported Formats:** MP3, WAV, M4A, WebM
- **Wake Words:** Case-insensitive detection
- **Streaming:** Chunked transfer for real-time playback

#### Validation
```bash
# Transcribe audio file
curl -X POST https://web-production-a6ccf.up.railway.app/api/jarvis/voice/transcribe-file \
  -F "file=@recording.mp3"

# Generate speech
curl -X POST https://web-production-a6ccf.up.railway.app/api/jarvis/voice/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from Jarvis","voice":"nova"}'
```

**References:**
- [src/services/voice_service.py](src/services/voice_service.py)
- [src/routes/jarvis_api.py](src/routes/jarvis_api.py)
- [docs/CASEYOS_HENRY_EVOLUTION.md](docs/CASEYOS_HENRY_EVOLUTION.md)

---

### Sprint 16: Proactive Daemon (2026-01-24)

**Goal:** Background monitoring that surfaces insights without user prompting

#### Added
- **Background Monitor Service** (`src/tasks/monitor_signals.py`)
  - `check_all_signals()` - Celery task running every 5 minutes
  - Monitors: HubSpot signals, Gmail signals, queue health, system health
  - Creates proactive notifications via NotificationService
- **Notification System**
  - **Model:** `JarvisNotification` (`src/models/notification.py`)
  - **Service:** `NotificationService` (`src/services/notification_service.py`)
  - Priority levels: urgent, high, normal, low
  - State tracking: unread, read, acknowledged, actioned
- **Proactive API Endpoints** (`src/routes/jarvis_api.py`)
  - `GET /api/jarvis/whats-up` - Morning briefing with pending notifications
  - `GET /api/jarvis/notifications` - List all notifications (filterable)
  - `GET /api/jarvis/notifications/{id}` - Get specific notification
  - `POST /api/jarvis/notifications/{id}/read` - Mark as read
  - `POST /api/jarvis/notifications/{id}/acknowledge` - Acknowledge
  - `POST /api/jarvis/notifications/{id}/action` - Mark as actioned
- **Database Migration** (`infra/migrations/versions/20260125_notifications.py`)
  - Table: `jarvis_notifications` with priority + state indexes

#### Changed
- **Celery Beat Schedule** (`src/celery_app.py`)
  - Added `daemon-monitor-signals` task running every 5 minutes

#### Technical Details
- **Monitoring Frequency:** Every 5 minutes
- **Notification Types:** signal_spike, queue_health, system_health, custom
- **Priority Scoring:** Automatic based on signal type and context
- **Expiry:** 4-minute task expiry to prevent overlaps

#### Validation
```bash
# Get morning briefing
curl https://web-production-a6ccf.up.railway.app/api/jarvis/whats-up

# List notifications
curl https://web-production-a6ccf.up.railway.app/api/jarvis/notifications
```

**References:**
- [src/tasks/monitor_signals.py](src/tasks/monitor_signals.py)
- [src/services/notification_service.py](src/services/notification_service.py)
- [src/models/notification.py](src/models/notification.py)

---

### Sprint 15: Persistent Memory (2026-01-24)

**Goal:** Jarvis remembers conversations across sessions with semantic search

#### Added
- **Memory Models** (`src/models/memory.py`)
  - `JarvisSession` - Persistent sessions with active context window
  - `ConversationMemory` - Individual messages with vector embeddings
  - `MemorySummary` - Compressed summaries of old conversations
- **MemoryService** (`src/services/memory_service.py` - 557 lines)
  - `remember()` - Store messages with OpenAI embeddings
  - `recall()` - Get recent conversation history
  - `search_similar()` - Semantic search for relevant context
  - `summarize_old_messages()` - Compress old conversations (>100 messages)
  - `forget()` - GDPR-compliant deletion
- **Memory API** (`src/routes/memory.py`)
  - `GET /api/jarvis/sessions` - List user sessions
  - `GET /api/jarvis/memory/{session_id}` - Get session memory
  - `POST /api/jarvis/memory/search` - Semantic search across sessions
  - `POST /api/jarvis/remember` - Manually add memory
  - `DELETE /api/jarvis/memory/{session_id}` - GDPR deletion
  - `POST /api/jarvis/sessions/create` - Create new session
  - `GET /api/jarvis/memory/stats` - Memory usage statistics
- **Database Migration** (`infra/migrations/versions/20260125_persistent_memory.py`)
  - Tables: `jarvis_sessions`, `conversation_memory`, `memory_summaries`
  - Indexes: user_id, session_id, is_active, created_at

#### Changed
- **Jarvis Integration** (`src/agents/jarvis.py`)
  - Jarvis now uses MemoryService for persistent context
  - User queries stored with embeddings
  - Responses summarized and saved
  - Semantic search retrieves relevant historical context
  - New parameters: `user_id`, `session_name` for session management

#### Technical Details
- **Embeddings:** OpenAI `text-embedding-3-small` (1536 dimensions)
- **Context Window:** Last 50 messages per session
- **Compression:** Automatic summarization after 100 messages
- **Search:** Cosine similarity with configurable threshold
- **Storage:** PostgreSQL with vector support (pgvector planned)

#### Breaking Changes
- ⚠️ **Jarvis Interface Changed:** `ask()` method now requires `user_id` parameter
- ⚠️ **Session Management:** Sessions must be explicitly created/managed

#### Validation
```bash
# Create session
curl -X POST https://web-production-a6ccf.up.railway.app/api/jarvis/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"user_id":"casey","session_name":"Morning Planning"}'

# Search memory
curl -X POST https://web-production-a6ccf.up.railway.app/api/jarvis/memory/search \
  -H "Content-Type: application/json" \
  -d '{"user_id":"casey","query":"pipeline health"}'

# Get stats
curl https://web-production-a6ccf.up.railway.app/api/jarvis/memory/stats?user_id=casey
```

**References:**
- [src/services/memory_service.py](src/services/memory_service.py)
- [src/models/memory.py](src/models/memory.py)
- [src/routes/memory.py](src/routes/memory.py)
- [docs/CASEYOS_HENRY_EVOLUTION.md](docs/CASEYOS_HENRY_EVOLUTION.md)

---

## [1.5.0] - 2026-01-24 - "GTM Command Center"

### Summary: Sprints 11-14 (Expansion Phase)

This release expands CaseyOS beyond sales automation into a full GTM command center covering Sales, Marketing, and Customer Success domains.

---

### Sprint 13: Twitter/X + Grok Integration (2026-01-24)

**Goal:** Social intelligence and xAI Grok integration for Twitter monitoring

#### Added
- **Twitter Connector** (`src/connectors/twitter.py`)
  - OAuth 2.0 authentication
  - Personal feed fetching
  - Tweet search and filtering
  - Profile lookup
- **Grok Connector** (`src/connectors/grok.py`)
  - xAI API integration
  - Twitter-aware prompting
  - Competitive intelligence analysis
- **Social Signal Processor** (`src/signals/social_processor.py`)
  - Twitter activity → command queue items
  - Engagement tracking
  - Mention detection
- **Twitter API Routes** (`src/routes/twitter.py`)
  - `GET /api/twitter/feed` - Personal feed
  - `GET /api/twitter/search` - Search tweets
  - `POST /api/twitter/analyze` - Grok analysis

#### Changed
- Extended ActionType enum with social actions
- Added social domain to command queue

#### Technical Details
- **Twitter API:** OAuth 2.0 with PKCE
- **xAI Grok:** API key authentication
- **Rate Limits:** Twitter API v2 limits enforced

#### Documentation
- [docs/TWITTER_GROK_SETUP.md](docs/TWITTER_GROK_SETUP.md)

**References:**
- [src/connectors/twitter.py](src/connectors/twitter.py)
- [src/connectors/grok.py](src/connectors/grok.py)
- [SPRINT_13_EXECUTION.md](SPRINT_13_EXECUTION.md)

---

### Sprint 11-12: CaseyOS Dashboard + GTM Domains (2026-01-24)

**Goal:** Transform sales-agent UI into unified GTM command center

#### Added
- **CaseyOS Dashboard** (`src/static/caseyos/`)
  - `index.html` - Main dashboard UI
  - `styles.css` - Complete design system with dark mode
  - `script.js` - Interactive command queue with keyboard shortcuts
- **Domain Field** (`src/models/command_queue.py`)
  - Added `domain` column: sales, marketing, cs
  - Domain-based filtering in API
- **GTM Action Types**
  - Marketing: `content_repurpose`, `social_post`, `email_campaign`
  - Customer Success: `client_check_in`, `risk_alert`, `deliverable_update`
- **Domain Agents** (`src/agents/`)
  - **Content:** ContentRepurposeAgent, SocialSchedulerAgent, GraphicsRequestAgent
  - **Fulfillment:** DeliverableTrackerAgent, ApprovalGatewayAgent, ClientHealthAgent
  - **Contracts:** ProposalGeneratorAgent, ContractReviewAgent, PricingCalculatorAgent
  - **Ops:** CompetitorWatchAgent, RevenueOpsAgent, PartnerCoordinatorAgent

#### Changed
- **Command Queue API** (`src/routes/command_queue.py`)
  - Added `?domain=sales|marketing|cs` filter parameter
  - Default: returns all domains
- **Database Migration** (`infra/migrations/versions/20260124_070237_add_domain_to_command_queue.py`)
  - Added `domain` VARCHAR(20) column to `command_queue_items`
  - Default: 'sales'

#### UI Features
- Dark mode toggle (persisted to localStorage)
- Domain tabs: All | Sales | Marketing | CS
- Real-time stats: pending, completed, reply rate, net impact
- Execute/Dismiss actions with modal confirmation
- Keyboard shortcuts: `r` (refresh), `d` (dark mode), `1-4` (domain tabs)
- Responsive design (desktop-first, mobile breakpoints)

#### Breaking Changes
- ⚠️ **URL Changed:** Main dashboard moved from `/` to `/caseyos`
- ⚠️ **API Response:** Command queue items now include `domain` field

#### Validation
```bash
# CaseyOS dashboard
open https://web-production-a6ccf.up.railway.app/caseyos

# Sales domain only
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=sales

# Marketing domain
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=marketing
```

**References:**
- [docs/SPRINT_11_12_COMPLETE.md](docs/SPRINT_11_12_COMPLETE.md)
- [src/static/caseyos/](src/static/caseyos/)
- [src/models/command_queue.py](src/models/command_queue.py)

---

## [1.0.0] - 2026-01-24 - "Core Platform Complete"

### Summary: Sprints 7-10 (Core Platform Phase)

This release establishes the core CaseyOS platform with command queue, signal ingestion, APS scoring, action execution, and closed-loop outcome tracking.

---

### Sprint 10: Closed-Loop Outcomes (2026-01-24)

**Goal:** Track outcomes (replies, meetings booked, deals advanced) and feed back into APS scoring

#### Added
- **Outcome Models** (`src/models/outcome.py`)
  - `OutcomeRecord` - Stores tracked outcomes with impact scores
  - 18 outcome types: email_replied, meeting_booked, deal_stage_advanced, etc.
  - Impact scores: -5 (negative) to +10 (very positive)
- **Outcome Service** (`src/services/outcome_service.py`)
  - `record_outcome()` - Store outcome with automatic impact scoring
  - `get_outcomes_for_contact()` - Contact outcome history
  - `calculate_aps_adjustment()` - APS boost/penalty based on outcomes
  - Auto-detection: Gmail replies, HubSpot deal changes, Calendar meetings
- **Outcome API** (`src/routes/outcomes.py`)
  - `GET /api/outcomes/types` - List outcome types
  - `GET /api/outcomes/stats` - Aggregate statistics
  - `GET /api/outcomes/recent` - Recent outcomes
  - `POST /api/outcomes/record` - Manually record outcome
  - `GET /api/outcomes/contact/{email}` - Contact outcomes
  - `GET /api/outcomes/contact/{email}/score-adjustment` - APS adjustment
  - `POST /api/outcomes/detect/*` - Auto-detection endpoints

#### Changed
- **APS Calculator** (`src/services/aps_calculator.py`)
  - Now factors in historical outcomes via `outcome_adjustment` parameter
  - Contacts with positive outcomes get +5 to +20 APS boost
  - Contacts with negative outcomes get -5 to -20 APS penalty

#### Technical Details
- **Outcome Categories:** email, meeting, deal, task, general
- **Impact Scoring:** Automatic based on outcome type
- **APS Adjustment Range:** -20 to +20 points
- **Detection:** Automatic via webhooks + polling

#### Validation
```bash
# Get outcome types
curl https://web-production-a6ccf.up.railway.app/api/outcomes/types

# Record outcome
curl -X POST https://web-production-a6ccf.up.railway.app/api/outcomes/record \
  -H "Content-Type: application/json" \
  -d '{"outcome_type":"email_replied","source":"gmail","contact_email":"john@acme.com"}'

# Get stats
curl https://web-production-a6ccf.up.railway.app/api/outcomes/stats
```

**References:**
- [src/services/outcome_service.py](src/services/outcome_service.py)
- [src/models/outcome.py](src/models/outcome.py)
- [API_ENDPOINTS.md](API_ENDPOINTS.md) - Outcomes section

---

### Sprint 9: Execution with Guardrails (2026-01-24)

**Goal:** One-click execution of Today's Moves with full safety guardrails

#### Added
- **Action Executor** (`src/actions/executor.py`)
  - Core execution engine with kill switch, rate limiting, dry-run mode
  - Idempotency tracking to prevent duplicate actions
  - Rollback support for undoable actions
  - Audit trail integration
  - Telemetry emission
- **Action API** (`src/routes/actions.py`)
  - `POST /api/actions/execute` - Execute action with full payload
  - `POST /api/actions/execute/{id}` - Quick execute by queue item ID
  - `POST /api/actions/rollback` - Rollback previous action
  - `GET /api/actions/types` - List available action types
  - `GET /api/actions/history` - Execution history
  - `GET /api/actions/status` - Executor status (kill switch, rate limits)
  - `DELETE /api/actions/history/clear` - Clear history (admin)
- **Action Types** (`src/actions/contracts.py`)
  - 9 action types: send_email, create_draft, book_meeting, create_task, complete_task, follow_up, check_in, update_deal_stage, custom
- **UI Execution** (`src/static/command-queue.html`)
  - Execute button with confirmation modal
  - Preview button for dry-run mode
  - Loading states and error handling

#### Safety Guardrails
1. **Kill Switch** - Global disable via feature flags
2. **Rate Limiting** - 2/week per contact, 20/day total
3. **Dry-Run Mode** - Preview before execution
4. **Idempotency** - Duplicate prevention via action tracking
5. **Audit Trail** - All executions logged
6. **Rollback** - Undo support for reversible actions

#### Technical Details
- **Execution Modes:** dry-run, execute, rollback
- **Result Types:** success, dry_run, error, blocked, rate_limited
- **Idempotency Keys:** `{queue_item_id}:{action_type}`
- **Rollback Tokens:** Stored for undo operations

#### Breaking Changes
- ⚠️ **Draft-Only Mode Enforced:** Real email sends require `ALLOW_REAL_SENDS=true` (defaults to false)

#### Validation
```bash
# Dry-run execution
curl -X POST https://web-production-a6ccf.up.railway.app/api/actions/execute \
  -H "Content-Type: application/json" \
  -d '{"queue_item_id":"test","dry_run":true}'

# Check executor status
curl https://web-production-a6ccf.up.railway.app/api/actions/status
```

**References:**
- [SPRINT_9_COMPLETE.md](SPRINT_9_COMPLETE.md)
- [src/actions/executor.py](src/actions/executor.py)
- [src/actions/contracts.py](src/actions/contracts.py)

---

### Sprint 8: Signal Framework & APS Scoring (2026-01-24)

**Goal:** Proactive signal ingestion from HubSpot/Gmail and Action Priority Score calculation

#### Added
- **Signal Framework** (`src/models/signal.py`, `src/services/signal_to_recommendation.py`)
  - Signal model with deduplication via `payload_hash`
  - Signal sources: form, hubspot, gmail, manual
  - Signal-to-recommendation mapping with urgency/revenue context
- **APS Calculator** (`src/services/aps_calculator.py`)
  - Revenue Impact: 40% weight
  - Urgency: 30% weight
  - Strategic Value: 20% weight
  - Effort (inverted): 10% weight
  - Score range: 0-100
- **Signal Polling** (`src/tasks/signal_polling.py`)
  - `poll_hubspot_signals()` - Every 5 minutes
  - `poll_gmail_signals()` - Every 5 minutes
  - `process_unprocessed_signals()` - Every 10 minutes
- **Signals API** (`src/routes/signals.py`)
  - `GET /api/signals/health` - Health check
  - `GET /api/signals` - List signals with filtering
  - `POST /api/hubspot/signals/refresh` - Manual refresh (admin)
- **Database Migration** (`infra/migrations/versions/20260124_signals.py`)
  - Table: `signals` with payload_hash index for deduplication

#### Changed
- **Command Queue** - Items now include `aps_score` and `reasoning`
- **Celery Beat** - Added signal polling tasks to schedule

#### Technical Details
- **APS Formula:** `0.4*revenue + 0.3*urgency + 0.2*strategic + 0.1*(1-effort)`
- **Deduplication:** SHA-256 hash of JSON payload
- **Signal Processing:** Async via Celery tasks
- **Polling Frequency:** 5-10 minutes (configurable)

#### Validation
```bash
# Check signal health
curl https://web-production-a6ccf.up.railway.app/api/signals/health

# List signals
curl https://web-production-a6ccf.up.railway.app/api/signals?limit=10

# Today's Moves with APS scores
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today
```

**References:**
- [SPRINT_8_COMPLETE.md](SPRINT_8_COMPLETE.md)
- [src/services/aps_calculator.py](src/services/aps_calculator.py)
- [src/services/signal_to_recommendation.py](src/services/signal_to_recommendation.py)
- [docs/SIGNALS.md](docs/SIGNALS.md)

---

### Sprint 7: Command Queue Foundation (2026-01-24)

**Goal:** Stabilize production and build command queue MVP

#### Added
- **Command Queue Model** (`src/models/command_queue.py`)
  - `CommandQueueItem` - Priority queue with APS scoring
  - Status: pending, in_progress, completed, skipped, snoozed
  - Relationships: linked to workflow, signal, outcome
- **Command Queue API** (`src/routes/command_queue.py`)
  - `GET /api/command-queue/` - List items
  - `GET /api/command-queue/today` - Today's Moves (prioritized)
  - `POST /api/command-queue/` - Create item
  - `POST /api/command-queue/{id}/complete` - Mark complete
  - `POST /api/command-queue/{id}/skip` - Skip item
  - `POST /api/command-queue/{id}/snooze` - Snooze item
- **Command Queue UI** (`src/static/command-queue.html`)
  - Display Today's Moves
  - Priority badges (color-coded by APS score)
  - Accept/Dismiss buttons
- **Telemetry System** (`src/telemetry.py`)
  - Structured event logging
  - `log_recommendation_accepted()`, `log_action_executed()` helpers
  - `@track_event` decorator with duration tracking
- **Database Migration** (`infra/migrations/versions/20260123_command_queue.py`)
  - Table: `command_queue_items` with priority + status indexes

#### Changed
- **Health Endpoints** (`src/routes/health.py`)
  - `/health` - Basic health check
  - `/healthz` - Kubernetes liveness
  - `/ready` - Readiness check (DB + Redis)

#### Fixed
- **Production 502 Errors** - Renamed `src/auth.py` → `src/oauth_manager_legacy.py` to resolve namespace collision

#### Documentation
- [docs/ADMIN_PASSWORD_ROTATION.md](docs/ADMIN_PASSWORD_ROTATION.md) - NEW
- [docs/SENTRY_SETUP.md](docs/SENTRY_SETUP.md) - NEW
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - Enhanced
- [.github/prompts/](..github/prompts/) - 8 new prompt files

#### Validation
```bash
# Health check
curl https://web-production-a6ccf.up.railway.app/health

# Readiness check
curl https://web-production-a6ccf.up.railway.app/ready

# Today's Moves
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today
```

**References:**
- [SPRINT_7_COMPLETE.md](SPRINT_7_COMPLETE.md)
- [src/models/command_queue.py](src/models/command_queue.py)
- [src/routes/command_queue.py](src/routes/command_queue.py)

---

## [0.6.0] - 2026-01-23 - "Production Hardening"

### Summary: Sprint 6 (Security & Monitoring)

This release hardens the platform for production with security features, monitoring, and GDPR compliance.

---

### Sprint 6: Production Hardening (2026-01-23)

**Goal:** Production-ready security, monitoring, and compliance

#### Added
- **Security Features** (`src/security/`)
  - CSRF protection middleware with token generation/validation
  - Admin authentication via `X-Admin-Token` header
  - Security headers: X-Frame-Options, X-Content-Type-Options, etc.
  - Rate limiting: 11 requests/60s on auth endpoints
- **GDPR Compliance** (`src/gdpr.py`, `src/routes/gdpr.py`)
  - User data deletion endpoint
  - Draft cleanup task (90-day retention)
  - Audit logging (1-year retention)
  - Data export capability
- **Monitoring** (`src/sentry_integration.py`)
  - Sentry error tracking integration
  - Environment tagging (production/staging)
  - Custom error context
- **Circuit Breakers** (`src/circuit_breaker.py`)
  - Gmail, HubSpot, Calendar circuit breakers
  - Failure threshold: 5 consecutive failures
  - Recovery timeout: 60 seconds
  - Status monitoring endpoint
- **GDPR API** (`src/routes/gdpr.py`)
  - `DELETE /api/gdpr/user/{email}` - User deletion
  - `GET /api/gdpr/status` - Compliance status
- **Circuit Breaker API** (`src/routes/circuit_breakers.py`)
  - `GET /api/circuit-breakers/status` - Circuit breaker monitoring
- **Celery Retention Task** (`src/tasks/retention.py`)
  - `cleanup_old_drafts()` - Runs daily at 2 AM
  - Deletes drafts older than 90 days

#### Changed
- **Middleware** (`src/middleware.py`)
  - Added CSRF middleware
  - Added security headers middleware
- **Celery Beat Schedule** (`src/celery_app.py`)
  - Added draft cleanup task to daily schedule

#### Security
- **Admin Password:** Rotated to strong random value (32 chars)
- **CSRF Tokens:** Required on all state-changing endpoints
- **Rate Limiting:** Enforced on sensitive endpoints
- **Audit Trail:** All admin actions logged

#### Breaking Changes
- ⚠️ **CSRF Required:** All POST/PUT/DELETE endpoints require `X-CSRF-Token` header
- ⚠️ **Admin Auth:** Admin endpoints require `X-Admin-Token` header
- ⚠️ **Rate Limits:** 11 req/60s on `/auth/*` endpoints

#### Validation
```bash
# CSRF token flow
CSRF=$(curl -sD- https://web-production-a6ccf.up.railway.app/health | grep X-CSRF-Token | cut -d' ' -f2)

# Admin action with CSRF
curl -X POST https://web-production-a6ccf.up.railway.app/api/admin/flags/test/toggle \
  -H "X-Admin-Token: $ADMIN_PASSWORD" \
  -H "X-CSRF-Token: $CSRF"

# Circuit breaker status
curl https://web-production-a6ccf.up.railway.app/api/circuit-breakers/status

# GDPR status
curl https://web-production-a6ccf.up.railway.app/api/gdpr/status
```

**References:**
- [LIVE_DEPLOYMENT_INFO.md](LIVE_DEPLOYMENT_INFO.md)
- [docs/SECURITY_AUDIT.md](docs/SECURITY_AUDIT.md)
- [docs/ADMIN_PASSWORD_ROTATION.md](docs/ADMIN_PASSWORD_ROTATION.md)
- [docs/SENTRY_SETUP.md](docs/SENTRY_SETUP.md)

---

## [0.4.0] - 2026-01-23 - "Auto-Approval Rules"

### Summary: Sprint 4

This release adds an intelligent auto-approval rules engine for draft emails.

---

### Sprint 4: Auto-Approval Rules Engine (2026-01-23)

**Goal:** Automated draft approval based on configurable rules

#### Added
- **Auto-Approval Models** (`src/models/auto_approval.py`)
  - `AutoApprovalRule` - Configurable approval rules with priority
  - Rule types: icp_match, approved_recipient, reply_history, domain_match, low_risk_action
  - Conditions stored as JSONB for flexibility
- **Auto-Approval Service** (`src/auto_approval.py`)
  - `evaluate_draft()` - Evaluates draft against all enabled rules
  - Priority-based rule ordering
  - Detailed reason tracking
- **Auto-Approval API** (`src/routes/auto_approval.py`)
  - `GET /api/auto-approval/rules` - List rules
  - `POST /api/auto-approval/rules` - Create rule
  - `PUT /api/auto-approval/rules/{id}` - Update rule
  - `DELETE /api/auto-approval/rules/{id}` - Delete rule
  - `POST /api/auto-approval/rules/{id}/enable` - Enable rule
  - `POST /api/auto-approval/rules/{id}/disable` - Disable rule
  - `POST /api/auto-approval/evaluate` - Evaluate draft
- **Database Migration** (`infra/migrations/versions/20260125_auto_approval.py`)
  - Table: `auto_approval_rules` with priority index

#### Changed
- **Operator Mode** (`src/operator_mode.py`)
  - Integrated auto-approval checks before manual review
  - Auto-approved drafts skip manual queue

#### Technical Details
- **Rule Evaluation:** Priority-ordered (highest first)
- **Conditions:** JSON-based with flexible matching
- **Approval:** First matching rule determines outcome
- **Audit:** All auto-approvals logged

#### Validation
```bash
# List rules
curl https://web-production-a6ccf.up.railway.app/api/auto-approval/rules

# Evaluate draft
curl -X POST https://web-production-a6ccf.up.railway.app/api/auto-approval/evaluate \
  -H "Content-Type: application/json" \
  -d '{"draft_id":"123","recipient":"john@acme.com"}'
```

**References:**
- [archive/old_docs/SPRINT_4_IMPLEMENTATION_COMPLETE.md](archive/old_docs/SPRINT_4_IMPLEMENTATION_COMPLETE.md)
- [src/auto_approval.py](src/auto_approval.py)
- [src/models/auto_approval.py](src/models/auto_approval.py)

---

## [0.2.0] - 2026-01-23 - "Async Processing"

### Summary: Sprint 2

This release adds background task processing via Celery and webhook support.

---

### Sprint 2: Async Task Processing (2026-01-23)

**Goal:** Background processing for long-running tasks and webhook integration

#### Added
- **Celery Integration** (`src/celery_app.py`)
  - Celery app configuration with Redis broker
  - Task routing and result backend
  - Beat scheduler for periodic tasks
- **Formlead Task** (`src/tasks/formlead_task.py`)
  - `process_formlead_async()` - Async form processing
  - Workflow tracking integration
- **Webhook Handler** (`src/routes/webhooks.py`)
  - `POST /api/webhooks/hubspot` - HubSpot form submission webhook
  - HMAC-SHA256 signature validation
  - Automatic workflow creation
- **Celery Beat Schedule** (`src/celery_app.py`)
  - Configured for periodic task scheduling

#### Changed
- **Dependencies** (`requirements.txt`)
  - Added celery, redis, flower

#### Technical Details
- **Broker:** Redis
- **Result Backend:** Redis
- **Task Routing:** Default queue
- **Serialization:** JSON

#### Validation
```bash
# Webhook test
curl -X POST https://web-production-a6ccf.up.railway.app/api/webhooks/hubspot \
  -H "Content-Type: application/json" \
  -d '{"submittedAt":1234567890,"email":"test@example.com"}'
```

**References:**
- [archive/old_docs/SPRINT_2_IMPLEMENTATION_COMPLETE.md](archive/old_docs/SPRINT_2_IMPLEMENTATION_COMPLETE.md)
- [src/celery_app.py](src/celery_app.py)
- [src/tasks/formlead_task.py](src/tasks/formlead_task.py)

---

## [0.1.0] - 2026-01-23 - "Email Send Capability"

### Summary: Sprint 1

This release implements email sending with MIME formatting, threading, and safety guardrails.

---

### Sprint 1: Email Send Capability (2026-01-23)

**Goal:** Send emails via Gmail API with full safety features

#### Added
- **Email Sender** (`src/connectors/gmail.py`)
  - MIME message creation with HTML + plain text
  - Email threading support (In-Reply-To, References headers)
  - Automatic retries on transient failures
  - Rate limiting integration
- **Feature Flags** (`src/config.py`)
  - `ALLOW_REAL_SENDS` - Enable/disable real email sends (default: false)
  - `MODE_DRAFT_ONLY` - Force draft-only mode
- **Draft Status Tracking** (`src/db/workflow_db.py`)
  - `record_draft_send()` - Persists send metadata
  - Status tracking: draft → sent
  - Message ID and thread ID storage
- **Rate Limiter** (`src/rate_limiter.py`)
  - Daily limit: 20 emails/day
  - Weekly limit: 2 emails/week per contact
  - Token bucket algorithm
- **Send API** (`src/operator_mode.py`)
  - `send_draft()` - Send approved draft
  - Feature flag checks
  - Rate limit enforcement
  - Safety checks integration

#### Safety Guardrails
1. **Feature Flag:** `ALLOW_REAL_SENDS` must be true
2. **Rate Limiting:** 2/week per contact, 20/day total
3. **Safety Checks:** PII detection, tone validation
4. **Audit Trail:** All sends logged
5. **Draft Status:** Tracked in database

#### Breaking Changes
- ⚠️ **Sends Disabled by Default:** `ALLOW_REAL_SENDS=false` by default

#### Validation
```bash
# Check send status
curl https://web-production-a6ccf.up.railway.app/api/operator/status

# Send draft (requires auth + flags)
curl -X POST https://web-production-a6ccf.up.railway.app/api/drafts/{id}/send \
  -H "X-Admin-Token: $ADMIN_PASSWORD"
```

**References:**
- [archive/old_docs/SPRINT_1_IMPLEMENTATION_COMPLETE.md](archive/old_docs/SPRINT_1_IMPLEMENTATION_COMPLETE.md)
- [src/connectors/gmail.py](src/connectors/gmail.py)
- [src/operator_mode.py](src/operator_mode.py)

---

## [0.0.1] - 2025-01-25 - "Foundation"

### Summary: Sprint 0

Initial foundation cleanup and infrastructure setup.

---

### Sprint 0: Foundation Cleanup (2025-01-25)

**Goal:** Clean codebase and establish documentation hierarchy

#### Added
- **TRUTH.md** - Single source of truth for system state
- **Archive Structure** (`archive/`)
  - 8 organized subdirectories for historical docs
  - 59 files archived from root
- **Test Infrastructure** (`pytest.ini`)
  - pytest-asyncio configuration
  - Async test support

#### Changed
- **Documentation Cleanup**
  - Reduced root docs from 64 → 6 files (90% reduction)
  - Organized by category: phases, builds, sprints, campaigns, guides, status, reference
- **Test Suite**
  - 83% passing (164/197 tests)
  - No new regressions

#### Fixed
- Removed stub routes (0 NotImplementedError)
- Removed skipped tests (0 @pytest.mark.skip)

#### Removed
- 59 conflicting/outdated documentation files (archived, not deleted)

#### Validation
```bash
# No stub routes
grep -r "NotImplementedError" src/ | wc -l
# Returns: 0

# Tests passing
pytest
# 164 passed, 17 failed, 16 errors
```

**References:**
- [archive/old_docs/SPRINT_0_COMPLETE.md](archive/old_docs/SPRINT_0_COMPLETE.md)
- [TRUTH.md](TRUTH.md)

---

## Migration Guide

### From 1.x to 2.0 (Henry Evolution)

**Breaking Changes:**
1. **Jarvis Interface:** `ask()` method now requires `user_id` parameter
2. **Action Execution:** All actions now perform real API calls (use dry-run mode for testing)
3. **OAuth Required:** Gmail, Calendar, and HubSpot OAuth tokens required for action execution

**Migration Steps:**
1. Update Jarvis calls to include `user_id`:
   ```python
   # Before
   result = await jarvis.ask("What's my top priority?")
   
   # After
   result = await jarvis.ask("What's my top priority?", user_id="casey")
   ```

2. Enable persistent memory (optional):
   ```python
   # Create session
   session = await memory_service.create_session(user_id="casey", session_name="Daily Planning")
   
   # Use with Jarvis
   result = await jarvis.ask(query, user_id="casey", session_name="Daily Planning")
   ```

3. Configure MCP for Claude Desktop (optional):
   - See [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md)

4. Set up local deployment (optional):
   ```bash
   # Copy template
   cp .env.local.template .env.local
   
   # Edit with your credentials
   vim .env.local
   
   # Start stack
   make local-up
   ```

---

## Links

- **Production:** https://web-production-a6ccf.up.railway.app
- **Repository:** https://github.com/casey-larkin/sales-agent
- **Documentation:** [docs/](docs/)
- **API Reference:** [API_ENDPOINTS.md](API_ENDPOINTS.md)

---

**Versioning Scheme:** MAJOR.MINOR.PATCH
- **MAJOR:** Breaking changes, architecture shifts
- **MINOR:** New features, backward-compatible
- **PATCH:** Bug fixes, documentation

