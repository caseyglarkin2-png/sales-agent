"""
Email Template Library.

Manages email templates for various personas, use cases, and scenarios.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TemplateCategory(Enum):
    COLD_OUTREACH = "cold_outreach"
    FOLLOW_UP = "follow_up"
    MEETING_REQUEST = "meeting_request"
    POST_MEETING = "post_meeting"
    NURTURE = "nurture"
    EVENT_INVITATION = "event_invitation"
    CONTENT_SHARE = "content_share"
    REFERRAL_REQUEST = "referral_request"
    REENGAGEMENT = "reengagement"


@dataclass
class EmailTemplate:
    """Email template."""
    id: str
    name: str
    category: TemplateCategory
    subject: str
    body: str
    
    # Targeting
    personas: List[str]
    industries: Optional[List[str]] = None
    
    # Metadata
    description: Optional[str] = None
    tags: List[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    # Performance
    use_count: int = 0
    reply_rate: float = 0.0
    
    # Variables
    variables: List[str] = None  # List of placeholder names
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.variables is None:
            self.variables = self._extract_variables()
    
    def _extract_variables(self) -> List[str]:
        """Extract variable placeholders from template."""
        import re
        pattern = r'\{(\w+)\}'
        found = set()
        found.update(re.findall(pattern, self.subject))
        found.update(re.findall(pattern, self.body))
        return list(found)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "subject": self.subject,
            "body": self.body,
            "personas": self.personas,
            "industries": self.industries,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "use_count": self.use_count,
            "reply_rate": self.reply_rate,
            "variables": self.variables,
        }
    
    def render(self, context: Dict[str, str]) -> tuple[str, str]:
        """Render template with context variables.
        
        Args:
            context: Variable values
            
        Returns:
            Tuple of (rendered_subject, rendered_body)
        """
        subject = self.subject
        body = self.body
        
        for var, value in context.items():
            placeholder = "{" + var + "}"
            subject = subject.replace(placeholder, value)
            body = body.replace(placeholder, value)
        
        return subject, body


# Pre-built templates
DEFAULT_TEMPLATES = [
    {
        "name": "Field Marketing Introduction",
        "category": TemplateCategory.COLD_OUTREACH,
        "subject": "Quick question about {company}'s field marketing",
        "body": """Hi {first_name},

I noticed {company} has been expanding your field marketing efforts — congrats on the growth.

I'm working with similar B2B teams who were struggling to scale their event programs without doubling headcount. We helped them automate the manual work (lead capture, follow-up, reporting) so their team could focus on strategy.

Would it make sense to share what we're seeing work for teams like yours?

Best,
Casey""",
        "personas": ["VP Field Marketing", "Director Events", "Head of Field Marketing"],
        "description": "Initial outreach to field marketing leaders",
        "tags": ["events", "field-marketing", "introduction"],
    },
    {
        "name": "Demand Gen Value Prop",
        "category": TemplateCategory.COLD_OUTREACH,
        "subject": "{first_name}, question about {company}'s pipeline",
        "body": """Hi {first_name},

I've been researching {company} and noticed you're leading demand generation there.

Quick question: how much of your team's time goes into manual follow-up vs. strategic work?

We help demand gen teams reclaim 10+ hours per week by automating the repetitive parts of outbound — without sacrificing personalization.

Worth a quick chat to see if this could help {company}?

Best,
Casey""",
        "personas": ["VP Demand Generation", "Director Growth", "Head of Marketing"],
        "description": "Initial outreach to demand gen leaders",
        "tags": ["demand-gen", "pipeline", "automation"],
    },
    {
        "name": "Gentle Follow-up",
        "category": TemplateCategory.FOLLOW_UP,
        "subject": "Re: {original_subject}",
        "body": """Hi {first_name},

Just floating this back up in case it got buried.

Happy to share a quick example of how we've helped teams like yours if it would be helpful.

No pressure either way — just let me know.

Best,
Casey""",
        "personas": ["all"],
        "description": "Soft follow-up after no response",
        "tags": ["follow-up", "gentle"],
    },
    {
        "name": "Value-Add Follow-up",
        "category": TemplateCategory.FOLLOW_UP,
        "subject": "Thought you might find this useful, {first_name}",
        "body": """Hi {first_name},

I came across this article on {topic} and immediately thought of the work you're doing at {company}.

{content_link}

Let me know if it's helpful — happy to share more resources like this.

Best,
Casey""",
        "personas": ["all"],
        "description": "Follow-up with relevant content",
        "tags": ["follow-up", "content", "value-add"],
    },
    {
        "name": "Meeting Request",
        "category": TemplateCategory.MEETING_REQUEST,
        "subject": "15 minutes this week?",
        "body": """Hi {first_name},

Based on our previous exchange, I think there's a good fit here.

Would you have 15 minutes this week for a quick call? I can share some specifics on how we've helped similar teams at {similar_company} and {similar_company_2}.

Here are a few times that work for me:
{proposed_times}

Let me know what works best.

Best,
Casey""",
        "personas": ["all"],
        "description": "Direct meeting request",
        "tags": ["meeting", "calendar"],
    },
    {
        "name": "Post-Meeting Thank You",
        "category": TemplateCategory.POST_MEETING,
        "subject": "Great chatting, {first_name}",
        "body": """Hi {first_name},

