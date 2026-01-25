"""Add content memory for Content Engine.

Revision ID: 20260125_content_memory
Revises: 20260125_notifications
Create Date: 2026-01-25 14:00:00.000000

This migration adds:
- content_memory: Ingested content (YouTube, Drive, etc)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260125_content_memory'
down_revision = '20260125_notifications'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create content_memory table
    op.create_table(
        'content_memory',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.String(length=255), nullable=False),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('title', sa.String(length=1000), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('embedding', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add index for source lookups
    op.create_index(
        'ix_content_memory_source',
        'content_memory',
        ['source_type', 'source_id'],
        unique=False
    )
    
    # Add index for vector search (placeholder JSONB logic for now)
    # When pgvector is fully enabled, this would be customized


def downgrade() -> None:
    op.drop_index('ix_content_memory_source', table_name='content_memory')
    op.drop_table('content_memory')
