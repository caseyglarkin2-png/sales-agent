# Jarvis Draft Preview Feature - Sprint Plan (REVISED)

**Feature**: Jarvis reads email draft content aloud before asking for approval

**Status**: Sprint 0 Complete ✅ → Sprint 1A In Progress  
**Review Grade**: A (Revised from C+ based on subagent feedback)  
**Sprint 0 Results**: 22/22 tests passing, 3 atomic commits, all fixes validated  
**Key Changes**: Split large tasks into atomic commits, moved error handling to Sprint 1, removed scope creep

---

## 🎯 Feature Summary

**Current State**: UI displays draft, but user must read silently. No voice confirmation of content.

**Target State**: Jarvis auto-reads draft summary when loaded. User can request full read or specific sections via voice.

**Core Value**: 5x faster approval workflow through voice-first interaction.

---

## 📋 Sprint Overview

| Sprint | Goal | Tasks | Effort | Demoable Output |
|--------|------|-------|--------|-----------------|
| **0** | Test infrastructure ready | 3 | 1-2hr | pytest runs, config loads |
| **1A** | Manual TTS works | 5 | 4-6hr | Click "Read Draft" → Hears email |
| **1B** | Auto-summary on load | 6 | 6-8hr | Load draft → Auto-reads summary |
| **2** | Voice commands | 4 | 6-8hr | "What's the subject?" → Response |
| **3** | Visual polish | 5 | 4-6hr | Calendar links highlighted |
| **4** | Advanced features | 4 | 4-6hr | Keyboard shortcuts, analytics |

**Total**: 28 atomic tasks, ~25-36 hours

---

# SPRINT 0: Foundation & Setup ✅ COMPLETE

**Goal**: Test files and configuration ready

**Duration**: 1-2 hours (Actual: 2.5 hours including fixes)

**Status**: ✅ Complete - 22 tests passing, 3 atomic commits

