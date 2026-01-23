"""Debug endpoint to check database state."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.deps import get_db_session
from src.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/db-tables")
async def get_db_tables(db: AsyncSession = Depends(get_db_session)):
    """List all tables in the database."""
    result = await db.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
    )
    tables = [row[0] for row in result.fetchall()]
    
    # Check alembic version
    version_result = await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
    version = version_result.scalar_one_or_none()
    
    return {
        "migration_version": version,
        "table_count": len(tables),
        "tables": tables
    }


@router.post("/create-workflow-tables")
async def create_workflow_tables(db: AsyncSession = Depends(get_db_session)):
    """Create missing workflow tables."""
    try:
        # Drop existing tables if they exist (CASCADE to handle foreign keys)
        await db.execute(text("DROP TABLE IF EXISTS workflow_errors CASCADE"))
        await db.execute(text("DROP TABLE IF EXISTS hubspot_tasks CASCADE"))
        await db.execute(text("DROP TABLE IF EXISTS draft_emails CASCADE"))
        await db.execute(text("DROP TABLE IF EXISTS workflows CASCADE"))
        await db.execute(text("DROP TABLE IF EXISTS form_submissions CASCADE"))
        
        # Drop and recreate enum types
        await db.execute(text("DROP TYPE IF EXISTS workflowstatus CASCADE"))
        await db.execute(text("DROP TYPE IF EXISTS workflowmode CASCADE"))
        
        # Enable UUID extension
        await db.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        
        # Create enum types (use Python enum values - lowercase)
        await db.execute(text("CREATE TYPE workflowstatus AS ENUM ('triggered', 'processing', 'completed', 'failed')"))
        await db.execute(text("CREATE TYPE workflowmode AS ENUM ('DRAFT_ONLY', 'SEND')"))
        
        logger.info("Created enum types with values: workflowstatus={'triggered','processing','completed','failed'}, workflowmode={'DRAFT_ONLY','SEND'}")
        
        # Create form_submissions table
        await db.execute(text("""
            CREATE TABLE form_submissions (
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
        await db.execute(text("CREATE INDEX IF NOT EXISTS ix_form_submissions_form_submission_id ON form_submissions (form_submission_id)"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS ix_form_submissions_prospect_email ON form_submissions (prospect_email)"))
        
        # Create workflows table
        await db.execute(text("""
            CREATE TABLE workflows (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                form_submission_id UUID NOT NULL REFERENCES form_submissions(id) ON DELETE CASCADE,
                status workflowstatus NOT NULL DEFAULT 'triggered',
                mode workflowmode NOT NULL DEFAULT 'DRAFT_ONLY',
                started_at TIMESTAMP NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMP,
                error_message TEXT,
                error_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        await db.execute(text("CREATE INDEX IF NOT EXISTS ix_workflows_form_submission_id ON workflows (form_submission_id)"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS ix_workflows_status ON workflows (status)"))
        await db.execute(text("CREATE INDEX IF NOT EXISTS ix_workflows_created_at ON workflows (created_at)"))
        
        # Create draft_emails table
        await db.execute(text("""
            CREATE TABLE draft_emails (
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
        await db.execute(text("CREATE INDEX IF NOT EXISTS ix_draft_emails_workflow_id ON draft_emails (workflow_id)"))
        
        # Create hubspot_tasks table
        await db.execute(text("""
            CREATE TABLE hubspot_tasks (
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
        await db.execute(text("CREATE INDEX IF NOT EXISTS ix_hubspot_tasks_workflow_id ON hubspot_tasks (workflow_id)"))
        
        # Create workflow_errors table
        await db.execute(text("""
            CREATE TABLE workflow_errors (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
                error_type VARCHAR(100),
                error_message TEXT,
                stack_trace TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        await db.execute(text("CREATE INDEX IF NOT EXISTS ix_workflow_errors_workflow_id ON workflow_errors (workflow_id)"))
        
        await db.commit()
        
        logger.info("Successfully created all workflow tables")
        return {
            "success": True,
            "message": "All workflow tables created successfully",
            "tables_created": [
                "form_submissions",
                "workflows",
                "draft_emails",
                "hubspot_tasks",
                "workflow_errors"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to create workflow tables: {e}")
        await db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
