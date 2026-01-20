#!/bin/sh
# Railway start script

# Debug: show environment
echo "PORT env var is: $PORT"
echo "Starting uvicorn..."

# Use PORT if set, otherwise 8000
if [ -z "$PORT" ]; then
    PORT=8000
fi

exec uvicorn src.main:app --host 0.0.0.0 --port "$PORT"
