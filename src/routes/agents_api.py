"""Agents API - Discovery and management endpoints.

Sprint 41: Provides API for discovering and invoking agents.
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.agents.registry import get_agent_registry, AgentMeta, DOMAIN_CONFIG
from src.logger import get_logger

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
