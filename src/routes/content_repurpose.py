from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from src.connectors.llm import LLMConnector
from src.agents.content.repurpose import ContentRepurposeAgent
from src.logger import get_logger

router = APIRouter(prefix="/api/content/repurpose", tags=["Content Engine"])
logger = get_logger(__name__)

class RepurposeRequest(BaseModel):
    content_memory_id: str
    formats: List[str] = ["linkedin", "newsletter"]
    tone: str = "professional"

@router.post("/")
async def repurpose_content(request: RepurposeRequest):
    """
    Repurpose a ContentMemory item into social posts/newsletters.
    """
    try:
        # Initialize connectors (Drive is optional but good to have if we expand)
        llm = LLMConnector()
        agent = ContentRepurposeAgent(llm_connector=llm)

        context = {
            "source_content_memory_id": request.content_memory_id,
            "formats": request.formats,
            "tone": request.tone
        }

        result = await agent.execute(context)
        
        if result.get("status") == "error":
             raise HTTPException(status_code=400, detail=result.get("error"))

        return result

    except Exception as e:
        logger.error(f"Repurpose API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
