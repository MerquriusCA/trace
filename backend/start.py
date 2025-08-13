#!/usr/bin/env python3
"""
Startup script for Railway deployment
Handles PORT environment variable properly
"""
import os
import sys
from app import app

if __name__ == '__main__':
    # Get port from environment variable
    port = int(os.environ.get('PORT', 8000))
    
    print(f"🚀 Starting Flask app on port {port}")
    print(f"📍 Environment: {os.environ.get('FLASK_ENV', 'production')}")
    print(f"🔗 Database: {'PostgreSQL' if 'postgres' in os.environ.get('DATABASE_URL', '') else 'SQLite'}")
    
    # Run the Flask app directly (for Railway)
    # In production, Railway will handle the process management
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )