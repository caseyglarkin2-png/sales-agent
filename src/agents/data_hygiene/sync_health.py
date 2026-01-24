"""Sync Health Agent - Monitors sync health between systems.

Responsibilities:
- Monitor HubSpot <-> CaseyOS sync health
- Detect sync failures and lag
- Track rate limit usage
- Alert on sync issues
- Provide sync status dashboard data
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from src.agents.base import BaseAgent
from src.logger import get_logger

logger = get_logger(__name__)


class SyncStatus(str, Enum):
    """Overall sync status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    UNKNOWN = "unknown"


class SyncDirection(str, Enum):
    """Direction of sync."""
    INBOUND = "inbound"   # From external to CaseyOS
    OUTBOUND = "outbound"  # From CaseyOS to external
    BIDIRECTIONAL = "bidirectional"


@dataclass
class SyncMetrics:
    """Metrics for a sync operation."""
    records_synced: int
    records_failed: int
    last_sync_at: Optional[datetime]
    sync_duration_seconds: float
    rate_limit_remaining: int
    rate_limit_max: int
    errors: List[str]


@dataclass
class SyncHealthReport:
    """Health report for a sync connection."""
    connection_name: str
    status: SyncStatus
    direction: SyncDirection
    last_successful_sync: Optional[datetime]
    sync_lag_seconds: int
    metrics: SyncMetrics
    recommendations: List[str]


