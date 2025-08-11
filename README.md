# Trace - Chrome Extension

Trace is an intelligent Chrome extension that enhances your web browsing experience with AI-powered page summarization and analysis.

## Features

- 🔍 **Intelligent Page Analysis** - Get instant summaries and insights from any webpage
- 🎨 **Modern Side Panel Interface** - Clean, responsive UI that doesn't interrupt your browsing
- 🔐 **Google OAuth Integration** - Secure authentication with your Google account
- 💳 **Subscription Management** - Premium features with Stripe integration
- 🚀 **Fast & Reliable** - Powered by OpenAI's GPT models
- 🛠️ **Developer Friendly** - Easy local development with Docker

## Project Structure

```
trace/
├── manifest.json          # Chrome extension configuration
├── popup.html/js/css      # Extension popup interface
├── sidepanel.html/js/css  # Side panel interface
├── background.js          # Background service worker
├── content.js            # Content script for page interaction
└── backend/              # Flask backend API
    ├── app.py           # Main Flask application
    ├── Dockerfile       # Docker configuration
    └── docker-compose.yml # Local development setup
```

## Quick Start

### Chrome Extension Setup

1. Clone the repository:
```bash
git clone https://github.com/davidmerqurius/trace.git
cd trace
```

2. Load the extension in Chrome:
   - Open Chrome and navigate to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" and select the `trace` directory

### Backend Development

1. Start the backend with Docker:
```bash
cd backend
docker-compose up --build
```

2. The backend will be available at `http://localhost:8000`

## Environment Variables

Copy `backend/.env.example` to `backend/.env.docker` and fill in your credentials:

```bash
cp backend/.env.example backend/.env.docker
```

Required variables:
- `DATABASE_URL` - PostgreSQL connection string
- `STRIPE_SECRET_KEY` - Your Stripe secret key (use test key for development)
- `OPENAI_API_KEY` - Your OpenAI API key
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `SECRET_KEY` - Flask secret key

## Railway Deployment

### Prerequisites
- Railway CLI installed (`brew install railway`)
- GitHub repository connected
- Railway account

### Deployment Steps

1. **Link to Railway Project:**
```bash
cd backend
railway link
```

2. **Set Environment Variables:**
```bash
# Set required environment variables
railway variables set DATABASE_URL="your-postgres-url"
railway variables set STRIPE_SECRET_KEY="sk_live_..."
railway variables set STRIPE_PUBLISHABLE_KEY="pk_live_..."
railway variables set STRIPE_WEBHOOK_SECRET="whsec_..."
railway variables set STRIPE_PRICE_ID="price_..."
railway variables set OPENAI_API_KEY="sk-..."
railway variables set GOOGLE_CLIENT_ID="your-client-id"
railway variables set GOOGLE_CLIENT_SECRET="your-client-secret"
railway variables set SECRET_KEY="your-secret-key"
railway variables set ADMIN_TOKEN="your-admin-token"
```

3. **Deploy:**
```bash
railway up
```

Or connect GitHub for automatic deployments:
```bash
# In Railway dashboard:
# 1. Go to your project settings
# 2. Connect GitHub repo
# 3. Set branch to 'main'
# 4. Set root directory to '/backend'
```

### Database Setup

Railway provides PostgreSQL:
1. Add PostgreSQL service in Railway dashboard
2. Copy the `DATABASE_URL` from the PostgreSQL service
3. Set it as an environment variable in your backend service

## Production Configuration

### Update Chrome Extension

1. Update the backend URL in `manifest.json`:
```json
"host_permissions": [
  "https://trace-api-production.up.railway.app/*"
]
```

2. Update the production URL in `use_local_backend.js`

### Stripe Webhook

Configure webhook endpoint in Stripe Dashboard:
- Endpoint URL: `https://your-railway-url.up.railway.app/stripe/webhook`
- Events to listen: `checkout.session.completed`, `customer.subscription.deleted`

## Development Commands

```bash
# Local development with hot reload
cd backend
docker-compose up

# Run tests
python -m pytest

# Database migrations
python init_db.py

# Create admin token
python create_test_token.py
```

## API Endpoints

- `POST /api/summarize` - Summarize webpage content
- `POST /api/auth/google` - Google OAuth authentication
- `GET /api/subscription/status` - Check subscription status
- `POST /api/subscription/create-checkout` - Create Stripe checkout session
- `GET /admin/dashboard` - Admin dashboard (requires token)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is private and proprietary.

## Support

For issues or questions, please open an issue on GitHub.