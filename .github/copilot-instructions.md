# Sales Agent (CaseyOS) Copilot Instructions

**Vision**: Autonomous B2B GTM Command Center with human operator oversight.
**Stack**: FastAPI (Async), PostgreSQL (SQLAlchemy + pgvector), Redis/Celery, Railway.
**Frontend**: Jinja2 Templates + Tailwind CSS + HTMX (Server-Side Rendering).

## Architecture Overview

```
Webhooks/Signals → SignalService → CommandQueue → Jarvis Orchestrator → Domain Agents
                                                                              ↓
                 UI (Jinja2/HTMX) ← Routes ← Connectors (Gmail, HubSpot, LLM)
```

### Core Components
- **Jarvis** ([src/agents/jarvis.py](src/agents/jarvis.py)): Master orchestrator routes intents to specialized agents
- **Domain Agents** ([src/agents/](src/agents/)): Inherit `BaseAgent`, implement `validate_input()` → `execute()` pattern
- **Command Queue** ([src/models/command_queue.py](src/models/command_queue.py)): Prioritized actions scored by APS (Action Priority Score)
- **Connectors** ([src/connectors/](src/connectors/)): External API integrations (Gmail, HubSpot, LLM, Calendar)
- **Services** ([src/services/](src/services/)): Business logic layer (SignalService, MemoryService, APSCalculator)

### Signal Flow
1. External signals (webhooks, polling) → `src/routes/webhooks.py` → `SignalService`
2. Celery tasks (`src/celery_app.py`) process signals → create `CommandQueueItem`
3. Jarvis routes to appropriate agent → generates draft/action
4. Operator approval required before external sends

## Critical Development Patterns

### Database Access (MUST FOLLOW)
```python
# ALWAYS use SafeJSON for JSON columns (works with Postgres & SQLite)
from src.db import Base, SafeJSON, get_session

class MyModel(Base):
    metadata_field: Mapped[dict] = mapped_column(SafeJSON, default=dict)

# ALWAYS use async context manager
async with get_session() as session:
    result = await session.execute(stmt)
    await session.commit()

# For FastAPI dependencies, use get_db
from src.db import get_db
async def route(db: AsyncSession = Depends(get_db)):
    ...
```

### UI Routes (Server-Side Rendering)
```python
# CORRECT - Use Jinja2Templates (src/routes/ui.py pattern)
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="src/templates")

@router.get("/caseyos/page")
async def page(request: Request):
    return templates.TemplateResponse("page.html", {"request": request, "active_tab": "page"})

# WRONG - Never return raw HTML strings from routes
```

Templates extend `base.html` (includes Tailwind, HTMX, nav). Use HTMX for interactivity.

### Agent Pattern
```python
from src.agents.base import BaseAgent

class MyAgent(BaseAgent):
    def __init__(self, connector=None):
        super().__init__(name="MyAgent", description="...")
        self.connector = connector

    async def validate_input(self, context: dict) -> bool:
        return "required_field" in context

    async def execute(self, context: dict) -> dict:
        # Business logic here
        return {"status": "success", "data": ...}
```

### API Route Pattern
```python
# Thin routes - delegate to services/agents
@router.post("/api/items")
async def create_item(
    payload: ItemCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    service = ItemService(db)
    return await service.create(payload, user_id=user.id)
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `make local-up` | Start full stack (API + Celery + Redis + DB) |
| `make local-down` | Stop local stack |
| `make test-unit` | Fast isolated tests |
| `make test-integration` | Tests requiring DB/Redis |
| `make coverage` | Run with coverage (baseline: 40%) |
| `make lint` | Ruff + Pyright checks |
| `make format` | Auto-format code |

## Project Structure

```
src/
├── agents/           # Business logic (Jarvis, Prospecting, Nurturing, etc.)
├── routes/           # API + UI endpoints (keep thin, delegate to agents/services)
├── models/           # SQLAlchemy models (use SafeJSON for JSON fields)
├── services/         # Core services (SignalService, MemoryService)
├── connectors/       # External APIs (Gmail, HubSpot, LLM, Slack)
├── templates/        # Jinja2 HTML (extend base.html)
├── tasks/            # Celery task definitions
├── db/               # Database utilities and session management
└── config.py         # Pydantic settings (env vars)

tests/
├── unit/             # Fast, isolated tests
├── integration/      # DB/Redis required
└── fixtures/         # Shared test data
```

## Important Files

- [src/db/__init__.py](src/db/__init__.py): `Base`, `SafeJSON`, `get_session`, `get_db`
- [src/config.py](src/config.py): All settings via `get_settings()` (Pydantic)
- [src/celery_app.py](src/celery_app.py): Celery config + beat schedule
- [src/main.py](src/main.py): FastAPI app + all route registrations
- [SPRINT_ROADMAP_V2.md](SPRINT_ROADMAP_V2.md): Master sprint plan (supersedes all others)

## Authentication Patterns

```python
# Protected route - requires valid session, raises 401/403
from src.auth.decorators import get_current_user
@router.get("/api/protected")
async def protected(user: User = Depends(get_current_user)):
    return {"user_id": user.id}

