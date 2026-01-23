"""
Analytics API endpoints.

Provides business intelligence dashboards and metrics.
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional

from src.db import get_db
from src.analytics_engine import AnalyticsEngine, TimeWindow
from src.workflow_state_machine import WorkflowRecovery
from src.logger import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics", "insights"])


@router.get("/metrics")
async def get_workflow_metrics(
    time_window: str = Query(default="day", regex="^(hour|day|week|month|all_time)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get workflow execution metrics.
    
    Returns completion rate, throughput, average duration, etc.
    """
    try:
        engine = AnalyticsEngine(db)
        window = TimeWindow(time_window)
        metrics = await engine.get_workflow_metrics(window)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get workflow metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.get("/mode-distribution")
async def get_mode_distribution(
    time_window: str = Query(default="day", regex="^(hour|day|week|month|all_time)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get distribution of DRAFT_ONLY vs SEND mode workflows.
    
    Important for monitoring production readiness.
    """
    try:
        engine = AnalyticsEngine(db)
        window = TimeWindow(time_window)
        distribution = await engine.get_mode_distribution(window)
        
        return distribution
        
    except Exception as e:
        logger.error(f"Failed to get mode distribution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get distribution: {str(e)}"
        )


@router.get("/errors")
async def get_error_analysis(
    time_window: str = Query(default="day", regex="^(hour|day|week|month|all_time)$"),
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze error patterns.
    
    Returns error rate, top errors, retry statistics.
    """
    try:
        engine = AnalyticsEngine(db)
        window = TimeWindow(time_window)
        analysis = await engine.get_error_analysis(window, limit)
        
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to get error analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze errors: {str(e)}"
        )


@router.get("/trends/{metric}")
async def get_performance_trends(
    metric: str,
    granularity: str = Query(default="hour", regex="^(hour|day|week)$"),
    points: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    """
    Get time-series performance trends.
    
    Args:
        metric: completion_rate, throughput, or error_rate
        granularity: hour, day, or week
        points: Number of data points (max 168 for week-long hourly data)
    
    Returns time-series data.
    """
    try:
        valid_metrics = ["completion_rate", "throughput", "error_rate"]
        if metric not in valid_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metric. Valid: {valid_metrics}"
            )
        
        engine = AnalyticsEngine(db)
        trends = await engine.get_performance_trends(metric, granularity, points)
        
        return {
            "metric": metric,
            "granularity": granularity,
            "data": trends
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trends: {str(e)}"
        )


@router.get("/dashboard")
async def get_comprehensive_dashboard(
    time_window: str = Query(default="day", regex="^(hour|day|week|month|all_time)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive analytics dashboard.
    
    One-stop-shop for all key metrics, trends, and insights.
    """
    try:
        engine = AnalyticsEngine(db)
        window = TimeWindow(time_window)
        dashboard = await engine.get_comprehensive_dashboard(window)
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Failed to get dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate dashboard: {str(e)}"
        )


@router.get("/recovery/stats")
async def get_recovery_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get workflow recovery statistics.
    
    Shows stuck workflows, eligible for retry, etc.
    """
    try:
        recovery = WorkflowRecovery(db)
        stats = await recovery.get_recovery_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get recovery stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recovery stats: {str(e)}"
        )


@router.post("/recovery/auto-recover")
async def auto_recover_workflows(
    timeout_minutes: int = Query(default=10, ge=1, le=60),
    max_to_recover: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Automatically recover stuck workflows.
    
    Marks stuck workflows as FAILED so they can be retried.
    """
    try:
        recovery = WorkflowRecovery(db)
        recovered = await recovery.auto_recover_stuck_workflows(
            timeout_minutes=timeout_minutes,
            max_to_recover=max_to_recover
        )
        
        return {
            "recovered": recovered,
            "timeout_minutes": timeout_minutes,
            "max_to_recover": max_to_recover
        }
        
    except Exception as e:
        logger.error(f"Failed to auto-recover workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to auto-recover: {str(e)}"
        )


@router.post("/recovery/retry-failed")
async def retry_failed_workflows(
    max_retries: int = Query(default=3, ge=1, le=10),
    max_to_retry: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Retry failed workflows that are eligible.
    
    Only retries workflows under the max retry count.
    """
    try:
        recovery = WorkflowRecovery(db)
        retried = await recovery.retry_failed_workflows(
            max_retries=max_retries,
            max_to_retry=max_to_retry
        )
        
        return {
            "retried": retried,
            "max_retries": max_retries,
            "max_to_retry": max_to_retry
        }
        
    except Exception as e:
        logger.error(f"Failed to retry workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry workflows: {str(e)}"
        )
