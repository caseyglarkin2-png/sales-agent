"""Database persistence for workflow runs and audit logs."""
import os
from datetime import datetime
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

import asyncpg

from src.logger import get_logger

logger = get_logger(__name__)


class WorkflowDB:
    """Database interface for workflow persistence."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize with database URL from environment."""
        self.database_url = database_url or os.environ.get("DATABASE_URL")
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> bool:
        """Create connection pool."""
        if not self.database_url:
            logger.warning("DATABASE_URL not set, workflow persistence disabled")
            return False
        
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5,
                command_timeout=30,
            )
            logger.info("Database connection pool created")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool."""
        if not self.pool:
            yield None
            return
        
        async with self.pool.acquire() as conn:
            yield conn
    
    async def create_workflow_run(
        self,
        workflow_id: str,
        workflow_type: str,
        submission_id: Optional[str] = None,
        contact_email: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> Optional[str]:
        """Create a new workflow run record."""
        async with self.get_connection() as conn:
            if not conn:
                return None
            
            try:
                result = await conn.fetchrow(
                    """
                    INSERT INTO workflow_runs (
                        workflow_id, workflow_type, status, submission_id,
                        contact_email, company_name, started_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                    """,
                    workflow_id,
                    workflow_type,
                    "running",
                    submission_id,
                    contact_email,
                    company_name,
                    datetime.utcnow(),
                )
                logger.info(f"Created workflow run: {workflow_id}")
                return str(result["id"]) if result else None
            except Exception as e:
                logger.error(f"Error creating workflow run: {e}")
                return None
    
    async def update_workflow_run(
        self,
        workflow_id: str,
        status: str,
        draft_id: Optional[str] = None,
        steps_completed: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update a workflow run status."""
        async with self.get_connection() as conn:
            if not conn:
                return False
            
            try:
                import json
                steps_json = json.dumps(steps_completed) if steps_completed else None
                
                await conn.execute(
                    """
                    UPDATE workflow_runs
                    SET status = $2,
                        draft_id = COALESCE($3, draft_id),
                        steps_completed = COALESCE($4::jsonb, steps_completed),
                        error_message = $5,
                        completed_at = CASE WHEN $2 IN ('success', 'failed') THEN NOW() ELSE completed_at END
                    WHERE workflow_id = $1
                    """,
                    workflow_id,
                    status,
                    draft_id,
                    steps_json,
                    error_message,
                )
                logger.info(f"Updated workflow run {workflow_id}: status={status}")
                return True
            except Exception as e:
                logger.error(f"Error updating workflow run: {e}")
                return False
    
    async def get_recent_workflows(self, limit: int = 50) -> list:
        """Get recent workflow runs."""
        async with self.get_connection() as conn:
            if not conn:
                return []
            
            try:
                rows = await conn.fetch(
                    """
                    SELECT workflow_id, workflow_type, status, submission_id,
                           contact_email, company_name, draft_id, error_message,
                           started_at, completed_at
                    FROM workflow_runs
                    ORDER BY started_at DESC
                    LIMIT $1
                    """,
                    limit,
                )
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Error fetching recent workflows: {e}")
                return []
    
    async def get_workflow_stats(self) -> Dict[str, Any]:
        """Get workflow statistics."""
        async with self.get_connection() as conn:
            if not conn:
                return {}
            
            try:
                # Get counts by status
                status_counts = await conn.fetch(
                    """
                    SELECT status, COUNT(*) as count
                    FROM workflow_runs
                    WHERE started_at > NOW() - INTERVAL '24 hours'
                    GROUP BY status
                    """
                )
                
                # Get total counts
                totals = await conn.fetchrow(
                    """
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status = 'success') as success,
                        COUNT(*) FILTER (WHERE status = 'failed') as failed,
                        COUNT(*) FILTER (WHERE status = 'running') as running
                    FROM workflow_runs
                    WHERE started_at > NOW() - INTERVAL '24 hours'
                    """
                )
                
                return {
                    "today": {
                        "total": totals["total"] if totals else 0,
                        "success": totals["success"] if totals else 0,
                        "failed": totals["failed"] if totals else 0,
                        "running": totals["running"] if totals else 0,
                    },
                    "status_breakdown": {row["status"]: row["count"] for row in status_counts},
                }
            except Exception as e:
                logger.error(f"Error fetching workflow stats: {e}")
                return {}
    
    async def create_audit_log(
        self,
        action: str,
        actor: str,
        draft_id: str,
        contact_id: str,
        company_id: str,
        mode: str,
        status: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create an audit log entry."""
        async with self.get_connection() as conn:
            if not conn:
                return False
            
            try:
                import json
                meta_json = json.dumps(metadata) if metadata else None
                
                await conn.execute(
                    """
                    INSERT INTO draft_audit_log (
                        action, actor, draft_id, contact_id, company_id,
                        mode, status, reason, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
                    """,
                    action,
                    actor,
                    draft_id,
                    contact_id,
                    company_id,
                    mode,
                    status,
                    reason,
                    meta_json,
                )
                return True
            except Exception as e:
                logger.error(f"Error creating audit log: {e}")
                return False


# Singleton instance
_db: Optional[WorkflowDB] = None


async def get_workflow_db() -> WorkflowDB:
    """Get or create the workflow database instance."""
    global _db
    if _db is None:
        _db = WorkflowDB()
        await _db.connect()
    return _db


async def close_workflow_db():
    """Close the database connection."""
    global _db
    if _db:
        await _db.disconnect()
        _db = None
