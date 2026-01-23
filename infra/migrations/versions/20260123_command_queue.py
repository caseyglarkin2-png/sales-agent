"""Add command queue and action recommendation tables

Revision ID: 20260123_command_queue
Revises: 004
Create Date: 2026-01-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260123_command_queue"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "action_recommendations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("aps_score", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("revenue_impact", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("urgency_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("effort_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("strategic_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "command_queue_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("priority_score", sa.Float(), index=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("action_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("owner", sa.String(length=64), nullable=False, server_default="casey"),
        sa.Column("due_by", sa.DateTime(), nullable=True),
        sa.Column("recommendation_id", sa.String(length=36), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("outcome", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_index("ix_command_queue_items_priority", "command_queue_items", ["priority_score"])
    op.create_index("ix_command_queue_items_status", "command_queue_items", ["status"])


def downgrade():
    op.drop_index("ix_command_queue_items_status", table_name="command_queue_items")
    op.drop_index("ix_command_queue_items_priority", table_name="command_queue_items")
    op.drop_table("command_queue_items")
    op.drop_table("action_recommendations")
