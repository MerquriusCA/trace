// Centralized configuration for the Trace extension
const CONFIG = {
  // Backend API configuration
  backend: {
    production: 'https://trace-production-79d5.up.railway.app',
    development: 'http://localhost:8000',
    // Set to 'production' or 'development'
    environment: 'production'
  },
  
  // Get the current backend URL based on environment
  getBackendUrl() {
    return this.backend[this.backend.environment];
  },
  
  // API endpoints
  api: {
    auth: {
      google: '/api/auth/google',
      verify: '/api/auth/verify'
    },
    subscription: {
      status: '/api/subscription/status',
      refresh: '/api/subscription/refresh',
      createCheckout: '/api/subscription/create-checkout-session',
      createPortal: '/api/subscription/create-portal-session',
      cancel: '/api/subscription/cancel'
    },
    summarize: '/api/summarize',
    test: '/api/test',
    preferences: '/api/preferences',
    feedback: '/api/feedback'
  },
  
  // Stripe configuration
  stripe: {
    priceId: 'price_1RpIEaKtat2K2WuIYhlyXSrE' // Production price ID
    // Test: 'price_1RrNm2Ktat2K2WuILiZCzn4M'
  },

  // OAuth configuration
  oauth: {
    production: {
      clientId: '953660294928-e9hfvo7c9rhvobsij5rli2lv5vqj221q.apps.googleusercontent.com',
      extensionId: 'aclegbimjnjckchogjimbgdpinohimon' // Chrome Web Store extension ID
    },
    development: {
      clientId: 'YOUR_DEV_CLIENT_ID_HERE', // Replace with local dev OAuth client ID
      extensionId: 'YOUR_LOCAL_EXTENSION_ID_HERE' // Replace with unpacked extension ID
    },
    scopes: ['openid', 'email', 'profile']
  },

  // Get the current OAuth client ID based on environment
  getOAuthClientId() {
    return this.oauth[this.backend.environment].clientId;
  },
  
  // Debug mode (set to false for production)
  debug: false,
  
  // Logging function that respects debug mode
  log(...args) {
    if (this.debug) {
      console.log(...args);
    }
  },
  
  error(...args) {
    // Always log errors
    console.error(...args);
  }
};

// Make config available globally
if (typeof window !== 'undefined') {
  window.TRACE_CONFIG = CONFIG;
}

// For use in background scripts
if (typeof self !== 'undefined') {
  self.TRACE_CONFIG = CONFIG;
}