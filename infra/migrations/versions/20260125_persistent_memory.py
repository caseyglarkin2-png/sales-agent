"""Add persistent memory tables for Jarvis.

Revision ID: 20260125_persistent_memory
Revises: 20260125_command_queue_v2
Create Date: 2026-01-25 10:00:00.000000

This migration adds:
- jarvis_sessions: Persistent sessions with active context
- conversation_memory: Individual messages with embeddings
- memory_summaries: Compressed summaries of old conversations
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260125_persistent_memory'
down_revision = '20260125_command_queue_v2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create jarvis_sessions table
    op.create_table(
        'jarvis_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('session_name', sa.String(255), default='default'),
        sa.Column('active_context', postgresql.JSONB, default={}),
        sa.Column('preferences', postgresql.JSONB, default={}),
        sa.Column('last_topic', sa.String(500), nullable=True),
        sa.Column('current_focus', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('message_count', sa.Integer, default=0),
        sa.Column('last_active', sa.DateTime, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create indexes for jarvis_sessions
    op.create_index('ix_jarvis_sessions_user_id', 'jarvis_sessions', ['user_id'])
    op.create_index('ix_jarvis_sessions_user_active', 'jarvis_sessions', ['user_id', 'is_active'])
    op.create_index('ix_jarvis_sessions_last_active', 'jarvis_sessions', ['last_active'])
    
    # Create conversation_memory table
    op.create_table(
        'conversation_memory',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('jarvis_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('embedding', postgresql.JSONB, nullable=True),
        sa.Column('metadata', postgresql.JSONB, default={}),
        sa.Column('parent_message_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('conversation_memory.id'), nullable=True),
        sa.Column('token_count', sa.Integer, nullable=True),
        sa.Column('importance', sa.Integer, default=50),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create indexes for conversation_memory
    op.create_index('ix_conversation_memory_session_created', 'conversation_memory', 
                    ['session_id', 'created_at'])
    op.create_index('ix_conversation_memory_role', 'conversation_memory', ['role'])
    op.create_index('ix_conversation_memory_importance', 'conversation_memory', ['importance'])
    
    # Create memory_summaries table
    op.create_table(
        'memory_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('jarvis_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('summary', sa.Text, nullable=False),
        sa.Column('key_facts', postgresql.JSONB, default=[]),
        sa.Column('start_date', sa.DateTime, nullable=False),
        sa.Column('end_date', sa.DateTime, nullable=False),
        sa.Column('message_count', sa.Integer, default=0),
        sa.Column('embedding', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create indexes for memory_summaries
    op.create_index('ix_memory_summaries_session', 'memory_summaries', ['session_id'])
    op.create_index('ix_memory_summaries_date_range', 'memory_summaries',
                    ['session_id', 'start_date', 'end_date'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_memory_summaries_date_range', table_name='memory_summaries')
    op.drop_index('ix_memory_summaries_session', table_name='memory_summaries')
    op.drop_table('memory_summaries')
    
    op.drop_index('ix_conversation_memory_importance', table_name='conversation_memory')
    op.drop_index('ix_conversation_memory_role', table_name='conversation_memory')
    op.drop_index('ix_conversation_memory_session_created', table_name='conversation_memory')
    op.drop_table('conversation_memory')
    
    op.drop_index('ix_jarvis_sessions_last_active', table_name='jarvis_sessions')
    op.drop_index('ix_jarvis_sessions_user_active', table_name='jarvis_sessions')
    op.drop_index('ix_jarvis_sessions_user_id', table_name='jarvis_sessions')
    op.drop_table('jarvis_sessions')
