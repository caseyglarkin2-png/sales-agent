# Sprint 23 Plan: Command Center Activation

**Status:** Planned  
**Focus:** Deep Research & Content Engine ("The Brain")  
**Goal:** Transform CaseyOS into a business-specific command center for "Dude What's The Bid?! LLC".

---

## Strategic Context
We are moving from "Building the Car" (Infrastructure/Henry) to "Driving the Car" (Business Logic).
We will leverage the "treasure trove" of internal data (Drive, Slack, YouTube) to power the agents.

## Task Inventory

### Task 23.1: Deep Research Infrastructure (Gemini 1.5 Pro)
- **Goal:** Enable agents to read massive context (1M+ tokens) from Drive folders.
- **Files:** `src/connectors/gemini.py`, `src/agents/research_deep.py`
- **Action:**
    - [x] Upgrade `GeminiConnector` to support 1.5 Pro via Google AI Studio API.
    - [x] Implement recursive Drive folder reader (filtering for "Pesti", "Yardflow", "Dude").
    - [x] Create `DeepResearchAgent` that accepts a "Research Query" and a "Drive Path".

### Task 23.2: Content Engine - Ingestion (YouTube)
- **Goal:** Ingest "Dude What's The Bid?!" transcripts for training/repurposing.
- **Files:** `src/connectors/youtube.py`
- **Action:**
    - [x] Create `YoutubeConnector` using `youtube-transcript-api` (or Google API).
    - [x] Create ingestion route `POST /api/content/ingest-video`.
    - [x] Store transcripts in `ContentMemory` (new vector collection).

### Task 23.3: Content Engine - Repurposing
- **Goal:** Automate "The Freight Marketer" newsletter draft.
- **Files:** `src/agents/content/repurpose_v2.py`
- **Action:**
    - [x] Create specialized prompt chains for:
        - "LinkedIn Post (Viral/Story)"
        - "Newsletter Section (Insight/News)"
    - [x] Input: YouTube Transcript -> Output: Draft Content.

### Task 23.4: Slack Integration (The "Comms Trove")
- **Goal:** Ingest team communications for context.
- **Files:** `src/connectors/slack.py`
- **Action:**
    - Implement `SlackConnector` using `slack-sdk`.
    - Function: `fetch_channel_history(channel_id, days=30)`.
    - Index history into `MemoryService`.

---

## Execution Order
1. **Gemini 1.5** (Unlocks the "Brain" for large context)
2. **YouTube Ingestion** (Unlocks the source material)
3. **Content Agents** (Unlocks the output)
4. **Slack** (Unlocks the internal context)

## Definition of Done
- [ ] capable of answering specific questions about Pesti/Yardflow contracts from Drive.
- [ ] capable of drafting a newsletter from a provided YouTube URL.
- [ ] Slack history searchable via Jarvis.
