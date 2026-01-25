
# Sales Agent (CaseyOS) Copilot Instructions

**Vision:** Autonomous GTM Command Center. "Dude What's The Bid?!" Execution Engine.
**Stack:** FastAPI (Async), PostgreSQL (SQLAlchemy+pgvector), Redis/Celery, Railway.

## 1. Architecture & Data Flow
- **Orchestrator Layer (`src/agents/jarvis.py`)**: Master router (`Jarvis`) directs intents to Domains (`Sales`, `Content`, `Research`).
- **Data Layer**:
  - `CommandQueueItem`: Prioritized actions (APS Score: Revenue > Urgency > Effort).
  - `ContentMemory` (`src/models/content.py`): Vector store for YouTube/Drive transcripts.
  - **Models**: Located in `src/models/*.py`.
- **Connector Layer**:
  - `YoutubeConnector`: Sync lib wrapped in `run_in_executor`.
  - `SlackConnector`: Uses `AsyncWebClient` for internal comms ingestion.
  - `GmailConnector`: OAuth-based draft/send.
- **Wiring**: All routes must be explicitly mounted in `src/main.py`.

## 2. Key Development Conventions (CRITICAL)

### Database Compatibility (Postgres vs SQLite)
**ALWAYS** use `SafeJSON` for JSON fields to support both Production (Postgres/JSONB) and Tests (SQLite/JSON).
```python
from src.db import Base, SafeJSON
from sqlalchemy.orm import Mapped, mapped_column

class MyModel(Base):
    # BAD: data = Column(JSONB) -> Crashes tests
    # GOOD:
    data: Mapped[dict] = mapped_column(SafeJSON, default=dict)
```

### Async Database Access
**ALWAYS** use `async with get_session() as session:`. NEVER use global `async_session` directly.
```python
from src.db import get_session
async with get_session() as session:
    result = await session.execute(select(Model))
    await session.commit()
```

### Sync-to-Async Wrapper
For blocking I/O libs (e.g., `youtube_transcript_api`), wrap to keep FastAPI loop alive.
```python
result = await asyncio.get_running_loop().run_in_executor(None, lambda: sync_func())
```

## 3. Essential Workflows
- **Running Stack**: `make docker-up` (Postgres + Redis + API).
- **Migrations**: `python run_migrations.py` (Do not run raw alembic).
- **Deployment Verification**:
  - Run `python scripts/verify_ui.py` to check production health (200 OK on assets).
- **Testing**:
  - Unit: `make test-unit` (runs `pytest tests/unit`).
  - Integration: `pytest tests/integration/`. Setup: `tests/fixtures/seed_data.py`.

## 4. Domain Agent Inventory
| Domain       | Path                      | Type | Key Agents |
|--------------|---------------------------|------|------------|
| **Sales**    | `src/agents/*.py`         | Module | `Prospecting`, `Nurturing` |
| **Research** | `src/agents/research/`    | Package | `DeepResearch` (Gemini 1.5 + Drive), `StandardResearch` |
| **Content**  | `src/agents/content/`     | Package | `ContentRepurpose` (YouTube -> LinkedIn/Newsletter) |
| **Ops**      | `src/agents/ops/`         | Package | `RevenueOps` |

## 5. Deployment Checklist
1. Update `requirements.txt` if adding deps.
2. Push to `main` triggers Railway build.
3. Monitor for "502 Bad Gateway" (Build/Start) -> "200 OK" (Healthy).
4. Run `scripts/verify_ui.py`.
