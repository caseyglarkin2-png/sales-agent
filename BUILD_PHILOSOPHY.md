# Build Philosophy (Agent Command Style)

**Owner:** Casey Larkin — Founder, Dude, What's The Bid??! LLC  
**Last Updated:** January 23, 2026

---

## The Law

**Atomic tasks. Clear validation. Demoable sprints. Ship early, ship often. No drama.**  
If your plan violates this, it's not "close." It's wrong.

---

## Core Tenants

### 0) Ship Ship Ship 🚢

**Deploy features the moment they're ready. Test in production.**

- ✅ Push live as soon as feature passes validation
- ✅ Use subagents to test UI/UX in production environment
- ✅ Discover bugs and optimizations through real usage
- ✅ Iterate based on production feedback, not speculation
- ❌ Don't wait for "perfect" - ship working code, improve iteratively

**Why:** Bugs found in production with real data > bugs imagined in development. 
Fast feedback loops beat overthinking. Ship it, test it, fix it, repeat.

---

## Non-Negotiables

### 1) Atomic Means Atomic

Every task/ticket must be:
- ✅ **Independently committable** (mergeable in isolation)
- ✅ **Scope-limited** (one intent, small diff, tight blast radius)
- ✅ **Testable** (automated tests OR explicit manual verification)
- ✅ **Reversible** (rollback plan or obvious reversion)
- ✅ **Readable** (future-us understands it in 30 seconds)

**Good vs Bad**
- ✅ "Add email validation to contact form + unit tests for edge cases"
- ❌ "Improve the form"

---

### 2) Validation First, Then Code

Define success before you write code.

**Validation options:**
- **Automated:** unit / integration / E2E (when worth it)
- **Manual:** curl commands, SQL queries, screenshots/recordings, console checks, perf checks

**Rule:** If you can't explain how we verify it, you can't ship it.

---

### 3) Demoable Sprints Only

Every sprint ships something that is:
- ✅ Runnable
- ✅ Visible
- ✅ Extends prior work
- ✅ Production-grade (no half-features, no commented-out "someday" code)

**Sprint Demo Gate**
- Deploy works
- New capability works end-to-end
- Regression checks complete
- No unowned performance regressions
- Docs updated

---

### 4) Big Goal, Small Tasks

Sprint goals are big. Tasks are small.

**Allowed:**
- "Google Workspace Integration"
- "Meeting booking pipeline with dedupe + audit trail"

**Required task behavior:**
- Each task maps to the sprint goal
- No "misc" buckets
- No "various fixes"
- If it matters, name it. If you can't name it, it's not ready.

---

## Definitions (So We Don't Argue About Words)

### Definition of Ready (DoR)

A task is ready when:
- Scope boundaries are explicit ("does" and "does NOT")
- Validation is defined
- Contracts are written (API/schema expectations)
- Rollback path exists
- Dependencies are listed (or explicitly none)

### Definition of Done (DoD)

A task is done when:
- PR merged to main
- Validation completed and documented
- Observability added where failure can hide (logs/metrics)
- Docs updated (README / /docs / inline)
- Rollback is credible and documented

---

## Task Spec Template (Use This)

```markdown
### Task X.Y: [Atomic Task Name]

**Priority:** CRITICAL/HIGH/MEDIUM/LOW  
**Dependencies:** [IDs] or "None"

**One-liner:** What this does.

**Scope Boundaries (NOT included):**
- Bullet list of exclusions

**Files:**
- Create: path/to/new-file.ts
- Modify: path/to/existing.ts (key sections)

**Contracts:**
- Endpoint(s): METHOD /path
- Request schema:
- Response schema:
- Error codes:

**DB Changes (if any):**
```prisma
// exact schema changes
```

**Implementation Notes:**
- key decisions + why
- edge cases
- failure handling

**Validation:**
```bash
# exact commands
```

**Acceptance Criteria:**
- measurable outcome 1
- measurable outcome 2

**Rollback:**
Revert PR OR disable flag OR undo migration steps
```

---

## Automation Safety Rails (If It Sends / Books / Writes / Triggers)

If your feature touches outreach, booking, enrichment, workflows, or external APIs:

- **Idempotency:** repeats don't duplicate outcomes
- **Rate limits:** protect APIs and reputation
- **Dry-run mode:** simulate without executing
- **Kill switch:** quick disable path
- **Audit trail:** who/what/why for every action

**Rule:** silent failure is a future incident. Design like you hate incidents.

---

## Observability Is a Feature

Add logs/metrics where problems hide:
- outbound email + webhook callbacks
- meeting booking flows
- API retries and backoffs
- data writes + dedupe logic
- auth/token refresh
- background jobs/queues

**If we can't see it, we can't trust it.**

---

## Subagent Review Process (Mandatory for Plans)

1) Write the sprint/task breakdown  
2) Run subagent review  
3) Incorporate feedback  
4) Update the latest `.md` in repo (single source of truth)

**Review Prompt**
```
Review this sprint plan for:
- Are all tasks atomic and independently committable?
- Does each task include explicit validation?
- Is the sprint demoable and production-grade?
- Are scope boundaries explicit?
- Any missing edge cases, failure modes, rollback plans, or observability?

Suggest 3-5 concrete improvements.
```

---

## Sprint Completion Output (What "Complete" Means)

A sprint is complete when:
- ✅ all tasks meet DoD
- ✅ tests/manual validation documented
- ✅ merged to main
- ✅ deployed or otherwise runnable for demo
- ✅ sprint summary recorded (what shipped + notable changes)
- ✅ demo artifact captured (screenshots/short recording/notes)

---

## Casey's Operating Vibe (Yes, This Matters)

We build like closers:
- no vagueness
- no fragile hacks
- no "we'll circle back"
- crisp execution, auditable results

You're working for **Casey Larkin**, Founder of **Dude, What's The Bid??! LLC**.  
That means we ship *clean*, we ship *real*, and we ship *with receipts*.

---

## Quick Checklist

- □ Atomic task
- □ Explicit validation
- □ Rollback path
- □ Demoable sprint output
- □ Observable + auditable
- □ Subagent review done
- □ Repo .md updated

**If all checked → ship it.**  
**If not → refine first.**

---

## File Location

This document lives at the root of the repository: `/BUILD_PHILOSOPHY.md`

All sprint plans, roadmaps, and task breakdowns should reference this philosophy and comply with its standards.
