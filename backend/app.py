#!/usr/bin/env python3
"""
Enhanced Flask application for Chrome extension backend
Includes Google SSO authentication and Stripe subscription processing
"""

import os
import json
import urllib.request
import ssl
import re
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, render_template, redirect
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import jwt
from google.auth.transport import requests
from google.oauth2 import id_token
from dotenv import load_dotenv

# Import Stripe with error handling
try:
    import stripe
    print("✅ Stripe module imported successfully")
    # Check if Stripe has the expected structure
    if hasattr(stripe, '__version__'):
        print(f"✅ Stripe version: {stripe.__version__}")
    
    # Import specific submodules we need
    import stripe.error
    import stripe.checkout
    print("✅ Stripe submodules imported successfully")
    
except ImportError as e:
    print(f"❌ Failed to import Stripe: {e}")
    stripe = None

# Detect environment first (Railway sets these variables)
is_railway = bool(os.getenv('RAILWAY_ENVIRONMENT_ID') or os.getenv('RAILWAY_PROJECT_ID'))

# Only load .env files for local development (not on Railway)
if not is_railway:
    load_dotenv()
    print("🔧 Loaded local .env file for development")
else:
    print("🚀 Running on Railway - using environment variables only")

environment = 'railway' if is_railway else 'local'
print(f"🌍 Environment: {environment}")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration - ALWAYS use DATABASE_URL
database_url = os.getenv('DATABASE_URL')

if not database_url:
    if is_railway:
        print("⚠️ WARNING: Railway detected but DATABASE_URL not set!")
        print("⚠️ Please add a PostgreSQL service to your Railway project")
        print("⚠️ Using SQLite as temporary fallback...")
        database_url = 'sqlite:///railway_temp.db'
    else:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        print("⚠️  Please set DATABASE_URL in your .env file")
        print("⚠️  Example: DATABASE_URL=sqlite:///chrome_extension.db")
        raise ValueError("DATABASE_URL must be set in environment variables")

# Handle PostgreSQL URL variants (Railway sometimes uses postgres:// instead of postgresql://)
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
    print("📝 Updated database URL scheme from postgres:// to postgresql://")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Log database connection info
if database_url.startswith('postgresql://'):
    print(f"🐘 Using PostgreSQL database")
elif database_url.startswith('sqlite://'):
    print(f"🗄️ Using SQLite database")
else:
    print(f"🗄️ Using database: {database_url[:30]}...")

# Debug environment variables (safely)
print("🔧 Environment variables check:")
print(f"   DATABASE_URL: {'✅ Set' if database_url else '❌ Not set'}")
print(f"   STRIPE_SECRET_KEY: {'✅ Set' if os.getenv('STRIPE_SECRET_KEY') else '❌ Not set'}")
print(f"   GOOGLE_CLIENT_ID: {'✅ Set' if os.getenv('GOOGLE_CLIENT_ID') else '❌ Not set'}")
print(f"   SECRET_KEY: {'✅ Set' if os.getenv('SECRET_KEY') != 'dev-secret-key-change-in-production' else '⚠️ Using default'}")

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app)

# Configure Stripe - Initialize safely
def init_stripe():
    """Initialize Stripe with proper error handling"""
    try:
        # Check if Stripe module is available
        if stripe is None:
            print("❌ Stripe module not available")
            return False
            
        stripe_key = os.getenv('STRIPE_SECRET_KEY')
        if not stripe_key:
            print("⚠️ STRIPE_SECRET_KEY not found in environment")
            return False
        
        if not stripe_key.startswith('sk_'):
            print(f"⚠️ Invalid Stripe key format: {stripe_key[:10]}...")
            return False
        
        # Set the API key
        stripe.api_key = stripe_key
        print(f"✅ Stripe initialized with key: {stripe_key[:10]}...")
        
        # Verify the key is set properly
        if hasattr(stripe, 'api_key') and stripe.api_key == stripe_key:
            print("✅ Stripe API key configured successfully")
            return True
        else:
            print("⚠️ Stripe API key may not be set properly")
            return True  # Still return True to continue
            
    except Exception as e:
        print(f"❌ Failed to initialize Stripe: {e}")
        return False

# Try to initialize Stripe at startup
stripe_initialized = init_stripe()

# Google OAuth settings
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    picture = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Subscription fields
    stripe_customer_id = db.Column(db.String(100))
    subscription_status = db.Column(db.String(50), default='inactive')  # active, inactive, cancelled, past_due
    subscription_id = db.Column(db.String(100))
    current_period_end = db.Column(db.DateTime)
    plan_id = db.Column(db.String(100))
    
    # User preferences
    summary_style = db.Column(db.String(20), default='eli8')  # quick, eli8, detailed
    auto_summarize_enabled = db.Column(db.Boolean, default=False)
    notifications_enabled = db.Column(db.Boolean, default=True)
    reader_type = db.Column(db.String(50), default='lifelong_learner')  # student, business, researcher, tech, lifelong_learner, creative
    reading_level = db.Column(db.String(20), default='balanced')  # simple, balanced, detailed, technical
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'picture': self.picture,
            'subscription_status': self.subscription_status,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'plan_id': self.plan_id,
            'preferences': {
                'summary_style': self.summary_style,
                'auto_summarize_enabled': self.auto_summarize_enabled,
                'notifications_enabled': self.notifications_enabled,
                'reader_type': self.reader_type,
                'reading_level': self.reading_level
            }
        }

class APIUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    endpoint = db.Column(db.String(100), nullable=False)  # summarize, analyze
    url = db.Column(db.String(500))
    tokens_used = db.Column(db.Integer, default=0)
    cost = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('api_usage', lazy=True))

class Counter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'count': self.count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Cnter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'count': self.count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feedback_type = db.Column(db.String(20), nullable=False)  # bug, feature, general
    message = db.Column(db.Text, nullable=False)
    page_url = db.Column(db.String(500))
    page_title = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('feedback', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'user_email': self.user.email if self.user else None,
            'feedback_type': self.feedback_type,
            'message': self.message,
            'page_url': self.page_url,
            'page_title': self.page_title,
            'created_at': self.created_at.isoformat()
        }

