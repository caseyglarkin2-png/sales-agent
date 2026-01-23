"""Admin routes for system controls and emergency operations."""
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auto_approval import seed_default_rules
from src.config import get_settings
from src.db import get_db
from src.logger import get_logger
from src.models.auto_approval import ApprovedRecipient, AutoApprovalRule

logger = get_logger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/admin", tags=["Admin"])


# Emergency kill switch state (in-memory, can be replaced with Redis)
_KILL_SWITCH_ACTIVE = False


class EmergencyStopRequest(BaseModel):
    """Request to activate emergency kill switch."""

    admin_password: str
    reason: str


class EmergencyStopResponse(BaseModel):
    """Response from emergency stop."""

    status: str
    message: str
    auto_approve_disabled: bool


@router.post("/emergency-stop", response_model=EmergencyStopResponse)
async def emergency_stop(request: EmergencyStopRequest) -> EmergencyStopResponse:
    """
    Emergency kill switch - disable all auto-approval immediately.

    Requires admin password for security. Sets AUTO_APPROVE_ENABLED=false globally,
    forcing all drafts to go through manual operator review.

    Use when:
    - Bad rule is auto-approving incorrectly
    - System is sending problematic emails
    - Need immediate control

    Args:
        request: Emergency stop request with admin password and reason

    Returns:
        Response indicating kill switch status

    Raises:
        HTTPException: If admin password is incorrect

    Example:
        POST /api/admin/emergency-stop
        {
            "admin_password": "secret123",
            "reason": "Bad rule approving spam emails"
        }
    """
    # Verify admin password
    expected_password = os.getenv("ADMIN_PASSWORD", "change_me_in_production")
    if request.admin_password != expected_password:
        logger.warning("Failed emergency stop attempt - invalid password")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin password",
        )

    global _KILL_SWITCH_ACTIVE
    _KILL_SWITCH_ACTIVE = True

    # Update settings (this is in-memory - in production use Redis/DB)
    settings.auto_approve_enabled = False

    logger.critical(
        "EMERGENCY STOP ACTIVATED - Auto-approval disabled",
        reason=request.reason,
    )

    # TODO: Send email/Slack alert to operations team
    # await send_alert(
    #     subject="EMERGENCY: Auto-Approval Disabled",
    #     message=f"Emergency stop activated. Reason: {request.reason}",
    #     severity="critical"
    # )

    return EmergencyStopResponse(
        status="emergency_stop_active",
        message=f"Auto-approval disabled. Reason: {request.reason}. All drafts will require manual review.",
        auto_approve_disabled=True,
    )


@router.post("/emergency-resume")
async def emergency_resume(admin_password: str = Query(...)) -> Dict[str, Any]:
    """
    Resume auto-approval after emergency stop.

    Args:
        admin_password: Admin password for verification

    Returns:
        Response indicating resume status

    Raises:
        HTTPException: If admin password is incorrect
    """
    # Verify admin password
    expected_password = os.getenv("ADMIN_PASSWORD", "change_me_in_production")
    if admin_password != expected_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin password",
        )

    global _KILL_SWITCH_ACTIVE
    _KILL_SWITCH_ACTIVE = False

    settings.auto_approve_enabled = True

    logger.warning("Emergency stop deactivated - Auto-approval re-enabled")

    return {
        "status": "resumed",
        "message": "Auto-approval re-enabled. System operating normally.",
        "auto_approve_enabled": True,
    }


@router.get("/emergency-status")
async def get_emergency_status() -> Dict[str, Any]:
    """
    Get current emergency kill switch status.

    Returns:
        Current status of emergency controls
    """
    return {
        "kill_switch_active": _KILL_SWITCH_ACTIVE,
        "auto_approve_enabled": getattr(settings, "auto_approve_enabled", True),
        "allow_real_sends": settings.allow_real_sends,
    }


# Auto-Approval Rule Management