**Commits**:
- `a968131` - test: Add smoke tests to validate fixtures (Fix #1)
- `4bf1d68` - test: Create config test suite (Fix #2)  
- `b65bcfd` - config: Add Pydantic validators to TTS settings (Fix #3)

**Test Results**:
- 6 smoke tests (fixtures validated)
- 9 config tests (defaults, boundaries, validators)
- 7 rate limiting tests (from original Sprint 0)
- **Total: 22/22 passing**

**Key Improvements** (based on subagent review):
- Fixed Issue #1: Added 6 smoke tests instead of placeholder files
- Fixed Issue #2: Created comprehensive config test suite
- Fixed Issue #3: Added Pydantic validators (ge/le constraints) for runtime safety

---

## Task 0.1: Create Test File Structure ✅

**Status**: ✅ COMPLETE (with improvements)

**File**: Create 4 new files in `tests/`

**Implementation**:
```python
# tests/test_voice_summary.py
import pytest
from src.voice_approval import get_voice_approval

@pytest.fixture
def mock_draft():
    return {
        "id": "test-123",
        "recipient": "john@techcorp.com",
        "subject": "Q1 Supply Chain Meeting",
        "body": "Hi John,\n\nI wanted to reach out...\n\nBest,\nCasey"
    }

# Placeholder - tests added in later sprints


# tests/test_detail_levels.py
import pytest
# Placeholder


# tests/test_command_parsing.py
import pytest
# Placeholder


# tests/test_calendar_detection.py
import pytest
# Placeholder
```

**Acceptance**: All 4 files importable, `pytest --collect-only` shows them

**Validation**:
```bash
pytest --collect-only tests/
# Expected: 4 files listed, 0 tests
```

**Effort**: 30min

---

## Task 0.2: Add TTS Configuration

**File**: `src/config.py`

**Implementation**:
```python
# Add to src/config.py
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"
TTS_VOICE_NAME = os.getenv("TTS_VOICE_NAME", "Google UK English Female")
TTS_RATE = float(os.getenv("TTS_RATE", "1.0"))
TTS_PITCH = float(os.getenv("TTS_PITCH", "1.0"))
TTS_VOLUME = float(os.getenv("TTS_VOLUME", "1.0"))
```

**Acceptance**: Config imports without error

**Validation**:
```bash
python -c "from src.config import TTS_ENABLED; print('OK:', TTS_ENABLED)"
# Expected: OK: True
```

**Effort**: 15min

---

## Task 0.3: Add GPT-4 Rate Limiting

**File**: `src/utils/gpt_helpers.py` (new file)

**Implementation**:
```python
"""GPT-4 API helpers with rate limiting"""
import time
from collections import deque
from functools import wraps

_rate_limit_calls = deque(maxlen=100)

class RateLimitExceeded(Exception):
    pass

def check_rate_limit(max_per_minute=10):
    now = time.time()
    recent = [t for t in _rate_limit_calls if t > now - 60]
    if len(recent) >= max_per_minute:
        raise RateLimitExceeded(f"Exceeded {max_per_minute} calls/min")
    _rate_limit_calls.append(now)

def rate_limited_gpt4(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        check_rate_limit()
        return await func(*args, **kwargs)
    return wrapper
```

**Acceptance**: Decorator blocks >10 calls/min

**Validation**:
```python
# tests/test_rate_limiting.py
from src.utils.gpt_helpers import check_rate_limit, RateLimitExceeded, _rate_limit_calls

def test_rate_limit():
    _rate_limit_calls.clear()
    for i in range(10):
        check_rate_limit()  # OK
    
    with pytest.raises(RateLimitExceeded):
        check_rate_limit()  # 11th should fail
```

```bash
pytest tests/test_rate_limiting.py -v
# Expected: PASSED
```

**Effort**: 45min

---

**Sprint 0 Complete**: ✅ Test infrastructure + Config + Rate limiting (22 tests passing)

---

# SPRINT 1A: Basic TTS (MVP)

**Goal**: User can click button to manually hear draft

**Duration**: 4-6 hours

**Demo**: Load draft → Click "Read Draft" → Hears full email

**Status**: 🔄 Ready to Start

---

## Task 1A.1: Add speakResponse() Function

**File**: `src/static/jarvis.html`

**Implementation**:
```javascript
// Add after line ~170

let isSpeaking = false;

function speakResponse(text) {
    if (!window.speechSynthesis) {
        console.warn('TTS not supported');
        return;
    }
    
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    utterance.lang = 'en-US';
    
    utterance.onstart = () => { isSpeaking = true; };
    utterance.onend = () => { isSpeaking = false; };
    
    window.speechSynthesis.speak(utterance);
}
```

**Acceptance**: Function callable from console, plays audio

**Validation**:
```javascript
// In browser console at http://localhost:8000/jarvis
speakResponse("Hello, this is a test");
// Expected: Audio plays, isSpeaking = true during speech
```

**Effort**: 1hr

---

## Task 1A.2: Add Mute Toggle

**File**: `src/static/jarvis.html`

**Implementation**:
```javascript
// Add after speakResponse()

let isMuted = false;

function toggleMute() {
    isMuted = !isMuted;
    const btn = document.getElementById('mute-toggle');
    btn.textContent = isMuted ? '🔇 Muted' : '🔊 Sound On';
    btn.className = isMuted ? 
        'px-4 py-2 bg-gray-500 rounded-lg' :
        'px-4 py-2 bg-green-500 rounded-lg';
}

// Update speakResponse()
function speakResponse(text) {
    if (isMuted || !window.speechSynthesis) return;  // Check mute
    // ... rest of function
}
```

**Add button to UI** (after voice interface controls):
```html
<button id="mute-toggle" onclick="toggleMute()" 
        class="w-full px-4 py-2 bg-green-500 rounded-lg hover:bg-green-600 mt-2">
    🔊 Sound On
</button>
```

**Acceptance**: Button toggles state, muted = no audio

**Validation**: Click button → state changes, speakResponse() respects mute

**Effort**: 30min

---

## Task 1A.3: Add Browser Compatibility Check

**File**: `src/static/jarvis.html`

**Implementation**:
```javascript
// Add on page load

function checkTTSSupport() {
    if (!('speechSynthesis' in window)) {
        const warning = document.createElement('div');
        warning.className = 'bg-yellow-500/20 p-4 rounded-lg mb-4';
        warning.innerHTML = `
            <p class="text-sm">⚠️ Text-to-speech not supported in this browser.</p>
            <p class="text-xs mt-1">Try Chrome, Edge, or Safari for voice features.</p>
        `;
        document.querySelector('.container').prepend(warning);
        
        // Hide TTS controls
        document.getElementById('mute-toggle')?.remove();
        return false;
    }
    return true;
}

// Run on load
document.addEventListener('DOMContentLoaded', () => {
    checkTTSSupport();
});
```

**Acceptance**: Warning shows in unsupported browsers

**Validation**:
Test in browsers:
- Chrome: ✅ No warning
- Firefox: ✅ No warning
- Safari: ✅ No warning
- Firefox Android: ⚠️ Warning shows (TTS limited)

**Effort**: 1hr

---

## Task 1A.4: Return Full Draft Body from API

**File**: `src/voice_approval.py` (line ~346)

**Implementation**:
```python
# In _next_item() method, change:

# BEFORE:
"preview": next_draft.get("body", "")[:150]

# AFTER:
"body": next_draft.get("body", ""),  # Full content
"body_preview": next_draft.get("body", "")[:150]  # Keep preview
```

**Acceptance**: Status endpoint returns full body (not truncated)

**Validation**:
```bash
curl -s http://localhost:8000/api/voice-approval/status | \
  jq '.current_item.body' | wc -w

# Expected: >150 words for typical draft
```

**Effort**: 30min

---

## Task 1A.5: Add "Read Draft" Button

**File**: `src/static/jarvis.html` (~line 327, in displayCurrentItem)

**Implementation**:
```javascript
function displayCurrentItem(item) {
    const container = document.getElementById('current-item');
    
    if (item.type === 'email_draft') {
        const fullBody = item.content?.body || item.body || 'No content';
        
        container.innerHTML = `
            <div class="space-y-4">
                <div>
                    <label class="text-sm opacity-70">To:</label>
                    <p class="text-lg">${escapeHtml(item.content?.to_name || item.recipient)}</p>
                </div>
                <div>
                    <label class="text-sm opacity-70">Subject:</label>
                    <p class="text-lg font-semibold">${escapeHtml(item.content?.subject || item.subject)}</p>
                </div>
                <div>
                    <label class="text-sm opacity-70">Body:</label>
                    <div class="bg-white/10 rounded-lg p-4 max-h-96 overflow-y-auto">
                        <pre class="whitespace-pre-wrap font-sans">${escapeHtml(fullBody)}</pre>
                    </div>
                </div>
                
                <!-- NEW: Read Draft Button -->
                <button onclick="speakResponse(\`${fullBody.replace(/`/g, '')}\`)" 
                        class="w-full px-4 py-3 bg-purple-500 rounded-lg hover:bg-purple-600 transition">
                    🔊 Read This Draft Aloud
                </button>
            </div>
        `;
    }
}
```

**Acceptance**: Button appears, clicking reads full email

**Validation**: Load draft → Click button → Email read aloud

**Effort**: 1hr

---

**Sprint 1A Demo**:
1. Open http://localhost:8000/jarvis
2. Draft loads with full content displayed
3. Click "Read This Draft Aloud" → Hears full email
4. Click mute toggle → Button grays out
5. Click "Read" again → Silent (muted)

**Sprint 1A Complete**: ✅ Manual TTS functional

---

# SPRINT 1B: Auto-Summary with GPT-4

**Goal**: Draft summary auto-plays on load (voice-first)

**Duration**: 6-8 hours

**Demo**: Load Jarvis → Hears "Email to John at TechCorp about... Ready to approve?"

---

## Task 1B.1: Add GPT-4 Summary Generation Method

**File**: `src/voice_approval.py`

**Implementation**:
```python
# Add new method to VoiceApprovalInterface class

from src.utils.gpt_helpers import rate_limited_gpt4

@rate_limited_gpt4
async def _generate_spoken_summary(self, draft: Dict[str, Any]) -> str:
    """Generate 2-3 sentence summary for voice reading.
    
    Uses GPT-4 to condense email to natural spoken format.
    Fallback to simple summary if GPT-4 fails.
    """
    subject = draft.get("subject", "No subject")
    recipient = draft.get("recipient", "Unknown")
    company = draft.get("company_name", "")
    body = draft.get("body", "")
    
    # For short emails, just use full text
    if len(body) < 200:
        return f"Email to {recipient} about {subject}. {body}"
    
    # Use GPT-4 for longer emails
    prompt = f"""Summarize this sales email in 2-3 sentences for voice reading.

Subject: {subject}
To: {recipient}
Body: {body}

Create natural spoken summary focusing on:
1. Main purpose
2. Key value proposition
3. Call to action

Maximum 50 words. Natural speaking tone."""
    
    try:
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=100,
            timeout=10
        )
        summary = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        # Fallback: first 100 words
        summary = " ".join(body.split()[:100]) + "..."
    
    company_part = f" at {company}" if company else ""
    return f"Email to {recipient}{company_part} about {subject}. {summary}"
```

**Acceptance**: Returns 20-50 word summary

**Validation**:
```python
# Add to tests/test_voice_summary.py

@pytest.mark.asyncio
async def test_generate_summary(mock_draft):
    jarvis = get_voice_approval()
    summary = await jarvis._generate_spoken_summary(mock_draft)
    
    assert len(summary.split()) < 100
    assert "john" in summary.lower() or "techcorp" in summary.lower()
    assert "Q1 Supply Chain" in summary or "supply chain" in summary.lower()
```

```bash
pytest tests/test_voice_summary.py::test_generate_summary -v
# Expected: PASSED
```

**Effort**: 2hr

---

## Task 1B.2: Add GPT-4 Error Handling

**File**: `src/voice_approval.py`

**Implementation**:
Already included in Task 1B.1 (try/except with fallback).

**Additional**: Add to _generate_spoken_summary:
```python
# Add logging and metrics
try:
    # ... GPT-4 call
    logger.info(f"Generated summary: {len(summary)} words")
except Exception as e:
    logger.error(f"Summary generation failed: {e}", exc_info=True)
    # Track failures
    summary = f"Email to {recipient} about {subject}"
```

**Acceptance**: Handles GPT-4 timeout, returns fallback

**Validation**:
```python
# tests/test_voice_summary.py

@pytest.mark.asyncio
async def test_summary_fallback_on_error(mock_draft, monkeypatch):
    jarvis = get_voice_approval()
    
    # Mock GPT-4 failure
    async def mock_create(*args, **kwargs):
        raise Exception("API Error")
    
    monkeypatch.setattr(jarvis.client.chat.completions, 'create', mock_create)
    
    summary = await jarvis._generate_spoken_summary(mock_draft)
    
    # Should still return something
    assert len(summary) > 0
    assert "Email to" in summary
```

```bash
pytest tests/test_voice_summary.py::test_summary_fallback_on_error -v
# Expected: PASSED
```

**Effort**: 1hr

---

## Task 1B.3: Update _next_item() to Include Summary

**File**: `src/voice_approval.py` (method _next_item, ~line 346)

**Implementation**:
```python
async def _next_item(self) -> Dict[str, Any]:
    """Get info about next item in queue."""
    pending = await self._get_pending_drafts()
    if not pending:
        return {"action": "queue_empty", "message": "No more items to review"}
    
    next_draft = pending[0]
    
    # Generate spoken summary (NEW)
    spoken_intro = await self._generate_spoken_summary(next_draft)
    
    return {
        "action": "next",
        "action_taken": False,
        "spoken_intro": spoken_intro,  # NEW
        "item": {
            "id": next_draft.get("id"),
            "recipient": next_draft.get("recipient"),
            "subject": next_draft.get("subject"),
            "company": next_draft.get("company_name"),
            "body": next_draft.get("body", ""),
            "body_preview": next_draft.get("body", "")[:150]
        }
    }
```

**Acceptance**: _next_item() includes spoken_intro field

**Validation**:
```python
# tests/test_voice_summary.py

@pytest.mark.asyncio
async def test_next_item_includes_summary(mock_draft):
    # Add mock draft to queue
    # ... setup code
    
    jarvis = get_voice_approval()
    result = await jarvis._next_item()
    
    assert "spoken_intro" in result
    assert len(result["spoken_intro"]) > 0
```

**Effort**: 30min

---

## Task 1B.4: Update Status Route to Return Summary

**File**: `src/voice_approval.py` (get_status_async method, ~line 583)

**Implementation**:
```python
async def get_status_async(self) -> Dict[str, Any]:
    """Get current status of approval queue."""
    try:
        pending = await self._get_pending_drafts()
        current = pending[0] if pending else None
        
        # Add spoken intro if current item exists (NEW)
        spoken_intro = None
        if current:
            spoken_intro = await self._generate_spoken_summary(current)
        
        return {
            "pending_count": len(pending),
            "current_item": current,
            "spoken_intro": spoken_intro,  # NEW
            "queue": pending[:10]
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {
            "pending_count": 0,
            "current_item": None,
            "spoken_intro": None,
            "queue": [],
            "error": str(e)
        }
```

**Acceptance**: GET /api/voice-approval/status includes spoken_intro

**Validation**:
```bash
curl -s http://localhost:8000/api/voice-approval/status | jq '.spoken_intro'

# Expected: "Email to John Smith at TechCorp about..."
```

**Effort**: 30min

---

## Task 1B.5: Auto-Read Summary on Draft Load

**File**: `src/static/jarvis.html` (loadStatus function, ~line 313)

**Implementation**:
```javascript
let lastDraftId = null;

async function loadStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/voice-approval/status`);
        const data = await response.json();
        
        updateStatus(data);
        
        // Auto-read on new draft (NEW)
        if (data.current_item && data.current_item.id !== lastDraftId) {
            lastDraftId = data.current_item.id;
            
            if (data.spoken_intro && !isMuted) {
                // Add "Ready to approve?" at end
                speakResponse(data.spoken_intro + " Ready to approve?");
            }
        }
    } catch (error) {
        console.error('Error loading status:', error);
    }
}
```

**Acceptance**: New draft auto-plays summary (if not muted)

**Validation**:
1. Load Jarvis → Auto-reads
2. Approve draft → Next loads → Auto-reads
3. Mute → Approve → Next loads → Silent

**Effort**: 1hr

---

## Task 1B.6: Add Loading State UI

**File**: `src/static/jarvis.html`

**Implementation**:
```javascript
// Add loading indicator
function showLoadingState() {
    const container = document.getElementById('current-item');
    container.innerHTML = `
        <div class="flex items-center justify-center py-12">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
            <p class="ml-4 text-lg">Generating summary...</p>
        </div>
    `;
}

