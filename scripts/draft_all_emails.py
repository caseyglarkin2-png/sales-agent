#!/usr/bin/env python3
"""
Draft personalized emails for all CHAINge NA contacts.
Researches each contact and generates email proposals.
"""
import json
import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analysis import analyze_prospect
from src.draft_generator import generate_email_draft
from src.logger import get_logger

logger = get_logger(__name__)

CONTACTS_FILE = "/workspaces/sales-agent/chainge_contacts.json"
OUTPUT_FILE = "/workspaces/sales-agent/email_drafts.json"
STATUS_FILE = "/workspaces/sales-agent/draft_status.txt"

def log(msg):
    """Log to console and status file."""
    print(msg, flush=True)
    with open(STATUS_FILE, "a") as f:
        f.write(msg + "\n")

async def draft_emails():
    """Generate email drafts for all contacts."""
    
    # Clear status
    with open(STATUS_FILE, "w") as f:
        f.write(f"Started: {datetime.now()}\n")
    
    log("="*80)
    log("CHAINGE NA EMAIL DRAFTING")
    log("="*80)
    
    # Load contacts
    with open(CONTACTS_FILE, "r") as f:
        data = json.load(f)
    
    contacts = data["contacts"]
    log(f"\nLoaded {len(contacts)} contacts")
    
    # Process each contact
    results = []
    success_count = 0
    error_count = 0
    
    for i, contact in enumerate(contacts, 1):
        email = contact.get("email")
        name = f"{contact.get('firstname', '')} {contact.get('lastname', '')}".strip()
        company = contact.get("company", "")
        
        log(f"\n[{i}/{len(contacts)}] {name} <{email}> - {company}")
        
        try:
            # Research the prospect
            log(f"  → Researching...")
            prospect_data = {
                "email": email,
                "first_name": contact.get("firstname", ""),
                "last_name": contact.get("lastname", ""),
                "company": company,
                "phone": contact.get("phone"),
                "notes": contact.get("how_can_we_help_you_", ""),
            }
            
            research = await analyze_prospect(prospect_data)
            log(f"  → Research complete")
            
            # Generate email draft
            log(f"  → Generating email draft...")
            draft = await generate_email_draft(
                prospect_info=prospect_data,
                research_data=research,
                template_hints={"tone": "professional", "focus": "CHAINge NA event"}
            )
            
            results.append({
                "contact": prospect_data,
                "research": research,
                "draft": draft,
                "status": "success",
                "processed_at": datetime.now().isoformat()
            })
            
            success_count += 1
            log(f"  ✅ Draft created")
            
            # Save progress every 10 contacts
            if i % 10 == 0:
                with open(OUTPUT_FILE, "w") as f:
                    json.dump({
                        "total_processed": i,
                        "success_count": success_count,
                        "error_count": error_count,
                        "results": results
                    }, f, indent=2)
                log(f"\n💾 Progress saved ({i}/{len(contacts)})")
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error processing {email}: {e}")
            log(f"  ❌ Error: {str(e)[:100]}")
            results.append({
                "contact": prospect_data,
                "error": str(e),
                "status": "error",
                "processed_at": datetime.now().isoformat()
            })
            error_count += 1
    
    # Final save
    final_output = {
        "total_contacts": len(contacts),
        "success_count": success_count,
        "error_count": error_count,
        "completed_at": datetime.now().isoformat(),
        "results": results
    }
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(final_output, f, indent=2)
    
    log("\n" + "="*80)
    log(f"✅ COMPLETE!")
    log(f"   Total: {len(contacts)}")
    log(f"   Success: {success_count}")
    log(f"   Errors: {error_count}")
    log(f"   Output: {OUTPUT_FILE}")
    log("="*80)
    
    return final_output

if __name__ == "__main__":
    try:
        result = asyncio.run(draft_emails())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
