// Background script for Chrome Extension
let extensionEnabled = true;
let pageTitles = new Map(); // Store page titles
let authToken = null;
let currentUser = null;

// Initialize extension state
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get(['extensionEnabled', 'authToken', 'currentUser'], (result) => {
    extensionEnabled = result.extensionEnabled !== false; // Default to true
    authToken = result.authToken;
    currentUser = result.currentUser;
  });
});

// Listen for messages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'toggleExtension') {
    extensionEnabled = request.enabled;
    console.log('Extension is now:', extensionEnabled ? 'ON' : 'OFF');
  } else if (request.action === 'pageLoaded' && extensionEnabled) {
    // Store page title when content script reports it
    if (sender.tab) {
      pageTitles.set(sender.tab.id, {
        title: request.title,
        url: request.url,
        timestamp: Date.now()
      });
      console.log('Page loaded:', request.title);
    }
  } else if (request.action === 'checkEnabled') {
    sendResponse({enabled: extensionEnabled});
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
    console.log('Tab updated:', tab.title);
  }
});

// Open side panel when extension icon is clicked
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ windowId: tab.windowId });
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
      console.log('Cannot access restricted URL:', tab.url);
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
    console.error('Error getting page content:', error);
    return null;
  }
}

// OpenAI API function
async function callOpenAI(prompt, apiKey) {
  try {
    console.log('🔗 API CALL: Direct OpenAI API (callOpenAI function)');
    console.log('📍 Endpoint: https://api.openai.com/v1/chat/completions');
    console.log('🎯 Action: GPT analysis');
    console.log('📏 Prompt length:', prompt.length);
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: 'gpt-3.5-turbo',
        messages: [
          {
            role: 'system',
            content: 'You are a helpful assistant that analyzes web page content. When given page text, identify and list the top 5 sentences that best convey the purpose and main message of the page. Format your response as a numbered list with just the sentences, no additional commentary.'
          },
          {
            role: 'user',
            content: `Here is the page content. Please identify the top 5 sentences that best convey the purpose of this page:\n\n${prompt}`
          }
        ],
        temperature: 0.3,
        max_tokens: 300
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || 'API request failed');
    }

    const data = await response.json();
    return {
      success: true,
      analysis: data.choices[0].message.content
    };
  } catch (error) {
    console.error('OpenAI API error:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// Helper function to get backend base URL
async function getBackendBaseUrl() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['backendUrl'], (result) => {
      // Default to Railway production URL
      const defaultUrl = 'https://trace-production-79d5.up.railway.app/api';
      
      if (result.backendUrl) {
        // Extract base URL from the stored URL
        const url = new URL(result.backendUrl);
        const baseUrl = `${url.protocol}//${url.host}/api`;
        console.log('📍 Using backend URL from storage:', baseUrl);
        resolve(baseUrl);
      } else {
        console.log('📍 Using default LOCAL backend URL:', defaultUrl);
        resolve(defaultUrl);
      }
    });
  });
}

// Authentication Functions
async function authenticateWithGoogle(sendResponse) {
  try {
    console.log('🔄 Starting Google authentication...');
    
    // Clear any cached tokens first
    chrome.identity.clearAllCachedAuthTokens(() => {
      console.log('🔄 Cleared cached tokens');
      
      // Use the simpler Chrome Identity API
      chrome.identity.getAuthToken({ 
        interactive: true 
      }, async function(token) {
        if (chrome.runtime.lastError || !token) {
          console.error('Auth error:', chrome.runtime.lastError);
          sendResponse({ success: false, error: chrome.runtime.lastError?.message || 'Failed to get token' });
          return;
        }

        try {
          console.log('✅ Received token from Chrome Identity API');
          
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
          console.log('Got user info:', { email: userInfo.email, name: userInfo.name });
          
          // Send to backend for authentication
          const baseUrl = await getBackendBaseUrl();
          const backendUrl = `${baseUrl}/auth/google`;
          console.log('🔗 API CALL: Google Authentication');
          console.log('📍 Endpoint:', backendUrl);
          
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
            console.error('Backend response:', errorData);
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

          console.log('✅ Authentication successful for:', currentUser.email);
          sendResponse({ 
            success: true, 
            user: currentUser,
            token: authToken
          });

        } catch (error) {
          console.error('Authentication error:', error);
          sendResponse({ success: false, error: error.message });
        }
      });
    });

  } catch (error) {
    console.error('Auth setup error:', error);
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
        console.log('✅ Cached token removed');
        
        // Also revoke the token server-side
        await fetch(`https://oauth2.googleapis.com/revoke?token=${currentToken}`, {
          method: 'POST'
        });
        console.log('✅ Token revoked server-side');
      } catch (e) {
        console.log('⚠️ Error revoking token:', e);
      }
    }

    // Clear all cached auth tokens for this extension
    chrome.identity.clearAllCachedAuthTokens(() => {
      console.log('✅ All cached tokens cleared');
    });

    sendResponse({ success: true });
  } catch (error) {
    console.error('Logout error:', error);
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
    const baseUrl = await getBackendBaseUrl();
    const backendUrl = `${baseUrl}/auth/verify`;
    console.log('🔗 API CALL: Verify Authentication');
    console.log('📍 Endpoint:', backendUrl);
    
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
    console.error('Auth check error:', error);
    sendResponse({ authenticated: false });
  }
}

