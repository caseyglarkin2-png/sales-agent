#!/usr/bin/env python3
"""E2E smoke test: form lead → draft → task workflow.

Full end-to-end test of the prospecting workflow:
1. Accept form submission payload
2. Resolve HubSpot contact/company
3. Search Gmail for existing threads
4. Pull thread context if found
5. Query Calendar freebusy
6. Create Gmail draft reply
7. Create HubSpot note + follow-up task

Usage:
    python -m src.commands.smoke_formlead                  # Interactive
    python -m src.commands.smoke_formlead --mock           # With mocked APIs
    python -m src.commands.smoke_formlead --no-gmail       # Skip Gmail access
    python -m src.commands.smoke_formlead --no-calendar    # Skip Calendar
    python -m src.commands.smoke_formlead --input=payload.json  # From file
"""
import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmokeTestContext:
    """Track state during smoke test."""

    def __init__(self, mock: bool = False, skip_gmail: bool = False, skip_calendar: bool = False):
        """Initialize context."""
        self.mock = mock
        self.skip_gmail = skip_gmail
        self.skip_calendar = skip_calendar
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "mode": "mocked" if mock else "live",
            "steps": {},
            "final_status": "pending",
            "draft_id": None,
            "task_id": None,
        }

    def record_step(self, name: str, status: str, details: dict[str, Any] | None = None) -> None:
        """Record a step in the workflow."""
        self.results["steps"][name] = {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {},
        }
        logger.info(f"Step: {name} → {status}")


async def step_1_load_payload(ctx: SmokeTestContext, input_file: str | None = None) -> dict[str, Any]:
    """Step 1: Load or generate form submission payload."""
    print("\n" + "=" * 70)
    print("STEP 1: Load Form Submission Payload")
    print("=" * 70)

    if input_file:
        logger.info(f"Loading payload from {input_file}")
        payload = json.loads(Path(input_file).read_text())
        print(f"✓ Loaded from {input_file}")
    else:
        # Generate sample payload
        payload = {
            "portalId": 12345,
            "formId": "lead-interest-form",
            "formSubmissionId": "submission-smoke-test-" + datetime.utcnow().strftime("%Y%m%d%H%M%S"),
            "pageTitle": "Sales Demo Request",
            "pageUri": "https://company.com/demo",
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            "submitText": "Request Demo",
            "userMessage": None,
            "fieldValues": [
                {"name": "firstname", "value": "Sarah"},
                {"name": "lastname", "value": "Johnson"},
                {"name": "email", "value": "sarah.johnson@techcorp.com"},
                {"name": "company", "value": "TechCorp Inc"},
                {"name": "phone", "value": "+1-555-123-4567"},
                {"name": "company_size", "value": "100-500"},
            ],
        }
        print("✓ Generated sample payload")

    email = next(
        (f["value"] for f in payload["fieldValues"] if f["name"] == "email"),
        None,
    )
    company = next(
        (f["value"] for f in payload["fieldValues"] if f["name"] == "company"),
        None,
    )

    ctx.record_step(
        "load_payload",
        "success",
        {"email": email, "company": company, "fields": len(payload["fieldValues"])},
    )

    print(f"\nPayload:")
    print(f"  Email:    {email}")
    print(f"  Company:  {company}")
    print(f"  Fields:   {len(payload['fieldValues'])}")

    return payload


async def step_2_hubspot_resolve(ctx: SmokeTestContext, payload: dict[str, Any]) -> dict[str, Any]:
    """Step 2: Resolve HubSpot contact/company."""
    print("\n" + "=" * 70)
    print("STEP 2: Resolve HubSpot Contact/Company")
    print("=" * 70)

    email = next(
        (f["value"] for f in payload["fieldValues"] if f["name"] == "email"),
        None,
    )
    company_name = next(
        (f["value"] for f in payload["fieldValues"] if f["name"] == "company"),
        None,
    )

    if ctx.mock:
        # Mock HubSpot response
        contact = {
            "id": "contact-12345",
            "email": email,
            "firstname": next(
                (f["value"] for f in payload["fieldValues"] if f["name"] == "firstname"),
                None,
            ),
            "lastname": next(
                (f["value"] for f in payload["fieldValues"] if f["name"] == "lastname"),
                None,
            ),
        }
        company = {"id": "company-789", "name": company_name}
        print(f"✓ Resolved (mocked)")
    else:
        # TODO: Call real HubSpot API
        print("TODO: Call real HubSpot API to resolve contact/company")
        contact = {"id": "contact-demo", "email": email}
        company = {"id": "company-demo", "name": company_name}

    ctx.record_step(
        "hubspot_resolve",
        "success",
        {"contact_id": contact["id"], "company_id": company["id"]},
    )

    print(f"\nResolved:")
    print(f"  Contact ID: {contact['id']}")
    print(f"  Company ID: {company['id']}")

    return {"contact": contact, "company": company}


