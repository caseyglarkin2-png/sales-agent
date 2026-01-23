# JARVIS Voice Approval System - Quick Start Guide

## 🎯 Overview

You now have a **Jarvis-style voice approval interface** for human-in-the-loop workflows! Just like Tony Stark's AI assistant, you can use voice commands to review and approve agent outputs (email drafts, campaigns, etc.).

## ✅ What's Complete

1. **Voice Approval Engine** - Full natural language command parsing
2. **JARVIS Web Interface** - Beautiful UI with voice & text input
3. **API Routes** - RESTful endpoints for all approval actions
4. **Email Draft Integration** - Currently generating 535 personalized emails
5. **Multi-Modal Input** - Voice, text, or button clicks

## 🚀 Quick Start

### 1. The server is already running (started earlier)

### 2. Load Email Drafts into JARVIS (once generation completes)

```bash
python /workspaces/sales-agent/scripts/load_drafts_to_jarvis.py
```

This will:
- Load all 535 generated email drafts
- Add them to the JARVIS approval queue
- Display next steps

### 3. Open JARVIS Interface

Visit: **http://localhost:8000/jarvis**

## 🎙️ Voice Commands

JARVIS understands natural language. Try:

### Approval Commands
- "Approve this email"
- "Looks good, send it"
- "Yes, approve"
- "This one is perfect"

### Rejection Commands
- "Reject this"
- "No, skip this one"
- "This doesn't work"
- "Reject and tell me why"

### Navigation Commands
- "Next"
- "Show me the next one"
- "Skip this"
- "What's next?"

### Editing Commands
- "Change the subject line to 'Quick question about logistics'"
- "Make the tone more casual"
- "Edit the first paragraph"
- "Update the company name to 'ABC Corp'"

### Bulk Commands
- "Approve all"
- "Approve everything for Bristol Myers Squibb"
- "Reject all the drafts from yesterday"

### Information Commands
- "Why was this created?"
- "Show me more details"
- "What's the context?"
- "Tell me about this contact"

## 💡 How It Works

### Voice Processing Flow

1. **You speak** → Microphone captures audio
2. **Whisper API** → Transcribes speech to text
3. **GPT-4** → Parses natural language into structured command
4. **Action Execution** → Performs approve/reject/edit/etc.
5. **GPT-4** → Generates natural spoken response
6. **JARVIS responds** → Text displayed (and can be synthesized to audio)

### Command Understanding

JARVIS uses GPT-4 to understand context:
- "this" refers to current item
- "all" or "everything" triggers bulk actions
- Company/contact names are extracted intelligently
- Edits are parsed into structured field updates

## 🔧 API Endpoints

All available at `/api/voice-approval/`:

### Voice Input
```bash
# Text input
POST /api/voice-approval/voice-input
{
  "text": "Approve this email"
}

# Audio input
POST /api/voice-approval/voice-input/audio
Form data: audio file (MP3, WAV, WebM)
```

### Queue Management
```bash
# Add single email draft
POST /api/voice-approval/add-email-draft
{
  "draft_id": "unique_id",
  "to_email": "john@example.com",
  "to_name": "John Doe",
  "subject": "...",
  "body": "...",
  "context": {...}
}

# Bulk add drafts
POST /api/voice-approval/bulk-add-drafts
[{...}, {...}, ...]

# Get status
GET /api/voice-approval/status

# Clear queue
POST /api/voice-approval/clear-queue
```

## 📊 Current Status

**Email Drafts**: Generating 535 personalized emails for CHAINge NA contacts
- Progress: ~97/535 complete (18%)
- Success rate: 100%
- Estimated completion: 30-40 minutes from now

Once complete:
1. Run `load_drafts_to_jarvis.py`
2. Open `/jarvis` interface
3. Start reviewing with voice!

## 🎨 UI Features

The JARVIS interface includes:

1. **Voice Button** - Click to record, click again to process
2. **Text Input** - Type commands if you prefer
3. **Quick Commands** - Pre-set buttons for common actions
4. **Current Item Display** - Full email preview with formatting
5. **Queue Status** - Real-time pending count and progress
6. **Action Buttons** - Approve/Reject/Next buttons
7. **JARVIS Response** - Conversational AI feedback
8. **Conversation History** - Full transcript of all interactions

## 🔮 Future Enhancements

Easy to add:
- **Text-to-Speech** - Have JARVIS speak responses aloud
- **Agent Integration** - Any agent can submit items for approval
- **Workflow Rules** - Auto-approve based on criteria
- **Mobile Interface** - Review on phone via voice
- **Slack Integration** - Approve via Slack voice messages
- **Multi-User** - Team review and approval workflows
- **Priority Queues** - Urgent items jump to front
- **Approval History** - Track all decisions with reasoning

## 🎯 Example Workflow

**Scenario**: Reviewing 535 CHAINge NA email drafts

1. Open `/jarvis` in browser
2. Click microphone button
3. Say: "Show me the first email"
4. JARVIS displays email to Bristol Myers Squibb about logistics
5. You review the content
6. Say: "Approve this and show me the next one"
7. JARVIS: "Email approved. Moving to the next draft - this one is for Samsung SDS regarding supply chain optimization."
8. Continue through queue...
9. Say: "Approve all remaining drafts for Fortune 500 companies"
10. JARVIS bulk approves matching items

**Result**: Hands-free approval of hundreds of drafts in minutes instead of hours

## 🔐 Integration Points

JARVIS can integrate with ANY agent in your stack that needs human approval:

- **Email Drafters** - Review before sending (✅ Done!)
- **Campaign Agents** - Approve campaign launches
- **Outreach Sequences** - Validate multi-touch sequences
- **Contract Generators** - Review legal documents
- **Proposal Creators** - Approve quotes and proposals
- **Meeting Schedulers** - Confirm calendar invites
- **Content Generators** - Review blog posts, social posts
- **Data Updates** - Confirm CRM changes

Simply call the `/add-item` endpoint from any agent!

## 📝 Code Example: Adding Custom Items

```python
from src.voice_approval import get_voice_approval, ApprovalItem

# Get JARVIS instance
jarvis = get_voice_approval()

# Add custom item for approval
item = ApprovalItem(
    id="campaign_launch_001",
    type="campaign_launch",
    title="Q1 2026 Product Launch Campaign",
    content={
        "campaign_name": "New Product Reveal",
        "target_audience": "Enterprise SaaS buyers",
        "email_count": 5,
        "budget": "$50,000",
        "start_date": "2026-02-01"
    },
    context={
        "created_by": "campaign_agent",
        "estimated_reach": 10000,
        "expected_conversion": "3-5%"
    },
    agent_source="campaign_planner_v2",
    priority="high"
)

jarvis.add_item(item)
```

Then use voice to approve:
- "Show me the campaign launch"
- "What's the budget?" 
- "Approve the launch"

## 🎉 You're All Set!

Your sales agent now has a **voice-enabled, AI-powered approval interface** just like Jarvis from Iron Man. Review and approve work from any agent using natural conversation!

Access JARVIS: **http://localhost:8000/jarvis**

---

**Pro Tip**: Use the mobile browser with voice for a truly hands-free experience. Perfect for reviewing while commuting or multitasking!
