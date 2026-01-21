"""API routes for health monitoring."""

from fastapi import APIRouter
from typing import Optional
from src.monitoring import (
    get_health_monitor,
    HealthStatus,
)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/health")
async def get_health_summary():
    """Get overall health summary."""
    monitor = get_health_monitor()
    return monitor.get_health_summary()


@router.get("/services")
async def list_services(critical_only: bool = False):
    """List all monitored services."""
    monitor = get_health_monitor()
    
    if critical_only:
        services = monitor.get_critical_services()
    else:
        services = monitor.get_all_services()
    
    return {
        "services": [s.to_dict() for s in services],
        "total": len(services),
    }


@router.get("/services/{service_name}")
async def get_service(service_name: str):
    """Get details for a specific service."""
    monitor = get_health_monitor()
    service = monitor.get_service(service_name)
    
    if not service:
        return {"error": f"Service {service_name} not found"}
    
    return {
        "service": service.to_dict(),
        "history": [h.to_dict() for h in service.health_history[-20:]],
    }


@router.post("/services/{service_name}/check")
async def check_service(service_name: str):
    """Manually trigger a health check for a service."""
    monitor = get_health_monitor()
    
    check = await monitor.check_service(service_name)
    
    return {
        "check": check.to_dict(),
        "service_status": monitor.get_service(service_name).status.value if monitor.get_service(service_name) else None,
    }


@router.post("/check-all")
async def check_all_services():
    """Trigger health checks for all services."""
    monitor = get_health_monitor()
    
    results = await monitor.check_all_services()
    
    return {
        "overall_status": monitor.get_overall_status().value,
        "checks": {name: check.to_dict() for name, check in results.items()},
    }


@router.get("/unhealthy")
async def get_unhealthy_services():
    """Get all unhealthy services."""
    monitor = get_health_monitor()
    unhealthy = monitor.get_unhealthy_services()
    
    return {
        "unhealthy_services": [s.to_dict() for s in unhealthy],
        "count": len(unhealthy),
    }


@router.get("/metrics/{service_name}")
async def get_service_metrics(service_name: str):
    """Get metrics for a specific service."""
    monitor = get_health_monitor()
    service = monitor.get_service(service_name)
    
    if not service:
        return {"error": f"Service {service_name} not found"}
    
    return {
        "service_name": service_name,
        "metrics": service.metrics.to_dict() if service.metrics else None,
    }


@router.get("/statuses")
async def list_health_statuses():
    """List all possible health statuses."""
    return {
        "statuses": [
            {
                "status": status.value,
                "name": status.name.replace("_", " ").title(),
            }
            for status in HealthStatus
        ]
    }
