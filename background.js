// Background script for Chrome Extension
importScripts('config.js');

let extensionEnabled = true;
let pageTitles = new Map(); // Store page titles
let authToken = null;
let currentUser = null;

const config = self.TRACE_CONFIG;

// Initialize extension state
chrome.runtime.onInstalled.addListener(() => {
  initializeExtensionState();
});

// Initialize on startup as well
chrome.runtime.onStartup.addListener(() => {
  initializeExtensionState();
});

// Initialize extension state from storage
async function initializeExtensionState() {
  try {
    const result = await chrome.storage.local.get(['extensionEnabled', 'authToken', 'currentUser']);
    extensionEnabled = result.extensionEnabled !== false; // Default to true
    authToken = result.authToken;
    currentUser = result.currentUser;
    config.log('Extension state initialized:', { extensionEnabled, hasToken: !!authToken, hasUser: !!currentUser });
  } catch (error) {
    config.error('Failed to initialize extension state:', error);
    // Set safe defaults
    extensionEnabled = true;
    authToken = null;
    currentUser = null;
  }
}

// Combined message listener - handles all message types
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // Handle different message types
  switch(request.action) {
    case 'toggleExtension':
      extensionEnabled = request.enabled;
      config.log('Extension is now:', extensionEnabled ? 'ON' : 'OFF');
      break;
      
    case 'pageLoaded':
      if (extensionEnabled && sender.tab) {
        pageTitles.set(sender.tab.id, {
          title: request.title,
          url: request.url,
          timestamp: Date.now()
        });
        config.log('Page loaded:', request.title);
      }
      break;
      
    case 'checkEnabled':
      sendResponse({enabled: extensionEnabled});
      break;
      
      
    case 'summarizePage':
      handleSummarizePage(request, sendResponse);
      return true;

    case 'summarizeHTML':
      handleSummarizeHTML(request, sendResponse);
      return true;

    case 'testBackend':
      handleTestBackend(sendResponse);
      return true;
      
    case 'googleAuth':
      authenticateWithGoogle(sendResponse);
      return true;
      
    case 'logout':
      logout(sendResponse);
      return true;
      
    case 'checkAuth':
      checkAuthStatus(sendResponse);
      return true;
      
    case 'getSubscriptionStatus':
      getSubscriptionStatus(sendResponse);
      return true;

    case 'createCheckoutSession':
      createCheckoutSession(request.priceId, sendResponse);
      return true;

    case 'refreshSubscriptionStatus':
      refreshSubscriptionStatus(sendResponse);
      return true;

    case 'forceAuthRefresh':
      forceAuthRefresh(sendResponse);
      return true;
      
    case 'savePreferences':
      config.log('Background: Received savePreferences request:', request.preferences);
      saveUserPreferences(request.preferences, sendResponse);
      return true;
      
    case 'loadPreferences':
      loadUserPreferences(sendResponse);
      return true;
      
    case 'sendFeedback':
      config.log('Background: Received feedback request');
      sendFeedback(request.feedback, sendResponse);
      return true;
  }
});

// Clean up stored titles when tabs are closed
chrome.tabs.onRemoved.addListener((tabId) => {
  pageTitles.delete(tabId);
});

// Optional: Alert user when visiting a new page (if extension is enabled)
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && extensionEnabled && tab.url) {
    // You could add notifications or other features here
    config.log('Tab updated:', tab.title);
  }
});

// Open side panel when extension icon is clicked
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ windowId: tab.windowId });

  // Refresh auth state after panel opens (helps with post-checkout auth)
  initializeExtensionState();
});

// Function to check if URL is accessible
function isAccessibleUrl(url) {
  if (!url) return false;
  
  // List of URL patterns that extensions cannot access
  const restrictedPatterns = [
    /^chrome:\/\//,
    /^chrome-extension:\/\//,
    /^edge:\/\//,
    /^about:/,
    /^data:/,
    /^view-source:/,
    /^https:\/\/chrome\.google\.com\/webstore/,
    /^https:\/\/chromewebstore\.google\.com/
  ];
  
  return !restrictedPatterns.some(pattern => pattern.test(url));
}

