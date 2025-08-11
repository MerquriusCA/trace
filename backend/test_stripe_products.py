#!/usr/bin/env python3
"""
Test Stripe products API connection
"""
import sys
import os
from dotenv import load_dotenv

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from app import app, stripe

def test_stripe_products():
    with app.app_context():
        try:
            print("🔍 Testing Stripe API connection...")
            print(f"✅ Stripe API key configured: {stripe.api_key[:10]}...")
            
            # Test basic connection
            print("📦 Fetching products from Stripe...")
            products = stripe.Product.list(limit=10)
            
            print(f"✅ Successfully connected to Stripe!")
            print(f"📊 Found {len(products.data)} products")
            
            if products.data:
                print("\n📋 Products found:")
                for product in products.data:
                    print(f"  - {product.name} (ID: {product.id}, Active: {product.active})")
            else:
                print("ℹ️  No products found in your Stripe account")
                print("💡 You may need to create products in your Stripe dashboard first")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing Stripe: {e}")
            print(f"🔍 Error type: {type(e).__name__}")
            return False

if __name__ == "__main__":
    test_stripe_products()