#!/usr/bin/env python3
"""Add test freight/logistics contacts to the queue."""
import asyncio
import httpx

async def add_test_contacts():
    """Add freight industry test contacts."""
    base = "http://localhost:8000"
    
    contacts = [
        {
            "email": "john.smith@freightco.com",
            "first_name": "John",
            "last_name": "Smith",
            "company": "Freight Solutions Inc",
            "job_title": "VP of Operations",
            "voice_profile": "freight_marketer_voice",
            "priority": 1
        },
        {
            "email": "sarah.johnson@logistics.com",
            "first_name": "Sarah",
            "last_name": "Johnson",
            "company": "Logistics Dynamics",
            "job_title": "Director of Supply Chain",
            "voice_profile": "freight_marketer_voice",
            "priority": 1
        },
        {
            "email": "mike.davis@trucking.net",
            "first_name": "Mike",
            "last_name": "Davis",
            "company": "Davis Trucking Co",
            "job_title": "CEO",
            "voice_profile": "freight_marketer_voice",
            "priority": 2
        },
        {
            "email": "lisa.chen@shipping.io",
            "first_name": "Lisa",
            "last_name": "Chen",
            "company": "Global Shipping Partners",
            "job_title": "Head of Marketing",
            "voice_profile": "freight_marketer_voice",
            "priority": 0
        },
        {
            "email": "robert.williams@3pl.com",
            "first_name": "Robert",
            "last_name": "Williams",
            "company": "Williams 3PL Solutions",
            "job_title": "VP Business Development",
            "voice_profile": "freight_marketer_voice",
            "priority": 1
        }
    ]
    
    async with httpx.AsyncClient() as client:
        print("Adding test contacts to queue...")
        response = await client.post(
            f"{base}/api/contact-queue/add-bulk",
            json=contacts
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Added {result['contacts_added']} contacts")
            print(f"Contact IDs: {result['contact_ids'][:3]}...")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    asyncio.run(add_test_contacts())