// Update loadStatus to show loading
async function loadStatus() {
    showLoadingState();  // NEW
    
    try {
        const response = await fetch(`${API_BASE}/api/voice-approval/status`);
        const data = await response.json();
        updateStatus(data);
        // ... rest of function
    } catch (error) {
        console.error('Error loading status:', error);
    }
}
```

**Acceptance**: Spinner shows while loading

**Validation**: Throttle network in DevTools → See spinner

**Effort**: 30min

---

**Sprint 1B Demo**:
1. Open http://localhost:8000/jarvis
2. Loading spinner shows briefly
3. Jarvis speaks: "Email to John Smith at TechCorp about Q1 Supply Chain Meeting. The email discusses our platform's supply chain optimization. It includes your calendar link. Ready to approve?"
4. Click "Approve" button
5. Next draft loads
6. Auto-reads next summary
7. Click mute
8. Next draft → Loads silently

**Sprint 1B Complete**: ✅ Auto-summary functional with GPT-4

---

# SPRINT 2: Voice Commands

**Goal**: User asks questions about draft via voice

**Duration**: 6-8 hours

**Demo**: Say "What's the subject?" → "The subject is: Q1 Supply Chain Meeting"

---

## Task 2.1: Add Detail Level Parameter

**File**: `src/voice_approval.py` (_get_item_details method, ~line 366)

**Implementation**:
```python
async def _get_item_details(
    self, 
    item_id: Optional[str],
    detail_level: str = "full"  # NEW parameter
) -> Dict[str, Any]:
    """Get item details with specified detail level.
    
    Args:
        item_id: Draft ID (None = current)
        detail_level: "subject_only" | "preview" | "full"
    """
    pending = await self._get_pending_drafts()
    draft = next((d for d in pending if d.get("id") == item_id), None) if item_id else pending[0] if pending else None
    
    if not draft:
        return {"action": "error", "message": "Draft not found"}
    
    # Return based on detail level (NEW)
    if detail_level == "subject_only":
        return {
            "action": "details",
            "detail_level": "subject_only",
            "subject": draft.get("subject"),
            "recipient": draft.get("recipient"),
            "message": f"The subject is: {draft.get('subject')}"
        }
    
    elif detail_level == "preview":
        preview = " ".join(draft.get("body", "").split()[:100])
        return {
            "action": "details",
            "detail_level": "preview",
            "subject": draft.get("subject"),
            "preview": preview,
            "message": f"Here's a preview: {preview}..."
        }
    
    else:  # full
        spoken_summary = await self._generate_spoken_summary(draft)
        return {
            "action": "details",
            "detail_level": "full",
            "item": draft,
            "spoken_summary": spoken_summary,
            "message": spoken_summary
        }
