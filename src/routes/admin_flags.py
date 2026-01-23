"""
Admin endpoints for feature flag management.

Provides kill switch and observability for production safety.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from src.feature_flags import get_flag_manager, OperationMode
from src.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/admin/flags", tags=["admin", "flags"])


class SendModeToggleRequest(BaseModel):
    """Request to enable/disable SEND mode."""
    operator: str
    reason: str


class SendModeStatusResponse(BaseModel):
    """Current SEND mode status."""
    mode: OperationMode
    send_enabled: bool
    circuit_breaker_status: dict
    mode_history: list[dict]


@router.get("/send-mode", response_model=SendModeStatusResponse)
async def get_send_mode_status():
    """
    Get current SEND mode status and history.
    
    Returns current mode, circuit breaker state, and audit trail.
    """
    flag_manager = get_flag_manager()
    
    return SendModeStatusResponse(
        mode=flag_manager.get_operation_mode(),
        send_enabled=flag_manager.is_send_mode_enabled(),
        circuit_breaker_status=flag_manager.get_circuit_breaker_status(),
        mode_history=flag_manager.get_mode_history()
    )


@router.post("/send-mode/disable")
async def disable_send_mode(request: SendModeToggleRequest):
    """
    🚨 KILL SWITCH: Disable SEND mode immediately.
    
    Use this endpoint in emergencies to stop all automatic email sends.
    Does not require application restart.
    
    Args:
        request: Must include operator name and reason
        
    Returns:
        Confirmation with timestamp and audit record
    """
    flag_manager = get_flag_manager()
    
    try:
        change_record = flag_manager.disable_send_mode(
            operator=request.operator,
            reason=request.reason
        )
        
        logger.critical(
            f"🚨 SEND MODE DISABLED via kill switch",
            extra={
                "operator": request.operator,
                "reason": request.reason,
                "timestamp": change_record["timestamp"]
            }
        )
        
        return {
            "status": "success",
            "message": "SEND mode disabled immediately",
            "change_record": change_record
        }
        
    except Exception as e:
        logger.error(f"Failed to disable SEND mode: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kill switch failed: {str(e)}"
        )


@router.post("/send-mode/enable")
async def enable_send_mode(request: SendModeToggleRequest):
    """
    Enable SEND mode (requires production environment).
    
    Args:
        request: Must include operator name and reason
        
    Returns:
        Confirmation with timestamp
        
    Raises:
        403: If environment is not production
        500: If validation fails
    """
    flag_manager = get_flag_manager()
    
    try:
        change_record = flag_manager.enable_send_mode(
            operator=request.operator,
            reason=request.reason
        )
        
        logger.warning(
            f"⚠️  SEND MODE ENABLED",
            extra={
                "operator": request.operator,
                "reason": request.reason,
                "timestamp": change_record["timestamp"]
            }
        )
        
        return {
            "status": "success",
            "message": "SEND mode enabled - emails will be sent automatically",
            "warning": "Use /disable endpoint for emergency shutoff",
            "change_record": change_record
        }
        
    except Exception as e:
        logger.error(f"Failed to enable SEND mode: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot enable SEND mode: {str(e)}"
        )


@router.get("/circuit-breaker")
async def get_circuit_breaker_status():
    """
    Get circuit breaker status and metrics.
    
    Returns current error rate, threshold, and recent send stats.
    """
    flag_manager = get_flag_manager()
    
    return {
        "circuit_breaker": flag_manager.get_circuit_breaker_status(),
        "description": "Circuit breaker automatically disables SEND mode if error rate exceeds threshold"
    }
