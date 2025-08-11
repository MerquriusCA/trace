# Stripe Setup Guide

Complete guide for setting up Stripe payments for the Chrome Extension Backend.

## Prerequisites

- Stripe account (stripe.com)
- Chrome extension backend deployed or running locally
- Basic understanding of webhooks and API keys

## Step 1: Create Stripe Account & Get API Keys

### Sign Up for Stripe
1. Go to [Stripe.com](https://stripe.com) and create an account
2. Complete account verification (may take some time)
3. Access your Stripe Dashboard

### Get API Keys
1. In Stripe Dashboard → **Developers** → **API Keys**
2. Copy your keys:
   - **Publishable Key**: `pk_test_...` (for frontend)
   - **Secret Key**: `sk_test_...` (for backend)

⚠️ **Important**: Start with test keys (contain `test`). Use live keys only when ready for production.

## Step 2: Create Products & Pricing

### Create a Product
1. Stripe Dashboard → **Products** → **Add Product**
2. Fill in details:
   - **Name**: "Pro Subscription" (or your product name)
   - **Description**: "AI-powered web analysis subscription"
   - **Image**: Upload product image (optional)

### Set Up Pricing
1. In the same product creation flow or **Add pricing**:
   - **Pricing Model**: Standard pricing
   - **Price**: $9.99 (or your preferred amount)
   - **Billing Period**: Monthly
   - **Currency**: USD
2. **Save** the product
3. **Copy the Price ID**: `price_...` (you'll need this)

## Step 3: Configure Webhooks

Webhooks notify your backend when payment events occur.

### Create Webhook Endpoint
1. Stripe Dashboard → **Developers** → **Webhooks**
2. **Add Endpoint**
3. **Endpoint URL**: 
   - Local: `http://localhost:8000/stripe-webhook`
   - Production: `https://your-app.up.railway.app/stripe-webhook`

### Select Events
Add these events (essential for subscriptions):
- `customer.subscription.created`
- `customer.subscription.updated` 
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`

### Get Webhook Secret
1. After creating the webhook, click on it
2. **Signing Secret** → **Reveal** → Copy the `whsec_...` value
3. You'll need this for environment variables

## Step 4: Environment Variables

Add these to your environment (Railway, Docker, or `.env`):

### Required Variables
```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
STRIPE_PRICE_ID=price_your_price_id_here
```

### Where to Add Them

**Railway:**
1. Project Dashboard → **Variables**
2. Add each variable

**Docker:**
1. In `docker-compose.yml` environment section
2. Or create `.env` file

**Local Development:**
1. Create `.env` file in backend directory
2. Add variables above

## Step 5: Test the Integration

### Test Products API
```bash
# Check if products are loading
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:8000/api/admin/products
```

Should return your product with pricing information.

### Test Subscription Flow
1. Open Chrome extension
2. Sign in with Google
3. Try to subscribe (use test card: `4242 4242 4242 4242`)
4. Check Stripe Dashboard → **Customers** for new entries

### Verify Webhooks
1. Make a test payment
2. Stripe Dashboard → **Developers** → **Webhooks** → Your endpoint
3. Check **Recent deliveries** for successful events

## Step 6: Test Credit Cards

Use these test cards for different scenarios:

| Scenario | Card Number | CVC | Date |
|----------|-------------|-----|------|
| **Success** | 4242 4242 4242 4242 | Any 3 digits | Any future date |
| **Declined** | 4000 0000 0000 0002 | Any 3 digits | Any future date |
| **Insufficient Funds** | 4000 0000 0000 9995 | Any 3 digits | Any future date |
| **3D Secure** | 4000 0025 0000 3155 | Any 3 digits | Any future date |

## Step 7: Admin Dashboard Integration

Your backend already includes:
- **Product Management**: View all Stripe products at `/admin/products`
- **User Subscriptions**: Monitor user subscriptions at `/admin/dashboard`
- **API Integration**: Direct Stripe API calls for real-time data

### Access Admin Features
```bash
# Generate admin token
python create_test_token.py

# View products
http://localhost:8000/admin/products?token=YOUR_TOKEN

# View users and subscriptions
http://localhost:8000/admin/dashboard?token=YOUR_TOKEN
```

## Step 8: Production Checklist

Before going live:

### Stripe Account
- [ ] Complete business verification in Stripe
- [ ] Activate live payments
- [ ] Replace test API keys with live keys

### Security
- [ ] Enable webhook signature verification
- [ ] Use HTTPS for webhook endpoints
- [ ] Secure environment variables
- [ ] Test with live (small amount) transactions

### Monitoring
- [ ] Set up Stripe email notifications
- [ ] Monitor webhook delivery success
- [ ] Set up error alerting

## Webhook Implementation Details

Your backend handles these webhook events:

```python
# Subscription created/updated
@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    # Verifies webhook signature
    # Updates user subscription status
    # Handles payment success/failure
```

### Key Functions:
- **Subscription Creation**: Updates user status to "active"
- **Payment Success**: Extends subscription period
- **Payment Failed**: Marks subscription as "past_due"
- **Cancellation**: Updates status to "cancelled"

## Troubleshooting

### Common Issues

**Webhook Not Receiving Events**
- Check endpoint URL is correct and accessible
- Verify webhook secret matches environment variable
- Check Stripe logs for delivery attempts

**Products Not Loading**
- Verify Stripe API keys are correct
- Check if products exist in Stripe Dashboard
- Ensure API has proper permissions

**Payment Failures**
- Use test card numbers for testing
- Check Stripe logs for detailed error messages
- Verify webhook endpoints are working

### Debug Commands

```bash
# Test Stripe connection
python test_stripe_products.py

# Check webhook deliveries
# Go to Stripe Dashboard → Webhooks → Recent deliveries

# View backend logs
docker-compose logs -f app
```

## Support Resources

- [Stripe Documentation](https://stripe.com/docs)
- [Stripe Testing](https://stripe.com/docs/testing)
- [Webhook Testing](https://stripe.com/docs/webhooks/test)
- [Stripe CLI](https://stripe.com/docs/stripe-cli) for local webhook testing

---

**Last Updated**: January 2025  
**Stripe API Version**: 2023-10-16