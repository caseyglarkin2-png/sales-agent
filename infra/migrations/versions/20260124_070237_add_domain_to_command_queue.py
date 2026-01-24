"""Add domain field to command_queue_items.

Revision ID: add_domain_to_queue
Revises: auto
Create Date: 2026-01-24

Sprint 12: GTM Domain Expansion
- Adds domain column to command_queue_items table
- Default value is 'sales' for backward compatibility
"""
from alembic import op
import sqlalchemy as sa


# Revision identifiers
revision = 'add_domain_to_queue'
down_revision = None  # Will be updated by alembic
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add domain column with default value
    op.add_column(
        'command_queue_items',
        sa.Column('domain', sa.String(32), nullable=True, server_default='sales')
    )
    
    # Create index for domain filtering
    op.create_index(
        'ix_command_queue_items_domain',
        'command_queue_items',
        ['domain']
    )
    
    # Update existing rows to have 'sales' domain
    op.execute("UPDATE command_queue_items SET domain = 'sales' WHERE domain IS NULL")
    
    # Make column non-nullable after setting defaults
    op.alter_column('command_queue_items', 'domain', nullable=False)


def downgrade() -> None:
    op.drop_index('ix_command_queue_items_domain', table_name='command_queue_items')
    op.drop_column('command_queue_items', 'domain')
