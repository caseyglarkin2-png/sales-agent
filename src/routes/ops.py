"""Operational endpoints (admin-only)."""

from fastapi import APIRouter, Depends

from src.security.auth import require_admin_role

router = APIRouter(prefix="/api", tags=["Ops"], dependencies=[Depends(require_admin_role)])


@router.post("/test-error")
async def trigger_test_error() -> dict:
    """Trigger a test exception to verify Sentry wiring (admin-only)."""
    raise RuntimeError("Sentry test error: manual trigger")
