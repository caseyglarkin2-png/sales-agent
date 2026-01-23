"""Add workflow persistence schema.

Revision ID: 002_workflow_persistence
Revises: 001_initial_schema
Create Date: 2026-01-23

Adds tables for workflow execution tracking, form submissions, draft emails,
HubSpot tasks, and error tracking with retry logic.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_workflow_persistence'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create workflow persistence tables."""
    
    # Create form_submissions table
    op.create_table(
        'form_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('portal_id', sa.Integer, nullable=False),
        sa.Column('form_id', sa.String(255), nullable=False),
        sa.Column('form_submission_id', sa.String(255), nullable=False, unique=True),
        sa.Column('prospect_email', sa.String(255), nullable=False),
        sa.Column('prospect_first_name', sa.String(255), nullable=True),
        sa.Column('prospect_last_name', sa.String(255), nullable=True),
        sa.Column('prospect_company', sa.String(255), nullable=True),
        sa.Column('prospect_phone', sa.String(100), nullable=True),
        sa.Column('prospect_title', sa.String(255), nullable=True),
        sa.Column('raw_payload', postgresql.JSONB, nullable=True),
        sa.Column('hubspot_contact_id', sa.String(255), nullable=True),
        sa.Column('hubspot_company_id', sa.String(255), nullable=True),
        sa.Column('processed', sa.Integer, nullable=False, server_default='0'),
        sa.Column('processing_error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('received_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('processed_at', sa.DateTime, nullable=True),
        sa.UniqueConstraint('portal_id', 'form_id', 'form_submission_id', name='uq_form_submission')
    )
    
    # Create indexes for form_submissions
    op.create_index('idx_form_submissions_email', 'form_submissions', ['prospect_email'])
    op.create_index('idx_form_submissions_received', 'form_submissions', ['received_at'])
    op.create_index('idx_form_submissions_portal_form', 'form_submissions', ['portal_id', 'form_id'])
    op.create_index('idx_form_submissions_hubspot_contact', 'form_submissions', ['hubspot_contact_id'])
    op.create_index('idx_form_submissions_processing_state', 'form_submissions', ['processed', 'received_at'])
    op.create_index('idx_form_submissions_created_at', 'form_submissions', ['created_at'])
    
    # Create workflows table
    op.create_table(
        'workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('form_submission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='triggered'),
        sa.Column('mode', sa.String(20), nullable=False, server_default='DRAFT_ONLY'),
        sa.Column('started_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('error_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['form_submission_id'], ['form_submissions.id'], ondelete='CASCADE')
    )
    
    # Create indexes for workflows
    op.create_index('idx_workflows_status', 'workflows', ['status'])
    op.create_index('idx_workflows_status_created', 'workflows', ['status', 'created_at'])
    op.create_index('idx_workflows_form_submission', 'workflows', ['form_submission_id'])
    op.create_index('idx_workflows_created_at', 'workflows', ['created_at'])
    
    # Create draft_emails table
    op.create_table(
        'draft_emails',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('form_submission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('gmail_draft_id', sa.String(255), nullable=True),
        sa.Column('recipient_email', sa.String(255), nullable=False),
        sa.Column('subject', sa.Text, nullable=False),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('rejected_at', sa.DateTime, nullable=True),
        sa.Column('rejected_by', sa.String(255), nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('sent_at', sa.DateTime, nullable=True),
        sa.Column('gmail_message_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['form_submission_id'], ['form_submissions.id'], ondelete='CASCADE')
    )
    
    # Create indexes for draft_emails
    op.create_index('idx_draft_emails_workflow', 'draft_emails', ['workflow_id'])
    op.create_index('idx_draft_emails_recipient', 'draft_emails', ['recipient_email'])
    op.create_index('idx_draft_emails_gmail_draft', 'draft_emails', ['gmail_draft_id'])
    op.create_index('idx_draft_emails_approval_status', 'draft_emails', ['approved_at', 'sent_at'])
    op.create_index('idx_draft_emails_created_at', 'draft_emails', ['created_at'])
    op.create_index('idx_draft_emails_sent_at', 'draft_emails', ['sent_at'])
    
    # Create hubspot_tasks table
    op.create_table(
        'hubspot_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hubspot_task_id', sa.String(255), nullable=False, unique=True),
        sa.Column('contact_id', sa.String(255), nullable=False),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('body', sa.Text, nullable=True),
        sa.Column('due_date', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('hubspot_created_at', sa.DateTime, nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE')
    )
    
    # Create indexes for hubspot_tasks
    op.create_index('idx_hubspot_tasks_workflow', 'hubspot_tasks', ['workflow_id'])
    op.create_index('idx_hubspot_tasks_contact', 'hubspot_tasks', ['contact_id'])
    op.create_index('idx_hubspot_tasks_hubspot_task_id', 'hubspot_tasks', ['hubspot_task_id'])
    
    # Create workflow_errors table
    op.create_table(
        'workflow_errors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('error_type', sa.String(255), nullable=False),
        sa.Column('error_message', sa.Text, nullable=False),
        sa.Column('traceback', sa.Text, nullable=True),
        sa.Column('step_name', sa.String(255), nullable=True),
        sa.Column('retry_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer, nullable=False, server_default='3'),
        sa.Column('next_retry_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('resolved_at', sa.DateTime, nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE')
    )
    
    # Create indexes for workflow_errors
    op.create_index('idx_workflow_errors_workflow', 'workflow_errors', ['workflow_id'])
    op.create_index('idx_workflow_errors_error_type', 'workflow_errors', ['error_type'])
    op.create_index('idx_workflow_errors_step_name', 'workflow_errors', ['step_name'])
    op.create_index('idx_workflow_errors_retry', 'workflow_errors', ['next_retry_at', 'retry_count'])
    op.create_index('idx_workflow_errors_type_step', 'workflow_errors', ['error_type', 'step_name'])
    op.create_index('idx_workflow_errors_created_at', 'workflow_errors', ['created_at'])


def downgrade() -> None:
    """Drop workflow persistence tables."""
    op.drop_table('workflow_errors')
    op.drop_table('hubspot_tasks')
    op.drop_table('draft_emails')
    op.drop_table('workflows')
    op.drop_table('form_submissions')
