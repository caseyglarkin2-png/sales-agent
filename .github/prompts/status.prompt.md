# Project Status

Get comprehensive status of the CaseyOS project.

## Instructions

1. Check production health:
```bash
curl https://web-production-a6ccf.up.railway.app/health
curl https://web-production-a6ccf.up.railway.app/ready
```

2. Check sprint progress:
   - Read `SPRINT_*_COMPLETE.md` files
   - Check `docs/CASEYOS_SPRINT_ROADMAP.md` for next tasks

3. Check git status:
   - Any uncommitted changes?
   - Any unpushed commits?

4. Check key systems:
```bash
curl https://web-production-a6ccf.up.railway.app/api/command-queue/today
curl https://web-production-a6ccf.up.railway.app/api/signals/health
curl https://web-production-a6ccf.up.railway.app/api/actions/status
```

5. Summarize:
   - Current sprint and task
   - What's working
   - What's next
   - Any blockers

## Output Format
Brief status report with:
- 🟢 Production: UP/DOWN
- 📊 Sprint: X of Y tasks complete
- 🎯 Next: What to work on
- ⚠️ Blockers: Any issues
