# CaseyOS "Henry" Evolution Roadmap

**Date:** January 25, 2026  
**Inspired By:** Alex Finn's "Henry" AI Agent (Mac Mini + Claude, always-on, voice-first)  
**Goal:** Transform CaseyOS from cloud API to autonomous local agent

**Status:** Sprint 18 (Local Deployment) - COMPLETE ✅

---

## Sprint 18 Implementation Status

### ✅ Completed Tasks

1. **Docker Compose with Celery** (`docker-compose.yml`)
   - Added `celery-worker` service for background tasks
   - Added `celery-beat` service for scheduled tasks (daemon mode)
   - All services use shared `.env.local` file

2. **CLI Entrypoint** (`src/__main__.py`)
   - `python -m src run` - Start full local stack
   - `python -m src api` - Start API server only
   - `python -m src worker` - Start Celery worker
   - `python -m src beat` - Start Celery beat
   - `python -m src shell` - Interactive Python shell
   - `python -m src health` - Check system health
   - `python -m src migrate` - Run database migrations

3. **Local Environment Template** (`.env.local.template`)
   - All required variables documented with comments
   - Safe defaults for local development
   - Sections: Database, Redis, OpenAI, Google, HubSpot, Security, Features

4. **Makefile Targets** (`Makefile`)
   - `make local-up` - Start full stack with Docker
   - `make local-down` - Stop stack
   - `make local-logs` - Tail logs
   - `make local-shell` - Python shell with app context
   - `make local-health` - Check API and Jarvis health

---

## Sprint 17 Implementation Status

### ✅ Completed Tasks

1. **VoiceService** (`src/services/voice_service.py`)
   - `transcribe()`: Audio → text via OpenAI Whisper API
   - `speak()`: Text → audio via OpenAI TTS API
   - `speak_streaming()`: Streaming TTS for real-time playback
   - Wake word detection ("Hey Jarvis", "Jarvis", "Hey Casey", "Casey")
   - 6 voice options: alloy, echo, fable, onyx, nova (default), shimmer

2. **Voice API Endpoints** (`src/routes/jarvis_api.py`)
   - `POST /api/jarvis/voice/transcribe-file`: Upload audio → get text
   - `POST /api/jarvis/voice/speak`: Text → get base64 MP3 audio
   - `POST /api/jarvis/voice/conversation`: Full loop (audio in → Jarvis → audio out)
   - `GET /api/jarvis/voice/voices`: List available TTS voices

3. **Jarvis Voice Integration**
   - Voice conversation wired to Jarvis with persistent memory
   - Wake word stripped before query processing
   - Response synthesized with configurable voice

---

## Sprint 16 Implementation Status

### ✅ Completed Tasks

1. **Background Monitor Service** (`src/tasks/monitor_signals.py`)
   - `check_all_signals()`: Celery task running every 5 minutes
   - Checks HubSpot signals, Gmail signals, queue health, system health
   - Creates proactive notifications via NotificationService

2. **Notification System** (`src/models/notification.py` + `src/services/notification_service.py`)
   - `JarvisNotification` model with priority levels (urgent/high/normal/low)
   - Full CRUD with `create()`, `mark_read()`, `mark_acknowledged()`, `mark_actioned()`
   - `get_whats_up()`: Returns prioritized unread notifications

3. **Proactive API Endpoints** (`src/routes/jarvis_api.py`)
   - `GET /api/jarvis/whats-up`: Morning briefing - pending notifications + suggestions
   - `GET /api/jarvis/notifications`: List all notifications (filterable)
   - `GET /api/jarvis/notifications/{id}`: Get specific notification
   - `POST /api/jarvis/notifications/{id}/read`: Mark as read
   - `POST /api/jarvis/notifications/{id}/acknowledge`: Acknowledge
   - `POST /api/jarvis/notifications/{id}/action`: Mark as actioned

