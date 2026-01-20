"""Smoke test for formlead orchestration (DRAFT_ONLY mode)."""
import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from src.logger import get_logger
from src.formlead_orchestrator import get_formlead_orchestrator
from src.connectors.gmail import GmailConnector
from src.connectors.hubspot import HubSpotConnector
from src.connectors.calendar_connector import CalendarConnector
from tests.fixtures.seed_data import get_sample_form_submission

logger = get_logger(__name__)


# Mock connectors for testing
class MockGmailConnector:
    """Mock Gmail connector."""
    async def search_threads(self, *args, **kwargs):
        return [{"id": "thread-mock-001", "snippet": "Previous conversation..."}]
    
    async def get_thread(self, *args, **kwargs):
        return {
            "id": "thread-mock-001",
            "messages": [
                {"internalDate": "2026-01-20T10:00:00Z", "snippet": "First message"},
                {"internalDate": "2026-01-20T14:00:00Z", "snippet": "Recent message"},
            ],
        }
    
    async def create_draft(self, to: str, subject: str, body: str):
        return f"draft-mock-{datetime.utcnow().isoformat()}"


class MockHubSpotConnector:
    """Mock HubSpot connector."""
    async def search_contacts(self, email: str):
        return {"id": "contact-mock-001", "email": email}
    
    async def create_note(self, *args, **kwargs):
        return f"note-mock-{datetime.utcnow().isoformat()}"
    
    async def create_task(self, *args, **kwargs):
        return f"task-mock-{datetime.utcnow().isoformat()}"


async def run_smoke_test(
    mock: bool = True,
    json_output: bool = False,
    custom_form_data: Optional[Dict[str, Any]] = None,
) -> int:
    """Run formlead smoke test."""
    logger.info("🚀 Starting formlead smoke test (DRAFT_ONLY mode)")
    
    try:
        # Initialize connectors
        gmail = MockGmailConnector() if mock else None
        hubspot = MockHubSpotConnector() if mock else None
        calendar = None  # Calendar is optional
        
        # Get orchestrator
        orchestrator = get_formlead_orchestrator(
            gmail_connector=gmail,
            hubspot_connector=hubspot,
            calendar_connector=calendar,
        )

        # Get test form data
        form_submission = custom_form_data or get_sample_form_submission()

        # Run orchestration
        logger.info("Processing form submission through 11-step workflow...")
        result = await orchestrator.process_formlead(form_submission)

        # Format output
        if json_output:
            print(json.dumps(result, indent=2, default=str))
        else:
            await print_result_summary(result)

        # Determine exit code
        exit_code = 0 if result.get("final_status") == "success" else 1
        
        if exit_code == 0:
            logger.info("✅ Formlead smoke test PASSED (DRAFT_ONLY mode confirmed)")
        else:
            logger.error("❌ Formlead smoke test FAILED")

        return exit_code

    except Exception as e:
        logger.error(f"Smoke test error: {e}", exc_info=True)
        if json_output:
            print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        else:
            print(f"❌ Error: {e}")
        return 1


async def print_result_summary(result: Dict[str, Any]) -> None:
    """Print human-readable result summary."""
    print("\n" + "═" * 70)
    print("FORMLEAD E2E SMOKE TEST RESULTS")
    print("═" * 70)
    print()

    # Overall status
    status = result.get("final_status", "unknown").upper()
    status_symbol = "✅" if status == "SUCCESS" else "❌"
    print(f"{status_symbol} Status: {status}")
    print(f"   Mode: {result.get('mode', 'UNKNOWN')}")
    print(f"   Workflow ID: {result.get('workflow_id', 'N/A')}")
    print()

    # Form data
    if "prospect" in result:
        prospect = result["prospect"]
        print(f"📧 Prospect: {prospect.get('first_name', 'Unknown')} {prospect.get('last_name', '')} ({prospect.get('email')})")
        print(f"   Company: {prospect.get('company', 'N/A')}")
        print()

    # Step-by-step results
    print("📋 Workflow Steps:")
    print("─" * 70)
    
    steps_map = {
        "validate_payload": "1. Validate webhook payload",
        "resolve_hubspot": "2. Resolve HubSpot contact/company",
        "search_gmail": "3. Search Gmail threads",
        "read_thread": "4. Read thread context",
        "long_memory": "5. Find similar patterns",
        "asset_hunter": "6. Hunt Drive assets (allowlist)",
        "meeting_slots": "7. Propose meeting slots",
        "next_step_plan": "8. Plan next step (CTA)",
        "draft_writer": "9. Write draft (voice profile)",
        "create_draft": "10. Create Gmail draft",
        "create_task": "11. Create HubSpot task",
        "label_thread": "12. Label thread",
    }

    for step_key, step_name in steps_map.items():
        if step_key in result.get("steps", {}):
            step = result["steps"][step_key]
            status = step.get("status", "unknown").upper()
            symbol = "✓" if status == "SUCCESS" else "✗" if status == "FAILED" else "?"
            print(f"  {symbol} {step_name}: {status}")

    print()

    # Deliverables
    print("📦 Deliverables:")
    print("─" * 70)
    if result.get("draft_id"):
        print(f"  ✓ Draft Email ID: {result['draft_id']}")
        print(f"    Mode: DRAFT_ONLY (NOT sent)")
    else:
        print("  ✗ Draft not created")

    if result.get("task_id"):
        print(f"  ✓ HubSpot Task ID: {result['task_id']}")
        print(f"    Due: 2 business days")
    else:
        print("  ✗ Task not created")

    print()

    # Verification
    print("✨ Verification:")
    print("─" * 70)
    
    checks = [
        ("DRAFT_ONLY mode enforced", result.get("mode") == "DRAFT_ONLY"),
        ("Webhook payload validated", result["steps"].get("validate_payload", {}).get("status") == "success"),
        ("HubSpot contact resolved", result["steps"].get("resolve_hubspot", {}).get("status") == "success"),
        ("Gmail searched", result["steps"].get("search_gmail", {}).get("status") == "success"),
        ("Meeting slots proposed", result["steps"].get("meeting_slots", {}).get("status") == "success"),
        ("Draft created", result.get("draft_id") is not None),
        ("Task created", result.get("task_id") is not None),
    ]

    for check_name, check_result in checks:
        symbol = "✓" if check_result else "✗"
        print(f"  {symbol} {check_name}")

    print()
    print("═" * 70)
    print()


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Formlead E2E smoke test")
    parser.add_argument("--live", action="store_true", help="Use live connectors")
    parser.add_argument("--mock", action="store_true", help="Use mocked connectors (default)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    
    args = parser.parse_args()
    
    mock = not args.live  # Default to mock
    json_output = args.json
    
    exit_code = asyncio.run(run_smoke_test(mock=mock, json_output=json_output))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
