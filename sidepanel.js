document.addEventListener('DOMContentLoaded', function() {
  const config = window.TRACE_CONFIG;
  const summarizeButton = document.getElementById('summarizeButton');
  const testBackendButton = document.getElementById('testBackendButton');
  const checkPageButton = document.getElementById('checkPageButton');
  const feedbackButton = document.getElementById('feedbackButton');
  const messageDiv = document.getElementById('message');
  const toggleSwitch = document.getElementById('toggleSwitch');
  const statusText = document.getElementById('statusText');
  const pageInfo = document.getElementById('pageInfo');
  const analysisResult = document.getElementById('analysisResult');
  
  // Authentication elements
  const googleSignInButton = document.getElementById('googleSignInButton');
  const logoutButtonBottom = document.getElementById('logoutButtonBottom');
  const resetSubscriptionButton = document.getElementById('resetSubscriptionButton');
  const welcomeMessage = document.getElementById('welcomeMessage');
  const loginSection = document.getElementById('loginSection');
  const userSection = document.getElementById('userSection');
  
  // Bottom user profile elements
  const userProfileBottom = document.getElementById('userProfileBottom');
  const userAvatarBottom = document.getElementById('userAvatarBottom');
  const userNameBottom = document.getElementById('userNameBottom');
  const userEmailBottom = document.getElementById('userEmailBottom');
  const userAvatar = document.getElementById('userAvatar');
  const userName = document.getElementById('userName');
  const userEmail = document.getElementById('userEmail');
  const subscriptionStatus = document.getElementById('subscriptionStatus');
  const subscriptionActions = document.getElementById('subscriptionActions');
  
  // Tab navigation elements
  const mainTabButton = document.getElementById('mainTabButton');
  const settingsTabButton = document.getElementById('settingsTabButton');
  const mainView = document.getElementById('mainView');
  const settingsView = document.getElementById('settingsView');
  
  // Settings elements
  const settingsUserAvatar = document.getElementById('settingsUserAvatar');
  const settingsUserName = document.getElementById('settingsUserName');
  const settingsUserEmail = document.getElementById('settingsUserEmail');
  const subscriptionStatusSettings = document.getElementById('subscriptionStatusSettings');
  const subscriptionPlan = document.getElementById('subscriptionPlan');
  const cancelSubscriptionButton = document.getElementById('cancelSubscriptionButton');
  const savePreferencesButton = document.getElementById('savePreferencesButton');
  const settingsMessage = document.getElementById('settingsMessage');
  const autoSummarizeEnabled = document.getElementById('autoSummarizeEnabled');
  
  const notificationsEnabled = document.getElementById('notificationsEnabled');
  const startOnboardingButton = document.getElementById('startOnboardingButton');
  
  let currentPageUrl = null;
  let isAuthenticated = false;
  let currentUser = null;
  let cachedPrice = null; // Cache for subscription price

  // Initialize authentication state
  let authCheckTimeout = null;
  initializeAuth();
  
  // Initialize tab navigation
  initializeTabs();
  
  // Set a timeout for auth check, but cancel it if auth succeeds
  authCheckTimeout = setTimeout(function() {
    if (!isAuthenticated && loginSection.classList.contains('hidden')) {
      config.log('🚨 Auth timeout - forcing login section display');
      showLoginSection();
    }
  }, 2000);
  
  // Load saved state
  chrome.storage.local.get(['extensionEnabled'], function(result) {
    const isEnabled = result.extensionEnabled !== false; // Default to true
    toggleSwitch.checked = isEnabled;
    updateStatus(isEnabled);
    if (isEnabled) {
      displayCurrentPageInfo();
    }
    
    // Show AI features if enabled and authenticated
    if (isEnabled && isAuthenticated) {
      summarizeButton.classList.remove('hidden');
    }
  });

  // Handle toggle switch
  toggleSwitch.addEventListener('change', function() {
    const isEnabled = toggleSwitch.checked;
    chrome.storage.local.set({extensionEnabled: isEnabled}, function() {
      updateStatus(isEnabled);
      // Send message to background script
      chrome.runtime.sendMessage({action: 'toggleExtension', enabled: isEnabled});
      
      if (isEnabled) {
        displayCurrentPageInfo();
        // Show summarize button if authenticated and subscription is active
        if (isAuthenticated && currentUser && currentUser.subscription_status === 'active') {
          summarizeButton.classList.remove('hidden');
        }
      } else {
        pageInfo.classList.add('hidden');
        summarizeButton.classList.add('hidden');
        analysisResult.classList.add('hidden');
      }
    });
  });

  // Update UI based on status
  function updateStatus(isEnabled) {
    statusText.textContent = isEnabled ? 'ON' : 'OFF';
    statusText.className = isEnabled ? 'on' : 'off';
  }


  // Function to display current page info
  function displayCurrentPageInfo() {
    // Only display page info if user is authenticated
    if (!currentUser) {
      pageInfo.classList.add('hidden');
      return;
    }
    
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      if (tabs[0]) {
        // Check if URL has changed
        if (currentPageUrl && currentPageUrl !== tabs[0].url) {
          // Clear analysis results when navigating to a new page
          analysisResult.classList.add('hidden');
        }
        
        currentPageUrl = tabs[0].url;
        // Try to get info from content script
        chrome.tabs.sendMessage(tabs[0].id, {action: 'getPageInfo'}, function(response) {
          if (chrome.runtime.lastError || !response) {
            // Fallback to tab info if content script not available
            displayPageTitle(tabs[0].title);
          } else {
            displayPageTitle(response.title);
          }
        });
      }
    });
  }

  function displayPageTitle(title) {
    // Only show page info if user is authenticated
    if (!currentUser) {
      pageInfo.classList.add('hidden');
      return;
    }
    
    pageInfo.innerHTML = `
      <h3 class="font-semibold text-gray-900 mb-1">Current Page:</h3>
      <p class="text-sm text-gray-600">${title || 'Unable to get page title'}</p>
    `;
    pageInfo.classList.remove('hidden');
  }

  // Track tab listeners to avoid duplicates
  let tabActivatedListener = null;
  let tabUpdatedListener = null;
  
  // Listen for tab changes to update page info
  if (!window.sidePanel_tabListenersAdded) {
    tabActivatedListener = function() {
      chrome.storage.local.get(['extensionEnabled'], function(result) {
        if (result.extensionEnabled !== false) {
          displayCurrentPageInfo();
        }
      });
    };
    chrome.tabs.onActivated.addListener(tabActivatedListener);

    // Listen for tab updates
    tabUpdatedListener = function(tabId, changeInfo, tab) {
      if (changeInfo.status === 'complete' || changeInfo.url) {
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
          if (tabs[0] && tabs[0].id === tabId) {
            chrome.storage.local.get(['extensionEnabled'], function(result) {
              if (result.extensionEnabled !== false) {
                // Check if URL has changed
                if (changeInfo.url && currentPageUrl && currentPageUrl !== changeInfo.url) {
                  // Clear analysis results when URL changes
                  analysisResult.classList.add('hidden');
                }
                displayCurrentPageInfo();
              }
            });
          }
        });
      }
    };
    chrome.tabs.onUpdated.addListener(tabUpdatedListener);
    
    // Mark listeners as added to prevent duplicates
    window.sidePanel_tabListenersAdded = true;
    
    // Store listeners for cleanup
    window.sidePanel_listeners = { tabActivatedListener, tabUpdatedListener };
  }
  
  
  
  
  // Handle summarize button with authentication check
  summarizeButton.addEventListener('click', async function(e) {
    // Check authentication first
    if (!isAuthenticated) {
      e.preventDefault();
      messageDiv.textContent = 'Please sign in to use AI features';
      setMessageColor(messageDiv, messageDiv.textContent, '#ff9800');
      setTimeout(() => {
        messageDiv.textContent = '';
      }, 3000);
      return;
    }
    
    // Check subscription status for AI features
    if (currentUser && currentUser.subscription_status !== 'active') {
      e.preventDefault();
      messageDiv.textContent = 'Active subscription required for AI features';
      setMessageColor(messageDiv, messageDiv.textContent, '#ff9800');
      setTimeout(() => {
        messageDiv.textContent = '';
      }, 3000);
      return;
    }
    // Get current tab
    chrome.tabs.query({active: true, currentWindow: true}, async function(tabs) {
      config.log('Query result - tabs:', tabs);
      if (!tabs[0]) {
        messageDiv.textContent = 'Unable to get current tab';
        setMessageColor(messageDiv, messageDiv.textContent, '#f44336');
        return;
      }
      
      config.log('Current tab:', tabs[0]);
      config.log('Tab ID:', tabs[0].id, 'Tab URL:', tabs[0].url);
      
      // No URL restriction check - backend service will handle all URLs
      
      summarizeButton.disabled = true;
      
      // Get user's preferred summary style
      const customPrompt = await getSummaryPrompt();
      
      messageDiv.textContent = 'Summarizing page content with GPT-3.5...';
      setMessageColor(messageDiv, messageDiv.textContent, '#2196f3');
      
      chrome.runtime.sendMessage({
        action: 'summarizePage',
        tabId: tabs[0].id,
        customPrompt: customPrompt
      }, function(response) {
        summarizeButton.disabled = false;
        
        if (response.success) {
          // Check if it's an article or not
          if (response.is_article === false) {
            // Display the message for non-article pages
            analysisResult.innerHTML = `
              <h4>🟡 Not Suitable for Summarization</h4>
              <p>${response.summary}</p>
            `;
            analysisResult.classList.remove('hidden');
            // Clear any existing status message for non-articles
            messageDiv.textContent = '';
            messageDiv.classList.add('hidden');
          } else {
            // Display the summary for articles
            analysisResult.innerHTML = `
              <h4>Page Summary:</h4>
              <p>${response.summary}</p>
            `;
            analysisResult.classList.remove('hidden');
            // Border color is now handled by CSS classes
            
            messageDiv.textContent = 'Summary complete!';
            setMessageColor(messageDiv, messageDiv.textContent, '#4CAF50');
            messageDiv.classList.remove('hidden');
          }
        } else {
          const errorMsg = response.error || 'Summary failed';

          // Check if it's an auth token error - trigger refresh and retry
          if (errorMsg.includes('Authorization token required') || errorMsg.includes('Token has expired') || errorMsg.includes('Invalid token')) {
            messageDiv.textContent = 'Refreshing authentication...';
            setMessageColor(messageDiv, messageDiv.textContent, '#ff9800');

            // Force auth refresh and retry
            chrome.runtime.sendMessage({action: 'forceAuthRefresh'}, function(refreshResponse) {
              if (refreshResponse && refreshResponse.success) {
                messageDiv.textContent = 'Authentication refreshed. Please try again.';
                setMessageColor(messageDiv, messageDiv.textContent, '#4CAF50');

                // Update our local auth state
                isAuthenticated = true;
                currentUser = refreshResponse.auth.user;

                // Also update subscription status if available
                if (refreshResponse.subscription && refreshResponse.subscription.success) {
                  if (currentUser && refreshResponse.subscription.subscription) {
                    currentUser.subscription_status = refreshResponse.subscription.subscription.status;
                  }
                }

                setTimeout(() => {
                  messageDiv.textContent = '';
                }, 2000);
              } else {
                messageDiv.textContent = 'Please sign in again to use AI features';
                setMessageColor(messageDiv, messageDiv.textContent, '#f44336');
                isAuthenticated = false;
                currentUser = null;
                showLoginSection();
              }
            });
          } else {
            messageDiv.textContent = 'Error: ' + errorMsg;
            setMessageColor(messageDiv, messageDiv.textContent, '#f44336');
          }
        }

        // Only clear status message for successful summaries and errors, not for non-articles
        if (response.success && response.is_article !== false) {
          setTimeout(() => {
            messageDiv.textContent = '';
          }, 3000);
        } else if (!response.success) {
          setTimeout(() => {
            messageDiv.textContent = '';
          }, 3000);
        }
      });
    });
  });
  
  // Test backend button
  testBackendButton.addEventListener('click', function() {
    settingsMessage.textContent = 'Testing backend connection...';
    setMessageColor(settingsMessage, settingsMessage.textContent, '#ff5722');

    chrome.runtime.sendMessage({action: 'testBackend'}, function(response) {
      if (response.success) {
        settingsMessage.textContent = 'Backend is working! ' + JSON.stringify(response.data);
        setMessageColor(settingsMessage, settingsMessage.textContent, '#4CAF50');
      } else {
        settingsMessage.textContent = 'Backend test failed: ' + response.error;
        setMessageColor(settingsMessage, settingsMessage.textContent, '#f44336');
        if (response.rawResponse) {
          console.log('Raw response:', response.rawResponse);
        }
      }

      setTimeout(() => {
        settingsMessage.textContent = '';
      }, 5000);
    });
  });
  
  // Check page compatibility button
  checkPageButton.addEventListener('click', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      if (!tabs[0]) {
        settingsMessage.textContent = 'Unable to get current tab';
        setMessageColor(settingsMessage, settingsMessage.textContent, '#f44336');
        return;
      }

      const url = tabs[0].url;
      const title = tabs[0].title;

      // Check for obvious incompatible URLs
      const incompatiblePatterns = [
        /^chrome:\/\//,
        /^chrome-extension:\/\//,
        /^about:/,
        /^data:/,
        /^file:/,
        /\.pdf$/i,
        /\.(jpg|jpeg|png|gif|svg|mp4|mp3|avi)$/i
      ];

      const isIncompatible = incompatiblePatterns.some(pattern => pattern.test(url));

      if (isIncompatible) {
        settingsMessage.textContent = '❌ This page type is not compatible with the tool';
        setMessageColor(settingsMessage, settingsMessage.textContent, '#f44336');
        setTimeout(() => { settingsMessage.textContent = ''; }, 4000);
        return;
      }

      // Check page content via content script
      chrome.tabs.sendMessage(tabs[0].id, {action: 'checkContent'}, function(response) {
        if (chrome.runtime.lastError || !response) {
          settingsMessage.textContent = '⚠️ Cannot access page content (may be restricted)';
          setMessageColor(settingsMessage, settingsMessage.textContent, '#ff9800');
        } else {
          const textLength = response.textLength || 0;
          const hasText = response.hasText || false;

          if (textLength > 200) {
            settingsMessage.textContent = `✅ Page looks good! (~${textLength} chars of text)`;
            setMessageColor(settingsMessage, settingsMessage.textContent, '#4CAF50');
          } else if (textLength > 50) {
            settingsMessage.textContent = `⚠️ Limited content (~${textLength} chars) - may work`;
            setMessageColor(settingsMessage, settingsMessage.textContent, '#ff9800');
          } else {
            settingsMessage.textContent = '❌ Very little text content detected';
            setMessageColor(settingsMessage, settingsMessage.textContent, '#f44336');
          }
        }

        setTimeout(() => { settingsMessage.textContent = ''; }, 5000);
      });
    });
  });
  
  // Feedback Modal Elements
  const feedbackModal = document.getElementById('feedbackModal');
  const closeFeedbackModal = document.getElementById('closeFeedbackModal');
  const cancelFeedback = document.getElementById('cancelFeedback');
  const submitFeedback = document.getElementById('submitFeedback');
  const feedbackMessage = document.getElementById('feedbackMessage');
  const charCount = document.getElementById('charCount');
  const submitText = document.getElementById('submitText');
  const submitLoader = document.getElementById('submitLoader');
  
  // Feedback button event listener - Open modal
  feedbackButton.addEventListener('click', function() {
    config.log('🗨️ Opening feedback modal');
    
    if (!isAuthenticated || !currentUser) {
      messageDiv.textContent = 'Please sign in to send feedback';
      setMessageColor(messageDiv, messageDiv.textContent, '#ff9800');
      setTimeout(() => { messageDiv.textContent = ''; }, 3000);
      return;
    }
    
    // Show modal
    feedbackModal.classList.remove('hidden');
    feedbackMessage.focus();
  });
  
  // Close modal handlers
  closeFeedbackModal.addEventListener('click', function() {
    feedbackModal.classList.add('hidden');
    feedbackMessage.value = '';
    charCount.textContent = '0';
  });
  
  cancelFeedback.addEventListener('click', function() {
    feedbackModal.classList.add('hidden');
    feedbackMessage.value = '';
    charCount.textContent = '0';
  });
  
  // Character counter
  feedbackMessage.addEventListener('input', function() {
    const length = feedbackMessage.value.length;
    charCount.textContent = length;
    
    if (length > 900) {
      charCount.style.color = '#dc3545';
    } else if (length > 700) {
      charCount.style.color = '#ffc107';
    } else {
      charCount.style.color = '#6c757d';
    }
  });
  
  // Submit feedback
  submitFeedback.addEventListener('click', async function() {
    const message = feedbackMessage.value.trim();
    
    // Validate
    if (!message) {
      feedbackMessage.focus();
      return;
    }
    
    if (message.length > 1000) {
      alert('Feedback must be less than 1000 characters');
      return;
    }
    
    // Get feedback type
    const feedbackTypeElement = document.querySelector('input[name="feedbackType"]:checked');
    if (!feedbackTypeElement) {
      messageDiv.textContent = 'Please select a feedback type';
      setMessageColor(messageDiv, messageDiv.textContent, '#f44336');
      return;
    }
    const feedbackType = feedbackTypeElement.value;
    
    // Get current page context
    let currentPageUrl = 'Unknown';
    let currentPageTitle = 'Unknown';
    
    try {
      const tabs = await chrome.tabs.query({active: true, currentWindow: true});
      if (tabs[0]) {
        currentPageUrl = tabs[0].url || 'Unknown';
        currentPageTitle = tabs[0].title || 'Unknown';
      }
    } catch (error) {
      console.error('Error getting current tab:', error);
    }
    
    // Disable submit button
    submitFeedback.disabled = true;
    submitText.classList.add('hidden');
    submitLoader.classList.remove('hidden');
    
    // Prepare feedback data (with XSS prevention)
    const feedbackData = {
      type: feedbackType,
      message: message, // Will be sanitized on backend
      page_url: currentPageUrl,
      page_title: currentPageTitle,
      user_id: currentUser.id,
      user_email: currentUser.email,
      user_name: currentUser.name,
      timestamp: new Date().toISOString()
    };
    
    try {
      // Send to backend
      chrome.runtime.sendMessage({
        action: 'sendFeedback',
        feedback: feedbackData
      }, function(response) {
        if (response && response.success) {
          // Success
          feedbackModal.classList.add('hidden');
          feedbackMessage.value = '';
          charCount.textContent = '0';
          
          messageDiv.textContent = '✅ Feedback sent successfully!';
          setMessageColor(messageDiv, messageDiv.textContent, '#4CAF50');
        } else {
          // Error
          messageDiv.textContent = '❌ Failed to send feedback. Please try again.';
          setMessageColor(messageDiv, messageDiv.textContent, '#f44336');
        }
        
        // Re-enable button
        submitFeedback.disabled = false;
        submitText.classList.remove('hidden');
        submitLoader.classList.add('hidden');
        
        setTimeout(() => { messageDiv.textContent = ''; }, 5000);
      });
    } catch (error) {
      console.error('Error sending feedback:', error);
      
      // Re-enable button
      submitFeedback.disabled = false;
      submitText.classList.remove('hidden');
      submitLoader.classList.add('hidden');
      
      messageDiv.textContent = '❌ Error sending feedback';
      setMessageColor(messageDiv, messageDiv.textContent, '#f44336');
      setTimeout(() => { messageDiv.textContent = ''; }, 5000);
    }
  });
  
  // Authentication Functions
  function initializeAuth() {
    config.log('🔄 Initializing authentication...');
    
    // Check authentication status
    chrome.runtime.sendMessage({action: 'checkAuth'}, function(response) {
      config.log('Auth check response:', response);
      
      // Clear the auth timeout since we got a response
      if (authCheckTimeout) {
        clearTimeout(authCheckTimeout);
        authCheckTimeout = null;
      }
      
      if (response && response.authenticated) {
        config.log('✅ User is authenticated:', response.user);
        isAuthenticated = true;
        currentUser = response.user;
        showUserSection();

        // Check if we might be returning from a checkout (recent auth with no cached subscription data)
        // This helps refresh subscription status immediately after purchase
        chrome.storage.local.get(['lastSubscriptionCheck'], function(result) {
          const lastCheck = result.lastSubscriptionCheck;
          const fiveMinutesAgo = Date.now() - (5 * 60 * 1000);

          if (!lastCheck || lastCheck < fiveMinutesAgo) {
            // It's been a while since we checked subscription status, force refresh
            config.log('🔄 Forcing auth and subscription refresh due to stale data...');
            chrome.runtime.sendMessage({action: 'forceAuthRefresh'}, function(refreshResponse) {
              if (refreshResponse && refreshResponse.success) {
                config.log('✅ Post-checkout refresh successful');

                // Update current user with fresh data from refresh
                if (refreshResponse.auth && refreshResponse.auth.user) {
                  currentUser = refreshResponse.auth.user;
                }

                // Store the check time
                chrome.storage.local.set({ lastSubscriptionCheck: Date.now() });
              }
              loadSubscriptionStatus();
            });
          } else {
            loadSubscriptionStatus();
          }
        });

        // Check if user needs onboarding
        checkOnboardingStatus();
      } else {
        config.log('❌ User not authenticated, showing login');
        isAuthenticated = false;
        currentUser = null;
        showLoginSection();
      }
    });
  }
  
  function checkOnboardingStatus() {
    // Check if onboarding has been completed
    chrome.storage.sync.get(['onboardingCompleted', 'userPreferences'], function(result) {
      config.log('Onboarding status:', result);
      
      if (!result.onboardingCompleted) {
        config.log('🎯 Starting onboarding for new user');
        startOnboarding();
      } else {
        config.log('✅ Onboarding already completed');
        // Load user preferences if available
        if (result.userPreferences) {
          applyUserPreferences(result.userPreferences);
        }
      }
    });
  }
  
  function startOnboarding() {
    // Open onboarding in a new popup window
    chrome.windows.create({
      url: chrome.runtime.getURL('onboarding.html'),
      type: 'popup',
      width: 380,
      height: 620,
      left: Math.round((screen.availWidth - 380) / 2),
      top: Math.round((screen.availHeight - 620) / 2)
    }, function(window) {
      config.log('🚀 Onboarding window opened');
    });
  }
  
  function applyUserPreferences(preferences) {
    config.log('⚙️ Applying user preferences:', preferences);
    
    // Apply summary style preferences to UI elements
    if (preferences.summaryStyle) {
      // Update radio buttons in settings to match saved preferences
      const styleRadios = document.querySelectorAll('input[name="summaryStyle"]');
      styleRadios.forEach(radio => {
        radio.checked = radio.value === preferences.summaryStyle;
      });
    }
    
    // Store preferences locally for quick access
    chrome.storage.local.set({ 
      currentUserPreferences: preferences 
    });
    
    // Sync preferences with backend if authenticated
    if (isAuthenticated && preferences.summaryStyle) {
      config.log('🔄 Syncing onboarding preferences with backend...');
      chrome.runtime.sendMessage({
        action: 'savePreferences',
        preferences: {
          summary_style: preferences.summaryStyle,  // Backend expects snake_case
          auto_summarize_enabled: false,
          notifications_enabled: true
        }
      }, function(response) {
        if (response && response.success) {
          config.log('✅ Onboarding preferences synced with backend');
        } else {
          config.log('⚠️ Could not sync preferences with backend:', response?.error);
        }
      });
    }
  }
  
  function showLoginSection() {
    config.log('🔑 Showing login section');
    loginSection.classList.remove('hidden');
    userSection.classList.add('hidden');
    userProfileBottom.classList.add('hidden');
    
    // Hide utility buttons when not authenticated
    const utilityButtonsSection = document.getElementById('utilityButtonsSection');
    if (utilityButtonsSection) {
      utilityButtonsSection.classList.add('hidden');
    }
    
    
    // Hide page info when not authenticated
    const pageInfo = document.getElementById('pageInfo');
    if (pageInfo) {
      pageInfo.classList.add('hidden');
    }
    
    // Hide action buttons when not authenticated
    const actionButtonsSection = document.getElementById('actionButtonsSection');
    if (actionButtonsSection) {
      actionButtonsSection.classList.add('hidden');
    }
    
    // Hide AI features when not authenticated
    summarizeButton.classList.add('hidden');
    
    // Hide settings tab when not authenticated
    settingsTabButton.classList.add('hidden');
    
    // Force switch to main view if currently on settings
    if (settingsView && !settingsView.classList.contains('hidden')) {
      showMainView();
    }
    
    config.log('Login section classes:', loginSection.className);
    config.log('User section classes:', userSection.className);
  }
  
  function showUserSection() {
    loginSection.classList.add('hidden');
    userSection.classList.remove('hidden');
    userProfileBottom.classList.remove('hidden');
    
    // Show utility buttons when authenticated
    const utilityButtonsSection = document.getElementById('utilityButtonsSection');
    if (utilityButtonsSection) {
      utilityButtonsSection.classList.remove('hidden');
    }
    
    
    // Show action buttons when authenticated
    const actionButtonsSection = document.getElementById('actionButtonsSection');
    if (actionButtonsSection) {
      actionButtonsSection.classList.remove('hidden');
    }
    
    // Show settings tab when authenticated
    settingsTabButton.classList.remove('hidden');
    
    if (currentUser) {
      config.log('📸 Setting user avatar from Google picture:', currentUser.picture);
      
      // Set Google profile picture for bottom profile
      if (currentUser.picture) {
        userAvatarBottom.src = currentUser.picture;
        userAvatarBottom.onerror = function() {
          config.log('❌ Failed to load Google profile picture, using fallback');
          userAvatarBottom.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMTYiIGN5PSIxNiIgcj0iMTYiIGZpbGw9IiNFMEUwRTAiLz4KPHBhdGggZD0iTTE2IDE2QzE4LjIwOTEgMTYgMjAgMTQuMjA5MSAyMCAxMkMyMCA5Ljc5MDg2IDE4LjIwOTEgOCAxNiA4QzEzLjc5MDkgOCAxMiA5Ljc5MDg2IDEyIDEyQzEyIDE0LjIwOTEgMTMuNzkwOSAxNiAxNiAxNloiIGZpbGw9IiM5RTlFOUUiLz4KPHBhdGggZD0iTTI0IDI2QzI0IDIxLjU4MTcgMjAuNDE4MyAxOCAxNiAxOEMxMS41ODE3IDE4IDggMjEuNTgxNyA4IDI2IiBmaWxsPSIjOUU5RTlFIi8+Cjwvc3ZnPg==';
        };
      } else {
        // Use a default avatar if no picture URL
        userAvatarBottom.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMTYiIGN5PSIxNiIgcj0iMTYiIGZpbGw9IiNFMEUwRTAiLz4KPHBhdGggZD0iTTE2IDE2QzE4LjIwOTEgMTYgMjAgMTQuMjA5MSAyMCAxMkMyMCA5Ljc5MDg2IDE4LjIwOTEgOCAxNiA4QzEzLjc5MDkgOCAxMiA5Ljc5MDg2IDEyIDEyQzEyIDE0LjIwOTEgMTMuNzkwOSAxNiAxNiAxNloiIGZpbGw9IiM5RTlFOUUiLz4KPHBhdGggZD0iTTI0IDI2QzI0IDIxLjU4MTcgMjAuNDE4MyAxOCAxNiAxOEMxMS41ODE3IDE4IDggMjEuNTgxNyA4IDI2IiBmaWxsPSIjOUU5RTlFIi8+Cjwvc3ZnPg==';
      }
      
      userNameBottom.textContent = currentUser.name || '';
      userEmailBottom.textContent = currentUser.email || '';
      
      // Update welcome message with first name
      const firstName = currentUser.name ? currentUser.name.split(' ')[0] : 'there';
      welcomeMessage.textContent = `Welcome, ${firstName}!`;
      
      // Load user preferences from backend when user signs in
      loadUserPreferences();
      
      // Show AI features if extension is enabled AND user has active subscription
      chrome.storage.local.get(['extensionEnabled'], function(result) {
        if (result.extensionEnabled !== false && currentUser.subscription_status === 'active') {
          summarizeButton.classList.remove('hidden');
        } else {
          summarizeButton.classList.add('hidden');
        }
      });
    }
  }
  
  function loadSubscriptionStatus() {
    if (!isAuthenticated) return;
    
    chrome.runtime.sendMessage({action: 'getSubscriptionStatus'}, async function(response) {
      if (response && response.success) {
        const subscription = response.subscription;
        await updateSubscriptionUI(subscription);
      } else {
        // Default to inactive if can't get status
        await updateSubscriptionUI({ status: 'inactive' });
      }
    });
  }
  
  // Function to fetch subscription price from backend
  async function fetchSubscriptionPrice() {
    if (cachedPrice) {
      return cachedPrice;
    }

    try {
      const response = await fetch(`${config.getBackendUrl()}/api/subscription/price`);
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.price) {
          cachedPrice = data.price;
          config.log('✅ Subscription price fetched:', data.price.display);
          return data.price;
        }
      }
    } catch (error) {
      config.error('❌ Error fetching subscription price:', error);
    }

    // Fallback to default price
    return {
      display: '$9.99/month (fallback)',
      formatted_amount: 9.99,
      interval: 'month'
    };
  }
  
  // Helper function to update subscribe button text with dynamic price
  async function updateSubscribeButtonText(button) {
    if (button) {
      const priceInfo = await fetchSubscriptionPrice();
      button.textContent = `Upgrade to Pro - ${priceInfo.display}`;
    }
  }
  
  async function updateSubscriptionUI(subscription) {
    const status = subscription.status || 'inactive';
    
    // Clear existing content
    subscriptionStatus.innerHTML = '';
    subscriptionActions.innerHTML = '';
    
    // Check if user is whitelisted
    const isWhitelisted = currentUser && config.whitelist.isWhitelisted(currentUser.email);
    
    // Fetch dynamic price
    const priceInfo = await fetchSubscriptionPrice();
    
    // Update subscription status display
    if (status === 'active') {
      subscriptionStatus.className = 'subscription-status active';
      subscriptionStatus.innerHTML = `
        ✅ <strong>Active Subscription</strong><br>
        <small>Access to all AI features</small>
      `;
      
      subscriptionActions.innerHTML = '';
    } else if (isWhitelisted) {
      // Special display for whitelisted users
      subscriptionStatus.className = 'subscription-status active';
      subscriptionStatus.innerHTML = `
        🎯 <strong>Beta Access</strong>
      `;
      
      // Show purchase button for whitelisted users to convert to paid
      subscriptionActions.innerHTML = `
        <button class="subscribe-button" id="upgradeButton">
          Upgrade to Pro - ${priceInfo.display}
        </button>
      `;
    } else if (status === 'past_due') {
      subscriptionStatus.className = 'subscription-status expired';
      subscriptionStatus.innerHTML = `
        ⚠️ <strong>Payment Required</strong><br>
        <small>Subscription payment is past due</small>
      `;
      
      subscriptionActions.innerHTML = `
        <button class="subscribe-button" onclick="updatePayment()">
          Update Payment Method
        </button>
      `;
    } else {
      // Regular users (non-whitelisted) - NO purchase button
      subscriptionStatus.className = 'subscription-status inactive';
      subscriptionStatus.innerHTML = `
        🔒 <strong>Limited Access</strong><br>
        <small>AI features are not available in this version</small>
      `;
      
      // No purchase button for non-whitelisted users
      subscriptionActions.innerHTML = '';
    }
    
    // Add click handler for upgrade button (only exists for whitelisted users)
    const upgradeBtn = document.getElementById('upgradeButton');
    if (upgradeBtn) {
      upgradeBtn.addEventListener('click', function() {
        config.log('Upgrade button clicked');
        startSubscription();
      });
    }
  }
  
  // Authentication event handlers
  googleSignInButton.addEventListener('click', function() {
    messageDiv.textContent = 'Signing in with Google...';
    setMessageColor(messageDiv, messageDiv.textContent, '#4285f4');
    
    chrome.runtime.sendMessage({action: 'googleAuth'}, function(response) {
      if (response && response.success) {
        isAuthenticated = true;
        currentUser = response.user;
        showUserSection();
        loadSubscriptionStatus();
        
        messageDiv.textContent = 'Welcome, ' + currentUser.name + '!';
        setMessageColor(messageDiv, messageDiv.textContent, '#4CAF50');
        
        setTimeout(() => {
          messageDiv.textContent = '';
        }, 3000);
      } else {
        messageDiv.textContent = 'Sign in failed: ' + (response?.error || 'Unknown error');
        setMessageColor(messageDiv, messageDiv.textContent, '#f44336');
        
        setTimeout(() => {
          messageDiv.textContent = '';
        }, 5000);
      }
    });
  });
  
  // Logout button (bottom bar)
  logoutButtonBottom.addEventListener('click', function() {
    messageDiv.textContent = 'Signing out and clearing cached credentials...';
    setMessageColor(messageDiv, messageDiv.textContent, '#ff9800');
    
    chrome.runtime.sendMessage({action: 'logout'}, function(response) {
      if (response && response.success) {
        isAuthenticated = false;
        currentUser = null;
        showLoginSection();
        
        messageDiv.textContent = 'Signed out successfully. Next sign-in will show the Google account picker.';
        setMessageColor(messageDiv, messageDiv.textContent, '#4CAF50');
        
        setTimeout(() => {
          messageDiv.textContent = '';
        }, 5000);
      }
    });
  });
  
  resetSubscriptionButton.addEventListener('click', function() {
    if (confirm('Are you sure you want to refresh your subscription data? This will clear cached subscription information and fetch fresh data.')) {
      // Use settings message instead of main message since button is now in settings
      showMessage(settingsMessage, 'Refreshing subscription data...', 'info');
      
      chrome.storage.local.remove(['subscription', 'subscriptionStatus', 'subscriptionPlan', 'subscriptionExpiry'], function() {
        showMessage(settingsMessage, 'Subscription data refreshed successfully!', 'success');
        
        // Refresh the subscription display
        if (currentUser) {
          loadSubscriptionStatusForSettings();
        }
        
        setTimeout(() => {
          hideMessage(settingsMessage);
        }, 3000);
      });
    }
  });
  
  // Define subscription management functions
  function startSubscription() {
    config.log('🔥 startSubscription called');
    const priceId = config.stripe.priceId; // Get from config
    
    // Using production price ID from config: price_1RpIEaKtat2K2WuIYhlyXSrE
    // Test price ID available: price_1RrNm2Ktat2K2WuILiZCzn4M


    // Disable button to prevent double-clicks
    const subscribeButton = document.querySelector('.subscribe-button');
    if (subscribeButton) {
      subscribeButton.disabled = true;
      subscribeButton.textContent = 'Loading...';
    }
    
    if (!messageDiv) {
      console.error('❌ messageDiv not found');
      return;
    }
    
    messageDiv.textContent = 'Creating secure checkout session...';
    setMessageColor(messageDiv, messageDiv.textContent, '#2196f3');
    
    console.log('📤 Sending createCheckoutSession message');
    
    // Add timeout to prevent stuck loading state
    const timeout = setTimeout(() => {
      console.log('⏰ Request timeout - re-enabling button');
      if (subscribeButton) {
        subscribeButton.disabled = false;
        updateSubscribeButtonText(subscribeButton);
      }
      messageDiv.textContent = 'Request timed out. Please try again.';
      setMessageColor(messageDiv, messageDiv.textContent, '#ff9800');
    }, 10000); // 10 second timeout
    
    chrome.runtime.sendMessage({
      action: 'createCheckoutSession',
      priceId: priceId
    }, function(response) {
      clearTimeout(timeout); // Clear timeout since we got a response
      console.log('📥 Received response:', response);
      
      if (chrome.runtime.lastError) {
        console.error('❌ Chrome runtime error:', chrome.runtime.lastError);
        messageDiv.textContent = 'Error: ' + chrome.runtime.lastError.message;
        setMessageColor(messageDiv, messageDiv.textContent, '#f44336');
        // Re-enable button on error
        if (subscribeButton) {
          subscribeButton.disabled = false;
          updateSubscribeButtonText(subscribeButton);
        }
        return;
      }
      
      if (!response) {
        console.error('❌ No response received');
        messageDiv.textContent = 'No response from server. Please check if backend is running.';
        setMessageColor(messageDiv, messageDiv.textContent, '#f44336');
        // Re-enable button
        if (subscribeButton) {
          subscribeButton.disabled = false;
          updateSubscribeButtonText(subscribeButton);
        }
        return;
      }
      
      if (response && response.success) {
        // Open Stripe checkout in new tab
        chrome.tabs.create({ url: response.checkout_url });
        
        messageDiv.innerHTML = `
          <div style="text-align: center;">
            <strong>✅ Checkout opened in new tab</strong><br>
            <small>Complete your purchase and return here</small><br>
            <button onclick="checkAndRefreshStatus()" style="margin-top: 10px; padding: 5px 10px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;">
              Check Subscription Status
            </button>
          </div>
        `;
        setMessageColor(messageDiv, messageDiv.textContent, '#4CAF50');
        
        // Re-enable button and change text to indicate status checking
        if (subscribeButton) {
          subscribeButton.disabled = false;
          subscribeButton.textContent = 'Checking subscription...';
        }
        
        // Start checking subscription status periodically with manual refresh
        let checkCount = 0;
        const checkInterval = setInterval(() => {
          checkCount++;
          
          // First try to refresh subscription status from Stripe
          chrome.runtime.sendMessage({action: 'refreshSubscriptionStatus'}, function(refreshResponse) {
            console.log('Refresh response:', refreshResponse);
            
            // Then check the updated status
            chrome.runtime.sendMessage({action: 'getSubscriptionStatus'}, function(statusResponse) {
              if (statusResponse && statusResponse.success && statusResponse.subscription.status === 'active') {
                clearInterval(checkInterval);
                messageDiv.innerHTML = '<strong>🎉 Subscription activated! Refreshing...</strong>';
                // Just reload to update UI - onboarding now happens in success tab
                setTimeout(() => location.reload(), 1500);
              }
              // Stop checking after 5 minutes
              if (checkCount > 60) {
                clearInterval(checkInterval);
                // Reset button to original state
                if (subscribeButton) {
                  updateSubscribeButtonText(subscribeButton);
                }
              }
            });
          });
        }, 5000); // Check every 5 seconds
        
      } else {
        messageDiv.textContent = 'Failed to start subscription: ' + (response?.error || 'Unknown error');
        setMessageColor(messageDiv, messageDiv.textContent, '#f44336');
        
        // Re-enable button on error
        if (subscribeButton) {
          subscribeButton.disabled = false;
          updateSubscribeButtonText(subscribeButton);
        }
      }
      
      // Don't auto-hide message for subscription flow
    });
  }
  
  // Also attach to window for onclick handlers
  window.startSubscription = startSubscription;
  
  // Function to manually check subscription status
  window.checkAndRefreshStatus = function() {
    messageDiv.textContent = 'Checking subscription status...';
    setMessageColor(messageDiv, messageDiv.textContent, '#2196f3');
    
    chrome.runtime.sendMessage({action: 'getSubscriptionStatus'}, function(statusResponse) {
      if (statusResponse && statusResponse.success && statusResponse.subscription.status === 'active') {
        messageDiv.innerHTML = '<strong>🎉 Subscription activated! Refreshing...</strong>';
        setMessageColor(messageDiv, messageDiv.textContent, '#4CAF50');
        // Just reload to update UI - onboarding now happens in success tab
        setTimeout(() => location.reload(), 1500);
      } else {
        messageDiv.textContent = 'Subscription not yet active. Please complete checkout and try again.';
        setMessageColor(messageDiv, messageDiv.textContent, '#ff9800');
        setTimeout(() => {
          messageDiv.textContent = '';
        }, 3000);
      }
    });
  };
  
  // Test function removed - no longer needed
  
  // Manual refresh subscription status
  window.refreshSubscription = function() {
    console.log('🔄 Manually refreshing subscription status...');
    messageDiv.textContent = 'Refreshing subscription status...';
    setMessageColor(messageDiv, messageDiv.textContent, '#2196f3');
    
    chrome.runtime.sendMessage({action: 'refreshSubscriptionStatus'}, function(response) {
      if (response && response.success) {
        messageDiv.textContent = '✅ Subscription status refreshed!';
        setMessageColor(messageDiv, messageDiv.textContent, '#4CAF50');
        
        // Reload to show updated status
        setTimeout(() => location.reload(), 1000);
      } else {
        messageDiv.textContent = '❌ Refresh failed: ' + (response?.error || 'Unknown error');
        setMessageColor(messageDiv, messageDiv.textContent, '#f44336');
      }
    });
  };
  
  window.manageSubscription = function() {
    // In a real implementation, you'd link to your customer portal
    chrome.tabs.create({ url: 'https://billing.stripe.com/p/login/test_your_portal_link' });
  };
  
  window.updatePayment = function() {
    // Link to update payment method
    chrome.tabs.create({ url: 'https://billing.stripe.com/p/login/test_your_portal_link' });
  };
  
  // Note: Authentication checks are now integrated directly into the button click handlers above
  

  // Tab Navigation Functions
  function initializeTabs() {
    // Set initial state
    showMainView();
    
    // Hide settings tab initially (shown when user logs in)
    settingsTabButton.classList.add('hidden');
    
    // Load user preferences
    loadUserPreferences();
    
    // Tab button event listeners
    mainTabButton.addEventListener('click', function() {
      showMainView();
    });
    
    settingsTabButton.addEventListener('click', function() {
      if (!isAuthenticated) {
        console.log('Settings access denied - user not authenticated');
        showMessage(messageDiv, 'Please sign in to access settings', 'warning');
        setTimeout(() => hideMessage(messageDiv), 3000);
        return;
      }
      showSettingsView();
    });
    
    // Settings event listeners
    savePreferencesButton.addEventListener('click', function() {
      saveUserPreferences();
    });
    
    cancelSubscriptionButton.addEventListener('click', function() {
      cancelSubscription();
    });
    
    startOnboardingButton.addEventListener('click', function() {
      console.log('🚀 Manual onboarding triggered from settings');
      startOnboarding();
    });
  }
  
  function showMainView() {
    mainView.classList.remove('hidden');
    settingsView.classList.add('hidden');
    mainTabButton.classList.add('active');
    settingsTabButton.classList.remove('active');
  }
  
  function showSettingsView() {
    // Double-check authentication before showing settings
    if (!isAuthenticated) {
      console.log('Cannot show settings - user not authenticated');
      showMainView();
      return;
    }
    
    mainView.classList.add('hidden');
    settingsView.classList.remove('hidden');
    mainTabButton.classList.remove('active');
    settingsTabButton.classList.add('active');
    
    // Update settings view with current user info
    updateSettingsView();
  }
  
  function updateSettingsView() {
    if (currentUser) {
      // Update user profile in settings with Google picture
      if (currentUser.picture) {
        settingsUserAvatar.src = currentUser.picture;
        settingsUserAvatar.onerror = function() {
          console.log('❌ Failed to load Google profile picture in settings, using fallback');
          settingsUserAvatar.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMTYiIGN5PSIxNiIgcj0iMTYiIGZpbGw9IiNFMEUwRTAiLz4KPHBhdGggZD0iTTE2IDE2QzE4LjIwOTEgMTYgMjAgMTQuMjA5MSAyMCAxMkMyMCA5Ljc5MDg2IDE4LjIwOTEgOCAxNiA4QzEzLjc5MDkgOCAxMiA5Ljc5MDg2IDEyIDEyQzEyIDE0LjIwOTEgMTMuNzkwOSAxNiAxNiAxNloiIGZpbGw9IiM5RTlFOUUiLz4KPHBhdGggZD0iTTI0IDI2QzI0IDIxLjU4MTcgMjAuNDE4MyAxOCAxNiAxOEMxMS41ODE3IDE4IDggMjEuNTgxNiA4IDI2IiBmaWxsPSIjOUU5RTlFIi8+Cjwvc3ZnPg==';
        };
      } else {
        settingsUserAvatar.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMTYiIGN5PSIxNiIgcj0iMTYiIGZpbGw9IiNFMEUwRTAiLz4KPHBhdGggZD0iTTE2IDE2QzE4LjIwOTEgMTYgMjAgMTQuMjA5MSAyMCAxMkMyMCA5Ljc5MDg2IDE4LjIwOTEgOCAxNiA4QzEzLjc5MDkgOCAxMiA5Ljc5MDg2IDEyIDEyQzEyIDE0LjIwOTEgMTMuNzkwOSAxNiAxNiAxNloiIGZpbGw9IiM5RTlFOUUiLz4KPHBhdGggZD0iTTI0IDI2QzI0IDIxLjU4MTcgMjAuNDE4MyAxOCAxNiAxOEMxMS41ODE3IDE4IDggMjEuNTgxNiA4IDI2IiBmaWxsPSIjOUU5RTlFIi8+Cjwvc3ZnPg==';
      }
      settingsUserName.textContent = currentUser.name || 'Loading...';
      settingsUserEmail.textContent = currentUser.email || 'Loading...';
      
      // Update subscription info in settings
      loadSubscriptionStatusForSettings();
    }
  }
  
  function loadSubscriptionStatusForSettings() {
    if (!isAuthenticated) {
      subscriptionStatusSettings.textContent = 'Sign in to view subscription';
      subscriptionStatusSettings.className = 'subscription-status subscription-inactive';
      subscriptionPlan.textContent = '';
      return;
    }
    
    chrome.runtime.sendMessage({action: 'getSubscriptionStatus'}, async function(response) {
      if (response && response.success) {
        const subscription = response.subscription;
        await updateSubscriptionSettingsUI(subscription);
      } else {
        // Default to inactive if can't get status
        await updateSubscriptionSettingsUI({ status: 'inactive' });
      }
    });
  }
  
  async function updateSubscriptionSettingsUI(subscription) {
    // Use the same logic as the main view for consistency
    const status = subscription.status || 'inactive';
    const isWhitelisted = currentUser && config.whitelist.isWhitelisted(currentUser.email);
    
    // Fetch dynamic price
    const priceInfo = await fetchSubscriptionPrice();
    
    if (status === 'active') {
      subscriptionStatusSettings.textContent = '✅ Active';
      subscriptionStatusSettings.className = 'subscription-status subscription-active';
      subscriptionPlan.textContent = `Pro Plan subscription is active - ${priceInfo.display}`;

      // Show subscription management buttons for active users
      resetSubscriptionButton.style.display = 'flex';
      cancelSubscriptionButton.style.display = 'block';
    } else if (status === 'past_due') {
      subscriptionStatusSettings.textContent = '⚠️ Past Due';
      subscriptionStatusSettings.className = 'subscription-status subscription-inactive';
      subscriptionPlan.textContent = 'Subscription payment is overdue - please update payment method';

      // Show subscription management buttons for past due users
      resetSubscriptionButton.style.display = 'flex';
      cancelSubscriptionButton.style.display = 'block';
    } else if (status === 'canceled') {
      subscriptionStatusSettings.textContent = '❌ Canceled';
      subscriptionStatusSettings.className = 'subscription-status subscription-inactive';
      subscriptionPlan.textContent = 'Subscription has been canceled - AI features unavailable';

      // Hide subscription management buttons for canceled users
      resetSubscriptionButton.style.display = 'none';
      cancelSubscriptionButton.style.display = 'none';
    } else {
      // Regular users (non-whitelisted) - No subscription
      subscriptionStatusSettings.textContent = '⭕ No Active Subscription';
      subscriptionStatusSettings.className = 'subscription-status subscription-trial';
      subscriptionPlan.textContent = 'Subscribe to access AI-powered analysis features';

      // Hide subscription management buttons for users without subscriptions
      resetSubscriptionButton.style.display = 'none';
      cancelSubscriptionButton.style.display = 'none';
    }
  }
  
  // User Preferences Functions
  function loadUserPreferences() {
    if (isAuthenticated) {
      // Load from backend if authenticated
      chrome.runtime.sendMessage({action: 'loadPreferences'}, function(response) {
        if (response && response.success) {
          updatePreferencesUI(response.preferences);
        } else {
          console.log('Failed to load preferences from backend, using local storage fallback:', response?.error);
          loadPreferencesFromStorage();
        }
      });
    } else {
      // Fallback to local storage if not authenticated
      loadPreferencesFromStorage();
    }
  }
  
  function loadPreferencesFromStorage() {
    chrome.storage.local.get([
      'summaryStyle',
      'autoSummarizeEnabled', 
      'notificationsEnabled'
    ], function(result) {
      updatePreferencesUI({
        summaryStyle: result.summaryStyle || 'eli8',
        autoSummarizeEnabled: result.autoSummarizeEnabled || false,
        notificationsEnabled: result.notificationsEnabled !== false
      });
    });
  }
  
  function updatePreferencesUI(preferences) {
    // Set summary style radio button
    const radioButton = document.getElementById(preferences.summaryStyle + 'Summary');
    if (radioButton) {
      radioButton.checked = true;
    }
    
    // Set checkboxes
    autoSummarizeEnabled.checked = preferences.autoSummarizeEnabled || false;
    notificationsEnabled.checked = preferences.notificationsEnabled !== false;
  }
  
  function saveUserPreferences() {
    // Get selected summary style
    const summaryStyleRadios = document.querySelectorAll('input[name="summaryStyle"]');
    let selectedSummaryStyle = 'eli8'; // default
    
    for (const radio of summaryStyleRadios) {
      if (radio.checked) {
        selectedSummaryStyle = radio.value;
        break;
      }
    }
    
    const preferences = {
      summary_style: selectedSummaryStyle,
      auto_summarize_enabled: autoSummarizeEnabled.checked,
      notifications_enabled: notificationsEnabled.checked
    };
    
    if (isAuthenticated) {
      // Save to backend if authenticated
      console.log('🔄 Saving preferences to backend:', preferences);
      console.log('🔑 User authenticated:', isAuthenticated);
      
      chrome.runtime.sendMessage({
        action: 'savePreferences',
        preferences: preferences
      }, function(response) {
        console.log('📥 Response from background script:', response);
        
        if (response && response.success) {
          // Also save to local storage for faster access
          chrome.storage.local.set({
            summaryStyle: selectedSummaryStyle,
            autoSummarizeEnabled: autoSummarizeEnabled.checked,
            notificationsEnabled: notificationsEnabled.checked
          });
          
          showMessage(settingsMessage, 'Preferences saved to your account!', 'success');
          console.log('Preferences saved to backend:', preferences);
        } else {
          console.error('❌ Failed to save preferences to backend:', response);
          showMessage(settingsMessage, 'Failed to save preferences: ' + (response?.error || 'Unknown error'), 'error');
        }
        setTimeout(() => hideMessage(settingsMessage), 3000);
      });
    } else {
      // Save to local storage only if not authenticated
      chrome.storage.local.set({
        summaryStyle: selectedSummaryStyle,
        autoSummarizeEnabled: autoSummarizeEnabled.checked,
        notificationsEnabled: notificationsEnabled.checked
      }, function() {
        showMessage(settingsMessage, 'Preferences saved locally! Sign in to sync across devices.', 'info');
        setTimeout(() => hideMessage(settingsMessage), 3000);
        
        console.log('Preferences saved locally:', {
          summaryStyle: selectedSummaryStyle,
          autoSummarizeEnabled: autoSummarizeEnabled.checked,
          notificationsEnabled: notificationsEnabled.checked
        });
      });
    }
  }
  
  function getSummaryPrompt() {
    return new Promise((resolve) => {
      chrome.storage.local.get(['summaryStyle'], function(result) {
        const style = result.summaryStyle || 'eli8';
        
        let prompt;
        switch (style) {
          case 'quick':
            prompt = 'Summarize this content in exactly one clear, concise sentence that captures the main point.';
            break;
          case 'detailed':
            prompt = 'Provide a thorough summary of this content in exactly 5 bullet points, covering all key aspects and important details.';
            break;
          case 'eli8':
          default:
            prompt = 'Explain this content like I\'m 8 years old - use simple, clear language that busy people can quickly understand.';
            break;
        }
        
        resolve(prompt);
      });
    });
  }
  
  // Subscription Management Functions
  function manageSubscription() {
    if (!isAuthenticated) {
      showMessage(settingsMessage, 'Please sign in to manage your subscription', 'warning');
      setTimeout(() => hideMessage(settingsMessage), 3000);
      return;
    }
    
    showMessage(settingsMessage, 'Opening subscription management...', 'info');
    
    // Create customer portal session
    chrome.runtime.sendMessage({action: 'createPortalSession'}, function(response) {
      if (response && response.success) {
        chrome.tabs.create({ url: response.portal_url });
        showMessage(settingsMessage, 'Subscription management opened in new tab', 'success');
      } else {
        showMessage(settingsMessage, 'Failed to open subscription management: ' + (response?.error || 'Unknown error'), 'error');
      }
      setTimeout(() => hideMessage(settingsMessage), 3000);
    });
  }
  
  function cancelSubscription() {
    if (!isAuthenticated) {
      showMessage(settingsMessage, 'Please sign in to cancel your subscription', 'warning');
      setTimeout(() => hideMessage(settingsMessage), 3000);
      return;
    }
    
    if (confirm('Are you sure you want to cancel your subscription? You will lose access to AI features at the end of your billing period.')) {
      showMessage(settingsMessage, 'Processing cancellation...', 'info');
      
      chrome.runtime.sendMessage({action: 'cancelSubscription'}, function(response) {
        if (response && response.success) {
          showMessage(settingsMessage, 'Subscription cancelled successfully. Access continues until end of billing period.', 'success');
          
          // Refresh subscription status after a short delay
          setTimeout(() => {
            loadSubscriptionStatusForSettings();
          }, 2000);
        } else {
          showMessage(settingsMessage, 'Failed to cancel subscription: ' + (response?.error || 'Unknown error'), 'error');
        }
        setTimeout(() => hideMessage(settingsMessage), 5000);
      });
    }
  }
  
  // Export functions for global access
  window.getSummaryPrompt = getSummaryPrompt;
});