4. **Celery Beat Integration** (`src/celery_app.py`)
   - Added `daemon-monitor-signals` task to beat schedule
   - Runs every 5 minutes with 4-minute expiry

5. **Database Migration** (`infra/migrations/versions/20260125_notifications.py`)
   - Table: `jarvis_notifications` with priority indexes

---

## Sprint 15 Implementation Status

### ✅ Completed Tasks

1. **Memory Models** (`src/models/memory.py`)
   - `JarvisSession`: Persistent sessions with active context
   - `ConversationMemory`: Individual messages with embeddings
   - `MemorySummary`: Compressed summaries of old conversations

2. **MemoryService** (`src/services/memory_service.py` - 557 lines)
   - `remember()`: Store messages with embeddings
   - `recall()`: Get recent conversation history
   - `search_similar()`: Semantic search for relevant context
   - `summarize_old_messages()`: Compress old conversations
   - `forget()`: GDPR-compliant deletion

3. **Jarvis Integration** (`src/agents/jarvis.py`)
   - Jarvis now uses MemoryService for persistent memory
   - User queries are stored with embeddings
   - Responses are summarized and saved
   - Semantic search retrieves relevant context
   - New parameters: `user_id`, `session_name` for session management

4. **Memory API** (`src/routes/memory.py`)
   - `GET /api/jarvis/sessions`: List user sessions
   - `GET /api/jarvis/memory/{session_id}`: Get session memory
   - `POST /api/jarvis/memory/search`: Semantic search
   - `POST /api/jarvis/remember`: Manually add memory
   - `DELETE /api/jarvis/memory/{session_id}`: GDPR deletion
   - `POST /api/jarvis/sessions/create`: Create new session
   - `GET /api/jarvis/memory/stats`: Memory usage statistics

5. **Database Migration** (`infra/migrations/versions/20260125_persistent_memory.py`)
   - Tables: `jarvis_sessions`, `conversation_memory`, `memory_summaries`
   - Indexes for efficient queries

---

## The Vision: Casey's Digital Chief of Staff

