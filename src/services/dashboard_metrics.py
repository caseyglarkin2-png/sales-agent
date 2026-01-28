"""
Dashboard Metrics Service.

Aggregates key metrics for dashboard display including:
- Pending actions count
- Completed actions today
- Failed executions today
- Agent activity in last 24h
- Success rates

Sprint 43: Dashboard Intelligence & Metrics
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_execution import AgentExecution, ExecutionStatus
from src.models.command_queue import CommandQueueItem
from src.logger import get_logger

logger = get_logger(__name__)


class DashboardMetricsService:
    """
    Service for aggregating dashboard metrics.
    
    Provides real-time metrics for the dashboard including:
    - Queue statistics (pending, approved, sent)
    - Agent execution statistics
    - Today's activity summary
    """
    
    def __init__(self, db_session: AsyncSession):
        """Initialize with database session."""
        self.db = db_session
    
    async def get_today_metrics(self) -> Dict[str, Any]:
        """
        Get today's key metrics for dashboard.
        
        Returns dict with:
        - pending_actions: Count of items awaiting approval
        - approved_today: Count of items approved today
        - sent_today: Count of items sent today
        - failed_today: Count of failed executions today
        - agent_executions_24h: Total agent runs in last 24h
        - success_rate: Percentage of successful executions
        """
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        
        # Get queue metrics
        queue_metrics = await self._get_queue_metrics(today_start)
        
        # Get execution metrics
        exec_metrics = await self._get_execution_metrics(yesterday)
        
        return {
            **queue_metrics,
            **exec_metrics,
            "as_of": datetime.utcnow().isoformat(),
        }
    
    async def _get_queue_metrics(self, since: datetime) -> Dict[str, int]:
        """Get command queue metrics."""
        # Pending count
        pending_result = await self.db.execute(
            select(func.count(CommandQueueItem.id)).where(
                CommandQueueItem.status == "pending"
            )
        )
        pending_count = pending_result.scalar() or 0
        
        # Approved today
        approved_result = await self.db.execute(
            select(func.count(CommandQueueItem.id)).where(
                and_(
                    CommandQueueItem.status == "approved",
                    CommandQueueItem.updated_at >= since,
                )
            )
        )
        approved_count = approved_result.scalar() or 0
        
        # Sent today
        sent_result = await self.db.execute(
            select(func.count(CommandQueueItem.id)).where(
                and_(
                    CommandQueueItem.status == "sent",
                    CommandQueueItem.updated_at >= since,
                )
            )
        )
        sent_count = sent_result.scalar() or 0
        
        return {
            "pending_actions": pending_count,
            "approved_today": approved_count,
            "sent_today": sent_count,
        }
    
    async def _get_execution_metrics(self, since: datetime) -> Dict[str, Any]:
        """Get agent execution metrics."""
        # Total executions in period
        total_result = await self.db.execute(
            select(func.count(AgentExecution.id)).where(
                AgentExecution.created_at >= since
            )
        )
        total_executions = total_result.scalar() or 0
        
        # Successful executions
        success_result = await self.db.execute(
            select(func.count(AgentExecution.id)).where(
                and_(
                    AgentExecution.created_at >= since,
                    AgentExecution.status == ExecutionStatus.SUCCESS.value,
                )
            )
        )
        success_count = success_result.scalar() or 0
        
        # Failed executions (today only)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        failed_result = await self.db.execute(
            select(func.count(AgentExecution.id)).where(
                and_(
                    AgentExecution.created_at >= today_start,
                    AgentExecution.status == ExecutionStatus.FAILED.value,
                )
            )
        )
        failed_count = failed_result.scalar() or 0
        
        # Running executions
        running_result = await self.db.execute(
            select(func.count(AgentExecution.id)).where(
                AgentExecution.status == ExecutionStatus.RUNNING.value
            )
        )
        running_count = running_result.scalar() or 0
        
        # Calculate success rate
        success_rate = 0.0
        if total_executions > 0:
            success_rate = round((success_count / total_executions) * 100, 1)
        
        return {
            "agent_executions_24h": total_executions,
            "successful_executions": success_count,
            "failed_today": failed_count,
            "running_executions": running_count,
            "success_rate": success_rate,
        }
    
    async def get_top_priority_items(self, limit: int = 5) -> list:
        """
        Get top priority queue items by priority score.
        
        Returns list of items with contact info for quick display.
        """
        result = await self.db.execute(
            select(CommandQueueItem)
            .where(CommandQueueItem.status == "pending")
            .order_by(CommandQueueItem.priority_score.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        
        priority_items = []
        for item in items:
            # Try to get contact name from action_context
            contact_name = None
            if item.action_context and "contact_name" in item.action_context:
                contact_name = item.action_context["contact_name"]
            elif item.action_context and "email" in item.action_context:
                contact_name = item.action_context["email"]
            
            priority_items.append({
                "id": item.id,
                "title": item.title,
                "action_type": item.action_type,
                "priority_score": item.priority_score,
                "contact_name": contact_name or "Unknown",
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })
        
        return priority_items
    
    async def get_agent_performance(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get agent performance summary.
        
        Returns:
        - most_active: Agent with most executions
        - highest_success_rate: Agent with best success rate
        - most_failed: Agent with most failures
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get execution counts by agent
        result = await self.db.execute(
            select(
                AgentExecution.agent_name,
                func.count(AgentExecution.id).label("total"),
                func.sum(
                    case(
                        (AgentExecution.status == ExecutionStatus.SUCCESS.value, 1),
                        else_=0
                    )
                ).label("success_count"),
                func.sum(
                    case(
                        (AgentExecution.status == ExecutionStatus.FAILED.value, 1),
                        else_=0
                    )
                ).label("failed_count"),
            )
            .where(AgentExecution.created_at >= since)
            .group_by(AgentExecution.agent_name)
        )
        rows = result.all()
        
        if not rows:
            return {
                "most_active": None,
                "highest_success_rate": None,
                "most_failed": None,
                "agents": [],
            }
        
        agents = []
        for row in rows:
            total = row.total or 0
            success_count = row.success_count or 0
            failed_count = row.failed_count or 0
            success_rate = (success_count / total * 100) if total > 0 else 0
            
            agents.append({
                "agent_name": row.agent_name,
                "total": total,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": round(success_rate, 1),
            })
        
        # Sort to find leaders
        most_active = max(agents, key=lambda x: x["total"]) if agents else None
        highest_success = max(
            [a for a in agents if a["total"] >= 3], 
            key=lambda x: x["success_rate"],
            default=None
        )
        most_failed = max(
            [a for a in agents if a["failed_count"] > 0],
            key=lambda x: x["failed_count"],
            default=None
        )
        
        return {
            "most_active": most_active,
            "highest_success_rate": highest_success,
            "most_failed": most_failed,
            "agents": sorted(agents, key=lambda x: x["total"], reverse=True),
        }
    
    async def get_recent_activity(self, limit: int = 20) -> list:
        """
        Get recent activity feed combining queue and executions.
        
        Returns list of activity events with type, actor, timestamp.
        """
        activities = []
        
        # Get recent queue changes
        queue_result = await self.db.execute(
            select(CommandQueueItem)
            .where(CommandQueueItem.status.in_(["approved", "sent", "rejected"]))
            .order_by(CommandQueueItem.updated_at.desc())
            .limit(limit // 2)
        )
        for item in queue_result.scalars():
            activities.append({
                "type": "queue",
                "action": item.status,
                "actor": "operator" if item.status != "sent" else "system",
                "description": f"{item.action_type} {item.status}",
                "timestamp": item.updated_at.isoformat() if item.updated_at else None,
                "item_id": item.id,
            })
        
        # Get recent executions
        exec_result = await self.db.execute(
            select(AgentExecution)
            .where(AgentExecution.status.in_([
                ExecutionStatus.SUCCESS.value,
                ExecutionStatus.FAILED.value,
            ]))
            .order_by(AgentExecution.completed_at.desc())
            .limit(limit // 2)
        )
        for execution in exec_result.scalars():
            activities.append({
                "type": "execution",
                "action": execution.status,
                "actor": execution.agent_name,
                "description": f"{execution.agent_name} {execution.status}",
                "timestamp": (
                    execution.completed_at.isoformat() 
                    if execution.completed_at 
                    else execution.created_at.isoformat()
                ),
                "execution_id": execution.id,
            })
        
        # Sort by timestamp and limit
        activities.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        return activities[:limit]


def get_dashboard_metrics_service(db: AsyncSession) -> DashboardMetricsService:
    """Factory function for dashboard metrics service."""
    return DashboardMetricsService(db)
