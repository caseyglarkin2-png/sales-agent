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

