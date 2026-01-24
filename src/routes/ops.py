"""Operational endpoints (admin-only)."""

import subprocess
from fastapi import APIRouter, Depends, HTTPException

from src.security.auth import require_admin_role
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["Ops"], dependencies=[Depends(require_admin_role)])


@router.post("/test-error")
async def trigger_test_error() -> dict:
    """Trigger a test exception to verify Sentry wiring (admin-only)."""
    raise RuntimeError("Sentry test error: manual trigger")


@router.post("/ops/run-migrations")
async def run_migrations() -> dict:
    """Run database migrations (admin-only).
    
    Executes alembic upgrade head to apply any pending migrations.
    """
    try:
        logger.info("Running database migrations...")
        
        # Run alembic upgrade head
        result = subprocess.run(
            ["python", "-m", "alembic", "-c", "infra/alembic.ini", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/app",  # Railway container path
        )
        
        if result.returncode != 0:
            logger.error(f"Migration failed: {result.stderr}")
            return {
                "status": "error",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        
        logger.info("Migrations completed successfully")
        return {
            "status": "success",
            "returncode": 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        
    except subprocess.TimeoutExpired:
        logger.error("Migration timed out")
        raise HTTPException(status_code=504, detail="Migration timed out")
    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ops/migration-status")
async def get_migration_status() -> dict:
    """Get current migration status (admin-only)."""
    try:
        result = subprocess.run(
            ["python", "-m", "alembic", "-c", "infra/alembic.ini", "current"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/app",
        )
        
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "current": result.stdout.strip(),
            "stderr": result.stderr if result.returncode != 0 else None,
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/ops/create-signals-table")
async def create_signals_table() -> dict:
    """Create signals table directly (emergency fallback)."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    import os
    
    try:
        database_url = os.getenv("DATABASE_URL", "")
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            
        engine = create_async_engine(database_url)
        
        async with engine.begin() as conn:
            # Create enum type
            await conn.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE signal_source_enum AS ENUM ('form', 'hubspot', 'gmail', 'manual');
                EXCEPTION
                    WHEN duplicate_object THEN NULL;
                END $$;
            """))
            
            # Create table
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS signals (
                    id VARCHAR(36) PRIMARY KEY,
                    source signal_source_enum NOT NULL,
                    event_type VARCHAR(64) NOT NULL,
                    payload JSONB NOT NULL DEFAULT '{}',
                    processed_at TIMESTAMP,
                    recommendation_id VARCHAR(36),
                    source_id VARCHAR(128),
                    created_at TIMESTAMP NOT NULL
                );
            """))
            
            # Create indexes
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_signals_source ON signals(source);"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_signals_event_type ON signals(event_type);"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_signals_processed_at ON signals(processed_at);"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_signals_recommendation_id ON signals(recommendation_id);"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_signals_source_id ON signals(source_id);"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_signals_created_at ON signals(created_at);"))
        
        await engine.dispose()
        
        logger.info("Signals table created successfully")
        return {"status": "success", "message": "Signals table created"}
        
    except Exception as e:
        logger.error(f"Failed to create signals table: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


