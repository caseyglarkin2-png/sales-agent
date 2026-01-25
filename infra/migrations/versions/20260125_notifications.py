"""Add notifications table for Jarvis daemon mode.

Revision ID: 20260125_notifications
Revises: 20260125_persistent_memory
Create Date: 2026-01-25 12:00:00.000000

This migration adds:
- jarvis_notifications: Proactive alerts from daemon monitor
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260125_notifications'
down_revision = '20260125_persistent_memory'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create jarvis_notifications table
    op.create_table(
        'jarvis_notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('priority', sa.String(50), default='normal'),
        sa.Column('action_type', sa.String(100), nullable=True),
        sa.Column('action_url', sa.String(500), nullable=True),
        sa.Column('action_data', postgresql.JSONB, default={}),
        sa.Column('is_read', sa.Boolean, default=False),
        sa.Column('is_acknowledged', sa.Boolean, default=False),
        sa.Column('is_actioned', sa.Boolean, default=False),
        sa.Column('delivered_via', postgresql.JSONB, default=[]),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('read_at', sa.DateTime, nullable=True),
        sa.Column('acknowledged_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
    )
    
    # Create indexes
    op.create_index('ix_jarvis_notifications_user_id', 'jarvis_notifications', ['user_id'])
    op.create_index('ix_jarvis_notifications_user_unread', 'jarvis_notifications', ['user_id', 'is_read'])
    op.create_index('ix_jarvis_notifications_priority', 'jarvis_notifications', ['priority', 'created_at'])
    op.create_index('ix_jarvis_notifications_created', 'jarvis_notifications', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_jarvis_notifications_created', table_name='jarvis_notifications')
    op.drop_index('ix_jarvis_notifications_priority', table_name='jarvis_notifications')
    op.drop_index('ix_jarvis_notifications_user_unread', table_name='jarvis_notifications')
    op.drop_index('ix_jarvis_notifications_user_id', table_name='jarvis_notifications')
    op.drop_table('jarvis_notifications')
