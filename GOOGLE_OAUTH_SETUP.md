# Google OAuth Setup Guide for Trace Extension

## Fix the OAuth Error

The error "bad client id" indicates that the Google OAuth client ID needs to be properly configured. Follow these steps:

## Step 1: Get Your Chrome Extension ID

1. Open Chrome and go to `chrome://extensions/`
2. Find your "Trace" extension
3. Copy the Extension ID (looks like: `odhobgmlohpeilfgnlomeihcnncmeggc`)

## Step 2: Create/Update Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project or create a new one
3. Navigate to **APIs & Services** → **Credentials**

### Create OAuth 2.0 Client ID for Chrome Extension:

1. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
2. Select **Chrome Extension** as the application type
3. Enter:
   - **Name**: Trace Chrome Extension
   - **Extension ID**: [Your extension ID from Step 1]
4. Click **Create**
5. Copy the generated Client ID

## Step 3: Update Your Extension

1. Update `manifest.json` with your new client ID:

```json
"oauth2": {
  "client_id": "YOUR_NEW_CLIENT_ID.apps.googleusercontent.com",
  "scopes": ["openid", "email", "profile"]
}
```

2. Make sure the client ID is complete and ends with `.apps.googleusercontent.com`

## Step 4: Configure OAuth Consent Screen

1. In Google Cloud Console, go to **APIs & Services** → **OAuth consent screen**
2. Configure:
   - **App name**: Trace
   - **User support email**: Your email
   - **App domain**: (can be left empty for testing)
   - **Authorized domains**: (can be left empty for testing)
   - **Developer contact**: Your email
3. Add scopes:
   - `openid`
   - `email`
   - `profile`
4. Add test users if in testing mode

## Step 5: Enable Required APIs

In Google Cloud Console, enable these APIs:
1. Go to **APIs & Services** → **Library**
2. Search and enable:
   - Google+ API (deprecated but sometimes still needed)
   - Google Identity Toolkit API
   - Chrome Web Store API (if publishing)

## Step 6: Update Backend Configuration

If you have a backend, update the environment variables:

```bash
GOOGLE_CLIENT_ID=your_new_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret  # Only for backend, not extension
```

## Step 7: Test the Configuration

1. Reload your extension in Chrome
2. Try signing in again
3. You should see Google's OAuth consent screen

## Common Issues and Solutions

### Issue: "bad client id" error
**Solution**: Ensure the client ID in manifest.json matches exactly what's in Google Cloud Console

### Issue: Extension ID changed
**Solution**: Update the Extension ID in Google Cloud Console OAuth credentials

### Issue: "Invalid OAuth client" 
**Solution**: Make sure you selected "Chrome Extension" as the application type, not "Web application"

### Issue: Scopes not working
**Solution**: Ensure scopes in manifest.json match what's configured in OAuth consent screen

## Testing with Different Client ID

For testing, you can use a test client ID. Create a new OAuth client specifically for development:

1. Create a new OAuth 2.0 Client ID
2. Type: Chrome Extension
3. Extension ID: Your unpacked extension ID
4. Use this for local development

## Production Setup

For production:
1. Publish your extension to Chrome Web Store
2. Use the permanent Extension ID from the store
3. Create a production OAuth client with that ID
4. Update manifest.json before publishing

## Quick Checklist

- [ ] Extension ID copied from chrome://extensions/
- [ ] OAuth 2.0 Client created as "Chrome Extension" type
- [ ] Client ID updated in manifest.json
- [ ] OAuth consent screen configured
- [ ] Required APIs enabled
- [ ] Extension reloaded after changes
- [ ] Test sign-in working

## Need a New Client ID?

If you need to create a fresh client ID:

1. Go to https://console.cloud.google.com
2. Create a new project called "Trace"
3. Follow steps 2-4 above
4. Your new client ID will be in format: `XXXXXXXXXXXXX-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX.apps.googleusercontent.com`

Remember to reload your extension after any manifest.json changes!