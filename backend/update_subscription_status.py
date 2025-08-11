#!/usr/bin/env python3
"""
Update user subscription status - either manually or by fetching from Stripe
"""
import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from app import app, db, User, stripe

def update_user_subscription(user_id, check_stripe=False):
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            print(f"User with ID {user_id} not found!")
            return
        
        print(f"Current status for {user.email}:")
        print(f"  Subscription Status: {user.subscription_status}")
        print(f"  Stripe Customer ID: {user.stripe_customer_id}")
        print(f"  Subscription ID: {user.subscription_id}")
        print("-" * 50)
        
        if check_stripe and user.stripe_customer_id:
            print("Checking Stripe for subscription status...")
            try:
                # Get subscriptions from Stripe
                subscriptions = stripe.Subscription.list(
                    customer=user.stripe_customer_id,
                    limit=1
                )
                
                if subscriptions.data:
                    sub = subscriptions.data[0]
                    print(f"Found Stripe subscription: {sub.id}")
                    print(f"  Status: {sub.status}")
                    print(f"  Current period end: {datetime.fromtimestamp(sub.current_period_end)}")
                    
                    # Update user in database
                    user.subscription_status = sub.status
                    user.subscription_id = sub.id
                    user.current_period_end = datetime.fromtimestamp(sub.current_period_end)
                    user.plan_id = sub.items.data[0].price.id if sub.items.data else None
                    db.session.commit()
                    print("✅ Updated user subscription from Stripe!")
                else:
                    print("No active subscriptions found in Stripe")
            except Exception as e:
                print(f"Error checking Stripe: {e}")
        else:
            # Manual update for testing
            print("\nManually updating subscription to ACTIVE status for testing...")
            user.subscription_status = 'active'
            user.subscription_id = 'sub_test_123456'
            user.current_period_end = datetime.utcnow() + timedelta(days=30)
            user.plan_id = 'price_test_pro'
            
            # If no Stripe customer ID, create a test one
            if not user.stripe_customer_id:
                user.stripe_customer_id = f'cus_test_{user.id}'
            
            db.session.commit()
            print("✅ Manually updated user subscription to ACTIVE!")
        
        # Show updated status
        print("\nUpdated status:")
        print(f"  Subscription Status: {user.subscription_status}")
        print(f"  Stripe Customer ID: {user.stripe_customer_id}")
        print(f"  Subscription ID: {user.subscription_id}")
        print(f"  Current Period End: {user.current_period_end}")
        print(f"  Plan ID: {user.plan_id}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Update user subscription status')
    parser.add_argument('--user-id', type=int, default=2, help='User ID to update (default: 2)')
    parser.add_argument('--check-stripe', action='store_true', help='Check Stripe for actual subscription')
    args = parser.parse_args()
    
    update_user_subscription(args.user_id, args.check_stripe)