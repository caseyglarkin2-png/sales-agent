"""Agents API - Discovery and management endpoints.

Sprint 41: Provides API for discovering and invoking agents.
Sprint 42: Adds execution tracking and manual trigger endpoints.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.registry import get_agent_registry, AgentMeta, DOMAIN_CONFIG
from src.db import get_db
from src.logger import get_logger
from src.models.agent_execution import ExecutionStatus
from src.services.execution_service import ExecutionService, get_execution_service
from src.tasks.agent_executor import queue_agent_execution

logger = get_logger(__name__)

router = APIRouter(prefix="/api/agents", tags=["Agents"])


# ============================================================================
# Pydantic Models
# ============================================================================

class AgentResponse(BaseModel):
    """Response model for a single agent."""
    name: str
    description: str
    domain: str
    module_path: str
    class_name: str
    capabilities: List[str]
    icon: str
    status: str


class DomainResponse(BaseModel):
    """Response model for a domain."""
    id: str
    label: str
    icon: str
    color: str
    count: int


class AgentListResponse(BaseModel):
    """Response model for agent list."""
    total: int
    domains: List[DomainResponse]
    agents: List[AgentResponse]


class AgentSearchResponse(BaseModel):
    """Response for agent search."""
    query: str
    count: int
    agents: List[AgentResponse]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("", response_model=AgentListResponse)
async def list_agents(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    status: Optional[str] = Query(None, description="Filter by status: active, beta, deprecated"),
):
    """
    List all registered agents.
    
    Optionally filter by domain or status.
    """
    registry = get_agent_registry()
    
    if domain:
        agents = registry.get_by_domain(domain)
    else:
        agents = registry.list_all()
    
    # Filter by status if provided
    if status:
        agents = [a for a in agents if a.status == status]
    
    return AgentListResponse(
        total=len(agents),
        domains=registry.list_domains(),
        agents=[AgentResponse(**a.to_dict()) for a in agents],
    )


class DomainsListResponse(BaseModel):
    """Response for list of domains."""
    domains: List[DomainResponse]


@router.get("/domains", response_model=DomainsListResponse)
async def list_domains():
    """List all agent domains with counts."""
    registry = get_agent_registry()
    return DomainsListResponse(domains=registry.list_domains())


@router.get("/search", response_model=AgentSearchResponse)
async def search_agents(
    q: str = Query(..., min_length=1, description="Search query"),
):
    """Search agents by name or description."""
    registry = get_agent_registry()
    agents = registry.search(q)
    
    return AgentSearchResponse(
        query=q,
        count=len(agents),
        agents=[AgentResponse(**a.to_dict()) for a in agents],
    )


@router.get("/stats")
async def get_agent_stats():
    """Get agent statistics."""
    registry = get_agent_registry()
    agents = registry.list_all()
    
    # Count by status
    status_counts = {}
    for agent in agents:
        status_counts[agent.status] = status_counts.get(agent.status, 0) + 1
    
    # Count by domain
    domain_counts = {}
    for agent in agents:
        domain_counts[agent.domain] = domain_counts.get(agent.domain, 0) + 1
    
    return {
        "total_agents": len(agents),
        "domains": len(domain_counts),
        "active": status_counts.get("active", 0),
        "beta": status_counts.get("beta", 0),
        "deprecated": status_counts.get("deprecated", 0),
        "by_status": status_counts,
        "by_domain": domain_counts,
    }


@router.get("/{agent_name}", response_model=AgentResponse)
async def get_agent(agent_name: str):
    """Get a specific agent by name."""
    registry = get_agent_registry()
    
    # Try by name first
    agent = registry.get_by_name(agent_name)
    
    # Try by class name if not found
    if not agent:
        agent = registry.get_by_class(agent_name)
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
    
    return AgentResponse(**agent.to_dict())


# ============================================================================
# Execution Models & Endpoints (Sprint 42)
# ============================================================================

class ExecuteAgentRequest(BaseModel):
    """Request to execute an agent."""
    context: Dict[str, Any] = Field(default_factory=dict, description="Execution context/payload")
    async_mode: bool = Field(default=True, description="Run asynchronously via Celery")
    triggered_by: Optional[str] = Field(None, description="User or system that triggered execution")


class ExecutionResponse(BaseModel):
    """Response for an execution operation."""
    execution_id: int
    agent_name: str
    domain: str
    status: str
    trigger_source: str
    triggered_by: Optional[str]
    created_at: datetime
    message: str


class ExecutionDetailResponse(BaseModel):
    """Detailed response for an execution."""
    id: int
    agent_name: str
    domain: str
    status: str
    input_context: Optional[Dict[str, Any]]
    output_result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    error_traceback: Optional[str]
    duration_ms: Optional[int]
    trigger_source: str
    triggered_by: Optional[str]
    celery_task_id: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class ExecutionListResponse(BaseModel):
    """Response for list of executions."""
    total: int
    executions: List[ExecutionDetailResponse]


class ExecutionStatsResponse(BaseModel):
    """Response for execution statistics."""
    period_hours: int
    agent_name: Optional[str]
    total: int
    success_rate: float
    avg_duration_ms: Optional[int]
    by_status: Dict[str, Any]


@router.post("/{agent_name}/execute", response_model=ExecutionResponse)
async def execute_agent(
    agent_name: str,
    request: ExecuteAgentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger manual execution of an agent.
    
    This creates an execution record and optionally queues the agent
    for async execution via Celery (default) or runs synchronously.
    """
    registry = get_agent_registry()
    
    # Find the agent
    agent_meta = registry.get_by_name(agent_name)
    if not agent_meta:
        agent_meta = registry.get_by_class(agent_name)
    
    if not agent_meta:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
    
    # Create execution record
    service = get_execution_service(db)
    
    execution = await service.start_execution(
        agent_name=agent_meta.class_name,
        domain=agent_meta.domain,
        input_context=request.context,
        trigger_source="api" if request.async_mode else "api_sync",
        triggered_by=request.triggered_by,
    )
    
    if request.async_mode:
        # Queue for async execution via Celery
        task_id = queue_agent_execution(
            execution_id=execution.id,
            agent_class_name=agent_meta.class_name,
            module_path=agent_meta.module_path,
            context=request.context,
        )
        message = f"Agent {agent_meta.name} queued for execution (task: {task_id[:8]}...)"
    else:
        # Sync execution not implemented - use async
        message = f"Agent {agent_meta.name} execution started (sync mode not supported, using async)"
        task_id = queue_agent_execution(
            execution_id=execution.id,
            agent_class_name=agent_meta.class_name,
            module_path=agent_meta.module_path,
            context=request.context,
        )
    
    logger.info(f"Execution {execution.id} started for {agent_meta.name}")
    
    return ExecutionResponse(
        execution_id=execution.id,
        agent_name=agent_meta.name,
        domain=agent_meta.domain,
        status=execution.status,
        trigger_source=execution.trigger_source,
        triggered_by=execution.triggered_by,
        created_at=execution.created_at,
        message=message,
    )


