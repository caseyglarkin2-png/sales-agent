#!/usr/bin/env python3
import requests
import json
import sys

STATUS_FILE = "/workspaces/sales-agent/import_status.txt"
OUTPUT_FILE = "/workspaces/sales-agent/chainge_contacts.json"

def log(msg):
    """Log to both console and status file."""
    print(msg, flush=True)
    with open(STATUS_FILE, "a") as f:
        f.write(msg + "\n")

try:
    # Clear status file
    with open(STATUS_FILE, "w") as f:
        f.write("Starting import...\n")
    
    API_KEY = "pat-na1-d0dca073-79c0-43fd-a2d2-124c27c6e247"
    FORM_ID = "db8b22de-c3d4-4fc6-9a16-011fe322e82c"
    
    log("="*60)
    log("CHAINGE NA IMPORT")
    log("="*60)
    log(f"API Key: {API_KEY[:25]}...")
    log(f"Form ID: {FORM_ID}")
    
    headers = {"Authorization": f"Bearer {API_KEY}"}
    all_submissions = []
    page = 1
    after = None
    
    while True:
        log(f"\nPage {page}...")
        
        url = f"https://api.hubapi.com/form-integrations/v1/submissions/forms/{FORM_ID}"
        params = {"limit": 50}
        if after:
            params["after"] = after
        
        r = requests.get(url, headers=headers, params=params, timeout=30)
        log(f"Status: {r.status_code}")
        
        if r.status_code != 200:
            log(f"ERROR: {r.text[:300]}")
            sys.exit(1)
        
        data = r.json()
        results = data.get("results", [])
        log(f"Got {len(results)} submissions")
        
        all_submissions.extend(results)
        
        paging = data.get("paging", {})
        next_link = paging.get("next", {})
        after = next_link.get("after")
        
        if not after:
            log("No more pages")
            break
        
        page += 1
    
    log(f"\nTOTAL: {len(all_submissions)} submissions")
    
    # Process
    contacts = []
    for sub in all_submissions:
        contact = {"submitted_at": sub.get("submittedAt")}
        for field in sub.get("values", []):
            contact[field.get("name")] = field.get("value")
        contacts.append(contact)
    
    # Save
    with open(OUTPUT_FILE, "w") as f:
        json.dump({"total": len(contacts), "contacts": contacts}, f, indent=2)
    
    log(f"\nSAVED to {OUTPUT_FILE}")
    log(f"SUCCESS - {len(contacts)} contacts imported")
    
    # Sample
    if contacts:
        log("\nSAMPLE:")
        for i, c in enumerate(contacts[:3], 1):
            log(f"{i}. {c.get('email')} - {c.get('firstname')} {c.get('lastname')}")

except Exception as e:
    log(f"\nFATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    with open(STATUS_FILE, "a") as f:
        traceback.print_exc(file=f)
    sys.exit(1)
