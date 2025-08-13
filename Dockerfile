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

# Set default environment variables for minimal startup
ENV FLASK_ENV=production
ENV SECRET_KEY=temporary-secret-key-please-change
ENV DATABASE_URL=sqlite:///instance/chrome_extension.db

# Start the application
# Use exec form with sh -c to ensure PORT variable expansion works
CMD ["/bin/sh", "-c", "exec gunicorn app:app --bind 0.0.0.0:${PORT:-8000} --timeout 120 --workers 1 --log-level info"]