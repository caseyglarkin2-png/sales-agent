#!/usr/bin/env python3
"""Complete workflow test: Import CHAINge NA forms → Research → Generate emails."""
import asyncio
import httpx
import os
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"


async def test_complete_workflow():
    """Test the full CHAINge NA import and outreach workflow."""
    print("\n" + "="*60)
    print("🚀 CHAINge NA Form → Research → Email Workflow Test")
    print("="*60 + "\n")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        
        # Step 1: Import CHAINge NA form submissions
        print("📥 Step 1: Importing CHAINge NA form submissions from HubSpot...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/contact-queue/import/chainge-na",
                params={"days_back": 30}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Import successful!")
                print(f"   Contacts imported: {result.get('contacts_imported')}")
                print(f"   Contacts skipped: {result.get('contacts_skipped')}")
                print(f"   Total processed: {result.get('total_processed')}")
                
                contact_ids = result.get('contact_ids', [])
                
                if not contact_ids:
                    print("\n❌ No contacts imported. Trying general form import instead...")
                    
                    # Try general form import
                    response = await client.post(
                        f"{BASE_URL}/api/contact-queue/import/hubspot-forms",
                        params={
                            "days_back": 30,
                            "voice_profile": "casey_larkin",
                            "priority": 1
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        contact_ids = result.get('contact_ids', [])
                        print(f"✅ Found {len(contact_ids)} contacts from general import")
                    
                if not contact_ids:
                    print("\n⚠️  No contacts found. Adding test contact...")
                    response = await client.post(
                        f"{BASE_URL}/api/contact-queue/add",
                        json={
                            "email": "test@freightcompany.com",
                            "first_name": "Test",
                            "last_name": "User",
                            "company": "Freight Test Co",
                            "job_title": "VP Operations",
                            "voice_profile": "casey_larkin",
                            "priority": 1
                        }
                    )
                    if response.status_code == 200:
                        contact_ids = [response.json()["contact_id"]]
                        print(f"✅ Test contact added: {contact_ids[0]}")
            else:
                print(f"❌ Import failed: {response.status_code}")
                print(response.text[:500])
                return
                
        except Exception as e:
            print(f"❌ Import error: {e}")
            return
        
        # Step 2: List queue
        print(f"\n📋 Step 2: Listing contact queue...")
        try:
            response = await client.get(f"{BASE_URL}/api/contact-queue/list")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Queue loaded")
                print(f"   Total contacts: {result['total']}")
                print(f"   Status breakdown:")
                for status, count in result.get('status_counts', {}).items():
                    if count > 0:
                        print(f"      {status}: {count}")
        except Exception as e:
            print(f"❌ List error: {e}")
        
        # Step 3: Research each contact
        print(f"\n🔍 Step 3: Researching contacts...")
        researched_ids = []
        
        for i, contact_id in enumerate(contact_ids[:5], 1):  # Limit to 5 for testing
            print(f"\n   [{i}/{min(len(contact_ids), 5)}] Researching {contact_id}...")
            try:
                response = await client.post(
                    f"{BASE_URL}/api/contact-queue/{contact_id}/research"
                )
                
                if response.status_code == 200:
                    result = response.json()
                    research = result.get('research', {})
                    contact_info = research.get('contact_info', {})
                    company_info = research.get('company_info', {})
                    comm_history = research.get('communication_history', {})
                    
                    print(f"   ✅ Research complete for {contact_info.get('email')}")
                    print(f"      Company: {contact_info.get('company')}")
                    print(f"      Title: {contact_info.get('title')}")
                    
                    if comm_history:
                        total_eng = comm_history.get('total_engagements', 0)
                        print(f"      Prior contact: {total_eng} engagements")
                    
                    if company_info:
                        if company_info.get('industry'):
                            print(f"      Industry: {company_info.get('industry')}")
                        if company_info.get('employee_count'):
                            print(f"      Size: {company_info.get('employee_count')} employees")
                    
                    print(f"      Insights: {', '.join(research.get('insights', [])[:2])}")
                    print(f"      Approach: {research.get('recommended_angle', 'N/A')[:60]}...")
                    
                    researched_ids.append(contact_id)
                else:
                    print(f"   ❌ Research failed: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Research error: {e}")
        
        # Step 4: Generate email proposals
        print(f"\n✉️  Step 4: Generating email proposals...")
        
        for i, contact_id in enumerate(researched_ids[:3], 1):  # Limit to 3 for testing
            print(f"\n   [{i}/{min(len(researched_ids), 3)}] Generating proposals for {contact_id}...")
            try:
                response = await client.post(
                    f"{BASE_URL}/api/contact-queue/{contact_id}/propose-email",
                    params={"num_variants": 2}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    proposals = result.get('proposals', [])
                    
                    print(f"   ✅ Generated {len(proposals)} email variants")
                    
                    for p in proposals:
                        print(f"\n   --- Variant {p['variant']} ---")
                        print(f"   Subject: {p['subject']}")
                        print(f"   Reasoning: {p['reasoning']}")
                        print(f"\n{p['body']}\n")
                else:
                    print(f"   ❌ Proposal generation failed: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Proposal error: {e}")
        
        # Step 5: Summary
        print("\n" + "="*60)
        print("📊 Workflow Summary")
        print("="*60)
        
        try:
            response = await client.get(f"{BASE_URL}/api/contact-queue/list")
            if response.status_code == 200:
                result = response.json()
                counts = result.get('status_counts', {})
                
                print(f"   Total contacts: {result['total']}")
                print(f"   Pending: {counts.get('pending', 0)}")
                print(f"   Ready: {counts.get('ready', 0)}")
                print(f"   Draft created: {counts.get('draft_created', 0)}")
                print(f"\n✅ Workflow complete! Check the queue for email proposals.")
        except Exception as e:
            print(f"   Error getting summary: {e}")


async def test_voice_training():
    """Test voice training from HubSpot newsletters."""
    print("\n" + "="*60)
    print("🎨 Voice Training Test")
    print("="*60 + "\n")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        
        # Train from HubSpot newsletters
        print("📧 Training from HubSpot newsletters...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/voice/training/hubspot-newsletters",
                json={
                    "search_query": "freight",
                    "limit": 15
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Newsletter training successful!")
                print(f"   Newsletters fetched: {result.get('newsletters_fetched')}")
                print(f"   Total samples: {result.get('total_samples')}")
            else:
                print(f"⚠️  Newsletter training unavailable: {response.status_code}")
                print(f"   This requires HubSpot Marketing API access")
        except Exception as e:
            print(f"⚠️  Newsletter training error: {e}")
        
        # Check training status
        print("\n📊 Checking training status...")
        try:
            response = await client.get(f"{BASE_URL}/api/voice/training/status")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Training status:")
                print(f"   Samples: {result.get('samples_count')}")
                print(f"   Sources: {', '.join(result.get('sources', []))}")
        except Exception as e:
            print(f"   Error: {e}")


async def test_api_keys():
    """Test that all API keys are configured."""
    print("\n" + "="*60)
    print("🔑 API Key Configuration Test")
    print("="*60 + "\n")
    
    keys_to_check = {
        "HUBSPOT_API_KEY": "HubSpot CRM & Marketing",
        "OPENAI_API_KEY": "OpenAI for voice analysis",
        "GOOGLE_CLIENT_ID": "Google OAuth",
        "GOOGLE_CLIENT_SECRET": "Google OAuth",
    }
    
    for key, description in keys_to_check.items():
        value = os.environ.get(key)
        if value:
            masked = value[:10] + "..." + value[-4:] if len(value) > 14 else "***"
            print(f"✅ {key}: {masked}")
            print(f"   ({description})")
        else:
            print(f"❌ {key}: NOT SET")
            print(f"   ({description})")
    
    print()


async def main():
    """Run all tests."""
    await test_api_keys()
    await test_voice_training()
    await test_complete_workflow()
    
    print("\n" + "="*60)
    print("✨ All tests complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
