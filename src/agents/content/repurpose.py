"""ContentRepurposeAgent - Transform one piece of content into multiple formats.

Takes a single source (case study, blog post, webinar) and generates:
- LinkedIn posts (carousel-style or single)
- Twitter/X threads
- Email snippets
- Newsletter sections
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select

from src.agents.base import BaseAgent
from src.logger import get_logger
from src.db import get_session
from src.models.content import ContentMemory

logger = get_logger(__name__)


class ContentRepurposeAgent(BaseAgent):
    """Repurposes one piece of content into multiple distribution formats.
    
    Example:
        agent = ContentRepurposeAgent(drive_connector, llm_connector)
        result = await agent.execute({
            "source_doc_id": "1abc...",  # Drive file ID
            "formats": ["linkedin", "twitter", "email"],
            "tone": "professional_casual",
            "brand_voice": "confident, helpful, no jargon",
        })
    """

    # Output format templates
    FORMATS = {
        "linkedin": {
            "count": 3,
            "max_chars": 3000,
            "include_emoji": True,
            "include_hashtags": True,
        },
        "twitter": {
            "count": 1,  # Thread
            "max_tweets": 5,
            "max_chars_per_tweet": 280,
        },
        "email": {
            "count": 1,
            "max_chars": 500,
            "type": "snippet",  # Not full email, just usable paragraph
        },
        "newsletter": {
            "count": 1,
            "max_chars": 800,
            "include_cta": True,
        },
    }

    def __init__(
        self,
        drive_connector=None,
        llm_connector=None,
    ):
        """Initialize with connectors."""
        super().__init__(
            name="Content Repurpose Agent",
            description="Transforms source content into multiple distribution formats"
        )
        self.drive_connector = drive_connector
        self.llm_connector = llm_connector

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input has source content."""
        return (
            "source_doc_id" in context or 
            "source_text" in context or
            "source_url" in context or
            "source_content_memory_id" in context
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute content repurposing."""
        logger.info("ContentRepurposeAgent executing")
        
        if not await self.validate_input(context):
            return {"status": "error", "error": "No source content provided"}
        
        try:
            # 1. Extract source content
            source_content = await self._get_source_content(context)
            if not source_content:
                return {"status": "error", "error": "Could not extract source content"}
            
            # 2. Determine output formats
            formats = context.get("formats", ["linkedin", "email"])
            
            # 3. Generate each format
            outputs = {}
            queue_items = []
            
            for fmt in formats:
                if fmt in self.FORMATS:
                    generated = await self._generate_format(
                        source_content=source_content,
                        format_type=fmt,
                        format_config=self.FORMATS[fmt],
                        context=context,
                    )
                    outputs[fmt] = generated
                    
                    # Create queue items for review
                    for i, item in enumerate(generated.get("items", [])):
                        queue_items.append({
                            "type": f"content_{fmt}",
                            "title": f"{fmt.title()} Post #{i+1}",
                            "content": item,
                            "status": "pending_review",
                        })
            
            return {
                "status": "success",
                "source_summary": source_content[:200] + "...",
                "formats_generated": list(outputs.keys()),
                "outputs": outputs,
                "queue_items_created": len(queue_items),
                "queue_items": queue_items,
                "generated_at": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"ContentRepurposeAgent error: {e}")
            return {"status": "error", "error": str(e)}

    async def _get_source_content(self, context: Dict[str, Any]) -> Optional[str]:
        """Extract source content from various inputs."""
        # Direct text
        if "source_text" in context:
            return context["source_text"]
            
        # From Content Memory (DB)
        if "source_content_memory_id" in context:
            try:
                cm_id = context["source_content_memory_id"]
                async with get_session() as session:
                    result = await session.execute(
                        select(ContentMemory).where(ContentMemory.id == cm_id)
                    )
                    record = result.scalars().first()
                    if record and record.content:
                        return record.content
                    logger.warning(f"ContentMemory record not found or empty: {cm_id}")
            except Exception as e:
                logger.error(f"Error fetching from ContentMemory: {e}")
        
        # From Drive
        if "source_doc_id" in context and self.drive_connector:
            try:
                doc = await self.drive_connector.get_file_content(context["source_doc_id"])
                return doc.get("content", "")
            except Exception as e:
                logger.warning(f"Could not get Drive doc: {e}")
        
        # From URL (future: web scraping)
        if "source_url" in context:
            # TODO: Implement web scraping
            logger.warning("URL extraction not yet implemented")
        
        return None

    async def _generate_format(
        self,
        source_content: str,
        format_type: str,
        format_config: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate content in a specific format."""
        if not self.llm_connector:
            # Return placeholder if no LLM
            return {
                "items": [f"[Placeholder {format_type} content - LLM not configured]"],
                "format": format_type,
            }
        
        tone = context.get("tone", "professional")
        brand_voice = context.get("brand_voice", "confident and helpful")
        
        prompt = self._build_prompt(
            source_content=source_content,
            format_type=format_type,
            format_config=format_config,
            tone=tone,
            brand_voice=brand_voice,
        )
        
        try:
            response = await self.llm_connector.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=2000,
            )
            
            # Parse response into items
            items = self._parse_response(response, format_type)
            
            return {
                "items": items,
                "format": format_type,
                "config": format_config,
            }
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return {"items": [], "error": str(e)}

    def _build_prompt(
        self,
        source_content: str,
        format_type: str,
        format_config: Dict[str, Any],
        tone: str,
        brand_voice: str,
    ) -> str:
        """Build LLM prompt for content generation."""
        count = format_config.get("count", 1)
        max_chars = format_config.get("max_chars", 500)
        
        if format_type == "linkedin":
            return f"""Transform this content into {count} LinkedIn posts.

SOURCE CONTENT:
{source_content}

REQUIREMENTS:
- Tone: {tone}
- Brand voice: {brand_voice}
- Max {max_chars} characters per post
- Include 2-3 relevant hashtags
- Start with a hook that stops the scroll
- End with a question or CTA to drive engagement
- Use line breaks for readability

Generate {count} distinct posts, each offering a different angle on the content.
Separate each post with "---POST---"
"""
        
        elif format_type == "twitter":
            max_tweets = format_config.get("max_tweets", 5)
            return f"""Transform this content into a Twitter/X thread.

SOURCE CONTENT:
{source_content}

REQUIREMENTS:
- Tone: {tone}
- Brand voice: {brand_voice}
- Max 280 characters per tweet
- {max_tweets} tweets maximum
- Start with a hook (Tweet 1)
- Number each tweet (1/, 2/, etc.)
- End with a CTA

Separate each tweet with "---TWEET---"
"""
        
        elif format_type == "email":
            return f"""Transform this content into an email snippet.

SOURCE CONTENT:
{source_content}

REQUIREMENTS:
- Tone: {tone}
- Brand voice: {brand_voice}
- Max {max_chars} characters
- Focus on the key insight or value prop
- Include a soft CTA
- This is a snippet to include in a larger email, not a full email

Output just the snippet.
"""
        
        elif format_type == "newsletter":
            return f"""Transform this content into a newsletter section.

SOURCE CONTENT:
{source_content}

REQUIREMENTS:
- Tone: {tone}
- Brand voice: {brand_voice}
- Max {max_chars} characters
- Include a headline
- 2-3 short paragraphs
- End with a CTA link placeholder [LINK]

Output the newsletter section.
"""
        
        return f"Summarize this content in {max_chars} characters:\n{source_content}"

    def _parse_response(self, response: str, format_type: str) -> List[str]:
        """Parse LLM response into individual items."""
        if format_type == "linkedin":
            return [p.strip() for p in response.split("---POST---") if p.strip()]
        elif format_type == "twitter":
            return [t.strip() for t in response.split("---TWEET---") if t.strip()]
        else:
            return [response.strip()]