```

**Acceptance**: Method returns correct data for each level

**Validation**:
```python
# tests/test_detail_levels.py

@pytest.mark.asyncio
async def test_detail_levels(mock_draft):
    jarvis = get_voice_approval()
    
    # Subject only
    result = await jarvis._get_item_details(None, "subject_only")
    assert result["detail_level"] == "subject_only"
    assert "subject" in result
    
    # Preview
    result = await jarvis._get_item_details(None, "preview")
    assert result["detail_level"] == "preview"
    assert len(result["preview"].split()) <= 100
    
    # Full
    result = await jarvis._get_item_details(None, "full")
    assert result["detail_level"] == "full"
    assert "spoken_summary" in result
```

```bash
pytest tests/test_detail_levels.py -v
# Expected: 3 tests PASSED
```

**Effort**: 2hr

---

## Task 2.2: Update Command Parser with Detail Hints

**File**: `src/voice_approval.py` (_parse_voice_command method, ~line 140)

**Implementation**:
```python
async def _parse_voice_command(self, text: str) -> VoiceCommand:
    """Parse natural language command using GPT-4."""
    context = self._build_command_context()
    
    prompt = f"""Parse voice command for email approval system.

Context: {context}
User said: "{text}"

Parse to JSON:
{{
  "action": "approve|reject|skip|request_info",
  "metadata": {{
    "detail_level": "subject_only|preview|full"  // For request_info only
  }}
}}

Examples:
"What's the subject?" → {{"action": "request_info", "metadata": {{"detail_level": "subject_only"}}}}
"Give me a preview" → {{"action": "request_info", "metadata": {{"detail_level": "preview"}}}}
"Read this email" → {{"action": "request_info", "metadata": {{"detail_level": "full"}}}}
"Approve" → {{"action": "approve"}}
"""

    response = await self.client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
        timeout=10
    )
    
    parsed = json.loads(response.choices[0].message.content)
    
    return VoiceCommand(
        action=ApprovalAction(parsed["action"]),
        metadata=parsed.get("metadata", {})
    )
