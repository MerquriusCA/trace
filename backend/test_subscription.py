#!/usr/bin/env python3
"""
Test subscription flow locally without webhooks
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_subscription_flow(auth_token, user_email):
    """Test the complete subscription flow"""
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }
    
    print("🧪 Testing Subscription Flow")
    print("=" * 40)
    
    # 1. Check current status
    print("\n1️⃣ Checking current subscription status:")
    response = requests.get(f"{BASE_URL}/api/subscription/status", headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Current status: {data['subscription']['status']}")
        print(f"   Subscription ID: {data['subscription'].get('subscription_id', 'None')}")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return
    
    # 2. Create checkout session
    print("\n2️⃣ Creating checkout session:")
    response = requests.post(
        f"{BASE_URL}/api/subscription/create-checkout-session",
        headers=headers,
        json={"price_id": "price_1RrNm2Ktat2K2WuILiZCzn4M"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Checkout URL: {data.get('checkout_url', 'N/A')}")
        print(f"   Session ID: {data.get('session_id', 'N/A')}")
        print("\n📝 Complete the checkout in your browser, then press Enter to continue...")
        input()
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
        return
    
    # 3. Refresh subscription status
    print("\n3️⃣ Refreshing subscription status from Stripe:")
    response = requests.post(f"{BASE_URL}/api/subscription/refresh", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        sub = data.get('subscription', {})
        print(f"✅ Refreshed status: {sub.get('status', 'unknown')}")
        print(f"   Subscription ID: {sub.get('subscription_id', 'None')}")
        print(f"   Plan ID: {sub.get('plan_id', 'None')}")
        print(f"   Period End: {sub.get('current_period_end', 'None')}")
    else:
        print(f"❌ Failed: {response.status_code} - {response.text}")
    
    # 4. Final status check
    print("\n4️⃣ Final subscription status:")
    response = requests.get(f"{BASE_URL}/api/subscription/status", headers=headers)
    if response.status_code == 200:
        data = response.json()
        status = data['subscription']['status']
        if status == 'active':
            print(f"🎉 Subscription is now ACTIVE!")
        else:
            print(f"⚠️  Subscription status: {status}")
    
    print("\n✅ Test completed!")

def simulate_webhook(session_id, user_id):
    """Simulate a webhook event locally"""
    print("\n🪝 Simulating webhook event...")
    
    webhook_data = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": session_id,
                "mode": "subscription",
                "subscription": "sub_test123",
                "customer": "cus_test123",
                "metadata": {
                    "user_id": str(user_id)
                }
            }
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/webhooks/stripe",
        headers={
            'Content-Type': 'application/json',
            'Stripe-Signature': 'test_signature'
        },
        json=webhook_data
    )
    
    if response.status_code == 200:
        print("✅ Webhook processed successfully")
    else:
        print(f"❌ Webhook failed: {response.status_code} - {response.text}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_subscription.py <auth_token> [user_email]")
        print("\nTo get your auth token:")
        print("1. Open Chrome DevTools in the extension")
        print("2. Look in Application > Local Storage")
        print("3. Find 'authToken' value")
        sys.exit(1)
    
    auth_token = sys.argv[1]
    user_email = sys.argv[2] if len(sys.argv) > 2 else "test@example.com"
    
    test_subscription_flow(auth_token, user_email)