#!/usr/bin/env python3
"""
Draft emails for all contacts in the queue.

This script:
1. Fetches all pending/ready contacts from the queue
2. Researches each contact (enriches data, analyzes company, gets HubSpot history)
3. Generates personalized email proposals using the trained voice
4. Outputs results for review
"""
import asyncio
import httpx
import sys
from typing import List, Dict, Any

BASE_URL = "http://localhost:8000"


async def draft_emails_for_all_contacts(
    num_variants: int = 3,
    voice_profile: str = "freight_marketer_voice"
):
    """Research and draft emails for all contacts in the queue."""
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        print("=" * 80)
        print("📧 AUTOMATED EMAIL DRAFTING FOR CONTACT QUEUE")
        print("=" * 80)
        
        # 1. Get all pending/ready contacts
        print("\n📋 Step 1: Fetching contacts from queue...")
        response = await client.get(
            f"{BASE_URL}/api/contact-queue/list",
            params={"limit": 100}
        )
        
        if response.status_code != 200:
            print(f"❌ Error fetching contacts: {response.status_code}")
            print(response.text)
            return
        
        data = response.json()
        contacts = data.get("contacts", [])
        
        if not contacts:
            print("⚠️  No contacts in queue. Import CHAINge NA submissions first:")
            print("   curl -X POST http://localhost:8000/api/forms/import-to-queue")
            return
        
        print(f"✅ Found {len(contacts)} contacts in queue")
        print(f"\nStatus breakdown:")
        for status, count in data.get("status_counts", {}).items():
            if count > 0:
                print(f"   {status}: {count}")
        
        # 2. Filter contacts that need processing
        needs_research = [c for c in contacts if c["status"] in ["pending"]]
        needs_drafts = [c for c in contacts if c["status"] in ["ready"]]
        
        print(f"\n📊 Processing plan:")
        print(f"   Contacts needing research: {len(needs_research)}")
        print(f"   Contacts ready for drafts: {len(needs_drafts)}")
        
        # 3. Research contacts
        if needs_research:
            print(f"\n🔍 Step 2: Researching {len(needs_research)} contacts...")
            for i, contact in enumerate(needs_research, 1):
                contact_id = contact["id"]
                email = contact["email"]
                
                print(f"\n   [{i}/{len(needs_research)}] Researching {email}...")
                
                try:
                    response = await client.post(
                        f"{BASE_URL}/api/contact-queue/{contact_id}/research"
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        insights = result.get("research", {}).get("insights", [])
                        print(f"      ✅ Research complete")
                        if insights:
                            print(f"      💡 Key insights: {insights[0]}")
                    else:
                        print(f"      ⚠️  Research failed: {response.status_code}")
                        
                except Exception as e:
                    print(f"      ❌ Error: {e}")
        
        # 4. Re-fetch contacts to get updated statuses
        response = await client.get(
            f"{BASE_URL}/api/contact-queue/list",
            params={"status": "ready", "limit": 100}
        )
        
        ready_contacts = response.json().get("contacts", [])
        
        if not ready_contacts:
            print("\n⚠️  No contacts ready for email drafting")
            return
        
        # 5. Generate email proposals
        print(f"\n✉️  Step 3: Generating email drafts for {len(ready_contacts)} contacts...")
        
        drafted_count = 0
        failed_count = 0
        
        for i, contact in enumerate(ready_contacts, 1):
            contact_id = contact["id"]
            email = contact["email"]
            name = f"{contact['first_name']} {contact['last_name']}"
            company = contact.get("company", "Unknown")
            
            print(f"\n   [{i}/{len(ready_contacts)}] Drafting for {name} ({email})")
            print(f"      Company: {company}")
            
            try:
                response = await client.post(
                    f"{BASE_URL}/api/contact-queue/{contact_id}/propose-email",
                    params={"num_variants": num_variants}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    proposals = result.get("proposals", [])
                    drafted_count += 1
                    
                    print(f"      ✅ Generated {len(proposals)} email variants")
                    
                    # Show first variant summary
                    if proposals:
                        first = proposals[0]
                        print(f"\n      📧 Variant 1 Preview:")
                        print(f"      Subject: {first['subject']}")
                        print(f"      Approach: {first['reasoning']}")
                        body_preview = first['body'][:150].replace('\n', ' ')
                        print(f"      Body: {body_preview}...")
                else:
                    failed_count += 1
                    print(f"      ⚠️  Draft failed: {response.status_code}")
                    
            except Exception as e:
                failed_count += 1
                print(f"      ❌ Error: {e}")
        
        # 6. Summary
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"\n✅ Successfully drafted emails: {drafted_count}")
        if failed_count > 0:
            print(f"⚠️  Failed: {failed_count}")
        
        print(f"\n📬 Next steps:")
        print(f"   1. Review drafts in UI or via API:")
        print(f"      curl http://localhost:8000/api/contact-queue/list?status=draft_created")
        print(f"\n   2. View specific contact's proposals:")
        print(f"      curl http://localhost:8000/api/contact-queue/{{contact_id}}")
        print(f"\n   3. Select best variant and send (manual for now)")
        
        # 7. Show detailed results for first few contacts
        print(f"\n" + "=" * 80)
        print("📧 SAMPLE EMAIL DRAFTS (First 3)")
        print("=" * 80)
        
        response = await client.get(
            f"{BASE_URL}/api/contact-queue/list",
            params={"status": "draft_created", "limit": 3}
        )
        
        if response.status_code == 200:
            draft_contacts = response.json().get("contacts", [])
            
            for i, contact in enumerate(draft_contacts, 1):
                contact_id = contact["id"]
                
                # Get full contact details with proposals
                response = await client.get(
                    f"{BASE_URL}/api/contact-queue/{contact_id}"
                )
                
                if response.status_code == 200:
                    details = response.json()
                    contact_info = details["contact"]
                    proposals = details.get("proposals", [])
                    
                    print(f"\n{'-' * 80}")
                    print(f"Contact {i}: {contact_info['first_name']} {contact_info['last_name']}")
                    print(f"Email: {contact_info['email']}")
                    print(f"Company: {contact_info.get('company', 'N/A')}")
                    print(f"Title: {contact_info.get('job_title', 'N/A')}")
                    
                    if proposals:
                        best_proposal = proposals[0]
                        print(f"\n📧 Best Email Variant:")
                        print(f"\nSubject: {best_proposal['subject']}")
                        print(f"\nBody:\n{best_proposal['body']}")
                        print(f"\n💡 Reasoning: {best_proposal['reasoning']}")
                        print(f"\n🎯 Personalization:")
                        for note in best_proposal.get('personalization_notes', []):
                            print(f"   • {note}")


async def main():
    """Main entry point."""
    try:
        await draft_emails_for_all_contacts(
            num_variants=3,
            voice_profile="freight_marketer_voice"
        )
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
