#!/usr/bin/env python3
"""Run database migrations on Railway."""
import os
import sys
from alembic.config import Config
from alembic import command

def run_migrations():
    """Run all pending database migrations."""
    # Get the directory containing this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    alembic_cfg_path = os.path.join(base_dir, "infra", "alembic.ini")
    
    # Create Alembic config
    alembic_cfg = Config(alembic_cfg_path)
    
    # Set the script location
    alembic_cfg.set_main_option("script_location", os.path.join(base_dir, "infra", "migrations"))
    
    # Run migrations
    print("Running database migrations...")
    try:
        command.upgrade(alembic_cfg, "head")
        print("✅ Migrations completed successfully!")
        return 0
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_migrations())