```

**Update _execute_command**:
```python
async def _execute_command(self, command: VoiceCommand) -> Dict[str, Any]:
    if command.action == ApprovalAction.REQUEST_INFO:
        detail_level = command.metadata.get("detail_level", "full")  # NEW
        return await self._get_item_details(None, detail_level=detail_level)
    # ... rest of method
```

**Acceptance**: Parser extracts detail_level correctly

**Validation**:
```python
# tests/test_command_parsing.py

@pytest.mark.asyncio
async def test_parse_detail_commands():
    jarvis = get_voice_approval()
    
    test_cases = [
        ("What's the subject?", "request_info", "subject_only"),
        ("Give me a preview", "request_info", "preview"),
        ("Read this email", "request_info", "full"),
    ]
    
    for text, expected_action, expected_level in test_cases:
        command = await jarvis._parse_voice_command(text)
        assert command.action.value == expected_action
        assert command.metadata.get("detail_level") == expected_level
```

```bash
pytest tests/test_command_parsing.py -v
# Expected: 3 assertions PASSED
```

**Effort**: 3hr

---

## Task 2.3: Generate Spoken Responses for Detail Levels

**File**: `src/voice_approval.py` (_generate_response method, ~line 456)

**Implementation**:
```python
async def _generate_response(self, command: VoiceCommand, result: Dict[str, Any]) -> Dict[str, Any]:
    """Generate natural spoken response."""
    
    # Use templates for detail levels (fast)
    if command.action == ApprovalAction.REQUEST_INFO:
        spoken = result.get("message", "Here are the details.")
    
    else:
        # For other actions, use simple templates
        action_map = {
            "approved": "Draft approved. Moving to next.",
            "rejected": "Draft rejected. Next draft?",
            "next": "Loading next draft."
        }
        spoken = action_map.get(result.get("action"), "Done.")
    
    return {
        "spoken_response": spoken,
        "action_taken": result.get("action"),
        "status": {
            "pending_count": len(await self._get_pending_drafts())
        },
        **result
    }
```

**Acceptance**: Responses under 100 words, natural tone

**Validation**:
```bash
curl -X POST http://localhost:8000/api/voice-approval/voice-input \
  -H "Content-Type: application/json" \
  -d '{"text": "What'\''s the subject?"}' | jq '.spoken_response'

# Expected: "The subject is: Q1 Supply Chain Meeting"
```

**Effort**: 2hr

---

## Task 2.4: Wire Up Voice Input to Detail Levels

**File**: `src/routes/voice_approval_routes.py`

**Implementation**:
Ensure existing `/voice-input` endpoint calls updated methods:

```python
@router.post("/voice-input")
async def process_voice_input_text(request: VoiceInputRequest):
    jarvis = get_voice_approval()
    response = await jarvis.process_voice_input(text_input=request.text)
    return response
```

(No changes needed - just verify it works end-to-end)

**Acceptance**: Voice commands work end-to-end

**Validation**:
```bash
# Test subject only
curl -X POST http://localhost:8000/api/voice-approval/voice-input \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the subject line?"}' | jq

# Expected: Returns detail_level="subject_only" with subject

# Test preview
curl -X POST http://localhost:8000/api/voice-approval/voice-input \
  -H "Content-Type: application/json" \
  -d '{"text": "Give me a quick preview"}' | jq

# Expected: Returns preview with ~100 words
```

**Effort**: 1hr

---

**Sprint 2 Demo**:
1. Load draft in Jarvis
2. Say: "What's the subject?" → "The subject is: Q1 Supply Chain Meeting"
3. Say: "Give me a preview" → Reads first 100 words
4. Say: "Read the full email" → Reads complete summary
5. Say: "Approve" → "Draft approved. Moving to next."

**Sprint 2 Complete**: ✅ Voice commands functional

---

# SPRINT 3: Visual Polish & Metadata

**Goal**: UI shows draft context clearly

**Duration**: 4-6 hours

**Demo**: Calendar links highlighted, metadata badges shown

---

## Task 3.1: Add Calendar Link Detection

**File**: `src/voice_approval.py`

**Implementation**:
```python
import re

def _check_calendar_link(self, body: str) -> Dict[str, Any]:
    """Check if draft includes calendar booking link."""
    patterns = [
        r'https://meetings\.hubspot\.com/[a-z0-9-]+',
        r'https://calendly\.com/[a-z0-9-]+',
        r'https://cal\.com/[a-z0-9-]+'
    ]
    
    links = []
    for pattern in patterns:
        matches = re.findall(pattern, body)
        links.extend(matches)
    
    return {
        "has_calendar_link": len(links) > 0,
        "calendar_links": links,
        "warning": None if links else "⚠️ No calendar booking link found"
    }
```

**Acceptance**: Detects all calendar link patterns

**Validation**:
```python
# tests/test_calendar_detection.py

