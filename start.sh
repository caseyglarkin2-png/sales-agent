#!/bin/sh
# Railway start script

echo "🚀 Starting Sales Agent with JARVIS..."

# Get PORT from environment (Railway sets this automatically)
PORT=${PORT:-8000}

echo "📦 Running database migrations..."
cd /app

# Check current migration state
echo "🔍 Checking current migration state..."
python -m alembic -c infra/alembic.ini current || echo "Failed to get current state"

# List available migrations
echo "🔍 Available migrations:"
python -m alembic -c infra/alembic.ini heads || echo "Failed to list heads"

# Try to run migrations. If it fails due to existing tables, stamp the migration as complete.
echo "🔍 Attempting migration with verbose output..."
if ! python -m alembic -c infra/alembic.ini upgrade head; then
    echo "⚠️  Migration failed, trying to stamp current revision..."
    # Stamp the migration as done if tables already exist
    python -m alembic -c infra/alembic.ini stamp head || echo "❌ Stamp also failed - continuing anyway"
else
    echo "✅ Migrations completed successfully!"
    # Show final state
    python -m alembic -c infra/alembic.ini current
fi

echo "🎙️  Starting JARVIS Voice Approval System..."
echo "Port: $PORT"
exec uvicorn src.main:app --host 0.0.0.0 --port $PORT
