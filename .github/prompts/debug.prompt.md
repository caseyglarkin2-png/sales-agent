# Debug Issue

Investigate and fix the issue end-to-end.

## Instructions

1. Reproduce the issue:
   - Check production logs if available
   - Run locally to see error
   - Identify the failing component

2. Trace the problem:
   - Search codebase for relevant code
   - Read the files involved
   - Identify root cause

3. Fix it:
   - Make minimal change to fix
   - Don't refactor unrelated code
   - Add logging if failure was silent

4. Verify:
   - Run relevant tests
   - Test locally with curl/browser
   - Deploy and verify in production

5. Prevent recurrence:
   - Add test if appropriate
   - Add better error handling
   - Update docs if behavior changed

## Common Issues
- Import errors → Check `src/main.py` imports
- 502 errors → Check Railway logs, usually import/startup failure
- CSRF errors → Need token from response headers
- Rate limits → Check `src/rate_limiter.py`
