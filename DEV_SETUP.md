# Local Development Setup

This guide helps you set up Trace for local development with separate OAuth credentials.

## Quick Start

### 1. Get Your Local Extension ID

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked" and select this directory
4. Copy the **Extension ID** (looks like: `abcdefghijklmnopqrstuvwxyz123456`)

### 2. Create Development OAuth Client

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. Application type: **Chrome Extension**
4. Name: "Trace - Local Development"
5. Extension ID: Paste your local extension ID from step 1
6. Click "Create"
7. Copy the **Client ID**

### 3. Add Redirect URI

In your new OAuth client:
1. Add authorized redirect URI: `https://YOUR_LOCAL_EXTENSION_ID.chromiumapp.org/`
2. Save

### 4. Configure Local Environment

Edit `config.js`:
```javascript
development: {
  clientId: 'YOUR_DEV_CLIENT_ID_HERE', // Paste your dev OAuth client ID
  extensionId: 'YOUR_LOCAL_EXTENSION_ID_HERE' // Paste your local extension ID
}
```

Edit `manifest.dev.json`:
```json
"oauth2": {
  "client_id": "YOUR_DEV_CLIENT_ID_HERE"
}
```

### 5. Switch to Development Mode

```bash
./switch-env.sh dev
```

This will:
- Set `config.js` to use `development` environment
- Enable debug logging
- Use `manifest.dev.json` with your dev OAuth client
- Point to `http://localhost:8000` backend

### 6. Start Local Backend

```bash
cd backend
python app.py
# Backend runs on http://localhost:8000
```

### 7. Reload Extension

1. Go to `chrome://extensions/`
2. Click the refresh icon on Trace (Dev)
3. Extension now uses local backend and dev OAuth

## Switching Back to Production

```bash
./switch-env.sh prod
```

This restores production settings for building Chrome Web Store packages.

## Environment Comparison

| Feature | Development | Production |
|---------|------------|------------|
| Backend URL | http://localhost:8000 | https://trace.hachoo.com |
| OAuth Client | Local dev client | Production client |
| Extension ID | Unpacked extension ID | aclegbimjnjckchogjimbgdpinohimon |
| Debug Logs | Enabled | Disabled |
| Name | "Trace (Dev)" | "Trace" |

## Troubleshooting

### OAuth Error: "bad client id"
- Make sure your dev OAuth client has the correct extension ID
- Check that redirect URI is `https://YOUR_EXTENSION_ID.chromiumapp.org/`
- Verify `manifest.dev.json` has your dev client ID

### Backend Connection Failed
- Make sure local backend is running: `cd backend && python app.py`
- Check `config.js` has `environment: 'development'`
- Verify `host_permissions` in manifest includes `http://localhost:8000/*`

### Changes Not Applying
- Always reload the extension after config changes
- Clear extension storage: Chrome DevTools → Application → Storage → Clear
