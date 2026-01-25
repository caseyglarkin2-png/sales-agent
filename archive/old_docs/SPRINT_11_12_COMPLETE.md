# Sprint 11-12 Complete: CaseyOS Dashboard + GTM Domain Expansion

**Date:** January 24, 2026  
**Status:** ✅ COMPLETE  
**Commits:**
- `97fa05e`: feat(Sprint 11-12): CaseyOS Dashboard + GTM Domain Expansion
- `2ac8aae`: fix: Update CaseyOS static asset paths to use /caseyos/* routes

---

## Executive Summary

Sprint 11-12 transforms the Sales Agent into a unified **CaseyOS GTM Command Center**. The dashboard provides a single pane of glass for all "Today's Moves" across Sales, Marketing, and Customer Success domains.

**Key Deliverables:**
1. **CaseyOS Dashboard** - Full-featured command center UI with dark mode, keyboard shortcuts, and real-time updates
2. **GTM Domain Expansion** - New `domain` field with Marketing and CS action types
3. **Domain Filtering** - API and UI support for filtering by Sales/Marketing/CS

---

## Live URLs

| Resource | URL |
|----------|-----|
| **CaseyOS Dashboard** | https://web-production-a6ccf.up.railway.app/caseyos |
| **CaseyOS Health** | https://web-production-a6ccf.up.railway.app/caseyos/health |
| **Today's Moves API** | https://web-production-a6ccf.up.railway.app/api/command-queue/today |
| **Sales Moves** | https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=sales |
| **Marketing Moves** | https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=marketing |
| **CS Moves** | https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=cs |

---

## Sprint 11: Dashboard Transformation

### Goal
Replace the sales-agent dashboard with a unified CaseyOS command center that serves as Casey's Chief of Staff interface.

### Files Created

#### 1. `src/static/caseyos/index.html`
Main dashboard HTML with the following components:

**Header**
- CaseyOS branding with theme toggle
- Domain tabs: All | Sales | Marketing | CS
- Health indicator (green/red dot)

**Stats Row**
- Pending count
- Completed today
- Reply rate
- Net impact score
- Signals processed

**Main Content - Today's Moves**
- Priority-ranked list of action items
- Each item shows:
  - Priority badge (color-coded by score)
  - Action type icon
  - Title and reasoning
  - Due date
  - Action buttons (Execute, Dismiss)
- Domain-based filtering

**Sidebar Widgets**
- **Recent Signals** - Latest ingested signals with source icons
- **Execution History** - Recent actions with status
- **Quick Actions** - Refresh, Seed Queue, Kill Switch
- **Conversion Funnel** - Visual funnel chart

**Execute Modal**
- Dry-run preview
- Confirmation before execution
- Loading states
- Error handling

#### 2. `src/static/caseyos/styles.css`
Complete styling system:

```css
/* CSS Custom Properties for Theming */
:root {
    --bg-primary: #f8fafc;
    --text-primary: #1e293b;
    --accent: #3b82f6;
    /* ... 20+ variables */
}

[data-theme="dark"] {
    --bg-primary: #0f172a;
    --text-primary: #f1f5f9;
    /* ... dark mode overrides */
}
```

**Features:**
- Dark mode via `[data-theme="dark"]`
- Responsive breakpoints (1200px, 768px)
- Priority badge colors (green/yellow/orange/red by score)
- Widget cards with hover states
- Modal animations
- Toast notification styles
- Loading skeleton animations

#### 3. `src/static/caseyos/app.js`
JavaScript application layer:

**API Integration**
- Fetches from `/api/command-queue/today`
- Fetches from `/api/signals`
- Fetches from `/api/outcomes/stats`
- Posts to `/api/command-queue/{id}/accept`
- Posts to `/api/command-queue/{id}/dismiss`
- Posts to `/api/command-queue/{id}/execute`

**Keyboard Shortcuts**
| Key | Action |
|-----|--------|
| `A` | Accept selected item |
| `D` | Dismiss selected item |
| `E` | Execute selected item (opens modal) |
| `R` | Refresh all widgets |
| `j` | Select next item |
| `k` | Select previous item |
| `?` | Show keyboard shortcuts help |

**Features**
- 30-second auto-refresh
- Domain tab filtering
- Dark mode toggle with localStorage persistence
- Toast notifications for feedback
- Execute modal with dry-run preview
- Error boundary handling
- Loading states for all widgets

#### 4. `src/routes/caseyos_ui.py`
FastAPI routes for serving the dashboard:

```python
@router.get("/caseyos", response_class=HTMLResponse)
async def caseyos_dashboard()

@router.get("/caseyos/styles.css", response_class=Response)
async def caseyos_styles()

@router.get("/caseyos/app.js", response_class=Response)
async def caseyos_app()

