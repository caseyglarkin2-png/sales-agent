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
COPY start.sh ./
RUN chmod +x start.sh

EXPOSE 8000

# Cache bust: 20260127-v1 - Gemini Portal + Drive Integration
# Use startup script for proper PORT handling
CMD ["./start.sh"]