class SyncHealthAgent(BaseAgent):
    """Monitors sync health between CaseyOS and external systems.
    
    Monitored Connections:
    - HubSpot Contacts (bidirectional)
    - HubSpot Deals (inbound)
    - Gmail Threads (inbound)
    - Calendar Events (inbound)
    
    Health Criteria:
    - Sync lag < 5 minutes: Healthy
    - Sync lag 5-15 minutes: Degraded
    - Sync lag > 15 minutes or errors: Failing
    
    Alerts:
    - Rate limit approaching (>80% used)
    - Sync failing for >30 minutes
    - High error rate (>5%)
    """
    
    # Thresholds
    LAG_HEALTHY_SECONDS = 300  # 5 minutes
    LAG_DEGRADED_SECONDS = 900  # 15 minutes
    RATE_LIMIT_WARNING_THRESHOLD = 0.8  # 80%
    ERROR_RATE_THRESHOLD = 0.05  # 5%
    
    def __init__(self):
        super().__init__(
            name="SyncHealthAgent",
            description="Monitors sync health between systems"
        )
        # In-memory sync state (would be persisted in real implementation)
        self.sync_state: Dict[str, Dict[str, Any]] = {}
    
    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate input based on action."""
        action = context.get("action", "get_status")
        if action == "record_sync":
            return "connection" in context and "metrics" in context
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute sync health check based on action."""
        action = context.get("action", "get_status")
        
        if action == "get_status":
            # Get overall sync health status
            connection = context.get("connection")
            if connection:
                report = self._get_connection_health(connection)
                return {
                    "status": "success",
                    "report": self._report_to_dict(report) if report else None,
                }
            else:
                reports = self._get_all_health_reports()
                return {
                    "status": "success",
                    "overall_status": self._calculate_overall_status(reports).value,
                    "connections": [self._report_to_dict(r) for r in reports],
                }
        
        elif action == "record_sync":
            # Record a sync operation
            connection = context.get("connection")
            metrics = context.get("metrics", {})
            self._record_sync(connection, metrics)
            return {
                "status": "success",
                "connection": connection,
                "recorded": True,
            }
        
        elif action == "get_rate_limits":
            # Get rate limit status for all connections
            limits = self._get_rate_limit_status()
            return {
                "status": "success",
                "rate_limits": limits,
            }
        
        elif action == "get_alerts":
            # Get active sync alerts
            alerts = self._check_for_alerts()
            return {
                "status": "success",
                "alerts": alerts,
                "alert_count": len(alerts),
            }
        
        elif action == "get_dashboard":
            # Get full dashboard data
            reports = self._get_all_health_reports()
            alerts = self._check_for_alerts()
            limits = self._get_rate_limit_status()
            
            return {
                "status": "success",
                "dashboard": {
                    "overall_status": self._calculate_overall_status(reports).value,
                    "connections": [self._report_to_dict(r) for r in reports],
                    "alerts": alerts,
                    "rate_limits": limits,
                    "last_updated": datetime.utcnow().isoformat(),
                },
            }
        
        return {"status": "error", "error": f"Unknown action: {action}"}
    
    def _get_connection_health(self, connection: str) -> Optional[SyncHealthReport]:
        """Get health report for a specific connection."""
        state = self.sync_state.get(connection)
        if not state:
            # Return default unknown state
            return SyncHealthReport(
                connection_name=connection,
                status=SyncStatus.UNKNOWN,
                direction=SyncDirection.BIDIRECTIONAL,
                last_successful_sync=None,
                sync_lag_seconds=0,
                metrics=SyncMetrics(
                    records_synced=0,
                    records_failed=0,
                    last_sync_at=None,
                    sync_duration_seconds=0,
                    rate_limit_remaining=0,
                    rate_limit_max=0,
                    errors=[],
                ),
                recommendations=["No sync data available. Initiate first sync."],
            )
        
        return self._build_health_report(connection, state)
    
    def _get_all_health_reports(self) -> List[SyncHealthReport]:
        """Get health reports for all known connections."""
        # Define known connections
        known_connections = [
            "hubspot_contacts",
            "hubspot_deals",
            "hubspot_companies",
            "gmail_threads",
            "calendar_events",
        ]
        
        reports = []
        for conn in known_connections:
            report = self._get_connection_health(conn)
            if report:
                reports.append(report)
        
        return reports
    
    def _build_health_report(
        self, 
        connection: str, 
        state: Dict[str, Any]
    ) -> SyncHealthReport:
        """Build health report from state."""
        now = datetime.utcnow()
        last_sync = state.get("last_sync_at")
        
        # Calculate lag
        if last_sync:
            lag = (now - last_sync).total_seconds()
        else:
            lag = float('inf')
        
        # Determine status
        if state.get("last_error"):
            status = SyncStatus.FAILING
        elif lag > self.LAG_DEGRADED_SECONDS:
            status = SyncStatus.FAILING
        elif lag > self.LAG_HEALTHY_SECONDS:
            status = SyncStatus.DEGRADED
        else:
            status = SyncStatus.HEALTHY
        
        # Calculate error rate
        total = state.get("records_synced", 0) + state.get("records_failed", 0)
        error_rate = state.get("records_failed", 0) / total if total > 0 else 0
        if error_rate > self.ERROR_RATE_THRESHOLD:
            status = SyncStatus.DEGRADED if status == SyncStatus.HEALTHY else status
        
        # Build recommendations
        recommendations = []
        if status == SyncStatus.FAILING:
            recommendations.append("Investigate sync failures immediately")
        if lag > self.LAG_HEALTHY_SECONDS:
            recommendations.append(f"Sync lag is {int(lag)}s - consider increasing sync frequency")
        
        rate_used = 1 - (state.get("rate_limit_remaining", 0) / max(state.get("rate_limit_max", 1), 1))
        if rate_used > self.RATE_LIMIT_WARNING_THRESHOLD:
            recommendations.append(f"Rate limit at {rate_used:.0%} - reduce sync frequency")
        
        if error_rate > 0.01:
            recommendations.append(f"Error rate at {error_rate:.1%} - review failed records")
        
        return SyncHealthReport(
            connection_name=connection,
            status=status,
            direction=state.get("direction", SyncDirection.BIDIRECTIONAL),
            last_successful_sync=last_sync,
            sync_lag_seconds=int(lag) if lag != float('inf') else -1,
            metrics=SyncMetrics(
                records_synced=state.get("records_synced", 0),
                records_failed=state.get("records_failed", 0),
                last_sync_at=last_sync,
                sync_duration_seconds=state.get("sync_duration", 0),
                rate_limit_remaining=state.get("rate_limit_remaining", 0),
                rate_limit_max=state.get("rate_limit_max", 0),
                errors=state.get("errors", [])[-5:],  # Last 5 errors
            ),
            recommendations=recommendations,
        )
    
    def _record_sync(self, connection: str, metrics: Dict[str, Any]) -> None:
        """Record a sync operation."""
        now = datetime.utcnow()
        
        if connection not in self.sync_state:
            self.sync_state[connection] = {
                "records_synced": 0,
                "records_failed": 0,
                "errors": [],
                "direction": SyncDirection.BIDIRECTIONAL,
            }
        
        state = self.sync_state[connection]
        state["last_sync_at"] = now
        state["records_synced"] = state.get("records_synced", 0) + metrics.get("records_synced", 0)
        state["records_failed"] = state.get("records_failed", 0) + metrics.get("records_failed", 0)
        state["sync_duration"] = metrics.get("duration_seconds", 0)
        state["rate_limit_remaining"] = metrics.get("rate_limit_remaining", 0)
        state["rate_limit_max"] = metrics.get("rate_limit_max", 0)
        
        if metrics.get("error"):
            state["errors"] = state.get("errors", [])
            state["errors"].append({
                "message": metrics["error"],
                "at": now.isoformat(),
            })
            # Keep only last 100 errors
            state["errors"] = state["errors"][-100:]
            state["last_error"] = metrics["error"]
        else:
            state["last_error"] = None
        
        logger.info(f"Recorded sync for {connection}: {metrics.get('records_synced', 0)} synced, {metrics.get('records_failed', 0)} failed")
    
    def _get_rate_limit_status(self) -> Dict[str, Any]:
        """Get rate limit status for all connections."""
        status = {}
        
        for conn, state in self.sync_state.items():
            remaining = state.get("rate_limit_remaining", 0)
            max_limit = state.get("rate_limit_max", 0)
            
            if max_limit > 0:
                used_pct = 1 - (remaining / max_limit)
                status[conn] = {
                    "remaining": remaining,
                    "max": max_limit,
                    "used_pct": round(used_pct * 100, 1),
                    "warning": used_pct > self.RATE_LIMIT_WARNING_THRESHOLD,
                }
        
        return status
    
    def _check_for_alerts(self) -> List[Dict[str, Any]]:
        """Check for active alerts across all connections."""
        alerts = []
        now = datetime.utcnow()
        
        for conn, state in self.sync_state.items():
            # Check for sync failures
            if state.get("last_error"):
                alerts.append({
                    "type": "sync_error",
                    "connection": conn,
                    "severity": "high",
                    "message": f"Sync error: {state['last_error'][:100]}",
                })
            
            # Check for sync lag
            last_sync = state.get("last_sync_at")
            if last_sync:
                lag = (now - last_sync).total_seconds()
                if lag > self.LAG_DEGRADED_SECONDS:
                    alerts.append({
                        "type": "sync_lag",
                        "connection": conn,
                        "severity": "high" if lag > 1800 else "medium",
                        "message": f"Sync lag: {int(lag)}s (last sync: {last_sync.isoformat()})",
                    })
            
            # Check for rate limits
            remaining = state.get("rate_limit_remaining", 0)
            max_limit = state.get("rate_limit_max", 1)
            if max_limit > 0:
                used_pct = 1 - (remaining / max_limit)
                if used_pct > self.RATE_LIMIT_WARNING_THRESHOLD:
                    alerts.append({
                        "type": "rate_limit",
                        "connection": conn,
                        "severity": "medium",
                        "message": f"Rate limit at {used_pct:.0%} ({remaining}/{max_limit} remaining)",
                    })
        
        return alerts
    
    def _calculate_overall_status(self, reports: List[SyncHealthReport]) -> SyncStatus:
        """Calculate overall sync status from all reports."""
        if not reports:
            return SyncStatus.UNKNOWN
        
        statuses = [r.status for r in reports]
        
        if any(s == SyncStatus.FAILING for s in statuses):
            return SyncStatus.FAILING
        if any(s == SyncStatus.DEGRADED for s in statuses):
            return SyncStatus.DEGRADED
        if any(s == SyncStatus.UNKNOWN for s in statuses):
            return SyncStatus.UNKNOWN
        
        return SyncStatus.HEALTHY
    
    def _report_to_dict(self, report: SyncHealthReport) -> Dict[str, Any]:
        """Convert report to dict."""
        return {
            "connection_name": report.connection_name,
            "status": report.status.value,
            "direction": report.direction.value,
            "last_successful_sync": report.last_successful_sync.isoformat() if report.last_successful_sync else None,
            "sync_lag_seconds": report.sync_lag_seconds,
            "metrics": {
                "records_synced": report.metrics.records_synced,
                "records_failed": report.metrics.records_failed,
                "last_sync_at": report.metrics.last_sync_at.isoformat() if report.metrics.last_sync_at else None,
                "sync_duration_seconds": report.metrics.sync_duration_seconds,
                "rate_limit_remaining": report.metrics.rate_limit_remaining,
                "rate_limit_max": report.metrics.rate_limit_max,
                "errors": report.metrics.errors,
            },
            "recommendations": report.recommendations,
        }
