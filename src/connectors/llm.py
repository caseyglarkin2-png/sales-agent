"""LLM connector for OpenAI integration."""
from typing import Any, Dict, Optional

import openai

from src.logger import get_logger

logger = get_logger(__name__)


class LLMConnector:
    """Connector for OpenAI LLM."""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        """Initialize LLM connector."""
        openai.api_key = api_key
        self.model = model

    async def generate_text(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 500
    ) -> Optional[str]:
        """Generate text using OpenAI."""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = response.choices[0].message.content
            logger.info(f"Generated text with {len(text)} characters")
            return text
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return None

    async def generate_embedding(self, text: str) -> Optional[list]:
        """Generate embedding for text."""
        try:
            response = openai.Embedding.create(
                input=text,
                model="text-embedding-3-small",
            )
            embedding = response.data[0].embedding
            logger.info(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