// Function to get page content from tab
async function getPageContent(tabId) {
  try {
    // First check if we can access this tab
    const tab = await chrome.tabs.get(tabId);
    if (!isAccessibleUrl(tab.url)) {
      config.log('Cannot access restricted URL:', tab.url);
      return null;
    }
    
    const results = await chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: () => {
        // Get text content from the page
        const bodyText = document.body.innerText || document.body.textContent || '';
        return bodyText.substring(0, 5000); // Limit to first 5000 characters
      }
    });
    return results[0]?.result || '';
  } catch (error) {
    config.error('Error getting page content:', error);
    return null;
  }
}


// Helper function to get backend base URL
async function getBackendBaseUrl() {
  return config.getBackendUrl();
}

// Authentication Functions
async function authenticateWithGoogle(sendResponse) {
  try {
    config.log('🔄 Starting Google authentication...');
    
    // Clear any cached tokens first
    chrome.identity.clearAllCachedAuthTokens(() => {
      config.log('🔄 Cleared cached tokens');
      
      // Use the simpler Chrome Identity API
      chrome.identity.getAuthToken({ 
        interactive: true 
      }, async function(token) {
        if (chrome.runtime.lastError || !token) {
          config.error('Auth error:', chrome.runtime.lastError);
          sendResponse({ success: false, error: chrome.runtime.lastError?.message || 'Failed to get token' });
          return;
        }

        try {
          config.log('✅ Received token from Chrome Identity API');
          
          // Get user info from Google
          const userInfoResponse = await fetch('https://www.googleapis.com/oauth2/v2/userinfo', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          
          if (!userInfoResponse.ok) {
            throw new Error('Failed to get user info');
          }
          
          const userInfo = await userInfoResponse.json();
          config.log('Got user info:', { email: userInfo.email, name: userInfo.name });
          
          // Send to backend for authentication
          const backendUrl = `${config.getBackendUrl()}${config.api.auth.google}`;
          config.log('🔗 API CALL: Google Authentication');
          config.log('📍 Endpoint:', backendUrl);
          
          const response = await fetch(backendUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              access_token: token,
              user_info: userInfo
            })
          });

          if (!response.ok) {
            const errorData = await response.text();
            config.error('Backend response:', errorData);
            throw new Error('Backend authentication failed');
          }

          const data = await response.json();
          
          // Store authentication data
          authToken = data.token;
          currentUser = data.user;
          
          await chrome.storage.local.set({
            authToken: authToken,
            currentUser: currentUser
          });

          config.log('✅ Authentication successful for:', currentUser.email);
          sendResponse({ 
            success: true, 
            user: currentUser,
            token: authToken
          });

        } catch (error) {
          config.error('Authentication error:', error);
          sendResponse({ success: false, error: error.message });
        }
      });
    });

  } catch (error) {
    config.error('Auth setup error:', error);
    sendResponse({ success: false, error: error.message });
  }
}

async function logout(sendResponse) {
  try {
    // Get the current token first
    const currentToken = authToken;
    
    // Clear stored authentication
    authToken = null;
    currentUser = null;
    
    await chrome.storage.local.remove(['authToken', 'currentUser']);
    
    // Revoke Google token if exists
    if (currentToken) {
      try {
        await chrome.identity.removeCachedAuthToken({ token: currentToken });
        config.log('✅ Cached token removed');
        
        // Also revoke the token server-side
        await fetch(`https://oauth2.googleapis.com/revoke?token=${currentToken}`, {
          method: 'POST'
        });
        config.log('✅ Token revoked server-side');
      } catch (e) {
        config.log('⚠️ Error revoking token:', e);
      }
    }

    // Clear all cached auth tokens for this extension
    chrome.identity.clearAllCachedAuthTokens(() => {
      config.log('✅ All cached tokens cleared');
    });

    sendResponse({ success: true });
  } catch (error) {
    config.error('Logout error:', error);
    sendResponse({ success: false, error: error.message });
  }
}

