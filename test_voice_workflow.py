#!/usr/bin/env python3
"""
Test script for voice training and contact queue workflow.

This demonstrates the complete flow:
1. Train voice from videos and newsletters
2. Queue contacts
3. Research and generate email proposals
"""
import asyncio
import httpx
import json
from typing import List

BASE_URL = "http://localhost:8000"

# Replace with actual "Dude, What's The Bid?!" video URLs
EXAMPLE_VIDEOS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Replace with real video
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Replace with real video
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Replace with real video
]

EXAMPLE_CONTACTS = [
    {
        "email": "john.doe@freightco.com",
        "first_name": "John",
        "last_name": "Doe",
        "company": "Freight Company Inc",
        "job_title": "VP of Operations",
        "voice_profile": "freight_voice",
        "priority": 1
    },
    {
        "email": "jane.smith@logistics.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "company": "Logistics Solutions",
        "job_title": "Director of Marketing",
        "voice_profile": "freight_voice",
        "priority": 0
    }
]


async def test_voice_training():
    """Test voice training from videos and newsletters."""
    print("\n" + "="*60)
    print("🎥 VOICE TRAINING TEST")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Train from YouTube videos
        print("\n1️⃣  Training from YouTube videos...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/voice/training/youtube-videos",
                json={
                    "video_urls": EXAMPLE_VIDEOS,
                    "profile_name": "dude_whats_the_bid"
                }
            )
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Videos processed: {result.get('videos_processed', 0)}")
                print(f"   ✅ Transcripts added: {result.get('transcripts_added', 0)}")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
                print(f"   Note: {response.json().get('detail', 'Unknown error')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 2. Train from HubSpot newsletters
        print("\n2️⃣  Training from HubSpot newsletters...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/voice/training/hubspot-newsletters",
                json={
                    "search_query": "freight marketer",
                    "limit": 20,
                    "profile_name": "freight_marketer_voice"
                }
            )
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Newsletters fetched: {result.get('newsletters_fetched', 0)}")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
                if response.status_code == 400:
                    print(f"   Note: {response.json().get('detail', '')}")
                    print(f"   Tip: Make sure HUBSPOT_API_KEY is set")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 3. Check training status
        print("\n3️⃣  Checking training status...")
        try:
            response = await client.get(f"{BASE_URL}/api/voice/training/status")
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Total samples: {result.get('samples_count', 0)}")
                print(f"   ✅ Sources: {', '.join(result.get('sources', []))}")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 4. Create voice profile
        print("\n4️⃣  Creating voice profile...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/voice/training/create-profile",
                params={"profile_name": "freight_voice"}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Profile created: {result.get('profile_name', 'Unknown')}")
                print(f"   ✅ Tone: {result.get('tone', 'Unknown')}")
                print(f"   ✅ Samples used: {result.get('samples_used', 0)}")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
                print(f"   Note: {response.json().get('detail', '')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def test_contact_queue():
    """Test contact queue and email generation."""
    print("\n" + "="*60)
    print("👥 CONTACT QUEUE TEST")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Add contacts to queue
        print("\n1️⃣  Adding contacts to queue...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/contact-queue/add-bulk",
                json={"contacts": EXAMPLE_CONTACTS}
            )
            if response.status_code == 200:
                result = response.json()
                contact_ids = result.get("contact_ids", [])
                print(f"   ✅ Contacts added: {result.get('contacts_added', 0)}")
                print(f"   ✅ Contact IDs: {', '.join(contact_ids[:3])}...")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
                return
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # 2. List queue
        print("\n2️⃣  Listing queued contacts...")
        try:
            response = await client.get(f"{BASE_URL}/api/contact-queue/list")
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Total contacts: {result.get('total', 0)}")
                status_counts = result.get('status_counts', {})
                for status, count in status_counts.items():
                    if count > 0:
                        print(f"   ✅ {status}: {count}")
            else:
                print(f"   ⚠️  Status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 3. Research first contact
        if contact_ids:
            contact_id = contact_ids[0]
            print(f"\n3️⃣  Researching contact: {contact_id[:8]}...")
            try:
                response = await client.post(
                    f"{BASE_URL}/api/contact-queue/{contact_id}/research"
                )
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ Research complete")
                    research = result.get('research', {})
                    insights = research.get('insights', [])
                    print(f"   ✅ Insights: {', '.join(insights[:2])}")
                else:
                    print(f"   ⚠️  Status: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # 4. Generate email proposals
            print(f"\n4️⃣  Generating email proposals...")
            try:
                response = await client.post(
                    f"{BASE_URL}/api/contact-queue/{contact_id}/propose-email",
                    params={"num_variants": 2}
                )
                if response.status_code == 200:
                    result = response.json()
                    proposals = result.get('proposals', [])
                    print(f"   ✅ Proposals generated: {len(proposals)}")
                    
                    # Show first proposal
                    if proposals:
                        p = proposals[0]
                        print(f"\n   📧 Example Proposal:")
                        print(f"      Subject: {p.get('subject', '')}")
                        print(f"      Body preview: {p.get('body', '')[:100]}...")
                        print(f"      Reasoning: {p.get('reasoning', '')}")
                else:
                    print(f"   ⚠️  Status: {response.status_code}")
                    print(f"   Note: {response.json().get('detail', '')}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # 5. View contact details
            print(f"\n5️⃣  Viewing contact details...")
            try:
                response = await client.get(
                    f"{BASE_URL}/api/contact-queue/{contact_id}"
                )
                if response.status_code == 200:
                    result = response.json()
                    contact = result.get('contact', {})
                    print(f"   ✅ Contact: {contact.get('first_name')} {contact.get('last_name')}")
                    print(f"   ✅ Status: {contact.get('status')}")
                    print(f"   ✅ Proposals: {result.get('proposal_count', 0)}")
                else:
                    print(f"   ⚠️  Status: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error: {e}")


async def main():
    """Run all tests."""
    print("\n")
    print("╔═══════════════════════════════════════════════════════╗")
    print("║  Voice Training & Contact Queue Test Suite           ║")
    print("╚═══════════════════════════════════════════════════════╝")
    
    print("\n⚙️  Server URL: " + BASE_URL)
    print("⚙️  Make sure the server is running:")
    print("    uvicorn src.main:app --reload")
    
    # Test voice training
    await test_voice_training()
    
    # Test contact queue
    await test_contact_queue()
    
    print("\n" + "="*60)
    print("✨ TEST COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. Replace EXAMPLE_VIDEOS with real 'Dude, What's The Bid?!' URLs")
    print("2. Ensure HUBSPOT_API_KEY is set for newsletter training")
    print("3. Review generated email proposals")
    print("4. Start queuing real contacts!")
    print()


if __name__ == "__main__":
    asyncio.run(main())
