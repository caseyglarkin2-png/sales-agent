"""
Analytics and insights engine.

Provides business intelligence dashboards and metrics:
- Workflow performance (conversion rates, timing)
- Email engagement (opens, clicks, replies)
- Agent performance (TriggerAgent scoring accuracy)
- System health (error rates, throughput)
- Trend analysis
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.sql import text

from src.models.workflow import Workflow, WorkflowStatus, WorkflowMode
from src.models.form_submission import FormSubmission
from src.logger import get_logger

logger = get_logger(__name__)


class TimeWindow(str, Enum):
    """Time windows for analytics."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    ALL_TIME = "all_time"


class AnalyticsEngine:
    """
    Business intelligence and analytics engine.
    
    Generates insights from workflow execution data.
    """
    
    def __init__(self, db_session: AsyncSession):
        """Initialize analytics engine."""
        self.db = db_session
    
    async def get_workflow_metrics(
        self,
        time_window: TimeWindow = TimeWindow.DAY
    ) -> Dict[str, Any]:
        """
        Get workflow execution metrics.
        
        Returns:
            {
                "total_workflows": int,
                "completed": int,
                "failed": int,
                "processing": int,
                "completion_rate": float,
                "avg_duration_seconds": float,
                "throughput_per_hour": float
            }
        """
        cutoff_time = self._get_cutoff_time(time_window)
        
        # Count by status
        status_query = select(
            Workflow.status,
            func.count(Workflow.id).label('count')
        ).where(Workflow.created_at >= cutoff_time).group_by(Workflow.status)
        
        status_result = await self.db.execute(status_query)
        status_counts = {row[0]: row[1] for row in status_result}
        
        total = sum(status_counts.values())
        completed = status_counts.get(WorkflowStatus.COMPLETED, 0)
        failed = status_counts.get(WorkflowStatus.FAILED, 0)
        processing = status_counts.get(WorkflowStatus.PROCESSING, 0)
        
        # Completion rate
        completion_rate = (completed / total * 100) if total > 0 else 0.0
        
        # Average duration for completed workflows
        duration_query = select(
            func.avg(
                func.extract('epoch', Workflow.completed_at - Workflow.started_at)
            ).label('avg_duration')
        ).where(
            and_(
                Workflow.status == WorkflowStatus.COMPLETED.value,
                Workflow.created_at >= cutoff_time,
                Workflow.completed_at.isnot(None)
            )
        )
        
        duration_result = await self.db.execute(duration_query)
        avg_duration = duration_result.scalar() or 0.0
        
        # Throughput (workflows per hour)
        hours_in_window = self._get_hours_in_window(time_window)
        throughput = total / hours_in_window if hours_in_window > 0 else 0.0
        
        return {
            "total_workflows": total,
            "completed": completed,
            "failed": failed,
            "processing": processing,
            "completion_rate": round(completion_rate, 2),
            "avg_duration_seconds": round(avg_duration, 2),
            "throughput_per_hour": round(throughput, 2),
            "time_window": time_window.value,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_mode_distribution(
        self,
        time_window: TimeWindow = TimeWindow.DAY
    ) -> Dict[str, Any]:
        """
        Get distribution of DRAFT_ONLY vs SEND mode.
        
        Important for monitoring production readiness.
        """
        cutoff_time = self._get_cutoff_time(time_window)
        
        mode_query = select(
            Workflow.mode,
            func.count(Workflow.id).label('count')
        ).where(Workflow.created_at >= cutoff_time).group_by(Workflow.mode)
        
        mode_result = await self.db.execute(mode_query)
        mode_counts = {row[0]: row[1] for row in mode_result}
        
        total = sum(mode_counts.values())
        draft_only = mode_counts.get(WorkflowMode.DRAFT_ONLY, 0)
        send = mode_counts.get(WorkflowMode.SEND, 0)
        
        return {
            "total": total,
            "draft_only": draft_only,
            "send": send,
            "draft_only_pct": round(draft_only / total * 100, 2) if total > 0 else 0,
            "send_pct": round(send / total * 100, 2) if total > 0 else 0,
            "time_window": time_window.value
        }
    
    async def get_error_analysis(
        self,
        time_window: TimeWindow = TimeWindow.DAY,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze error patterns.
        
        Returns top errors, error rate trends, retry statistics.
        """
        cutoff_time = self._get_cutoff_time(time_window)
        
        # Error rate
        total_query = select(func.count(Workflow.id)).where(
            Workflow.created_at >= cutoff_time
        )
        total = (await self.db.execute(total_query)).scalar() or 0
        
        failed_query = select(func.count(Workflow.id)).where(
            and_(
                Workflow.created_at >= cutoff_time,
                Workflow.status == WorkflowStatus.FAILED.value
            )
        )
        failed = (await self.db.execute(failed_query)).scalar() or 0
        
        error_rate = (failed / total * 100) if total > 0 else 0.0
        
        # Top error messages
        error_query = select(
            Workflow.error_message,
            func.count(Workflow.id).label('count')
        ).where(
            and_(
                Workflow.created_at >= cutoff_time,
                Workflow.error_message.isnot(None)
            )
        ).group_by(Workflow.error_message).order_by(text('count DESC')).limit(limit)
        
        error_result = await self.db.execute(error_query)
        top_errors = [
            {"message": row[0], "count": row[1]}
            for row in error_result
        ]
        
        # Retry statistics
        retry_query = select(
            func.avg(Workflow.error_count).label('avg_retries'),
            func.max(Workflow.error_count).label('max_retries')
        ).where(
            and_(
                Workflow.created_at >= cutoff_time,
                Workflow.error_count > 0
            )
        )
        
        retry_result = await self.db.execute(retry_query)
        retry_stats = retry_result.first()
        
        return {
            "total_workflows": total,
            "failed_workflows": failed,
            "error_rate": round(error_rate, 2),
            "top_errors": top_errors,
            "retry_stats": {
                "avg_retries": round(retry_stats[0] or 0, 2),
                "max_retries": retry_stats[1] or 0
            },
            "time_window": time_window.value
        }
    
    async def get_performance_trends(
        self,
        metric: str = "completion_rate",
        granularity: str = "hour",
        points: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get time-series performance trends.
        
        Args:
            metric: Metric to track (completion_rate, throughput, error_rate)
            granularity: hour, day, week
            points: Number of data points
        
        Returns:
            List of {timestamp, value} points
        """
        # Generate time buckets
        now = datetime.utcnow()
        if granularity == "hour":
            delta = timedelta(hours=1)
        elif granularity == "day":
            delta = timedelta(days=1)
        else:
            delta = timedelta(weeks=1)
        
        trend_data = []
        
        for i in range(points):
            start_time = now - delta * (i + 1)
            end_time = now - delta * i
            
            # Get metrics for this bucket
            total_query = select(func.count(Workflow.id)).where(
                and_(
                    Workflow.created_at >= start_time,
                    Workflow.created_at < end_time
                )
            )
            total = (await self.db.execute(total_query)).scalar() or 0
            
            if metric == "completion_rate":
                completed_query = select(func.count(Workflow.id)).where(
                    and_(
                        Workflow.created_at >= start_time,
                        Workflow.created_at < end_time,
                        Workflow.status == WorkflowStatus.COMPLETED.value
                    )
                )
                completed = (await self.db.execute(completed_query)).scalar() or 0
                value = (completed / total * 100) if total > 0 else 0.0
            
            elif metric == "throughput":
                value = total
            
            elif metric == "error_rate":
                failed_query = select(func.count(Workflow.id)).where(
                    and_(
                        Workflow.created_at >= start_time,
                        Workflow.created_at < end_time,
                        Workflow.status == WorkflowStatus.FAILED.value
                    )
                )
                failed = (await self.db.execute(failed_query)).scalar() or 0
                value = (failed / total * 100) if total > 0 else 0.0
            
            else:
                value = 0.0
            
            trend_data.append({
                "timestamp": start_time.isoformat(),
                "value": round(value, 2)
            })
        
        return list(reversed(trend_data))
    
    async def get_comprehensive_dashboard(
        self,
        time_window: TimeWindow = TimeWindow.DAY
    ) -> Dict[str, Any]:
        """
        Get comprehensive dashboard with all key metrics.
        
        One-stop-shop for monitoring system health.
        """
        workflow_metrics = await self.get_workflow_metrics(time_window)
        mode_distribution = await self.get_mode_distribution(time_window)
        error_analysis = await self.get_error_analysis(time_window)
        
        # Hourly trend for last 24 hours
        completion_trend = await self.get_performance_trends(
            metric="completion_rate",
            granularity="hour",
            points=24
        )
        
        return {
            "summary": workflow_metrics,
            "mode_distribution": mode_distribution,
            "errors": error_analysis,
            "trends": {
                "completion_rate_24h": completion_trend
            },
            "generated_at": datetime.utcnow().isoformat(),
            "time_window": time_window.value
        }
    
    def _get_cutoff_time(self, window: TimeWindow) -> datetime:
        """Get cutoff time for time window."""
        now = datetime.utcnow()
        
        if window == TimeWindow.HOUR:
            return now - timedelta(hours=1)
        elif window == TimeWindow.DAY:
            return now - timedelta(days=1)
        elif window == TimeWindow.WEEK:
            return now - timedelta(weeks=1)
        elif window == TimeWindow.MONTH:
            return now - timedelta(days=30)
        else:  # ALL_TIME
            return datetime(2020, 1, 1)
    
    def _get_hours_in_window(self, window: TimeWindow) -> float:
        """Get number of hours in time window."""
        if window == TimeWindow.HOUR:
            return 1.0
        elif window == TimeWindow.DAY:
            return 24.0
        elif window == TimeWindow.WEEK:
            return 168.0
        elif window == TimeWindow.MONTH:
            return 720.0
        else:
            return 8760.0  # 1 year for all-time
