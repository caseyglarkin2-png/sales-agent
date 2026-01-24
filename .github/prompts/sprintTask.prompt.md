---
name: sprintTask
description: Create an atomic sprint task following CaseyOS philosophy
---
Create a sprint task specification following the CaseyOS build philosophy:

## Task Details
- **Task ID**: ${1:Sprint.Task (e.g., 7.4)}
- **Title**: ${2:Atomic Task Name}
- **Priority**: ${3:CRITICAL|HIGH|MEDIUM|LOW}

## Task Specification

### Task ${Task ID}: ${Title}

**Priority:** ${Priority}  
**Dependencies:** ${4:Task IDs or "None"}  
**Effort:** ${5:X hours}

**One-liner:** ${6:What this does in one sentence}

**Scope Boundaries:**

Does include:
- ${7:bullet 1}
- ${8:bullet 2}

Does NOT include:
- ${9:exclusion 1}
- ${10:exclusion 2}

**Files:**
- Create: `${11:path/to/new-file.py}`
- Modify: `${12:path/to/existing.py}` (specific sections)

**Contracts:**
```python
# Define the interface/schema
```

**Implementation Notes:**
- Key decisions and why
- Edge cases to handle
- Failure modes to prevent

**Validation:**
```bash
# Exact commands to verify success
curl -X GET http://localhost:8000/api/...
pytest tests/test_... -v
```

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

**Rollback:**
```bash
# How to undo if something goes wrong
git revert <commit-hash>
# OR
alembic downgrade -1
```

## Philosophy Checklist
- [ ] Atomic: Single intent, independently committable
- [ ] Testable: Automated or explicit manual verification
- [ ] Reversible: Rollback plan exists
- [ ] Observable: Logs/metrics where failure can hide
