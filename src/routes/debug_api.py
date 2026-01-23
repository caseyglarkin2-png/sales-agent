"""Debug endpoint to check database state."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.deps import get_db_session

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
