"""API routes for email deliverability."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from src.deliverability import get_deliverability_optimizer

router = APIRouter(prefix="/api/deliverability", tags=["deliverability"])


class CheckSpamRequest(BaseModel):
    subject: str
    body: str
    from_name: str = ""


class OptimizeContentRequest(BaseModel):
    subject: str
    body: str


class ScoreRequest(BaseModel):
    subject: str
    body: str
    from_domain: str


@router.post("/spam-check")
async def check_spam_score(request: CheckSpamRequest):
    """Check email content for spam triggers."""
    optimizer = get_deliverability_optimizer()
    
    result = optimizer.check_spam_score(
        subject=request.subject,
        body=request.body,
        from_name=request.from_name,
    )
    
    return result.to_dict()


@router.post("/optimize")
async def optimize_content(request: OptimizeContentRequest):
    """Get content optimization suggestions."""
    optimizer = get_deliverability_optimizer()
    
    return optimizer.optimize_content(
        subject=request.subject,
        body=request.body,
    )


@router.post("/score")
async def get_deliverability_score(request: ScoreRequest):
    """Get overall deliverability score for an email."""
    optimizer = get_deliverability_optimizer()
    
    score = optimizer.get_deliverability_score(
        subject=request.subject,
        body=request.body,
        from_domain=request.from_domain,
    )
    
    return score.to_dict()


@router.get("/warmup/{domain}")
async def get_warmup_status(domain: str):
    """Get warmup status for a domain."""
    optimizer = get_deliverability_optimizer()
    status = optimizer.get_warmup_status(domain)
    
    return status.to_dict()


@router.post("/warmup/{domain}/start")
async def start_warmup(domain: str, target_daily_limit: int = 200):
    """Start warming up a domain."""
    optimizer = get_deliverability_optimizer()
    status = optimizer.start_warmup(domain, target_daily_limit)
    
    return {
        "message": "Warmup started",
        "status": status.to_dict(),
    }


@router.post("/warmup/{domain}/record-send")
async def record_email_sent(
    domain: str,
    bounced: bool = False,
    spam_complaint: bool = False,
):
    """Record an email sent for warmup tracking."""
    optimizer = get_deliverability_optimizer()
    
    status = optimizer.record_email_sent(
        domain=domain,
        bounced=bounced,
        spam_complaint=spam_complaint,
    )
    
    return {
        "message": "Email recorded",
        "can_send_more": status.can_send_more(),
        "status": status.to_dict(),
    }


@router.get("/domain/{domain}")
async def check_domain_health(domain: str):
    """Check health of a sending domain."""
    optimizer = get_deliverability_optimizer()
    health = optimizer.check_domain_health(domain)
    
    return health.to_dict()


@router.post("/reset-daily")
async def reset_daily_counts():
    """Reset daily email counts (for testing)."""
    optimizer = get_deliverability_optimizer()
    count = optimizer.reset_daily_counts()
    
    return {
        "message": f"Reset {count} domain(s)",
    }