async function getSubscriptionStatus(sendResponse) {
  if (!authToken) {
    sendResponse({ success: false, error: 'Not authenticated' });
    return;
  }

  try {
    const baseUrl = await getBackendBaseUrl();
    const backendUrl = `${baseUrl}/subscription/status`;
    console.log('🔗 API CALL: Get Subscription Status');
    console.log('📍 Endpoint:', backendUrl);
    
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
    console.error('Subscription status error:', error);
    sendResponse({ success: false, error: error.message });
  }
}

async function createCheckoutSession(priceId, sendResponse) {
  if (!authToken) {
    sendResponse({ success: false, error: 'Not authenticated' });
    return;
  }

  try {
    const baseUrl = await getBackendBaseUrl();
    const backendUrl = `${baseUrl}/subscription/create-checkout-session`;
    console.log('🔗 API CALL: Create Checkout Session');
    console.log('📍 Endpoint:', backendUrl);
    
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
    console.error('Checkout session error:', error);
    sendResponse({ success: false, error: error.message });
  }
}

async function refreshSubscriptionStatus(sendResponse) {
  if (!authToken) {
    sendResponse({ success: false, error: 'Not authenticated' });
    return;
  }

  try {
    const baseUrl = await getBackendBaseUrl();
    const backendUrl = `${baseUrl}/subscription/refresh`;
    console.log('🔗 API CALL: Refresh Subscription Status');
    console.log('📍 Endpoint:', backendUrl);
    
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    if (response.ok) {
      const data = await response.json();
      console.log('✅ Subscription refresh successful:', data);
      sendResponse(data);
    } else {
      const error = await response.json();
      throw new Error(error.error || 'Failed to refresh subscription status');
    }
  } catch (error) {
    console.error('Subscription refresh error:', error);
    sendResponse({ success: false, error: error.message });
  }
}

