"""Add auto-approval tables.

Revision ID: 20260125_auto_approval
Revises: 20260125_command_queue_v2
Create Date: 2026-01-25

Sprint 4: Auto-Approval Rules Engine
- AutoApprovalRule: Rule definitions for auto-approving drafts
- ApprovedRecipient: Whitelist of known good recipients
- AutoApprovalLog: Audit trail of all auto-approval decisions
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "20260125_auto_approval"
down_revision = "20260125_command_queue_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create auto-approval tables."""
    
    # AutoApprovalRule - Rule definitions
    op.create_table(
        "auto_approval_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_type", sa.String(50), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("conditions", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("priority", sa.Integer, server_default="100"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(255)),
    )
    
    # ApprovedRecipient - Whitelist of known good recipients
    op.create_table(
        "approved_recipients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("domain", sa.String(255), index=True),
        sa.Column("first_approved_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_sent_at", sa.DateTime),
        sa.Column("total_sends", sa.Integer, server_default="1"),
        sa.Column("total_replies", sa.Integer, server_default="0"),
        sa.Column("added_by", sa.String(255)),
        sa.Column("source_draft_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # AutoApprovalLog - Audit trail of decisions
    op.create_table(
        "auto_approval_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("draft_id", sa.String(255), nullable=False, index=True),
        sa.Column("recipient_email", sa.String(255), nullable=False, index=True),
        sa.Column("decision", sa.String(50), nullable=False, index=True),
        sa.Column("matched_rule_id", sa.String(36)),
        sa.Column("matched_rule_type", sa.String(50)),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("reasoning", sa.Text),
        sa.Column("decision_metadata", postgresql.JSONB),
        sa.Column("evaluated_at", sa.DateTime, server_default=sa.func.now(), index=True),
    )
    
    # Create indexes for common queries
    op.create_index(
        "ix_auto_approval_rules_enabled_priority",
        "auto_approval_rules",
        ["enabled", "priority"],
    )
    op.create_index(
        "ix_auto_approval_logs_decision_date",
        "auto_approval_logs",
        ["decision", "evaluated_at"],
    )


def downgrade() -> None:
    """Drop auto-approval tables."""
    op.drop_index("ix_auto_approval_logs_decision_date", "auto_approval_logs")
    op.drop_index("ix_auto_approval_rules_enabled_priority", "auto_approval_rules")
    op.drop_table("auto_approval_logs")
    op.drop_table("approved_recipients")
    op.drop_table("auto_approval_rules")
