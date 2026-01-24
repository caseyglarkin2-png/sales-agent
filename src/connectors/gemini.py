"""Gemini AI Connector for Google Workspace integration.

Supports multiple Gemini models:
- gemini-2.0-flash-exp: Fast, multimodal, great for most tasks
- gemini-1.5-pro: High capability, 1M context window
- gemini-1.5-flash: Fast and versatile
- gemini-exp-1206: Experimental with enhanced reasoning

Features:
- Deep Research: Multi-step research with citations
- Canvas: Collaborative document creation
- Grounding: Google Search integration for factual responses
"""
import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
import json

import httpx

from src.logger import get_logger
from src.config import get_settings

logger = get_logger(__name__)

settings = get_settings()


class GeminiModel(str, Enum):
    """Available Gemini models."""
    # Latest and fastest
    FLASH_2_0 = "gemini-2.0-flash-exp"
    # High capability with massive context
    PRO_1_5 = "gemini-1.5-pro"
    # Fast and versatile
    FLASH_1_5 = "gemini-1.5-flash"
    # Experimental enhanced reasoning
    EXP_1206 = "gemini-exp-1206"
    # Efficient model (nano-like)
    FLASH_8B = "gemini-1.5-flash-8b"


@dataclass
class GeminiResponse:
    """Response from Gemini API."""
    text: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    grounding_sources: Optional[List[Dict]] = None
    safety_ratings: Optional[List[Dict]] = None


@dataclass
class ResearchResult:
    """Result from deep research."""
    summary: str
    findings: List[Dict[str, str]]
    sources: List[str]
    confidence: float


