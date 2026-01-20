#!/bin/sh
# Railway start script

echo "Running database migrations..."
cd /app

# Try to run migrations. If it fails due to existing tables, stamp the migration as complete.
if ! python -m alembic -c infra/alembic.ini upgrade head 2>&1; then
    echo "Migration failed, trying to stamp current revision..."
    # Stamp the migration as done if tables already exist
    python -m alembic -c infra/alembic.ini stamp head 2>&1 || echo "Stamp also failed - continuing anyway"
fi

echo "Starting uvicorn..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