// Add OpenAI message handler
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'analyzeWithGPT') {
    console.log('Received analyzeWithGPT request with tabId:', request.tabId);
    chrome.storage.local.get(['openaiApiKey', 'backendUrl'], async (result) => {
      if (!result.openaiApiKey) {
        sendResponse({success: false, error: 'API key not set'});
        return;
      }
      
      // Get the current tab info
      let tab, url;
      try {
        tab = await chrome.tabs.get(request.tabId);
        console.log('Full tab object for analyze:', tab);
        url = tab.url;
        console.log('Got tab URL for analyze:', url);
        if (!url) {
          console.error('Tab exists but URL is undefined:', tab);
          sendResponse({success: false, error: 'Tab URL is not available'});
          return;
        }
      } catch (error) {
        console.error('Failed to get tab for analyze:', error);
        sendResponse({success: false, error: 'Unable to get current tab URL'});
        return;
      }
      
      // Always use backend service for all URLs
      const backendUrl = result.backendUrl || 'https://trace-production-79d5.up.railway.app/api/summarize';
      
      try {
        console.log('🔗 API CALL: Backend Service');
        console.log('📍 Endpoint:', backendUrl);
        console.log('🎯 Action: analyzeWithGPT');
        console.log('🌐 Page URL:', url);
        console.log('📦 Request body:', JSON.stringify({
          url: url,
          apiKey: '***hidden***',
          action: 'analyze'
        }, null, 2));
        
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
            url: url,
            apiKey: result.openaiApiKey,
            action: 'analyze'
          })
        });

        // Check content type before parsing
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          const text = await response.text();
          console.error('Non-JSON response:', text.substring(0, 200));
          throw new Error('Backend returned non-JSON response. Check if the backend URL is correct.');
        }

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.error || 'Backend service error');
        }

        const data = await response.json();
        sendResponse({
          success: true,
          analysis: data.analysis
        });
      } catch (error) {
        console.error('Analysis error:', error);
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
    return true; // Keep message channel open for async response
  } else if (request.action === 'summarizePage') {
    console.log('Received summarizePage request with tabId:', request.tabId);
    chrome.storage.local.get(['openaiApiKey', 'backendUrl'], async (result) => {
      if (!result.openaiApiKey) {
        sendResponse({success: false, error: 'API key not set'});
        return;
      }
      
      // Get the current tab info
      let tab, url;
      try {
        tab = await chrome.tabs.get(request.tabId);
        console.log('Full tab object for summarize:', tab);
        url = tab.url;
        console.log('Got tab URL for summarize:', url);
        if (!url) {
          console.error('Tab exists but URL is undefined:', tab);
          sendResponse({success: false, error: 'Tab URL is not available'});
          return;
        }
      } catch (error) {
        console.error('Failed to get tab for summarize:', error);
        sendResponse({success: false, error: 'Unable to get current tab URL'});
        return;
      }
      
      // Always use backend service for all URLs
      const backendUrl = result.backendUrl || 'https://trace-production-79d5.up.railway.app/api/summarize';
      
      try {
        console.log('🔗 API CALL: Backend Service');
        console.log('📍 Endpoint:', backendUrl);
        console.log('🎯 Action: summarizePage');
        console.log('🌐 Page URL:', url);
        console.log('🔑 Auth token present:', !!authToken);
        console.log('🔑 OpenAI key present:', !!result.openaiApiKey);
        console.log('📦 Request body:', JSON.stringify({
          url: url,
          apiKey: '***hidden***'
        }, null, 2));
        
        const headers = {
          'Content-Type': 'application/json'
        };
        
        // Add auth token if available
        if (authToken) {
          headers['Authorization'] = `Bearer ${authToken}`;
          console.log('✅ Added auth token to request');
        } else {
          console.log('⚠️ No auth token available');
        }
        
        console.log('📡 Making fetch request to:', backendUrl);
        
        const requestBody = {
          url: url,
          apiKey: result.openaiApiKey
        };
        
        // Add custom prompt if provided
        if (request.customPrompt) {
          requestBody.customPrompt = request.customPrompt;
          console.log('📝 Custom prompt provided:', request.customPrompt.substring(0, 100) + '...');
        }
        
        const response = await fetch(backendUrl, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify(requestBody)
        }).catch(error => {
          console.error('🚨 Fetch failed:', error);
          throw new Error(`Network error: ${error.message}. Check if Railway backend is deployed and running.`);
        });

        console.log('📥 Response status:', response.status);
        console.log('📥 Response headers:', Object.fromEntries(response.headers.entries()));

        // Check content type before parsing
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          const text = await response.text();
          console.error('Non-JSON response:', text.substring(0, 500));
          throw new Error(`Backend returned non-JSON response (${response.status}). Response: ${text.substring(0, 100)}...`);
        }

        if (!response.ok) {
          const error = await response.json();
          console.error('❌ Backend error response:', error);
          throw new Error(error.error || `Backend service error (${response.status})`);
        }

        const data = await response.json();
        console.log('✅ Successful response received');
        sendResponse({
          success: true,
          summary: data.summary
        });
      } catch (error) {
        console.error('Summarization error:', error);
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
    return true; // Keep message channel open for async response
  } else if (request.action === 'testBackend') {
    // Simple test endpoint to check if backend is working
    (async () => {
      const testUrl = 'https://trace-production-79d5.up.railway.app/api/test';
      
      try {
        console.log('🔗 API CALL: Backend Test');
        console.log('📍 Endpoint:', testUrl);
        console.log('🎯 Action: testBackend');
        console.log('📦 Request body:', JSON.stringify({ test: true }, null, 2));
        const response = await fetch(testUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ test: true })
        });
        
        console.log('Response status:', response.status);
        console.log('Response headers:', Object.fromEntries(response.headers.entries()));
        
        const text = await response.text();
        console.log('Response text:', text);
        
        let data;
        try {
          data = JSON.parse(text);
        } catch (e) {
          console.error('Failed to parse JSON:', e);
          sendResponse({success: false, error: 'Invalid JSON response', rawResponse: text});
          return;
        }
        
        sendResponse({success: true, data: data});
      } catch (error) {
        console.error('Backend test error:', error);
        sendResponse({success: false, error: error.message});
      }
    })();
    return true;
  } else if (request.action === 'googleAuth') {
    // Handle Google authentication
    authenticateWithGoogle(sendResponse);
    return true;
  } else if (request.action === 'logout') {
    // Handle logout
    logout(sendResponse);
    return true;
  } else if (request.action === 'checkAuth') {
    // Check authentication status
    checkAuthStatus(sendResponse);
    return true;
  } else if (request.action === 'getSubscriptionStatus') {
    // Get subscription status
    getSubscriptionStatus(sendResponse);
    return true;
  } else if (request.action === 'createCheckoutSession') {
    // Create Stripe checkout session
    createCheckoutSession(request.priceId, sendResponse);
    return true;
  } else if (request.action === 'refreshSubscriptionStatus') {
    // Refresh subscription status from Stripe
    refreshSubscriptionStatus(sendResponse);
    return true;
  } else if (request.action === 'savePreferences') {
    // Save user preferences to backend
    console.log('🔄 Background: Received savePreferences request:', request.preferences);
    saveUserPreferences(request.preferences, sendResponse);
    return true;
  } else if (request.action === 'loadPreferences') {
    // Load user preferences from backend
    loadUserPreferences(sendResponse);
    return true;
  } else if (request.action === 'sendFeedback') {
    // Send feedback to backend
    console.log('📧 Background: Received feedback request');
    sendFeedback(request.feedback, sendResponse);
    return true;
  }
});