def test_calendar_link_detection():
    jarvis = get_voice_approval()
    
    # Has link
    body1 = "Book time: https://meetings.hubspot.com/casey-larkin"
    result = jarvis._check_calendar_link(body1)
    assert result["has_calendar_link"] == True
    assert len(result["calendar_links"]) == 1
    
    # No link
    body2 = "Let's schedule a call"
    result = jarvis._check_calendar_link(body2)
    assert result["has_calendar_link"] == False
    assert result["warning"] is not None
```

```bash
pytest tests/test_calendar_detection.py -v
# Expected: PASSED
```

**Effort**: 1hr

---

## Task 3.2: Highlight Calendar Links in UI

**File**: `src/static/jarvis.html` (displayCurrentItem function, ~line 327)

**Implementation**:
```javascript
function displayCurrentItem(item) {
    const container = document.getElementById('current-item');
    
    if (item.type === 'email_draft') {
        let body = escapeHtml(item.content?.body || item.body || 'No content');
        
        // Highlight calendar links (NEW)
        body = body.replace(
            /(https:\/\/(meetings\.hubspot\.com|calendly\.com|cal\.com)\/[a-z0-9-]+)/gi,
            '<a href="$1" target="_blank" class="text-green-400 font-bold underline">$1 ✓</a>'
        );
        
        // ... rest of displayCurrentItem
    }
}
```

**Acceptance**: Calendar links are green, clickable, with checkmark

**Validation**: Load draft with calendar link → Link is green and clickable

**Effort**: 1hr

---

## Task 3.3: Add Calendar Badge

**File**: `src/static/jarvis.html`

**Implementation**:
```javascript
function displayCurrentItem(item) {
    // ... existing code
    
    // Check for calendar link (NEW)
    const hasCalendar = (item.content?.body || item.body || '').match(/meetings\.hubspot\.com|calendly\.com|cal\.com/);
    const calendarBadge = hasCalendar ?
        '<span class="px-2 py-1 bg-green-500 rounded text-xs ml-2">✓ Calendar Link</span>' :
        '<span class="px-2 py-1 bg-yellow-500 rounded text-xs ml-2">⚠️ No Calendar Link</span>';
    
    container.innerHTML = `
        <div class="space-y-4">
            <div class="flex justify-between items-start">
                <div>
                    <label class="text-sm opacity-70">Subject:</label>
                    <p class="text-lg font-semibold">${escapeHtml(item.content?.subject || item.subject)}</p>
                </div>
                ${calendarBadge}
            </div>
            <!-- ... rest of draft display -->
        </div>
    `;
}
```

**Acceptance**: Badge shows correct status (green/yellow)

**Validation**: Load drafts with/without calendar → Badge shows correctly

**Effort**: 30min

---

## Task 3.4: Add Draft Metadata Enrichment

**File**: `src/voice_approval.py` (get_status_async method)

**Implementation**:
```python
async def get_status_async(self) -> Dict[str, Any]:
    """Get current status with enriched metadata."""
    try:
        pending = await self._get_pending_drafts()
        current = pending[0] if pending else None
        
        # Enrich metadata (NEW)
        if current:
            current["metadata_enriched"] = {
                "campaign_id": current.get("metadata", {}).get("campaign_id"),
                "workflow_name": current.get("metadata", {}).get("workflow_name"),
                "voice_profile": current.get("metadata", {}).get("voice_profile", "casey_larkin"),
                "source": current.get("metadata", {}).get("source", "manual"),
                "generated_at": current.get("metadata", {}).get("generated_at")
            }
        
        # ... rest of method
```

**Acceptance**: Status includes metadata_enriched

**Validation**:
```bash
curl -s http://localhost:8000/api/voice-approval/status | jq '.current_item.metadata_enriched'

