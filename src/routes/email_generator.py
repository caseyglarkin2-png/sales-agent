"""
Email Generator API Routes
==========================
Endpoints for AI-powered email generation.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import structlog

from src.email_generator import (
    get_email_generator,
    EmailType,
    EmailTone,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/email-generator", tags=["Email Generator"])


class GenerateEmailRequest(BaseModel):
    email_type: str
    context: dict
    tone: str = "professional"
    include_alternatives: bool = True


class GenerateSequenceRequest(BaseModel):
    context: dict
    num_emails: int = 4
    tone: str = "professional"


class RewriteEmailRequest(BaseModel):
    original_body: str
    new_tone: str
    instructions: str = ""


@router.post("/generate")
async def generate_email(request: GenerateEmailRequest):
    """Generate a personalized email."""
    generator = get_email_generator()
    
    try:
        email_type = EmailType(request.email_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid email type: {request.email_type}",
        )
    
    try:
        tone = EmailTone(request.tone)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tone: {request.tone}",
        )
    
    email = generator.generate(
        email_type=email_type,
        context=request.context,
        tone=tone,
        include_alternatives=request.include_alternatives,
    )
    
    return {
        "message": "Email generated",
        "email": email.to_dict(),
    }


@router.post("/sequence")
async def generate_sequence(request: GenerateSequenceRequest):
    """Generate a follow-up email sequence."""
    generator = get_email_generator()
    
    try:
        tone = EmailTone(request.tone)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tone: {request.tone}",
        )
    
    sequence = generator.generate_follow_up_sequence(
        context=request.context,
        num_emails=request.num_emails,
        tone=tone,
    )
    
    return {
        "message": "Sequence generated",
        "emails": [e.to_dict() for e in sequence],
        "count": len(sequence),
    }


@router.post("/rewrite")
async def rewrite_email(request: RewriteEmailRequest):
    """Rewrite an email with a new tone."""
    generator = get_email_generator()
    
    try:
        tone = EmailTone(request.new_tone)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tone: {request.new_tone}",
        )
    
    email = generator.rewrite(
        original_body=request.original_body,
        new_tone=tone,
        instructions=request.instructions,
    )
    
    return {
        "message": "Email rewritten",
        "email": email.to_dict(),
    }


@router.get("/recent")
async def get_recent_emails(limit: int = Query(10, ge=1, le=100)):
    """Get recently generated emails."""
    generator = get_email_generator()
    
    emails = generator.get_recent_emails(limit=limit)
    
    return {
        "emails": [e.to_dict() for e in emails],
        "count": len(emails),
    }


@router.get("/types")
async def list_email_types():
    """List available email types."""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in EmailType
        ]
    }


@router.get("/tones")
async def list_tones():
    """List available email tones."""
    return {
        "tones": [
            {"value": t.value, "name": t.name}
            for t in EmailTone
        ]
    }


@router.post("/analyze")
async def analyze_email(body: str):
    """Analyze an email for spam score and suggestions."""
    generator = get_email_generator()
    
    # Use internal methods to analyze
    spam_score = generator._calculate_spam_score(body)
    word_count = len(body.split())
    
    suggestions = []
    if word_count > 150:
        suggestions.append("Consider shortening the email - ideal length is under 150 words")
    if word_count < 50:
        suggestions.append("Email may be too short - add more value or context")
    if "?" not in body:
        suggestions.append("Add a question to encourage engagement")
    if spam_score > 30:
        suggestions.append("High spam risk - review and remove trigger words")
    
    return {
        "word_count": word_count,
        "reading_time_seconds": max(1, word_count // 3),
        "spam_score": spam_score,
        "spam_risk": "low" if spam_score < 20 else "medium" if spam_score < 50 else "high",
        "suggestions": suggestions,
    }
