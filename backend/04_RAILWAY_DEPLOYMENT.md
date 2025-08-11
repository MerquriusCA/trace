# Railway Deployment Guide

Complete guide for deploying the Chrome Extension Backend to Railway.

## Prerequisites

- Railway account (railway.app)
- GitHub repository with your backend code
- Stripe account with API keys
- Google OAuth credentials

## Step 1: Railway Project Setup

### Create New Project
1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Connect your GitHub account if not already connected
5. Select your repository: `speed/backend` (or the backend directory)

### Configure Build Settings
Railway should automatically detect your Python app, but verify:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python app.py` 
- **Port**: `8000` (or whatever port your app uses)

## Step 2: Database Configuration

Since you already have a database added:

1. In your Railway project dashboard, verify you have a **PostgreSQL** service
2. The database should automatically provide a `DATABASE_URL` environment variable
3. Format should be: `postgresql://user:password@host:port/database`

## Step 3: Environment Variables

In Railway Project → **Settings** → **Environment Variables**, add:

### Required Variables

```bash
# Application Security
SECRET_KEY=your-super-secure-random-secret-key-min-32-chars

# Google OAuth
GOOGLE_CLIENT_ID=your-google-oauth-client-id

# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_PRICE_ID=price_your_subscription_price_id

# Environment
ENVIRONMENT=production
PORT=8000
```

### Auto-Generated Variables
These should be automatically set by Railway:
- `DATABASE_URL` - PostgreSQL connection string
- `RAILWAY_ENVIRONMENT_ID` - Railway environment identifier

## Step 4: Domain Configuration

### Default Railway Domain
Your app will be automatically available at:
```
https://your-app-name.up.railway.app
```

### Custom Domain (Optional)
1. Go to **Settings** → **Domains**
2. Click **"Custom Domain"**
3. Add your domain (e.g., `api.yourdomain.com`)
4. Update your DNS records as instructed by Railway

## Step 5: Deployment Commands

### Initial Deployment
Railway deploys automatically when you:
1. Push to your connected GitHub branch
2. Or click **"Deploy"** in the Railway dashboard

### Manual Deployment with Railway CLI
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Link to your project (if not already linked)
railway link

# Deploy from backend directory
cd backend
railway up

# Note: The 'railway up' command will:
# 1. Package your backend code
# 2. Upload it to Railway
# 3. Build and deploy automatically
# 4. Show deployment progress in terminal
```

### Quick Deploy for Existing Railway Apps
If you already have a Railway app running:
```bash
# From the backend directory
cd backend

# Check you're logged in
railway whoami

# Check project status
railway status

# Deploy directly
railway up
```

## Step 6: Health Check & Verification

After deployment, test your endpoints:

### Health Endpoint
```bash
curl https://your-app-name.up.railway.app/health
```

Should return:
```json
{
  "status": "healthy",
  "database": "postgresql://...",
  "stripe": "configured",
  "google_oauth": "configured"
}
```

### Admin Dashboard
```bash
https://your-app-name.up.railway.app/admin/dashboard?token=YOUR_TOKEN
```

## Step 7: Chrome Extension Configuration

Update your Chrome extension to use the Railway URL:

In `sidepanel.js` or wherever you define the backend URL:
```javascript
const BACKEND_URL = 'https://your-app-name.up.railway.app';
```

## Environment-Specific Configuration

### Local Development
Create `.env` file in backend directory:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/chrome_extension
SECRET_KEY=dev-secret-key
GOOGLE_CLIENT_ID=your-google-client-id
STRIPE_SECRET_KEY=sk_test_your_test_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_test_key
ENVIRONMENT=local
PORT=8000
```

### Production (Railway)
All variables set through Railway dashboard as above.

## Monitoring & Logs

### View Logs
1. Railway Dashboard → Your Project → **Logs**
2. Or via CLI: `railway logs`

### Monitoring
- Railway provides built-in monitoring
- Check **Metrics** tab for CPU, Memory, Network usage
- Set up alerts in **Settings** → **Notifications**

## Database Management

### Database Access
```bash
# Connect to Railway database
railway connect postgres
```

### Migrations
Your app should handle migrations automatically on startup. If not:
```bash
# Run migrations manually
railway run python init_db.py
```

### Backups
Railway automatically backs up PostgreSQL databases.

## Stripe Webhook Configuration

### Set Webhook URL in Stripe Dashboard
1. Go to Stripe Dashboard → **Webhooks**
2. Add endpoint: `https://your-app-name.up.railway.app/stripe-webhook`
3. Select events you need
4. Copy the webhook secret to Railway environment variables

## Security Considerations

### Environment Variables
- Never commit `.env` files to Git
- Use Railway's encrypted environment variables
- Rotate secrets regularly

### CORS Configuration
Ensure your app allows requests from your Chrome extension domain.

## Troubleshooting

### Common Issues

**Database Connection Fails**
- Verify PostgreSQL service is running in Railway
- Check `DATABASE_URL` format
- Ensure database migrations ran successfully

**Environment Variables Not Found**
- Double-check variable names in Railway dashboard
- Restart deployment after adding variables
- Check for typos in variable names

**Stripe Errors**
- Verify API keys are correct
- Check if using test vs live keys appropriately
- Ensure webhook secret matches

### Debug Commands
```bash
# Check deployed environment
railway run env

# Test database connection
railway run python -c "from app import db; print(db)"

# View recent logs
railway logs --tail
```

## Useful Railway Commands

```bash
# Check project status
railway status

# Open deployed app
railway open

# View environment variables
railway variables

# Connect to database
railway connect postgres

# Run one-off commands
railway run python your_script.py
```

## Production Checklist

- [ ] PostgreSQL database added and connected
- [ ] All environment variables set
- [ ] Health endpoint returns "healthy"
- [ ] Custom domain configured (if needed)
- [ ] Chrome extension updated with production URL
- [ ] Stripe webhooks configured
- [ ] Database migrations completed
- [ ] Logs show no errors
- [ ] Admin dashboard accessible
- [ ] API endpoints working correctly

## Support

- [Railway Documentation](https://docs.railway.app/)
- [Railway Discord](https://discord.gg/railway)
- Railway Dashboard help section

---

**Last Updated**: January 2025
**Railway CLI Version**: Latest