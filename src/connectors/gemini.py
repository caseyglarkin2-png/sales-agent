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

    async def analyze_context(
        self,
        context_text: str,
        query: str,
        model: Optional[GeminiModel] = GeminiModel.PRO_1_5,
    ) -> str:
        """
        Analyze a large context (documents) and answer a query.
        
        Args:
            context_text: The massive text block from documents.
            query: The user's question.
            model: Defaults to PRO_1_5 (1M context).
            
        Returns:
            The analysis result.
        """
        # Truncate if insanely large (safety check), though 1M is huge.
        # 1 token ~= 4 chars. 1M tokens ~= 4MB text.
        max_chars = 10 * 1024 * 1024  # Cap at 10MB approx
        if len(context_text) > max_chars:
            logger.warning("Context truncated to 10MB characters")
            context_text = context_text[:max_chars]

        prompt = f"""
        You are a Deep Research expert. You have access to the following Internal Knowledge Block.
        Answer the query based ONLY on this context. 
        If the answer is not in the context, state that clearly.
        
        === INTERNAL KNOWLEDGE BLOCK START ===
        {context_text}
        === INTERNAL KNOWLEDGE BLOCK END ===
        
        QUERY: {query}
        """
        
        response = await self.generate(
            prompt=prompt,
            model=model,
            max_tokens=8192,
            temperature=0.3,  # More factual
        )
        
        return response.text
    
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
        """
        Check Gemini API connectivity.
        
        Uses a cached result to avoid rate limiting on repeated health checks.
        Cache expires after 60 seconds.
        """
        if not self.api_key:
            return {
                "status": "not_configured",
                "message": "GEMINI_API_KEY not set",
            }
        
        # Check cached health result
        import time
        cache_key = "_health_cache"
        cache_ttl = 60  # Cache for 60 seconds
        
        cached = getattr(self, cache_key, None)
        if cached and (time.time() - cached.get("timestamp", 0)) < cache_ttl:
            return cached.get("result", {"status": "cached"})
        
        try:
            start = time.time()
            response = await self.generate(
                prompt="Reply with 'ok'",
                model=GeminiModel.FLASH_8B,  # Use smallest model for health check
                max_tokens=5,
                temperature=0,
            )
            latency_ms = (time.time() - start) * 1000
            
            result = {
                "status": "healthy",
                "model": response.model,
                "latency_ms": round(latency_ms, 2),
                "message": "Gemini API connected",
            }
            
            # Cache result
            setattr(self, cache_key, {"timestamp": time.time(), "result": result})
            
            return result
        except Exception as e:
            error_msg = str(e)
            # Check for rate limit error
            if "429" in error_msg:
                result = {
                    "status": "rate_limited",
                    "message": "Rate limited - try again later",
                }
            else:
                result = {
                    "status": "error",
                    "message": error_msg,
                }
            
            # Cache error result for shorter time
            setattr(self, cache_key, {"timestamp": time.time(), "result": result})
            
            return result
    
    # ==================== CANVAS FEATURES ====================
    
    async def create_document(
        self,
        title: str,
        content_type: str = "sales_proposal",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a structured document using Canvas-like generation.
        
        Content types:
        - sales_proposal: Full sales proposal with sections
        - meeting_recap: Meeting summary with action items
        - case_study: Customer success story
        - battle_card: Competitive analysis card
        - email_sequence: Multi-email nurture sequence
        
        Args:
            title: Document title
            content_type: Type of document to generate
            context: Additional context (company info, deal details, etc.)
            
        Returns:
            Document with sections and metadata
        """
        templates = {
            "sales_proposal": """Create a professional sales proposal with these sections:
1. Executive Summary (2-3 sentences)
2. Understanding Your Needs (based on context)
3. Our Solution
4. Key Benefits (bullet points)
5. Investment & Timeline
6. Next Steps

Format as JSON with sections array.""",
            
            "meeting_recap": """Create a meeting recap with:
1. Meeting Overview (date, attendees, purpose)
2. Key Discussion Points
3. Decisions Made
4. Action Items (with owners and due dates)
5. Next Meeting

Format as JSON.""",
            
            "case_study": """Create a customer case study with:
1. Customer Overview
2. Challenge
3. Solution
4. Results (with metrics)
5. Customer Quote

Format as JSON.""",
            
            "battle_card": """Create a competitive battle card with:
1. Competitor Overview
2. Their Strengths
3. Their Weaknesses
4. Our Advantages
5. Common Objections & Responses
6. Win Themes

Format as JSON.""",
            
            "email_sequence": """Create a 3-email nurture sequence with:
1. Initial Outreach (subject, body)
2. Follow-up #1 (subject, body, wait_days)
3. Follow-up #2 (subject, body, wait_days)

Format as JSON with emails array.""",
        }
        
        template = templates.get(content_type, templates["sales_proposal"])
        context_str = json.dumps(context or {}, indent=2)
        
        prompt = f"""Title: {title}

Context:
{context_str}

{template}"""

        response = await self.generate(
            prompt=prompt,
            model=GeminiModel.PRO_1_5,  # Use Pro for document generation
            temperature=0.7,
            max_tokens=4096,
            system_instruction="You are a professional business writer. Create well-structured, compelling documents.",
        )
        
        try:
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            document = json.loads(text)
            document["_meta"] = {
                "title": title,
                "type": content_type,
                "model": response.model,
                "tokens_used": response.usage.get("total_tokens", 0),
            }
            return document
        except json.JSONDecodeError:
            return {
                "title": title,
                "type": content_type,
                "content": response.text,
                "_meta": {"raw": True},
            }
    
    async def refine_content(
        self,
        content: str,
        instruction: str,
        preserve_structure: bool = True,
    ) -> str:
        """
        Refine/edit existing content based on instructions.
        
        Canvas-like editing capability.
        
        Args:
            content: Original content to refine
            instruction: What to change (e.g., "make it more concise", "add humor")
            preserve_structure: Keep the original structure
            
        Returns:
            Refined content
        """
        system = "You are an expert editor. Refine the content based on instructions."
        if preserve_structure:
            system += " Preserve the original structure and format."
        
        prompt = f"""Original Content:
{content}

---

Instruction: {instruction}

Provide the refined content:"""

        response = await self.generate(
            prompt=prompt,
            model=GeminiModel.FLASH_2_0,
            temperature=0.5,
            max_tokens=4096,
            system_instruction=system,
        )
        
        return response.text
    
    # ==================== MULTIMODAL FEATURES ====================
    
    async def analyze_image(
        self,
        image_data: bytes,
        prompt: str = "Describe this image in detail.",
        mime_type: str = "image/png",
    ) -> str:
        """
        Analyze an image using Gemini's vision capabilities.
        
        Args:
            image_data: Raw image bytes
            prompt: What to analyze/extract from the image
            mime_type: Image MIME type (image/png, image/jpeg, etc.)
            
        Returns:
            Analysis text
        """
        import base64
        
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        
        body = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": image_b64,
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 2048,
            }
        }
        
        client = await self._get_client()
        
        try:
            response = await client.post(
                self._get_endpoint(GeminiModel.FLASH_2_0.value),
                json=body,
            )
            response.raise_for_status()
            data = response.json()
            
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts)
            return "Could not analyze image"
            
        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            raise
    
    async def analyze_document_image(
        self,
        image_data: bytes,
        extraction_type: str = "text",
    ) -> Dict[str, Any]:
        """
        Extract structured data from document images.
        
        Useful for:
        - Business cards → contact info
        - Invoices → line items
        - Contracts → key terms
        - Screenshots → UI elements
        
        Args:
            image_data: Raw image bytes
            extraction_type: What to extract (text, contact, invoice, contract)
            
        Returns:
            Extracted data as structured JSON
        """
        prompts = {
            "text": "Extract all text from this image. Return as plain text.",
            "contact": """Extract contact information from this business card.
Return JSON with: name, title, company, email, phone, address, linkedin, website""",
            "invoice": """Extract invoice data from this document.
Return JSON with: invoice_number, date, vendor, line_items (array), subtotal, tax, total""",
            "contract": """Extract key terms from this contract.
Return JSON with: parties, effective_date, term_length, key_obligations, payment_terms, termination_clause""",
        }
        
        prompt = prompts.get(extraction_type, prompts["text"])
        result = await self.analyze_image(image_data, prompt)
        
        if extraction_type == "text":
            return {"text": result}
        
        try:
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw": result}
    
    # ==================== STREAMING FEATURES ====================
    
    async def generate_stream(
        self,
        prompt: str,
        model: Optional[GeminiModel] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        """
        Generate text with streaming response.
        
        Yields chunks as they're generated.
        
        Args:
            prompt: User prompt
            model: Gemini model
            temperature: Creativity
            max_tokens: Max output tokens
            
        Yields:
            Text chunks as they arrive
        """
        model_name = (model or self.default_model).value
        
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        endpoint = f"{self.BASE_URL}/models/{model_name}:streamGenerateContent?key={self.api_key}"
        
        client = await self._get_client()
        
        try:
            async with client.stream("POST", endpoint, json=body) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    if "text" in part:
                                        yield part["text"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            raise
    
    # ==================== ADVANCED SALES FEATURES ====================
    
    async def score_lead(
        self,
        lead_data: Dict[str, Any],
        icp_criteria: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        AI-powered lead scoring with explanation.
        
        Args:
            lead_data: Lead information (name, company, role, etc.)
            icp_criteria: Ideal Customer Profile criteria
            
        Returns:
            Score (0-100) with reasoning
        """
        default_icp = {
            "company_size": "50-500 employees",
            "industry": "B2B SaaS, Technology",
            "role": "VP Sales, CRO, Head of Revenue",
            "pain_points": "sales efficiency, pipeline visibility, forecasting",
        }
        
        icp = icp_criteria or default_icp
        
        prompt = f"""Score this lead against our ICP criteria.

Lead Data:
{json.dumps(lead_data, indent=2)}

ICP Criteria:
{json.dumps(icp, indent=2)}

Return JSON with:
- score: 0-100 overall fit score
- fit_reasons: array of why they fit
- gaps: array of concerns
- recommended_action: what to do next
- priority: high/medium/low"""

        response = await self.generate(
            prompt=prompt,
            model=GeminiModel.FLASH_2_0,
            temperature=0.3,
            max_tokens=1024,
            enable_grounding=True,  # Get real company data
        )
        
        try:
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            return json.loads(text)
        except json.JSONDecodeError:
            return {"score": 50, "raw_analysis": response.text}
    
    async def generate_objection_response(
        self,
        objection: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate response to sales objection.
        
        Args:
            objection: The objection raised
            context: Deal context (product, stage, etc.)
            
        Returns:
            Response with talk track and supporting points
        """
        context_str = json.dumps(context or {}, indent=2)
        
        prompt = f"""A prospect raised this objection:

"{objection}"

Context: {context_str}

Provide a response with:
1. Acknowledge (show understanding)
2. Reframe (shift perspective)
3. Evidence (data/case study reference)
4. Bridge to value
5. Suggested response (2-3 sentences)

Return as JSON."""

        response = await self.generate(
            prompt=prompt,
            model=GeminiModel.FLASH_2_0,
            temperature=0.6,
            max_tokens=1024,
        )
        
        try:
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            return json.loads(text)
        except json.JSONDecodeError:
            return {"response": response.text}

    # =========================================================================
    # Sprint 36: Tool/Function Calling Support
    # =========================================================================
    
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        model: Optional[GeminiModel] = None,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate with function/tool calling support.
        
        Enables Gemini to decide when to call tools and returns
        either a text response or a tool call request.
        
        Args:
            prompt: User prompt
            tools: List of tool definitions in Gemini format
            model: Model to use
            system_instruction: System context
            
        Returns:
            Dict with either:
            - {"type": "text", "content": "response text"}
            - {"type": "tool_call", "name": "tool_name", "args": {...}}
        """
        model_name = (model or self.default_model).value
        
        body: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"functionDeclarations": tools}],
            "generationConfig": {
                "temperature": 0.3,  # Lower for tool calling
                "maxOutputTokens": 2048,
            },
        }
        
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
        client = await self._get_client()
        
        try:
            response = await client.post(
                self._get_endpoint(model_name),
                json=body,
            )
            response.raise_for_status()
            data = response.json()
            
            candidates = data.get("candidates", [])
            if not candidates:
                return {"type": "error", "message": "No candidates in response"}
            
            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            
            # Check for function call
            for part in parts:
                if "functionCall" in part:
                    fc = part["functionCall"]
                    logger.info(f"Gemini requested tool call: {fc.get('name')}")
                    return {
                        "type": "tool_call",
                        "name": fc.get("name"),
                        "args": fc.get("args", {}),
                    }
            
            # Text response
            text = "".join(p.get("text", "") for p in parts if "text" in p)
            return {"type": "text", "content": text}
            
        except Exception as e:
            logger.error(f"Gemini tool call error: {e}")
            return {"type": "error", "message": str(e)}
    
    async def continue_with_tool_result(
        self,
        original_prompt: str,
        tool_name: str,
        tool_result: Any,
        tools: List[Dict[str, Any]],
        model: Optional[GeminiModel] = None,
        system_instruction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Continue generation after providing a tool result.
        
        Args:
            original_prompt: The original user prompt
            tool_name: Name of the tool that was called
            tool_result: Result from executing the tool
            tools: Tool definitions
            model: Model to use
            system_instruction: System context
            
        Returns:
            Next response (text or another tool call)
        """
        model_name = (model or self.default_model).value
        
        # Build conversation with tool result
        contents = [
            {"role": "user", "parts": [{"text": original_prompt}]},
            {
                "role": "model",
                "parts": [{"functionCall": {"name": tool_name, "args": {}}}]
            },
            {
                "role": "function",
                "parts": [{
                    "functionResponse": {
                        "name": tool_name,
                        "response": {"result": tool_result}
                    }
                }]
            }
        ]
        
        body: Dict[str, Any] = {
            "contents": contents,
            "tools": [{"functionDeclarations": tools}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048,
            },
        }
        
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        
        client = await self._get_client()
        
        try:
            response = await client.post(
                self._get_endpoint(model_name),
                json=body,
            )
            response.raise_for_status()
            data = response.json()
            
            candidates = data.get("candidates", [])
            if not candidates:
                return {"type": "error", "message": "No candidates in response"}
            
            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            
            # Check for another function call
            for part in parts:
                if "functionCall" in part:
                    fc = part["functionCall"]
                    return {
                        "type": "tool_call",
                        "name": fc.get("name"),
                        "args": fc.get("args", {}),
                    }
            
            # Text response
            text = "".join(p.get("text", "") for p in parts if "text" in p)
            return {"type": "text", "content": text}
            
        except Exception as e:
            logger.error(f"Gemini continue error: {e}")
            return {"type": "error", "message": str(e)}


# Singleton instance
_gemini_instance: Optional[GeminiConnector] = None


def get_gemini() -> GeminiConnector:
    """Get or create Gemini connector singleton."""
    global _gemini_instance
    if _gemini_instance is None:
        _gemini_instance = GeminiConnector()
    return _gemini_instance