async function checkAuthStatus(sendResponse) {
  if (!authToken || !currentUser) {
    sendResponse({ authenticated: false });
    return;
  }

  try {
    // Verify token with backend
    const backendUrl = `${config.getBackendUrl()}${config.api.auth.verify}`;
    config.log('🔗 API CALL: Verify Authentication');
    config.log('📍 Endpoint:', backendUrl);
    
    const response = await fetch(backendUrl, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    if (response.ok) {
      const data = await response.json();
      currentUser = data.user;
      await chrome.storage.local.set({ currentUser: currentUser });
      sendResponse({ 
        authenticated: true, 
        user: currentUser 
      });
    } else {
      // Token is invalid, clear it
      authToken = null;
      currentUser = null;
      await chrome.storage.local.remove(['authToken', 'currentUser']);
      sendResponse({ authenticated: false });
    }
  } catch (error) {
    config.error('Auth check error:', error);
    sendResponse({ authenticated: false });
  }
}

async function getSubscriptionStatus(sendResponse) {
  if (!authToken) {
    sendResponse({ success: false, error: 'Not authenticated' });
    return;
  }

  try {
    const backendUrl = `${config.getBackendUrl()}${config.api.subscription.status}`;
    config.log('🔗 API CALL: Get Subscription Status');
    config.log('📍 Endpoint:', backendUrl);

    const response = await fetch(backendUrl, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    if (response.ok) {
      const data = await response.json();
      sendResponse(data);
    } else {
      throw new Error('Failed to get subscription status');
    }
  } catch (error) {
    config.error('Subscription status error:', error);
    sendResponse({ success: false, error: error.message });
  }
}


async function createCheckoutSession(priceId, sendResponse) {
  if (!authToken) {
    sendResponse({ success: false, error: 'Not authenticated' });
    return;
  }

  try {
    const backendUrl = `${config.getBackendUrl()}${config.api.subscription.createCheckout}`;
    config.log('🔗 API CALL: Create Checkout Session');
    config.log('📍 Endpoint:', backendUrl);
    
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
      },
      body: JSON.stringify({
        price_id: priceId
      })
    });

    if (response.ok) {
      const data = await response.json();
      sendResponse(data);
    } else {
      throw new Error('Failed to create checkout session');
    }
  } catch (error) {
    config.error('Checkout session error:', error);
    sendResponse({ success: false, error: error.message });
  }
}

async function refreshSubscriptionStatus(sendResponse) {
  if (!authToken) {
    sendResponse({ success: false, error: 'Not authenticated' });
    return;
  }

  try {
    const backendUrl = `${config.getBackendUrl()}${config.api.subscription.refresh}`;
    config.log('🔗 API CALL: Refresh Subscription Status');
    config.log('📍 Endpoint:', backendUrl);
    
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    if (response.ok) {
      const data = await response.json();
      config.log('✅ Subscription refresh successful:', data);
      sendResponse(data);
    } else {
      const error = await response.json();
      throw new Error(error.error || 'Failed to refresh subscription status');
    }
  } catch (error) {
    config.error('Subscription refresh error:', error);
    sendResponse({ success: false, error: error.message });
  }
}

// Handler functions for different message types

