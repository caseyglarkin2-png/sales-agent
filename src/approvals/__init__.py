"""Approvals module for workflow approval management."""

from .approval_service import (
    ApprovalService,
    ApprovalRequest,
    ApprovalRule,
    ApprovalChain,
    ApprovalStatus,
    get_approval_service,
)