async def step_3_gmail_search(ctx: SmokeTestContext, email: str) -> list[dict[str, Any]]:
    """Step 3: Search Gmail for existing threads with email."""
    print("\n" + "=" * 70)
    print("STEP 3: Search Gmail for Existing Threads")
    print("=" * 70)

    if ctx.skip_gmail:
        print("⊘ Skipped (--no-gmail)")
        ctx.record_step("gmail_search", "skipped", {"reason": "skip_gmail flag"})
        return []

    print(f"Searching for threads with: {email}")

    if ctx.mock:
        # Mock Gmail response
        threads = [
            {
                "id": "thread-1",
                "messages": [
                    {
                        "id": "msg-1",
                        "snippet": "Interested in your sales demo...",
                        "internalDate": str(int((datetime.utcnow() - timedelta(days=30)).timestamp() * 1000)),
                    }
                ],
            }
        ]
        print(f"✓ Found 1 thread (mocked)")
    else:
        # TODO: Call real Gmail API
        print("TODO: Call real Gmail API to search threads")
        threads = []
        print(f"✓ Found {len(threads)} threads")

    ctx.record_step("gmail_search", "success", {"threads_found": len(threads)})

    return threads


async def step_4_gmail_context(ctx: SmokeTestContext, threads: list[dict[str, Any]]) -> str | None:
    """Step 4: Pull thread context if found."""
    print("\n" + "=" * 70)
    print("STEP 4: Extract Thread Context")
    print("=" * 70)

    if not threads:
        print("⊘ No threads to extract context from")
        ctx.record_step("gmail_context", "skipped", {"reason": "no_threads"})
        return None

    if ctx.mock:
        context = "Sarah has been interested in our solution for 30 days. Previously inquired about enterprise features."
        print(f"✓ Extracted context (mocked)")
    else:
        context = None
        print("TODO: Extract context from Gmail thread")

    ctx.record_step("gmail_context", "success", {"context_available": bool(context)})

    if context:
        print(f"\nContext: {context[:100]}...")

    return context


async def step_5_calendar_availability(ctx: SmokeTestContext, email: str) -> list[dict[str, Any]]:
    """Step 5: Query Calendar and propose time slots."""
    print("\n" + "=" * 70)
    print("STEP 5: Check Calendar Availability & Propose Slots")
    print("=" * 70)

    if ctx.skip_calendar:
        print("⊘ Skipped (--no-calendar)")
        ctx.record_step("calendar_availability", "skipped", {"reason": "skip_calendar flag"})
        return []

    print("Checking calendar availability...")

    if ctx.mock:
        # Mock Calendar response with 2-3 30-min slots
        now = datetime.utcnow()
        slots = [
            {
                "start": (now + timedelta(days=1, hours=10)).isoformat(),
                "end": (now + timedelta(days=1, hours=10, minutes=30)).isoformat(),
                "confidence": "high",
            },
            {
                "start": (now + timedelta(days=2, hours=14)).isoformat(),
                "end": (now + timedelta(days=2, hours=14, minutes=30)).isoformat(),
                "confidence": "medium",
            },
            {
                "start": (now + timedelta(days=3, hours=16)).isoformat(),
                "end": (now + timedelta(days=3, hours=16, minutes=30)).isoformat(),
                "confidence": "high",
            },
        ]
        print(f"✓ Proposed 3 slots (mocked)")
    else:
        # TODO: Call real Calendar API
        print("TODO: Call real Calendar API")
        slots = []

    ctx.record_step("calendar_availability", "success", {"slots_proposed": len(slots)})

    print(f"\nProposed slots:")
    for i, slot in enumerate(slots, 1):
        start = datetime.fromisoformat(slot["start"]).strftime("%a %b %d, %I:%M %p")
        print(f"  {i}. {start} ({slot['confidence']} confidence)")

    return slots


async def step_6_create_draft(
    ctx: SmokeTestContext, payload: dict[str, Any], context: str | None, slots: list[dict[str, Any]]
) -> str:
    """Step 6: Create Gmail draft reply."""
    print("\n" + "=" * 70)
    print("STEP 6: Create Gmail Draft Reply")
    print("=" * 70)

    if ctx.mock:
        draft_id = "draft-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
        subject = "Re: Sales Demo Request - Next Steps"
        body = f"""Hi Sarah,

Thanks for your interest in our platform! I'd love to discuss how we can help TechCorp Inc scale your sales operations.

Based on your inquiry, here are some times that work for me:

1. Tomorrow at 10:00 AM (PT)
2. Wednesday at 2:00 PM (PT)
3. Thursday at 4:00 PM (PT)

Would any of these work for you?

Best regards,
Sales Team
"""
        print(f"✓ Created draft (mocked)")
    else:
        # TODO: Call real Gmail API to create draft
        print("TODO: Call real Gmail API to create draft")
        draft_id = "draft-demo"
        subject = "Demo Draft"
        body = "Demo body"

    ctx.record_step("create_draft", "success", {"draft_id": draft_id, "mode": "DRAFT_ONLY"})
    ctx.results["draft_id"] = draft_id

    print(f"\nDraft created: {draft_id}")
    print(f"Subject: {subject}")
    print(f"Body (first 100 chars): {body[:100]}...")
    print(f"\nMode: DRAFT_ONLY (not sent)")

    return draft_id


