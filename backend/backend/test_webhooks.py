#!/usr/bin/env python3
"""
Simple webhook testing tool for local development
Usage: python test_webhooks.py
"""

import requests
import json
import time
from datetime import datetime

# Configuration
WEBHOOK_URL = "http://localhost:8000/api/webhooks/stripe"
TEST_EVENTS = {
    "1": {
        "name": "Checkout Session Completed",
        "event": {
            "id": "evt_test_webhook",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "mode": "subscription",
                    "subscription": "sub_test_123",
                    "metadata": {
                        "user_id": "1"
                    }
                }
            }
        }
    },
    "2": {
        "name": "Invoice Payment Succeeded",
        "event": {
            "id": "evt_test_webhook",
            "object": "event",
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "id": "in_test_123",
                    "subscription": "sub_test_123",
                    "lines": {
                        "data": [{
                            "period": {
                                "end": int(time.time()) + 2592000  # 30 days from now
                            }
                        }]
                    }
                }
            }
        }
    },
    "3": {
        "name": "Subscription Updated",
        "event": {
            "id": "evt_test_webhook",
            "object": "event",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test_123",
                    "status": "active",
                    "current_period_end": int(time.time()) + 2592000,
                    "items": {
                        "data": [{
                            "price": {
                                "id": "price_test_123"
                            }
                        }]
                    }
                }
            }
        }
    },
    "4": {
        "name": "Payment Failed",
        "event": {
            "id": "evt_test_webhook",
            "object": "event",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "id": "in_test_123",
                    "subscription": "sub_test_123"
                }
            }
        }
    },
    "5": {
        "name": "Subscription Deleted",
        "event": {
            "id": "evt_test_webhook",
            "object": "event",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_test_123"
                }
            }
        }
    }
}

def send_test_webhook(event_data):
    """Send a test webhook to the local server"""
    headers = {
        'Content-Type': 'application/json',
        # For testing without signature verification
        'Stripe-Signature': 'test_signature'
    }
    
    try:
        response = requests.post(WEBHOOK_URL, 
                               data=json.dumps(event_data),
                               headers=headers,
                               timeout=5)
        
        print(f"✅ Response: {response.status_code}")
        print(f"📦 Body: {response.json()}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: Make sure your server is running on localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🧪 Stripe Webhook Tester")
    print("=" * 40)
    print(f"Target URL: {WEBHOOK_URL}")
    print("=" * 40)
    
    # Check if server is running
    try:
        health = requests.get("http://localhost:8000/health", timeout=2)
        print(f"✅ Server is running: {health.json()}")
    except:
        print("❌ Server is not running! Start it with: python app.py")
        return
    
    while True:
        print("\nSelect a webhook to test:")
        for key, value in TEST_EVENTS.items():
            print(f"{key}. {value['name']}")
        print("0. Exit")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == "0":
            print("👋 Goodbye!")
            break
        
        if choice in TEST_EVENTS:
            event = TEST_EVENTS[choice]
            print(f"\n📮 Sending: {event['name']}")
            print(f"📋 Event Type: {event['event']['type']}")
            
            # Update timestamp
            event['event']['created'] = int(time.time())
            
            if send_test_webhook(event['event']):
                print("✅ Webhook sent successfully!")
            else:
                print("❌ Failed to send webhook")
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()