# Expected: Shows campaign_id, voice_profile, etc.
```

**Effort**: 1hr

---

## Task 3.5: Display Metadata in UI

**File**: `src/static/jarvis.html`

**Implementation**:
```javascript
function displayCurrentItem(item) {
    // ... existing display code
    
    // Add metadata section (NEW)
    const metadata = item.metadata_enriched || {};
    const metadataHTML = `
        <div class="mt-4 text-xs opacity-70 space-y-1">
            ${metadata.workflow_name ? `<p>📊 Campaign: ${metadata.workflow_name}</p>` : ''}
            ${metadata.voice_profile ? `<p>🎙️ Voice: ${metadata.voice_profile}</p>` : ''}
            ${metadata.source ? `<p>📍 Source: ${metadata.source}</p>` : ''}
            ${metadata.generated_at ? `<p>🕐 Generated: ${new Date(metadata.generated_at).toLocaleString()}</p>` : ''}
        </div>
    `;
    
    // Append to container
    container.querySelector('.space-y-4').insertAdjacentHTML('beforeend', metadataHTML);
}
```

**Acceptance**: Metadata displays below draft

**Validation**: Load draft → Metadata section shows campaign, voice, source

**Effort**: 30min

---

**Sprint 3 Demo**:
1. Load draft
2. Calendar link highlighted in green with ✓
3. Badge shows "✓ Calendar Link" (or warning if missing)
4. Metadata section shows:
   - 📊 Campaign: CHAINge NA Sponsorship
   - 🎙️ Voice: casey_larkin
   - 📍 Source: chainge_import

**Sprint 3 Complete**: ✅ Visual polish functional

---

# SPRINT 4: Advanced Features

**Goal**: Keyboard shortcuts and analytics

**Duration**: 4-6 hours

**Demo**: Press A to approve, view usage stats at /analytics

---

## Task 4.1: Add Core Keyboard Shortcuts

**File**: `src/static/jarvis.html` (~line 430)

**Implementation**:
```javascript
// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ignore if typing in input
    if (e.target.matches('input, textarea')) return;
    
    const shortcuts = {
        'KeyA': () => sendTextCommand('Approve this'),
        'KeyR': () => sendTextCommand('Reject this'),
        'KeyN': () => sendTextCommand('Show me the next one'),
        'Space': () => toggleMute()
    };
    
    const handler = shortcuts[e.code];
    if (handler) {
        e.preventDefault();
        handler();
        showToast(`Shortcut: ${e.code}`);
    }
});

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-4 right-4 bg-purple-500 px-4 py-2 rounded-lg shadow-lg';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
}
```

**Acceptance**: A, R, N, Space work as shortcuts

**Validation**:
Manual test:
1. Load draft
2. Press A → Approves, shows toast
3. Press N → Next draft
4. Press R → Rejects
5. Click in input, press A → Nothing happens

**Effort**: 1hr

---

## Task 4.2: Add Keyboard Help Overlay

**File**: `src/static/jarvis.html`

**Implementation**:
```html
<!-- Add before </body> -->
<div id="help-overlay" class="hidden fixed inset-0 bg-black/50 flex items-center justify-center z-50">
    <div class="glass rounded-2xl p-8 max-w-md">
        <h2 class="text-2xl font-bold mb-4">Keyboard Shortcuts</h2>
        <div class="space-y-2">
            <div class="flex justify-between">
                <kbd class="px-3 py-1 bg-white/20 rounded">A</kbd>
                <span>Approve draft</span>
            </div>
            <div class="flex justify-between">
                <kbd class="px-3 py-1 bg-white/20 rounded">R</kbd>
                <span>Reject draft</span>
            </div>
            <div class="flex justify-between">
                <kbd class="px-3 py-1 bg-white/20 rounded">N</kbd>
                <span>Next draft</span>
            </div>
            <div class="flex justify-between">
                <kbd class="px-3 py-1 bg-white/20 rounded">Space</kbd>
                <span>Toggle mute</span>
            </div>
            <div class="flex justify-between">
                <kbd class="px-3 py-1 bg-white/20 rounded">?</kbd>
                <span>Toggle this help</span>
            </div>
        </div>
        <button onclick="toggleHelp()" class="mt-6 w-full px-4 py-2 bg-purple-500 rounded-lg">Close</button>
    </div>
</div>

<script>
function toggleHelp() {
    document.getElementById('help-overlay').classList.toggle('hidden');
}

// Add to shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === '?') {
        toggleHelp();
        e.preventDefault();
    }
});
</script>
```

**Acceptance**: Pressing ? shows/hides help

**Validation**: Press ? → Modal appears, press again → Closes

**Effort**: 1hr

---

## Task 4.3: Add Voice Command Analytics

**File**: `src/routes/voice_approval_routes.py`

**Implementation**:
```python
# Add at top of file
from datetime import datetime
from typing import List, Dict

_analytics_events: List[Dict] = []

def track_event(event_type: str, metadata: Dict = None):
    """Track voice command events."""
    _analytics_events.append({
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "metadata": metadata or {}
    })
    # Keep last 1000
    if len(_analytics_events) > 1000:
        _analytics_events.pop(0)

# Update voice-input endpoint
@router.post("/voice-input")
async def process_voice_input_text(request: VoiceInputRequest):
    track_event("voice_command", {"text": request.text})
    
    try:
        jarvis = get_voice_approval()
        response = await jarvis.process_voice_input(text_input=request.text)
        
        track_event("command_success", {"action": response.get("action_taken")})
        return response
    except Exception as e:
        track_event("command_error", {"error": str(e)})
        raise
```

**Acceptance**: Events tracked in memory

**Validation**: Send commands, check _analytics_events list

**Effort**: 1hr

---

## Task 4.4: Add Analytics Endpoint

**File**: `src/routes/voice_approval_routes.py`

**Implementation**:
```python
@router.get("/analytics")
async def get_analytics():
    """Get voice command analytics."""
    if not _analytics_events:
        return {"total_commands": 0}
    
    total = len([e for e in _analytics_events if e["event_type"] == "voice_command"])
    successes = len([e for e in _analytics_events if e["event_type"] == "command_success"])
    errors = len([e for e in _analytics_events if e["event_type"] == "command_error"])
    
    # Command breakdown
    actions = [e["metadata"].get("action") for e in _analytics_events 
               if e["event_type"] == "command_success" and e["metadata"].get("action")]
    action_counts = {}
    for action in actions:
        action_counts[action] = action_counts.get(action, 0) + 1
    
    return {
        "total_commands": total,
        "successful": successes,
        "errors": errors,
        "success_rate": (successes / total * 100) if total > 0 else 0,
        "action_breakdown": action_counts,
        "recent_events": _analytics_events[-20:]
    }
```

**Acceptance**: Endpoint returns analytics

**Validation**:
```bash
# Send some commands
curl -X POST http://localhost:8000/api/voice-approval/voice-input \
  -d '{"text": "Approve this"}' -H "Content-Type: application/json"

curl -X POST http://localhost:8000/api/voice-approval/voice-input \
  -d '{"text": "Next draft"}' -H "Content-Type: application/json"

# Check analytics
curl http://localhost:8000/api/voice-approval/analytics | jq

