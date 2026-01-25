
# Sales Agent (CaseyOS) Copilot Instructions

**Vision:** Autonomous GTM Command Center. "Dude What's The Bid?!" Execution Engine.
**Stack:** FastAPI (Async), PostgreSQL (SQLAlchemy+pgvector), Redis/Celery, Railway.

## 1. Architecture & Data Flow
- **Orchestrator Layer (`src/agents/jarvis.py`)**: Master router (`Jarvis`) directs intents to Domains (`Sales`, `Content`, `Research`).
- **Data Layer**:
  - `CommandQueueItem`: Prioritized actions (APS Score: Revenue > Urgency > Effort).
  - `ContentMemory` (`src/models/content.py`): Vector store for YouTube/Drive transcripts (Sprint 23).
- **Connector Layer**:
  - `YoutubeConnector` (`src/connectors/youtube.py`): Ingests video -> Text. **Pattern**: Sync lib wrapped in `run_in_executor`.
  - `GmailConnector`: OAuth-based draft/send.
- **Wiring**: All routes must be explicitly mounted in `src/main.py`.

## 2. Key Development Conventions
- **Async Database (CRITICAL)**: Always use `async with get_session() as session:`. NEVER usage global `async_session`.
  ```python
  from src.db import get_session
  async with get_session() as session:
      result = await session.execute(select(Model))
  ```
- **Sync-to-Async Wrapper**: For blocking I/O (e.g., `youtube_transcript_api`), wrap to keep FastAPI loop alive.
  ```python
  # src/connectors/youtube.py pattern
  transcript = await asyncio.get_running_loop().run_in_executor(None, lambda: sync_func())
  ```
- **Dependency Discipline**: Prefer light logic (Regex/httpx) over heavy deps (BeautifulSoup) for simple extraction.
- **Agent Pattern**: Extend `BaseAgent` (`src/agents/base.py`). Implement `validate_input` + `execute`.

## 3. Essential Workflows
- **Running Stack**: `make docker-up` (Postgres + Redis + API).
- **Migrations**: `python run_migrations.py` (Do not run raw alembic).
- **Testing**:
  - Integration: `pytest tests/integration/` (Uses `tests/fixtures/seed_data.py`).
  - Validation: `python validate_csrf.py` (Checks 99.6% protection coverage).

## 4. Domain Agent Inventory
| Domain       | Path                      | Key Agents |
|--------------|---------------------------|------------|
| **Sales**    | `src/agents/*.py`         | `Prospecting`, `Nurturing` |
| **Research** | `src/agents/research/`    | `DeepResearch` (Drive+Gemini 1.5) |
| **Content**  | `src/agents/content/`     | `ContentRepurpose` (LinkedIn/Newsletter) |
| **Ops**      | `src/agents/ops/`         | `RevenueOps` |

**Strategic Focus (Sprint 23)**: "Content Engine". Ingesting YouTube -> `ContentMemory` -> Repurposing Agents.
