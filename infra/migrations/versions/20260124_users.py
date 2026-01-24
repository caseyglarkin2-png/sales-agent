"""Add users and user_sessions tables for CaseyOS Sprint 1

Revision ID: 20260124_users
Revises: 20260124_signals_idx
Create Date: 2026-01-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260124_users'
down_revision = '20260124_signals_idx'
branch_labels = None
depends_on = None


def upgrade():
    """Create users and user_sessions tables for CaseyOS authentication."""
    
    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('picture', sa.Text(), nullable=True),
        
        # Google OAuth tokens
        sa.Column('google_access_token', sa.Text(), nullable=True),
        sa.Column('google_refresh_token', sa.Text(), nullable=True),
        sa.Column('google_token_expiry', sa.DateTime(), nullable=True),
        sa.Column('google_token_scopes', postgresql.JSONB(), nullable=True),
        
        # Account status
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_allowed', sa.Boolean(), nullable=False, server_default='false'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
    )
    
    # Create index on email
    op.create_index('idx_users_email', 'users', ['email'])
    
    # User sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_token', sa.String(255), unique=True, nullable=False),
        
        # Session metadata
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        
        # Expiration
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('last_accessed', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        
        # Foreign key
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Create indexes
    op.create_index('idx_user_sessions_token', 'user_sessions', ['session_token'])
    op.create_index('idx_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_user_sessions_expires', 'user_sessions', ['expires_at'])


def downgrade():
    """Drop users and user_sessions tables."""
    op.drop_index('idx_user_sessions_expires', table_name='user_sessions')
    op.drop_index('idx_user_sessions_user_id', table_name='user_sessions')
    op.drop_index('idx_user_sessions_token', table_name='user_sessions')
    op.drop_table('user_sessions')
    
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
