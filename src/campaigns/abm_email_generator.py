"""ABM Email Generator.

Generates personalized emails for Account-Based Marketing campaigns.
Uses account and persona context for deep personalization.
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ABMEmailContext:
    """Context for generating an ABM email."""
    # Contact info
    first_name: str
    last_name: Optional[str] = None
    email: str = ""
    title: Optional[str] = None
    persona: Optional[str] = None
    
    # Company info
    company_name: str = ""
    company_domain: Optional[str] = None
    company_industry: Optional[str] = None
    company_size: Optional[str] = None
    
    # Account-level context
    pain_points: Optional[List[str]] = None
    trigger_event: Optional[str] = None
    competitor_using: Optional[str] = None
    recent_news: Optional[str] = None
    
    # Sender info
    sender_name: str = "Casey"
    sender_title: str = "Account Executive"
    sender_company: str = "Your Company"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "title": self.title,
            "persona": self.persona,
            "company_name": self.company_name,
            "company_domain": self.company_domain,
            "company_industry": self.company_industry,
            "company_size": self.company_size,
            "pain_points": self.pain_points,
            "trigger_event": self.trigger_event,
            "competitor_using": self.competitor_using,
            "recent_news": self.recent_news,
            "sender_name": self.sender_name,
            "sender_title": self.sender_title,
            "sender_company": self.sender_company,
        }


@dataclass
class GeneratedEmail:
    """A generated ABM email."""
    subject: str
    body: str
    personalization_score: int
    personalization_elements: List[str]


def calculate_personalization_score(context: ABMEmailContext) -> tuple[int, List[str]]:
    """Calculate personalization score based on available context.
    
    Returns:
        Tuple of (score 0-100, list of personalization elements used)
    """
    score = 0
    elements = []
    
    # Basic contact info (30 points max)
    if context.first_name:
        score += 10
        elements.append("first_name")
    if context.title:
        score += 10
        elements.append("title")
    if context.persona:
        score += 10
        elements.append("persona")
    
    # Company info (25 points max)
    if context.company_name:
        score += 15
        elements.append("company_name")
    if context.company_industry:
        score += 10
        elements.append("industry")
    
    # Deep personalization (45 points max)
    if context.pain_points:
        score += 15
        elements.append("pain_points")
    if context.trigger_event:
        score += 15
        elements.append("trigger_event")
    if context.recent_news:
        score += 10
        elements.append("recent_news")
    if context.competitor_using:
        score += 5
        elements.append("competitor")
    
    return min(score, 100), elements


def generate_abm_email(
    context: ABMEmailContext,
    email_type: str = "cold_outreach",
) -> GeneratedEmail:
    """Generate a personalized ABM email.
    
    Args:
        context: ABM email context with contact and account info
        email_type: Type of email (cold_outreach, follow_up, etc.)
        
    Returns:
        Generated email with subject, body, and personalization score
    """
    score, elements = calculate_personalization_score(context)
    
    # Generate subject line
    subject = _generate_subject(context, email_type)
    
    # Generate email body
    body = _generate_body(context, email_type)
    
    logger.info(
        f"Generated ABM email for {context.email} with score {score}, "
        f"elements: {elements}"
    )
    
    return GeneratedEmail(
        subject=subject,
        body=body,
        personalization_score=score,
        personalization_elements=elements,
    )


def _generate_subject(context: ABMEmailContext, email_type: str) -> str:
    """Generate email subject line."""
    templates = {
        "cold_outreach": [
            f"{context.first_name}, quick question about {context.company_name}",
            f"Idea for {context.company_name}'s {context.company_industry or 'growth'} strategy",
            f"{context.first_name} - saw {context.company_name}'s recent {context.trigger_event or 'news'}",
        ],
        "follow_up": [
            f"Following up, {context.first_name}",
            f"Re: {context.company_name}",
            f"{context.first_name}, circling back",
        ],
        "value_add": [
            f"Resource for {context.title or 'leaders'} at {context.company_name}",
            f"{context.first_name}, thought you'd find this useful",
        ],
        "break_up": [
            f"Should I close your file?",
            f"{context.first_name}, one last try",
        ],
    }
    
    subjects = templates.get(email_type, templates["cold_outreach"])
    
    # Pick subject based on available context
    if context.trigger_event and email_type == "cold_outreach":
        return subjects[2]  # Use trigger event subject
    elif context.title and email_type == "value_add":
        return subjects[0]  # Use title-based subject
    else:
        return subjects[0]  # Default


def _generate_body(context: ABMEmailContext, email_type: str) -> str:
    """Generate email body."""
    greeting = f"Hi {context.first_name},"
    
    # Opening based on context
    if context.trigger_event:
        opening = f"I noticed {context.company_name} recently {context.trigger_event}. Congrats!"
    elif context.recent_news:
        opening = f"Saw the news about {context.recent_news} - exciting times at {context.company_name}."
    else:
        opening = f"I've been following {context.company_name}'s work in the {context.company_industry or 'industry'} space."
    
    # Value proposition based on persona/title
    if context.persona and context.persona.lower() in ["ceo", "founder", "president"]:
        value_prop = (
            "As a fellow executive, I know your time is valuable. "
            "I wanted to share how we've helped similar companies drive measurable growth."
        )
    elif context.persona and "vp" in context.persona.lower():
        value_prop = (
            "Given your role, I thought you'd be interested in how we've helped "
            f"other {context.title or 'VPs'} at {context.company_industry or 'similar'} companies."
        )
    elif context.persona and "director" in context.persona.lower():
        value_prop = (
            "I work with a lot of Directors who are looking to drive impact. "
            "Would love to share what's working for teams like yours."
        )
    else:
        value_prop = (
            "We've been helping companies like yours solve similar challenges. "
            "I'd love to share what we've learned."
        )
    
    # Pain point mention if available
    if context.pain_points:
        pain_mention = f"\n\nI understand teams at {context.company_name} are focused on {context.pain_points[0]}."
    else:
        pain_mention = ""
    
    # CTA
    cta = "Would you be open to a quick 15-minute call to explore if there's a fit?"
    
    # Signature
    signature = f"\n\nBest,\n{context.sender_name}\n{context.sender_title}"
    
    body = f"""{greeting}