**Henry Pattern (Alex's Implementation):**
- Mac Mini always-on in the background
- Claude API for reasoning/execution
- Persistent memory across sessions
- Voice-first interaction ("Hey Henry...")
- Proactive suggestions without prompting
- MCP integration for tool access

**CaseyOS Current State:**
- Cloud-hosted FastAPI (Railway)
- 25+ specialized agents under Jarvis
- In-memory conversation context (LOST on restart)
- Text-primary, voice-optional
- Reactive (responds to webhooks, not proactive)
- No local deployment option

**CaseyOS Target State:**
- Hybrid cloud + local deployment
- Persistent memory with semantic search
- Voice-first with ambient listening
- Proactive "Casey, you should..." suggestions
- Full GTM automation without prompting
- MCP integration for browser, calendar, docs

---

## Architecture Gap Analysis

| Capability | Henry | CaseyOS Now | Gap |
|------------|-------|-------------|-----|
| Memory Persistence | SQLite + embeddings | In-memory dict | 🔴 Critical |
| Daemon Mode | Always-on background | HTTP request-driven | 🔴 Critical |
| Voice Input | Whisper + wake word | Text-primary | 🟡 Medium |
| Voice Output | TTS synthesis | None | 🟡 Medium |
| Proactive Mode | Observes + suggests | Waits for triggers | 🟡 Medium |
| Local Deploy | Mac Mini native | Cloud-only | 🟡 Medium |
| MCP Integration | Browser, files, tools | Limited connectors | 🟡 Medium |

---

## Evolution Phases (Sprints 15-20)

### Phase 1: Persistent Memory (Sprint 15)
**Demo:** "Jarvis remembers our conversation from yesterday and picks up where we left off."

**Why First:** Without memory, nothing else works. Henry's power is remembering context.

**Tasks:**

#### 15.1: Create ConversationMemory Model
**Scope:**
- Create `ConversationMemory` table in PostgreSQL
- Fields: id, session_id, user_id, role (user/assistant), content, embedding, created_at
- Add pgvector for semantic search

**Files:**
- Create: `src/models/memory.py`
- Modify: `infra/migrations/versions/20260126_persistent_memory.py`

**Validation:**
```bash
alembic upgrade head
psql $DATABASE_URL -c "\d conversation_memory"
```

**Acceptance:**
- [ ] Table created with embedding column
- [ ] Can insert/query messages
- [ ] pgvector similarity search works

---

#### 15.2: Create JarvisSession Model
**Scope:**
- Track user sessions with persistent state
- Store: active_context (JSONB), preferences, last_topic
- Link to conversation history

**Files:**
- Modify: `src/models/memory.py`
- Create migration

**Contracts:**
```python
class JarvisSession(Base):
    __tablename__ = "jarvis_sessions"
    
    id: str (UUID)
    user_id: str
    session_name: str  # "Morning routine", "Deal review", etc.
    active_context: JSONB  # Current working memory
    preferences: JSONB  # Voice settings, notification prefs
    last_topic: str  # Resume point
    last_active: datetime
    created_at: datetime
```

---

#### 15.3: Create MemoryService
**Scope:**
- Abstract memory persistence
- Methods: remember(), recall(), forget(), search_similar()
- Use embeddings for semantic recall

**Files:**
- Create: `src/services/memory_service.py`
- Integrate with: `src/agents/jarvis.py`

**Contracts:**
```python
class MemoryService:
    async def remember(self, session_id: str, content: str, role: str) -> str:
        """Store message with embedding."""
        
    async def recall(self, session_id: str, limit: int = 10) -> List[ConversationMemory]:
        """Get recent conversation history."""
        
    async def search_similar(self, session_id: str, query: str, limit: int = 5) -> List[ConversationMemory]:
        """Semantic search for relevant past context."""
```

---

#### 15.4: Wire Jarvis to MemoryService
**Scope:**
- Replace `_conversation_context` dict with MemoryService calls
- Load context on session start
- Save every interaction
- Semantic recall for relevant context

**Files:**
- Modify: `src/agents/jarvis.py`

**Before:**
```python
_conversation_context: Dict[str, Any] = {}  # LOST on restart
```

**After:**
```python
async def ask(self, query: str, session_id: str = "default") -> str:
    # Load relevant context from memory
    context = await self.memory.search_similar(session_id, query)
    
    # Process with context
    result = await self._process_with_agents(query, context)
    
    # Remember this interaction
    await self.memory.remember(session_id, query, "user")
    await self.memory.remember(session_id, result, "assistant")
    
    return result
```

---

#### 15.5: Add Memory API Endpoints
**Scope:**
- `GET /api/jarvis/memory/{session_id}` - Get conversation history
- `POST /api/jarvis/memory/search` - Semantic search
- `DELETE /api/jarvis/memory/{session_id}` - Clear session

**Files:**
- Modify: `src/routes/jarvis_api.py`

---

### Phase 2: Daemon Mode (Sprint 16)
**Demo:** "Jarvis runs in the background and pings me when something needs attention."

**Tasks:**

#### 16.1: Create Background Monitor Service
**Scope:**
- Celery task that runs every 5 minutes
- Checks: new form submissions, email replies, deal changes, calendar conflicts
- Creates proactive recommendations

**Files:**
- Create: `src/tasks/monitor_signals.py`
- Modify: `src/celery_app.py` (add to beat schedule)

---

#### 16.2: Implement Notification System
**Scope:**
- Store pending notifications per user
- Priority levels: urgent, high, normal, low
- Channels: in-app, email, push (future), voice (future)

**Files:**
- Create: `src/models/notification.py`
- Create: `src/services/notification_service.py`

---

#### 16.3: Create "Hey Jarvis" Proactive Endpoint
**Scope:**
- `GET /api/jarvis/whats-up` - Returns pending notifications + suggestions
- Weighted by urgency + recency
- Clears after acknowledgment

**Files:**
- Modify: `src/routes/jarvis_api.py`

---

#### 16.4: Desktop Notification Bridge (Optional)
**Scope:**
- WebSocket endpoint for real-time push
- Desktop notification via browser API
- Tray icon indicator (future: Electron wrapper)

**Files:**
- Create: `src/routes/jarvis_ws.py`

---

### Phase 3: Voice-First Interface (Sprint 17)
**Demo:** "Say 'Hey Jarvis' and have a natural conversation about deals."

**Tasks:**

#### 17.1: Implement Wake Word Detection
**Scope:**
- Client-side wake word ("Hey Jarvis" or "Hey Casey")
- Open browser audio stream on detection
- Use Web Speech API or Picovoice

**Files:**
- Create: `src/static/js/voice-interface.js`
- Create: `src/static/voice-interface.html`

---

#### 17.2: Real-Time Whisper Transcription
**Scope:**
- Stream audio to OpenAI Whisper
- Real-time transcription display
- End-of-speech detection

**Files:**
- Modify: `src/voice_approval.py` (wire up Whisper)
- Create: `src/routes/voice_stream.py`

---

#### 17.3: TTS Response Synthesis
**Scope:**
- Generate spoken response from Jarvis
- Use OpenAI TTS or ElevenLabs
- Configurable voice (professional, casual, Casey-style)

**Files:**
- Create: `src/services/tts_service.py`
- Modify: `src/routes/jarvis_api.py` (add audio response)

---

#### 17.4: Conversational Flow Manager
**Scope:**
- Multi-turn conversation without re-prompting
- "And then...", "Actually...", "Wait, also..."
- Graceful interruption handling

**Files:**
- Create: `src/services/conversation_flow.py`

---

### Phase 4: Local Deployment (Sprint 18)
**Demo:** "CaseyOS runs on Casey's Mac Mini, always available."

**Tasks:**

#### 18.1: Create Standalone Package
**Scope:**
- Package as pip-installable CLI
- `caseyos start` - launches daemon
- `caseyos talk` - voice interface
- `caseyos status` - health check

**Files:**
- Create: `src/cli/__init__.py`
- Create: `src/cli/main.py`
- Modify: `pyproject.toml` (add CLI entry point)

---

#### 18.2: SQLite + Local PostgreSQL Option
**Scope:**
- Auto-detect database (SQLite for local, Postgres for cloud)
- Seamless migration between environments
- Local Redis alternative (fakeredis)

**Files:**
- Modify: `src/config.py`
- Modify: `src/db/__init__.py`

---

#### 18.3: Mac Menubar App (Optional)
**Scope:**
- System tray icon with quick actions
- "Talk to Jarvis", "Today's Moves", "Settings"
- Built with py2app or Tauri

**Files:**
- Create: `src/desktop/` directory
- Research: py2app, rumps, or Tauri

---

#### 18.4: Sync Between Local and Cloud
**Scope:**
- Hybrid mode: local for quick queries, cloud for heavy agents
- Sync memory to cloud for mobile access
- Offline mode with queue for later sync

---

### Phase 5: MCP Integration (Sprint 19-20)
**Demo:** "Jarvis controls my browser, reads my docs, and manages my calendar directly."

**Tasks:**

#### 19.1: Implement MCP Server Protocol
**Scope:**
- Make CaseyOS an MCP server that Claude can connect to
- Expose tools: read_email, send_draft, create_task, search_contacts
- Enable Claude Desktop → CaseyOS communication

**Files:**
- Create: `src/mcp/__init__.py`
- Create: `src/mcp/server.py`
- Create: `src/mcp/tools.py`

---

#### 19.2: Browser Automation Bridge
**Scope:**
- Control browser via Playwright or Puppeteer
- Actions: navigate, click, fill forms, screenshot
- Use for: research, form submissions, data scraping

---

#### 19.3: Calendar Deep Integration
**Scope:**
- Read full calendar (not just freebusy)
- Create events with context
- Reschedule with conflict detection
- Smart scheduling suggestions

---

#### 19.4: Document Access Layer
**Scope:**
- Google Drive deep search
- Notion/Confluence integration
- Local file system access (with permissions)
- Content extraction + summarization

---

## Implementation Priority Matrix

| Phase | Sprint | Impact | Effort | Dependencies | Priority |
|-------|--------|--------|--------|--------------|----------|
| Memory | 15 | 🔴 Critical | Medium | None | **NOW** |
| Daemon | 16 | 🔴 High | Medium | Memory | Next |
| Voice | 17 | 🟡 Medium | High | Daemon | After |
| Local | 18 | 🟡 Medium | High | Voice | After |
| MCP | 19-20 | 🟡 Medium | High | Local | Future |

---

## Quick Wins (Do This Week)

### 1. Memory Persistence (2-3 days)
Start with Sprint 15.1-15.4. This unblocks everything.

### 2. Proactive Notifications (1-2 days)
Add `GET /api/jarvis/whats-up` that returns:
- Pending Today's Moves count
- Unanswered emails needing response
- Upcoming meetings needing prep
- Deals that need attention

### 3. Voice Prototype (1 day)
Wire existing `src/voice_approval.py` Whisper code to Jarvis API.
Create simple HTML page with:
- Record button → transcribe → send to Jarvis → show response

---

## Success Metrics

### Sprint 15 (Memory)
- [ ] Conversation persists across server restarts
- [ ] Semantic search finds relevant past context
- [ ] 90-day retention with auto-cleanup

### Sprint 16 (Daemon)
- [ ] Proactive notification within 5 min of signal
- [ ] "What's up" returns actionable items
- [ ] Zero manual polling required

### Sprint 17 (Voice)
- [ ] Voice command response < 3 seconds
- [ ] Wake word detection works 95%+ of time
- [ ] Natural multi-turn conversation

### Sprint 18 (Local)
- [ ] `pip install caseyos` works
- [ ] Runs on Mac Mini without Docker
- [ ] Syncs with cloud seamlessly

### Sprint 19-20 (MCP)
- [ ] Claude Desktop can call CaseyOS tools
- [ ] Browser automation for research
- [ ] Full calendar control

---

## Risk Mitigation

### Memory Bloat
- Limit to 1000 messages per session
- Compress old context into summaries
- Auto-archive after 90 days

### Voice Latency
- Local wake word detection (no cloud round-trip)
- Streaming transcription (don't wait for full audio)
- Prefetch likely responses

### Local Deployment Complexity
- Start with Docker Desktop for Mac
- Graduate to native package later
- Keep cloud as fallback

---

## The "Henry" Manifesto

> "The goal isn't to build a chatbot. It's to build a Chief of Staff who knows your business, remembers your preferences, anticipates your needs, and executes without being asked."

**Henry's Power:**
1. **Always On:** Runs 24/7, not just when you open a browser
2. **Memory:** Remembers everything, surfaces relevant context
3. **Voice:** Talk naturally, not type commands
4. **Proactive:** "Hey Casey, you should call John - he replied positively"
5. **Integrated:** Controls browser, calendar, email, docs directly

**CaseyOS Path to Henry:**
1. ✅ Agents exist (25+ specialized)
2. ✅ Command Queue exists (Today's Moves)
3. ✅ Execution exists (dry-run, guardrails)
4. ⏳ Memory persistence (Sprint 15)
5. ⏳ Daemon mode (Sprint 16)
6. ⏳ Voice-first (Sprint 17)
7. ⏳ Local deploy (Sprint 18)
8. ⏳ MCP integration (Sprint 19-20)

---

**Ready to evolve. Starting with memory.**
