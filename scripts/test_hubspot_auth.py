#!/usr/bin/env python3
"""
Test different HubSpot authentication methods.
"""
import asyncio
import os
import httpx

APP_ID = os.environ.get("HUBSPOT_API_KEY", "")
FORM_ID = os.environ.get("EXPECTED_HUBSPOT_FORM_ID", "")


async def test_auth_methods():
    """Try different authentication approaches."""
    
    print("=" * 80)
    print("🔐 TESTING HUBSPOT AUTHENTICATION METHODS")
    print("=" * 80)
    
    print(f"\nApp ID: {APP_ID}")
    print(f"Form ID: {FORM_ID}")
    
    async with httpx.AsyncClient(timeout=30) as client:
        
        # Method 1: Bearer token (private app)
        print("\n📋 Method 1: Bearer token authentication...")
        try:
            headers = {
                "Authorization": f"Bearer {APP_ID}",
                "Content-Type": "application/json",
            }
            response = await client.get(
                "https://api.hubapi.com/crm/v3/objects/contacts?limit=1",
                headers=headers
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ SUCCESS with Bearer token!")
                return
            else:
                print(f"   ❌ {response.text[:200]}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        # Method 2: API key parameter
        print("\n📋 Method 2: API key as query parameter...")
        try:
            response = await client.get(
                f"https://api.hubapi.com/crm/v3/objects/contacts?hapikey={APP_ID}&limit=1"
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ SUCCESS with hapikey parameter!")
                return
            else:
                print(f"   ❌ {response.text[:200]}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        # Method 3: Get form submissions directly with form ID
        if FORM_ID:
            print(f"\n📋 Method 3: Direct form submissions API (Form ID: {FORM_ID})...")
            try:
                headers = {
                    "Authorization": f"Bearer {APP_ID}",
                }
                response = await client.get(
                    f"https://api.hubapi.com/form-integrations/v1/submissions/forms/{FORM_ID}",
                    headers=headers,
                    params={"limit": 50}
                )
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ SUCCESS! Found {len(data.get('results', []))} submissions")
                    return data
                else:
                    print(f"   ❌ {response.text[:200]}")
            except Exception as e:
                print(f"   ❌ Exception: {e}")
        
        print("\n⚠️  All authentication methods failed.")
        print("Please check:")
        print("  1. HubSpot private app access token is correct")
        print("  2. Token has required scopes (crm.objects.contacts.read, forms)")
        print("  3. Token is not expired")


if __name__ == "__main__":
    asyncio.run(test_auth_methods())
