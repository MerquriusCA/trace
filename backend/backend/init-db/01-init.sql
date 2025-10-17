-- PostgreSQL initialization script for Chrome Extension Backend
-- This script will be run automatically when the Docker container starts

-- Create database if it doesn't exist (usually not needed with Docker)
-- The database is already created by POSTGRES_DB environment variable

-- Grant permissions to the user
GRANT ALL PRIVILEGES ON DATABASE chrome_extension TO chrome_user;

-- Set timezone
SET timezone = 'UTC';

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";