"""Action execution system for CaseyOS.

This module provides the infrastructure for executing actions from the Command Queue
with safety guardrails including:
- Kill switch integration
- Rate limiting
- Dry-run mode
- Idempotency
- Audit trail
"""
from src.actions.executor import ActionExecutor, ActionResult
from src.actions.contracts import ActionRequest, ActionType

__all__ = ["ActionExecutor", "ActionResult", "ActionRequest", "ActionType"]
