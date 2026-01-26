# Sprint 24 Plan: UI/UX Modernization (The "Face")

**Type:** Architecture / Technical Debt
**Focus:** Frontend Architecture, Jinja2 Templating, Design Unification
**Goal:** Replace the fragmented static/SPA hybrid with a unified Server-Side Rendering (SSR) architecture using Jinja2 and Tailwind.

---

## 1. The Problem
- **Fragmentation:** `command-queue.html` (Rich JS) vs `index.html` (Monolith) vs `/api/command-queue` (Python HTML string).
- **Maintenance Cost:** Navigation bar is copy-pasted across 10 files. Updates are impossible.
- **Inconsistency:** Tailwind colors mixed with custom CSS variables.
- **Dead Code:** Old route handlers returning basic HTML tables are conflicting with modern static assets.

## 2. The Solution
We will introduce `fastapi.templating.Jinja2Templates` to serve a unified "Shell".
- **Base Template:** `src/templates/base.html` (Head, Nav, Footer, Scripts).
- **Page Templates:** `src/templates/dashboard.html`, `src/templates/queue.html`.
- **Componentization:** Use Jinja2 `{% include %}` for partials.

## 3. Atomic Task List

### Phase 1: Foundation Setup
- [x] **Task 24.1: Install & Config Jinja2**
  - Add `jinja2` to `requirements.txt`.
  - Create `src/templates/` directory.
  - Create `src/templates/base.html` (The Shell).
  - Define `templates = Jinja2Templates(directory="src/templates")` in `src/routes/ui.py` (new file).

### Phase 2: Dashboard Migration (The Landing Page)
- [x] **Task 24.2: Port Dashboard**
  - Extract body content from `static/jarvis.html` to `src/templates/dashboard.html`.
  - Wire `/caseyos` -> renders `dashboard.html`.
  - Verify all JS/CSS assets load correctly from `/static`.

### Phase 3: Command Queue Unification
- [x] **Task 24.3: Port Command Queue**
  - Extract logic from `static/command-queue.html`.
  - Create `src/templates/queue.html` extending `base.html`.
  - **CRITICAL:** Delete the old route handler in `src/routes/command_queue.py` that returning raw HTML strings.
  - Create standard route `/caseyos/queue` rendering the template.

### Phase 4: Standardization
- [x] **Task 24.4: Navigation & Styles**
  - Standardize the Nav Bar in `base.html`.
  - Ensure Tailwind Config matches established brand colors (Primary: `#4f46e5`).
  - Add "Flash Message" (Toast) container to `base.html`.

### Phase 5: Verification & Cleanup
- [x] **Task 24.5: Cleanup Static Folder**
  - Delete `static/jarvis.html` (legacy).
  - Delete `static/command-queue.html` (legacy).
  - Audit `scripts/verify_ui.py` to check for 200 OK on new routes (`/caseyos`, `/caseyos/queue`).

## 4. Definition of Done
- [x] NO inline HTML strings in Python files.
- [x] NO copy-pasted Navigation bars in HTML files.
- [x] `base.html` exists and is used by at least 2 pages.
- [x] `scripts/verify_ui.py` passes.
- [x] Site looks visually consistent.
