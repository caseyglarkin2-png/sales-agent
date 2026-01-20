#!/bin/sh
# Railway start script

echo "Running database migrations..."
cd /app && python -m alembic -c infra/alembic.ini upgrade head || echo "Migration failed or already up to date"

echo "Starting uvicorn..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
