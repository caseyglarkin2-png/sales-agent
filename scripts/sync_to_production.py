#!/usr/bin/env python3
"""
Transform and sync email drafts to production.

This script:
1. Reads the raw email_drafts.json file
2. Transforms to the API-expected format
3. Posts to the production bulk-load-drafts endpoint
"""

import json
import os
import sys
import requests
from datetime import datetime

# Configuration
PRODUCTION_URL = os.environ.get(
    "PRODUCTION_URL", 
    "https://web-production-a6ccf.up.railway.app"
)
INPUT_FILE = os.environ.get("INPUT_FILE", "email_drafts.json")
BATCH_SIZE = 50  # Send in batches to avoid timeouts


def transform_draft(raw_item: dict) -> dict | None:
    """Transform raw draft to API format."""
    if raw_item.get("status") != "success":
        return None
    
    contact = raw_item.get("contact", {})
    body = raw_item.get("draft", "")
    company = contact.get("company", "")
    
    # Generate subject from company/context
    request = contact.get("request", "")
    if "sponsor" in request.lower():
        subject = f"CHAINge NA 2026 - Sponsorship Opportunities for {company}"
    elif "exhib" in request.lower():
        subject = f"CHAINge NA 2026 - Exhibition Options for {company}"
    elif "speak" in request.lower():
        subject = f"CHAINge NA 2026 - Speaking Opportunities"
    else:
        subject = f"CHAINge NA 2026 - Thank You for Your Interest"
    
    return {
        "recipient": contact.get("email", ""),
        "recipient_name": contact.get("name", ""),
        "company_name": company,
        "subject": subject,
        "body": body,
        "request": request,
    }


def load_and_transform(input_file: str) -> list[dict]:
    """Load and transform all drafts."""
    print(f"📂 Loading {input_file}...")
    
    with open(input_file, "r") as f:
        raw_data = json.load(f)
    
    # Handle both formats: direct list or wrapped in {"results": [...]}
    if isinstance(raw_data, dict) and "results" in raw_data:
        items = raw_data["results"]
        print(f"   Found {len(items)} items in 'results' array")
    elif isinstance(raw_data, list):
        items = raw_data
        print(f"   Found {len(items)} items in list")
    else:
        print(f"   Unknown format: {type(raw_data)}")
        return []
    
    transformed = []
    for item in items:
        draft = transform_draft(item)
        if draft:
            transformed.append(draft)
    
    print(f"   Transformed {len(transformed)} drafts")
    return transformed


def sync_to_production(drafts: list[dict], production_url: str) -> dict:
    """Send drafts to production in batches."""
    endpoint = f"{production_url}/api/operator/bulk-load-drafts"
    
    total_loaded = 0
    total_skipped = 0
    all_errors = []
    
    # Send in batches
    for i in range(0, len(drafts), BATCH_SIZE):
        batch = drafts[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(drafts) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"   Sending batch {batch_num}/{total_batches} ({len(batch)} drafts)...")
        
        try:
            response = requests.post(
                endpoint,
                json={"drafts": batch, "source": "chainge_import"},
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            
            if response.status_code == 200:
                result = response.json()
                total_loaded += result.get("loaded", 0)
                total_skipped += result.get("skipped", 0)
                all_errors.extend(result.get("errors", []))
                print(f"      ✅ Batch {batch_num}: {result.get('loaded', 0)} loaded")
            else:
                print(f"      ❌ Batch {batch_num} failed: {response.status_code}")
                print(f"         {response.text[:200]}")
                total_skipped += len(batch)
                
        except requests.exceptions.RequestException as e:
            print(f"      ❌ Batch {batch_num} error: {e}")
            total_skipped += len(batch)
    
    return {
        "loaded": total_loaded,
        "skipped": total_skipped,
        "errors": all_errors,
    }


def verify_production(production_url: str) -> dict:
    """Verify drafts are visible in production."""
    drafts_url = f"{production_url}/api/drafts"
    status_url = f"{production_url}/api/status"
    
    print(f"\n🔍 Verifying production state...")
    
    try:
        # Check status
        status_resp = requests.get(status_url, timeout=10)
        status = status_resp.json() if status_resp.ok else {}
        
        # Check drafts
        drafts_resp = requests.get(drafts_url, timeout=10)
        drafts = drafts_resp.json() if drafts_resp.ok else {}
        
        return {
            "status": status,
            "drafts_total": drafts.get("total", 0),
            "pending_drafts": status.get("pending_drafts", 0),
        }
        
    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
        return {}


def main():
    print("=" * 60)
    print("🚀 CHAINge NA Drafts Sync to Production")
    print("=" * 60)
    print(f"   Production URL: {PRODUCTION_URL}")
    print(f"   Input file: {INPUT_FILE}")
    print()
    
    # Check production health first
    try:
        health = requests.get(f"{PRODUCTION_URL}/health", timeout=10)
        if not health.ok:
            print("❌ Production server not healthy!")
            sys.exit(1)
        print("✅ Production server is healthy")
    except Exception as e:
        print(f"❌ Cannot reach production: {e}")
        sys.exit(1)
    
    # Load and transform
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input file not found: {INPUT_FILE}")
        sys.exit(1)
    
    drafts = load_and_transform(INPUT_FILE)
    
    if not drafts:
        print("❌ No valid drafts to sync")
        sys.exit(1)
    
    # Confirm before syncing
    print(f"\n📝 Ready to sync {len(drafts)} drafts to production")
    confirm = input("   Continue? [y/N]: ").strip().lower()
    if confirm != "y":
        print("   Aborted.")
        sys.exit(0)
    
    # Sync
    print(f"\n📤 Syncing to production...")
    result = sync_to_production(drafts, PRODUCTION_URL)
    
    print(f"\n📊 Sync Results:")
    print(f"   ✅ Loaded: {result['loaded']}")
    print(f"   ⏭️  Skipped: {result['skipped']}")
    if result.get("errors"):
        print(f"   ❌ Errors: {len(result['errors'])}")
    
    # Verify
    verification = verify_production(PRODUCTION_URL)
    if verification:
        print(f"\n📊 Production State:")
        print(f"   Pending drafts: {verification.get('pending_drafts', 'unknown')}")
        print(f"   Total drafts: {verification.get('drafts_total', 'unknown')}")
    
    print("\n✅ Sync complete!")
    print(f"   View at: {PRODUCTION_URL}")


if __name__ == "__main__":
    main()