async function handleSummarizePage(request, sendResponse, retryCount = 0) {
    config.log('Received summarizePage request with tabId:', request.tabId);
    chrome.storage.local.get(['backendUrl'], async (result) => {

      // Get the current tab info
      let tab, url;
      try {
        tab = await chrome.tabs.get(request.tabId);
        config.log('Full tab object for summarize:', tab);
        url = tab.url;
        config.log('Got tab URL for summarize:', url);
        if (!url) {
          config.error('Tab exists but URL is undefined:', tab);
          sendResponse({success: false, error: 'Tab URL is not available'});
          return;
        }
      } catch (error) {
        config.error('Failed to get tab for summarize:', error);
        sendResponse({success: false, error: 'Unable to get current tab URL'});
        return;
      }

      // Always use backend service for all URLs
      const backendUrl = `${config.getBackendUrl()}${config.api.summarize}`;

      try {
        config.log('🔗 API CALL: Backend Service');
        config.log('📍 Endpoint:', backendUrl);
        config.log('🎯 Action: summarizePage');
        config.log('🌐 Page URL:', url);
        config.log('🔑 Auth token present:', !!authToken);
        config.log('📦 Request body:', JSON.stringify({
          url: url
        }, null, 2));

        const headers = {
          'Content-Type': 'application/json'
        };

        // Add auth token if available
        if (authToken) {
          headers['Authorization'] = `Bearer ${authToken}`;
          config.log('✅ Added auth token to request');
        } else {
          config.log('⚠️ No auth token available');
        }

        config.log('📡 Making fetch request to:', backendUrl);

        const requestBody = {
          url: url
        };

        // Add custom prompt if provided
        if (request.customPrompt) {
          requestBody.customPrompt = request.customPrompt;
          config.log('📝 Custom prompt provided:', request.customPrompt.substring(0, 100) + '...');
        }

        const response = await fetch(backendUrl, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(requestBody)
        }).catch(error => {
          config.error('🚨 Fetch failed:', error);
          throw new Error(`Network error: ${error.message}. Check if Railway backend is deployed and running.`);
        });

        config.log('📥 Response status:', response.status);
        config.log('📥 Response headers:', Object.fromEntries(response.headers.entries()));

        // Handle 401 - token expired, refresh and retry once
        if (response.status === 401 && retryCount === 0) {
          config.log('🔄 Token expired during summarize, refreshing and retrying...');

          // Refresh auth state
          await initializeExtensionState();

          // Retry the request with the new token
          handleSummarizePage(request, sendResponse, 1);
          return;
        }

        // Check content type before parsing
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          const text = await response.text();
          config.error('Non-JSON response:', text.substring(0, 500));
          throw new Error(`Backend returned non-JSON response (${response.status}). Response: ${text.substring(0, 100)}...`);
        }

        if (!response.ok) {
          const error = await response.json();
          config.error('❌ Backend error response:', error);
          throw new Error(error.error || `Backend service error (${response.status})`);
        }

        const data = await response.json();
        config.log('✅ Successful response received');
        config.log('📊 Response includes summary_data:', !!data.summary_data);
        sendResponse({
          success: true,
          summary: data.summary,
          summary_data: data.summary_data,  // Include structured data!
          is_article: data.is_article
        });
      } catch (error) {
        config.error('Summarization error:', error);
        let errorMessage = error.message;
        if (error.message.includes('CORS') || error.message.includes('NetworkError')) {
          errorMessage = 'Network error. This may be a CORS issue with the backend service.';
        }
        sendResponse({
          success: false,
          error: errorMessage
        });
      }
    });
}

