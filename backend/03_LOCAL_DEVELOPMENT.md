# Local Development Guide

## Quick Start

1. **Start everything with Docker (Recommended):**
   ```bash
   cd backend
   docker-compose up --build
   ```
   This starts:
   - Flask backend at `http://localhost:8000`
   - PostgreSQL database at `localhost:5433`
   - pgAdmin at `http://localhost:5050`

2. **Chrome Extension is pre-configured for local backend:**
   - Extension now defaults to `http://localhost:8000` 
   - No configuration needed for local development!
   - Just reload the extension if you made changes

3. **Start developing!**
   - Backend will auto-reload on file changes (hot reload)
   - Chrome extension needs manual reload after changes
   - Database persists between restarts

## Features

✅ **Auto-reload**: Backend restarts automatically when you save files
✅ **Debug mode**: Detailed error messages in browser
✅ **PostgreSQL database**: Same as production environment
✅ **Test Stripe keys**: Already configured in .env
✅ **Port 8000**: Avoids macOS AirPlay conflict

## Backend URLs

- **Local**: `http://localhost:8000`
- **Production**: `https://trace-api-production.up.railway.app`
- **Admin Dashboard**: `http://localhost:8000/admin/dashboard` (requires authentication token)
- **Admin Products**: `http://localhost:8000/admin/products` (requires authentication token)

## Switching Between Local and Production

**Extension now defaults to LOCAL backend** (`http://localhost:8000`)

### Use Local Backend (Default):
```javascript
chrome.storage.local.remove(['backendUrl'])  // Use default
```

### Use Production Backend:
```javascript
chrome.storage.local.set({backendUrl: 'https://trace-api-production.up.railway.app/api/summarize'})
```

### Quick Helper Script:
Copy and paste `/use_local_backend.js` content into the extension console for easy switching.

## Accessing the Dashboard

The dashboard requires authentication. Here are two ways to access it:

### Option 1: Generate a Test Token
```bash
# Run the token generation script
cd backend
source speed/bin/activate  # If using virtual environment
python create_test_token.py

# This will output a URL like:
# http://localhost:8000/dashboard?token=YOUR_TOKEN_HERE
```

### Option 2: Use Chrome Extension Authentication
1. Sign in through the Chrome extension with Google
2. The extension will store an auth token
3. Access the admin dashboard at `http://localhost:8000/admin/dashboard`

## Docker Commands

```bash
# Start all services (recommended)
docker-compose up --build

# Start in background
docker-compose up -d --build

# View logs
docker-compose logs -f app

# Stop all services
docker-compose down

# Reset database (removes all data)
docker-compose down -v && docker-compose up -d

# Generate test token for dashboard
docker-compose exec app python create_test_token.py

# Access database directly
docker-compose exec postgres psql -U chrome_user -d chrome_extension
```

## Stripe CLI for Local Webhook Testing

The Stripe CLI allows you to test webhooks locally by forwarding Stripe events to your local backend.

### Install Stripe CLI

**macOS (Homebrew):**
```bash
brew install stripe/stripe-cli/stripe
```

**Other platforms:**
Download from [Stripe CLI releases](https://github.com/stripe/stripe-cli/releases)

### Setup Stripe CLI

```bash
# Login to your Stripe account
stripe login

# This will open a browser to authenticate with your Stripe account
```

### Forward Webhooks to Local Backend

```bash
# Forward Stripe webhooks to your local backend
stripe listen --forward-to localhost:8000/api/webhooks/stripe

# You'll see output like:
# > Ready! Your webhook signing secret is whsec_1234... (^C to quit)
```

### Update Environment Variables

Copy the webhook signing secret from the CLI output and add it to your environment:

**Docker (add to docker-compose.yml):**
```yaml
environment:
  - STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_from_cli
```

**Manual setup (.env file):**
```bash
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_from_cli
```

### Test Webhook Events

In a separate terminal, trigger test events:

```bash
# Test successful payment
stripe trigger payment_intent.succeeded

# Test subscription created
stripe trigger customer.subscription.created

# Test subscription updated
stripe trigger customer.subscription.updated

# View all available events
stripe trigger --help
```

### Monitor Webhook Events

You should see webhook events in:
1. **Stripe CLI output**: Shows events being forwarded
2. **Backend logs**: `docker-compose logs -f app`
3. **Your backend webhook endpoint**: Processing the events

### Typical Development Workflow

```bash
# Terminal 1: Start backend services
docker-compose up --build

# Terminal 2: Start Stripe webhook forwarding
stripe listen --forward-to localhost:8000/api/webhooks/stripe

# Terminal 3: Trigger test events or use your Chrome extension
stripe trigger customer.subscription.created
```

## Environment Variables

### Docker Setup (Recommended)
Environment variables are configured in `docker-compose.yml`. No `.env` file needed!

### Manual Setup
If running without Docker, create `.env` file:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/chrome_extension
PORT=8000
SECRET_KEY=your-dev-secret-key
GOOGLE_CLIENT_ID=your-google-client-id
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
```

## Troubleshooting

### Docker Issues
1. **Port already in use**: `docker-compose down` then try again
2. **Database connection fails**: `docker-compose down -v` to reset volumes
3. **Container won't start**: Check `docker-compose logs app` or `docker-compose logs postgres`

### General Issues
1. **Extension can't connect**: Check CORS and backend URL
2. **Database errors**: Ensure PostgreSQL container is running
3. **Import errors**: Use `docker-compose exec app` to run commands in container

## Tips

- Keep Chrome DevTools open to see API calls
- Use `console.log` liberally in both backend and extension
- Flask debug mode shows detailed error pages
- Check Network tab for failed requests