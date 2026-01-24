---
name: reviewCode
description: Review code changes following CaseyOS standards
---
Review the provided code changes against CaseyOS standards:

## Review Checklist

### 1. Atomicity & Scope
- [ ] Single intent per change
- [ ] Small diff, tight blast radius
- [ ] No "while I'm here" additions
- [ ] Clear commit message

### 2. Code Quality
- [ ] Type hints on all function signatures
- [ ] Docstrings on public functions/classes
- [ ] No bare `except:` clauses
- [ ] Uses `async with get_session()` for DB
- [ ] No global mutable state

### 3. Security
- [ ] No secrets/credentials in code
- [ ] CSRF token required on state-changing endpoints
- [ ] Admin auth required on sensitive endpoints
- [ ] Input validation present
- [ ] SQL injection prevention (use ORM)

### 4. Error Handling
- [ ] Specific exceptions caught (not bare except)
- [ ] Errors logged with context
- [ ] Appropriate HTTP status codes
- [ ] User-friendly error messages

### 5. Observability
- [ ] Logging at key decision points
- [ ] Extra context in log messages
- [ ] Telemetry events for important actions
- [ ] trace_id correlation used

### 6. Testing
- [ ] Unit tests for new logic
- [ ] Integration tests for workflows
- [ ] Edge cases covered
- [ ] Mocks used appropriately

### 7. Documentation
- [ ] Inline comments for complex logic
- [ ] API docs updated if endpoints change
- [ ] README updated if setup changes

## Common Issues to Flag

| Issue | Severity | Suggestion |
|-------|----------|------------|
| Missing type hints | Medium | Add `-> ReturnType` |
| Hardcoded values | Medium | Move to config.py |
| No input validation | High | Add validate_input() |
| Global DB session | Critical | Use context manager |
| Missing CSRF | Critical | Add verify_csrf_token |
| Bare except | Medium | Catch specific exceptions |
| No logging | Low | Add logger.info/error |

## Approval Criteria
- [ ] All Critical issues resolved
- [ ] All High issues resolved or justified
- [ ] No obvious security vulnerabilities
- [ ] Tests pass