class GeminiConnector:
    """
    Connector for Google Gemini AI.
    
    Integrates with Google Workspace for:
    - AI-powered content generation
    - Deep research with grounding
    - Multimodal understanding
    """
    
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: GeminiModel = GeminiModel.FLASH_2_0,
    ):
        """
        Initialize Gemini connector.
        
        Args:
            api_key: Google AI API key. Falls back to GEMINI_API_KEY env var.
            default_model: Default model to use.
        """
        self.api_key = api_key or getattr(settings, 'gemini_api_key', '')
        self.default_model = default_model
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=60.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    def _get_endpoint(self, model: str, action: str = "generateContent") -> str:
        """Build API endpoint URL."""
        return f"{self.BASE_URL}/models/{model}:{action}?key={self.api_key}"
    
    async def generate(
        self,
        prompt: str,
        model: Optional[GeminiModel] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_instruction: Optional[str] = None,
        enable_grounding: bool = False,
    ) -> GeminiResponse:
        """
        Generate text using Gemini.
        
        Args:
            prompt: User prompt
            model: Gemini model to use
            temperature: Creativity (0.0-2.0)
            max_tokens: Maximum output tokens
            system_instruction: System context/role
            enable_grounding: Enable Google Search grounding
            
        Returns:
            GeminiResponse with generated text
        """
        model_name = (model or self.default_model).value
        
        # Build request body
        contents = [{"parts": [{"text": prompt}]}]
        
        generation_config = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "topP": 0.95,
            "topK": 40,
        }
        
        body: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config,
        }
        
        # Add system instruction if provided
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
        # Enable Google Search grounding for factual responses
        if enable_grounding:
            body["tools"] = [{"googleSearch": {}}]
        
        client = await self._get_client()
        
        try:
            response = await client.post(
                self._get_endpoint(model_name),
                json=body,
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract response
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in response")
            
            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            
            # Extract usage
            usage_metadata = data.get("usageMetadata", {})
            usage = {
                "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                "total_tokens": usage_metadata.get("totalTokenCount", 0),
            }
            
            # Extract grounding sources if present
            grounding_metadata = candidate.get("groundingMetadata", {})
            grounding_sources = grounding_metadata.get("groundingChunks", [])
            
            logger.info(
                f"Gemini generation complete",
                model=model_name,
                tokens=usage["total_tokens"],
                grounded=bool(grounding_sources),
            )
            
            return GeminiResponse(
                text=text,
                model=model_name,
                usage=usage,
                finish_reason=candidate.get("finishReason", "STOP"),
                grounding_sources=grounding_sources if grounding_sources else None,
                safety_ratings=candidate.get("safetyRatings"),
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise
    
    async def generate_with_context(
        self,
        prompt: str,
        context: str,
        model: Optional[GeminiModel] = None,
    ) -> GeminiResponse:
        """
        Generate with additional context (like a document or email thread).
        
        Useful for:
        - Email drafting with thread context
        - Document summarization
        - Research synthesis
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
            model=model or GeminiModel.FLASH_2_0,
            system_instruction=system_instruction,
        )
    
    async def deep_research(
        self,
        topic: str,
        max_steps: int = 5,
    ) -> ResearchResult:
        """
        Perform deep research on a topic using grounded search.
        
        Uses Gemini's grounding feature to:
        1. Search for relevant information
        2. Synthesize findings
        3. Provide citations
        
        Args:
            topic: Research topic
            max_steps: Maximum research iterations
            
        Returns:
            ResearchResult with findings and sources
        """
        system_instruction = """You are a research analyst for a GTM (Go-to-Market) team.
Your task is to research topics thoroughly and provide actionable insights.

For each research query:
1. Identify key aspects to investigate
2. Gather facts from reliable sources
3. Synthesize findings into actionable insights
4. Note confidence level in findings

Format your response as JSON with:
- summary: Executive summary (2-3 sentences)
- findings: Array of {aspect, insight, implication}
- confidence: 0.0-1.0 based on source quality"""

        prompt = f"""Research the following topic for a B2B sales/marketing context:

Topic: {topic}

Provide a comprehensive analysis with actionable insights."""

        response = await self.generate(
            prompt=prompt,
            model=GeminiModel.PRO_1_5,  # Use Pro for research depth
            system_instruction=system_instruction,
            enable_grounding=True,
            max_tokens=4096,
        )
        
        # Parse response
        try:
            # Try to extract JSON from response
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            data = json.loads(text)
            
            return ResearchResult(
                summary=data.get("summary", response.text[:200]),
                findings=data.get("findings", []),
                sources=[s.get("uri", "") for s in (response.grounding_sources or [])],
                confidence=float(data.get("confidence", 0.7)),
            )
        except (json.JSONDecodeError, KeyError):
            # Fallback to simple response
            return ResearchResult(
                summary=response.text[:500],
                findings=[{"aspect": "Research", "insight": response.text, "implication": "Review findings"}],
                sources=[s.get("uri", "") for s in (response.grounding_sources or [])],
                confidence=0.5,
            )
    
    async def draft_email(
        self,
        recipient_context: Dict[str, Any],
        purpose: str,
        thread_context: Optional[str] = None,
        voice_style: Optional[str] = None,
    ) -> str:
        """
        Draft a personalized email using Gemini.
        
        Args:
            recipient_context: Info about recipient (name, company, role, etc.)
            purpose: What the email should accomplish
            thread_context: Previous email thread for replies
            voice_style: Writing style preferences
            
        Returns:
            Draft email text
        """
        voice_instruction = voice_style or "Professional but friendly. Concise. Action-oriented."
        
        system_instruction = f"""You are drafting emails for a sales/marketing professional.

Voice and Style: {voice_instruction}

Guidelines:
- Keep emails concise (under 150 words for initial outreach)
- Include a clear call-to-action
- Personalize based on recipient context
- For replies, maintain thread continuity
- Never use overly salesy language"""

        recipient_info = "\n".join([f"- {k}: {v}" for k, v in recipient_context.items()])
        
        prompt = f"""Draft an email with the following context:

Recipient:
{recipient_info}

Purpose: {purpose}

{"Previous Thread:\n" + thread_context if thread_context else "This is an initial outreach."}

Write only the email body (no subject line)."""

        response = await self.generate(
            prompt=prompt,
            model=GeminiModel.FLASH_2_0,  # Fast model for drafting
            system_instruction=system_instruction,
            temperature=0.8,  # Slightly creative
            max_tokens=1024,
        )
        
        return response.text
    
    async def analyze_company(
        self,
        company_name: str,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Research and analyze a company for sales context.
        
        Uses grounding to get current information.
        
        Args:
            company_name: Company to research
            domain: Company domain for additional context
            
        Returns:
            Company analysis with key insights
        """
        prompt = f"""Analyze this company for B2B sales context:

Company: {company_name}
{f"Domain: {domain}" if domain else ""}

Provide:
1. Company overview (what they do, size, industry)
2. Recent news or developments
3. Potential pain points for a GTM/sales solution
4. Key decision-maker titles to target
5. Recommended approach for outreach

Format as JSON."""

        response = await self.generate(
            prompt=prompt,
            model=GeminiModel.FLASH_2_0,
            enable_grounding=True,
            max_tokens=2048,
        )
        
        try:
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "overview": response.text,
                "sources": response.grounding_sources,
            }
    
    async def summarize_thread(
        self,
        thread_messages: List[Dict[str, str]],
    ) -> str:
        """
        Summarize an email thread for quick context.
        
        Args:
            thread_messages: List of {from, date, content} dicts
            
        Returns:
            Concise thread summary
        """
        messages_text = "\n\n---\n\n".join([
            f"From: {m.get('from', 'Unknown')}\nDate: {m.get('date', 'Unknown')}\n\n{m.get('content', '')}"
            for m in thread_messages
        ])
        
        prompt = f"""Summarize this email thread:

{messages_text}

Provide:
1. Key topics discussed (bullet points)
2. Current status/where the conversation stands
3. Any action items or next steps
4. Sentiment (positive/neutral/negative)

Keep it under 100 words."""

        response = await self.generate(
            prompt=prompt,
            model=GeminiModel.FLASH_8B,  # Use efficient model for summarization
            temperature=0.3,  # Low temp for accuracy
            max_tokens=512,
        )
        
        return response.text
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Gemini API connectivity."""
        if not self.api_key:
            return {
                "status": "not_configured",
                "message": "GEMINI_API_KEY not set",
            }
        
        try:
            response = await self.generate(
                prompt="Reply with 'ok'",
                model=GeminiModel.FLASH_2_0,
                max_tokens=10,
            )
            return {
                "status": "healthy",
                "model": response.model,
                "message": "Gemini API connected",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
            }


# Singleton instance
_gemini_instance: Optional[GeminiConnector] = None


def get_gemini() -> GeminiConnector:
    """Get or create Gemini connector singleton."""
    global _gemini_instance
    if _gemini_instance is None:
        _gemini_instance = GeminiConnector()
    return _gemini_instance
