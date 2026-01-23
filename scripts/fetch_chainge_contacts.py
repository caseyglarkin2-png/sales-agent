#!/usr/bin/env python3
"""
Import CHAINge NA form submissions from HubSpot.
Runs standalone and saves results.
"""
import requests
import json
import os
from datetime import datetime

API_KEY = os.environ.get("HUBSPOT_API_KEY", "")
FORM_ID = os.environ.get("EXPECTED_HUBSPOT_FORM_ID", "db8b22de-c3d4-4fc6-9a16-011fe322e82c")
OUTPUT_FILE = "/workspaces/sales-agent/chainge_contacts.json"

def main():
    print("=" * 80)
    print("CHAINGE NA FORM SUBMISSION IMPORT")
    print("=" * 80)
    print(f"\nAPI Key: {API_KEY[:25]}...")
    print(f"Form ID: {FORM_ID}")
    print()
    
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    # Fetch all submissions (paginated)
    all_submissions = []
    after = None
    page = 1
    
    while True:
        print(f"Fetching page {page}...", end=" ")
        
        url = f"https://api.hubapi.com/form-integrations/v1/submissions/forms/{FORM_ID}"
        params = {"limit": 50}
        if after:
            params["after"] = after
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            print(f"Got {len(results)} submissions")
            
            all_submissions.extend(results)
            
            # Check for next page
            paging = data.get("paging", {})
            next_link = paging.get("next", {})
            after = next_link.get("after")
            
            if not after:
                break
            
            page += 1
            
        except requests.exceptions.HTTPError as e:
            print(f"\nHTTP Error: {e.response.status_code}")
            print(e.response.text[:500])
            break
        except Exception as e:
            print(f"\nError: {e}")
            break
    
    print(f"\nTotal submissions fetched: {len(all_submissions)}")
    
    # Process submissions
    contacts = []
    for submission in all_submissions:
        values = submission.get("values", [])
        
        contact = {
            "submitted_at": submission.get("submittedAt"),
            "page_url": submission.get("pageUrl", ""),
        }
        
        # Extract field values
        for field in values:
            name = field.get("name", "")
            value = field.get("value", "")
            contact[name] = value
        
        contacts.append(contact)
    
    # Save to file
    with open(OUTPUT_FILE, "w") as f:
        json.dump({
            "total": len(contacts),
            "fetched_at": datetime.now().isoformat(),
            "contacts": contacts
        }, f, indent=2)
    
    print(f"\n✅ Saved {len(contacts)} contacts to {OUTPUT_FILE}")
    
    # Show sample
    if contacts:
        print("\nSample contacts:")
        for i, contact in enumerate(contacts[:5], 1):
            print(f"\n{i}. Email: {contact.get('email', 'N/A')}")
            print(f"   Name: {contact.get('firstname', '')} {contact.get('lastname', '')}")
            print(f"   Company: {contact.get('company', 'N/A')}")
            print(f"   Submitted: {contact.get('submitted_at', 'N/A')}")
    
    return contacts

if __name__ == "__main__":
    try:
        contacts = main()
        print(f"\n🎉 SUCCESS!")
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
