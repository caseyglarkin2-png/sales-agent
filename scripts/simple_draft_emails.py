#!/usr/bin/env python3
"""
Simple email draft generator for CHAINge NA contacts.
Uses OpenAI API directly.
"""
import json
import os
import sys
from datetime import datetime
from openai import OpenAI

CONTACTS_FILE = "/workspaces/sales-agent/chainge_contacts.json"
OUTPUT_FILE = "/workspaces/sales-agent/email_drafts.json"
STATUS_FILE = "/workspaces/sales-agent/draft_status.txt"

def log(msg):
    """Log to console and status file."""
    print(msg, flush=True)
    with open(STATUS_FILE, "a") as f:
        f.write(msg + "\n")

def generate_email(contact, client):
    """Generate a personalized email for a contact."""
    
    name = f"{contact.get('firstname', '')} {contact.get('lastname', '')}".strip()
    company = contact.get('company', '')
    request = contact.get('how_can_we_help_you_', '')
    
    prompt = f"""Write a personalized outreach email for CHAINge NA (logistics and supply chain conference).

Contact Info:
- Name: {name}
- Company: {company}
- Their request: {request}

Context:
- They filled out a form asking about CHAINge NA
- CHAINge NA is a premier logistics and supply chain conference
- We want to provide them with relevant information based on their request

Write an email that:
1. Addresses them by first name
2. References their specific request
3. Provides relevant information about CHAINge NA (exhibiting, sponsorship, speaking opportunities, etc.)
4. Has a friendly, professional tone
5. Includes a clear call-to-action
6. Keeps it concise (3-4 paragraphs max)

Do not include subject line. Just write the email body."""

    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": "You are a helpful sales assistant for CHAINge NA conference, writing personalized outreach emails."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content.strip()

def main():
    """Generate email drafts for all contacts."""
    
    # Clear status
    with open(STATUS_FILE, "w") as f:
        f.write(f"Started: {datetime.now()}\n")
    
    log("="*80)
    log("CHAINGE NA EMAIL DRAFTING")
    log("="*80)
    
    # Initialize OpenAI
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        log("❌ OPENAI_API_KEY not set")
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)
    
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
            # Generate email draft
            log(f"  → Generating email...")
            draft = generate_email(contact, client)
            
            results.append({
                "contact": {
                    "email": email,
                    "name": name,
                    "company": company,
                    "request": contact.get("how_can_we_help_you_", ""),
                },
                "draft": draft,
                "status": "success",
                "processed_at": datetime.now().isoformat()
            })
            
            success_count += 1
            log(f"  ✅ Draft created ({len(draft)} chars)")
            
            # Save progress every 20 contacts
            if i % 20 == 0:
                with open(OUTPUT_FILE, "w") as f:
                    json.dump({
                        "total_processed": i,
                        "success_count": success_count,
                        "error_count": error_count,
                        "results": results
                    }, f, indent=2)
                log(f"\n💾 Progress saved ({i}/{len(contacts)})")
            
        except Exception as e:
            log(f"  ❌ Error: {str(e)[:100]}")
            results.append({
                "contact": {
                    "email": email,
                    "name": name,
                    "company": company,
                },
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
        result = main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
