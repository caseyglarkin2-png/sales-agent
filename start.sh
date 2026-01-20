#!/bin/sh
# Railway start script - hardcoded port 8000
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
