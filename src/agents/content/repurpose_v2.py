"""ContentRepurposeAgent V2 - Specialized for 'Dude What's The Bid?!' content.

Deep Research / Context-Aware repurposing of transcripts into:
- Viral LinkedIn Posts (Freight/Sales focus)
- Newsletter Sections (The Freight Marketer)
"""
from typing import Any, Dict, List, Optional
from sqlalchemy import select

from src.agents.base import BaseAgent
from src.logger import get_logger
from src.db import get_session
from src.models.content import ContentMemory
from src.connectors.llm import LLMConnector

logger = get_logger(__name__)


class ContentRepurposeAgentV2(BaseAgent):
    """
    Repurposes YouTube transcripts into specific GTM assets.
    
    Status: Sprint 23 (Active)
    """

    def __init__(self, llm_connector: Optional[LLMConnector] = None):
        super().__init__(
            name="Content Repurpose V2", 
            description="Transforms transcripts into Freight Marketer assets"
        )
        self.llm = llm_connector or LLMConnector(provider="gemini")

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Requires a valid content_memory_id."""
        return "content_memory_id" in context

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the repurposing workflow.
        
        Args:
            context: {
                "content_memory_id": str (UUID),
                "formats": List[str] (optional, default=["linkedin", "newsletter"])
            }
        """
        memory_id = context.get("content_memory_id")
        formats = context.get("formats", ["linkedin", "newsletter"])

        # 1. Fetch Transcript
        transcript = await self._fetch_transcript(memory_id)
        if not transcript:
            return {
                "status": "error",
                "error": f"ContentMemory {memory_id} not found"
            }

        # 2. Limit context window if needed (Gemini handle 1M+, but let's be safe for costs/speed)
        # For now, we pass the whole thing as Gemini 1.5 Pro is the standard.
        
        results = {}
        
        # 3. Generate requested formats
        for fmt in formats:
            if fmt == "linkedin":
                results["linkedin"] = await self._generate_linkedin(transcript)
            elif fmt == "newsletter":
                results["newsletter"] = await self._generate_newsletter(transcript)

        return {
            "status": "success",
            "source_id": memory_id,
            "outputs": results
        }

    async def _fetch_transcript(self, memory_id: str) -> Optional[str]:
        """Retrieve transcript text from Postgres."""
        async with get_session() as session:
            # Check if UUID or string usage depending on model implementation
            # Assuming standard lookup
            stmt = select(ContentMemory).where(ContentMemory.id == memory_id)
            result = await session.execute(stmt)
            item = result.scalar_one_or_none()
            return item.content if item else None

    async def _generate_linkedin(self, transcript: str) -> str:
        """Generate a viral-style LinkedIn post."""
        prompt = f"""
        You are the ghostwriter for "Dude What's The Bid?!", a leading freight sales brand.
        
        TASK: Write a viral LinkedIn post based on the TRANSCRIPT below.
        
        STYLE GUIDE:
        - Hook: First line must be controversial or high-value. Break the pattern.
        - Voice: Confident, "Freight Marketer", High Energy, No Fluff.
        - Structure: Short paragraphs (1-2 lines). visually scannable.
        - Goal: Drive engagement from freight brokers and logistics sales pros.
        - Tone: "I've been in the trenches, here is the truth."
        
        TRANSCRIPT:
        {transcript[:100000]}  # Limit to 100k chars to be safe, though Gemini can handle more
        
        OUTPUT:
        Write ONLY the post content. No pre-amble.
        """
        return await self.llm.generate_text(prompt)

    async def _generate_newsletter(self, transcript: str) -> str:
        """Generate a section for 'The Freight Marketer' newsletter."""
        prompt = f"""
        You are the editor of "The Freight Marketer" newsletter.
        
        TASK: Write a deep-dive newsletter section based on the TRANSCRIPT below.
        
        STYLE GUIDE:
        - Headline: Catchy, value-driven.
        - Voice: Educational, Insightful, Professional but Conversational.
        - Structure: Introduction -> Core Insight/Story -> Actionable Takeaway.
        - Audience: Logistics professionals looking to modernize their sales.
        - Length: 300-500 words.
        
        TRANSCRIPT:
        {transcript[:100000]}
        
        OUTPUT:
        Write ONLY the newsletter section. No pre-amble.
        """
        return await self.llm.generate_text(prompt)
