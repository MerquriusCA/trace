#!/usr/bin/env python3
"""
Create a test JWT token for dashboard access
"""
import jwt
import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get secret key from environment or use default
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Create a test payload
payload = {
    'user_id': 1,  # Assuming user ID 1 exists
    'email': 'test@example.com',
    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
}

# Generate token
token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

print("Test token generated!")
print("-" * 50)
print(f"Token: {token}")
print("-" * 50)
print(f"\nAccess dashboard with token:")
print(f"http://localhost:5001/dashboard?token={token}")
print("\nThis token is valid for 24 hours")