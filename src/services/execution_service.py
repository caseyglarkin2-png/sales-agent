"""
Execution Service for Agent Tracking.

This service provides CRUD operations for agent executions,
enabling visibility into what agents are doing and their outcomes.

Key capabilities:
- start_execution(): Create new execution record
- complete_execution(): Mark execution as successful
- fail_execution(): Mark execution as failed
- get_recent_executions(): Query execution history
- get_execution_stats(): Aggregate success/failure metrics
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_execution import AgentExecution, ExecutionStatus
from src.logger import get_logger
from src.telemetry import log_event

logger = get_logger(__name__)


class ExecutionService:
    """
    Execution tracking service for all agents.
    
    Provides visibility into agent operations, success rates,
    and failure patterns for debugging and monitoring.
    """
    
    def __init__(self, db_session: AsyncSession):
        """Initialize with database session."""
        self.db = db_session
    
    # =========================================================================
    # Execution Lifecycle
    # =========================================================================
    
    async def start_execution(
        self,
        agent_name: str,
        domain: str,
        input_context: Dict[str, Any],
        trigger_source: str = "manual",
        triggered_by: Optional[str] = None,
        celery_task_id: Optional[str] = None,
    ) -> AgentExecution:
        """
        Create a new execution record and mark as running.
        
        Args:
            agent_name: Name of the agent being executed (e.g., "ProspectingAgent")
            domain: Domain of operation (e.g., "prospecting", "nurturing")
            input_context: The context/payload passed to the agent
            trigger_source: What triggered this ("manual", "celery", "signal", "api")
            triggered_by: User ID or system identifier
            celery_task_id: Celery task ID if async
            
        Returns:
            AgentExecution record in RUNNING status
        """
        execution = AgentExecution(
            agent_name=agent_name,
            domain=domain,
            status=ExecutionStatus.PENDING.value,
            input_context=input_context,
            trigger_source=trigger_source,
            triggered_by=triggered_by,
            celery_task_id=celery_task_id,
        )
        
        self.db.add(execution)
        await self.db.flush()  # Get ID without committing
        
        # Mark as running
        execution.mark_running()
        await self.db.commit()
        await self.db.refresh(execution)
        
        log_event(
            "agent_execution_started",
            execution_id=execution.id,
            agent_name=agent_name,
            domain=domain,
            trigger_source=trigger_source,
        )
        logger.info(f"Started execution {execution.id} for {agent_name} ({domain})")
        
        return execution
    
    async def complete_execution(
        self,
        execution_id: int,
        result: Dict[str, Any],
    ) -> AgentExecution:
        """
        Mark an execution as successfully completed.
        
        Args:
            execution_id: ID of the execution
            result: The output/result from the agent
            
        Returns:
            Updated AgentExecution record
            
        Raises:
            ValueError: If execution not found or already terminal
        """
        execution = await self._get_execution(execution_id)
        
        if execution.is_terminal:
            raise ValueError(
                f"Execution {execution_id} is already in terminal state: {execution.status}"
            )
        
        execution.mark_success(result)
        await self.db.commit()
        await self.db.refresh(execution)
        
        log_event(
            "agent_execution_completed",
            execution_id=execution_id,
            agent_name=execution.agent_name,
            duration_ms=execution.duration_ms,
        )
        logger.info(
            f"Completed execution {execution_id} for {execution.agent_name} "
            f"in {execution.duration_ms}ms"
        )
        
        return execution
    
    async def fail_execution(
        self,
        execution_id: int,
        error_message: str,
        error_traceback: Optional[str] = None,
    ) -> AgentExecution:
        """
        Mark an execution as failed.
        
        Args:
            execution_id: ID of the execution
            error_message: Error description
            error_traceback: Full traceback if available
            
        Returns:
            Updated AgentExecution record
            
        Raises:
            ValueError: If execution not found or already terminal
        """
        execution = await self._get_execution(execution_id)
        
        if execution.is_terminal:
            raise ValueError(
                f"Execution {execution_id} is already in terminal state: {execution.status}"
            )
        
        execution.mark_failed(error_message, error_traceback)
        await self.db.commit()
        await self.db.refresh(execution)
        
        log_event(
            "agent_execution_failed",
            execution_id=execution_id,
            agent_name=execution.agent_name,
            error_message=error_message,
        )
        logger.warning(
            f"Failed execution {execution_id} for {execution.agent_name}: {error_message}"
        )
        
        return execution
    
    async def timeout_execution(
        self,
        execution_id: int,
    ) -> AgentExecution:
        """
        Mark an execution as timed out.
        
        Args:
            execution_id: ID of the execution
            
        Returns:
            Updated AgentExecution record
            
        Raises:
            ValueError: If execution not found or already terminal
        """
        execution = await self._get_execution(execution_id)
        
        if execution.is_terminal:
            raise ValueError(
                f"Execution {execution_id} is already in terminal state: {execution.status}"
            )
        
        execution.mark_timed_out()
        await self.db.commit()
        await self.db.refresh(execution)
        
        log_event(
            "agent_execution_timed_out",
            execution_id=execution_id,
            agent_name=execution.agent_name,
        )
        logger.warning(f"Timed out execution {execution_id} for {execution.agent_name}")
        
        return execution
    
    async def cancel_execution(
        self,
        execution_id: int,
        reason: str = "Cancelled by user",
    ) -> AgentExecution:
        """
        Cancel a pending or running execution.
        
        Args:
            execution_id: ID of the execution
            reason: Reason for cancellation
            
        Returns:
            Updated AgentExecution record
            
        Raises:
            ValueError: If execution not found or already terminal
        """
        execution = await self._get_execution(execution_id)
        
        if execution.is_terminal:
            raise ValueError(
                f"Execution {execution_id} is already in terminal state: {execution.status}"
            )
        
        execution.status = ExecutionStatus.CANCELLED.value
        execution.completed_at = datetime.utcnow()
        execution.error_message = reason
        if execution.started_at:
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )
        
        await self.db.commit()
        await self.db.refresh(execution)
        
        log_event(
            "agent_execution_cancelled",
            execution_id=execution_id,
            agent_name=execution.agent_name,
            reason=reason,
        )
        logger.info(f"Cancelled execution {execution_id} for {execution.agent_name}: {reason}")
        
        return execution
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    async def get_execution(self, execution_id: int) -> Optional[AgentExecution]:
        """
        Get an execution by ID.
        
        Args:
            execution_id: ID of the execution
            
        Returns:
            AgentExecution or None if not found
        """
        result = await self.db.execute(
            select(AgentExecution).where(AgentExecution.id == execution_id)
        )
        return result.scalar_one_or_none()
    
    async def get_recent_executions(
        self,
        agent_name: Optional[str] = None,
        domain: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[AgentExecution]:
        """
        Get recent executions with optional filters.
        
        Args:
            agent_name: Filter by agent name
            domain: Filter by domain
            status: Filter by status
            limit: Max results to return
            
        Returns:
            List of AgentExecution records, newest first
        """
        query = select(AgentExecution)
        
        conditions = []
        if agent_name:
            conditions.append(AgentExecution.agent_name == agent_name)
        if domain:
            conditions.append(AgentExecution.domain == domain)
        if status:
            conditions.append(AgentExecution.status == status)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(desc(AgentExecution.created_at)).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_execution_stats(
        self,
        agent_name: Optional[str] = None,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Get execution statistics for an agent or all agents.
        
        Args:
            agent_name: Filter by agent name (None for all)
            hours: Time window in hours
            
        Returns:
            Dict with counts by status, avg duration, success rate
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        query = select(
            AgentExecution.status,
            func.count(AgentExecution.id).label("count"),
            func.avg(AgentExecution.duration_ms).label("avg_duration"),
        ).where(AgentExecution.created_at >= since)
        
        if agent_name:
            query = query.where(AgentExecution.agent_name == agent_name)
        
        query = query.group_by(AgentExecution.status)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        # Build stats dict
        stats = {
            "period_hours": hours,
            "by_status": {},
            "total": 0,
            "success_rate": 0.0,
            "avg_duration_ms": None,
        }
        
        total = 0
        success_count = 0
        total_duration = 0
        duration_count = 0
        
        for row in rows:
            status, count, avg_dur = row
            stats["by_status"][status] = {
                "count": count,
                "avg_duration_ms": round(avg_dur) if avg_dur else None,
            }
            total += count
            if status == ExecutionStatus.SUCCESS.value:
                success_count = count
            if avg_dur:
                total_duration += avg_dur * count
                duration_count += count
        
        stats["total"] = total
        if total > 0:
            stats["success_rate"] = round(success_count / total * 100, 1)
        if duration_count > 0:
            stats["avg_duration_ms"] = round(total_duration / duration_count)
        
        if agent_name:
            stats["agent_name"] = agent_name
        
        return stats
    
    async def get_running_executions(self) -> List[AgentExecution]:
        """
        Get all currently running executions.
        
        Returns:
            List of executions in RUNNING status
        """
        result = await self.db.execute(
            select(AgentExecution)
            .where(AgentExecution.status == ExecutionStatus.RUNNING.value)
            .order_by(AgentExecution.started_at)
        )
        return list(result.scalars().all())
    
    async def get_stale_executions(
        self,
        stale_after_minutes: int = 30,
    ) -> List[AgentExecution]:
        """
        Get executions that have been running too long (potentially stuck).
        
        Args:
            stale_after_minutes: Consider stale after this many minutes
            
        Returns:
            List of potentially stuck executions
        """
        cutoff = datetime.utcnow() - timedelta(minutes=stale_after_minutes)
        
        result = await self.db.execute(
            select(AgentExecution)
            .where(
                and_(
                    AgentExecution.status == ExecutionStatus.RUNNING.value,
                    AgentExecution.started_at < cutoff,
                )
            )
            .order_by(AgentExecution.started_at)
        )
        return list(result.scalars().all())
    
    # =========================================================================
    # Private Helpers
    # =========================================================================
    
    async def _get_execution(self, execution_id: int) -> AgentExecution:
        """Get execution by ID or raise ValueError."""
        execution = await self.get_execution(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        return execution


# Factory function for dependency injection
def get_execution_service(db: AsyncSession) -> ExecutionService:
    """Create ExecutionService instance with database session."""
    return ExecutionService(db)
