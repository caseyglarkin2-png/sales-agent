# Build Feature

Implement a complete feature end-to-end.

## Instructions

1. Understand the feature:
   - What problem does it solve?
   - Who uses it? (Casey, system, API consumer)
   - What's the success criteria?

2. Check existing infrastructure:
   - Search for related code that already exists
   - Identify what can be reused
   - List what needs to be built

3. Design the solution:
   - Database models (if needed)
   - API endpoints
   - Business logic
   - UI components (if needed)

4. Build it:
   - Create models/migrations first
   - Then services/business logic
   - Then API routes
   - Then UI
   - Register in `src/main.py`

5. Test it:
   - Verify imports work
   - Test endpoints locally
   - Check edge cases

6. Ship it:
   - Commit with clear message
   - Push to production
   - Verify in production
   - Brief demo of what works

## Patterns to Follow
- Use `async def` for all routes
- Use `get_session()` context manager for DB
- Log with `get_logger(__name__)`
- Emit telemetry with `log_event()`
