"""Circuit Breaker Monitoring Routes."""

from typing import Dict, Any
from fastapi import APIRouter, Request

from src.circuit_breaker import get_all_circuit_breaker_stats, reset_all_circuit_breakers
from src.security.auth import require_admin_role

router = APIRouter(prefix="/api/circuit-breakers", tags=["Circuit Breakers"])


@router.get("/status")
async def get_circuit_breaker_status() -> Dict[str, Any]:
    """Get status of all circuit breakers."""
    stats = get_all_circuit_breaker_stats()
    
    # Calculate summary
    total_breakers = len(stats)
    open_breakers = sum(1 for s in stats.values() if s["state"] == "open")
    half_open_breakers = sum(1 for s in stats.values() if s["state"] == "half_open")
    
    return {
        "summary": {
            "total": total_breakers,
            "open": open_breakers,
            "half_open": half_open_breakers,
            "closed": total_breakers - open_breakers - half_open_breakers,
        },
        "breakers": stats,
    }


@router.post("/reset")
async def reset_circuit_breakers(request: Request):
    """
    Reset all circuit breakers (admin only).
    
    Requires: X-Admin-Token header
    """
    await require_admin_role(request)
    
    reset_all_circuit_breakers()
    
    return {
        "status": "success",
        "message": "All circuit breakers have been reset to CLOSED state",
    }
