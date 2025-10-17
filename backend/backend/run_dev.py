#!/usr/bin/env python3
"""
Development server runner with auto-reload
"""

import os
import sys

# Set development environment
os.environ['ENVIRONMENT'] = 'development'
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'

# Ensure we're in the backend directory
if not os.path.exists('app.py'):
    print("❌ Error: run_dev.py must be run from the backend directory")
    print("📂 Current directory:", os.getcwd())
    print("💡 Try: cd backend && python run_dev.py")
    sys.exit(1)

# Import and run the app
print("🔄 Starting Flask development server...")
print("=" * 50)

from app import app

# The app will run with debug=True from app.py