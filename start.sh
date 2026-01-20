#!/bin/sh
# Railway start script - handles PORT variable

PORT="${PORT:-8000}"
echo "Starting uvicorn on port $PORT"
exec python -m uvicorn src.main:app --host 0.0.0.0 --port "$PORT"
