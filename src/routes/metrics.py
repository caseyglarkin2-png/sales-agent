"""Metrics and monitoring endpoints."""
import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter

from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])

# Track server start time
_server_start_time = time.time()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": int(time.time() - _server_start_time),
    }


@router.get("/summary")
async def metrics_summary() -> Dict[str, Any]:
    """Get a summary of system metrics."""
    try:
        from src.db.workflow_db import get_workflow_db
        from src.operator_mode import get_draft_queue
        
        db = await get_workflow_db()
        queue = get_draft_queue()
        
        # Get workflow stats
        stats = await db.get_workflow_stats()
        pending_drafts = await queue.get_pending_approvals()
        recent_workflows = await db.get_recent_workflows(limit=10)
        
        # Calculate success rate
        today = stats.get("today", {})
        total = today.get("total", 0)
        success = today.get("success", 0)
        success_rate = (success / total * 100) if total > 0 else 0
        
        # Calculate average workflow time
        completed_workflows = [
            w for w in recent_workflows 
            if w.get("completed_at") and w.get("started_at")
        ]
        
        avg_duration = 0
        if completed_workflows:
            durations = []
            for w in completed_workflows:
                try:
                    start = w.get("started_at")
                    end = w.get("completed_at")
                    if hasattr(start, 'timestamp') and hasattr(end, 'timestamp'):
                        durations.append((end.timestamp() - start.timestamp()))
                except Exception:
                    pass
            if durations:
                avg_duration = sum(durations) / len(durations)
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": int(time.time() - _server_start_time),
            "workflows": {
                "today_total": total,
                "today_success": success,
                "today_failed": today.get("failed", 0),
                "success_rate_percent": round(success_rate, 1),
                "avg_duration_seconds": round(avg_duration, 2),
            },
            "drafts": {
                "pending": len(pending_drafts),
            },
            "status_breakdown": stats.get("status_breakdown", {}),
        }
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }


@router.get("/prometheus")
async def prometheus_metrics() -> str:
    """Prometheus-compatible metrics endpoint."""
    try:
        from src.db.workflow_db import get_workflow_db
        from src.operator_mode import get_draft_queue
        
        db = await get_workflow_db()
        queue = get_draft_queue()
        
        stats = await db.get_workflow_stats()
        pending = await queue.get_pending_approvals()
        
        today = stats.get("today", {})
        
        lines = [
            "# HELP sales_agent_uptime_seconds Server uptime in seconds",
            "# TYPE sales_agent_uptime_seconds gauge",
            f"sales_agent_uptime_seconds {int(time.time() - _server_start_time)}",
            "",
            "# HELP sales_agent_workflows_total Total workflows processed today",
            "# TYPE sales_agent_workflows_total counter",
            f"sales_agent_workflows_total {today.get('total', 0)}",
            "",
            "# HELP sales_agent_workflows_success Successful workflows today",
            "# TYPE sales_agent_workflows_success counter",
            f"sales_agent_workflows_success {today.get('success', 0)}",
            "",
            "# HELP sales_agent_workflows_failed Failed workflows today",
            "# TYPE sales_agent_workflows_failed counter",
            f"sales_agent_workflows_failed {today.get('failed', 0)}",
            "",
            "# HELP sales_agent_pending_drafts Number of pending drafts",
            "# TYPE sales_agent_pending_drafts gauge",
            f"sales_agent_pending_drafts {len(pending)}",
        ]
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error generating prometheus metrics: {e}")
        return f"# Error: {e}"
