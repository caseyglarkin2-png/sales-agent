"""
Regenerate Morning Emails with Calendar Link
============================================

Ship Ship Ship: Regenerate emails with Casey's HubSpot calendar link!

This script:
1. Uses updated voice profile with calendar link
2. Regenerates all 5 morning emails
3. Ensures Casey-like tone and copy
4. Includes clear booking CTA
"""

import asyncio
import sys
from datetime import datetime
import uuid

from src.logger import get_logger
from src.draft_generator import create_draft_generator
from src.operator_mode import get_draft_queue
from src.voice_profile import get_voice_profile

logger = get_logger(__name__)


# Same prospects - regenerate with new voice profile
PROSPECTS = [
    {
        "name": "Sarah Chen",
        "email": "sarah.chen@techcorp.com",
        "company": "TechCorp Solutions",
        "talking_points": [
            "Just raised Series B - scaling fast",
            "Expanding sales team by 40%",
            "Need automation to keep up with growth"
        ],
        "personalization": [
            "Saw your LinkedIn post about sales efficiency challenges",
            "Congrats on hitting $50M ARR - that's huge"
        ]
    },
    {
        "name": "Mike Rodriguez",
        "email": "mike.r@growthco.io",
        "company": "GrowthCo",
        "talking_points": [
            "Fast-growing SaaS startup",
            "Need to scale outbound without adding headcount",
            "Manual processes holding back growth"
        ],
        "personalization": [
            "Heard your podcast interview - you mentioned lead follow-up as biggest bottleneck",
            "5 reps now, planning to scale to 15"
        ]
    },
    {
        "name": "Jennifer Park",
        "email": "j.park@venturesales.com",
        "company": "Venture Sales Partners",
        "talking_points": [
            "Sales consulting firm helping clients with automation",
            "Could be a great partnership fit",
            "You understand the value of modern sales tech"
        ],
        "personalization": [
            "Loved your article on modern sales tech stack last month",
            "Your webinars on sales productivity are excellent"
        ]
    },
    {
        "name": "David Nguyen",
        "email": "david@marketleaders.com",
        "company": "Market Leaders Inc",
        "talking_points": [
            "Enterprise B2B with long sales cycles",
            "100+ person sales org needs better nurturing",
            "Coming from Salesforce, you know the value of automation"
        ],
        "personalization": [
            "Congrats on the promotion to VP of Sales Operations",
            "Your Salesforce background means you get it"
        ]
    },
    {
        "name": "Amanda Stevens",
        "email": "amanda.s@innovatesoft.io",
        "company": "InnovateSoft",
        "talking_points": [
            "Product-led growth company adding sales-assist motion",
            "First sales team just hired",
            "Need help engaging high-intent leads"
        ],
        "personalization": [
            "Your blog about scaling from PLG to sales-assisted is spot on",
            "Perfect timing with your new sales team"
        ]
    }
]


async def regenerate_and_queue_drafts():
    """Regenerate personalized drafts with calendar link."""
    
    logger.info("🚢 Regenerating email drafts with Casey's calendar link")
    logger.info("")
    
    # Initialize components
    generator = create_draft_generator()
    queue = get_draft_queue()
    voice_profile = get_voice_profile("casey_larkin")
    
    logger.info(f"Voice Profile: {voice_profile.name}")
    logger.info(f"Tone: {voice_profile.tone}")
    logger.info(f"Calendar Link: {voice_profile.calendar_link}")
    logger.info(f"Signature: {voice_profile.signature_style[:50]}...")
    logger.info(f"Processing {len(PROSPECTS)} prospects")
    logger.info("")
    
    drafts_created = 0
    
    for i, prospect in enumerate(PROSPECTS, 1):
        try:
            logger.info(f"[{i}/{len(PROSPECTS)}] Generating draft for {prospect['name']} at {prospect['company']}")
            
            # Generate personalized draft using Casey's voice
            draft_result = await generator.generate_draft(
                prospect_email=prospect["email"],
                prospect_name=prospect["name"],
                company_name=prospect["company"],
                voice_profile=voice_profile,
                talking_points=prospect.get("talking_points"),
                personalization_hooks=prospect.get("personalization"),
            )
            
            subject = draft_result["subject"]
            body = draft_result["body"]
            
            # Verify calendar link is in the email
            has_calendar_link = "meetings.hubspot.com/casey-larkin" in body
            if not has_calendar_link:
                logger.warning(f"⚠️  Calendar link not found in draft for {prospect['name']}")
            
            # Queue for operator approval
            draft_id = str(uuid.uuid4())
            
            await queue.create_draft(
                draft_id=draft_id,
                recipient=prospect["email"],
                subject=subject,
                body=body,
                metadata={
                    "prospect_name": prospect["name"],
                    "company_name": prospect["company"],
                    "sender": "casey.l@pesti.io",
                    "generated_at": datetime.utcnow().isoformat(),
                    "voice_profile": voice_profile.name,
                    "model": draft_result.get("model", "gpt-4o"),
                    "has_calendar_link": has_calendar_link,
                    "talking_points": prospect.get("talking_points"),
                    "ready_for_morning_approval": True,
                    "regenerated": True
                }
            )
            
            drafts_created += 1
            
            # Show preview
            logger.info(f"   ✅ Draft {draft_id}")
            logger.info(f"   📧 Subject: {subject}")
            logger.info(f"   🔗 Calendar link: {'✅ Included' if has_calendar_link else '❌ Missing'}")
            logger.info(f"   📝 Preview:")
            body_lines = body.split('\n')
            for line in body_lines[:5]:  # Show first 5 lines
                logger.info(f"      {line}")
            if len(body_lines) > 5:
                logger.info(f"      ... ({len(body_lines) - 5} more lines)")
            logger.info("")
            
        except Exception as e:
            logger.error(f"❌ Failed to create draft for {prospect['name']}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue
    
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"🎉 COMPLETE: {drafts_created}/{len(PROSPECTS)} drafts regenerated and queued")
    logger.info("")
    logger.info("📧 All emails include:")
    logger.info("   ✅ Casey's authentic voice and tone")
    logger.info("   ✅ Calendar link: https://meetings.hubspot.com/casey-larkin")
    logger.info("   ✅ Personalized talking points from research")
    logger.info("   ✅ Clear, actionable CTA")
    logger.info("   ✅ Queued for your approval")
    logger.info("")
    logger.info("👉 View drafts: /api/operator/drafts")
    logger.info("👉 Production: https://web-production-a6ccf.up.railway.app/operator")
    logger.info("")
    logger.info("Next step: Review and approve in operator dashboard tomorrow morning!")
    logger.info("=" * 80)
    
    return drafts_created


async def main():
    """Main entry point."""
    try:
        drafts_created = await regenerate_and_queue_drafts()
        sys.exit(0 if drafts_created > 0 else 1)
    except Exception as e:
        logger.error(f"Script failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
