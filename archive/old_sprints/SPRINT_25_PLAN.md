# Sprint 25: The Nervous System (Interactivity & Data)

**Goal**: Make the Jinja2/HTMX shells "alive" by connecting them to the database and adding dynamic interactions.
**Theme**: "From Static Shell to Command Center."

## Phase 1: API & Data Layer
- [ ] **Task 25.1: Command Queue Service**
    - Create `src/services/queue_service.py` to handle `get_top_items(limit=10)`, `execute_item(id)`, and `dismiss_item(id)`.
    - Ensure it returns `CommandQueueItem` models enriched with Action Priority Scores (APS).

- [ ] **Task 25.2: HTMX Routes**
    - Update `src/routes/ui.py` to handle HTMX requests (headers `HX-Request: true`).
    - Create endpoints that return *HTML fragments* (partials) instead of full pages when requested via HTMX.
        - `GET /caseyos/queue/list` -> Returns `<tr>...</tr>` rows.
        - `POST /caseyos/queue/{id}/execute` -> Returns updated row or success toast.

## Phase 2: Frontend Implementation
- [ ] **Task 25.3: Alive Command Queue**
    - Update `src/templates/queue.html` to accept a `queue_items` list.
    - Loop through items and render them server-side.
    - Add `hx-post` to the "Execute" button to trigger the action without page reload.
    - Add standard "Flash/Toast" support for success messages.

- [ ] **Task 25.4: Dashboard Stats**
    - Inject real stats (Emails Sent, Queue Depth) into `src/templates/dashboard.html` context.
    - (Optional) Add `hx-trigger="every 10s"` polling for the "Active Agents" counter.

## Phase 3: Cleanup
- [ ] **Task 25.5: Legacy Route Removal**
    - Delete `src/routes/ui_command_queue.py` (marked deprecated in Sprint 24).
    - Delete `src/routes/caseyos_ui.py` (legacy SPA router).

## Definition of Done
1.  `/caseyos/queue` shows real data from the DB.
2.  Clicking "Execute" works without a full page refresh (Optimistic UI/Toast).
3.  Dashboard shows at least one real metric from the DB.
4.  Legacy UI routes are deleted.