// User Preferences Functions
async function saveUserPreferences(preferences, sendResponse) {
  console.log('🔄 saveUserPreferences called with:', preferences);
  
  try {
    console.log('🔑 Auth token available:', !!authToken);
    
    if (!authToken) {
      console.log('❌ No auth token - cannot save preferences');
      sendResponse({
        success: false,
        error: 'Authentication required to save preferences'
      });
      return;
    }

    chrome.storage.local.get(['backendUrl'], async (result) => {
      const backendUrl = result.backendUrl || 'https://trace-production-79d5.up.railway.app';
      const endpoint = `${backendUrl}/api/preferences`;

      console.log('💾 Saving user preferences to backend:', preferences);
      console.log('🌐 Backend endpoint:', endpoint);

      try {
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify(preferences)
        });

        console.log('📡 Response status:', response.status);
        console.log('📡 Response ok:', response.ok);
        
        const data = await response.json();
        console.log('📋 Response data:', data);
        
        if (response.ok && data.success) {
          console.log('✅ Preferences saved successfully:', data.preferences);
          sendResponse({
            success: true,
            preferences: data.preferences
          });
        } else {
          console.error('❌ Failed to save preferences:', data.error);
          sendResponse({
            success: false,
            error: data.error || 'Failed to save preferences'
          });
        }
      } catch (error) {
        console.error('❌ Error saving preferences:', error);
        sendResponse({
          success: false,
          error: 'Network error while saving preferences'
        });
      }
    });
  } catch (error) {
    console.error('❌ Error in saveUserPreferences:', error);
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
      const backendUrl = result.backendUrl || 'https://trace-production-79d5.up.railway.app';
      const endpoint = `${backendUrl}/api/preferences`;

      console.log('📥 Loading user preferences from backend');

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
          console.log('✅ Preferences loaded successfully:', data.preferences);
          
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
          console.error('❌ Failed to load preferences:', data.error);
          sendResponse({
            success: false,
            error: data.error || 'Failed to load preferences'
          });
        }
      } catch (error) {
        console.error('❌ Error loading preferences:', error);
        sendResponse({
          success: false,
          error: 'Network error while loading preferences'
        });
      }
    });
  } catch (error) {
    console.error('❌ Error in loadUserPreferences:', error);
    sendResponse({
      success: false,
      error: 'Failed to load preferences'
    });
  }
}

// Send Feedback Function
async function sendFeedback(feedbackData, sendResponse) {
  console.log("📧 Sending feedback to backend");
  
  try {
    if (!authToken) {
      console.log("❌ No auth token - cannot send feedback");
      sendResponse({
        success: false,
        error: "Authentication required"
      });
      return;
    }
    
    chrome.storage.local.get(["backendUrl"], async function(result) {
      const baseUrl = result.backendUrl ? 
        result.backendUrl.replace("/api/summarize", "") : 
        "https://trace-production-79d5.up.railway.app";
      const endpoint = `${baseUrl}/api/feedback`;
      
      console.log("📮 Sending feedback to:", endpoint);
      
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
          console.log("✅ Feedback sent successfully");
          sendResponse({
            success: true,
            message: "Feedback sent successfully"
          });
        } else {
          console.error("❌ Failed to send feedback:", data.error);
          sendResponse({
            success: false,
            error: data.error || "Failed to send feedback"
          });
        }
      } catch (error) {
        console.error("❌ Network error sending feedback:", error);
        sendResponse({
          success: false,
          error: "Network error while sending feedback"
        });
      }
    });
  } catch (error) {
    console.error("❌ Error in sendFeedback:", error);
    sendResponse({
      success: false,
      error: "Failed to send feedback"
    });
  }
}
