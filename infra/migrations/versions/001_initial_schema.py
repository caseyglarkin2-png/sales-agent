"""Initial schema with all tables.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-01-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create hubspot_companies table
    op.create_table(
        'hubspot_companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('hubspot_company_id', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(512), nullable=False),
        sa.Column('domain', sa.String(255), nullable=True),
        sa.Column('industry', sa.String(255), nullable=True),
        sa.Column('custom_properties', postgresql.JSONB, nullable=True),
        sa.Column('synced_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_hubspot_companies_domain', 'hubspot_companies', ['domain'])

    # Create hubspot_contacts table
    op.create_table(
        'hubspot_contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('hubspot_contact_id', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('firstname', sa.String(255), nullable=True),
        sa.Column('lastname', sa.String(255), nullable=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hubspot_companies.id'), nullable=True),
        sa.Column('custom_properties', postgresql.JSONB, nullable=True),
        sa.Column('synced_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_hubspot_contacts_email', 'hubspot_contacts', ['email'])

    # Create hubspot_deals table
    op.create_table(
        'hubspot_deals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('hubspot_deal_id', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('dealname', sa.String(512), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hubspot_companies.id'), nullable=True),
        sa.Column('stage', sa.String(255), nullable=True),
        sa.Column('amount', sa.String(255), nullable=True),
        sa.Column('synced_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
    )

    # Create hubspot_form_submissions table
    op.create_table(
        'hubspot_form_submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('submission_id', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('form_id', sa.String(255), nullable=False, index=True),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hubspot_contacts.id'), nullable=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hubspot_companies.id'), nullable=True),
        sa.Column('fields', postgresql.JSONB, nullable=True),
        sa.Column('submitted_at', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_hubspot_form_submissions_form_id_submitted', 'hubspot_form_submissions', ['form_id', 'submitted_at'])

    # Create threads table
    op.create_table(
        'threads',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('gmail_thread_id', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hubspot_company_id', sa.String(255), nullable=True, index=True),
        sa.Column('hubspot_contact_id', sa.String(255), nullable=True, index=True),
        sa.Column('subject', sa.String(512), nullable=False),
        sa.Column('last_message_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_threads_hubspot_company_id', 'threads', ['hubspot_company_id'])
    op.create_index('ix_threads_hubspot_contact_id', 'threads', ['hubspot_contact_id'])

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('gmail_message_id', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('gmail_thread_id', sa.String(255), nullable=False, index=True),
        sa.Column('sender', sa.String(255), nullable=False),
        sa.Column('recipient', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(512), nullable=False),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float), nullable=True),
        sa.Column('gmail_metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_messages_gmail_thread_id', 'messages', ['gmail_thread_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])

    # Create agent_tasks table
    op.create_table(
        'agent_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('hubspot_task_id', sa.String(255), nullable=True, unique=True),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hubspot_contacts.id'), nullable=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hubspot_companies.id'), nullable=True),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('body', sa.Text, nullable=True),
        sa.Column('type', sa.String(255), nullable=True),
        sa.Column('due_date', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
    )

    # Create agent_notes table
    op.create_table(
        'agent_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('hubspot_note_id', sa.String(255), nullable=True, unique=True),
        sa.Column('contact_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hubspot_contacts.id'), nullable=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hubspot_companies.id'), nullable=True),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('context_json', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
    )

    # Create draft_audit_log table (immutable)
    op.create_table(
        'draft_audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('actor', sa.String(255), nullable=False),
        sa.Column('draft_id', sa.String(255), nullable=False, index=True),
        sa.Column('contact_id', sa.String(255), nullable=False, index=True),
        sa.Column('company_id', sa.String(255), nullable=False, index=True),
        sa.Column('mode', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()'), index=True),
    )
    op.create_index('ix_draft_audit_log_draft_id', 'draft_audit_log', ['draft_id'])
    op.create_index('ix_draft_audit_log_contact_id', 'draft_audit_log', ['contact_id'])
    op.create_index('ix_draft_audit_log_company_id', 'draft_audit_log', ['company_id'])
    op.create_index('ix_draft_audit_log_created_at', 'draft_audit_log', ['created_at'])

    # Create workflow_runs table (for tracking orchestrator executions)
    op.create_table(
        'workflow_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('workflow_id', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('workflow_type', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('submission_id', sa.String(255), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('company_name', sa.String(512), nullable=True),
        sa.Column('draft_id', sa.String(255), nullable=True),
        sa.Column('steps_completed', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('started_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )
    op.create_index('ix_workflow_runs_status', 'workflow_runs', ['status'])
    op.create_index('ix_workflow_runs_started_at', 'workflow_runs', ['started_at'])


def downgrade() -> None:
    op.drop_table('workflow_runs')
    op.drop_table('draft_audit_log')
    op.drop_table('agent_notes')
    op.drop_table('agent_tasks')
    op.drop_table('messages')
    op.drop_table('threads')
    op.drop_table('hubspot_form_submissions')
    op.drop_table('hubspot_deals')
    op.drop_table('hubspot_contacts')
    op.drop_table('hubspot_companies')
