"""Add training_samples table for voice training enhancement

Revision ID: 003
Revises: 
Create Date: 2026-01-23 03:37:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '003'
down_revision = None  # No dependency on 002 since it may not exist
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create training_samples table for voice training data ingestion."""
    op.create_table(
        'training_samples',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False, comment='drive, hubspot, youtube, upload, link'),
        sa.Column('source_id', sa.String(255), nullable=True, comment='Drive file ID, HubSpot object ID, YouTube video ID'),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('extracted_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('embedding_generated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('voice_profile_id', UUID(as_uuid=True), nullable=True),
        sa.Column('source_metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), onupdate=sa.text('NOW()')),
    )
    
    # Create indexes
    op.create_index('idx_training_samples_user_id', 'training_samples', ['user_id'])
    op.create_index('idx_training_samples_voice_profile_id', 'training_samples', ['voice_profile_id'])
    op.create_index('idx_training_samples_source_type', 'training_samples', ['source_type'])
    op.create_index('idx_training_samples_created_at', 'training_samples', ['created_at'])
    
    # Add foreign key constraint if voice_profiles table exists
    # Note: voice_profiles table may not exist yet, so we'll make this conditional
    # op.create_foreign_key(
    #     'fk_training_samples_voice_profile_id',
    #     'training_samples', 'voice_profiles',
    #     ['voice_profile_id'], ['id'],
    #     ondelete='SET NULL'
    # )


def downgrade() -> None:
    """Drop training_samples table."""
    op.drop_index('idx_training_samples_created_at', 'training_samples')
    op.drop_index('idx_training_samples_source_type', 'training_samples')
    op.drop_index('idx_training_samples_voice_profile_id', 'training_samples')
    op.drop_index('idx_training_samples_user_id', 'training_samples')
    op.drop_table('training_samples')