@router.get("/caseyos/health")
async def caseyos_health()
```

### Sprint 11 Validation

```bash
# Dashboard loads
curl -s -o /dev/null -w "%{http_code}" https://web-production-a6ccf.up.railway.app/caseyos
# Expected: 200

# Health check
curl -s https://web-production-a6ccf.up.railway.app/caseyos/health | jq
# Expected: {"status": "ok", "dashboard": "caseyos"}

# CSS loads
curl -s -o /dev/null -w "%{http_code}" https://web-production-a6ccf.up.railway.app/caseyos/styles.css
# Expected: 200

# JS loads
curl -s -o /dev/null -w "%{http_code}" https://web-production-a6ccf.up.railway.app/caseyos/app.js
# Expected: 200
```

---

## Sprint 12: GTM Domain Expansion

### Goal
Expand CaseyOS beyond sales outreach to support Marketing Ops and Customer Success workflows.

### Model Updates (`src/models/command_queue.py`)

**New DomainType Enum:**
```python
class DomainType(str, Enum):
    SALES = "sales"
    MARKETING = "marketing"
    CS = "cs"
```

**Updated CommandQueueItem:**
```python
class CommandQueueItem(Base):
    # ... existing fields ...
    domain: Mapped[DomainType] = mapped_column(
        SQLAlchemyEnum(DomainType),
        default=DomainType.SALES,
        index=True
    )
```

**New Action Types:**

| Domain | Action Type | Description |
|--------|-------------|-------------|
| Marketing | `content_repurpose` | Transform content into social posts |
| Marketing | `social_post` | Schedule social media post |
| Marketing | `newsletter_draft` | Draft newsletter content |
| Marketing | `asset_create` | Create new marketing asset |
| CS | `cs_health_check` | Customer health assessment |
| CS | `renewal_outreach` | Renewal reminder outreach |
| CS | `risk_escalation` | Escalate at-risk customer |
| CS | `onboarding_follow_up` | New customer follow-up |

### API Updates (`src/routes/command_queue.py`)

**New `/today` Endpoint:**
```python
@router.get("/today", response_model=TodayMovesResponse)
async def get_todays_moves(
    limit: int = Query(10, ge=1, le=50),
    domain: Optional[str] = Query(None, regex="^(sales|marketing|cs)$"),
    db: AsyncSession = Depends(get_async_db)
)
```

**Domain Filtering:**
- `GET /api/command-queue/today` - All domains
- `GET /api/command-queue/today?domain=sales` - Sales only
- `GET /api/command-queue/today?domain=marketing` - Marketing only
- `GET /api/command-queue/today?domain=cs` - CS only

**Updated Response Schema:**
```python
class CommandQueueItemResponse(BaseModel):
    id: str
    priority_score: float
    action_type: str
    action_context: dict
    status: str
    owner: Optional[str]
    due_by: Optional[datetime]
    domain: str  # NEW
    aps_score: float  # NEW (alias for priority_score)
    reasoning: Optional[str]
    created_at: datetime
```

### Migration (`infra/migrations/versions/20260124_*_add_domain_to_command_queue.py`)

```python
def upgrade():
    # Add domain column with default 'sales'
    op.add_column(
        'command_queue_items',
        sa.Column('domain', sa.String(20), nullable=False, server_default='sales')
    )
    # Create index for domain filtering
    op.create_index('ix_command_queue_items_domain', 'command_queue_items', ['domain'])

def downgrade():
    op.drop_index('ix_command_queue_items_domain', table_name='command_queue_items')
    op.drop_column('command_queue_items', 'domain')
```

### Sprint 12 Validation

```bash
# All domains
curl -s https://web-production-a6ccf.up.railway.app/api/command-queue/today | jq '.today_moves | length'

# Sales only
curl -s "https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=sales" | jq '.today_moves[0].domain'
# Expected: "sales"

# Marketing only
curl -s "https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=marketing" | jq

# CS only
curl -s "https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=cs" | jq

# Verify domain in response
curl -s https://web-production-a6ccf.up.railway.app/api/command-queue/today | jq '.today_moves[0] | {id, domain, action_type, aps_score}'
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  CaseyOS Dashboard (/caseyos)                                       │
│  ├── index.html (structure)                                         │
│  ├── styles.css (theming + responsive)                              │
│  └── app.js (API calls + interactivity)                             │
├─────────────────────────────────────────────────────────────────────┤
│  FastAPI Routes                                                      │
│  ├── GET /caseyos              → Dashboard HTML                     │
│  ├── GET /caseyos/styles.css   → CSS                                │
│  ├── GET /caseyos/app.js       → JavaScript                         │
│  ├── GET /caseyos/health       → Health check                       │
│  ├── GET /api/command-queue/today?domain=X → Filtered moves         │
│  └── POST /api/command-queue/{id}/execute  → Execute action         │
├─────────────────────────────────────────────────────────────────────┤
│  Domain Models                                                       │
│  ├── DomainType: SALES | MARKETING | CS                             │
│  └── CommandQueueItem.domain (indexed)                              │
├─────────────────────────────────────────────────────────────────────┤
│  Action Types by Domain                                              │
│  ├── SALES: send_email, create_task, schedule_meeting               │
│  ├── MARKETING: content_repurpose, social_post, newsletter_draft    │
│  └── CS: cs_health_check, renewal_outreach, risk_escalation         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Keyboard Shortcuts Reference

