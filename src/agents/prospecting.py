"""Prospecting agent implementation."""
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent
from src.analysis import MessageAnalyzer
from src.connectors.llm import LLMConnector
from src.logger import get_logger

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
