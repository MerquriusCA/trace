# Getting Started - Chrome Extension Local Development

Quick guide to test this Chrome extension locally with the backend.

## Prerequisites

- Chrome browser
- Docker & Docker Compose
- Git

## 1. Start the Backend (Required)

```bash
cd backend
docker-compose up --build
```

This starts:
- Flask backend at `http://localhost:8000`
- PostgreSQL database
- All required services

## 2. Load the Chrome Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable **"Developer mode"** (toggle in top right)
3. Click **"Load unpacked"**
4. Select the `speed/` folder (this directory)
5. The extension should now appear in your extensions list

## 3. Test the Extension

1. **Pin the extension**: Click the puzzle piece icon in Chrome toolbar, then pin the Speed extension
2. **Open side panel**: Click the Speed extension icon to open the side panel
3. **Navigate to any webpage**: The extension will show the page title
4. **Test summarization**: Click "Summarize" or "Analyze" buttons

## 4. Extension Features

- **Side Panel**: Main interface (opens on right side of browser)
- **Page Summarization**: AI-powered content summaries
- **Page Analysis**: Key sentence extraction
- **User Authentication**: Google sign-in integration
- **Subscription Management**: Stripe integration for premium features

## 5. Development Workflow

1. **Make extension changes**: Edit files in `speed/` directory
2. **Reload extension**: Go to `chrome://extensions/` and click the reload icon
3. **Backend changes**: Auto-reload with Docker (no restart needed)
4. **Test**: Use the side panel to test your changes

## 6. Useful Development Links

- **Admin Dashboard**: `http://localhost:8000/admin/dashboard` (requires auth)
- **Backend API**: `http://localhost:8000/api/`
- **Extension Console**: Right-click extension → "Inspect" → Console tab

## 7. Troubleshooting

**Extension not loading?**
- Check that all files are in the `speed/` directory
- Ensure `manifest.json` exists and is valid
- Look for errors in `chrome://extensions/`

**Backend connection issues?**
- Ensure Docker containers are running: `docker-compose ps`
- Check backend logs: `docker-compose logs -f app`
- Extension defaults to `http://localhost:8000`

**Side panel not opening?**
- Chrome 114+ required for side panel API
- Try reloading the extension
- Check browser console for errors

## Next Steps

For detailed setup and configuration, see:
- `backend/01_STRIPE_SETUP.md` - Stripe integration
- `backend/02_DOCKER_SETUP.md` - Docker configuration details
- `backend/03_LOCAL_DEVELOPMENT.md` - Advanced development guide
- `backend/04_RAILWAY_DEPLOYMENT.md` - Production deployment

## Quick Commands

```bash
# Start everything
cd backend && docker-compose up --build

# View backend logs
docker-compose logs -f app

# Stop everything
docker-compose down

# Reset database
docker-compose down -v && docker-compose up -d
```

That's it! You should now have the Chrome extension running locally with a fully functional backend.