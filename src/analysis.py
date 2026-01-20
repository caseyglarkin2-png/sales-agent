"""Message analysis utilities for prospecting agent."""
import re
from typing import Any, Dict, List

from src.logger import get_logger

logger = get_logger(__name__)


class MessageAnalyzer:
    """Analyze email messages for prospecting signals."""

    # Intent patterns
    PATTERNS = {
        "question": r"\?$",
        "greeting": r"^(hi|hello|hey|greetings)\b",
        "proposal": r"(would you|interested|opportunity|partnership|collaboration)",
        "budget": r"(budget|investment|spend|cost)",
        "timeline": r"(timeline|schedule|when|soon|asap)",
        "pain_point": r"(problem|challenge|issue|struggle|difficult)",
    }

    @classmethod
    def extract_intent(cls, message_body: str) -> Dict[str, bool]:
        """Extract intent signals from message body."""
        intents = {}
        for intent_type, pattern in cls.PATTERNS.items():
            intents[intent_type] = bool(re.search(pattern, message_body, re.IGNORECASE | re.MULTILINE))
        logger.debug(f"Extracted intents: {intents}")
        return intents

    @classmethod
    def score_message(cls, message_body: str) -> float:
        """Score message for prospecting relevance (0.0-1.0)."""
        intents = cls.extract_intent(message_body)
        score = sum(intents.values()) / len(intents) if intents else 0.0
        logger.debug(f"Message score: {score}")
        return score

    @classmethod
    def extract_entities(cls, message_body: str) -> Dict[str, List[str]]:
        """Extract key entities from message."""
        entities = {
            "emails": re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", message_body),
            "companies": [],  # Would integrate with company DB
            "urls": re.findall(r"https?://\S+", message_body),
        }
        logger.debug(f"Extracted entities: {entities}")
        return entities
