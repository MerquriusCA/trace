#!/usr/bin/env python3
"""
Check existing users in database and create a valid JWT token
"""
import sys
import os
import jwt
import datetime
from dotenv import load_dotenv

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import database models
from app import app, db, User

def check_users_and_create_token():
    with app.app_context():
        # Get all users
        users = User.query.all()
        
        if not users:
            print("No users found in database!")
            print("-" * 50)
            print("Creating a test admin user...")
            
            # Create a test admin user
            admin_user = User(
                email='admin@example.com',
                name='Admin User',
                google_id='test_google_id_123'
            )
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"Created admin user with ID: {admin_user.id}")
            user_id = admin_user.id
            user_email = admin_user.email
        else:
            print(f"Found {len(users)} users in database:")
            print("-" * 50)
            for user in users:
                print(f"ID: {user.id} | Email: {user.email} | Name: {user.name}")
            
            # Use the first user for token generation
            user_id = users[0].id
            user_email = users[0].email
            print("-" * 50)
            print(f"Generating token for user ID {user_id} ({user_email})")
        
        # Get secret key from environment or use default
        SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
        
        # Create a token payload for the first user
        payload = {
            'user_id': user_id,
            'email': user_email,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }
        
        # Generate token
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        
        print("-" * 50)
        print("Token generated successfully!")
        print("-" * 50)
        print(f"Token: {token}")
        print("-" * 50)
        print(f"\nAccess the pages with this token:")
        print(f"Dashboard: http://localhost:8000/dashboard?token={token}")
        print(f"Admin Users: http://localhost:8000/admin/users?token={token}")
        print("\nThis token is valid for 24 hours")

if __name__ == "__main__":
    check_users_and_create_token()