"""Add new fields to command_queue_items for CaseyOS Sprint 2

Revision ID: 20260125_command_queue_v2
Revises: 20260124_users
Create Date: 2026-01-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260125_command_queue_v2"
down_revision = "20260124_users"
branch_labels = None
depends_on = None


def upgrade():
    """Add new fields to command_queue_items for Today's Moves UI."""
    
    # Add title - required field for human-readable context
    op.add_column(
        "command_queue_items",
        sa.Column("title", sa.String(length=256), nullable=True)
    )
    
    # Add description for additional context
    op.add_column(
        "command_queue_items",
        sa.Column("description", sa.Text(), nullable=True)
    )
    
    # Add reasoning - why this action matters
    op.add_column(
        "command_queue_items",
        sa.Column("reasoning", sa.Text(), nullable=True)
    )
    
    # Add drivers - JSONB for score breakdown {"urgency": 8, "revenue": 9}
    op.add_column(
        "command_queue_items",
        sa.Column("drivers", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    
    # Add HubSpot reference IDs
    op.add_column(
        "command_queue_items",
        sa.Column("contact_id", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "command_queue_items",
        sa.Column("deal_id", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "command_queue_items",
        sa.Column("company_id", sa.String(length=64), nullable=True)
    )
    
    # Add snooze and completion tracking
    op.add_column(
        "command_queue_items",
        sa.Column("snoozed_until", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "command_queue_items",
        sa.Column("completed_at", sa.DateTime(), nullable=True)
    )
    
    # Add indexes for HubSpot lookups
    op.create_index("ix_command_queue_items_contact_id", "command_queue_items", ["contact_id"])
    op.create_index("ix_command_queue_items_deal_id", "command_queue_items", ["deal_id"])
    op.create_index("ix_command_queue_items_company_id", "command_queue_items", ["company_id"])
    
    # Add FK constraint for recommendation_id (if not exists)
    op.create_foreign_key(
        "fk_command_queue_recommendation",
        "command_queue_items",
        "action_recommendations",
        ["recommendation_id"],
        ["id"],
        ondelete="SET NULL"
    )
    
    # Expand owner column to 128 chars for email addresses
    op.alter_column(
        "command_queue_items",
        "owner",
        type_=sa.String(length=128)
    )
    
    # Backfill title for any existing rows (use action_type as fallback)
    op.execute("""
        UPDATE command_queue_items 
        SET title = COALESCE(
            action_context->>'title',
            INITCAP(REPLACE(action_type, '_', ' '))
        )
        WHERE title IS NULL
    """)
    
    # Ensure ALL rows have titles before making non-nullable (safety net)
    op.execute("""
        UPDATE command_queue_items 
        SET title = 'Untitled'
        WHERE title IS NULL
    """)
    
    # Now make title non-nullable
    op.alter_column("command_queue_items", "title", nullable=False)


def downgrade():
    """Remove Sprint 2 additions."""
    
    # Drop FK constraint
    op.drop_constraint("fk_command_queue_recommendation", "command_queue_items", type_="foreignkey")
    
    # Drop indexes
    op.drop_index("ix_command_queue_items_company_id", table_name="command_queue_items")
    op.drop_index("ix_command_queue_items_deal_id", table_name="command_queue_items")
    op.drop_index("ix_command_queue_items_contact_id", table_name="command_queue_items")
    
    # Drop columns
    op.drop_column("command_queue_items", "completed_at")
    op.drop_column("command_queue_items", "snoozed_until")
    op.drop_column("command_queue_items", "company_id")
    op.drop_column("command_queue_items", "deal_id")
    op.drop_column("command_queue_items", "contact_id")
    op.drop_column("command_queue_items", "drivers")
    op.drop_column("command_queue_items", "reasoning")
    op.drop_column("command_queue_items", "description")
    op.drop_column("command_queue_items", "title")
    
    # Revert owner column size
    op.alter_column(
        "command_queue_items",
        "owner",
        type_=sa.String(length=64)
    )
