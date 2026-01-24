"""Add composite index and deduplication support for signals

Revision ID: 20260124_signals_idx
Revises: 20260124_signals
Create Date: 2026-01-24
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260124_signals_idx"
down_revision = "20260124_signals"
branch_labels = None
depends_on = None


def upgrade():
    # Add composite index for source + processed_at queries
    # Useful for: "get all processed signals from hubspot"
    op.create_index(
        "ix_signals_source_processed",
        "signals",
        ["source", "processed_at"],
    )
    
    # Add payload_hash column for deduplication
    op.add_column(
        "signals",
        sa.Column("payload_hash", sa.String(64), nullable=True),
    )
    
    # Add index on payload_hash + source for fast dedup lookups
    op.create_index(
        "ix_signals_dedup",
        "signals",
        ["source", "payload_hash", "created_at"],
    )


def downgrade():
    op.drop_index("ix_signals_dedup", table_name="signals")
    op.drop_column("signals", "payload_hash")
    op.drop_index("ix_signals_source_processed", table_name="signals")