# Authentication decorator
def require_admin_token(f):
    """Decorator for admin template routes - checks for valid admin JWT token in query params"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.args.get('token')
        
        if not token:
            return redirect('/admin/login')
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            
            # Check if this is an admin token
            if not payload.get('admin'):
                return redirect('/admin/login')
                
            # Token is valid, proceed with the route
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return redirect('/admin/login?error=expired')
        except jwt.InvalidTokenError:
            return redirect('/admin/login?error=invalid')
    
    return decorated_function

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid authorization header format'}), 401
        
        if not token:
            return jsonify({'error': 'Authorization token required'}), 401
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            
            # Check if this is an admin token
            if payload.get('admin'):
                # Create a mock admin user object for admin tokens
                class AdminUser:
                    def __init__(self):
                        self.id = 0
                        self.email = payload.get('email', 'admin@trace.com')
                        self.name = 'Admin'
                        self.subscription_status = 'active'
                        self.is_admin = True
                    
                    def to_dict(self):
                        return {
                            'id': self.id,
                            'email': self.email,
                            'name': self.name,
                            'is_admin': True
                        }
                
                current_user = AdminUser()
            else:
                # Regular user token
                current_user = User.query.get(payload['user_id'])
                if not current_user:
                    return jsonify({'error': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated_function

def require_active_subscription(f):
    @wraps(f)
    def decorated_function(current_user, *args, **kwargs):
        # Check for active subscription (allow special user)
        print(f"📝 Subscription check - User: {current_user.email}, Status: {current_user.subscription_status}")
        
        # Define whitelisted emails (should match frontend config)
        whitelisted_emails = [
            'david@merqurius.com',
            # Add more emails here as needed
            # 'investor@example.com',
            # 'demo@example.com'
        ]
        
        # Allow whitelisted users to bypass subscription requirement
        if current_user.email.lower() in [email.lower() for email in whitelisted_emails]:
            print(f"✅ Whitelisted user access granted: {current_user.email}")
            return f(current_user, *args, **kwargs)
        
        if current_user.subscription_status != 'active':
            return jsonify({
                'error': 'Active subscription required',
                'subscription_status': current_user.subscription_status,
                'message': 'Please upgrade to Pro to access AI features'
            }), 403
        
        # Check if subscription is still valid
        if current_user.current_period_end and current_user.current_period_end < datetime.utcnow():
            current_user.subscription_status = 'past_due'
            db.session.commit()
            return jsonify({
                'error': 'Subscription has expired',
                'subscription_status': 'past_due',
                'message': 'Your subscription has expired. Please renew to continue using AI features.'
            }), 403
        
        return f(current_user, *args, **kwargs)
    
    return decorated_function

# Authentication Routes
@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    """Authenticate user with Google access token or user info"""
    try:
        data = request.get_json()
        access_token = data.get('access_token')
        user_info = data.get('user_info')
        
        if not user_info:
            return jsonify({'error': 'User info required'}), 400
        
        # For Chrome extensions, we trust the user info from the extension
        # since it comes from chrome.identity API which is secure
        google_id = user_info.get('id')
        email = user_info.get('email')
        name = user_info.get('name', user_info.get('given_name', ''))
        picture = user_info.get('picture', '')
        
        # Find or create user
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            user = User(
                google_id=google_id,
                email=email,
                name=name,
                picture=picture
            )
            db.session.add(user)
            db.session.commit()
            
            # Create Stripe customer
            try:
                if stripe_initialized:
                    stripe_customer = stripe.Customer.create(
                        email=email,
                        name=name,
                        metadata={'user_id': user.id}
                    )
                    user.stripe_customer_id = stripe_customer.id
                    db.session.commit()
                else:
                    print("Stripe not initialized - skipping customer creation")
            except Exception as e:
                print(f"Failed to create Stripe customer: {e}")
        else:
            # Update user info
            user.name = name
            user.picture = picture
            user.updated_at = datetime.utcnow()
            db.session.commit()
        
        # Generate JWT token
        token_payload = {
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(days=30)
        }
        token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'success': True,
            'token': token,
            'user': user.to_dict()
        })
        
    except ValueError:
        return jsonify({'error': 'Invalid ID token'}), 400
    except Exception as e:
        print(f"Google auth error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

@app.route('/api/auth/verify', methods=['GET'])
@require_auth
def verify_token(current_user):
    """Verify if token is still valid and return user info"""
    return jsonify({
        'success': True,
        'user': current_user.to_dict()
    })

# Subscription Routes
@app.route('/api/subscription/create-checkout-session', methods=['POST'])
@require_auth
def create_checkout_session(current_user):
    """Create a Stripe checkout session for subscription"""
    print(f"\n{'='*50}")
    print(f"📝 CREATE CHECKOUT SESSION REQUEST")
    print(f"👤 User: {current_user.email}")
    print(f"💳 Stripe Customer ID: {current_user.stripe_customer_id or 'None'}")
    
    try:
        if not stripe_initialized:
            print("❌ Stripe not initialized, attempting to reinitialize...")
            if init_stripe():
                print("✅ Stripe reinitialized successfully")
            else:
                print("❌ Failed to reinitialize Stripe")
                return jsonify({'error': 'Stripe not available'}), 503
            
        data = request.get_json()
        price_id = data.get('price_id')  # Stripe price ID
        print(f"💰 Price ID: {price_id}")
        
        if not price_id:
            print("❌ No price ID provided")
            return jsonify({'error': 'Price ID required'}), 400
        
        # Create checkout session
        # For Chrome extensions, redirect to a success page that instructs users to return to extension
        base_url = request.url_root.rstrip('/')
        
        # Skip customer creation if it's causing issues
        # Stripe will create a customer during checkout
        if not current_user.stripe_customer_id:
            print(f"⚠️ No Stripe customer ID, will use customer_email in checkout")
        
        # Create checkout session
        checkout_params = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price': price_id,
                'quantity': 1,
            }],
            'mode': 'subscription',
            'success_url': f"{base_url}/subscription-success?session_id={{CHECKOUT_SESSION_ID}}",
            'cancel_url': f"{base_url}/subscription-cancelled",
            'metadata': {
                'user_id': current_user.id
            }
        }
        
        # Add customer if available, otherwise let Stripe create one
        if current_user.stripe_customer_id:
            checkout_params['customer'] = current_user.stripe_customer_id
        else:
            # Let Stripe collect customer email during checkout
            checkout_params['customer_email'] = current_user.email
        
        print(f"Checkout params: {checkout_params}")
        
        # Use direct API call to create checkout session
        # This avoids issues with Stripe module structure
        import requests
        
        if not stripe or not stripe.api_key:
            print("❌ Stripe API key not available")
            return jsonify({'error': 'Payment service not configured'}), 500
        
        print(f"📤 Making direct API call to Stripe")
        
        headers = {
            'Authorization': f'Bearer {stripe.api_key}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        # Convert params to form data
        form_data = {
            'payment_method_types[]': 'card',
            'line_items[0][price]': price_id,
            'line_items[0][quantity]': '1',
            'mode': 'subscription',
            'success_url': checkout_params['success_url'],
            'cancel_url': checkout_params['cancel_url'],
            'customer_email': current_user.email,
            'metadata[user_id]': str(current_user.id)
        }
        
        response = requests.post(
            'https://api.stripe.com/v1/checkout/sessions',
            headers=headers,
            data=form_data
        )
        
        print(f"📥 Stripe API response status: {response.status_code}")
        
        if response.status_code == 200:
            checkout_session = response.json()
            print(f"✅ Checkout session data: {checkout_session}")
        else:
            error_msg = response.json().get('error', {}).get('message', response.text)
            print(f"❌ Stripe API error: {error_msg}")
            raise Exception(f"Stripe API error: {error_msg}")
        
        # Extract the relevant fields from the response
        session_id = checkout_session.get('id')
        checkout_url = checkout_session.get('url')
        
        print(f"✅ Checkout session created: {session_id}")
        print(f"🔗 Checkout URL: {checkout_url}")
        print(f"{'='*50}\n")
        
        return jsonify({
            'success': True,
            'checkout_url': checkout_url,
            'session_id': session_id
        })
        
    except Exception as e:
        print(f"❌ Checkout session error: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        print(f"{'='*50}\n")
        return jsonify({'error': f'Failed to create checkout session: {str(e)}'}), 500

@app.route('/api/subscription/status', methods=['GET'])
@require_auth
def subscription_status(current_user):
    """Get current subscription status"""
    return jsonify({
        'success': True,
        'subscription': {
            'status': current_user.subscription_status,
            'current_period_end': current_user.current_period_end.isoformat() if current_user.current_period_end else None,
            'plan_id': current_user.plan_id
        }
    })

@app.route('/api/subscription/price', methods=['GET'])
def get_subscription_price():
    """Get the subscription price from Stripe"""
    try:
        if not stripe or not stripe.api_key:
            return jsonify({'success': False, 'error': 'Stripe not configured'}), 500
        
        # Get the price ID from environment variable
        price_id = os.environ.get('STRIPE_PRICE_ID', 'price_1RpIEaKtat2K2WuIYhlyXSrE')
        
        print(f"🔍 Fetching price details for: {price_id}")
        
        import requests
        headers = {
            'Authorization': f'Bearer {stripe.api_key}',
            'Stripe-Version': '2023-10-16'
        }
        
        # Get price details from Stripe
        price_response = requests.get(
            f'https://api.stripe.com/v1/prices/{price_id}',
            headers=headers
        )
        
        if price_response.status_code != 200:
            print(f"❌ Failed to fetch price: {price_response.status_code}")
            return jsonify({'success': False, 'error': 'Failed to fetch price from Stripe'}), 500
        
        price_data = price_response.json()
        
        # Extract price information
        amount = price_data.get('unit_amount', 0)
        currency = price_data.get('currency', 'usd')
        recurring = price_data.get('recurring', {})
        interval = recurring.get('interval', 'month') if recurring else 'one-time'
        
        # Convert amount from cents to dollars
        price_amount = amount / 100
        
        # Format price display
        price_display = f"${price_amount:.2f}"
        if interval != 'one-time':
            price_display += f"/{interval}"
        
        print(f"✅ Price fetched: {price_display}")
        
        return jsonify({
            'success': True,
            'price': {
                'id': price_id,
                'amount': amount,
                'currency': currency,
                'display': price_display,
                'interval': interval,
                'formatted_amount': price_amount
            }
        })
        
    except Exception as e:
        print(f"❌ Error fetching price: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/subscription/refresh', methods=['POST'])
@require_auth
def refresh_subscription_status(current_user):
    """Manually refresh subscription status from Stripe"""
    try:
        if not current_user.stripe_customer_id:
            return jsonify({
                'success': False,
                'error': 'No Stripe customer ID found'
            }), 400
        
        # Get customer's subscriptions from Stripe
        import requests
        headers = {
            'Authorization': f'Bearer {stripe.api_key}',
            'Stripe-Version': '2023-10-16'
        }
        
        print(f"📤 Refreshing subscription status for customer: {current_user.stripe_customer_id}")
        response = requests.get(
            f'https://api.stripe.com/v1/customers/{current_user.stripe_customer_id}/subscriptions',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            subscriptions_data = response.json()
            subscriptions = subscriptions_data.get('data', [])
            
            if subscriptions:
                # Get the most recent active subscription
                active_sub = None
                for sub in subscriptions:
                    if sub['status'] in ['active', 'trialing']:
                        active_sub = sub
                        break
                
                if active_sub:
                    # Update user with active subscription
                    current_user.subscription_id = active_sub['id']
                    current_user.subscription_status = 'active'
                    current_user.current_period_end = datetime.fromtimestamp(active_sub['current_period_end'])
                    current_user.plan_id = active_sub['items']['data'][0]['price']['id']
                    
                    db.session.commit()
                    
                    print(f"✅ Refreshed subscription for {current_user.email}")
                    print(f"   Subscription ID: {current_user.subscription_id}")
                    print(f"   Status: {current_user.subscription_status}")
                    
                    return jsonify({
                        'success': True,
                        'message': 'Subscription status refreshed',
                        'subscription': {
                            'status': current_user.subscription_status,
                            'subscription_id': current_user.subscription_id,
                            'current_period_end': current_user.current_period_end.isoformat(),
                            'plan_id': current_user.plan_id
                        }
                    })
                else:
                    print(f"⚠️ No active subscriptions found for {current_user.email}")
                    return jsonify({
                        'success': True,
                        'message': 'No active subscriptions found',
                        'subscription': {
                            'status': 'inactive',
                            'subscription_id': None,
                            'current_period_end': None,
                            'plan_id': None
                        }
                    })
            else:
                print(f"⚠️ No subscriptions found for customer {current_user.stripe_customer_id}")
                return jsonify({
                    'success': True,
                    'message': 'No subscriptions found',
                    'subscription': {
                        'status': 'inactive',
                        'subscription_id': None,
                        'current_period_end': None,
                        'plan_id': None
                    }
                })
        else:
            print(f"❌ Failed to fetch subscriptions: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'Failed to fetch subscriptions from Stripe: {response.status_code}'
            }), 500
            
    except Exception as e:
        print(f"❌ Subscription refresh error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to refresh subscription: {str(e)}'
        }), 500

@app.route('/api/subscription/cancel', methods=['POST'])
@require_auth
def cancel_subscription(current_user):
    """Cancel user's subscription"""
    try:
        if not stripe_initialized:
            return jsonify({'error': 'Stripe not available'}), 503
            
        if not current_user.subscription_id:
            return jsonify({'error': 'No active subscription found'}), 400
        
        # Cancel at period end
        stripe.Subscription.modify(
            current_user.subscription_id,
            cancel_at_period_end=True
        )
        
        return jsonify({
            'success': True,
            'message': 'Subscription will be cancelled at the end of the current period'
        })
        
    except Exception as e:
        print(f"Cancel subscription error: {e}")
        return jsonify({'error': 'Failed to cancel subscription'}), 500

# User Preferences Endpoints
@app.route('/api/preferences', methods=['GET'])
@require_auth
def get_preferences(current_user):
    """Get user preferences"""
    try:
        return jsonify({
            'success': True,
            'preferences': {
                'summary_style': current_user.summary_style or 'eli8',
                'auto_summarize_enabled': current_user.auto_summarize_enabled or False,
                'notifications_enabled': current_user.notifications_enabled if current_user.notifications_enabled is not None else True,
                'reader_type': current_user.reader_type or 'lifelong_learner',
                'reading_level': current_user.reading_level or 'balanced'
            }
        })
    except Exception as e:
        print(f"❌ Get preferences error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get preferences: {str(e)}'
        }), 500

@app.route('/api/preferences', methods=['POST'])
@require_auth
def save_preferences(current_user):
    """Save user preferences"""
    print(f"\n🔄 SAVE PREFERENCES REQUEST")
    print(f"👤 User: {current_user.email}")
    
    try:
        data = request.get_json()
        print(f"📝 Request data: {data}")
        
        # Validate summary_style
        valid_styles = ['quick', 'eli8', 'detailed']
        summary_style = data.get('summary_style', 'eli8')
        if summary_style not in valid_styles:
            return jsonify({
                'success': False,
                'error': f'Invalid summary_style. Must be one of: {valid_styles}'
            }), 400
        
        # Validate reader_type
        valid_reader_types = ['student', 'business', 'researcher', 'tech', 'lifelong_learner', 'creative']
        reader_type = data.get('reader_type', 'lifelong_learner')
        if reader_type not in valid_reader_types:
            reader_type = 'lifelong_learner'  # Default fallback
        
        # Validate reading_level
        valid_reading_levels = ['simple', 'balanced', 'detailed', 'technical']
        reading_level = data.get('reading_level', 'balanced')
        if reading_level not in valid_reading_levels:
            reading_level = 'balanced'  # Default fallback
        
        # Update user preferences
        current_user.summary_style = summary_style
        current_user.auto_summarize_enabled = bool(data.get('auto_summarize_enabled', False))
        current_user.notifications_enabled = bool(data.get('notifications_enabled', True))
        current_user.reader_type = reader_type
        current_user.reading_level = reading_level
        current_user.updated_at = datetime.utcnow()
        
        # Save to database
        db.session.commit()
        
        print(f"✅ Saved preferences for user {current_user.email}: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Preferences saved successfully',
            'preferences': {
                'summary_style': current_user.summary_style,
                'auto_summarize_enabled': current_user.auto_summarize_enabled,
                'notifications_enabled': current_user.notifications_enabled,
                'reader_type': current_user.reader_type,
                'reading_level': current_user.reading_level
            }
        })
        
    except Exception as e:
        print(f"❌ Save preferences error: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to save preferences: {str(e)}'
        }), 500

