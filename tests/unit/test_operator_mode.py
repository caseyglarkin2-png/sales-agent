"""Tests for operator mode."""
import pytest

from src.operator_mode import DraftQueue, DraftStatus


@pytest.mark.asyncio
async def test_draft_queue_create_draft():
    """Test creating a draft."""
    queue = DraftQueue(approval_required=True)
    
    draft = await queue.create_draft(
        "draft-123",
        "prospect@example.com",
        "Follow-up",
        "Hi, just checking in on our previous conversation. Would you be available for a quick call next week?"
    )
    
    assert draft["id"] == "draft-123"
    assert draft["status"] == DraftStatus.PENDING_APPROVAL


@pytest.mark.asyncio
async def test_draft_queue_approve():
    """Test approving a draft."""
    queue = DraftQueue(approval_required=True)
    
    await queue.create_draft(
        "draft-123",
        "prospect@example.com",
        "Follow-up",
        "Hi, just checking in on our previous conversation. Would you be available for a quick call?"
    )
    
    approved = await queue.approve_draft("draft-123", "operator@company.com")
    assert approved is True
    
    draft = await queue.get_draft("draft-123")
    assert draft["status"] == DraftStatus.APPROVED
    assert draft["approved_by"] == "operator@company.com"


@pytest.mark.asyncio
async def test_draft_queue_reject():
    """Test rejecting a draft."""
    queue = DraftQueue(approval_required=True)
    
    await queue.create_draft(
        "draft-123",
        "prospect@example.com",
        "Subject",
        "Body text here that is long enough to pass validation."
    )
    
    rejected = await queue.reject_draft(
        "draft-123",
        "Too generic - needs more personalization",
        "operator@company.com"
    )
    assert rejected is True
    
    draft = await queue.get_draft("draft-123")
    assert draft["status"] == DraftStatus.REJECTED
    assert draft["rejected_reason"] == "Too generic - needs more personalization"


@pytest.mark.asyncio
async def test_draft_queue_pending_approvals():
    """Test getting pending approvals."""
    queue = DraftQueue(approval_required=True)
    
    await queue.create_draft("draft-1", "p1@example.com", "Subject", "Body text that is long enough.")
    await queue.create_draft("draft-2", "p2@example.com", "Subject", "Body text that is long enough.")
    await queue.approve_draft("draft-1", "op@company.com")
    
    pending = await queue.get_pending_approvals()
    assert len(pending) == 1
    assert pending[0]["id"] == "draft-2"


@pytest.mark.asyncio
async def test_draft_queue_auto_approve():
    """Test auto-approval when not required."""
    queue = DraftQueue(approval_required=False)
    
    draft = await queue.create_draft(
        "draft-123",
        "prospect@example.com",
        "Subject",
        "Body text that is long enough for validation."
    )
    
    assert draft["status"] == DraftStatus.APPROVED