function handleSummarizeHTML(request, sendResponse) {
    config.log('Received summarizeHTML request');

    if (!request.html) {
        sendResponse({success: false, error: 'No HTML content provided'});
        return;
    }

    chrome.storage.local.get(['backendUrl'], async (result) => {
        // Always use backend service
        const backendUrl = `${config.getBackendUrl()}${config.api.summarize}`;

        try {
            config.log('🔗 API CALL: Backend Service (HTML)');
            config.log('📍 Endpoint:', backendUrl);
            config.log('🎯 Action: summarizeHTML');
            config.log('🌐 Page URL:', request.url);
            config.log('📄 HTML length:', request.html.length);

            const headers = {
                'Content-Type': 'application/json'
            };

            // Add auth token if available
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }

            const response = await fetch(backendUrl, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    html: request.html,
                    url: request.url,
                    title: request.title,
                    action: 'summarize'
                })
            });

            // Check content type before parsing
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                config.error('Non-JSON response:', text.substring(0, 200));
                throw new Error('Backend returned non-JSON response. Check if the backend URL is correct.');
            }

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Backend service error');
            }

            const data = await response.json();
            config.log('✅ HTML summarization successful');
            sendResponse({
                success: true,
                summary: data.summary,
                is_article: data.is_article
            });
        } catch (error) {
            config.error('HTML Summarization error:', error);
            let errorMessage = error.message;
            if (error.message.includes('CORS') || error.message.includes('NetworkError')) {
                errorMessage = 'Network error. This may be a CORS issue with the backend service.';
            }
            sendResponse({
                success: false,
                error: errorMessage
            });
        }
    });
}

function handleTestBackend(sendResponse) {
    // Simple test endpoint to check if backend is working
    (async () => {
      const testUrl = `${config.getBackendUrl()}${config.api.test}`;
      
      try {
        config.log('🔗 API CALL: Backend Test');
        config.log('📍 Endpoint:', testUrl);
        config.log('🎯 Action: testBackend');
        config.log('📦 Request body:', JSON.stringify({ test: true }, null, 2));
        const response = await fetch(testUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ test: true })
        });
        
        config.log('Response status:', response.status);
        config.log('Response headers:', Object.fromEntries(response.headers.entries()));
        
        const text = await response.text();
        config.log('Response text:', text);
        
        let data;
        try {
          data = JSON.parse(text);
        } catch (e) {
          config.error('Failed to parse JSON:', e);
          sendResponse({success: false, error: 'Invalid JSON response', rawResponse: text});
          return;
        }
        
        sendResponse({success: true, data: data});
      } catch (error) {
        config.error('Backend test error:', error);
        sendResponse({success: false, error: error.message});
      }
    })();
}

// User Preferences Functions
async function saveUserPreferences(preferences, sendResponse, retryCount = 0) {
  config.log('🔄 saveUserPreferences called with:', preferences);

  try {
    config.log('🔑 Auth token available:', !!authToken);

    if (!authToken) {
      config.log('❌ No auth token - cannot save preferences');
      sendResponse({
        success: false,
        error: 'Authentication required to save preferences'
      });
      return;
    }

    chrome.storage.local.get(['backendUrl'], async (result) => {
      const endpoint = `${config.getBackendUrl()}${config.api.preferences}`;

      config.log('💾 Saving user preferences to backend:', preferences);
      config.log('🌐 Backend endpoint:', endpoint);

      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify(preferences)
        });

        config.log('📡 Response status:', response.status);
        config.log('📡 Response ok:', response.ok);

        // Handle 401 - token expired, refresh and retry once
        if (response.status === 401 && retryCount === 0) {
          config.log('🔄 Token expired, refreshing and retrying...');

          // Refresh auth state
          await initializeExtensionState();

          // Retry the request with the new token
          saveUserPreferences(preferences, sendResponse, 1);
          return;
        }

        const data = await response.json();
        config.log('📋 Response data:', data);

        if (response.ok && data.success) {
          config.log('✅ Preferences saved successfully:', data.preferences);
          sendResponse({
            success: true,
            preferences: data.preferences
          });
        } else {
          config.error('❌ Failed to save preferences:', data.error);
          sendResponse({
            success: false,
            error: data.error || 'Failed to save preferences'
          });
        }
      } catch (error) {
        config.error('❌ Error saving preferences:', error);
        sendResponse({
          success: false,
          error: 'Network error while saving preferences'
        });
      }
    });
  } catch (error) {
    config.error('❌ Error in saveUserPreferences:', error);
    sendResponse({
      success: false,
      error: 'Failed to save preferences'
    });
  }
}

