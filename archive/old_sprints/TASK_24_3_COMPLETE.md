# Task 24.3: Command Queue Port Complete

## Summary
The "Command Queue" UI has been successfully ported from a static HTML/JS page to a server-side rendered Jinja2 template.

## Changes
1.  **New Template**: Created `src/templates/queue.html`.
    -   Extends `base.html`.
    -   Includes ported CSS for visual consistency.
    -   Uses HTMX for potential future interactivity (though currently static rendering structure).
2.  **Route Updates**:
    -   Updated `src/routes/ui.py` to serve `@router.get("/caseyos/queue")`.
    -   Deprecated `src/routes/ui_command_queue.py` (legacy raw HTML route).
    -   Updated `src/main.py` to use `ui.router` and remove `ui_command_queue.router` and `caseyos_ui.router`.
3.  **Cleanup**:
    -   Legacy `caseyos_ui.py` (SPA serving) is deprecated in favor of `ui.py` (Jinja2).

## Verification
-   Access `/caseyos/queue` to see the new queue.
-   Access `/caseyos` to see the main dashboard.
