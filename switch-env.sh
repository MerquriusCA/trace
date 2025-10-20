#!/bin/bash

# Script to switch between development and production environments

ENV=$1

if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
    echo "Usage: ./switch-env.sh [dev|prod]"
    exit 1
fi

if [ "$ENV" = "dev" ]; then
    echo "🔧 Switching to DEVELOPMENT mode..."
    
    # Update config.js to use development environment
    sed -i.bak "s/environment: 'production'/environment: 'development'/" config.js
    sed -i.bak "s/debug: false/debug: true/" config.js
    
    # Use development manifest
    cp manifest.dev.json manifest.json
    
    echo "✅ Switched to DEVELOPMENT mode"
    echo "📝 Don't forget to:"
    echo "   1. Get your local extension ID from chrome://extensions/"
    echo "   2. Update manifest.dev.json with your dev OAuth client ID"
    echo "   3. Update config.js development.clientId and extensionId"
    echo "   4. Reload the extension in Chrome"
    
else
    echo "🚀 Switching to PRODUCTION mode..."
    
    # Update config.js to use production environment
    sed -i.bak "s/environment: 'development'/environment: 'production'/" config.js
    sed -i.bak "s/debug: true/debug: false/" config.js
    
    # Restore production manifest from git
    git checkout manifest.json
    
    echo "✅ Switched to PRODUCTION mode"
    echo "📝 Ready to build for Chrome Web Store"
fi

# Clean up backup files
rm -f config.js.bak

echo ""
echo "Current config:"
echo "  Environment: $(grep "environment:" config.js | head -1)"
echo "  Debug: $(grep "debug:" config.js | head -1)"
echo "  OAuth Client: $(grep "client_id" manifest.json)"