@router.get("/{agent_name}/executions", response_model=ExecutionListResponse)
async def get_agent_executions(
    agent_name: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=200, description="Max results"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get execution history for a specific agent.
    """
    registry = get_agent_registry()
    
    # Resolve agent
    agent_meta = registry.get_by_name(agent_name)
    if not agent_meta:
        agent_meta = registry.get_by_class(agent_name)
    
    if not agent_meta:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
    
    service = get_execution_service(db)
    executions = await service.get_recent_executions(
        agent_name=agent_meta.class_name,
        status=status,
        limit=limit,
    )
    
    return ExecutionListResponse(
        total=len(executions),
        executions=[
            ExecutionDetailResponse(
                id=e.id,
                agent_name=e.agent_name,
                domain=e.domain,
                status=e.status,
                input_context=e.input_context,
                output_result=e.output_result,
                error_message=e.error_message,
                error_traceback=e.error_traceback,
                duration_ms=e.duration_ms,
                trigger_source=e.trigger_source,
                triggered_by=e.triggered_by,
                celery_task_id=e.celery_task_id,
                created_at=e.created_at,
                started_at=e.started_at,
                completed_at=e.completed_at,
            )
            for e in executions
        ],
    )


@router.get("/{agent_name}/executions/stats", response_model=ExecutionStatsResponse)
async def get_agent_execution_stats(
    agent_name: str,
    hours: int = Query(24, le=168, description="Time window in hours"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get execution statistics for a specific agent.
    """
    registry = get_agent_registry()
    
    # Resolve agent
    agent_meta = registry.get_by_name(agent_name)
    if not agent_meta:
        agent_meta = registry.get_by_class(agent_name)
    
    if not agent_meta:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")
    
    service = get_execution_service(db)
    stats = await service.get_execution_stats(
        agent_name=agent_meta.class_name,
        hours=hours,
    )
    
    return ExecutionStatsResponse(**stats)


@router.get("/executions/all", response_model=ExecutionListResponse)
async def get_all_executions(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=200, description="Max results"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get execution history across all agents.
    """
    service = get_execution_service(db)
    executions = await service.get_recent_executions(
        domain=domain,
        status=status,
        limit=limit,
    )
    
    return ExecutionListResponse(
        total=len(executions),
        executions=[
            ExecutionDetailResponse(
                id=e.id,
                agent_name=e.agent_name,
                domain=e.domain,
                status=e.status,
                input_context=e.input_context,
                output_result=e.output_result,
                error_message=e.error_message,
                error_traceback=e.error_traceback,
                duration_ms=e.duration_ms,
                trigger_source=e.trigger_source,
                triggered_by=e.triggered_by,
                celery_task_id=e.celery_task_id,
                created_at=e.created_at,
                started_at=e.started_at,
                completed_at=e.completed_at,
            )
            for e in executions
        ],
    )


@router.delete("/executions/{execution_id}")
async def cancel_execution(
    execution_id: int,
    reason: str = Query("Cancelled by user", description="Cancellation reason"),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a pending or running execution.
    """
    service = get_execution_service(db)
    
    try:
        execution = await service.cancel_execution(execution_id, reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return {
        "execution_id": execution_id,
        "status": execution.status,
        "message": f"Execution cancelled: {reason}",
    }

