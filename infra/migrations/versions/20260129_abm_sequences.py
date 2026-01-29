"""Add ABM campaigns and sequences tables.

Revision ID: 20260129_abm_sequences
Revises: 20260127_agent_executions
Create Date: 2026-01-29

Sprint 62-63: ABM Campaigns and Sequence Automation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260129_abm_sequences"
down_revision = "20260127_agent_executions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ABM Campaigns table
    op.create_table(
        "abm_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), default="draft"),
        sa.Column("target_personas", sa.JSON, nullable=True),
        sa.Column("target_industries", sa.JSON, nullable=True),
        sa.Column("email_template_type", sa.String(100), nullable=True),
        sa.Column("sequence_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("total_accounts", sa.Integer, default=0),
        sa.Column("total_contacts", sa.Integer, default=0),
        sa.Column("emails_generated", sa.Integer, default=0),
        sa.Column("emails_sent", sa.Integer, default=0),
        sa.Column("emails_opened", sa.Integer, default=0),
        sa.Column("emails_replied", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("launched_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_abm_campaigns_status", "abm_campaigns", ["status"])
    op.create_index("ix_abm_campaigns_owner", "abm_campaigns", ["owner_id"])

    # ABM Campaign Accounts table
    op.create_table(
        "abm_campaign_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("abm_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hubspot_companies.id"), nullable=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("company_domain", sa.String(255), nullable=True),
        sa.Column("company_industry", sa.String(255), nullable=True),
        sa.Column("account_context", sa.JSON, nullable=True),
        sa.Column("emails_generated", sa.Integer, default=0),
        sa.Column("emails_sent", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )
    op.create_index("ix_abm_campaign_accounts_campaign", "abm_campaign_accounts", ["campaign_id"])
    op.create_index("ix_abm_campaign_accounts_company", "abm_campaign_accounts", ["company_id"])

    # ABM Campaign Contacts table
    op.create_table(
        "abm_campaign_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("abm_campaign_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hubspot_contacts.id"), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("persona", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )
    op.create_index("ix_abm_campaign_contacts_account", "abm_campaign_contacts", ["account_id"])
    op.create_index("ix_abm_campaign_contacts_email", "abm_campaign_contacts", ["email"])

    # ABM Campaign Emails table
    op.create_table(
        "abm_campaign_emails",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("abm_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("abm_campaign_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("abm_campaign_contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("status", sa.String(50), default="draft"),
        sa.Column("queue_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("personalization_score", sa.Integer, nullable=True),
        sa.Column("sent_at", sa.DateTime, nullable=True),
        sa.Column("opened_at", sa.DateTime, nullable=True),
        sa.Column("replied_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_abm_campaign_emails_campaign", "abm_campaign_emails", ["campaign_id"])
    op.create_index("ix_abm_campaign_emails_status", "abm_campaign_emails", ["status"])

    # Sequences table
    op.create_table(
        "sequences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), default="draft"),
        sa.Column("target_persona", sa.String(100), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("total_enrollments", sa.Integer, default=0),
        sa.Column("active_enrollments", sa.Integer, default=0),
        sa.Column("completed_enrollments", sa.Integer, default=0),
        sa.Column("replied_enrollments", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_sequences_status", "sequences", ["status"])
    op.create_index("ix_sequences_owner", "sequences", ["owner_id"])

    # Sequence Steps table
    op.create_table(
        "sequence_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sequence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sequences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_number", sa.Integer, nullable=False),
        sa.Column("channel", sa.String(50), default="email"),
        sa.Column("delay_days", sa.Integer, default=0),
        sa.Column("delay_hours", sa.Integer, default=0),
        sa.Column("subject_template", sa.String(500), nullable=True),
        sa.Column("body_template", sa.Text, nullable=True),
        sa.Column("task_type", sa.String(100), nullable=True),
        sa.Column("task_description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, default=sa.func.now()),
    )
    op.create_index("ix_sequence_steps_sequence", "sequence_steps", ["sequence_id"])

    # Sequence Enrollments table
    op.create_table(
        "sequence_enrollments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sequence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sequences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hubspot_contacts.id"), nullable=True),
        sa.Column("context", sa.JSON, nullable=True),
        sa.Column("current_step", sa.Integer, default=0),
        sa.Column("status", sa.String(50), default="active"),
        sa.Column("enrolled_at", sa.DateTime, default=sa.func.now()),
        sa.Column("next_step_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("paused_at", sa.DateTime, nullable=True),
        sa.Column("step_history", sa.JSON, nullable=True),
    )
    op.create_index("ix_sequence_enrollments_sequence", "sequence_enrollments", ["sequence_id"])
    op.create_index("ix_sequence_enrollments_status", "sequence_enrollments", ["status"])
    op.create_index("ix_sequence_enrollments_next_step", "sequence_enrollments", ["next_step_at"])
    op.create_index("ix_sequence_enrollments_email", "sequence_enrollments", ["contact_email"])


def downgrade() -> None:
    op.drop_table("sequence_enrollments")
    op.drop_table("sequence_steps")
    op.drop_table("sequences")
    op.drop_table("abm_campaign_emails")
    op.drop_table("abm_campaign_contacts")
    op.drop_table("abm_campaign_accounts")
    op.drop_table("abm_campaigns")
