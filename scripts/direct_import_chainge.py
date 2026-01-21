#!/usr/bin/env python3
"""
Direct import of CHAINge NA form submissions from HubSpot.
This version works without the API server running.
"""
import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.forms.form_importer import FormSubmissionImporter
from src.connectors.hubspot import HubSpotConnector


async def main():
    """Import CHAINge NA submissions directly."""
    
    print("=" * 80)
    print("🚀 CHAINGE NA FORM SUBMISSION IMPORT (DIRECT)")
    print("=" * 80)
    
    # Initialize form importer
    api_key = os.environ.get("HUBSPOT_API_KEY")
    if not api_key:
        print("❌ Error: HUBSPOT_API_KEY not set")
        return
    
    form_id = os.environ.get("EXPECTED_HUBSPOT_FORM_ID", "db8b22de-c3d4-4fc6-9a16-011fe322e82c")
    
    print(f"\n📋 Configuration:")
    print(f"   HubSpot API Key: {api_key[:20]}...")
    print(f"   Form ID: {form_id}")
    
    hubspot = HubSpotConnector(api_key)
    importer = FormSubmissionImporter(hubspot)
    
    # Step 1: Get form submissions
    print(f"\n📥 Step 1: Fetching form submissions...")
    submissions = await importer.get_form_submissions(form_id)
    
    print(f"   Total submissions found: {len(submissions)}")
    
    if not submissions:
        print("\n⚠️  No submissions found. Possible reasons:")
        print("   1. Form ID is incorrect")
        print("   2. No submissions exist for this form")
        print("   3. API permissions issue")
        return
    
    # Step 2: Process each submission
    print(f"\n🔄 Step 2: Processing {len(submissions)} submissions...")
    
    contacts = []
    for i, submission in enumerate(submissions, 1):
        if i % 50 == 0:
            print(f"   Processed {i}/{len(submissions)}...")
        
        # Extract contact info
        values = submission.get("values", [])
        email = None
        first_name = None
        last_name = None
        company = None
        
        for field in values:
            name = field.get("name", "").lower()
            value = field.get("value", "")
            
            if "email" in name:
                email = value
            elif "firstname" in name or "first_name" in name:
                first_name = value
            elif "lastname" in name or "last_name" in name:
                last_name = value
            elif "company" in name:
                company = value
        
        if email:
            contact = {
                "email": email,
                "first_name": first_name or "",
                "last_name": last_name or "",
                "company": company or "",
                "source": "CHAINge NA Form",
                "submitted_at": submission.get("submittedAt"),
            }
            contacts.append(contact)
    
    print(f"\n✅ Step 3: Summary")
    print(f"   Total submissions: {len(submissions)}")
    print(f"   Valid contacts (with email): {len(contacts)}")
    
    # Save to file
    output_file = "/workspaces/sales-agent/chainge_contacts.json"
    import json
    with open(output_file, "w") as f:
        json.dump(contacts, f, indent=2)
    
    print(f"\n💾 Saved contacts to: {output_file}")
    
    # Display sample
    if contacts:
        print(f"\n📊 Sample contacts:")
        for contact in contacts[:5]:
            print(f"   • {contact.get('first_name')} {contact.get('last_name')} <{contact.get('email')}>")
            if contact.get('company'):
                print(f"     Company: {contact.get('company')}")
    
    return contacts


if __name__ == "__main__":
    contacts = asyncio.run(main())
    if contacts:
        print(f"\n🎉 SUCCESS! Imported {len(contacts)} contacts from CHAINge NA form")
    else:
        print(f"\n❌ FAILED: No contacts imported")
