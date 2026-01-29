"""OpenAI-powered email draft generation.

This module uses OpenAI's GPT models to generate personalized
email drafts based on voice profiles, context, and meeting slots.

Sprint 69: Added few-shot examples for Casey voice consistency.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from src.logger import get_logger
from src.voice_profile import VoiceProfile, get_voice_profile
from src.pii_detector import PIISafetyValidator
from src.agents.persona_router import detect_persona, get_challenger_hook

logger = get_logger(__name__)

# Path to Casey's exemplar emails
CASEY_EXAMPLES_PATH = Path(__file__).parent / "voice_profiles" / "casey_examples.json"


class DraftGenerator:
    """Generates email drafts using OpenAI."""
    
    def __init__(self, api_key: Optional[str] = None, enable_pii_check: bool = True):
        """Initialize draft generator.
        
        Args:
            api_key: OpenAI API key
            enable_pii_check: Enable PII safety validation
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        self.enable_pii_check = enable_pii_check
        self.pii_validator = PIISafetyValidator(strict_mode=False) if enable_pii_check else None
        
        # Load few-shot examples for Casey voice (Sprint 69)
        self.casey_examples = self._load_casey_examples()
    
    def _load_casey_examples(self) -> List[Dict[str, Any]]:
        """Load Casey's exemplar emails for few-shot learning."""
        try:
            if CASEY_EXAMPLES_PATH.exists():
                with open(CASEY_EXAMPLES_PATH, "r") as f:
                    examples = json.load(f)
                    logger.info(f"Loaded {len(examples)} Casey few-shot examples")
                    return examples
        except Exception as e:
            logger.warning(f"Could not load Casey examples: {e}")
        return []
    
    def _get_matching_examples(self, persona_hint: Optional[str] = None, count: int = 2) -> List[Dict[str, Any]]:
        """Get examples matching the target persona.
        
        Args:
            persona_hint: Keywords from company/title to match (e.g., "Marketing", "Sales")
            count: Number of examples to return
        """
        if not self.casey_examples:
            return []
        
        # Try to match by persona keyword
        if persona_hint:
            hint_lower = persona_hint.lower()
            matched = [
                ex for ex in self.casey_examples 
                if any(word in ex.get("persona", "").lower() for word in hint_lower.split())
            ]
            if matched:
                return matched[:count]
        
        # Fall back to first N examples
        return self.casey_examples[:count]
    
    async def generate_draft(
        self,
        prospect_email: str,
        prospect_name: str,
        company_name: str,
        thread_context: Optional[str] = None,
        meeting_slots: Optional[List[Dict[str, Any]]] = None,
        asset_link: Optional[str] = None,
        voice_profile: Optional[VoiceProfile] = None,
        talking_points: Optional[List[str]] = None,
        personalization_hooks: Optional[List[str]] = None,
        sender_context: Optional[Dict[str, str]] = None,
        job_title: Optional[str] = None,  # Sprint 69: For persona detection
    ) -> Dict[str, Any]:
        """Generate a personalized email draft.
        
        Args:
            prospect_email: Recipient email
            prospect_name: Recipient first name
            company_name: Company name
            thread_context: Summary of previous email thread
            meeting_slots: Available meeting times
            asset_link: Link to relevant asset (case study, proposal)
            voice_profile: Voice profile for tone/style
            talking_points: Research-based talking points
            personalization_hooks: Personalization hooks from research
            sender_context: Dict with sender_name, sender_title, sender_company, 
                           calendar_link from user profile (Sprint 53)
            job_title: Prospect's job title for persona detection (Sprint 69)
        
        Returns:
            Dict with subject, body, and metadata
        """
        profile = voice_profile or get_voice_profile()
        
        # Merge sender context from user profile if provided (Sprint 53)
        effective_sender = {
            "sender_name": profile.name,
            "sender_title": "",
            "sender_company": "",
            "calendar_link": profile.calendar_link,
        }
        if sender_context:
            effective_sender.update({k: v for k, v in sender_context.items() if v})
        
        if not self.client:
            logger.warning("OpenAI client not configured, using fallback draft")
            return self._fallback_draft(
                prospect_name, company_name, meeting_slots, asset_link, profile,
                sender_context=effective_sender
            )
        
        # Detect persona and get challenger hook (Sprint 69)
        persona, confidence = detect_persona(job_title, company_name)
        challenger_hook = get_challenger_hook(persona) if confidence >= 0.6 else None
        
        # Build the prompt with persona hint for few-shot matching
        persona_hint = job_title or company_name  # Use job title or company for matching examples
        system_prompt = self._build_system_prompt(
            profile, sender_context=effective_sender, persona_hint=persona_hint
        )
        user_prompt = self._build_user_prompt(
            prospect_name, company_name, thread_context, 
            meeting_slots, asset_link, profile,
            talking_points=talking_points,
            personalization_hooks=personalization_hooks,
            challenger_hook=challenger_hook,  # Sprint 69
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )
            
            content = response.choices[0].message.content
            subject, body = self._parse_response(content)
            
            # PII safety check
            safety_result = None  # Initialize to avoid undefined variable bug
            if self.enable_pii_check and self.pii_validator:
                full_email = f"{subject}\n\n{body}"
                safety_result = self.pii_validator.validate(full_email, context="email_draft")
                
                if not safety_result["safe"]:
                    logger.warning(f"PII detected in draft for {prospect_email}: {safety_result['warnings']}")
                    return {
                        "subject": subject,
                        "body": body,
                        "model": self.model,
                        "tokens_used": response.usage.total_tokens if response.usage else 0,
                        "voice_profile": profile.name,
                        "pii_safety": safety_result,
                        "blocked": not safety_result["safe"],
                    }
            
            logger.info(f"Generated draft for {prospect_email}")
            return {
                "subject": subject,
                "body": body,
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "voice_profile": profile.name,
                "pii_safety": safety_result,
                "blocked": False,
            }
        
        except Exception as e:
            logger.error(f"Error generating draft: {e}")
            return self._fallback_draft(
                prospect_name, company_name, meeting_slots, asset_link, profile,
                sender_context=effective_sender
            )
    
    def _build_system_prompt(
        self, 
        profile: VoiceProfile,
        sender_context: Optional[Dict[str, str]] = None,
        persona_hint: Optional[str] = None,
    ) -> str:
        """Build system prompt with voice profile, sender context, and few-shot examples.
        
        Args:
            profile: VoiceProfile with tone/style settings
            sender_context: Dict with sender_name, sender_title, sender_company,
                           calendar_link from user profile (Sprint 53)
            persona_hint: Keywords to match few-shot examples (e.g., "Marketing VP")
        """
        # Build sender info block from context (Sprint 53)
        sender_info = ""
        if sender_context:
            sender_parts = []
            if sender_context.get("sender_name"):
                sender_parts.append(f"Sender Name: {sender_context['sender_name']}")
            if sender_context.get("sender_title"):
                sender_parts.append(f"Sender Title: {sender_context['sender_title']}")
            if sender_context.get("sender_company"):
                sender_parts.append(f"Sender Company: {sender_context['sender_company']}")
            if sender_context.get("calendar_link"):
                sender_parts.append(f"Calendar Link: {sender_context['calendar_link']}")
            if sender_parts:
                sender_info = "\nSENDER INFORMATION:\n" + "\n".join(sender_parts) + "\n"
        
        # Build few-shot examples section (Sprint 69)
        examples_section = self._build_examples_section(persona_hint)
        
        return f"""You are Casey Larkin, a Socratic and provocative B2B communicator. 
Your emails make people stop and think. You challenge assumptions and ask questions 
that executives can't ignore.

{profile.to_prompt_context()}
{sender_info}
SOCRATIC APPROACH:
- Open with a question that makes them reconsider their current approach
- "What if the way you're measuring X is actually hiding Y?"
- "Have you noticed that [industry trend] isn't working for companies like yours?"
- Guide them to discover the insight themselves, don't lecture

PROVOCATIVE EDGE:
- Name the uncomfortable truth others won't say
- "Most [persona] are doing X wrong, and here's why..."
- Create productive tension between their status quo and what's possible
- Be the contrarian voice they secretly agree with
{examples_section}
OUTPUT FORMAT:
Subject: [compelling subject - question or contrarian hook]
---
[email body]

RULES:
- Short, punchy, zero filler
- One provocative insight or question per email
- End with a question they'll think about even if they don't reply
- Sound like a smart friend challenging their thinking, not a salesperson
- Use the sender's real name and title in the signature
"""
    
    def _build_examples_section(self, persona_hint: Optional[str] = None) -> str:
        """Build few-shot examples section for system prompt.
        
        Args:
            persona_hint: Keywords to match examples (e.g., "Marketing")
        """
        examples = self._get_matching_examples(persona_hint, count=2)
        if not examples:
            return ""
        
        parts = ["\nEXAMPLE EMAILS (study the Socratic style):"]
        for i, ex in enumerate(examples, 1):
            parts.append(f"\nExample {i} ({ex.get('persona', 'Prospect')}):")
            parts.append(f"Subject: {ex.get('subject', '')}")
            parts.append("---")
            parts.append(ex.get("body", ""))
        parts.append("")  # Extra newline
        return "\n".join(parts)
    
    def _build_user_prompt(
        self,
        prospect_name: str,
        company_name: str,
        thread_context: Optional[str],
        meeting_slots: Optional[List[Dict[str, Any]]],
        asset_link: Optional[str],
        profile: VoiceProfile,
        talking_points: Optional[List[str]] = None,
        personalization_hooks: Optional[List[str]] = None,
        challenger_hook: Optional[str] = None,  # Sprint 69
    ) -> str:
        """Build user prompt with context."""
        parts = [
            f"Write an email to {prospect_name} at {company_name}.",
        ]
        
        # Add challenger hook for Socratic opener (Sprint 69)
        if challenger_hook:
            parts.append(f"\nSUGGESTED OPENER (adapt this Socratic question to their context):")
            parts.append(f"'{challenger_hook}'")
        
        # Add research-based talking points
        if talking_points:
            parts.append("\nResearch insights to incorporate:")
            for point in talking_points:
                parts.append(f"- {point}")
        
        # Add personalization hooks
        if personalization_hooks:
            parts.append("\nPersonalization suggestions:")
            for hook in personalization_hooks:
                parts.append(f"- {hook}")
        
        if thread_context:
            parts.append(f"\nPrevious conversation context:\n{thread_context}")
        else:
            parts.append("\nThis is initial outreach after they submitted a form.")
        
        if meeting_slots:
            slots_text = "\n".join([
                f"- {slot.get('display', slot.get('start', 'TBD'))}"
                for slot in meeting_slots[:profile.slot_count]
            ])
            parts.append(f"\nOffer these meeting times:\n{slots_text}")
        
        if asset_link:
            parts.append(f"\nInclude this relevant resource: {asset_link}")
        
        # Add calendar link instruction if available
        if profile.calendar_link:
            parts.append(f"\nINCLUDE THIS CALENDAR LINK in the signature or as a clear CTA: {profile.calendar_link}")
            parts.append("(Make it easy for them to book time directly)")
        
        return "\n".join(parts)
    
    def _parse_response(self, content: str) -> tuple[str, str]:
        """Parse subject and body from response."""
        if "---" in content:
            parts = content.split("---", 1)
            subject_line = parts[0].replace("Subject:", "").strip()
            body = parts[1].strip()
        else:
            lines = content.split("\n", 1)
            subject_line = lines[0].replace("Subject:", "").strip()
            body = lines[1].strip() if len(lines) > 1 else content
        
        return subject_line, body
    
    def _fallback_draft(
        self,
        prospect_name: str,
        company_name: str,
        meeting_slots: Optional[List[Dict[str, Any]]],
        asset_link: Optional[str],
        profile: VoiceProfile,
        sender_context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Generate fallback draft without OpenAI.
        
        Args:
            sender_context: Dict with sender_name, sender_title, sender_company,
                           calendar_link from user profile (Sprint 53)
        """
        subject = f"Quick question for {company_name}"
        
        body_parts = [
            f"Hi {prospect_name},",
            "",
            "Thanks for reaching out. I'd love to learn more about what you're working on "
            f"at {company_name} and see if there's a way we can help.",
        ]
        
        if meeting_slots:
            body_parts.append("")
            body_parts.append("I have a few times available for a quick chat:")
            for i, slot in enumerate(meeting_slots[:profile.slot_count], 1):
                display = slot.get("display", slot.get("start", "TBD"))
                body_parts.append(f"  {i}. {display}")
        
        body_parts.append("")
        body_parts.append("Would any of these work for you?")
        body_parts.append("")
        
        # Build signature from sender_context if available (Sprint 53)
        if sender_context and sender_context.get("sender_name"):
            sig_lines = []
            sig_lines.append(sender_context["sender_name"])
            if sender_context.get("sender_title") and sender_context.get("sender_company"):
                sig_lines.append(f"{sender_context['sender_title']} | {sender_context['sender_company']}")
            elif sender_context.get("sender_title"):
                sig_lines.append(sender_context["sender_title"])
            elif sender_context.get("sender_company"):
                sig_lines.append(sender_context["sender_company"])
            if sender_context.get("calendar_link"):
                sig_lines.append(f"Book a time: {sender_context['calendar_link']}")
            body_parts.append("\n".join(sig_lines))
        else:
            body_parts.append(profile.signature_style)
        
        if profile.include_ps and asset_link:
            body_parts.append("")
            body_parts.append(f"P.S. Thought you might find this helpful: {asset_link}")
        
        return {
            "subject": subject,
            "body": "\n".join(body_parts),
            "model": "fallback",
            "tokens_used": 0,
            "voice_profile": profile.name,
        }


# Factory function
def create_draft_generator() -> DraftGenerator:
    """Create a draft generator with API key from environment."""
    return DraftGenerator()
