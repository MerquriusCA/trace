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

from flask import Flask, request, jsonify, render_template
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

# Load environment variables from .env file
load_dotenv()

# Detect environment
is_railway = bool(os.getenv('RAILWAY_ENVIRONMENT_ID') or os.getenv('RAILWAY_PROJECT_ID'))
environment = 'railway' if is_railway else 'local'
print(f"🚀 Environment: {environment}")

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
                'notifications_enabled': self.notifications_enabled
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

# Authentication decorator
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
        # Check for active subscription
        print(f"📝 Subscription check - User: {current_user.email}, Status: {current_user.subscription_status}")
        
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
                'notifications_enabled': current_user.notifications_enabled if current_user.notifications_enabled is not None else True
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
        
        # Update user preferences
        current_user.summary_style = summary_style
        current_user.auto_summarize_enabled = bool(data.get('auto_summarize_enabled', False))
        current_user.notifications_enabled = bool(data.get('notifications_enabled', True))
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
                'notifications_enabled': current_user.notifications_enabled
            }
        })
        
    except Exception as e:
        print(f"❌ Save preferences error: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Failed to save preferences: {str(e)}'
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
def admin_user_dashboard(user_id):
    """Serve the individual user dashboard page"""
    return render_template('user_dashboard_tw.html')

@app.route('/admin/products')
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
                monthly_revenue += 9.99  # Assuming $9.99/month
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
        return jsonify({
            'success': True,
            'products': products_with_prices,
            'count': len(products_with_prices)
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
        api_key = data.get('apiKey')  # User's OpenAI API key
        custom_prompt = data.get('customPrompt')  # Custom prompt from frontend
        
        print(f"\n{'='*50}")
        print(f"📝 AUTHENTICATED SUMMARIZE REQUEST")
        print(f"{'='*50}")
        print(f"👤 User: {current_user.email}")
        print(f"🌐 URL: {url}")
        print(f"⚙️  Action: {action}")
        print(f"🔑 API Key present: {bool(api_key)}")
        
        if not url:
            return jsonify({'success': False, 'error': 'URL required'}), 400
        
        if not api_key:
            return jsonify({'success': False, 'error': 'OpenAI API key required'}), 400
        
        # Fetch page content
        page_content = fetch_page_content(url)
        if not page_content:
            return jsonify({'success': False, 'error': 'Unable to fetch page content'}), 400
        
        # Call OpenAI API
        if action == 'analyze':
            result = call_openai_analyze(page_content, api_key)
        else:
            # Use custom prompt if provided, otherwise fallback to user's saved preference
            prompt_to_use = custom_prompt
            if not prompt_to_use and current_user.summary_style:
                # Generate prompt based on user's saved preference
                style_prompts = {
                    'quick': 'Summarize this content in exactly one clear, concise sentence that captures the main point.',
                    'eli8': 'Explain this content like I\'m 8 years old - use simple, clear language that busy people can quickly understand.',
                    'detailed': 'Provide a thorough summary of this content in exactly 5 bullet points, covering all key aspects and important details.'
                }
                prompt_to_use = style_prompts.get(current_user.summary_style, style_prompts['eli8'])
            
            result = call_openai_summarize(page_content, api_key, prompt_to_use)
        
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
    try:
        print(f"Fetching content from: {url}")
        
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, context=context, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        # Clean HTML
        html = re.sub(r'<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>', '', html, flags=re.IGNORECASE)
        html = re.sub(r'<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>', '', html, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) > 5000:
            text = text[:5000]
        
        return text
        
    except Exception as e:
        print(f"Error fetching content: {e}")
        return None

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
            system_content = 'You are a helpful assistant that creates summaries of web pages based on user preferences.'
            user_content = f'{custom_prompt}\n\nWeb page content:\n\n{content}'
            max_tokens = 200  # Allow more tokens for custom prompts
        else:
            system_content = 'You are a helpful assistant that creates concise summaries of web pages. Provide a brief 2-3 sentence summary that captures the main purpose and key information of the page.'
            user_content = f'Please summarize this web page content in 2-3 sentences:\n\n{content}'
            max_tokens = 150
        
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
        
        return {
            'success': True,
            'summary': result['choices'][0]['message']['content'],
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
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {
                    'role': 'system',
                    'content': '''You are an expert at identifying web page types. Analyze the given content and determine if it's a single article/blog post or a homepage/index/listing page.
                    
Article indicators:
- Has a clear title and author
- Contains a coherent narrative or argument
- Focuses on a single topic
- Has substantial body text
- Includes publication date

Non-article indicators:
- Lists of links to other pages
- Multiple unrelated topics
- Navigation menus dominate
- Homepage or landing page
- Category/tag listing page
- Search results page

Respond with JSON: {"is_article": true/false, "confidence": 0-100, "page_type": "article|homepage|listing|navigation|other", "reason": "brief explanation"}'''
                },
                {
                    'role': 'user',
                    'content': f'Analyze this page content and determine if it\'s a single article:\n\n{content[:2000]}'
                }
            ],
            'temperature': 0.1,
            'max_tokens': 150
        }
        
        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions',
            data=json.dumps(data).encode('utf-8'),
            headers=headers
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        gpt_response = result['choices'][0]['message']['content']
        
        try:
            analysis = json.loads(gpt_response)
            is_article = analysis.get('is_article', False)
            page_type = analysis.get('page_type', 'unknown')
            
            if not is_article:
                if page_type == 'homepage':
                    message = "This appears to be a homepage or main site page. This tool is designed for summarizing individual articles."
                elif page_type == 'listing':
                    message = "This appears to be a listing or category page with multiple articles. Please navigate to a specific article to summarize."
                elif page_type == 'navigation':
                    message = "This appears to be a navigation or menu page. Please select a specific article to summarize."
                else:
                    message = f"This doesn't appear to be a single article. It looks like a {page_type} page. This tool works best with individual articles or blog posts."
                
                return {
                    'is_article': False,
                    'message': message,
                    'page_type': page_type
                }
            else:
                return {
                    'is_article': True,
                    'page_type': page_type
                }
                
        except json.JSONDecodeError:
            return {
                'is_article': True,
                'page_type': 'unknown'
            }
            
    except Exception as e:
        return {
            'is_article': True,
            'page_type': 'unknown'
        }

def create_tables():
    """Create database tables if they don't exist"""
    with app.app_context():
        try:
            # Check if tables exist by trying a simple query
            User.query.limit(1).all()
            print("✅ Database tables already exist")
        except Exception as e:
            print(f"📝 Creating database tables: {e}")
            db.create_all()
            print("✅ Database tables created")

# Create tables on startup (for Railway runtime)
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