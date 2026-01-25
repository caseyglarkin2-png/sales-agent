#!/usr/bin/env python3
"""
UI Verification Script.
Checks that key UI assets are serving correctly from the production endpoint.
"""
import sys
import httpx
import asyncio

BASE_URL = "https://web-production-a6ccf.up.railway.app"

PAGES = [
    "/static/index.html",
    "/static/command-queue.html",
    "/static/jarvis.html",
    "/static/operator-dashboard.html",
    "/static/csrf-helper.js",  # CRITICAL
    "/health",
]

async def verify_url(client, path):
    url = f"{BASE_URL}{path}"
    try:
        response = await client.get(url, timeout=10.0)
        status = response.status_code
        if status == 200:
            print(f"✅ [200] {path} ({len(response.content)} bytes)")
            return True
        else:
            print(f"❌ [{status}] {path}")
            return False
    except Exception as e:
        print(f"❌ [ERR] {path}: {str(e)}")
        return False

async def main():
    print(f"🔍 Verifying UI assets at {BASE_URL}...")
    
    async with httpx.AsyncClient(verify=False) as client:  # verify=False for simplicity if certs issue
        results = await asyncio.gather(*[verify_url(client, p) for p in PAGES])
    
    if all(results):
        print("\n✨ All systems go! UI assets are deployed.")
        sys.exit(0)
    else:
        print("\n⚠️ Some assets failed to load.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
