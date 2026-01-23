#!/usr/bin/env python3
"""
Bulk import all CHAINge NA form submissions from HubSpot.

This script:
1. Fetches all contacts from HubSpot (including CHAINge NA submissions)
2. Filters and imports them to the contact queue
3. Shows progress and summary
"""
import asyncio
import httpx
import sys
from typing import List, Dict, Any

BASE_URL = "http://localhost:8000"


async def fetch_all_hubspot_contacts(limit: int = 500, days_back: int = 365) -> List[Dict[str, Any]]:
    """Fetch all contacts from HubSpot."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        print(f"📥 Fetching up to {limit} contacts from HubSpot (last {days_back} days)...")
        
        response = await client.get(
            f"{BASE_URL}/api/forms/submissions",
            params={"limit": limit, "days_back": days_back}
        )
        
        if response.status_code != 200:
            print(f"❌ Error fetching submissions: {response.status_code}")
            print(response.text)
            return []
        
        data = response.json()
        submissions = data.get("submissions", [])
        
        print(f"✅ Fetched {len(submissions)} contacts from HubSpot")
        return submissions


async def import_chainge_submissions():
    """Import CHAINge NA form submissions."""
    
    print("=" * 80)
    print("🚀 CHAINGE NA FORM SUBMISSION IMPORT")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        
        # Step 1: Import with filter for CHAINge
        print("\n📋 Step 1: Importing CHAINge NA submissions...")
        
        response = await client.post(
            f"{BASE_URL}/api/forms/import-to-queue",
            json={
                "form_name": "CHAINge",  # Filter for CHAINge
                "limit": 600,  # Get more than 500
                "days_back": 365,  # Look back 1 year
                "voice_profile": "freight_marketer_voice"
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Error importing: {response.status_code}")
            print(response.text)
            return
        
        result = response.json()
        imported = result.get("imported", 0)
        skipped = result.get("skipped", 0)
        total = result.get("total_submissions", 0)
        
        print(f"\n📊 Import Results:")
        print(f"   Total submissions found: {total}")
        print(f"   ✅ Imported to queue: {imported}")
        print(f"   ⏭️  Skipped (duplicates/invalid): {skipped}")
        
        if imported == 0:
            print("\n⚠️  No CHAINge submissions found with filter.")
            print("   Trying broader search...")
            
            # Try without filter
            response = await client.post(
                f"{BASE_URL}/api/forms/import-to-queue",
                json={
                    "form_name": "",  # No filter
                    "limit": 600,
                    "days_back": 365,
                    "voice_profile": "freight_marketer_voice"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                imported = result.get("imported", 0)
                total = result.get("total_submissions", 0)
                
                print(f"\n📊 Broader Search Results:")
                print(f"   Total contacts: {total}")
                print(f"   ✅ Imported: {imported}")
        
        # Step 2: Check queue status
        print("\n📋 Step 2: Checking queue status...")
        
        total_in_queue = 0
        response = await client.get(f"{BASE_URL}/api/contact-queue/list?limit=1000")
        
        if response.status_code == 200:
            data = response.json()
            total_in_queue = data.get("total", 0)
            status_counts = data.get("status_counts", {})
            
            print(f"\n📊 Contact Queue Status:")
            print(f"   Total contacts in queue: {total_in_queue}")
            print(f"\n   By status:")
            for status, count in status_counts.items():
                if count > 0:
                    print(f"      {status}: {count}")
            
            # Show sample contacts
            contacts = data.get("contacts", [])[:10]
            if contacts:
                print(f"\n📧 Sample Contacts (first 10):")
                for i, contact in enumerate(contacts, 1):
                    email = contact.get("email", "")
                    name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                    company = contact.get("company", "N/A")
                    print(f"   {i}. {name} ({email}) - {company}")
        
        print("\n" + "=" * 80)
        print("✅ IMPORT COMPLETE")
        print("=" * 80)
        
        if total_in_queue > 0:
            print(f"\n🎯 Next Step: Research and draft emails")
            print(f"   Run: python scripts/draft_emails_for_queue.py")
        else:
            print(f"\n⚠️  No contacts in queue. Check HubSpot API access.")


async def main():
    """Main entry point."""
    try:
        await import_chainge_submissions()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