{opening}

{value_prop}{pain_mention}

{cta}
{signature}"""
    
    return body


async def generate_emails_for_campaign(
    campaign_id: str,
    accounts: List[Dict[str, Any]],
    email_type: str = "cold_outreach",
) -> List[Dict[str, Any]]:
    """Generate emails for all contacts in a campaign.
    
    Args:
        campaign_id: Campaign ID
        accounts: List of account dicts with contacts
        email_type: Type of email to generate
        
    Returns:
        List of generated email dicts
    """
    emails = []
    
    for account in accounts:
        for contact in account.get("contacts", []):
            context = ABMEmailContext(
                first_name=contact.get("first_name", ""),
                last_name=contact.get("last_name"),
                email=contact.get("email", ""),
                title=contact.get("title"),
                persona=contact.get("persona"),
                company_name=account.get("company_name", ""),
                company_domain=account.get("company_domain"),
                company_industry=account.get("company_industry"),
                pain_points=account.get("account_context", {}).get("pain_points"),
                trigger_event=account.get("account_context", {}).get("trigger_event"),
                recent_news=account.get("account_context", {}).get("recent_news"),
            )
            
            email = generate_abm_email(context, email_type)
            
            emails.append({
                "campaign_id": campaign_id,
                "account_id": account.get("id"),
                "contact_id": contact.get("id"),
                "to_email": contact.get("email"),
                "subject": email.subject,
                "body": email.body,
                "personalization_score": email.personalization_score,
                "personalization_elements": email.personalization_elements,
            })
    
    logger.info(f"Generated {len(emails)} emails for campaign {campaign_id}")
    return emails
