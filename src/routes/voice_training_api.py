"""
Voice training API endpoints.

Supports uploading training samples from multiple sources:
- Google Drive files
- HubSpot email threads
- YouTube videos
- Direct file uploads
- Share links
"""
import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.db import get_db
from src.models.training_sample import TrainingSample, TrainingSampleSource
from src.voice_training.youtube_extractor import YouTubeExtractor
from src.voice_training.drive_extractor import DriveExtractor
from src.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/voice/training", tags=["voice", "training"])


# ===========================
# Request/Response Models
# ===========================

class IngestRequest(BaseModel):
    """Request to ingest training sample from URL or link."""
    source_type: TrainingSampleSource
    source_url: HttpUrl
    user_id: UUID
    title: Optional[str] = None


class TrainingSampleResponse(BaseModel):
    """Response model for training sample."""
    id: UUID
    user_id: UUID
    source_type: str
    source_id: Optional[str]
    source_url: Optional[str]
    title: Optional[str]
    content_preview: str
    content_length: int
    extracted_at: datetime
    embedding_generated: bool
    created_at: datetime


class IngestStats(BaseModel):
    """Statistics about training samples."""
    total_samples: int
    by_source: dict
    total_content_length: int
    embedding_coverage: float


# ===========================
# Endpoints
# ===========================

@router.post("/ingest/url", response_model=TrainingSampleResponse, status_code=status.HTTP_201_CREATED)
async def ingest_from_url(
    request: IngestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest training sample from URL (YouTube, Drive share link, etc.).
    
    Supported sources:
    - YouTube videos (extracts transcript)
    - Google Drive share links (future)
    - HubSpot record links (future)
    """
    try:
        url_str = str(request.source_url)
        
        # Route to appropriate extractor based on source_type
        if request.source_type == TrainingSampleSource.YOUTUBE:
            if "youtube.com" not in url_str and "youtu.be" not in url_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid YouTube URL"
                )
            
            extraction = await YouTubeExtractor.extract(url_str)
            
        elif request.source_type == TrainingSampleSource.DRIVE:
            # Extract Google Drive file
            # Get user's Google credentials
            try:
                from src.auth.google_oauth import GoogleOAuthManager
                oauth_manager = GoogleOAuthManager()
                credentials = await oauth_manager.get_user_credentials(request.user_id)
                
                if not credentials:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Google Drive access not authorized. Please connect your Google account."
                    )
                
                extractor = DriveExtractor(credentials)
                extraction = await extractor.extract(file_id=None, file_url=url_str)
                
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Google Drive integration not available"
                )
            
        else:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Source type {request.source_type} not yet implemented"
            )
        
        # Create training sample record
        sample = TrainingSample(
            id=uuid4(),
            user_id=request.user_id,
            source_type=request.source_type.value,
            source_id=extraction["source_id"],
            source_url=url_str,
            title=request.title or extraction["title"],
            content=extraction["content"],
            extracted_at=datetime.utcnow(),
            embedding_generated=False,
            source_metadata=extraction.get("metadata", {})
        )
        
        db.add(sample)
        await db.commit()
        await db.refresh(sample)
        
        logger.info(f"Ingested training sample {sample.id} from {request.source_type}: {sample.title}")
        
        return TrainingSampleResponse(**sample.to_dict())
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to ingest training sample from {request.source_url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.post("/ingest/upload", response_model=TrainingSampleResponse, status_code=status.HTTP_201_CREATED)
async def ingest_from_upload(
    file: UploadFile = File(...),
    user_id: UUID = Form(...),
    title: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest training sample from direct file upload.
    
    Supported file types:
    - TXT
    - PDF (future)
    - DOCX (future)
    """
    try:
        # Read file content
        content_bytes = await file.read()
        
        # Basic text extraction (enhance later with PDF/DOCX support)
        if file.content_type == "text/plain" or file.filename.endswith(".txt"):
            content = content_bytes.decode('utf-8')
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file.content_type}. Currently only .txt files supported."
            )
        
        # Create training sample
        sample = TrainingSample(
            id=uuid4(),
            user_id=user_id,
            source_type=TrainingSampleSource.UPLOAD.value,
            source_id=None,
            source_url=None,
            title=title or file.filename,
            content=content,
            extracted_at=datetime.utcnow(),
            embedding_generated=False,
            source_metadata={
                "filename": file.filename,
                "content_type": file.content_type,
                "file_size": len(content_bytes)
            }
        )
        
        db.add(sample)
        await db.commit()
        await db.refresh(sample)
        
        logger.info(f"Uploaded training sample {sample.id}: {sample.title}")
        
        return TrainingSampleResponse(**sample.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload training sample: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/samples", response_model=List[TrainingSampleResponse])
async def list_training_samples(
    user_id: UUID,
    source_type: Optional[TrainingSampleSource] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all training samples for a user."""
    try:
        query = select(TrainingSample).where(TrainingSample.user_id == user_id)
        
        if source_type:
            query = query.where(TrainingSample.source_type == source_type.value)
        
        query = query.order_by(TrainingSample.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        samples = result.scalars().all()
        
        return [TrainingSampleResponse(**s.to_dict()) for s in samples]
        
    except Exception as e:
        logger.error(f"Failed to list training samples: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve training samples"
        )


@router.get("/stats", response_model=IngestStats)
async def get_training_stats(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get statistics about user's training samples."""
    try:
        # Total count
        count_query = select(func.count(TrainingSample.id)).where(TrainingSample.user_id == user_id)
        total_result = await db.execute(count_query)
        total_samples = total_result.scalar()
        
        # By source type
        by_source_query = (
            select(TrainingSample.source_type, func.count(TrainingSample.id))
            .where(TrainingSample.user_id == user_id)
            .group_by(TrainingSample.source_type)
        )
        by_source_result = await db.execute(by_source_query)
        by_source = {row[0]: row[1] for row in by_source_result.fetchall()}
        
        # Total content length
        length_query = select(func.sum(func.length(TrainingSample.content))).where(TrainingSample.user_id == user_id)
        length_result = await db.execute(length_query)
        total_content_length = length_result.scalar() or 0
        
        # Embedding coverage
        embedded_query = (
            select(func.count(TrainingSample.id))
            .where(TrainingSample.user_id == user_id, TrainingSample.embedding_generated == True)
        )
        embedded_result = await db.execute(embedded_query)
        embedded_count = embedded_result.scalar()
        embedding_coverage = embedded_count / total_samples if total_samples > 0 else 0.0
        
        return IngestStats(
            total_samples=total_samples,
            by_source=by_source,
            total_content_length=total_content_length,
            embedding_coverage=embedding_coverage
        )
        
    except Exception as e:
        logger.error(f"Failed to get training stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.delete("/samples/{sample_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_sample(
    sample_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a training sample."""
    try:
        query = select(TrainingSample).where(
            TrainingSample.id == sample_id,
            TrainingSample.user_id == user_id
        )
        result = await db.execute(query)
        sample = result.scalar_one_or_none()
        
        if not sample:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Training sample not found"
            )
        
        await db.delete(sample)
        await db.commit()
        
        logger.info(f"Deleted training sample {sample_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete training sample {sample_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete training sample"
        )
