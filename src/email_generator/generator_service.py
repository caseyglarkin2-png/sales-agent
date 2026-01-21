"""
Email Generator Service
=======================
AI-powered email content generation for sales outreach.
Generates personalized emails, follow-ups, and responses.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import structlog
import uuid
import random

logger = structlog.get_logger(__name__)


class EmailType(str, Enum):
    """Types of emails to generate."""
    COLD_OUTREACH = "cold_outreach"
    FOLLOW_UP = "follow_up"
    BREAKUP = "breakup"
    MEETING_REQUEST = "meeting_request"
    MEETING_CONFIRMATION = "meeting_confirmation"
    MEETING_REMINDER = "meeting_reminder"
    POST_MEETING = "post_meeting"
    PROPOSAL = "proposal"
    THANK_YOU = "thank_you"
    REFERRAL_REQUEST = "referral_request"
    RE_ENGAGEMENT = "re_engagement"
    VALUE_ADD = "value_add"
    CASE_STUDY = "case_study"
    CUSTOM = "custom"


class EmailTone(str, Enum):
    """Email tone options."""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CASUAL = "casual"
    FORMAL = "formal"
    URGENT = "urgent"
    ENTHUSIASTIC = "enthusiastic"
    EMPATHETIC = "empathetic"


@dataclass
class GeneratedEmail:
    """A generated email."""
    id: str
    email_type: EmailType
    subject: str
    body: str
    preview_text: str = ""
    tone: EmailTone = EmailTone.PROFESSIONAL
    word_count: int = 0
    reading_time_seconds: int = 0
    personalization_score: int = 0
    spam_score: int = 0
    suggestions: list[str] = field(default_factory=list)
    alternative_subjects: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email_type": self.email_type.value,
            "subject": self.subject,
            "body": self.body,
            "preview_text": self.preview_text,
            "tone": self.tone.value,
            "word_count": self.word_count,
            "reading_time_seconds": self.reading_time_seconds,
            "personalization_score": self.personalization_score,
            "spam_score": self.spam_score,
            "suggestions": self.suggestions,
            "alternative_subjects": self.alternative_subjects,
            "created_at": self.created_at.isoformat(),
        }


# Email templates for different types
TEMPLATES = {
    EmailType.COLD_OUTREACH: {
        "subjects": [
            "Quick question about {company}'s {pain_point}",
            "{first_name}, noticed something about {company}",
            "Idea for {company}'s {goal}",
            "{mutual_connection} suggested I reach out",
            "Helping {similar_company} with {result}",
        ],
        "openers": [
            "I noticed {company} recently {trigger_event}, and it got me thinking about how we might help.",
            "Congrats on {achievement}! That caught my attention.",
            "I've been following {company}'s growth in {industry}, and I'm impressed by {specific_detail}.",
            "{mutual_connection} mentioned you might be exploring solutions for {pain_point}.",
            "I help {target_persona} like yourself solve {pain_point}.",
        ],
        "bodies": [
            "We've helped companies like {similar_company} achieve {result} by {solution_summary}.",
            "Many {industry} leaders are facing {challenge}. We've developed a way to {benefit}.",
            "I wanted to share how we helped {case_study_company} {achievement} in just {timeframe}.",
        ],
        "ctas": [
            "Would you be open to a 15-minute call next week to explore this?",
            "If this resonates, I'd love to share some specific ideas for {company}.",
            "Happy to share a quick case study if helpful. Worth a conversation?",
            "Do you have 15 minutes this week to chat?",
        ],
    },
    EmailType.FOLLOW_UP: {
        "subjects": [
            "Following up - {original_subject}",
            "Re: {original_subject}",
            "Checking in, {first_name}",
            "Did you get a chance to review?",
            "Quick follow-up on my last email",
        ],
        "openers": [
            "I wanted to follow up on my email from {days_ago}.",
            "I know you're busy, so I wanted to bump this up in your inbox.",
            "Just checking in to see if you had any thoughts on my previous message.",
            "I haven't heard back, so I wanted to make sure this didn't get buried.",
        ],
        "bodies": [
            "To recap: {previous_summary}",
            "I'm still confident we could help {company} with {value_prop}.",
            "I've also attached {new_resource} that might be relevant to your situation.",
        ],
        "ctas": [
            "Is this something worth exploring, or should I close the loop?",
            "Let me know if the timing isn't right - happy to reconnect later.",
            "What does your calendar look like this week?",
        ],
    },
    EmailType.BREAKUP: {
        "subjects": [
            "Should I close your file?",
            "Last attempt to connect",
            "One final thought for {company}",
            "Permission to close the loop?",
        ],
        "openers": [
            "I've reached out a few times but haven't heard back.",
            "I don't want to be a pest, so this will be my last email.",
            "I'll assume the timing isn't right and step back.",
        ],
        "bodies": [
            "If {pain_point} becomes a priority, I'm here to help.",
            "Things change - if your situation evolves, my door is always open.",
        ],
        "ctas": [
            "If there's a better time to reconnect, just let me know.",
            "If I've missed the mark entirely, I'd appreciate the feedback.",
            "Feel free to reach out whenever it makes sense.",
        ],
    },
    EmailType.MEETING_REQUEST: {
        "subjects": [
            "Time to connect this week?",
            "15 minutes to discuss {topic}",
            "Coffee chat about {topic}?",
            "Calendar invite: {topic} discussion",
        ],
        "openers": [
            "I'd love to schedule some time to discuss {topic} with you.",
            "Based on our conversation, I think it would be valuable to meet.",
        ],
        "bodies": [
            "I have some ideas that could help {company} {benefit}.",
            "I'd like to show you how we've helped similar companies achieve {result}.",
        ],
        "ctas": [
            "Here's my calendar link: {calendar_link}",
            "What does your schedule look like {day_suggestion}?",
            "Would {time_suggestion} work for a quick call?",
        ],
    },
    EmailType.POST_MEETING: {
        "subjects": [
            "Great chatting today!",
            "Follow-up from our call",
            "Next steps from our discussion",
            "As promised: {resource}",
        ],
        "openers": [
            "Thanks for taking the time to speak with me today!",
            "I really enjoyed our conversation about {topic}.",
            "It was great learning more about {company}'s goals.",
        ],
        "bodies": [
            "As promised, here are the resources we discussed: {resources}",
            "To recap our conversation: {meeting_summary}",
            "Based on what you shared about {pain_point}, I think {solution} would be a great fit.",
        ],
        "ctas": [
            "Let me know if you have any questions about the materials.",
            "I'll follow up {next_step_date} to continue our discussion.",
            "Looking forward to our next conversation on {follow_up_date}.",
        ],
    },
}


class EmailGenerator:
    """
    AI-powered email content generator.
    """
    
    def __init__(self):
        self.generated_emails: list[GeneratedEmail] = []
    
    def generate(
        self,
        email_type: EmailType,
        context: dict,
        tone: EmailTone = EmailTone.PROFESSIONAL,
        include_alternatives: bool = True,
    ) -> GeneratedEmail:
        """Generate an email based on type and context."""
        
        # Get templates for this email type
        templates = TEMPLATES.get(email_type, TEMPLATES[EmailType.COLD_OUTREACH])
        
        # Select and personalize content
        subject = self._personalize(random.choice(templates["subjects"]), context)
        opener = self._personalize(random.choice(templates["openers"]), context)
        body = self._personalize(random.choice(templates["bodies"]), context)
        cta = self._personalize(random.choice(templates["ctas"]), context)
        
        # Compose full email body
        full_body = self._compose_body(opener, body, cta, context, tone)
        
        # Calculate metrics
        word_count = len(full_body.split())
        reading_time = max(1, word_count // 3)  # ~200 wpm / 60 seconds
        
        # Generate alternatives
        alt_subjects = []
        if include_alternatives:
            for subj in templates["subjects"][:3]:
                alt = self._personalize(subj, context)
                if alt != subject:
                    alt_subjects.append(alt)
        
        # Create generated email
        email = GeneratedEmail(
            id=str(uuid.uuid4()),
            email_type=email_type,
            subject=subject,
            body=full_body,
            preview_text=opener[:100],
            tone=tone,
            word_count=word_count,
            reading_time_seconds=reading_time,
            personalization_score=self._calculate_personalization_score(context),
            spam_score=self._calculate_spam_score(full_body),
            suggestions=self._generate_suggestions(full_body, context),
            alternative_subjects=alt_subjects,
        )
        
        self.generated_emails.append(email)
        
        logger.info(
            "email_generated",
            email_id=email.id,
            type=email_type.value,
            word_count=word_count,
        )
        
        return email
    
    def _personalize(self, template: str, context: dict) -> str:
        """Replace placeholders with context values."""
        result = template
        
        for key, value in context.items():
            placeholder = "{" + key + "}"
            if placeholder in result and value:
                result = result.replace(placeholder, str(value))
        
        # Remove any unfilled placeholders
        import re
        result = re.sub(r'\{[^}]+\}', '[info]', result)
        
        return result
    
    def _compose_body(
        self,
        opener: str,
        body: str,
        cta: str,
        context: dict,
        tone: EmailTone,
    ) -> str:
        """Compose the full email body."""
        first_name = context.get("first_name", "there")
        sender_name = context.get("sender_name", "")
        sender_title = context.get("sender_title", "")
        company_name = context.get("sender_company", "")
        
        # Adjust greeting based on tone
        if tone == EmailTone.FORMAL:
            greeting = f"Dear {first_name},"
        elif tone == EmailTone.CASUAL:
            greeting = f"Hey {first_name},"
        else:
            greeting = f"Hi {first_name},"
        
        # Compose body
        parts = [greeting, "", opener, "", body, "", cta]
        
        # Add signature
        signature_parts = ["", "Best,", sender_name]
        if sender_title:
            signature_parts.append(sender_title)
        if company_name:
            signature_parts.append(company_name)
        
        parts.extend(signature_parts)
        
        return "\n".join(parts)
    
    def _calculate_personalization_score(self, context: dict) -> int:
        """Calculate personalization score based on context provided."""
        score = 0
        
        high_value_fields = ["company", "first_name", "pain_point", "trigger_event", "achievement"]
        medium_value_fields = ["industry", "title", "similar_company", "result"]
        low_value_fields = ["mutual_connection", "goal", "specific_detail"]
        
        for field in high_value_fields:
            if context.get(field):
                score += 20
        
        for field in medium_value_fields:
            if context.get(field):
                score += 10
        
        for field in low_value_fields:
            if context.get(field):
                score += 5
        
        return min(score, 100)
    
    def _calculate_spam_score(self, body: str) -> int:
        """Calculate spam risk score (0-100, lower is better)."""
        score = 0
        body_lower = body.lower()
        
        # Spam trigger words
        spam_words = [
            "free", "guarantee", "no obligation", "winner", "congratulations",
            "act now", "limited time", "urgent", "click here", "buy now",
            "cash", "earn money", "work from home", "discount", "special offer",
        ]
        
        for word in spam_words:
            if word in body_lower:
                score += 10
        
        # Excessive punctuation
        if body.count("!") > 2:
            score += 15
        if body.count("?") > 3:
            score += 5
        
        # All caps words
        words = body.split()
        caps_words = sum(1 for w in words if w.isupper() and len(w) > 2)
        score += caps_words * 5
        
        return min(score, 100)
    
    def _generate_suggestions(self, body: str, context: dict) -> list[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        word_count = len(body.split())
        
        if word_count > 150:
            suggestions.append("Consider shortening the email - ideal length is under 150 words")
        
        if not context.get("pain_point"):
            suggestions.append("Add a specific pain point to increase relevance")
        
        if not context.get("trigger_event"):
            suggestions.append("Include a trigger event for better timing")
        
        if "?" not in body:
            suggestions.append("Add a question to encourage engagement")
        
        if not context.get("similar_company") and not context.get("case_study_company"):
            suggestions.append("Include a relevant case study or social proof")
        
        return suggestions
    
    def generate_follow_up_sequence(
        self,
        context: dict,
        num_emails: int = 4,
        tone: EmailTone = EmailTone.PROFESSIONAL,
    ) -> list[GeneratedEmail]:
        """Generate a sequence of follow-up emails."""
        sequence = []
        
        # First email: Cold outreach
        email1 = self.generate(EmailType.COLD_OUTREACH, context, tone)
        sequence.append(email1)
        
        # Add original subject to context for follow-ups
        context["original_subject"] = email1.subject
        
        # Follow-up emails
        for i in range(1, num_emails - 1):
            context["days_ago"] = f"{i * 3} days ago"
            email = self.generate(EmailType.FOLLOW_UP, context, tone)
            sequence.append(email)
        
        # Final breakup email
        if num_emails > 2:
            breakup = self.generate(EmailType.BREAKUP, context, tone)
            sequence.append(breakup)
        
        logger.info(
            "sequence_generated",
            num_emails=len(sequence),
            contact=context.get("first_name"),
        )
        
        return sequence
    
    def rewrite(
        self,
        original_body: str,
        new_tone: EmailTone,
        instructions: str = "",
    ) -> GeneratedEmail:
        """Rewrite an existing email with a new tone."""
        # Simple tone transformation (would use AI in production)
        lines = original_body.split("\n")
        
        # Adjust greeting
        for i, line in enumerate(lines):
            if line.startswith("Dear "):
                if new_tone == EmailTone.CASUAL:
                    lines[i] = line.replace("Dear", "Hey")
                elif new_tone == EmailTone.FRIENDLY:
                    lines[i] = line.replace("Dear", "Hi")
            elif line.startswith("Hey "):
                if new_tone == EmailTone.FORMAL:
                    lines[i] = line.replace("Hey", "Dear")
        
        new_body = "\n".join(lines)
        
        email = GeneratedEmail(
            id=str(uuid.uuid4()),
            email_type=EmailType.CUSTOM,
            subject="(Rewritten)",
            body=new_body,
            tone=new_tone,
            word_count=len(new_body.split()),
        )
        
        return email
    
    def get_recent_emails(self, limit: int = 10) -> list[GeneratedEmail]:
        """Get recently generated emails."""
        return sorted(
            self.generated_emails,
            key=lambda e: e.created_at,
            reverse=True,
        )[:limit]


# Singleton instance
_generator: Optional[EmailGenerator] = None


def get_email_generator() -> EmailGenerator:
    """Get the email generator singleton."""
    global _generator
    if _generator is None:
        _generator = EmailGenerator()
    return _generator