# Expected: Shows 2 commands, breakdown, success rate
```

**Effort**: 1hr

---

**Sprint 4 Demo**:
1. Load Jarvis
2. Press A → Approves (toast shows)
3. Press N → Next draft
4. Press ? → Help overlay shows
5. Open http://localhost:8000/api/voice-approval/analytics
6. See command counts and success rate

**Sprint 4 Complete**: ✅ Advanced features functional

---

# BACKLOG (Future Work)

Not part of core "draft preview" feature - defer to later:

1. **Section Extraction**: "Read the first paragraph" using GPT-4
2. **Recipient Context**: HubSpot integration for contact history
3. **Batch Approval**: "Approve next 5 drafts" workflow
4. **Mobile Responsiveness**: iOS/Android optimization
5. **Voice Editing**: "Change subject to X" commands
6. **Multi-language TTS**: Spanish, French support

---

# VALIDATION CHECKLIST

## Pre-Implementation
- [ ] All test files created (Sprint 0)
- [ ] Config added (Sprint 0)
- [ ] Rate limiting tested (Sprint 0)

## Sprint 1A (Basic TTS)
- [ ] speakResponse() callable
- [ ] Mute toggle works
- [ ] Browser compatibility check shows warnings
- [ ] Full draft body returned from API
- [ ] "Read Draft" button functional

## Sprint 1B (Auto-Summary)
- [ ] GPT-4 summary generates
- [ ] Error handling with fallback works
- [ ] _next_item() includes spoken_intro
- [ ] Status endpoint returns summary
- [ ] Auto-read on load functional
- [ ] Loading spinner shows

## Sprint 2 (Voice Commands)
- [ ] Detail levels work (subject/preview/full)
- [ ] Command parser extracts detail_level
- [ ] Spoken responses generated
- [ ] End-to-end voice commands work

## Sprint 3 (Visual Polish)
- [ ] Calendar link detection works
- [ ] Links highlighted in UI
- [ ] Badge shows correct status
- [ ] Metadata enrichment added
- [ ] Metadata displays in UI

## Sprint 4 (Advanced)
- [ ] Keyboard shortcuts work
- [ ] Help overlay toggles
- [ ] Analytics tracking events
- [ ] Analytics endpoint returns data

## Post-Implementation
- [ ] All tests passing: `pytest tests/ -v`
- [ ] No console errors in browser
- [ ] Works in Chrome, Firefox, Safari
- [ ] Production deployment successful
- [ ] User acceptance testing complete

---

# COMMIT STRATEGY

**Sprint 0**:
```bash
git add tests/test_*.py
git commit -m "test: Create test file structure with fixtures"

git add src/config.py
git commit -m "config: Add TTS configuration settings"

git add src/utils/gpt_helpers.py tests/test_rate_limiting.py
git commit -m "feat: Add GPT-4 rate limiting utility"
```

**Sprint 1A**:
```bash
git add src/static/jarvis.html
git commit -m "feat(tts): Add speakResponse() function with Web Speech API"

git add src/static/jarvis.html
git commit -m "feat(tts): Add mute toggle button"

git add src/static/jarvis.html
git commit -m "feat(tts): Add browser compatibility check"

git add src/voice_approval.py
git commit -m "feat(api): Return full draft body in status endpoint"

git add src/static/jarvis.html
git commit -m "feat(ui): Add Read Draft button with TTS integration"
```

**Sprint 1B**:
```bash
git add src/voice_approval.py tests/test_voice_summary.py
git commit -m "feat(voice): Add GPT-4 powered summary generation"

git add src/voice_approval.py
git commit -m "feat(voice): Add error handling for summary generation"

git add src/voice_approval.py
git commit -m "feat(voice): Update _next_item() to include spoken summary"

git add src/voice_approval.py
git commit -m "feat(api): Return spoken_intro in status endpoint"

git add src/static/jarvis.html
git commit -m "feat(voice): Auto-read summary on draft load"

git add src/static/jarvis.html
git commit -m "feat(ui): Add loading state spinner"
```

**Sprint 2**:
```bash
git add src/voice_approval.py tests/test_detail_levels.py
git commit -m "feat(voice): Add detail level parameter to _get_item_details()"

git add src/voice_approval.py tests/test_command_parsing.py
git commit -m "feat(voice): Update command parser with detail hints"

git add src/voice_approval.py
git commit -m "feat(voice): Generate spoken responses for detail levels"

git add src/routes/voice_approval_routes.py
git commit -m "feat(api): Wire up voice input to detail levels"
```

**Sprint 3**:
```bash
git add src/voice_approval.py tests/test_calendar_detection.py
git commit -m "feat(calendar): Add calendar link detection method"

git add src/static/jarvis.html
git commit -m "feat(ui): Highlight calendar links in green"

git add src/static/jarvis.html
git commit -m "feat(ui): Add calendar status badge"

git add src/voice_approval.py
git commit -m "feat(api): Add draft metadata enrichment"

git add src/static/jarvis.html
git commit -m "feat(ui): Display metadata in draft view"
```

**Sprint 4**:
```bash
git add src/static/jarvis.html
git commit -m "feat(shortcuts): Add core keyboard shortcuts (A/R/N/Space)"

git add src/static/jarvis.html
git commit -m "feat(ui): Add keyboard help overlay"

git add src/routes/voice_approval_routes.py
git commit -m "feat(analytics): Add voice command event tracking"

git add src/routes/voice_approval_routes.py
git commit -m "feat(api): Add analytics endpoint"
```

**Each commit**:
- Is atomic (one clear change)
- Has descriptive message
- Passes tests (or adds tests)
- Is independently deployable

---

# SUCCESS METRICS

**Week 1 (Post Sprint 1)**:
- TTS adoption rate: >70% of users use voice
- Auto-read success rate: >95%
- Average approval time: <5 seconds

**Week 4 (Post Sprint 4)**:
- Voice command usage: >50 commands/day
- Command success rate: >90%
- Keyboard shortcut usage: >30%
- Average approval time: <3 seconds

**Cost Metrics**:
- GPT-4 calls: <100/day
- Average cost per approval: <$0.02
- Rate limit violations: 0

---

**SPRINT PLAN COMPLETE** ✅

Total: 28 atomic, testable, committable tasks across 6 sprints.

Ready to begin Sprint 0.
