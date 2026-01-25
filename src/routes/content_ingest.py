"""
Content Ingestion API.

Endpoints for adding external content to the CaseyOS knowledge base.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.models.content import ContentMemory, ContentSourceType
from src.connectors.youtube import YoutubeConnector
from src.connectors.slack import SlackConnector
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/content", tags=["content"])

class IngestRequest(BaseModel):
    source_type: str  # "youtube", "drive", "slack", etc.
    url: str # For Slack this can be "channel_id:C12345" or web url
    title_override: str | None = None
    days_to_fetch: int = 30 # For Slack history lookback

class IngestResponse(BaseModel):
    id: str
    title: str
    source_id: str
    content_length: int

@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_content(payload: IngestRequest):
    """
    Ingest content from a URL or Source ID.
    
    Supports:
    - YouTube (extracts transcript)
    - Slack (fetches channel history, use channel ID as 'url')
    """
    source_type = payload.source_type.lower()
    
    # 1. YouTube Ingestion
    if source_type == ContentSourceType.YOUTUBE.value:
        connector = YoutubeConnector()
        try:
            data = await connector.get_video_content(payload.url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.exception(f"Ingestion failed for {payload.url}")
            raise HTTPException(status_code=500, detail="Internal ingestion error")
            
    # 2. Slack Ingestion
    elif source_type == ContentSourceType.SLACK.value:
        connector = SlackConnector()
        channel_id = payload.url # Treat provided URL as Channel ID
        
        try:
            messages = await connector.fetch_channel_history(
                channel_id=channel_id,
                days=payload.days_to_fetch
            )
            
            if not messages:
                raise HTTPException(status_code=404, detail="No messages found or channel inaccessible")
                
            # Convert messages to a single content block for "Knowledge"
            # Format: [Date] User: Message
            transcript_lines = []
            for msg in messages:
                user = msg.get("user", "Unknown")
                text = msg.get("text", "")
                ts = datetime.fromtimestamp(float(msg.get("ts", 0))).strftime('%Y-%m-%d %H:%M')
                transcript_lines.append(f"[{ts}] {user}: {text}")
            
            full_content = "\n".join(transcript_lines)
            
            data = {
                "source_id": channel_id,
                "source_url": f"slack://channel/{channel_id}",
                "title": f"Slack History: {channel_id}",
                "content": full_content,
                "metadata": {"message_count": len(messages), "days": payload.days_to_fetch}
            }
            
        except Exception as e:
            logger.exception(f"Slack ingestion failed for {channel_id}")
            raise HTTPException(status_code=500, detail=f"Slack ingestion error: {str(e)}")

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Unsupported source type: '{source_type}'"
        )

    # Store in DB
    async with get_session() as session:
        content_item = ContentMemory(
            source_type=source_type,
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
