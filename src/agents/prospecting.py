"""Prospecting agent implementation."""
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from src.agents.base import BaseAgent
from src.agents.persona_router import detect_persona, get_messaging_context, Persona
from src.analysis import MessageAnalyzer
from src.connectors.llm import LLMConnector
from src.logger import get_logger
from src.voice_profile import get_voice_profile_manager, VoiceProfile

if TYPE_CHECKING:
    from src.models.prospect import Prospect

logger = get_logger(__name__)


class ProspectingAgent(BaseAgent):
    """Agent for prospecting and lead generation."""

    def __init__(self, llm_connector: LLMConnector):
        """Initialize prospecting agent."""
        super().__init__(
            name="Prospecting Agent",
            description="Analyzes incoming messages to identify sales opportunities",
        )
        self.llm = llm_connector
        self.analyzer = MessageAnalyzer()
        self.voice_manager = get_voice_profile_manager()

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input has required fields."""
        required = ["message_id", "sender", "subject", "body"]
        return all(field in context for field in required)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute prospecting analysis on message."""
        logger.info(f"Prospecting analysis for message {context.get('message_id')}")

        # Validate input
        if not await self.validate_input(context):
            logger.error("Invalid input context for prospecting analysis")
            return {"error": "Missing required fields"}

        try:
            # Extract message components
            sender = context["sender"]
            subject = context["subject"]
            body = context["body"]

            # Analyze message for intent
            intents = self.analyzer.extract_intent(body)
            score = self.analyzer.score_message(body)
            entities = self.analyzer.extract_entities(body)

            # Generate response recommendation if high intent
            response_prompt = None
            if score > 0.5:
                response_prompt = await self._generate_response_prompt(sender, subject, body)

            result = {
                "message_id": context["message_id"],
                "sender": sender,
                "subject": subject,
                "intent_analysis": intents,
                "relevance_score": score,
                "entities": entities,
                "response_prompt": response_prompt,
                "action": "draft_required" if score > 0.5 else "archive",
            }

            logger.info(f"Prospecting result for {sender}: score={score}, action={result['action']}")
            return result

        except Exception as e:
            logger.error(f"Error in prospecting analysis: {e}")
            return {"error": str(e)}

    async def _generate_response_prompt(
        self, sender: str, subject: str, body: str
    ) -> Optional[str]:
        """Generate LLM prompt for response drafting."""
        try:
            prompt = f"""
You are a B2B sales expert. Generate a personalized response to this prospect inquiry.

From: {sender}
Subject: {subject}
Message: {body}

Generate a concise, professional response (2-3 sentences) that:
1. Acknowledges their inquiry
2. Shows understanding of their need
3. Proposes next steps

Response:"""

            response = await self.llm.generate_text(prompt, temperature=0.7, max_tokens=200)
            logger.debug(f"Generated response prompt for {sender}")
            return response

        except Exception as e:
            logger.error(f"Error generating response prompt: {e}")
            return None

    async def generate_message(
        self,
        prospect: Any,  # Prospect model from src.models.prospect
        context: Dict[str, Any] = None,
        available_slots: List[Dict[str, Any]] = None,
        profile_id: str = "casey_larkin",
    ) -> Optional[str]:
        """Generate a personalized prospecting email using persona-based messaging.
        
        Args:
            prospect: Prospect data with email, name, company, job_title
            context: Additional context (email threads, HubSpot data, etc.)
            available_slots: Calendar slots to offer
            profile_id: Voice profile to use
            
        Returns:
            Generated email body text
        """
        try:
            # Get voice profile
            profile = self.voice_manager.get_profile(profile_id)
            if not profile:
                profile = self.voice_manager.get_profile("casey_larkin")
            
            # Get job_title - support both Pydantic model and dict
            job_title = getattr(prospect, 'job_title', None) or ""
            company = getattr(prospect, 'company', None) or ""
            
            # Get persona-based messaging context
            persona_context = get_messaging_context(
                job_title=job_title,
                company_name=company,
            )
            persona = persona_context["persona"]
            
            logger.info(f"Generating message for {prospect.email} with persona: {persona}")
            
            # Build prompt with persona-specific messaging
            prompt = self._build_prospecting_prompt(
                prospect=prospect,
                persona_context=persona_context,
                voice_profile=profile,
                email_context=context,
                available_slots=available_slots,
            )
            
            # Generate with LLM
            response = await self.llm.generate_text(
                prompt,
                temperature=0.7,
                max_tokens=500,
            )
            
            logger.info(f"Generated {len(response)} char message for {prospect.email}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating message: {e}")
            return None
    
    def _build_prospecting_prompt(
        self,
        prospect: Any,
        persona_context: Dict[str, Any],
        voice_profile: VoiceProfile,
        email_context: Optional[Dict[str, Any]] = None,
        available_slots: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Build the LLM prompt for prospecting email generation."""
        
        # Extract prospect attributes (handle both Pydantic and dict)
        first_name = getattr(prospect, 'first_name', '') or ''
        last_name = getattr(prospect, 'last_name', '') or ''
        company = getattr(prospect, 'company', '') or ''
        job_title = getattr(prospect, 'job_title', '') or ''
        email = getattr(prospect, 'email', '') or ''
        
        # Voice profile guidance
        style_notes = "\n".join(f"- {note}" for note in voice_profile.style_notes)
        
        # Persona-specific guidance
        focus_area = persona_context.get("focus_area", "GTM execution")
        pain_points = persona_context.get("pain_points", [])
        value_props = persona_context.get("value_props", [])
        cta_style = persona_context.get("cta_style", "Quick chat to learn more")
        
        pain_points_str = "\n".join(f"- {p}" for p in pain_points[:3])
        value_props_str = "\n".join(f"- {v}" for v in value_props[:3])
        
        # Build email context section
        context_section = ""
        if email_context and email_context.get("threads"):
            context_section = "\nPrevious email context exists - reference the ongoing conversation naturally."
        
        # Available slots section
        slots_section = ""
        if available_slots and len(available_slots) > 0:
            slots_section = "\nOffer to find a time that works (don't list specific slots)."
        
        prompt = f"""You are writing a prospecting email as Casey from Pesti, a GTM execution partner.

PROSPECT INFORMATION:
- Name: {first_name} {last_name}
- Company: {company}
- Job Title: {job_title}
- Email: {email}

PERSONA: {persona_context.get('persona', 'unknown').upper()}
Focus Area: {focus_area}

RELEVANT PAIN POINTS TO ADDRESS:
{pain_points_str}

VALUE PROPOSITIONS:
{value_props_str}

CTA STYLE: {cta_style}
{context_section}
{slots_section}

VOICE PROFILE (write in this style):
Tone: {voice_profile.tone}
{style_notes}
Signature: {voice_profile.signature_style}
Use contractions: {"Yes" if voice_profile.use_contractions else "No"}
Max paragraphs: {voice_profile.max_paragraphs}
Include P.S.: {"Yes" if voice_profile.include_ps else "No"}

IMPORTANT:
- Do NOT mention freight, logistics, or shipping - Pesti does NOT work in that industry
- Pesti is a GTM/demand generation company
- Focus on field marketing, lead gen, nurturing, ABM
- Keep it short (2-3 paragraphs max)
- Be genuine and helpful, not salesy
- Reference their specific role/challenges

Write the email body only (no subject line):"""

        return prompt

