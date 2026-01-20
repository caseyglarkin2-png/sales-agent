FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY src ./src
COPY infra ./infra

EXPOSE 8000

# Railway sets PORT env var - use shell form for variable expansion
CMD /bin/sh -c "python -m uvicorn src.main:app --host 0.0.0.0 --port \${PORT:-8000}"
