#!/usr/bin/env python3
"""Quick test of HubSpot form submissions API."""
import asyncio
import os
import httpx
import json

API_KEY = os.environ.get("HUBSPOT_API_KEY", "")
FORM_ID = os.environ.get("EXPECTED_HUBSPOT_FORM_ID", "db8b22de-c3d4-4fc6-9a16-011fe322e82c")

async def test():
    async with httpx.AsyncClient(timeout=30) as client:
        # Try form submissions API
        print("Testing form submissions API...")
        url = f"https://api.hubapi.com/form-integrations/v1/submissions/forms/{FORM_ID}"
        headers = {"Authorization": f"Bearer {API_KEY}"}
        
        try:
            response = await client.get(url, headers=headers, params={"limit": 10})
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Results: {len(data.get('results', []))}")
                
                # Save to file
                with open("/tmp/submissions.json", "w") as f:
                    json.dump(data, f, indent=2)
                print("Saved to /tmp/submissions.json")
                
                # Show sample
                if data.get("results"):
                    print("\nSample submission:")
                    print(json.dumps(data["results"][0], indent=2)[:500])
            else:
                print(f"Error: {response.text[:500]}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test())
