# Emergency Fix Report: Deployment Crash & UI Lockout
**Date**: Jan 26, 2026
**Status**: RESOLVED

## Incident Summary
Post-deployment of Sprint 24, two critical issues were identified:
1. **Backend Crash**: Production failed to start (`ModuleNotFoundError: aiohttp`).
2. **UI Lockout**: Users reported "Site not working" due to stale Service Workers from the legacy SPA serving 404/broken assets.

## Resolution Steps

### 1. Backend Stabilization
- **Root Cause**: `slack-sdk` (or similar) required `aiohttp`, which was missing from `requirements.txt`.
- **Fix**: Added `aiohttp>=3.9.0`.
- **Verification**: `/health` endpoint returns 200 OK. Tests passed.

### 2. UI/Cache Remediation (The "Self-Destruct" Protocol)
- **Root Cause**: The old `caseyos-v1` service worker was intercepting requests and serving cached files that no longer exist in the new SSR architecture.
- **Fix Part A (Client-Side)**: Added `src/templates/base.html` script to aggressively `unregister()` any found service workers on load.
- **Fix Part B (Worker-Side)**: Replaced `src/static/sw.js` with a "Killer Worker" that immediately unregisters itself and reloads client tabs.
- **Verification**: `git show HEAD:src/static/sw.js` confirms the new logic is deployed.

### 3. Security Hardening
- **Issue**: HTMX requests were failing CSRF checks (403 Forbidden).
- **Fix**: Added `htmx:configRequest` listener in `base.html` to inject `X-CSRF-Token` header using the `{{ csrf_token }}` Jinja variable.

## Next Steps for Users
1. **Hard Refresh**: Users should press `Ctrl+Shift+R` (Cmd+Shift+R) once to fetch the new `sw.js` killer.
2. **Login**: Normal operation is restored.

## Code Artifacts
- `src/static/sw.js`: [SELF-DESTRUCT LOGIC]
- `src/templates/base.html`: [UNREGISTER SCRIPT + CSRF]
- `requirements.txt`: [+aiohttp]

---
*System is ready for Sprint 25 (Command Queue) execution.*
