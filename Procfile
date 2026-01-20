# Railway Procfile - defines multiple services
# Each line is a separate Railway service

# Main API server
web: uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}

# Celery worker for background tasks
worker: celery -A src.tasks worker --loglevel=info --concurrency=2

# Celery beat for scheduled tasks (optional, enable when needed)
# beat: celery -A src.tasks beat --loglevel=info
