"""Add signals table for signal ingestion framework

Revision ID: 20260124_signals
Revises: 20260123_command_queue
Create Date: 2026-01-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260124_signals"
down_revision = "20260123_command_queue"
branch_labels = None
depends_on = None


def upgrade():
    # Create the enum type first
    signal_source_enum = postgresql.ENUM(
        'form', 'hubspot', 'gmail', 'manual',
        name='signal_source_enum',
        create_type=True
    )
    signal_source_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "signals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "source",
            signal_source_enum,
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}"
        ),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("recommendation_id", sa.String(length=36), nullable=True),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # Create indexes for common query patterns
    op.create_index("ix_signals_source", "signals", ["source"])
    op.create_index("ix_signals_event_type", "signals", ["event_type"])
    op.create_index("ix_signals_processed_at", "signals", ["processed_at"])
    op.create_index("ix_signals_recommendation_id", "signals", ["recommendation_id"])
    op.create_index("ix_signals_source_id", "signals", ["source_id"])
    op.create_index("ix_signals_created_at", "signals", ["created_at"])
    
    # Composite index for finding unprocessed signals by source
    op.create_index(
        "ix_signals_source_unprocessed",
        "signals",
        ["source", "created_at"],
        postgresql_where=sa.text("processed_at IS NULL")
    )


def downgrade():
    op.drop_index("ix_signals_source_unprocessed", table_name="signals")
    op.drop_index("ix_signals_created_at", table_name="signals")
    op.drop_index("ix_signals_source_id", table_name="signals")
    op.drop_index("ix_signals_recommendation_id", table_name="signals")
    op.drop_index("ix_signals_processed_at", table_name="signals")
    op.drop_index("ix_signals_event_type", table_name="signals")
    op.drop_index("ix_signals_source", table_name="signals")
    op.drop_table("signals")
    
    # Drop the enum type
    postgresql.ENUM(name='signal_source_enum').drop(op.get_bind(), checkfirst=True)
