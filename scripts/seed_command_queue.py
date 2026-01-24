#!/usr/bin/env python3
"""Seed Command Queue with Realistic Test Data.

Sprint 2 Task 2.4 - Development-only script to populate the queue
with realistic items for testing the Today's Moves UI.

Usage:
    python scripts/seed_command_queue.py          # Add test data
    python scripts/seed_command_queue.py --clear  # Clear then add
    python scripts/seed_command_queue.py --only-clear  # Just clear
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.models.command_queue import CommandQueueItem

# Production guard
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
if ENVIRONMENT == "production":
    print("❌ ERROR: Seeds disabled in production")
    print("   Production queue is populated by signal ingestion.")
    sys.exit(1)


# =============================================================================
# Test Data - Realistic sales scenarios
# =============================================================================

def generate_seed_data(owner_email: str = "casey@example.com") -> list[dict]:
    """Generate realistic command queue items."""
    now = datetime.utcnow()
    
    return [
        # High Priority - Follow-ups
        {
            "id": str(uuid4()),
            "title": "Follow up with Sarah at Acme Corp",
            "description": "She opened your proposal 5 times this week and visited pricing page yesterday.",
            "action_type": "follow_up",
            "priority_score": 92.5,
            "reasoning": "High engagement signals: 5 email opens, 3 pricing page visits, deal stage is Negotiation",
            "drivers": {"urgency": 9, "revenue": 10, "effort": 3, "strategic": 8},
            "contact_id": "hs_12345",
            "deal_id": "hs_deal_789",
            "company_id": "hs_comp_456",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(hours=2),
        },
        {
            "id": str(uuid4()),
            "title": "Send proposal to TechStart Inc",
            "description": "They requested pricing last call. Decision by EOW.",
            "action_type": "send_proposal",
            "priority_score": 89.0,
            "reasoning": "Deal stage advanced, budget confirmed at $50K, timeline is this quarter",
            "drivers": {"urgency": 10, "revenue": 9, "effort": 5, "strategic": 7},
            "contact_id": "hs_23456",
            "deal_id": "hs_deal_234",
            "company_id": "hs_comp_567",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(hours=4),
        },
        
        # High Priority - Meetings
        {
            "id": str(uuid4()),
            "title": "Book demo with DataFlow (Inbound Lead)",
            "description": "Hot inbound from G2 review page. Enterprise inquiry.",
            "action_type": "book_meeting",
            "priority_score": 87.5,
            "reasoning": "Inbound enterprise lead, mentioned budget and timeline in form",
            "drivers": {"urgency": 9, "revenue": 8, "effort": 2, "strategic": 9},
            "contact_id": "hs_34567",
            "deal_id": None,
            "company_id": "hs_comp_678",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(hours=3),
        },
        {
            "id": str(uuid4()),
            "title": "Prep for CloudNine demo tomorrow",
            "description": "Review their use case, prepare custom demo flow, check competitors mentioned.",
            "action_type": "prep_meeting",
            "priority_score": 85.0,
            "reasoning": "Demo scheduled for tomorrow 2pm, $75K opportunity, CTO attending",
            "drivers": {"urgency": 10, "revenue": 9, "effort": 6, "strategic": 8},
            "contact_id": "hs_45678",
            "deal_id": "hs_deal_345",
            "company_id": "hs_comp_789",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(hours=18),
        },
        
        # Medium Priority - Follow-ups
        {
            "id": str(uuid4()),
            "title": "Check in with Bright Solutions (Stuck Deal)",
            "description": "Deal stalled for 14 days. Last contact was positive but no next steps.",
            "action_type": "check_in",
            "priority_score": 72.0,
            "reasoning": "Deal stalled 14 days, was moving quickly before, worth re-engaging",
            "drivers": {"urgency": 6, "revenue": 8, "effort": 3, "strategic": 6},
            "contact_id": "hs_56789",
            "deal_id": "hs_deal_456",
            "company_id": "hs_comp_890",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(days=1),
        },
        {
            "id": str(uuid4()),
            "title": "Send case study to InfoSec Pro",
            "description": "They asked about security compliance. Send the FinTech case study.",
            "action_type": "send_email",
            "priority_score": 68.5,
            "reasoning": "Specific ask from prospect, easy to fulfill, keeps deal moving",
            "drivers": {"urgency": 5, "revenue": 7, "effort": 2, "strategic": 6},
            "contact_id": "hs_67890",
            "deal_id": "hs_deal_567",
            "company_id": "hs_comp_901",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(days=1),
        },
        
        # Medium Priority - Deal Reviews
        {
            "id": str(uuid4()),
            "title": "Review MegaCorp deal pipeline",
            "description": "Multiple contacts, complex org chart. Map stakeholders before next call.",
            "action_type": "review_deal",
            "priority_score": 65.0,
            "reasoning": "Large deal ($120K), need stakeholder mapping, call next week",
            "drivers": {"urgency": 4, "revenue": 10, "effort": 7, "strategic": 9},
            "contact_id": None,
            "deal_id": "hs_deal_678",
            "company_id": "hs_comp_012",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(days=2),
        },
        {
            "id": str(uuid4()),
            "title": "Update GlobalTech deal notes",
            "description": "Call notes from Tuesday need to be logged. Champion info mentioned.",
            "action_type": "review_deal",
            "priority_score": 55.0,
            "reasoning": "Hygiene task, but important for team visibility and handoff",
            "drivers": {"urgency": 3, "revenue": 6, "effort": 2, "strategic": 5},
            "contact_id": "hs_78901",
            "deal_id": "hs_deal_789",
            "company_id": "hs_comp_123",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(days=3),
        },
        
        # Lower Priority - Nurture
        {
            "id": str(uuid4()),
            "title": "Send nurture email to StartupXYZ",
            "description": "Not ready to buy yet, but showed interest. Add to nurture sequence.",
            "action_type": "send_email",
            "priority_score": 45.0,
            "reasoning": "Long-term prospect, budget next quarter, stay top of mind",
            "drivers": {"urgency": 2, "revenue": 5, "effort": 2, "strategic": 4},
            "contact_id": "hs_89012",
            "deal_id": None,
            "company_id": "hs_comp_234",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(days=5),
        },
        {
            "id": str(uuid4()),
            "title": "LinkedIn connect with DevOps lead at ScaleUp",
            "description": "New contact from conference. Warm intro opportunity.",
            "action_type": "follow_up",
            "priority_score": 38.0,
            "reasoning": "Conference lead, early stage, build relationship",
            "drivers": {"urgency": 2, "revenue": 4, "effort": 1, "strategic": 5},
            "contact_id": "hs_90123",
            "deal_id": None,
            "company_id": "hs_comp_345",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(days=7),
        },
        
        # Additional variety
        {
            "id": str(uuid4()),
            "title": "Follow up on Quantum Labs trial",
            "description": "Trial ends in 3 days. Check usage and schedule conversion call.",
            "action_type": "follow_up",
            "priority_score": 82.0,
            "reasoning": "Trial ending soon, good usage metrics, convert to paid",
            "drivers": {"urgency": 9, "revenue": 7, "effort": 3, "strategic": 7},
            "contact_id": "hs_01234",
            "deal_id": "hs_deal_890",
            "company_id": "hs_comp_456",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(days=2),
        },
        {
            "id": str(uuid4()),
            "title": "Send ROI calculator to FinanceFirst",
            "description": "CFO asked for business case justification. Use the ROI template.",
            "action_type": "send_email",
            "priority_score": 76.0,
            "reasoning": "CFO engagement, deal blocker resolution, $60K opportunity",
            "drivers": {"urgency": 7, "revenue": 8, "effort": 4, "strategic": 7},
            "contact_id": "hs_12345b",
            "deal_id": "hs_deal_901",
            "company_id": "hs_comp_567b",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(hours=6),
        },
        {
            "id": str(uuid4()),
            "title": "Book renewal call with LoyalCustomer Inc",
            "description": "Contract up in 45 days. Proactive renewal + upsell opportunity.",
            "action_type": "book_meeting",
            "priority_score": 70.0,
            "reasoning": "Existing customer, renewal due, upsell signal from usage growth",
            "drivers": {"urgency": 5, "revenue": 7, "effort": 2, "strategic": 8},
            "contact_id": "hs_23456b",
            "deal_id": "hs_deal_012",
            "company_id": "hs_comp_678b",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(days=4),
        },
        {
            "id": str(uuid4()),
            "title": "Competitive intel on FastGrow deal",
            "description": "Competitor mentioned in discovery. Research their weaknesses.",
            "action_type": "review_deal",
            "priority_score": 62.0,
            "reasoning": "Competitive deal, need battle card prep, demo next week",
            "drivers": {"urgency": 5, "revenue": 6, "effort": 5, "strategic": 8},
            "contact_id": "hs_34567b",
            "deal_id": "hs_deal_123",
            "company_id": "hs_comp_789b",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(days=3),
        },
        {
            "id": str(uuid4()),
            "title": "Thank you email to referral source",
            "description": "Hot lead came from existing customer. Send appreciation + update.",
            "action_type": "send_email",
            "priority_score": 48.0,
            "reasoning": "Relationship maintenance, referral pipeline health",
            "drivers": {"urgency": 3, "revenue": 3, "effort": 1, "strategic": 6},
            "contact_id": "hs_45678b",
            "deal_id": None,
            "company_id": "hs_comp_890b",
            "status": "pending",
            "owner": owner_email,
            "due_by": now + timedelta(days=2),
        },
    ]


# =============================================================================
# Main Script
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Seed command queue with test data")
    parser.add_argument("--clear", action="store_true", help="Clear existing items first")
    parser.add_argument("--only-clear", action="store_true", help="Only clear, don't add new items")
    parser.add_argument("--owner", default="casey@pesti.io", help="Owner email for items")
    args = parser.parse_args()
    
    # Get database URL
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not set")
        sys.exit(1)
    
    # Convert to async URL if needed
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Create engine and session
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Check if queue has items
        result = await db.execute(select(CommandQueueItem).limit(1))
        has_items = result.scalar_one_or_none() is not None
        
        if has_items and not args.clear and not args.only_clear:
            print("⚠️  Queue is not empty. Use --clear to clear first.")
            print("   Existing items will not be overwritten.")
            return
        
        if args.clear or args.only_clear:
            print("🧹 Clearing existing queue items...")
            await db.execute(delete(CommandQueueItem))
            await db.commit()
            print("   ✓ Cleared")
        
        if args.only_clear:
            print("Done (clear only mode)")
            return
        
        # Generate and insert items
        print(f"🌱 Seeding queue for owner: {args.owner}")
        items_data = generate_seed_data(args.owner)
        
        for item_data in items_data:
            item = CommandQueueItem(
                id=item_data["id"],
                title=item_data["title"],
                description=item_data.get("description"),
                action_type=item_data["action_type"],
                priority_score=item_data["priority_score"],
                reasoning=item_data.get("reasoning"),
                drivers=item_data.get("drivers"),
                contact_id=item_data.get("contact_id"),
                deal_id=item_data.get("deal_id"),
                company_id=item_data.get("company_id"),
                status=item_data.get("status", "pending"),
                owner=item_data.get("owner", args.owner),
                due_by=item_data.get("due_by"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(item)
        
        await db.commit()
        print(f"   ✓ Added {len(items_data)} items")
        
        # Summary
        print("\n📊 Queue Summary:")
        print(f"   High Priority (75+):   {len([i for i in items_data if i['priority_score'] >= 75])}")
        print(f"   Medium Priority (50-74): {len([i for i in items_data if 50 <= i['priority_score'] < 75])}")
        print(f"   Lower Priority (<50):  {len([i for i in items_data if i['priority_score'] < 50])}")
        print("\n✅ Done! View at /todays-moves")


if __name__ == "__main__":
    asyncio.run(main())
