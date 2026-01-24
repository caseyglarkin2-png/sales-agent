"""xAI Grok Connector for CaseyOS.

Integrates with xAI's Grok API for real-time market intelligence,
competitive analysis, and social signal processing.

Features:
- Real-time knowledge via Grok's X/Twitter integration
- Market trend analysis with live data
- Competitive intelligence gathering
- Social signal summarization

Configuration:
    Add to src/config.py (Settings class):
        xai_api_key: str = Field(default="", alias="XAI_API_KEY", description="xAI Grok API Key")
    
    Set environment variable:
        XAI_API_KEY=your-xai-api-key

API Reference:
    Endpoint: https://api.x.ai/v1/chat/completions
    Auth: Bearer token
    Model: grok-4
"""
import asyncio
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from src.logger import get_logger
from src.config import get_settings

logger = get_logger(__name__)

settings = get_settings()


@dataclass
class GrokResponse:
    """Response from Grok API."""
    text: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


class GrokConnector:
    """
    Connector for xAI Grok API.
    
    Integrates with CaseyOS for:
    - Real-time market intelligence (leveraging X/Twitter data)
    - Competitive analysis with live insights
    - Social signal processing and summarization
    - GTM trend detection
    
    Example usage:
        grok = get_grok()
        response = await grok.generate("Analyze Tesla's recent market position")
        
        insights = await grok.get_competitive_insights("Salesforce", "CRM")
    """
    
    BASE_URL = "https://api.x.ai/v1"
    DEFAULT_MODEL = "grok-4"
    
    # Rate limiting configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0  # seconds
    MAX_BACKOFF = 32.0  # seconds
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = DEFAULT_MODEL,
    ):
        """
        Initialize Grok connector.
        
        Args:
            api_key: xAI API key. Falls back to XAI_API_KEY env var.
            default_model: Default model to use (default: grok-4).
        """
        # Try settings first, then env var, then passed api_key
        self.api_key = api_key or getattr(settings, 'xai_api_key', '') or os.getenv('XAI_API_KEY', '')
        self.default_model = default_model
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=60.0,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def _request_with_retry(
        self,
        endpoint: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Make API request with exponential backoff retry.
        
        Args:
            endpoint: API endpoint path
            body: Request body
            
        Returns:
            Response JSON data
            
        Raises:
            httpx.HTTPStatusError: On non-retryable HTTP error
            RuntimeError: After max retries exhausted
        """
        if not self.is_configured:
            raise RuntimeError("Grok API key not configured. Set XAI_API_KEY environment variable.")
        
        client = await self._get_client()
        url = f"{self.BASE_URL}/{endpoint}"
        
        backoff = self.INITIAL_BACKOFF
        last_error: Optional[Exception] = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await client.post(url, json=body)
                
                # Handle rate limiting (429) and server errors (5xx) with retry
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", backoff))
                    logger.warning(
                        f"Grok API rate limited, retrying after {retry_after}s",
                        attempt=attempt + 1,
                        max_retries=self.MAX_RETRIES,
                    )
                    await asyncio.sleep(retry_after)
                    backoff = min(backoff * 2, self.MAX_BACKOFF)
                    continue
                
                if response.status_code >= 500:
                    logger.warning(
                        f"Grok API server error {response.status_code}, retrying",
                        attempt=attempt + 1,
                        max_retries=self.MAX_RETRIES,
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, self.MAX_BACKOFF)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                # Don't retry client errors (4xx) except 429
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    logger.error(
                        f"Grok API client error: {e.response.status_code}",
                        response_text=e.response.text[:500],
                    )
                    raise
                last_error = e
                
            except httpx.RequestError as e:
                # Network errors - retry
                logger.warning(
                    f"Grok API request error: {e}",
                    attempt=attempt + 1,
                    max_retries=self.MAX_RETRIES,
                )
                last_error = e
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.MAX_BACKOFF)
        
        raise RuntimeError(f"Grok API request failed after {self.MAX_RETRIES} retries: {last_error}")
    
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_instruction: Optional[str] = None,
    ) -> GrokResponse:
        """
        Generate text using Grok.
        
        Args:
            prompt: User prompt
            model: Model to use (default: grok-4)
            temperature: Creativity (0.0-2.0)
            max_tokens: Maximum output tokens
            system_instruction: System context/role
            
        Returns:
            GrokResponse with generated text
        """
        model_name = model or self.default_model
        
        # Build messages array (OpenAI-compatible format)
        messages: List[Dict[str, str]] = []
        
        if system_instruction:
            messages.append({
                "role": "system",
                "content": system_instruction,
            })
        
        messages.append({
            "role": "user",
            "content": prompt,
        })
        
        body = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        try:
            data = await self._request_with_retry("chat/completions", body)
            
            # Extract response (OpenAI-compatible format)
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("No choices in response")
            
            choice = choices[0]
            message = choice.get("message", {})
            text = message.get("content", "")
            
            # Extract usage
            usage_data = data.get("usage", {})
            usage = {
                "prompt_tokens": usage_data.get("prompt_tokens", 0),
                "completion_tokens": usage_data.get("completion_tokens", 0),
                "total_tokens": usage_data.get("total_tokens", 0),
            }
            
            logger.info(
                "Grok generation complete",
                model=model_name,
                tokens=usage["total_tokens"],
                finish_reason=choice.get("finish_reason", "stop"),
            )
            
            return GrokResponse(
                text=text,
                model=model_name,
                usage=usage,
                finish_reason=choice.get("finish_reason", "stop"),
            )
            
        except Exception as e:
            logger.error(f"Grok generation failed: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check API connectivity with a simple prompt.
        
        Returns:
            Dict with status, latency_ms, and model info
        """
        import time
        
        if not self.is_configured:
            return {
                "status": "unconfigured",
                "error": "XAI_API_KEY not set",
                "model": self.default_model,
            }
        
        start = time.time()
        
        try:
            response = await self.generate(
                prompt="Say 'OK' and nothing else.",
                max_tokens=10,
                temperature=0.0,
            )
            
            latency_ms = (time.time() - start) * 1000
            
            return {
                "status": "healthy",
                "latency_ms": round(latency_ms, 2),
                "model": response.model,
                "response": response.text.strip(),
            }
            
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            
            return {
                "status": "unhealthy",
                "error": str(e),
                "latency_ms": round(latency_ms, 2),
                "model": self.default_model,
            }
    
    async def analyze_market_intel(
        self,
        topic: str,
        context: Optional[str] = None,
    ) -> GrokResponse:
        """
        Analyze market intelligence with Grok's real-time knowledge.
        
        Leverages Grok's integration with X/Twitter for live market data
        and trending discussions.
        
        Args:
            topic: Market topic to analyze (e.g., "AI SaaS funding trends Q1 2026")
            context: Additional context or specific questions
            
        Returns:
            GrokResponse with market analysis
        """
        system_instruction = """You are a market intelligence analyst for a B2B GTM (Go-to-Market) team.

Your analysis should include:
1. Current market trends and movements
2. Key players and their recent activities
3. Emerging opportunities or threats
4. Actionable insights for sales/marketing teams

Use your real-time knowledge from X/Twitter and current events.
Be specific with dates, numbers, and sources when available.
Format insights for quick executive consumption."""

        prompt = f"""Analyze the following market topic:

Topic: {topic}
"""
        
        if context:
            prompt += f"""
Additional Context:
{context}
"""
        
        prompt += """
Provide:
1. Executive Summary (2-3 sentences)
2. Key Trends (3-5 bullet points)
3. Notable Players/Moves
4. Actionable Recommendations for GTM team"""

        return await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.6,
            max_tokens=2048,
        )
    
    async def get_competitive_insights(
        self,
        company: str,
        industry: str,
    ) -> GrokResponse:
        """
        Get competitive intelligence for a company.
        
        Uses Grok's real-time knowledge to surface recent competitive moves,
        product announcements, and market positioning.
        
        Args:
            company: Company name to analyze
            industry: Industry context (e.g., "CRM", "Cloud Infrastructure")
            
        Returns:
            GrokResponse with competitive insights
        """
        system_instruction = """You are a competitive intelligence analyst supporting a B2B sales team.

Focus on actionable intel that helps:
- Position against competitors in sales conversations
- Identify competitive weaknesses and opportunities
- Understand recent product/pricing moves
- Track leadership changes and strategic shifts

Use your real-time knowledge from X/Twitter, news, and current events.
Be specific and cite recent developments when possible."""

        prompt = f"""Provide competitive intelligence for:

Company: {company}
Industry: {industry}

Analyze:
1. Recent News & Announcements (last 30 days)
2. Product/Feature Developments
3. Pricing or Packaging Changes
4. Leadership or Strategy Shifts
5. Customer Sentiment (from social signals)
6. Competitive Strengths & Weaknesses
7. Recommended Positioning Against Them

Focus on intel useful for sales conversations and competitive positioning."""

        return await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.5,
            max_tokens=2048,
        )
    
    async def summarize_social_signals(
        self,
        signals: List[Dict[str, Any]],
    ) -> GrokResponse:
        """
        Summarize social signals from Twitter/X.
        
        Processes a list of social signals (tweets, mentions, discussions)
        and provides actionable summary for GTM teams.
        
        Args:
            signals: List of signal dicts with keys like:
                - content: Tweet/post text
                - author: Username or display name
                - timestamp: When posted
                - engagement: Likes, retweets, etc.
                - url: Link to original
                
        Returns:
            GrokResponse with signal summary
        """
        system_instruction = """You are a social listening analyst for a GTM team.

Your job is to:
1. Identify key themes and sentiment
2. Highlight actionable opportunities (leads, pain points, needs)
3. Flag potential risks or negative sentiment
4. Prioritize signals by business impact

Be concise and action-oriented. Focus on what the sales/marketing team should DO based on these signals."""

        # Format signals for prompt
        signal_text = ""
        for i, signal in enumerate(signals[:20], 1):  # Limit to 20 signals
            content = signal.get("content", "")
            author = signal.get("author", "Unknown")
            timestamp = signal.get("timestamp", "")
            engagement = signal.get("engagement", {})
            
            signal_text += f"""
Signal {i}:
- Author: {author}
- Time: {timestamp}
- Content: {content}
- Engagement: {engagement}
---"""

        prompt = f"""Summarize the following social signals and provide actionable insights:

{signal_text}

Provide:
1. Key Themes (top 3-5)
2. Sentiment Overview (positive/negative/neutral mix)
3. Actionable Opportunities (leads, conversations to join, content ideas)
4. Risk Flags (negative mentions, complaints, competitor wins)
5. Recommended Actions (prioritized list)"""

        return await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=0.5,
            max_tokens=2048,
        )
    
    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        model: Optional[str] = None,
    ) -> GrokResponse:
        """
        Generate with additional context (like a document or email thread).
        
        Useful for:
        - Email drafting with thread context
        - Document summarization
        - Research synthesis
        
        Args:
            prompt: What to generate
            context: Background context
            model: Model to use
            
        Returns:
            GrokResponse with generated content
        """
        system_instruction = """You are CaseyOS, a GTM command center AI assistant.
You help with sales, marketing, and customer success operations.
Be concise, actionable, and professional.
When drafting emails, match the user's voice and style."""

        full_prompt = f"""Context:
{context}

---

Task: {prompt}"""

        return await self.generate(
            prompt=full_prompt,
            model=model,
            system_instruction=system_instruction,
        )


# Singleton instance
_grok_instance: Optional[GrokConnector] = None


def get_grok() -> GrokConnector:
    """
    Get singleton Grok connector instance.
    
    Returns:
        GrokConnector instance (creates if not exists)
    """
    global _grok_instance
    if _grok_instance is None:
        _grok_instance = GrokConnector()
    return _grok_instance


async def reset_grok() -> None:
    """Reset the singleton instance (useful for testing)."""
    global _grok_instance
    if _grok_instance is not None:
        await _grok_instance.close()
        _grok_instance = None
