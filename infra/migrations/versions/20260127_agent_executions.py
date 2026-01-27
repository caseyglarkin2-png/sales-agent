"""Add agent_executions table.

Revision ID: 20260127_agent_executions
Revises: 20260125_persistent_memory
Create Date: 2026-01-27

Sprint 42.1: Agent Execution Infrastructure
- AgentExecution: Track all agent executions with full audit trail
- Includes input/output JSON, status, duration, error handling
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "20260127_agent_executions"
down_revision = "20260125_persistent_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create agent_executions table."""
    
    op.create_table(
        "agent_executions",
        # Primary key
        sa.Column("id", sa.String(36), primary_key=True),
        
        # Agent identification
        sa.Column("agent_name", sa.String(128), nullable=False, index=True),
        sa.Column("domain", sa.String(64), nullable=False, server_default="unknown"),
        
        # Execution status
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        
        # Input/Output (JSONB for Postgres)
        sa.Column("input_context", postgresql.JSONB, server_default="{}"),
        sa.Column("output_result", postgresql.JSONB, server_default="{}"),
        
        # Error handling
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_traceback", sa.Text, nullable=True),
        
        # Performance metrics
        sa.Column("duration_ms", sa.Integer, nullable=True),
        
        # Timestamps
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        
        # Trigger info
        sa.Column("trigger_source", sa.String(64), nullable=False, server_default="manual"),
        sa.Column("triggered_by", sa.String(128), nullable=True),
        sa.Column("celery_task_id", sa.String(128), nullable=True),
    )
    
    # Composite indexes for common queries
    op.create_index(
        "ix_agent_execution_created_at",
        "agent_executions",
        ["created_at"]
    )
    op.create_index(
        "ix_agent_execution_status",
        "agent_executions",
        ["status"]
    )
    op.create_index(
        "ix_agent_execution_agent_status",
        "agent_executions",
        ["agent_name", "status"]
    )


def downgrade() -> None:
    """Drop agent_executions table."""
    op.drop_index("ix_agent_execution_agent_status", table_name="agent_executions")
    op.drop_index("ix_agent_execution_status", table_name="agent_executions")
    op.drop_index("ix_agent_execution_created_at", table_name="agent_executions")
    op.drop_table("agent_executions")
