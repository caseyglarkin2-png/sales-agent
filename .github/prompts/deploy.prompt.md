# Deploy & Verify

Push current changes to production and verify everything works.

## Instructions

1. Run `python -c "from src.main import app"` to verify imports
2. Run critical tests: `pytest tests/ -x --tb=short -q`
3. Commit all changes with descriptive message
4. Push to main: `git push origin main`
5. Wait 60-90 seconds for Railway deploy
6. Verify production health:
   - `curl https://web-production-a6ccf.up.railway.app/health`
   - `curl https://web-production-a6ccf.up.railway.app/ready`
7. Test the specific feature that was changed
8. Report success or failure

## Production URL
https://web-production-a6ccf.up.railway.app

## Common Endpoints to Verify
- `/health` - Basic health
- `/ready` - DB + Redis readiness
- `/api/command-queue/today` - Today's Moves
- `/api/signals/health` - Signals system
- `/api/actions/status` - Action executor
