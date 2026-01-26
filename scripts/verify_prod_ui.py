import httpx
import asyncio

BASE_URL = "https://web-production-a6ccf.up.railway.app"

async def check_url(client, path):
    try:
        response = await client.get(f"{BASE_URL}{path}", follow_redirects=True)
        print(f"[{response.status_code}] {path}")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        if response.status_code != 200:
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"Error checking {path}: {e}")

async def main():
    async with httpx.AsyncClient() as client:
        print(f"Checking {BASE_URL}...")
        await check_url(client, "/caseyos")
        await check_url(client, "/caseyos/queue")
        await check_url(client, "/static/caseyos/styles.css") # Check if old asset path is confused

if __name__ == "__main__":
    asyncio.run(main())