@app.route('/api/feedback', methods=['POST'])
@require_auth
def submit_feedback(current_user):
    """Submit user feedback with email notification"""
    import html
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    print(f"\n📧 FEEDBACK SUBMISSION")
    print(f"👤 User: {current_user.email}")
    
    try:
        data = request.get_json()
        
        # Sanitize input to prevent XSS attacks
        feedback_type = html.escape(data.get('type', 'general'))
        message = html.escape(data.get('message', ''))
        page_url = html.escape(data.get('page_url', 'Unknown'))
        page_title = html.escape(data.get('page_title', 'Unknown'))
        
        # Validate message length
        if not message or len(message) > 1000:
            return jsonify({
                'success': False,
                'error': 'Message must be between 1 and 1000 characters'
            }), 400
        
        # Get environment variables for email
        smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER', '')
        smtp_pass = os.getenv('SMTP_PASS', '')
        smtp_from = os.getenv('SMTP_FROM', 'david@merqurius.com')
        admin_email = os.getenv('ADMIN_EMAIL', 'david@merqurius.ca')
        
        # Get base URL for admin link
        base_url = os.getenv('BACKEND_URL', 'https://trace-production-79d5.up.railway.app')
        admin_user_url = f"{base_url}/admin/user/{current_user.id}/dashboard"
        
        # Create email content
        email_subject = f"[Trace Feedback] {feedback_type.capitalize()} from {current_user.name} ({current_user.email})"
        
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>New Feedback Received</h2>
            
            <h3>User Information:</h3>
            <ul>
                <li><strong>Name:</strong> {current_user.name}</li>
                <li><strong>Email:</strong> {current_user.email}</li>
                <li><strong>User ID:</strong> {current_user.id}</li>
                <li><strong>Subscription:</strong> {current_user.subscription_status}</li>
            </ul>
            
            <h3>Feedback Details:</h3>
            <ul>
                <li><strong>Type:</strong> {feedback_type}</li>
                <li><strong>Current Page:</strong> {page_title}</li>
                <li><strong>Page URL:</strong> {page_url}</li>
                <li><strong>Timestamp:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</li>
            </ul>
            
            <h3>Message:</h3>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0;">
                {message.replace(chr(10), '<br>')}
            </div>
            
            <h3>Admin Actions:</h3>
            <p>
                <a href="{admin_user_url}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    View User Dashboard
                </a>
            </p>
            
            <hr style="margin-top: 30px;">
            <p style="color: #666; font-size: 12px;">
                This feedback was submitted through the Trace Chrome Extension.
            </p>
        </body>
        </html>
        """
        
        # Send email if SMTP is configured
        print(f"🔧 SMTP Configuration Check:")
        print(f"   Host: {smtp_host}")
        print(f"   Port: {smtp_port}")
        print(f"   User: {smtp_user}")
        print(f"   Pass: {'*' * len(smtp_pass) if smtp_pass else 'None'}")
        print(f"   From: {smtp_from}")
        print(f"   Admin Email: {admin_email}")
        
        if smtp_user and smtp_pass:
            try:
                print(f"📧 Preparing email message...")
                msg = MIMEMultipart('alternative')
                msg['Subject'] = email_subject
                msg['From'] = smtp_from
                msg['To'] = admin_email
                
                html_part = MIMEText(email_body, 'html')
                msg.attach(html_part)
                print(f"✅ Email message prepared")
                
                # Use SSL for port 465, TLS for port 587
                if smtp_port == 465:
                    print(f"🔒 Using SMTP_SSL on port {smtp_port}")
                    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                        print(f"✅ Connected to {smtp_host}:{smtp_port} via SSL")
                        server.set_debuglevel(1)  # Enable SMTP debug logging
                        print(f"🔑 Attempting login with user: {smtp_user}")
                        server.login(smtp_user, smtp_pass)
                        print(f"✅ Login successful")
                        print(f"📤 Sending message...")
                        server.send_message(msg)
                        print(f"✅ Message sent via SSL")
                else:
                    print(f"🔒 Using SMTP with STARTTLS on port {smtp_port}")
                    with smtplib.SMTP(smtp_host, smtp_port) as server:
                        print(f"✅ Connected to {smtp_host}:{smtp_port}")
                        server.set_debuglevel(1)  # Enable SMTP debug logging
                        print(f"🔒 Starting TLS...")
                        server.starttls()
                        print(f"✅ TLS started")
                        print(f"🔑 Attempting login with user: {smtp_user}")
                        server.login(smtp_user, smtp_pass)
                        print(f"✅ Login successful")
                        print(f"📤 Sending message...")
                        server.send_message(msg)
                        print(f"✅ Message sent via TLS")
                
                print(f"✅ Feedback email sent to {admin_email}")
            except Exception as e:
                print(f"⚠️ Failed to send email: {e}")
                print(f"⚠️ Error type: {type(e).__name__}")
                import traceback
                print(f"⚠️ Full traceback: {traceback.format_exc()}")
                # Continue even if email fails
        else:
            print(f"⚠️ SMTP not configured - email not sent")
            print(f"📧 Would have sent to: {admin_email}")
            print(f"📝 Feedback: {message}")
        
        # Save feedback to database
        try:
            feedback = Feedback(
                user_id=current_user.id,
                feedback_type=feedback_type,
                message=message,
                page_url=data.get('page_url', ''),
                page_title=data.get('page_title', '')
            )
            db.session.add(feedback)
            db.session.commit()
            
            print(f"✅ Feedback saved to database with ID: {feedback.id}")
        except Exception as db_error:
            print(f"⚠️ Failed to save feedback to database: {db_error}")
            # Continue even if database save fails
        
        # Log feedback details
        print(f"✅ Feedback received from {current_user.email}")
        print(f"   Type: {feedback_type}")
        print(f"   Message: {message[:100]}...")
        
        return jsonify({
            'success': True,
            'message': 'Feedback sent successfully'
        })
        
    except Exception as e:
        print(f"❌ Feedback submission error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to send feedback'
        }), 500

# Stripe Webhooks
@app.route('/api/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks for subscription events"""
    if not stripe_initialized:
        print("⚠️ Stripe not initialized - ignoring webhook")
        return jsonify({'error': 'Stripe not available'}), 503
        
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    # Log webhook received
    print(f"\n{'='*50}")
    print(f"🪝 STRIPE WEBHOOK RECEIVED")
    print(f"{'='*50}")
    
    try:
        # For local development, skip signature verification
        if os.getenv('ENVIRONMENT') == 'development':
            print("⚠️  Development mode - parsing webhook payload directly")
            event = json.loads(payload)
        else:
            # Production: Verify webhook signature
            webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
            if not webhook_secret:
                print("❌ No webhook secret configured")
                return jsonify({'error': 'Webhook not configured'}), 400
                
            # Use direct API verification instead of SDK
            import hashlib
            import hmac
            
            # Extract timestamp and signature from header
            if not sig_header:
                print("❌ No signature header")
                return jsonify({'error': 'No signature'}), 400
                
            # For now, just parse the payload in development
            print("⚠️  Skipping signature verification for local testing")
            event = json.loads(payload)
            
        print(f"📋 Event Type: {event['type']}")
        print(f"🆔 Event ID: {event.get('id', 'unknown')}")
    except ValueError as e:
        print(f"❌ Invalid payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except Exception as e:
        print(f"❌ Webhook processing error: {e}")
        return jsonify({'error': 'Webhook processing failed'}), 400
    
    # Handle checkout session completed
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        print(f"✅ Checkout completed for session: {session['id']}")
        print(f"📋 Session details: {json.dumps(session, indent=2)}")
        
        # Handle subscription checkout
        if session['mode'] == 'subscription':
            user_id = session['metadata'].get('user_id')
            if not user_id:
                print(f"⚠️  No user_id in metadata")
                return jsonify({'success': True})
            
            user = User.query.get(user_id)
            if user:
                try:
                    subscription_id = session.get('subscription')
                    customer_id = session.get('customer')
                    
                    if subscription_id:
                        # Get subscription details via direct API call
                        import requests
                        headers = {
                            'Authorization': f'Bearer {stripe.api_key}',
                            'Stripe-Version': '2023-10-16'
                        }
                        
                        print(f"📤 Fetching subscription details for: {subscription_id}")
                        response = requests.get(
                            f'https://api.stripe.com/v1/subscriptions/{subscription_id}',
                            headers=headers,
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            subscription_data = response.json()
                            
                            # Update user subscription info
                            user.subscription_id = subscription_id
                            user.subscription_status = 'active'
                            user.stripe_customer_id = customer_id
                            user.current_period_end = datetime.fromtimestamp(subscription_data['current_period_end'])
                            user.plan_id = subscription_data['items']['data'][0]['price']['id']
                            
                            db.session.commit()
                            print(f"✅ Updated user {user.email} with subscription {subscription_id}")
                            print(f"   Status: {user.subscription_status}")
                            print(f"   Customer ID: {user.stripe_customer_id}")
                            print(f"   Plan ID: {user.plan_id}")
                        else:
                            print(f"❌ Failed to fetch subscription: {response.status_code} - {response.text}")
                    else:
                        print(f"⚠️  No subscription ID in checkout session")
                        
                except Exception as e:
                    print(f"❌ Error updating user subscription: {e}")
                    db.session.rollback()
            else:
                print(f"❌ User not found for ID: {user_id}")
    
    # Handle successful payment
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        subscription_id = invoice['subscription']
        print(f"💰 Payment succeeded for subscription: {subscription_id}")
        
        if subscription_id:
            user = User.query.filter_by(subscription_id=subscription_id).first()
            if user:
                user.subscription_status = 'active'
                # Update period end from invoice
                if invoice['lines'] and invoice['lines']['data']:
                    period_end = invoice['lines']['data'][0]['period']['end']
                    user.current_period_end = datetime.fromtimestamp(period_end)
                db.session.commit()
                print(f"✅ Updated payment status for user {user.email}")
    
    # Handle failed payment
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        subscription_id = invoice['subscription']
        print(f"❌ Payment failed for subscription: {subscription_id}")
        
        if subscription_id:
            user = User.query.filter_by(subscription_id=subscription_id).first()
            if user:
                user.subscription_status = 'past_due'
                db.session.commit()
                print(f"⚠️  Marked subscription as past_due for user {user.email}")
                # TODO: Send email notification to user
    
    # Handle subscription updated
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        print(f"🔄 Subscription updated: {subscription['id']}")
        
        user = User.query.filter_by(subscription_id=subscription['id']).first()
        if user:
            # Update subscription status
            user.subscription_status = subscription['status']
            user.current_period_end = datetime.fromtimestamp(subscription['current_period_end'])
            
            # Update plan if changed
            if subscription['items'] and subscription['items']['data']:
                user.plan_id = subscription['items']['data'][0]['price']['id']
            
            db.session.commit()
            print(f"✅ Updated subscription details for user {user.email}")
    
    # Handle subscription cancelled
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        print(f"🚫 Subscription cancelled: {subscription['id']}")
        
        user = User.query.filter_by(subscription_id=subscription['id']).first()
        if user:
            user.subscription_status = 'cancelled'
            user.subscription_id = None
            user.plan_id = None
            db.session.commit()
            print(f"✅ Cancelled subscription for user {user.email}")
    
    # Handle subscription trial ending
    elif event['type'] == 'customer.subscription.trial_will_end':
        subscription = event['data']['object']
        print(f"⏰ Trial ending soon for subscription: {subscription['id']}")
        
        user = User.query.filter_by(subscription_id=subscription['id']).first()
        if user:
            # TODO: Send trial ending notification email
            print(f"📧 Should notify user {user.email} that trial is ending")
    
    # Handle payment method attached
    elif event['type'] == 'payment_method.attached':
        payment_method = event['data']['object']
        customer_id = payment_method['customer']
        print(f"💳 Payment method attached for customer: {customer_id}")
        
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            print(f"✅ Payment method added for user {user.email}")
    
    # Handle charge succeeded (one-time payments)
    elif event['type'] == 'charge.succeeded':
        charge = event['data']['object']
        print(f"💵 Charge succeeded: ${charge['amount'] / 100:.2f}")
        
        # Log successful charge
        if charge['customer']:
            user = User.query.filter_by(stripe_customer_id=charge['customer']).first()
            if user:
                print(f"✅ Charge successful for user {user.email}")
    
    # Handle customer created
    elif event['type'] == 'customer.created':
        customer = event['data']['object']
        print(f"👤 New Stripe customer created: {customer['id']}")
    
    # Handle refunds
    elif event['type'] == 'charge.refunded':
        charge = event['data']['object']
        print(f"💸 Refund processed: ${charge['amount_refunded'] / 100:.2f}")
        
        if charge['customer']:
            user = User.query.filter_by(stripe_customer_id=charge['customer']).first()
            if user:
                print(f"💸 Refund processed for user {user.email}")
    
    # Log unhandled events (for debugging)
    else:
        print(f"ℹ️  Unhandled event type: {event['type']}")
    
    print(f"{'='*50}\n")
    return jsonify({'success': True})

# Admin Login Route
@app.route('/admin/login')
def admin_login():
    """Serve the admin login page"""
    return render_template('admin_login.html')

@app.route('/admin/authenticate', methods=['POST'])
def admin_authenticate():
    """Authenticate admin password and generate token"""
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        # Get admin password from environment variable or use a default for testing
        ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'trace-admin-2024')
        
        # Check if password is correct
        if password != ADMIN_PASSWORD:
            return jsonify({
                'success': False,
                'error': 'Invalid password'
            }), 401
        
        # Generate admin token with 24-hour expiration
        token_payload = {
            'admin': True,
            'email': 'admin@trace.com',
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        
        # Create JWT token
        token = jwt.encode(token_payload, app.config['SECRET_KEY'], algorithm='HS256')
        
        print(f"✅ Admin authenticated successfully at {datetime.utcnow()}")
        
        return jsonify({
            'success': True,
            'token': token,
            'expires_in': '24 hours'
        })
        
    except Exception as e:
        print(f"❌ Admin authentication error: {e}")
        return jsonify({
            'success': False,
            'error': 'Authentication failed'
        }), 500

# Dashboard and Usage Statistics Routes
@app.route('/admin/dashboard')
@require_admin_token
def admin_dashboard():
    """Serve the admin dashboard page"""
    return render_template('admin_users_tw.html')

@app.route('/admin/users')  # Keep old route for backward compatibility
def admin_users():
    """Redirect to new admin dashboard route"""
    from flask import redirect, request
    token = request.args.get('token')
    if token:
        return redirect(f'/admin/dashboard?token={token}')
    return redirect('/admin/dashboard')

@app.route('/admin/user/<int:user_id>/dashboard')
@require_admin_token
def admin_user_dashboard(user_id):
    """Serve the individual user dashboard page"""
    return render_template('user_dashboard_tw.html')

@app.route('/admin/feedback')
@require_admin_token
def admin_feedback():
    """Serve the admin feedback page"""
    return render_template('admin_feedback_tw.html')

@app.route('/admin/prompt-test')
@require_admin_token
def admin_prompt_test():
    """Serve the admin prompt testing page"""
    return render_template('admin_prompt_test_tw.html')

@app.route('/admin/style-guide')
@require_admin_token
def admin_style_guide():
    """Serve the admin style guide page"""
    return render_template('admin_style_guide_tw.html')

@app.route('/admin/landing-page')
@app.route('/landing')
def admin_landing_page():
    """Serve the landing page preview (no auth required, not indexed by search engines)"""
    return render_template('admin_landing_page_tw.html')

@app.route('/admin/logo')
def admin_logo():
    """Serve the logo exploration page (no auth required)"""
    return render_template('admin_logo_tw.html')

@app.route('/robots.txt')
def robots_txt():
    """Serve robots.txt to prevent search engine indexing of specific pages"""
    robots_content = """User-agent: *
Disallow: /admin/
Disallow: /landing
Disallow: /api/

User-agent: Googlebot
Disallow: /admin/
Disallow: /landing
Disallow: /api/
"""
    return robots_content, 200, {'Content-Type': 'text/plain'}

@app.route('/admin/products')
@require_admin_token
def admin_products():
    """Serve the admin products page"""
    return render_template('admin_products_tw.html')

@app.route('/subscription-success')
def subscription_success():
    """Success page after Stripe checkout"""
    return render_template('subscription-success.html')

@app.route('/subscription-cancelled')
def subscription_cancelled():
    """Cancellation page after Stripe checkout"""
    return render_template('subscription-cancelled.html')

@app.route('/api/usage/stats', methods=['GET'])
@require_auth
def usage_stats(current_user):
    """Get usage statistics for the current user"""
    try:
        # Calculate total requests
        total_requests = APIUsage.query.filter_by(user_id=current_user.id).count()
        
        # Calculate this month's requests
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_requests = APIUsage.query.filter(
            APIUsage.user_id == current_user.id,
            APIUsage.created_at >= start_of_month
        ).count()
        
        # Calculate total cost
        total_cost = db.session.query(db.func.sum(APIUsage.cost)).filter_by(user_id=current_user.id).scalar() or 0.0
        
        return jsonify({
            'success': True,
            'total_requests': total_requests,
            'month_requests': month_requests,
            'total_cost': total_cost
        })
        
    except Exception as e:
        print(f"Usage stats error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get usage statistics'}), 500

@app.route('/api/usage/recent', methods=['GET'])
@require_auth
def recent_activity(current_user):
    """Get recent activity for the current user"""
    try:
        # Get last 10 requests
        recent_usage = APIUsage.query.filter_by(user_id=current_user.id)\
            .order_by(APIUsage.created_at.desc())\
            .limit(10)\
            .all()
        
        activity = []
        for usage in recent_usage:
            activity.append({
                'endpoint': usage.endpoint,
                'url': usage.url,
                'tokens_used': usage.tokens_used,
                'cost': usage.cost,
                'created_at': usage.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'activity': activity
        })
        
    except Exception as e:
        print(f"Recent activity error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get recent activity'}), 500

@app.route('/api/admin/user/<int:user_id>', methods=['GET'])
@require_auth
def admin_get_user(current_user, user_id):
    """Get a specific user's details with subscription and usage stats"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Get user's subscription info
        subscription_info = {
            'status': user.subscription_status,
            'subscription_id': user.subscription_id,
            'current_period_end': user.current_period_end.isoformat() if user.current_period_end else None,
            'plan_name': 'Pro' if user.subscription_status == 'active' else 'Free',
            'stripe_customer_id': user.stripe_customer_id
        }
        
        # Get user's usage stats
        user_usage = APIUsage.query.filter_by(user_id=user.id).all()
        total_requests = len(user_usage)
        total_cost = sum(usage.cost or 0 for usage in user_usage)
        
        # Get this month's usage
        from datetime import datetime
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_usage = APIUsage.query.filter(
            APIUsage.user_id == user.id,
            APIUsage.created_at >= month_start
        ).all()
        month_requests = len(monthly_usage)
        
        usage_stats = {
            'total_requests': total_requests,
            'month_requests': month_requests,
            'total_cost': total_cost
        }
        
        # Get recent activity (last 10)
        recent_usage = APIUsage.query.filter_by(user_id=user.id)\
            .order_by(APIUsage.created_at.desc())\
            .limit(10)\
            .all()
        
        activity = []
        for usage in recent_usage:
            activity.append({
                'endpoint': usage.endpoint,
                'url': usage.url,
                'tokens_used': usage.tokens_used,
                'cost': usage.cost,
                'created_at': usage.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'stripe_customer_id': user.stripe_customer_id
            },
            'subscription': subscription_info,
            'usage': usage_stats,
            'activity': activity
        })
        
    except Exception as e:
        print(f"Admin get user error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get user data'}), 500

@app.route('/api/admin/user/<int:user_id>/cancel-subscription', methods=['POST'])
@require_auth
def admin_cancel_user_subscription(current_user, user_id):
    """Admin endpoint to cancel a user's subscription"""
    # Check if current user is admin
    if current_user.email != 'admin@trace.com':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        if not user.subscription_id:
            return jsonify({'success': False, 'error': 'User has no active subscription'}), 400

        # Cancel the subscription immediately using Stripe API
        if stripe and stripe.api_key:
            import requests
            headers = {
                'Authorization': f'Bearer {stripe.api_key}',
                'Content-Type': 'application/x-www-form-urlencoded',
            }

            # Cancel immediately instead of at period end
            response = requests.delete(
                f'https://api.stripe.com/v1/subscriptions/{user.subscription_id}',
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                # Update user's subscription status in database
                user.subscription_status = 'cancelled'
                user.subscription_id = None
                user.plan_id = None
                user.current_period_end = None
                db.session.commit()

                print(f"✅ Admin cancelled subscription for user {user.email}")
                return jsonify({
                    'success': True,
                    'message': f'Successfully cancelled subscription for {user.email}'
                })
            else:
                error_data = response.json()
                return jsonify({
                    'success': False,
                    'error': f'Stripe error: {error_data.get("error", {}).get("message", "Unknown error")}'
                }), 500
        else:
            return jsonify({'success': False, 'error': 'Stripe not configured'}), 500

    except Exception as e:
        print(f"Admin cancel subscription error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/test-prompt', methods=['POST'])
@require_auth
def admin_test_prompt(current_user):
    """Test prompts with different user profiles and settings"""
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        article_url = data.get('article_url')
        article_title = data.get('article_title')
        article_content = data.get('article_content')
        is_custom_url = data.get('is_custom_url', False)
        settings = data.get('settings', {})

        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Prompt is required'
            }), 400

        # If it's a custom URL, fetch the content
        if is_custom_url and article_url:
            print(f"🌐 Fetching content from custom URL: {article_url}")
            try:
                page_content = fetch_page_content(article_url)
                if not page_content:
                    return jsonify({
                        'success': False,
                        'error': f'Unable to fetch content from URL: {article_url}'
                    }), 400

                # Clean and extract text from HTML
                clean_content = clean_html_content(page_content)

                # Update the prompt to include the fetched content
                if '[Content will be fetched from URL]' in prompt:
                    prompt = prompt.replace('[Content will be fetched from URL]', clean_content)
                else:
                    # Append the content to the prompt
                    prompt = f"{prompt}\n\n{clean_content}"

                print(f"✅ Successfully fetched content ({len(clean_content)} characters)")

            except Exception as e:
                print(f"❌ Error fetching URL content: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Error fetching content from URL: {str(e)}'
                }), 400

        # Use backend OpenAI API key
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            return jsonify({
                'success': False,
                'error': 'OpenAI API key not configured. Please set OPENAI_API_KEY in Railway environment variables.'
            }), 500

        # Call OpenAI API
        import requests

        print(f"🧪 Testing prompt for {settings.get('reader_type', 'unknown')} reader")
        print(f"   Reading level: {settings.get('reading_level', 'balanced')}")
        print(f"   Summary style: {settings.get('summary_style', 'eli8')}")
        print(f"   Source: {'Custom URL' if is_custom_url else 'Test Article'}")
        print(f"🧪 TEST-PROMPT Content being sent to OpenAI:")
        print(f"   Prompt length: {len(prompt)}")
        print(f"   Contains 'JSON object': {('JSON object' in prompt)}")
        print(f"   First 300 chars: {prompt[:300]}")

        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {openai_api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are a helpful assistant that creates structured summaries with supporting quotes. You MUST return a valid JSON object with the exact structure requested. Extract actual direct quotes from the article text provided. Use **bold** markdown for emphasis on key phrases within the text fields.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.3,
                'max_tokens': 1000
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            summary = result['choices'][0]['message']['content']
            token_count = result.get('usage', {}).get('total_tokens', 0)

            print(f"✅ Summary generated successfully ({token_count} tokens)")
            print(f"🧪 TEST-PROMPT Generated summary content:")
            print(f"   Raw: {repr(summary)}")
            print(f"   Display: {summary}")
            print(f"   Length: {len(summary)}")
            print(f"   Starts with {{: {summary.strip().startswith('{')}")
            print(f"   Contains 'SUMMARY': {('SUMMARY' in summary)}")
            print(f"   Contains 'POINTS': {('POINTS' in summary)}")
            print(f"   First 200 chars: {summary[:200]}")
            
            return jsonify({
                'success': True,
                'summary': summary,
                'token_count': token_count,
                'model': 'gpt-3.5-turbo',
                'settings': settings
            })
        else:
            error_data = response.json()
            print(f"❌ OpenAI API error: {error_data}")
            return jsonify({
                'success': False,
                'error': error_data.get('error', {}).get('message', 'API request failed')
            }), 500
            
    except Exception as e:
        print(f"❌ Prompt testing error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/reading-level-prompts', methods=['GET'])
@require_auth
def get_standardized_prompts(current_user):
    """Get standardized reading level prompts for frontend use"""
    try:
        prompts = get_reading_level_prompts()
        return jsonify({
            'success': True,
            'prompts': prompts
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/check-article', methods=['POST'])
@require_auth
def admin_check_article(current_user):
    """Test article detection for admin prompt testing"""
    try:
        data = request.get_json()
        article_url = data.get('article_url')
        article_content = data.get('article_content')
        is_custom_url = data.get('is_custom_url', False)

        if not article_url:
            return jsonify({
                'success': False,
                'error': 'Article URL is required'
            }), 400

        # Use backend OpenAI API key
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            return jsonify({
                'success': False,
                'error': 'OpenAI API key not configured.'
            }), 500

        # Get content for analysis
        if is_custom_url:
            print(f"🌐 Fetching content from URL for article check: {article_url}")
            try:
                page_content = fetch_page_content(article_url)
                if not page_content:
                    return jsonify({
                        'success': False,
                        'error': f'Unable to fetch content from URL: {article_url}'
                    }), 400

                # Clean and extract text from HTML
                clean_content = clean_html_content(page_content)
                print(f"✅ Successfully fetched content ({len(clean_content)} characters)")

            except Exception as e:
                print(f"❌ Error fetching URL content: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Error fetching content from URL: {str(e)}'
                }), 400
        else:
            # Use provided test article content
            clean_content = article_content

        if not clean_content:
            return jsonify({
                'success': False,
                'error': 'No content available for analysis'
            }), 400

        print(f"🔍 Checking article status for {article_url}")
        print(f"   Content length: {len(clean_content)} characters")
        print(f"   Source: {'Custom URL' if is_custom_url else 'Test Article'}")
        print(f"   First 500 chars of content: {clean_content[:500]}...")

        # Call the article detection function
        article_check_result = check_if_article(clean_content, openai_api_key)

        if article_check_result.get('success', True):
            # Extract analysis data
            analysis = {
                'is_article': article_check_result.get('is_article', False),
                'confidence': article_check_result.get('confidence', 0),
                'page_type': article_check_result.get('page_type', 'unknown'),
                'reason': article_check_result.get('reason', 'No reason provided')
            }

            print(f"✅ Article check completed")
            print(f"   Is Article: {analysis['is_article']}")
            print(f"   Confidence: {analysis['confidence']}%")
            print(f"   Page Type: {analysis['page_type']}")

            return jsonify({
                'success': True,
                'analysis': analysis,
                'url': article_url,
                'content_length': len(clean_content)
            })
        else:
            return jsonify({
                'success': False,
                'error': article_check_result.get('error', 'Article check failed')
            }), 500

    except Exception as e:
        print(f"❌ Admin article check error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/admin/feedback', methods=['GET'])
@require_auth
def admin_get_feedback(current_user):
    """Get all feedback submissions (admin endpoint)"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        feedback_type = request.args.get('type')  # Optional filter by type
        
        # Build query
        query = Feedback.query.join(User)
        
        # Filter by type if specified
        if feedback_type and feedback_type in ['bug', 'feature', 'general']:
            query = query.filter(Feedback.feedback_type == feedback_type)
        
        # Order by most recent first and paginate
        query = query.order_by(Feedback.created_at.desc())
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        feedback_list = [feedback.to_dict() for feedback in pagination.items]
        
        return jsonify({
            'success': True,
            'feedback': feedback_list,
            'pagination': {
                'page': page,
                'pages': pagination.pages,
                'per_page': per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        print(f"❌ Error fetching feedback: {e}")
        return jsonify({'error': f'Failed to fetch feedback: {str(e)}'}), 500

@app.route('/api/admin/users', methods=['GET'])
@require_auth
def admin_get_all_users(current_user):
    """Get all users with their subscription and usage stats (admin endpoint)"""
    try:
        # Get all users
        users = User.query.all()
        
        users_data = []
        total_requests = 0
        active_subscriptions = 0
        monthly_revenue = 0
        
        for user in users:
            # Get user's subscription status from User model
            subscription_status = user.subscription_status or 'inactive'
            subscription_plan = 'Free'
            
            if subscription_status == 'active':
                subscription_plan = 'Pro'
                active_subscriptions += 1
                # Get actual price from Stripe instead of hardcoded value
                try:
                    price_id = os.environ.get('STRIPE_PRICE_ID', 'price_1RpIEaKtat2K2WuIYhlyXSrE')
                    price = stripe.Price.retrieve(price_id)
                    monthly_revenue += (price.unit_amount / 100) if price.unit_amount else 9.99
                except:
                    monthly_revenue += 9.99  # Fallback
            elif subscription_status == 'trialing':
                subscription_status = 'trial'
                subscription_plan = 'Trial'
            
            # Get user's usage stats
            user_usage = APIUsage.query.filter_by(user_id=user.id).all()
            user_total_requests = len(user_usage)
            user_total_cost = sum(usage.cost or 0 for usage in user_usage)
            
            # Get this month's usage
            from datetime import datetime, timedelta
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_usage = APIUsage.query.filter(
                APIUsage.user_id == user.id,
                APIUsage.created_at >= month_start
            ).all()
            user_monthly_requests = len(monthly_usage)
            
            # Get last activity
            last_activity = APIUsage.query.filter_by(user_id=user.id)\
                .order_by(APIUsage.created_at.desc()).first()
            
            users_data.append({
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'subscription_status': subscription_status,
                'subscription_plan': subscription_plan,
                'total_requests': user_total_requests,
                'monthly_requests': user_monthly_requests,
                'total_cost': user_total_cost,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_active': last_activity.created_at.isoformat() if last_activity else None
            })
            
            total_requests += user_total_requests
        
        # Calculate overview stats
        stats = {
            'total_users': len(users),
            'active_subscriptions': active_subscriptions,
            'total_requests': total_requests,
            'monthly_revenue': monthly_revenue
        }
        
        return jsonify({
            'success': True,
            'users': users_data,
            'stats': stats
        })
        
    except Exception as e:
        print(f"Admin users error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get users data'}), 500

@app.route('/api/admin/products', methods=['GET'])
@require_auth
def admin_get_products(current_user):
    """Get all Stripe products with their prices using direct API calls"""
    try:
        print(f"🔍 Fetching Stripe products for user: {current_user.email}")
        
        # Check if Stripe is properly configured
        if not stripe or not stripe.api_key:
            print("❌ Stripe API key not configured")
            return jsonify({'success': False, 'error': 'Stripe API key not configured'}), 500
        
        print(f"✅ Stripe API key configured: {stripe.api_key[:7]}...")
        
        import requests
        
        # Fetch products from Stripe using direct API call
        print("📦 Fetching products from Stripe...")
        headers = {
            'Authorization': f'Bearer {stripe.api_key}',
            'Stripe-Version': '2023-10-16'
        }
        
        # Get products
        products_response = requests.get(
            'https://api.stripe.com/v1/products?limit=100',
            headers=headers
        )
        
        if products_response.status_code != 200:
            print(f"❌ Failed to fetch products: {products_response.status_code}")
            return jsonify({'success': False, 'error': 'Failed to fetch products from Stripe'}), 500
        
        products_data = products_response.json()
        products = products_data.get('data', [])
        print(f"✅ Found {len(products)} products")
        
        # For each product, also fetch all its prices
        products_with_prices = []
        for product in products:
            print(f"💰 Fetching prices for product: {product.get('name', 'Unknown')}")
            
            # Get all prices for this product
            prices_response = requests.get(
                f'https://api.stripe.com/v1/prices?product={product["id"]}&limit=100',
                headers=headers
            )
            
            prices_data = []
            if prices_response.status_code == 200:
                prices_json = prices_response.json()
                prices_data = prices_json.get('data', [])
            
            product_data = {
                'id': product.get('id'),
                'name': product.get('name'),
                'description': product.get('description'),
                'active': product.get('active'),
                'created': product.get('created'),
                'updated': product.get('updated'),
                'url': product.get('url'),
                'images': product.get('images', []),
                'metadata': product.get('metadata', {}),
                'prices': []
            }
            
            # Add price information
            for price in prices_data:
                price_data = {
                    'id': price.get('id'),
                    'active': price.get('active'),
                    'currency': price.get('currency'),
                    'type': price.get('type'),
                    'unit_amount': price.get('unit_amount'),
                    'created': price.get('created'),
                    'recurring': None
                }
                
                # Add recurring information if it's a subscription
                if price.get('recurring'):
                    recurring = price['recurring']
                    price_data['recurring'] = {
                        'interval': recurring.get('interval'),
                        'interval_count': recurring.get('interval_count'),
                        'usage_type': recurring.get('usage_type')
                    }
                
                product_data['prices'].append(price_data)
            
            products_with_prices.append(product_data)
        
        print(f"✅ Successfully processed {len(products_with_prices)} products with prices")
        
        # Get abbreviated keys for debugging
        secret_key_abbrev = stripe.api_key[:12] + "..." if stripe.api_key else "Not set"
        publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
        publishable_key_abbrev = publishable_key[:12] + "..." if publishable_key else "Not set"
        
        return jsonify({
            'success': True,
            'products': products_with_prices,
            'count': len(products_with_prices),
            'debug_info': {
                'secret_key': secret_key_abbrev,
                'publishable_key': publishable_key_abbrev,
                'environment': 'test' if 'test' in stripe.api_key else 'live' if 'live' in stripe.api_key else 'unknown'
            }
        })
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return jsonify({'success': False, 'error': f'API request failed: {str(e)}'}), 500
    except Exception as e:
        print(f"Admin products error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get products data'}), 500

# Enhanced API endpoints with authentication
@app.route('/api/summarize', methods=['POST'])
@require_auth
@require_active_subscription
def summarize_with_auth(current_user):
    """Enhanced summarize endpoint with authentication and usage tracking"""
    try:
        data = request.get_json()
        url = data.get('url')
        action = data.get('action', 'summarize')
        custom_prompt = data.get('customPrompt')  # Custom prompt from frontend
        
        print(f"\n{'='*50}")
        print(f"📝 AUTHENTICATED SUMMARIZE REQUEST")
        print(f"{'='*50}")
        print(f"👤 User: {current_user.email}")
        print(f"🌐 URL: {url}")
        print(f"⚙️  Action: {action}")
        
        if not url:
            return jsonify({'success': False, 'error': 'URL required'}), 400
        
        # Use backend OpenAI API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'error': 'OpenAI API key not configured on server'}), 500
        
        # Check if HTML content is provided directly (to bypass 403 errors)
        html_content = data.get('html')
        if html_content:
            print(f"📄 Using provided HTML content (length: {len(html_content)})")
            # Clean the provided HTML content
            page_content = clean_html_content(html_content)
        else:
            # Fetch page content from URL
            page_content = fetch_page_content(url)
            if not page_content:
                return jsonify({'success': False, 'error': 'Unable to fetch page content'}), 400
        
        # Call OpenAI API
        if action == 'analyze':
            result = call_openai_analyze(page_content, api_key)
        else:
            # Use custom prompt if provided, otherwise generate based on user's reading level
            prompt_to_use = custom_prompt
            print(f"🔧 Custom prompt provided: {bool(custom_prompt)}")
            print(f"🔧 User reading level: {current_user.reading_level}")
            if not prompt_to_use:
                # Generate prompt based on user's reading level using shared prompts
                reading_level_prompts = get_reading_level_prompts()
                # Use user's reading level or default to 'balanced' if not set
                user_level = current_user.reading_level if current_user.reading_level else 'balanced'
                prompt_to_use = reading_level_prompts.get(user_level, reading_level_prompts['balanced'])

                # Add instruction to return fewer points if content only has fewer valid main points
                prompt_to_use += '\n\nNOTE: If the article genuinely has fewer distinct main points than requested, return only the valid points that exist. Do not artificially create points just to meet the count. Always include the SUMMARY line regardless.'

            print(f"🔧 Final prompt being used: {prompt_to_use[:200]}...")
            print(f"🔧 Using JSON-structured prompt: {bool(prompt_to_use and 'JSON object' in prompt_to_use)}")
            result = call_openai_summarize(page_content, api_key, prompt_to_use)

            # Only try to parse JSON for actual articles (not for non-article messages)
            if result.get('success') and result.get('is_article') is not False:
                # Check if this is actually an article response (vs non-article message)
                if not result.get('summary', '').startswith('🔍 This doesn\'t appear to be'):
                    try:
                        import json
                        # Try to parse as JSON only for article summaries
                        raw_summary = result['summary']
                        print(f"📋 Raw summary to parse: {raw_summary}")
                        summary_data = json.loads(raw_summary)
                        print(f"📋 Parsed JSON structure: {list(summary_data.keys())}")
                        print(f"📋 Full parsed JSON: {summary_data}")

                        # Handle different JSON formats the AI might return
                        summary_text = ""
                        points_list = []

                        # Extract summary text - handle SUMMARY (caps) and summary (lowercase)
                        if 'SUMMARY' in summary_data:
                            summary_text = summary_data['SUMMARY']
                        elif 'summary' in summary_data:
                            summary_text = summary_data['summary']
                        elif 'main_points' in summary_data and 'summary' in summary_data['main_points']:
                            summary_text = summary_data['main_points']['summary']

                        # Extract points - handle the new POINTS structure
                        if 'POINTS' in summary_data and isinstance(summary_data['POINTS'], list):
                            # Handle structure like: {"POINTS": [{"point": "...", "quotes": ["..."]}]}
                            for point_obj in summary_data['POINTS']:
                                if isinstance(point_obj, dict):
                                    point_text = point_obj.get('point', point_obj.get('text', str(point_obj)))
                                    point_quotes = point_obj.get('quotes', point_obj.get('QUOTES', []))
                                    points_list.append({'text': point_text, 'quotes': point_quotes})
                                else:
                                    points_list.append({'text': str(point_obj), 'quotes': []})

                        elif 'main_points' in summary_data and isinstance(summary_data['main_points'], list):
                            # Handle legacy structure like: {"main_points": [{"point": "...", "QUOTES": ["..."]}]}
                            for point_obj in summary_data['main_points']:
                                if isinstance(point_obj, dict):
                                    point_text = point_obj.get('point', point_obj.get('text', str(point_obj)))
                                    point_quotes = point_obj.get('QUOTES', point_obj.get('quotes', []))
                                    points_list.append({'text': point_text, 'quotes': point_quotes})
                                else:
                                    points_list.append({'text': str(point_obj), 'quotes': []})

                        elif 'points' in summary_data:
                            points_list = summary_data['points']
                        elif 'key_takeaways' in summary_data:
                            key_takeaways = summary_data['key_takeaways']
                            points_list = [{'text': point, 'quotes': []} for point in key_takeaways]

                        # If we don't have quotes embedded in points, try to extract and distribute them
                        if not any(point.get('quotes') for point in points_list):
                            all_quotes = []
                            if 'quotes' in summary_data:
                                quotes_obj = summary_data['quotes']
                                if isinstance(quotes_obj, dict):
                                    # Convert quotes object to list
                                    all_quotes = list(quotes_obj.values())
                                elif isinstance(quotes_obj, list):
                                    all_quotes = quotes_obj

                            # Distribute quotes among points if we have both
                            if all_quotes and points_list:
                                quotes_per_point = len(all_quotes) // len(points_list)
                                remaining_quotes = len(all_quotes) % len(points_list)

                                quote_index = 0
                                for i, point in enumerate(points_list):
                                    point_quotes = quotes_per_point + (1 if i < remaining_quotes else 0)
                                    if quote_index < len(all_quotes):
                                        point['quotes'] = all_quotes[quote_index:quote_index + point_quotes]
                                        quote_index += point_quotes

                        # Convert to expected text format for the frontend
                        formatted_summary = f"SUMMARY: {summary_text}\n\n"
                        print(f"📋 Processing {len(points_list)} points:")

                        for i, point in enumerate(points_list, 1):
                            point_text = point['text'] if isinstance(point, dict) else str(point)
                            print(f"📍 Point {i}: '{point_text}'")
                            formatted_summary += f"• {point_text}\n"

                            point_quotes = point.get('quotes', []) if isinstance(point, dict) else []
                            print(f"📝 Point {i} quotes: {point_quotes}")
                            if point_quotes:
                                quotes_str = ', '.join([f'"{quote}"' for quote in point_quotes])
                                formatted_summary += f"  QUOTES: {quotes_str}\n"
                                print(f"📄 Added QUOTES line: 'QUOTES: {quotes_str}'")
                            formatted_summary += "\n"

                        # Return the raw JSON structure directly to the sidebar
                        print(f"🔧 About to set summary_data in result")
                        print(f"🔧 summary_data type: {type(summary_data)}")
                        print(f"🔧 summary_data content: {summary_data}")
                        result['summary_data'] = summary_data  # Return the original JSON structure
                        result['summary'] = formatted_summary.strip()  # Keep for backward compatibility
                        print(f"✅ Successfully parsed JSON and returning raw structure to sidebar")
                        print(f"📊 Raw JSON structure: {summary_data}")
                        print(f"🔧 result after setting summary_data: {list(result.keys())}")

                    except (json.JSONDecodeError, KeyError) as e:
                        # If JSON parsing fails, keep the original summary
                        print(f"📝 Could not parse JSON summary, using original: {e}")
                        pass
                else:
                    print(f"📋 Non-article message detected, skipping JSON parsing")
        
        # Track usage
        usage_record = APIUsage(
            user_id=current_user.id,
            endpoint=action,
            url=url,
            tokens_used=150,  # Estimate, you could get actual from OpenAI response
            cost=0.01  # Estimate based on tokens
        )
        db.session.add(usage_record)
        db.session.commit()
        
        print(f"✅ Request completed successfully")
        print(f"📋 Final result keys: {list(result.keys())}")
        if 'summary_data' in result:
            print(f"📊 summary_data included: {result['summary_data']}")
        else:
            print(f"❌ summary_data NOT included in result")
        print(f"{'='*50}\n")

        return jsonify(result)
        
    except Exception as e:
        print(f"💥 EXCEPTION in authenticated summarize: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Health check and test endpoints
@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    # Check database connection
    try:
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        db_status = 'healthy'
        db_error = None
        db_type = 'PostgreSQL' if database_url.startswith(('postgresql://', 'postgres://')) else 'SQLite'
    except Exception as e:
        db_status = 'unhealthy'
        db_error = str(e)
        db_type = 'Unknown'
        print(f"Database health check failed: {e}")
        
        # Try to create tables if they don't exist
        try:
            db.create_all()
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            db_status = 'healthy'
            db_error = 'Tables created on health check'
            print("✅ Created missing tables during health check")
        except Exception as e2:
            print(f"Failed to create tables in health check: {e2}")
    
    # Check Stripe connection
    stripe_status = 'unhealthy'
    stripe_error = 'Not initialized'
    
    try:
        if not stripe_initialized:
            stripe_error = "Stripe not initialized - check STRIPE_SECRET_KEY"
        elif stripe is None:
            stripe_error = "Stripe module not available"
        elif not hasattr(stripe, 'api_key'):
            stripe_error = "Stripe module missing api_key attribute"
        elif not stripe.api_key:
            stripe_error = "Stripe API key not set"
        else:
            # Try a simple API call that doesn't involve complex objects
            try:
                # Use a direct HTTP request to test Stripe
                import urllib.request
                req = urllib.request.Request(
                    'https://api.stripe.com/v1/balance',
                    headers={
                        'Authorization': f'Bearer {stripe.api_key}',
                        'Stripe-Version': '2023-10-16'
                    }
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        stripe_status = 'healthy'
                        stripe_error = None
                        print("✅ Stripe API connection verified via direct HTTP")
                    else:
                        stripe_error = f"Stripe API returned status {response.status}"
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    stripe_error = "Invalid Stripe API key"
                else:
                    stripe_error = f"Stripe API error: {e.code}"
            except Exception as e:
                stripe_error = f"Stripe connection test failed: {str(e)}"
                
    except Exception as e:
        stripe_error = f"Stripe health check error: {str(e)}"
        
    print(f"Stripe health check: status={stripe_status}, error={stripe_error}")
    
    overall_status = 'healthy' if db_status == 'healthy' and stripe_status == 'healthy' else 'unhealthy'
    
    response_data = {
        'status': overall_status,
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'database': {
                'status': db_status,
                'type': db_type,
                'error': db_error
            },
            'stripe': {
                'status': stripe_status,
                'error': stripe_error
            }
        },
        'environment': {
            'platform': 'Railway' if is_railway else 'Local',
            'database_url_present': bool(os.getenv('DATABASE_URL')),
            'database_type': db_type,
            'stripe_key_present': bool(os.getenv('STRIPE_SECRET_KEY')),
            'google_client_id_present': bool(os.getenv('GOOGLE_CLIENT_ID')),
            'port': os.getenv('PORT', 'not set')
        }
    }
    
    return jsonify(response_data)

@app.route('/api/test', methods=['POST', 'GET'])
def test_endpoint():
    """Simple test endpoint"""
    return jsonify({
        'success': True,
        'message': 'Authenticated backend is working!',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/counter/increment', methods=['POST'])
def increment_counter():
    """Increment counter by 1 and return current count"""
    try:
        counter_name = request.json.get('name', 'default') if request.is_json else 'default'
        
        # Get or create counter
        counter = Counter.query.filter_by(name=counter_name).first()
        
        if not counter:
            # Create new counter
            counter = Counter(name=counter_name, count=1)
            db.session.add(counter)
            print(f"✅ Created new counter '{counter_name}' with count 1")
        else:
            # Increment existing counter
            counter.count += 1
            counter.updated_at = datetime.utcnow()
            print(f"✅ Incremented counter '{counter_name}' to {counter.count}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'counter': counter.to_dict(),
            'message': f'Counter incremented to {counter.count}'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Counter increment error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to increment counter: {str(e)}'
        }), 500

@app.route('/api/counter/<name>', methods=['GET'])
def get_counter(name):
    """Get current counter value"""
    try:
        counter = Counter.query.filter_by(name=name).first()
        
        if not counter:
            return jsonify({
                'success': False,
                'error': f'Counter "{name}" not found'
            }), 404
        
        return jsonify({
            'success': True,
            'counter': counter.to_dict()
        })
        
    except Exception as e:
        print(f"❌ Counter get error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get counter: {str(e)}'
        }), 500

@app.route('/api/counters', methods=['GET'])
def get_all_counters():
    """Get all counters"""
    try:
        counters = Counter.query.all()
        
        return jsonify({
            'success': True,
            'counters': [counter.to_dict() for counter in counters],
            'total': len(counters)
        })
        
    except Exception as e:
        print(f"❌ Counters get error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get counters: {str(e)}'
        }), 500

@app.route('/api/cnter/increment', methods=['POST'])
def increment_cnter():
    """Increment cnter by 1 and return current count"""
    try:
        cnter_name = request.json.get('name', 'default') if request.is_json else 'default'
        
        # Get or create cnter
        cnter = Cnter.query.filter_by(name=cnter_name).first()
        
        if not cnter:
            # Create new cnter
            cnter = Cnter(name=cnter_name, count=2)
            db.session.add(cnter)
            print(f"✅ Created new cnter '{cnter_name}' with count 2")
        else:
            # Increment existing cnter
            cnter.count += 2
            cnter.updated_at = datetime.utcnow()
            print(f"✅ Incremented cnter '{cnter_name}' to {cnter.count}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'cnter': cnter.to_dict(),
            'message': f'Cnter incremented to {cnter.count}'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Cnter increment error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to increment cnter: {str(e)}'
        }), 500

@app.route('/api/cnter/<name>', methods=['GET'])
def get_cnter(name):
    """Get current cnter value"""
    try:
        cnter = Cnter.query.filter_by(name=name).first()
        
        if not cnter:
            return jsonify({
                'success': False,
                'error': f'Cnter "{name}" not found'
            }), 404
        
        return jsonify({
            'success': True,
            'cnter': cnter.to_dict()
        })
        
    except Exception as e:
        print(f"❌ Cnter get error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get cnter: {str(e)}'
        }), 500

@app.route('/api/cnters', methods=['GET'])
def get_all_cnters():
    """Get all cnters"""
    try:
        cnters = Cnter.query.all()
        
        return jsonify({
            'success': True,
            'cnters': [cnter.to_dict() for cnter in cnters],
            'total': len(cnters)
        })
        
    except Exception as e:
        print(f"❌ Cnters get error: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to get cnters: {str(e)}'
        }), 500

@app.route('/api/test-stripe', methods=['GET'])
def test_stripe():
    """Test Stripe configuration"""
    result = {
        'stripe_module': stripe is not None,
        'stripe_type': str(type(stripe)) if stripe else None,
        'stripe_initialized': stripe_initialized,
        'api_key_set': bool(stripe.api_key) if stripe and hasattr(stripe, 'api_key') else False,
        'stripe_version': stripe.__version__ if stripe and hasattr(stripe, '__version__') else None,
        'has_customer': hasattr(stripe, 'Customer') if stripe else False,
        'has_checkout': hasattr(stripe, 'checkout') if stripe else False,
    }
    
    # Try a simple API call
    try:
        if stripe and stripe.api_key:
            # Try to get API version
            import urllib.request
            req = urllib.request.Request(
                'https://api.stripe.com/v1/charges?limit=1',
                headers={
                    'Authorization': f'Bearer {stripe.api_key}',
                    'Stripe-Version': '2023-10-16'
                }
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                result['api_test'] = 'success'
                result['api_status'] = response.status
        else:
            result['api_test'] = 'skipped - no API key'
    except Exception as e:
        result['api_test'] = f'failed: {str(e)}'
    
    return jsonify(result)

# Webhook status endpoint
@app.route('/api/webhooks/status', methods=['GET'])
def webhook_status():
    """Check webhook configuration status"""
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    return jsonify({
        'webhook_configured': bool(webhook_secret),
        'webhook_url': request.url_root + 'api/webhooks/stripe',
        'events_to_configure': [
            'checkout.session.completed',
            'customer.subscription.created',
            'customer.subscription.updated',
            'customer.subscription.deleted',
            'invoice.payment_succeeded',
            'invoice.payment_failed',
            'customer.subscription.trial_will_end',
            'payment_method.attached',
            'charge.succeeded',
            'charge.refunded'
        ]
    })

# Utility functions (reuse from existing server)
def fetch_page_content(url):
    """Fetch and clean page content from URL"""
    import time

    try:
        print(f"Fetching content from: {url}")

        # Add small delay to be more respectful to servers
        time.sleep(0.5)

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })

        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, context=context, timeout=15) as response:
            # Handle gzip compression
            content = response.read()
            if response.headers.get('Content-Encoding') == 'gzip':
                import gzip
                content = gzip.decompress(content)
            html = content.decode('utf-8', errors='ignore')
        
        # Clean HTML
        html = re.sub(r'<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>', '', html, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) > 5000:
            text = text[:5000]
        
        return text
        
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(f"403 Forbidden error: Website blocked the request. This often happens with e-commerce sites and pages with anti-bot protection.")
            return None
        elif e.code == 404:
            print(f"404 Not Found: Page does not exist")
            return None
        else:
            print(f"HTTP Error {e.code}: {e.reason}")
            return None
    except Exception as e:
        print(f"Error fetching content: {e}")
        return None

def clean_html_content(html):
    """Clean HTML content for summarization"""
    try:
        print(f"Cleaning HTML content (length: {len(html)})")

        # Clean HTML - same logic as fetch_page_content
        html = re.sub(r'<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'<[^>]+>', ' ', html)
        html = re.sub(r'\s+', ' ', html).strip()

        # Limit text length for OpenAI API
        text = html
        if len(text) > 5000:
            text = text[:5000]

        print(f"Cleaned HTML content (final length: {len(text)})")
        return text

    except Exception as e:
        print(f"Error cleaning HTML content: {e}")
        return None

def get_reading_level_prompts():
    """Get standardized prompts for different reading levels - matches admin prompt test page exactly"""
    return {
        'simple': '''Return a JSON object with this exact structure:

{
  "SUMMARY": "One simple sentence that captures what this article is about",
  "POINTS": [
    {
      "point": "Single most important point in simple, clear language - use **bold** for key phrases",
      "quotes": ["Direct quote from the article that supports this point"]
    }
  ]
}

Use **bold** markdown for emphasis. Include exactly 1 point with 1 supporting quote.''',
        'balanced': '''Return a JSON object with this exact structure:

{
  "SUMMARY": "One clear sentence that captures the main idea of this article",
  "POINTS": [
    {
      "point": "First main point in clear, accessible language - use **bold** for key phrases",
      "quotes": ["First direct quote", "Second supporting quote if relevant"]
    },
    {
      "point": "Second main point in clear, accessible language - use **bold** for key phrases",
      "quotes": ["First direct quote", "Second supporting quote if relevant"]
    }
  ]
}

Use **bold** markdown for emphasis. Include exactly 2 points with 1-2 supporting quotes each.''',
        'detailed': '''Return a JSON object with this exact structure:

{
  "SUMMARY": "One comprehensive sentence that captures the essence and significance of this article",
  "POINTS": [
    {
      "point": "First key point with comprehensive detail - use **bold** for important concepts",
      "quotes": ["First supporting quote", "Second supporting quote", "Third quote if highly relevant"]
    },
    {
      "point": "Second key point with comprehensive detail - use **bold** for important concepts",
      "quotes": ["First supporting quote", "Second supporting quote", "Third quote if highly relevant"]
    },
    {
      "point": "Third key point with comprehensive detail - use **bold** for important concepts",
      "quotes": ["First supporting quote", "Second supporting quote", "Third quote if highly relevant"]
    }
  ]
}

Use **bold** markdown for emphasis. Include exactly 3 points with 2-3 supporting quotes each.''',
        'technical': '''Return a JSON object with this exact structure:

{
  "SUMMARY": "One precise technical sentence that captures the core concept and implications",
  "POINTS": [
    {
      "point": "First technical point with precise detail - use **bold** for technical terms and key findings",
      "quotes": ["First technical quote", "Second supporting data/quote", "Third evidence if relevant"]
    },
    {
      "point": "Second technical point with precise detail - use **bold** for technical terms and key findings",
      "quotes": ["First technical quote", "Second supporting data/quote", "Third evidence if relevant"]
    },
    {
      "point": "Third technical point with precise detail - use **bold** for technical terms and key findings",
      "quotes": ["First technical quote", "Second supporting data/quote", "Third evidence if relevant"]
    },
    {
      "point": "Fourth technical point with precise detail - use **bold** for technical terms and key findings",
      "quotes": ["First technical quote", "Second supporting data/quote", "Third evidence if relevant"]
    },
    {
      "point": "Fifth technical point with precise detail - use **bold** for technical terms and key findings",
      "quotes": ["First technical quote", "Second supporting data/quote", "Third evidence if relevant"]
    }
  ]
}

Use **bold** markdown for emphasis. Include exactly 5 points with 2-3 supporting quotes each.'''
    }

def call_openai_summarize(content, api_key, custom_prompt=None):
    """Call OpenAI API for summarization"""
    try:
        # First check if this is an article
        article_check = check_if_article(content, api_key)
        if not article_check['is_article']:
            return {
                'success': True,
                'summary': article_check['message'],
                'is_article': False
            }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        # Use custom prompt if provided, otherwise use default
        if custom_prompt:
            system_content = 'You are a helpful assistant that creates structured summaries with supporting quotes. You MUST return a valid JSON object if the prompt requests JSON format, or follow the exact formatting instructions provided. Extract actual direct quotes from the article text provided. Use **bold** markdown for emphasis on key phrases.'
            user_content = f'{custom_prompt}\n\nWeb page content:\n\n{content}'
            max_tokens = 800  # Allow more tokens for summary sentence + bullet points + quotes
        else:
            system_content = 'You are a helpful assistant that creates concise summaries of web pages. Provide a brief 2-3 sentence summary that captures the main purpose and key information of the page.'
            user_content = f'Please summarize this web page content in 2-3 sentences:\n\n{content}'
            max_tokens = 150

        print(f"🤖 SUMMARIZE OpenAI request details:")
        print(f"   Custom prompt provided: {bool(custom_prompt)}")
        print(f"   System content: {system_content[:200]}...")
        print(f"   User content length: {len(user_content)}")
        print(f"   Max tokens: {max_tokens}")
        if custom_prompt:
            print(f"   Custom prompt length: {len(custom_prompt)}")
            print(f"   Contains 'JSON object': {('JSON object' in custom_prompt)}")
            print(f"   Custom prompt first 300 chars: {custom_prompt[:300]}")

        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {
                    'role': 'system',
                    'content': system_content
                },
                {
                    'role': 'user', 
                    'content': user_content
                }
            ],
            'temperature': 0.3,
            'max_tokens': max_tokens
        }
        
        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=json.dumps(data).encode('utf-8'),
            headers=headers
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))

        summary_content = result['choices'][0]['message']['content']
        print(f"🤖 Generated summary content:")
        print(f"   Raw: {repr(summary_content)}")
        print(f"   Display: {summary_content}")
        print(f"   Length: {len(summary_content)}")
        print(f"   Starts with {{: {summary_content.strip().startswith('{')}")
        print(f"   Contains 'SUMMARY': {('SUMMARY' in summary_content)}")
        print(f"   Contains 'POINTS': {('POINTS' in summary_content)}")
        print(f"   First 200 chars: {summary_content[:200]}")

        return {
            'success': True,
            'summary': summary_content,
            'is_article': True
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'OpenAI API error: {str(e)}'
        }

def call_openai_analyze(content, api_key):
    """Call OpenAI API for sentence analysis"""
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a helpful assistant that analyzes web page content. When given page text, identify and list the top 5 sentences that best convey the purpose and main message of the page. Format your response as a numbered list with just the sentences, no additional commentary.'
                },
                {
                    'role': 'user',
                    'content': f'Here is the page content. Please identify the top 5 sentences that best convey the purpose of this page:\n\n{content}'
                }
            ],
            'temperature': 0.3,
            'max_tokens': 300
        }
        
        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=json.dumps(data).encode('utf-8'),
            headers=headers
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        return {
            'success': True,
            'analysis': result['choices'][0]['message']['content']
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'OpenAI API error: {str(e)}'
        }

def check_if_article(content, api_key):
    """Check if the page content is a single article vs index/landing page"""
    try:
        print(f"\n{'='*60}")
        print(f"🔍 CHECK_IF_ARTICLE FUNCTION CALLED")
        print(f"{'='*60}")
        print(f"📊 Content length: {len(content)} characters")
        print(f"📝 Content preview (first 300 chars):")
        print(f"   {content[:300]}...")
        # Increase content limit significantly for better analysis
        # GPT-3.5-turbo can handle up to ~16k tokens, so we'll use substantial content
        content_limit = min(len(content), 25000)  # Send up to 25k characters
        content_sample = content[:content_limit]

        print(f"📝 Content sample being sent to AI (first 500 chars of {content_limit}):")
        print(f"   {content_sample[:500]}...")
        print(f"🔍 Looking for Substack indicators in content...")

        # Check for Substack indicators
        substack_indicators = ['substack', 'newsletter', 'subscribe', 'casualarchivist']
        found_indicators = [indicator for indicator in substack_indicators if indicator.lower() in content.lower()]
        print(f"🔎 Found Substack indicators: {found_indicators}")

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {
                    'role': 'system',
                    'content': '''You are an expert at identifying web page types. Analyze the given content and determine if it contains a single, substantial article worth summarizing or if it's a different type of page.

ARTICLE/SUMMARIZABLE CONTENT - Look for:
- Single coherent piece of writing (news article, blog post, research paper, tutorial, etc.)
- Clear main topic or thesis
- Substantial body text (typically 200+ words of meaningful content)
- Focused narrative, argument, or information
- May have: author byline, publication date, article headline
- Newsletter posts (Substack, ConvertKit, etc.) with substantial content
- Medium articles, Ghost blog posts, and similar platforms
- Opinion pieces, essays, and editorial content

NON-SUMMARIZABLE CONTENT - Reject if it's:
- Homepage/landing pages (multiple sections, various topics)
- Article listing/category pages (multiple article links/previews)
- Product catalog/shopping pages (multiple products, e-commerce listings)
- Search results pages
- Navigation/directory pages
- Social media feeds or timelines (multiple posts)
- Forum index pages
- Wiki category pages
- News site front pages (multiple story headlines)
- Corporate "About Us" or contact pages
- FAQ pages with multiple unrelated questions
- Course catalogs or event listings
- Restaurant menus or business directories

ALWAYS SUMMARIZABLE (prioritize these):
- Substack newsletter posts (even with author bio, subscription prompts, etc.)
- Medium articles with social elements
- Blog posts on personal or company blogs
- Long-form reviews (single product/service)
- Detailed how-to guides
- Academic papers or documentation
- Press releases (single announcement)
- Wikipedia articles (single topic)
- Newsletter articles from platforms like ConvertKit, Mailchimp, etc.
- Substacks, even if they have sidebars, comments, or subscription elements

IMPORTANT: If the content appears to be from Substack (newsletter platform), LinkedIn articles, Medium, or similar publishing platforms, it should almost always be considered summarizable as long as there's substantial written content.

Respond with JSON: {"is_article": true/false, "confidence": 0-100, "page_type": "article|homepage|listing|navigation|ecommerce|social|other", "reason": "brief explanation of why this is/isn't suitable for summarization"}'''
                },
                {
                    'role': 'user',
                    'content': f'Analyze this page content and determine if it\'s a single article:\n\n{content_sample}'
                }
            ],
            'temperature': 0.1,
            'max_tokens': 350
        }
        
        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=json.dumps(data).encode('utf-8'),
            headers=headers
        )
        
        print(f"🤖 Sending request to OpenAI...")

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))

        gpt_response = result['choices'][0]['message']['content']

        print(f"🤖 OpenAI raw response:")
        print(f"   {gpt_response}")

        try:
            analysis = json.loads(gpt_response)
            is_article = analysis.get('is_article', False)
            page_type = analysis.get('page_type', 'unknown')
            confidence = analysis.get('confidence', 0)
            reason = analysis.get('reason', 'No reason provided')

            print(f"📊 PARSED ANALYSIS RESULTS:")
            print(f"   ✅ Is Article: {is_article}")
            print(f"   🎯 Confidence: {confidence}%")
            print(f"   📁 Page Type: {page_type}")
            print(f"   💭 Reason: {reason}")
            
            if not is_article:
                if page_type == 'homepage':
                    message = "🏠 This appears to be a homepage or main page. Try navigating to a specific article or blog post to summarize."
                elif page_type == 'listing':
                    message = "📋 This appears to be a listing or category page with multiple articles. Please click on a specific article to summarize it."
                elif page_type == 'navigation':
                    message = "🧭 This appears to be a navigation or directory page. Please select a specific article or content page to summarize."
                elif page_type == 'ecommerce':
                    message = "🛒 This appears to be a shopping or product catalog page. This tool is designed for summarizing articles and written content."
                elif page_type == 'social':
                    message = "📱 This appears to be a social media feed or timeline. Try summarizing individual posts or articles instead."
                else:
                    message = f"🔍 This doesn't appear to be a single article suitable for summarization. It looks like a {page_type} page. Try navigating to a specific article, blog post, or news story."

                print(f"❌ FINAL RESULT: NOT AN ARTICLE")
                print(f"   Message: {message}")
                print(f"{'='*60}\n")

                return {
                    'is_article': False,
                    'message': message,
                    'page_type': page_type,
                    'confidence': confidence,
                    'reason': reason
                }
            else:
                print(f"✅ FINAL RESULT: IS AN ARTICLE")
                print(f"   Page Type: {page_type}")
                print(f"   Confidence: {confidence}%")
                print(f"{'='*60}\n")

                return {
                    'is_article': True,
                    'page_type': page_type,
                    'confidence': confidence,
                    'reason': reason
                }

        except json.JSONDecodeError as e:
            print(f"❌ JSON DECODE ERROR: {e}")
            print(f"   Raw response was: {gpt_response}")
            print(f"   Defaulting to: IS AN ARTICLE")
            print(f"{'='*60}\n")
            return {
                'is_article': True,
                'page_type': 'unknown'
            }

    except Exception as e:
        print(f"❌ GENERAL ERROR in check_if_article: {e}")
        print(f"   Defaulting to: IS AN ARTICLE")
        print(f"{'='*60}\n")
        return {
            'is_article': True,
            'page_type': 'unknown'
        }

def create_tables():
    """Create database tables if they don't exist"""
    with app.app_context():
        try:
            # Create all tables defined in models
            db.create_all()
            print("✅ Database tables created/verified")
            
            # List all tables for verification
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📊 Tables in database: {', '.join(tables)}")
            
            if 'feedback' in tables:
                print("✅ Feedback table confirmed")
            else:
                print("⚠️ Feedback table not found - creating...")
                # Try to create just the feedback table
                Feedback.__table__.create(db.engine, checkfirst=True)
                print("✅ Feedback table created")
            
            # Add missing columns to User table if they don't exist
            if 'user' in tables:
                columns = inspector.get_columns('user')
                column_names = [col['name'] for col in columns]
                
                # Add reader_type column if missing
                if 'reader_type' not in column_names:
                    print("📝 Adding reader_type column to User table...")
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE \"user\" ADD COLUMN reader_type VARCHAR(50) DEFAULT 'lifelong_learner'"))
                        conn.commit()
                    print("✅ reader_type column added")
                
                # Add reading_level column if missing
                if 'reading_level' not in column_names:
                    print("📝 Adding reading_level column to User table...")
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE \"user\" ADD COLUMN reading_level VARCHAR(20) DEFAULT 'balanced'"))
                        conn.commit()
                    print("✅ reading_level column added")
                
        except Exception as e:
            print(f"❌ Error with database tables: {e}")
            import traceback
            print(traceback.format_exc())

# Initialize database when module loads (works with gunicorn)
print("🔧 Initializing database tables...")
create_tables()

if __name__ == '__main__':
    
    # Get port from environment, default to 8000 to avoid AirPlay conflict
    port = int(os.environ.get('PORT', 8000))
    
    # Determine if we're in development mode
    is_development = os.getenv('ENVIRONMENT', 'development') == 'development'
    
    if is_development:
        print("🔧 Starting in DEVELOPMENT mode with auto-reload")
        print(f"🚀 Server: http://localhost:{port}")
        print("📝 Debug mode: ON")
        print("🔄 Auto-reload: ON")
        print("⚡ File changes will automatically restart the server")
        print("-" * 50)
        
        # Enable debug mode for development
        app.run(
            host='0.0.0.0', 
            port=port, 
            debug=True,
            use_reloader=True,
            use_debugger=True,
            threaded=True
        )
    else:
        print("🚀 Starting in PRODUCTION mode")
        print(f"📡 Server: http://0.0.0.0:{port}")
        # In production, use gunicorn or similar (not app.run)
        app.run(host='0.0.0.0', port=port, debug=False)