async function loadUserPreferences(sendResponse) {
  try {
    if (!authToken) {
      sendResponse({
        success: false,
        error: 'Authentication required to load preferences'
      });
      return;
    }

    chrome.storage.local.get(['backendUrl'], async (result) => {
      const endpoint = `${config.getBackendUrl()}${config.api.preferences}`;

      config.log('📥 Loading user preferences from backend');

      try {
        const response = await fetch(endpoint, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          }
        });

        const data = await response.json();
        
        if (response.ok && data.success) {
          config.log('✅ Preferences loaded successfully:', data.preferences);
          
          // Also save to local storage for faster access
          chrome.storage.local.set({
            summaryStyle: data.preferences.summary_style,
            autoSummarizeEnabled: data.preferences.auto_summarize_enabled,
            notificationsEnabled: data.preferences.notifications_enabled
          });
          
          sendResponse({
            success: true,
            preferences: {
              summaryStyle: data.preferences.summary_style,
              autoSummarizeEnabled: data.preferences.auto_summarize_enabled,
              notificationsEnabled: data.preferences.notifications_enabled
            }
          });
        } else {
          config.error('❌ Failed to load preferences:', data.error);
          sendResponse({
            success: false,
            error: data.error || 'Failed to load preferences'
          });
        }
      } catch (error) {
        config.error('❌ Error loading preferences:', error);
        sendResponse({
          success: false,
          error: 'Network error while loading preferences'
        });
      }
    });
  } catch (error) {
    config.error('❌ Error in loadUserPreferences:', error);
    sendResponse({
      success: false,
      error: 'Failed to load preferences'
    });
  }
}

// Send Feedback Function
async function sendFeedback(feedbackData, sendResponse) {
  config.log("📧 Sending feedback to backend");
  
  try {
    if (!authToken) {
      config.log("❌ No auth token - cannot send feedback");
      sendResponse({
        success: false,
        error: "Authentication required"
      });
      return;
    }
    
    chrome.storage.local.get(["backendUrl"], async function(result) {
      const endpoint = `${config.getBackendUrl()}${config.api.feedback}`;
      
      config.log("📮 Sending feedback to:", endpoint);
      
      try {
        const response = await fetch(endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${authToken}`
          },
          body: JSON.stringify(feedbackData)
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
          config.log("✅ Feedback sent successfully");
          sendResponse({
            success: true,
            message: "Feedback sent successfully"
          });
        } else {
          config.error("❌ Failed to send feedback:", data.error);
          sendResponse({
            success: false,
            error: data.error || "Failed to send feedback"
          });
        }
      } catch (error) {
        config.error("❌ Network error sending feedback:", error);
        sendResponse({
          success: false,
          error: "Network error while sending feedback"
        });
      }
    });
  } catch (error) {
    config.error("❌ Error in sendFeedback:", error);
    sendResponse({
      success: false,
      error: "Failed to send feedback"
    });
  }
}

// Force auth and subscription refresh (useful after checkout)
async function forceAuthRefresh(sendResponse) {
  try {
    config.log('🔄 Force refreshing authentication and subscription status...');

    // First re-initialize auth state from storage
    await initializeExtensionState();

    if (!authToken || !currentUser) {
      sendResponse({ success: false, error: 'Not authenticated' });
      return;
    }

    // First refresh subscription status from Stripe (this updates the database)
    const subscriptionResult = await new Promise((resolve) => {
      refreshSubscriptionStatus(resolve);
    });

    // Then verify token and get updated user data (including fresh subscription status)
    const authCheckResult = await new Promise((resolve) => {
      checkAuthStatus(resolve);
    });

    if (!authCheckResult.authenticated) {
      sendResponse({ success: false, error: 'Authentication expired' });
      return;
    }

    sendResponse({
      success: true,
      auth: authCheckResult,
      subscription: subscriptionResult
    });

  } catch (error) {
    config.error('❌ Error in forceAuthRefresh:', error);
    sendResponse({
      success: false,
      error: 'Failed to refresh authentication'
    });
  }
}
