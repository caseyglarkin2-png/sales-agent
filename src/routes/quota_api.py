"""
Rate limiting and quota management API endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from src.rate_limiter_enhanced import TokenBucketRateLimiter, QuotaManager, RateLimitService
from src.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/quotas", tags=["quotas", "rate-limits"])

# Global instances (should be injected via dependency in production)
rate_limiter = TokenBucketRateLimiter()
quota_manager = QuotaManager()


class QuotaStatusRequest(BaseModel):
    """Request for quota status."""
    user_id: str
    service: Optional[str] = None


@router.get("/rate-limits/{service}")
async def get_rate_limit_status(
    service: str,
    user_id: Optional[str] = None
):
    """
    Get current rate limit status for a service.
    
    Returns token availability, capacity, and utilization.
    """
    try:
        service_enum = RateLimitService(service)
        status = await rate_limiter.get_quota_status(service_enum, user_id)
        
        return {
            "service": service,
            "user_id": user_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid service: {service}. Valid: {[s.value for s in RateLimitService]}"
        )
    except Exception as e:
        logger.error(f"Failed to get rate limit status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rate limit status: {str(e)}"
        )


@router.get("/usage/{user_id}/{quota_type}")
async def get_quota_usage(
    user_id: str,
    quota_type: str,
    period: str = "daily"
):
    """
    Get quota usage for user.
    
    Args:
        user_id: User/tenant ID
        quota_type: Type of quota (emails_sent, api_calls, etc.)
        period: daily, weekly, monthly
    
    Returns usage statistics.
    """
    try:
        usage = await quota_manager.get_usage(user_id, quota_type, period)
        
        return {
            "user_id": user_id,
            "quota_type": quota_type,
            **usage
        }
        
    except Exception as e:
        logger.error(f"Failed to get quota usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quota usage: {str(e)}"
        )


@router.get("/dashboard/{user_id}")
async def get_quota_dashboard(user_id: str):
    """
    Get comprehensive quota and rate limit dashboard for user.
    
    Returns all services and quota types.
    """
    try:
        dashboard = {
            "user_id": user_id,
            "rate_limits": {},
            "quotas": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Get rate limits for all services
        for service in RateLimitService:
            try:
                status_data = await rate_limiter.get_quota_status(service, user_id)
                dashboard["rate_limits"][service.value] = status_data
            except Exception as e:
                logger.warning(f"Failed to get {service} rate limit: {e}")
                dashboard["rate_limits"][service.value] = {"error": str(e)}
        
        # Get common quota types
        quota_types = ["emails_sent", "workflows_triggered", "api_calls"]
        for quota_type in quota_types:
            try:
                for period in ["daily", "weekly", "monthly"]:
                    usage = await quota_manager.get_usage(user_id, quota_type, period)
                    
                    if quota_type not in dashboard["quotas"]:
                        dashboard["quotas"][quota_type] = {}
                    dashboard["quotas"][quota_type][period] = usage
            except Exception as e:
                logger.warning(f"Failed to get {quota_type} quota: {e}")
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Failed to generate quota dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quota dashboard: {str(e)}"
        )
