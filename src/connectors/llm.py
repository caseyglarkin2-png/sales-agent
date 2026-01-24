"""LLM connector with multi-provider support (OpenAI + Gemini).

Supports:
- OpenAI GPT-4 (default)
- Google Gemini 2.0 Flash
- Automatic failover between providers
"""
from typing import Any, Dict, List, Optional
import asyncio

from openai import AsyncOpenAI

from src.config import get_settings
from src.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class LLMConnector:
    """
    Multi-provider LLM connector.
    
    Supports OpenAI and Google Gemini with automatic failover.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        """
        Initialize LLM connector.
        
        Args:
            api_key: API key (defaults to config)
            model: Model name (defaults to config)
            provider: "openai" or "gemini" (defaults to config)
        """
        self.provider = provider or settings.llm_provider
        
        if self.provider == "gemini":
            from src.connectors.gemini import GeminiConnector, GeminiModel
            self.gemini = GeminiConnector(
                api_key=api_key or settings.gemini_api_key,
            )
            self.model = model or settings.gemini_model
            self.openai_client = None
        else:
            # Default to OpenAI - use new client API
            self.openai_client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
            self.model = model or settings.openai_model
            self.gemini = None
    
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        system_instruction: Optional[str] = None,
        enable_grounding: bool = False,
    ) -> Optional[str]:
        """
        Generate text using configured LLM provider.
        
        Args:
            prompt: User prompt
            temperature: Creativity (0.0-2.0)
            max_tokens: Maximum output tokens
            system_instruction: System context (Gemini only)
            enable_grounding: Enable Google Search grounding (Gemini only)
            
        Returns:
            Generated text or None on error
        """
        if self.provider == "gemini" and self.gemini:
            return await self._generate_with_gemini(
                prompt, temperature, max_tokens, system_instruction, enable_grounding
            )
        else:
            return await self._generate_with_openai(prompt, temperature, max_tokens)
    
    async def _generate_with_openai(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> Optional[str]:
        """Generate text using OpenAI (new 1.x API)."""
        try:
            # Create client on-demand if needed (for failover case)
            client = self.openai_client
            if client is None:
                client = AsyncOpenAI(api_key=settings.openai_api_key)
            
            response = await client.chat.completions.create(
                model=self.model or settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = response.choices[0].message.content
            logger.info(f"Generated text with OpenAI ({len(text)} chars)")
            return text
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            
            # Failover to Gemini if available
            if settings.gemini_api_key:
                logger.info("Failing over to Gemini...")
                from src.connectors.gemini import GeminiConnector
                gemini = GeminiConnector()
                try:
                    response = await gemini.generate(prompt, temperature=temperature, max_tokens=max_tokens)
                    return response.text
                except Exception as ge:
                    logger.error(f"Gemini failover also failed: {ge}")
            
            return None
    
    async def _generate_with_gemini(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        system_instruction: Optional[str] = None,
        enable_grounding: bool = False,
    ) -> Optional[str]:
        """Generate text using Gemini."""
        try:
            response = await self.gemini.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                system_instruction=system_instruction,
                enable_grounding=enable_grounding,
            )
            logger.info(f"Generated text with Gemini ({len(response.text)} chars)")
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            
            # Failover to OpenAI if available
            if settings.openai_api_key:
                logger.info("Failing over to OpenAI...")
                try:
                    return await self._generate_with_openai(prompt, temperature, max_tokens)
                except Exception as oe:
                    logger.error(f"OpenAI failover also failed: {oe}")
            
            return None
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text.
        
        Uses OpenAI embeddings (new 1.x API).
        """
        try:
            # Create client on-demand if needed
            client = self.openai_client
            if client is None:
                client = AsyncOpenAI(api_key=settings.openai_api_key)
            
            response = await client.embeddings.create(
                input=text,
                model="text-embedding-3-small",
            )
            embedding = response.data[0].embedding
            logger.info(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Optional[str]:
        """
        Generate text with additional context.
        
        Useful for:
        - Email drafting with thread context
        - Document analysis
        - Research synthesis
        """
        full_prompt = f"""Context:
{context}

---

{prompt}"""
        
        return await self.generate_text(
            prompt=full_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check LLM provider connectivity."""
        results = {
            "provider": self.provider,
            "model": self.model,
        }
        
        # Check primary provider
        try:
            response = await self.generate_text("Reply with 'ok'", max_tokens=10)
            results["status"] = "healthy" if response else "degraded"
        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
        
        # Check failover provider
        if self.provider == "openai" and settings.gemini_api_key:
            results["failover"] = "gemini_available"
        elif self.provider == "gemini" and settings.openai_api_key:
            results["failover"] = "openai_available"
        else:
            results["failover"] = "none"
        
        return results


# Singleton instance
_llm_instance: Optional[LLMConnector] = None


def get_llm() -> LLMConnector:
    """Get or create LLM connector singleton."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMConnector()
    return _llm_instance
