# This Dockerfile is for Railway deployment from root directory
# It builds the backend service

FROM python:3.11-slim

WORKDIR /app

# Copy backend files
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Create instance directory for SQLite (if used)
RUN mkdir -p instance

# Expose port
EXPOSE 8000

# Start the application
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]