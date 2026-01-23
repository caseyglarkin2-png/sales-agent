#!/usr/bin/env python3
"""
Load generated email drafts into JARVIS voice approval queue.
"""
import json
import asyncio
import os
import sys
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DRAFTS_FILE = "/workspaces/sales-agent/email_drafts.json"
API_BASE = "http://localhost:8000"


async def load_drafts_to_jarvis():
    """Load email drafts into JARVIS approval queue."""
    
    print("=" * 80)
    print("📧 LOADING EMAIL DRAFTS INTO JARVIS APPROVAL QUEUE")
    print("=" * 80)
    
    # Check if drafts file exists
    if not os.path.exists(DRAFTS_FILE):
        print(f"\n❌ Drafts file not found: {DRAFTS_FILE}")
        print("Run the email drafting script first to generate drafts.")
        return
    
    # Load drafts
    print(f"\n📖 Loading drafts from {DRAFTS_FILE}...")
    with open(DRAFTS_FILE, "r") as f:
        data = json.load(f)
    
    drafts = [r for r in data.get("results", []) if r.get("status") == "success"]
    print(f"   Found {len(drafts)} successful drafts")
    
    if not drafts:
        print("❌ No successful drafts to load")
        return
    
    # Prepare drafts for bulk upload
    approval_drafts = []
    for i, result in enumerate(drafts, 1):
        contact = result["contact"]
        draft_text = result["draft"]
        
        # Extract subject (first line of draft if it looks like a subject)
        lines = draft_text.split("\n")
        subject = "Follow-up regarding CHAINge NA"
        body = draft_text
        
        # Try to extract subject if draft starts with "Subject:"
        if lines and "subject" in lines[0].lower():
            subject = lines[0].replace("Subject:", "").strip()
            body = "\n".join(lines[1:]).strip()
        
        approval_drafts.append({
            "draft_id": f"chainge_{i}",
            "to_email": contact["email"],
            "to_name": contact["name"],
            "subject": subject,
            "body": body,
            "context": {
                "company": contact.get("company", ""),
                "request": contact.get("request", ""),
                "source": "CHAINge NA Form",
                "generated_at": result.get("processed_at", "")
            },
            "agent": "email_drafter_v1"
        })
    
    # Upload to JARVIS
    print(f"\n🚀 Uploading {len(approval_drafts)} drafts to JARVIS...")
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                f"{API_BASE}/api/voice-approval/bulk-add-drafts",
                json=approval_drafts
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"\n✅ SUCCESS!")
            print(f"   Drafts loaded: {result.get('count')}")
            print(f"   Queue length: {result.get('queue_length')}")
            print(f"\n🎙️  Open JARVIS interface: {API_BASE}/jarvis")
            print("\nYou can now:")
            print("  • Use voice commands to review and approve drafts")
            print("  • Say 'Approve this' or 'Show me the next one'")
            print("  • Click the microphone button or type commands")
            
        except httpx.HTTPStatusError as e:
            print(f"\n❌ HTTP Error: {e.response.status_code}")
            print(f"   {e.response.text[:500]}")
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(load_drafts_to_jarvis())