| Key | Action | Notes |
|-----|--------|-------|
| `A` | Accept selected item | Requires item selection |
| `D` | Dismiss selected item | Requires item selection |
| `E` | Execute selected item | Opens modal with dry-run |
| `R` | Refresh all widgets | Immediate refresh |
| `j` | Select next item | Vim-style navigation |
| `k` | Select previous item | Vim-style navigation |
| `?` | Show shortcuts help | Toggle help overlay |
| `Esc` | Close modal | Also clears selection |

---

## Dark Mode

Toggle dark mode using:
1. Click the theme toggle button in the header
2. Preference saved to `localStorage`
3. Persists across sessions

CSS uses `[data-theme="dark"]` selector for overrides.

---

## Acceptance Criteria ✅

### Sprint 11: Dashboard
- [x] CaseyOS dashboard accessible at `/caseyos`
- [x] Header with domain tabs (All/Sales/Marketing/CS)
- [x] Health indicator shows system status
- [x] Stats row displays key metrics
- [x] Today's Moves widget loads from API
- [x] Recent Signals widget loads from API
- [x] Execution History widget loads from API
- [x] Quick Actions panel functional
- [x] Execute modal with dry-run preview
- [x] Keyboard shortcuts (A/D/E/R/j/k)
- [x] 30-second auto-refresh
- [x] Dark mode toggle
- [x] Responsive design (mobile-friendly)
- [x] Toast notifications for feedback

### Sprint 12: GTM Expansion
- [x] DomainType enum (SALES, MARKETING, CS)
- [x] domain field added to CommandQueueItem
- [x] Migration adds domain column with index
- [x] /today endpoint supports ?domain= filter
- [x] Marketing action types added
- [x] CS action types added
- [x] Domain tabs in dashboard work
- [x] Response includes domain and aps_score fields

---

## Demo Script

```bash
# 1. Open CaseyOS Dashboard
open https://web-production-a6ccf.up.railway.app/caseyos

# 2. Check health
curl -s https://web-production-a6ccf.up.railway.app/caseyos/health | jq
# {"status": "ok", "dashboard": "caseyos"}

# 3. Get Today's Moves
curl -s https://web-production-a6ccf.up.railway.app/api/command-queue/today | jq '.today_moves | length'

# 4. Filter by Marketing
curl -s "https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=marketing" | jq

# 5. Filter by CS
curl -s "https://web-production-a6ccf.up.railway.app/api/command-queue/today?domain=cs" | jq

# 6. Test keyboard shortcuts in browser
# - Press 'j' to select next item
# - Press 'k' to select previous item
# - Press 'E' to open execute modal
# - Press 'R' to refresh
# - Press '?' to see shortcuts

# 7. Toggle dark mode
# - Click sun/moon icon in header
```

---

## Known Limitations

1. **No persistent selection** - Keyboard selection resets on refresh
2. **Domain seeding** - Manual seeding needed for Marketing/CS items
3. **Execution handlers** - Marketing/CS handlers return mock responses pending full implementation
4. **Mobile keyboard shortcuts** - Not applicable on touch devices

---

## Next Steps

### Immediate
1. Seed sample Marketing and CS items for demo
2. Wire Marketing action handlers to OpenAI for content generation
3. Wire CS action handlers to HubSpot for customer data

### Future Sprints
- Real-time WebSocket updates (replace polling)
- Browser notifications for high-priority items
- Widget collapse/expand persistence
- Custom dashboard layouts

---

## Files Changed Summary

| File | Change |
|------|--------|
| `src/static/caseyos/index.html` | Created - Dashboard HTML |
| `src/static/caseyos/styles.css` | Created - Full CSS with dark mode |
| `src/static/caseyos/app.js` | Created - JavaScript application |
| `src/routes/caseyos_ui.py` | Created - FastAPI routes |
| `src/models/command_queue.py` | Updated - Added DomainType, domain field |
| `src/routes/command_queue.py` | Updated - Added /today endpoint, domain filter |
| `src/main.py` | Updated - Registered caseyos_ui router |
| `infra/migrations/versions/20260124_*.py` | Created - Domain migration |

---

**Sprint 11-12 Complete. CaseyOS is ready for GTM operations.**