Thanks for taking the time to chat today. I really enjoyed learning more about {company}'s approach to {topic}.

As promised, here are the resources I mentioned:
{resources}

Next steps we discussed:
{next_steps}

Looking forward to staying in touch.

Best,
Casey""",
        "personas": ["all"],
        "description": "Thank you email after meeting",
        "tags": ["post-meeting", "thank-you"],
    },
    {
        "name": "Event Invitation",
        "category": TemplateCategory.EVENT_INVITATION,
        "subject": "You're invited: {event_name}",
        "body": """Hi {first_name},

Given your focus on {focus_area} at {company}, I thought you might be interested in this:

{event_name}
{event_date} | {event_location}

We're bringing together {audience} to discuss {topic}.

Would love to have you join us. Here's the link to register:
{registration_link}

Let me know if you have any questions!

Best,
Casey""",
        "personas": ["VP Field Marketing", "Director Events", "VP Demand Generation"],
        "description": "Event invitation email",
        "tags": ["event", "invitation"],
    },
    {
        "name": "Reengagement - Been a While",
        "category": TemplateCategory.REENGAGEMENT,
        "subject": "It's been a while, {first_name}",
        "body": """Hi {first_name},

It's been a few months since we last connected, and I wanted to check in.

A lot has changed on our end — we've launched some new capabilities that I think would be particularly relevant for {company} given {reason}.

Worth reconnecting for a quick update?

Best,
Casey""",
        "personas": ["all"],
        "description": "Reengagement after long silence",
        "tags": ["reengagement", "nurture"],
    },
]


class TemplateLibrary:
    """Manages email templates."""
    
    def __init__(self):
        self.templates: Dict[str, EmailTemplate] = {}
        self._load_defaults()
    
    def _load_defaults(self):
        """Load default templates."""
        for t in DEFAULT_TEMPLATES:
            template = EmailTemplate(
                id=f"tpl_{uuid.uuid4().hex[:6]}",
                name=t["name"],
                category=t["category"],
                subject=t["subject"],
                body=t["body"],
                personas=t["personas"],
                description=t.get("description"),
                tags=t.get("tags", []),
            )
            self.templates[template.id] = template
        
        logger.info(f"Loaded {len(self.templates)} default templates")
    
    def create_template(
        self,
        name: str,
        category: TemplateCategory,
        subject: str,
        body: str,
        personas: List[str],
        industries: Optional[List[str]] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> EmailTemplate:
        """Create a new template.
        
        Args:
            name: Template name
            category: Template category
            subject: Subject line
            body: Email body
            personas: Target personas
            industries: Target industries
            description: Template description
            tags: Template tags
            
        Returns:
            Created template
        """
        template = EmailTemplate(
            id=f"tpl_{uuid.uuid4().hex[:6]}",
            name=name,
            category=category,
            subject=subject,
            body=body,
            personas=personas,
            industries=industries,
            description=description,
            tags=tags or [],
        )
        
        self.templates[template.id] = template
        logger.info(f"Created template: {name}")
        
        return template
    
    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get template by ID."""
        return self.templates.get(template_id)
    
    def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        persona: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List templates with optional filters."""
        templates = list(self.templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        
        if persona:
            templates = [
                t for t in templates 
                if "all" in t.personas or any(persona.lower() in p.lower() for p in t.personas)
            ]
        
        if tag:
            templates = [t for t in templates if tag in t.tags]
        
        return [t.to_dict() for t in sorted(templates, key=lambda x: x.use_count, reverse=True)]
    
    def get_by_category(self, category: TemplateCategory) -> List[Dict[str, Any]]:
        """Get templates by category."""
        return self.list_templates(category=category)
    
    def search_templates(self, query: str) -> List[Dict[str, Any]]:
        """Search templates by name, description, or tags."""
        query_lower = query.lower()
        
        matches = []
        for t in self.templates.values():
            if (query_lower in t.name.lower() or
                (t.description and query_lower in t.description.lower()) or
                any(query_lower in tag for tag in t.tags)):
                matches.append(t.to_dict())
        
        return matches
    
    def record_use(self, template_id: str):
        """Record template usage."""
        if template_id in self.templates:
            self.templates[template_id].use_count += 1
            self.templates[template_id].updated_at = datetime.utcnow()
    
    def update_performance(
        self,
        template_id: str,
        reply_rate: float,
    ):
        """Update template performance metrics."""
        if template_id in self.templates:
            self.templates[template_id].reply_rate = reply_rate
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id in self.templates:
            del self.templates[template_id]
            return True
        return False
    
    def render_template(
        self,
        template_id: str,
        context: Dict[str, str],
    ) -> Optional[tuple[str, str]]:
        """Render a template with context.
        
        Returns:
            Tuple of (subject, body) or None
        """
        template = self.get_template(template_id)
        if not template:
            return None
        
        self.record_use(template_id)
        return template.render(context)


# Singleton
_library: Optional[TemplateLibrary] = None


def get_template_library() -> TemplateLibrary:
    """Get singleton template library."""
    global _library
    if _library is None:
        _library = TemplateLibrary()
    return _library
