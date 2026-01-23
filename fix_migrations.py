#!/usr/bin/env python3
"""Manually run missing migrations 001 and 002."""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.config import get_settings

async def run_missing_migrations():
    """Run migrations 001 and 002 manually."""
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url)
    
    print("🔧 Running missing migrations...")
    
    async with engine.begin() as conn:
        # Enable UUID extension
        print("📦 Enabling uuid-ossp extension...")
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        
        # Create form_submissions table from migration 002
        print("📦 Creating form_submissions table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS form_submissions (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                portal_id INTEGER NOT NULL,
                form_id VARCHAR(255) NOT NULL,
                form_submission_id VARCHAR(255) NOT NULL UNIQUE,
                prospect_email VARCHAR(255) NOT NULL,
                prospect_first_name VARCHAR(255),
                prospect_last_name VARCHAR(255),
                prospect_company VARCHAR(255),
                prospect_phone VARCHAR(100),
                prospect_title VARCHAR(255),
                raw_payload JSONB,
                hubspot_contact_id VARCHAR(255),
                hubspot_company_id VARCHAR(255),
                processed INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_form_submissions_form_submission_id ON form_submissions (form_submission_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_form_submissions_prospect_email ON form_submissions (prospect_email)"))
        
        # Create workflows table from migration 002
        print("📦 Creating workflows table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workflows (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                form_submission_id UUID NOT NULL REFERENCES form_submissions(id) ON DELETE CASCADE,
                status VARCHAR(50) NOT NULL DEFAULT 'triggered',
                mode VARCHAR(50) NOT NULL DEFAULT 'DRAFT_ONLY',
                started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMP,
                error_message TEXT,
                error_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workflows_form_submission_id ON workflows (form_submission_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workflows_status ON workflows (status)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workflows_created_at ON workflows (created_at)"))
        
        # Create draft_emails table
        print("📦 Creating draft_emails table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS draft_emails (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                gmail_draft_id VARCHAR(255),
                subject TEXT,
                body TEXT,
                to_email VARCHAR(255) NOT NULL,
                from_email VARCHAR(255),
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_draft_emails_workflow_id ON draft_emails (workflow_id)"))
        
        # Create hubspot_tasks table
        print("📦 Creating hubspot_tasks table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS hubspot_tasks (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                hubspot_task_id VARCHAR(255) UNIQUE,
                task_type VARCHAR(50),
                subject TEXT,
                notes TEXT,
                status VARCHAR(50),
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_hubspot_tasks_workflow_id ON hubspot_tasks (workflow_id)"))
        
        # Create workflow_errors table
        print("📦 Creating workflow_errors table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workflow_errors (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                error_type VARCHAR(100),
                error_message TEXT,
                stack_trace TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workflow_errors_workflow_id ON workflow_errors (workflow_id)"))
        
        print("✅ All tables created successfully!")
        
    await engine.dispose()
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(run_missing_migrations()))
