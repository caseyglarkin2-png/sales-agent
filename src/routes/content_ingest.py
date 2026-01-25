"""
Content Ingestion API.

Endpoints for adding external content to the CaseyOS knowledge base.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.models.content import ContentMemory, ContentSourceType
from src.connectors.youtube import YoutubeConnector
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/content", tags=["content"])

class IngestRequest(BaseModel):
    source_type: str  # "youtube", "drive", etc.
    url: str
    title_override: str | None = None

class IngestResponse(BaseModel):
    id: str
    title: str
    source_id: str
    content_length: int

@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_content(payload: IngestRequest):
    """
    Ingest content from a URL.
    
    Currently supports:
    - YouTube (extracts transcript)
    """
    if payload.source_type.lower() != ContentSourceType.YOUTUBE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Currently only '{ContentSourceType.YOUTUBE.value}' is supported."
        )

    connector = YoutubeConnector()
    
    try:
        data = await connector.get_video_content(payload.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Ingestion failed for {payload.url}")
        raise HTTPException(status_code=500, detail="Internal ingestion error")

    # Store in DB
    async with get_session() as session:
        content_item = ContentMemory(
            source_type=ContentSourceType.YOUTUBE.value,
            source_id=data["source_id"],
            source_url=data["source_url"],
            title=payload.title_override or data["title"],
            content=data["content"],
            content_metadata=data["metadata"]
        )
        session.add(content_item)
        await session.commit()
        await session.refresh(content_item)
        
        return IngestResponse(
            id=str(content_item.id),
            title=content_item.title,
            source_id=content_item.source_id,
            content_length=len(content_item.content)
        )
