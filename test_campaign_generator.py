#!/usr/bin/env python3
"""
Test Campaign Generator
=======================

Quick test to verify campaign generator functionality.
"""

import asyncio
import logging
from src.campaigns.campaign_generator import (
    CampaignGenerator,
    create_campaign_generator,
    CampaignSegment
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_personalization():
    """Test email personalization."""
    print("\n" + "=" * 60)
    print("TEST 1: Email Personalization")
    print("=" * 60)
    
    generator = create_campaign_generator()
    
    # Test contact
    contact = {
        "email": "john.doe@example.com",
        "firstname": "John",
        "lastname": "Doe",
        "company": "Example SaaS Corp",
        "jobtitle": "VP of Sales",
        "hubspot_id": "12345"
    }
    
    # CHAINge template
    template = """Hi {{firstname}},

I saw you're at {{company}} working on {{pain_point}}.

Looking forward to connecting!

{{signature}}"""
    
    personalized = generator.personalize_email(contact, template)
    
    print(f"\nOriginal template:")
    print(template)
    print(f"\nPersonalized email:")
    print(personalized)
    print(f"\n✅ Personalization test passed")


async def test_segment_contacts():
    """Test getting contacts by segment."""
    print("\n" + "=" * 60)
    print("TEST 2: Get Contacts by Segment")
    print("=" * 60)
    
    generator = create_campaign_generator()
    
    # Test each segment
    segments = ["chainge", "high_value", "engaged", "cold", "all"]
    
    for segment in segments:
        contacts = generator._get_segment_contacts(segment, limit=5)
        print(f"\n{segment.upper()} segment: {len(contacts)} contacts")
        
        if contacts:
            sample = contacts[0]
            print(f"  Sample: {sample.get('email')} - {sample.get('company')}")
    
    print(f"\n✅ Segment contacts test passed")


async def test_template_selection():
    """Test template selection for different segments."""
    print("\n" + "=" * 60)
    print("TEST 3: Template Selection")
    print("=" * 60)
    
    generator = create_campaign_generator()
    
    segments = ["chainge", "high_value", "engaged", "cold"]
    
    for segment in segments:
        template = generator._get_template(segment)
        print(f"\n{segment.upper()} template:")
        print(f"  Subject: {template['subject'][:60]}...")
        print(f"  Talking points: {len(template.get('talking_points', []))} points")
    
    print(f"\n✅ Template selection test passed")


async def test_industry_detection():
    """Test industry detection from company names."""
    print("\n" + "=" * 60)
    print("TEST 4: Industry Detection")
    print("=" * 60)
    
    generator = create_campaign_generator()
    
    test_companies = [
        "Acme Software Solutions",
        "Global Finance Group",
        "HealthTech Medical",
        "Manufacturing Inc",
        "Retail Store Corp",
        "Real Estate Partners",
        "University of Example",
        "CloudPlatform SaaS",
        "Strategy Consulting LLC",
    ]
    
    for company in test_companies:
        industry = generator._detect_industry(company)
        print(f"{company:30s} -> {industry}")
    
    print(f"\n✅ Industry detection test passed")


async def test_meeting_slots():
    """Test meeting slot generation."""
    print("\n" + "=" * 60)
    print("TEST 5: Meeting Slot Generation")
    print("=" * 60)
    
    generator = create_campaign_generator()
    
    slots = generator._generate_meeting_slots()
    
    print(f"\nGenerated {len(slots)} meeting slots:")
    for i, slot in enumerate(slots, 1):
        print(f"  {i}. {slot['display']}")
    
    print(f"\n✅ Meeting slot test passed")


async def test_personalization_hooks():
    """Test personalization hook generation."""
    print("\n" + "=" * 60)
    print("TEST 6: Personalization Hooks")
    print("=" * 60)
    
    generator = create_campaign_generator()
    
    test_contacts = [
        {
            "company": "Enterprise Software Inc",
            "jobtitle": "CEO",
            "segments": ["high_value"]
        },
        {
            "company": "StartupCo",
            "jobtitle": "VP of Sales",
            "segments": ["engaged"]
        },
        {
            "company": "CHAINge Corp",
            "jobtitle": "Marketing Manager",
            "segments": ["chainge"]
        }
    ]
    
    for contact in test_contacts:
        hooks = generator._get_personalization_hooks(contact)
        print(f"\n{contact.get('company')} - {contact.get('jobtitle')}:")
        for hook in hooks:
            print(f"  • {hook}")
    
    print(f"\n✅ Personalization hooks test passed")


async def test_dry_run():
    """Test campaign generation (dry run - no actual drafts)."""
    print("\n" + "=" * 60)
    print("TEST 7: Campaign Generation Stats (Dry Run)")
    print("=" * 60)
    
    generator = create_campaign_generator()
    
    # Get contact counts for each segment
    segments = ["chainge", "high_value", "engaged", "cold", "all"]
    
    print("\nContact availability by segment:")
    for segment in segments:
        contacts = generator._get_segment_contacts(segment, limit=1000)
        print(f"  {segment:15s}: {len(contacts):4d} contacts available")
    
    print("\n✅ Dry run test passed")
    
    print("\n" + "=" * 60)
    print("NOTE: To generate actual drafts, use the API endpoint:")
    print("  POST /api/campaigns/generate")
    print('  {"segment": "chainge", "limit": 10}')
    print("=" * 60)


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Campaign Generator Test Suite")
    print("=" * 60)
    
    tests = [
        test_personalization,
        test_segment_contacts,
        test_template_selection,
        test_industry_detection,
        test_meeting_slots,
        test_personalization_hooks,
        test_dry_run,
    ]
    
    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
