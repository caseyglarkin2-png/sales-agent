"""
API endpoint to queue morning emails for approval.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import asyncio

from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/queue", tags=["queue"])


@router.post("/morning-emails")
async def queue_morning_emails() -> Dict[str, Any]:
    """
    Queue personalized emails for tomorrow morning approval.
    
    Generates drafts using:
    - Casey's voice training
    - Sender: casey.l@pesti.io
    - Queued for operator approval
    """
    try:
        # Import here to avoid circular dependencies
        import subprocess
        import sys
        
        logger.info("🚢 Starting morning email generation...")
        
        # Run the queue script
        result = subprocess.run(
            [sys.executable, "queue_morning_emails.py"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "message": "Morning emails queued successfully",
                "output": result.stdout,
                "drafts_location": "/api/operator/drafts"
            }
        else:
            logger.error(f"Queue script failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to queue emails: {result.stderr}"
            )
            
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Email generation timed out"
        )
    except Exception as e:
        logger.error(f"Failed to queue morning emails: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.get("/status")
async def queue_status() -> Dict[str, Any]:
    """Get queue status."""
    try:
        from src.operator_mode import get_draft_queue
        
        queue = get_draft_queue()
        drafts = await queue.get_pending_drafts()
        
        morning_drafts = [
            d for d in drafts 
            if d.get("metadata", {}).get("ready_for_morning_approval")
        ]
        
        return {
            "total_pending": len(drafts),
            "morning_drafts": len(morning_drafts),
            "sender": "casey.l@pesti.io",
            "ready": len(morning_drafts) > 0
        }
        
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
