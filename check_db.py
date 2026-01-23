#!/usr/bin/env python3
"""Check database state."""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from src.config import get_settings

async def check_db():
    """Check database tables and migration status."""
    settings = get_settings()
    print(f"🔗 Database URL: {settings.database_url[:50]}...")
    
    engine = create_async_engine(settings.async_database_url)
    
    async with engine.begin() as conn:
        try:
            # Check if alembic_version table exists
            result = await conn.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            version = result.scalar_one_or_none()
            print(f"📋 Migration version: {version}")
            
            # Check if workflows table exists
            result = await conn.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'workflows'")
            )
            exists = result.scalar()
            print(f"🗄️  Workflows table exists: {bool(exists)}")
            
            # List all tables
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
            )
            tables = [row[0] for row in result.fetchall()]
            print(f"\n📊 Tables in database ({len(tables)}):")
            for table in tables:
                print(f"   - {table}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
    
    await engine.dispose()
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(check_db()))
