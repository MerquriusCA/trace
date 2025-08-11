# This Dockerfile is for Railway deployment from root directory
# It builds the backend service

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend files
COPY backend/ ./

# Create instance directory for SQLite (if used)
RUN mkdir -p instance

# Expose port (Railway will override with PORT env var)
EXPOSE 8000

# Start the application using PORT environment variable
CMD gunicorn app:app --bind 0.0.0.0:$PORT