@router.get("/rules")
async def list_rules() -> Dict[str, Any]:
    """
    List all auto-approval rules.

    Returns:
        List of rules with configuration
    """
    async with get_db() as session:
        result = await session.execute(
            select(AutoApprovalRule).order_by(AutoApprovalRule.priority.asc())
        )
        rules = result.scalars().all()

        return {
            "total_count": len(rules),
            "rules": [
                {
                    "id": rule.id,
                    "rule_type": rule.rule_type,
                    "name": rule.name,
                    "description": rule.description,
                    "conditions": rule.conditions,
                    "confidence": rule.confidence,
                    "enabled": rule.enabled,
                    "priority": rule.priority,
                    "created_by": rule.created_by,
                }
                for rule in rules
            ],
        }


@router.post("/rules/{rule_id}/enable")
async def enable_rule(rule_id: str) -> Dict[str, Any]:
    """
    Enable an auto-approval rule.

    Args:
        rule_id: Rule identifier

    Returns:
        Updated rule status
    """
    async with get_db() as session:
        result = await session.execute(
            select(AutoApprovalRule).where(AutoApprovalRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found",
            )

        rule.enabled = True
        await session.commit()

        logger.info(f"Enabled auto-approval rule", rule_id=rule_id, rule_type=rule.rule_type)

        return {"status": "enabled", "rule_id": rule_id, "rule_type": rule.rule_type}


@router.post("/rules/{rule_id}/disable")
async def disable_rule(rule_id: str) -> Dict[str, Any]:
    """
    Disable an auto-approval rule.

    Args:
        rule_id: Rule identifier

    Returns:
        Updated rule status
    """
    async with get_db() as session:
        result = await session.execute(
            select(AutoApprovalRule).where(AutoApprovalRule.id == rule_id)
        )
        rule = result.scalar_one_or_none()

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found",
            )

        rule.enabled = False
        await session.commit()

        logger.info(f"Disabled auto-approval rule", rule_id=rule_id, rule_type=rule.rule_type)

        return {"status": "disabled", "rule_id": rule_id, "rule_type": rule.rule_type}


@router.post("/rules/seed")
async def seed_rules() -> Dict[str, Any]:
    """
    Seed default auto-approval rules.

    Creates 3 standard rules if none exist.

    Returns:
        Seed operation status
    """
    async with get_db() as session:
        await seed_default_rules(session)

        return {"status": "success", "message": "Default rules seeded (if none existed)"}


# Approved Recipient Whitelist Management

@router.get("/approved-recipients")
async def list_approved_recipients(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    List approved recipients whitelist.

    Args:
        limit: Number of results (1-500, default 50)
        offset: Results to skip (default 0)

    Returns:
        Paginated list of approved recipients
    """
    async with get_db() as session:
        # Get total count
        count_result = await session.execute(select(func.count(ApprovedRecipient.id)))
        total_count = count_result.scalar() or 0

        # Get paginated results
        result = await session.execute(
            select(ApprovedRecipient)
            .order_by(ApprovedRecipient.last_sent_at.desc())
            .limit(limit)
            .offset(offset)
        )
        recipients = result.scalars().all()

        return {
            "total_count": total_count,
            "returned_count": len(recipients),
            "limit": limit,
            "offset": offset,
            "recipients": [
                {
                    "id": r.id,
                    "email": r.email,
                    "domain": r.domain,
                    "total_sends": r.total_sends,
                    "total_replies": r.total_replies,
                    "first_approved_at": r.first_approved_at.isoformat(),
                    "last_sent_at": r.last_sent_at.isoformat() if r.last_sent_at else None,
                }
                for r in recipients
            ],
        }


@router.delete("/approved-recipients/{recipient_id}")
async def remove_approved_recipient(recipient_id: str) -> Dict[str, Any]:
    """
    Remove recipient from approved whitelist.

    Args:
        recipient_id: Recipient identifier

    Returns:
        Removal status
    """
    async with get_db() as session:
        result = await session.execute(
            select(ApprovedRecipient).where(ApprovedRecipient.id == recipient_id)
        )
        recipient = result.scalar_one_or_none()

        if not recipient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recipient {recipient_id} not found",
            )

        email = recipient.email
        await session.delete(recipient)
        await session.commit()

        logger.info(f"Removed recipient from whitelist", email=email)

        return {"status": "removed", "email": email}


# Import after definitions to avoid circular imports
from sqlalchemy import func