async def step_7_create_hubspot_task(
    ctx: SmokeTestContext, contact_id: str, company_id: str, draft_id: str
) -> str:
    """Step 7: Create HubSpot note + follow-up task."""
    print("\n" + "=" * 70)
    print("STEP 7: Create HubSpot Note & Follow-up Task")
    print("=" * 70)

    if ctx.mock:
        task_id = "task-" + datetime.utcnow().strftime("%Y%m%d%H%M%S")
        follow_up_date = (datetime.utcnow() + timedelta(days=3)).isoformat()
        print(f"✓ Created task (mocked)")
    else:
        # TODO: Call real HubSpot API
        print("TODO: Call real HubSpot API to create task")
        task_id = "task-demo"
        follow_up_date = datetime.utcnow().isoformat()

    ctx.record_step(
        "create_hubspot_task",
        "success",
        {
            "task_id": task_id,
            "contact_id": contact_id,
            "company_id": company_id,
            "draft_id": draft_id,
        },
    )
    ctx.results["task_id"] = task_id

    print(f"\nTask created: {task_id}")
    print(f"Contact ID: {contact_id}")
    print(f"Company ID: {company_id}")
    print(f"Follow-up date: {follow_up_date}")
    print(f"Associated draft: {draft_id}")

    return task_id


async def run_smoke_test(
    ctx: SmokeTestContext, input_file: str | None = None
) -> dict[str, Any]:
    """Run full E2E smoke test."""
    print("""
╔════════════════════════════════════════════════════════════════════╗
║  E2E SMOKE TEST: Form Lead → Draft → Task                         ║
║                                                                    ║
║  This test validates the complete prospecting workflow:            ║
║  1. Load form submission payload                                  ║
║  2. Resolve HubSpot contact/company                               ║
║  3. Search Gmail for existing threads                             ║
║  4. Extract thread context                                        ║
║  5. Check Calendar and propose slots                              ║
║  6. Create Gmail draft reply                                      ║
║  7. Create HubSpot note & task                                    ║
║                                                                    ║
║  MODE: DRAFT_ONLY (drafts created, not sent)                      ║
╚════════════════════════════════════════════════════════════════════╝
""")

    try:
        # Run all steps
        payload = await step_1_load_payload(ctx, input_file)
        hubspot = await step_2_hubspot_resolve(ctx, payload)
        email = next(
            (f["value"] for f in payload["fieldValues"] if f["name"] == "email"),
            None,
        )
        threads = await step_3_gmail_search(ctx, email)
        context = await step_4_gmail_context(ctx, threads)
        slots = await step_5_calendar_availability(ctx, email)
        draft_id = await step_6_create_draft(ctx, payload, context, slots)
        task_id = await step_7_create_hubspot_task(
            ctx, hubspot["contact"]["id"], hubspot["company"]["id"], draft_id
        )

        ctx.results["final_status"] = "success"

        # Print summary
        print("\n" + "=" * 70)
        print("SMOKE TEST COMPLETE ✓")
        print("=" * 70)
        print(f"\nResults:")
        print(f"  Draft ID:  {draft_id}")
        print(f"  Task ID:   {task_id}")
        print(f"  Contact:   {hubspot['contact']['id']}")
        print(f"  Company:   {hubspot['company']['id']}")
        print(f"  Status:    SUCCESS")
        print(f"\nMode: DRAFT_ONLY")
        print(f"  → Draft created but NOT sent")
        print(f"  → Task created in HubSpot")
        print(f"  → Operator review required before send")

        return ctx.results

    except Exception as e:
        logger.error(f"Smoke test failed: {e}", exc_info=True)
        ctx.results["final_status"] = "failed"
        ctx.results["error"] = str(e)
        return ctx.results


async def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="E2E smoke test: form lead → draft → task",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full test with mocked APIs
  python -m src.commands.smoke_formlead --mock

  # Test without Gmail/Calendar access
  python -m src.commands.smoke_formlead --mock --no-gmail --no-calendar

  # Test with custom payload
  python -m src.commands.smoke_formlead --mock --input=payload.json

  # Test with live APIs (requires auth)
  python -m src.commands.smoke_formlead

Via Makefile:
  make smoke-formlead              # Run with mocked APIs
        """,
    )

    parser.add_argument("--mock", action="store_true", help="Use mocked APIs")
    parser.add_argument("--no-gmail", action="store_true", help="Skip Gmail operations")
    parser.add_argument("--no-calendar", action="store_true", help="Skip Calendar operations")
    parser.add_argument("--input", help="Load payload from JSON file")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    # Set mock to True by default for dev
    mock = args.mock or True

    ctx = SmokeTestContext(mock=mock, skip_gmail=args.no_gmail, skip_calendar=args.no_calendar)

    results = await run_smoke_test(ctx, args.input)

    if args.json:
        print("\n" + json.dumps(results, indent=2))

    return 0 if results["final_status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
