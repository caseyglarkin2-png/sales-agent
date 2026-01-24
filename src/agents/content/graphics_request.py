"""GraphicsRequestAgent - Create and queue design briefs.

Generates structured design briefs for graphics needs and queues them
for a designer (human or AI like Canva/Figma plugins).
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class DesignType(str, Enum):
    """Types of design requests."""
    SOCIAL_POST = "social_post"
    PRESENTATION = "presentation"
    INFOGRAPHIC = "infographic"
    EMAIL_HEADER = "email_header"
    CASE_STUDY = "case_study"
    LOGO = "logo"
    BANNER = "banner"
    THUMBNAIL = "thumbnail"


class Priority(str, Enum):
    """Design request priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class GraphicsRequestAgent(BaseAgent):
    """Creates design briefs and queues graphics requests.
    
    Example:
        agent = GraphicsRequestAgent()
        result = await agent.execute({
            "action": "create_brief",
            "design_type": "social_post",
            "title": "Q4 Results Announcement",
            "description": "Celebrate our 40% growth with a LinkedIn carousel",
            "brand_colors": ["#1E88E5", "#FFC107"],
            "dimensions": "1080x1080",
            "priority": "high",
        })
    """

    # Standard dimensions by design type
    STANDARD_DIMENSIONS = {
        DesignType.SOCIAL_POST: {
            "linkedin": "1200x1200",
            "twitter": "1200x675",
            "instagram": "1080x1080",
            "facebook": "1200x630",
        },
        DesignType.PRESENTATION: "1920x1080",
        DesignType.INFOGRAPHIC: "800x2000",
        DesignType.EMAIL_HEADER: "600x200",
        DesignType.BANNER: "1920x400",
        DesignType.THUMBNAIL: "1280x720",
    }

    def __init__(self, canva_connector=None, figma_connector=None):
        """Initialize with optional design tool connectors."""
        super().__init__(
            name="Graphics Request Agent",
            description="Creates design briefs and queues graphics requests"
        )
        self.canva_connector = canva_connector
        self.figma_connector = figma_connector
        
        # In-memory queue (would be DB in production)
        self._request_queue: List[Dict[str, Any]] = []

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input."""
        action = context.get("action", "create_brief")
        if action == "create_brief":
            return "design_type" in context or "description" in context
        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute graphics request action."""
        action = context.get("action", "create_brief")
        
        if action == "create_brief":
            return await self._create_brief(context)
        elif action == "list_queue":
            return await self._list_queue(context)
        elif action == "get_templates":
            return await self._get_templates(context)
        elif action == "update_status":
            return await self._update_status(context)
        else:
            return {"status": "error", "error": f"Unknown action: {action}"}

    async def _create_brief(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a design brief and add to queue."""
        design_type = context.get("design_type", "social_post")
        platform = context.get("platform", "linkedin")
        
        # Get dimensions
        if design_type in [dt.value for dt in DesignType]:
            dim_config = self.STANDARD_DIMENSIONS.get(DesignType(design_type), "1200x1200")
            if isinstance(dim_config, dict):
                dimensions = dim_config.get(platform, "1200x1200")
            else:
                dimensions = dim_config
        else:
            dimensions = context.get("dimensions", "1200x1200")
        
        brief = {
            "id": f"design-{datetime.utcnow().timestamp()}",
            "design_type": design_type,
            "platform": platform,
            "title": context.get("title", "Untitled Design"),
            "description": context.get("description", ""),
            "dimensions": dimensions,
            "brand_colors": context.get("brand_colors", []),
            "brand_fonts": context.get("brand_fonts", []),
            "reference_images": context.get("reference_images", []),
            "copy_text": context.get("copy_text", ""),
            "cta": context.get("cta", ""),
            "priority": context.get("priority", Priority.MEDIUM.value),
            "deadline": context.get("deadline"),
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "assigned_to": None,
        }
        
        # Add brand guidelines
        brief["brand_guidelines"] = self._get_brand_guidelines(context)
        
        # Generate prompt for AI design tools
        brief["ai_prompt"] = self._generate_ai_prompt(brief)
        
        self._request_queue.append(brief)
        
        logger.info(f"Created design brief: {brief['id']} - {brief['title']}")
        
        return {
            "status": "success",
            "brief": brief,
            "message": f"Design brief created and queued",
            "queue_position": len(self._request_queue),
        }

    async def _list_queue(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List queued design requests."""
        status = context.get("status")
        priority = context.get("priority")
        
        requests = self._request_queue
        
        if status:
            requests = [r for r in requests if r["status"] == status]
        if priority:
            requests = [r for r in requests if r["priority"] == priority]
        
        # Sort by priority and created_at
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        requests = sorted(
            requests,
            key=lambda x: (priority_order.get(x["priority"], 2), x["created_at"])
        )
        
        return {
            "status": "success",
            "count": len(requests),
            "requests": requests,
        }

    async def _get_templates(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get available design templates."""
        design_type = context.get("design_type")
        
        # Mock templates - would come from Canva/Figma API
        templates = [
            {
                "id": "template-001",
                "name": "Modern LinkedIn Post",
                "type": "social_post",
                "platform": "linkedin",
                "preview_url": "https://example.com/preview1.png",
            },
            {
                "id": "template-002",
                "name": "Case Study Layout",
                "type": "case_study",
                "platform": "pdf",
                "preview_url": "https://example.com/preview2.png",
            },
            {
                "id": "template-003",
                "name": "Stats Infographic",
                "type": "infographic",
                "platform": "general",
                "preview_url": "https://example.com/preview3.png",
            },
        ]
        
        if design_type:
            templates = [t for t in templates if t["type"] == design_type]
        
        return {
            "status": "success",
            "templates": templates,
        }

    async def _update_status(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update status of a design request."""
        request_id = context.get("request_id")
        new_status = context.get("new_status")
        assigned_to = context.get("assigned_to")
        
        for request in self._request_queue:
            if request["id"] == request_id:
                if new_status:
                    request["status"] = new_status
                if assigned_to:
                    request["assigned_to"] = assigned_to
                request["updated_at"] = datetime.utcnow().isoformat()
                
                return {
                    "status": "success",
                    "request": request,
                }
        
        return {"status": "error", "error": f"Request not found: {request_id}"}

    def _get_brand_guidelines(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get brand guidelines for the design."""
        # Default brand guidelines - would come from config/DB
        return {
            "primary_color": context.get("brand_colors", ["#1E88E5"])[0] if context.get("brand_colors") else "#1E88E5",
            "secondary_color": context.get("brand_colors", ["#1E88E5", "#FFC107"])[1] if len(context.get("brand_colors", [])) > 1 else "#FFC107",
            "font_headline": "Inter Bold",
            "font_body": "Inter Regular",
            "logo_placement": "top-left or bottom-right",
            "style": "modern, clean, professional",
        }

    def _generate_ai_prompt(self, brief: Dict[str, Any]) -> str:
        """Generate a prompt for AI design tools like DALL-E or Midjourney."""
        return f"""Create a {brief['design_type']} design with these specifications:

DIMENSIONS: {brief['dimensions']}
TITLE: {brief['title']}
DESCRIPTION: {brief['description']}

STYLE REQUIREMENTS:
- Modern, clean, professional aesthetic
- Primary color: {brief['brand_guidelines']['primary_color']}
- Secondary color: {brief['brand_guidelines']['secondary_color']}
- High contrast for readability
- No stock photo feel - authentic and original

TEXT TO INCLUDE:
{brief.get('copy_text', 'No text specified')}

CTA: {brief.get('cta', 'None')}

Generate a visually striking design that would perform well on {brief['platform']}.
"""
