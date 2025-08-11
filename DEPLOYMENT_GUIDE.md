# Trace - Deployment Guide

## 🚀 Quick Deployment Steps

Your repository is now successfully set up at: https://github.com/MerquriusCA/trace

## Railway Deployment

### Step 1: Create New Railway Project

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose `MerquriusCA/trace` repository
5. Select the `backend` directory as the root directory

### Step 2: Add PostgreSQL Database

1. In your Railway project, click "New Service"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically create a database and provide the `DATABASE_URL`

### Step 3: Configure Environment Variables

Click on your backend service and go to "Variables" tab. Add these environment variables:

```bash
# Database (automatically set by Railway when you add PostgreSQL)
DATABASE_URL=[automatically provided by Railway]

# Stripe Configuration (Get from https://dashboard.stripe.com)
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_PRICE_ID=price_your_stripe_price_id

# OpenAI Configuration (Get from https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-your_openai_api_key

# Google OAuth (Get from https://console.cloud.google.com)
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Flask Configuration
SECRET_KEY=your-secret-key-here-generate-random-string
FLASK_ENV=production
FLASK_DEBUG=False

# Admin Configuration
ADMIN_TOKEN=your-admin-token-generate-random-string

# Application URLs
FRONTEND_URL=chrome-extension://your-extension-id
BACKEND_URL=https://your-app.up.railway.app
```

### Step 4: Deploy

1. Railway will automatically deploy when you push to GitHub
2. Get your deployment URL from Railway (e.g., `https://trace-production.up.railway.app`)

### Step 5: Update Chrome Extension

1. Update `manifest.json` to include your Railway URL in `host_permissions`:
```json
"host_permissions": [
  "http://localhost:8000/*",
  "https://your-railway-url.up.railway.app/*",
  "https://api.openai.com/*",
  "https://accounts.google.com/*"
]
```

2. Update the production URL in JavaScript files if needed

### Step 6: Configure Stripe Webhook

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/webhooks)
2. Add endpoint: `https://your-railway-url.up.railway.app/stripe/webhook`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `customer.subscription.updated`
4. Copy the webhook secret and add it to Railway environment variables

## Alternative: Command Line Deployment

If you prefer using Railway CLI:

```bash
# Install Railway CLI if not installed
brew install railway

# Login to Railway
railway login

# Navigate to backend directory
cd backend

# Link to a new project (interactive)
railway link

# Or create a new project directly
railway init

# Add PostgreSQL
railway add postgresql

# Set environment variables
railway variables set STRIPE_SECRET_KEY="sk_live_..."
railway variables set OPENAI_API_KEY="sk-..."
# ... set all other variables

# Deploy
railway up
```

## Verifying Deployment

1. Check deployment logs in Railway dashboard
2. Visit your deployment URL to verify it's running
3. Test the health endpoint: `https://your-railway-url.up.railway.app/health`
4. Check admin dashboard: `https://your-railway-url.up.railway.app/admin/dashboard`
   (requires ADMIN_TOKEN as query parameter)

## Local Development

For local development with the production database:

```bash
# Set up Railway CLI
railway login
cd backend
railway link

# Run locally with production database
railway run python app.py
```

## Troubleshooting

### Common Issues:

1. **Build fails**: Check `runtime.txt` matches Railway's Python version
2. **Database connection fails**: Ensure DATABASE_URL is set correctly
3. **Stripe webhooks fail**: Verify webhook secret and endpoint URL
4. **Google OAuth fails**: Check redirect URIs in Google Console

### Useful Commands:

```bash
# View logs
railway logs

# Open Railway dashboard
railway open

# Check deployment status
railway status

# Redeploy
railway up
```

## Support

- Railway Documentation: https://docs.railway.app
- Stripe Documentation: https://stripe.com/docs
- Google OAuth Setup: https://console.cloud.google.com/apis/credentials

## Next Steps

1. ✅ Repository is at: https://github.com/MerquriusCA/trace
2. 📦 Deploy backend to Railway following steps above
3. 🔑 Configure all environment variables
4. 🎯 Update Chrome extension with production URLs
5. 🚀 Test the complete flow

Good luck with your deployment! 🎉