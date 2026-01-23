"""Add oauth_tokens table for secure token storage

Revision ID: 004
Revises: 003
Create Date: 2026-01-23 04:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Create oauth_tokens table for encrypted token storage."""
    op.create_table(
        'oauth_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service', sa.String(50), nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('token_type', sa.String(20), nullable=False, server_default='Bearer'),
        sa.Column('scopes', postgresql.JSONB(), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    
    # Create indexes
    op.create_index(
        'idx_oauth_tokens_user_service',
        'oauth_tokens',
        ['user_id', 'service'],
        unique=True
    )
    
    op.create_index(
        'idx_oauth_tokens_expires_at',
        'oauth_tokens',
        ['expires_at'],
        postgresql_where=sa.text('NOT revoked')
    )
    
    op.create_index(
        'idx_oauth_tokens_service',
        'oauth_tokens',
        ['service']
    )


def downgrade():
    """Drop oauth_tokens table and indexes."""
    op.drop_index('idx_oauth_tokens_service', table_name='oauth_tokens')
    op.drop_index('idx_oauth_tokens_expires_at', table_name='oauth_tokens')
    op.drop_index('idx_oauth_tokens_user_service', table_name='oauth_tokens')
    op.drop_table('oauth_tokens')
