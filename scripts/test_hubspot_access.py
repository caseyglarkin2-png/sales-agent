#!/usr/bin/env python3
"""
Diagnostic script to test HubSpot API access and find CHAINge NA submissions.
"""
import asyncio
import os
import httpx
from datetime import datetime, timedelta

HUBSPOT_API_KEY = os.environ.get("HUBSPOT_API_KEY", "")
BASE_URL = "https://api.hubapi.com"


async def test_hubspot_access():
    """Test HubSpot API access and search for contacts."""
    
    print("=" * 80)
    print("🔍 HUBSPOT API DIAGNOSTIC")
    print("=" * 80)
    
    if not HUBSPOT_API_KEY:
        print("\n❌ HUBSPOT_API_KEY not set!")
        print("   Set it with: export HUBSPOT_API_KEY='your_key_here'")
        return
    
    print(f"\n✅ API Key found: {HUBSPOT_API_KEY[:10]}...{HUBSPOT_API_KEY[-4:]}")
    
    headers = {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        
        # Test 1: Get account info
        print("\n📋 Test 1: Checking API access...")
        try:
            response = await client.get(
                f"{BASE_URL}/crm/v3/objects/contacts",
                headers=headers,
                params={"limit": 1}
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ API access confirmed")
            else:
                print(f"   ❌ Error: {response.text}")
                return
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return
        
        # Test 2: Count total contacts
        print("\n📋 Test 2: Counting total contacts...")
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=365)
            cutoff_timestamp = int(cutoff_date.timestamp() * 1000)
            
            payload = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "createdate",
                        "operator": "GTE",
                        "value": str(cutoff_timestamp)
                    }]
                }],
                "properties": ["email", "firstname", "lastname", "company"],
                "limit": 100
            }
            
            response = await client.post(
                f"{BASE_URL}/crm/v3/objects/contacts/search",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                total = data.get("total", 0)
                print(f"   ✅ Found {len(results)} contacts (showing first 100 of {total} total)")
                
                # Show sample
                for i, contact in enumerate(results[:5], 1):
                    props = contact.get("properties", {})
                    email = props.get("email", "")
                    firstname = props.get("firstname", "")
                    lastname = props.get("lastname", "")
                    company = props.get("company", "")
                    print(f"      {i}. {firstname} {lastname} ({email}) - {company}")
                
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        # Test 3: Search for "CHAINge" in various fields
        print("\n📋 Test 3: Searching for 'CHAINge' references...")
        try:
            # Search in form conversion events
            payload = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "recent_conversion_event_name",
                        "operator": "CONTAINS_TOKEN",
                        "value": "CHAINge"
                    }]
                }],
                "properties": [
                    "email", "firstname", "lastname", "company",
                    "recent_conversion_event_name", "recent_conversion_date",
                    "hs_analytics_source", "hs_analytics_source_data_1"
                ],
                "limit": 100
            }
            
            response = await client.post(
                f"{BASE_URL}/crm/v3/objects/contacts/search",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"   ✅ Found {len(results)} contacts with CHAINge in conversion event")
                
                for i, contact in enumerate(results[:10], 1):
                    props = contact.get("properties", {})
                    email = props.get("email", "")
                    conversion_event = props.get("recent_conversion_event_name", "")
                    print(f"      {i}. {email} - Event: {conversion_event}")
            else:
                print(f"   ⚠️  No contacts found with CHAINge filter")
                print(f"   Status: {response.status_code}")
        except Exception as e:
            print(f"   ⚠️  Exception: {e}")
        
        # Test 4: Get forms list
        print("\n📋 Test 4: Listing available forms...")
        try:
            response = await client.get(
                f"{BASE_URL}/marketing/v3/forms",
                headers=headers,
                params={"limit": 50}
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"   ✅ Found {len(results)} forms")
                
                chainge_forms = []
                for form in results:
                    name = form.get("name", "")
                    form_id = form.get("id", "")
                    if "chainge" in name.lower() or "chain" in name.lower():
                        chainge_forms.append((name, form_id))
                        print(f"      🎯 FOUND: {name} (ID: {form_id})")
                
                if not chainge_forms:
                    print(f"   ⚠️  No forms with 'CHAINge' in name")
                    print(f"   All forms:")
                    for form in results[:10]:
                        print(f"      • {form.get('name', 'Unnamed')}")
            else:
                print(f"   ⚠️  Could not list forms: {response.status_code}")
                print(f"   {response.text}")
        except Exception as e:
            print(f"   ⚠️  Exception: {e}")
        
        print("\n" + "=" * 80)
        print("DIAGNOSTIC COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_hubspot_access())
