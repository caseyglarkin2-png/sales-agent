# Railway Procfile
# Start with just the web service - add worker after Redis is configured

web: sh -c 'uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}'

# Uncomment these after adding Redis service in Railway:
# worker: celery -A src.tasks worker --loglevel=info --concurrency=2
# beat: celery -A src.tasks beat --loglevel=info