# Optional auth - returns None if not logged in
from src.auth.decorators import get_current_user_optional
@router.get("/api/public")
async def public(user: Optional[User] = Depends(get_current_user_optional)):
    if user:
        return {"message": f"Hello {user.email}"}
    return {"message": "Hello guest"}

# UI route with login redirect
from src.auth.decorators import get_current_user_redirect
@router.get("/caseyos/settings")
async def settings_page(request: Request, user: User = Depends(get_current_user_redirect)):
    return templates.TemplateResponse("settings.html", {"request": request, "user": user})
```

Session uses `caseyos_session` cookie. For dev/test, use `X-User-ID` header.

## External Integrations

### Connectors (`src/connectors/`)
```python
# All connectors use httpx for async HTTP
from src.connectors.hubspot import HubSpotConnector, create_hubspot_connector
connector = create_hubspot_connector()  # Uses HUBSPOT_API_KEY env var
contact = await connector.search_contacts("user@example.com")

from src.connectors.gmail import GmailConnector
from src.connectors.llm import LLMConnector, get_llm
```

### OAuth Token Management (`src/oauth_manager.py`)
- Tokens stored encrypted in `oauth_tokens` table (Fernet encryption)
- Requires `OAUTH_ENCRYPTION_KEY` env var in production
- Auto-refresh via Celery beat task every 30 minutes

## Celery Tasks

### Task Registration Pattern
```python
# In src/tasks/my_task.py
from src.celery_app import celery_app

@celery_app.task(
    name="src.tasks.my_task.do_something",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def do_something(self):
    # Wrap async code
    return _run_async(_do_something_async())

def _run_async(coro):
    """Run async in sync context for Celery."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)
```

### Beat Schedule (in `src/celery_app.py`)
| Task | Schedule | Purpose |
|------|----------|---------|
| `refresh-expiring-oauth-tokens` | 30 min | Token refresh |
| `poll-hubspot-signals` | 5 min | HubSpot deal monitoring |
| `poll-gmail-signals` | 5 min | Email monitoring |
| `daemon-monitor-signals` | 5 min | Proactive signal checks |

## Testing Patterns

### Test Structure - Use Inline Mocks
```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter that allows sends."""
    mock_limiter = AsyncMock()
    mock_limiter.check_can_send.return_value = (True, "OK")
    mock_limiter.record_send = AsyncMock()
    return mock_limiter

@pytest.mark.asyncio
async def test_send_draft(draft_queue, sample_draft, mock_rate_limiter):
    with patch("src.operator_mode.get_rate_limiter", return_value=mock_rate_limiter):
        with patch("src.config.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                allow_real_sends=True,  # CRITICAL: Must include this!
                google_client_id="test_id",
                google_client_secret="test_secret",
            )
            result = await draft_queue.send_draft(...)
```

### Common Test Gotchas
1. **Mock paths must match import location**: Use `src.operator_mode.get_rate_limiter`, not `src.rate_limiter.get_rate_limiter`
2. **Always include `allow_real_sends=True`** when mocking settings for send tests
3. **Use `checkfirst=True`** in `create_all()` to avoid duplicate table errors
4. **Enum comparisons**: Use `.value` when comparing with strings (`status == DraftStatus.SENT.value`)
5. **Body length validation**: Email bodies must be 50+ characters

### Running Tests
```bash
make test-unit          # Fast, isolated (no DB/Redis)
make test-integration   # Requires running services
make coverage           # Check coverage (baseline: 40%)
```

## Deprecations & Warnings

- **DEPRECATED**: `src/routes/ui_command_queue.py`, `caseyos_ui.py` → Use `src/routes/ui.py`
- **DEPRECATED**: Legacy SPA files in `src/static/*.html` → Use Jinja2 templates
- **REMOVED (Sprint 22)**: quotes_routes, forecasts_routes, territories_routes, competitors_routes
- **Coverage baseline**: 40% - Do not decrease
- **Sprint plans**: Use `SPRINT_ROADMAP_V2.md` only (supersedes all previous)

## SQLAlchemy Index Gotcha

When defining indexes, use EITHER `index=True` on the column OR an explicit `Index()` in `__table_args__`, never both:

```python
# WRONG - Causes "duplicate index" errors
class Message(Base):
    gmail_thread_id: Mapped[str] = mapped_column(String, index=True)  # ❌
    __table_args__ = (Index("ix_message_gmail_thread_id", "gmail_thread_id"),)

# CORRECT - Use only one approach
class Message(Base):
    gmail_thread_id: Mapped[str] = mapped_column(String)  # No index=True
    __table_args__ = (Index("ix_message_gmail_thread_id", "gmail_thread_id"),)
```

## CSRF Token Handling

CSRF tokens are injected via `htmx:configRequest` in `base.html`. All HTMX POST/PUT/DELETE requests automatically include the token from cookies. The legacy service worker is automatically unregistered on page load.
