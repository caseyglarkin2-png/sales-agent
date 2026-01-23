"""Database persistence for workflow runs and audit logs."""
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
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
            
            # Ensure tables exist
            await self._ensure_tables()
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    async def _ensure_tables(self):
        """Create tables if they don't exist."""
        async with self.get_connection() as conn:
            if not conn:
                return
            
            try:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS workflow_runs (
                        id SERIAL PRIMARY KEY,
                        workflow_id VARCHAR(255) UNIQUE NOT NULL,
                        workflow_type VARCHAR(100) NOT NULL,
                        status VARCHAR(50) DEFAULT 'running',
                        submission_id VARCHAR(255),
                        contact_email VARCHAR(255),
                        company_name VARCHAR(255),
                        draft_id VARCHAR(255),
                        steps_completed JSONB,
                        error_message TEXT,
                        started_at TIMESTAMP DEFAULT NOW(),
                        completed_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS pending_drafts (
                        id SERIAL PRIMARY KEY,
                        draft_id VARCHAR(255) UNIQUE NOT NULL,
                        gmail_draft_id VARCHAR(255),
                        recipient VARCHAR(255) NOT NULL,
                        subject TEXT,
                        body TEXT,
                        status VARCHAR(50) DEFAULT 'pending',
                        workflow_id VARCHAR(255),
                        contact_id VARCHAR(255),
                        company_name VARCHAR(255),
                        approved_by VARCHAR(255),
                        approved_at TIMESTAMP,
                        rejected_by VARCHAR(255),
                        rejected_at TIMESTAMP,
                        rejection_reason TEXT,
                        sent_at TIMESTAMP,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Add missing columns if they don't exist (migration)
                migration_columns = [
                    ("pending_drafts", "contact_id", "VARCHAR(255)"),
                    ("pending_drafts", "company_name", "VARCHAR(255)"),
                    ("pending_drafts", "updated_at", "TIMESTAMP DEFAULT NOW()"),
                ]
                for table, col, col_type in migration_columns:
                    try:
                        await conn.execute(f"""
                            ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_type}
                        """)
                    except Exception:
                        pass  # Column may already exist
                
                # Create indexes
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_workflow_runs_status 
                    ON workflow_runs(status)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_workflow_runs_email 
                    ON workflow_runs(contact_email)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_workflow_runs_submission
                    ON workflow_runs(submission_id)
                """)
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_pending_drafts_status 
                    ON pending_drafts(status)
                """)
                
                logger.info("Database tables ensured")
            except Exception as e:
                logger.error(f"Error ensuring tables: {e}")
    
    async def check_duplicate_submission(self, submission_id: str) -> bool:
        """Check if a submission ID has already been processed."""
        if not submission_id:
            return False
        
        async with self.get_connection() as conn:
            if not conn:
                return False
            
            try:
                row = await conn.fetchrow(
                    """
                    SELECT workflow_id, status 
                    FROM workflow_runs 
                    WHERE submission_id = $1
                    ORDER BY started_at DESC
                    LIMIT 1
                    """,
                    submission_id,
                )
                
                if row:
                    logger.warning(f"Duplicate submission detected: {submission_id} (workflow: {row['workflow_id']}, status: {row['status']})")
                    return True
                return False
            except Exception as e:
                logger.error(f"Error checking duplicate: {e}")
                return False
    
    async def check_recent_email_workflow(self, email: str, hours: int = 24) -> bool:
        """Check if we've already processed a workflow for this email recently."""
        if not email:
            return False
        
        async with self.get_connection() as conn:
            if not conn:
                return False
            
            try:
                row = await conn.fetchrow(
                    """
                    SELECT workflow_id, status, started_at
                    FROM workflow_runs 
                    WHERE contact_email = $1
                    AND started_at > NOW() - INTERVAL '1 hour' * $2
                    ORDER BY started_at DESC
                    LIMIT 1
                    """,
                    email,
                    hours,
                )
                
                if row:
                    logger.info(f"Recent workflow found for {email}: {row['workflow_id']} ({row['status']})")
                    return True
                return False
            except Exception as e:
                logger.error(f"Error checking recent email workflow: {e}")
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
                
                # Ensure status is a string
                status_str = str(status) if status else 'unknown'
                
                await conn.execute(
                    """
                    UPDATE workflow_runs
                    SET status = $2::VARCHAR,
                        draft_id = COALESCE($3::VARCHAR, draft_id),
                        steps_completed = COALESCE($4::jsonb, steps_completed),
                        error_message = $5::TEXT,
                        completed_at = CASE WHEN $2::VARCHAR IN ('success', 'failed') THEN NOW() ELSE completed_at END
                    WHERE workflow_id = $1
                    """,
                    workflow_id,
                    status_str,
                    draft_id,
                    steps_json,
                    error_message,
                )
                logger.info(f"Updated workflow run {workflow_id}: status={status_str}")
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
    
    # ==================== Pending Drafts Management ====================
    
    async def save_pending_draft(
        self,
        draft_id: str,
        gmail_draft_id: str,
        recipient: str,
        subject: str,
        body: str,
        workflow_id: Optional[str] = None,
        contact_id: Optional[str] = None,
        company_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Save a pending draft to the database."""
        async with self.get_connection() as conn:
            if not conn:
                logger.error("No database connection for save_pending_draft")
                return False
            
            try:
                import json
                meta_json = json.dumps(metadata) if metadata else None
                
                await conn.execute(
                    """
                    INSERT INTO pending_drafts (
                        draft_id, gmail_draft_id, recipient, subject, body,
                        status, workflow_id, contact_id, company_name, metadata
                    ) VALUES ($1, $2, $3, $4, $5, 'pending', $6, $7, $8, $9::jsonb)
                    ON CONFLICT (draft_id) DO UPDATE SET
                        gmail_draft_id = EXCLUDED.gmail_draft_id,
                        subject = EXCLUDED.subject,
                        body = EXCLUDED.body,
                        updated_at = NOW()
                    """,
                    draft_id,
                    gmail_draft_id,
                    recipient,
                    subject,
                    body,
                    workflow_id,
                    contact_id,
                    company_name,
                    meta_json,
                )
                logger.info(f"Saved pending draft {draft_id} to database")
                return True
            except Exception as e:
                logger.error(f"Error saving pending draft: {e}")
                return False
    
    async def get_pending_drafts(self, status: str = "pending") -> List[Dict[str, Any]]:
        """Get all pending drafts with a specific status."""
        async with self.get_connection() as conn:
            if not conn:
                return []
            
            try:
                rows = await conn.fetch(
                    """
                    SELECT 
                        draft_id, gmail_draft_id, recipient, subject, body,
                        status, workflow_id, contact_id, company_name, metadata,
                        created_at, updated_at
                    FROM pending_drafts
                    WHERE status = $1
                    ORDER BY created_at DESC
                    """,
                    status,
                )
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Error fetching pending drafts: {e}")
                return []
    
    async def update_draft_status(
        self,
        draft_id: str,
        status: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Update the status of a pending draft."""
        async with self.get_connection() as conn:
            if not conn:
                return False
            
            try:
                result = await conn.execute(
                    """
                    UPDATE pending_drafts
                    SET status = $2, updated_at = NOW()
                    WHERE draft_id = $1
                    """,
                    draft_id,
                    status,
                )
                return "UPDATE 1" in result
            except Exception as e:
                logger.error(f"Error updating draft status: {e}")
                return False

    async def record_draft_send(
        self,
        draft_id: str,
        metadata: Dict[str, Any],
        approved_by: Optional[str] = None,
    ) -> bool:
        """Persist send metadata and mark draft as sent."""
        async with self.get_connection() as conn:
            if not conn:
                return False

            try:
                result = await conn.execute(
                    """
                    UPDATE pending_drafts
                    SET status = 'sent',
                        sent_at = NOW(),
                        approved_by = COALESCE($3, approved_by),
                        metadata = $2,
                        updated_at = NOW()
                    WHERE draft_id = $1
                    """,
                    draft_id,
                    metadata,
                    approved_by,
                )
                return "UPDATE 1" in result
            except Exception as e:
                logger.error(f"Error recording draft send: {e}")
                return False

    async def get_draft_by_id(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific pending draft by ID."""
        async with self.get_connection() as conn:
            if not conn:
                return None
            
            try:
                row = await conn.fetchrow(
                    """
                    SELECT 
                        draft_id, gmail_draft_id, recipient, subject, body,
                        status, workflow_id, contact_id, company_name, metadata,
                        created_at, updated_at
                    FROM pending_drafts
                    WHERE draft_id = $1
                    """,
                    draft_id,
                )
                return dict(row) if row else None
            except Exception as e:
                logger.error(f"Error fetching draft by id: {e}")
                return None
    
    async def delete_draft(self, draft_id: str) -> bool:
        """Delete a pending draft."""
        async with self.get_connection() as conn:
            if not conn:
                return False
            
            try:
                result = await conn.execute(
                    "DELETE FROM pending_drafts WHERE draft_id = $1",
                    draft_id,
                )
                return "DELETE 1" in result
            except Exception as e:
                logger.error(f"Error deleting draft: {e}")
                return False
    
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
