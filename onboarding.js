// Onboarding workflow logic
document.addEventListener('DOMContentLoaded', function() {
  // Get elements
  const welcomeStep = document.getElementById('welcomeStep');
  const preferencesStep = document.getElementById('preferencesStep');
  const completionStep = document.getElementById('completionStep');
  
  const getStartedBtn = document.getElementById('getStartedBtn');
  const backBtn = document.getElementById('backBtn');
  const finishOnboardingBtn = document.getElementById('finishOnboardingBtn');
  const startUsingBtn = document.getElementById('startUsingBtn');
  
  // Step management
  let currentStep = 1;
  
  function showStep(stepNumber) {
    // Hide all steps
    welcomeStep.classList.remove('active');
    preferencesStep.classList.remove('active');
    completionStep.classList.remove('active');
    
    // Show current step
    switch(stepNumber) {
      case 1:
        welcomeStep.classList.add('active');
        break;
      case 2:
        preferencesStep.classList.add('active');
        break;
      case 3:
        completionStep.classList.add('active');
        break;
    }
    
    currentStep = stepNumber;
  }
  
  // Event listeners
  getStartedBtn.addEventListener('click', function() {
    showStep(2);
  });
  
  backBtn.addEventListener('click', function() {
    showStep(1);
  });
  
  finishOnboardingBtn.addEventListener('click', function() {
    saveOnboardingPreferences();
  });
  
  startUsingBtn.addEventListener('click', function() {
    completeOnboarding();
  });
  
  function saveOnboardingPreferences() {
    const selectedStyle = document.querySelector('input[name="summaryStyle"]:checked').value;
    
    // Save preferences to Chrome storage
    const preferences = {
      summaryStyle: selectedStyle,
      onboardingCompleted: true,
      onboardingDate: new Date().toISOString()
    };
    
    // First save to Chrome storage
    chrome.storage.sync.set({ 
      userPreferences: preferences,
      onboardingCompleted: true
    }, function() {
      console.log('Onboarding preferences saved to Chrome storage:', preferences);
      
      // Also save to local storage for immediate access
      chrome.storage.local.set({ 
        lastOnboardingPreferences: preferences,
        summaryStyle: selectedStyle,
        autoSummarizeEnabled: false,  // Default settings
        notificationsEnabled: true
      }, function() {
        // Save to backend through background script
        console.log('Saving preferences to backend...');
        chrome.runtime.sendMessage({
          action: 'savePreferences',
          preferences: {
            summary_style: selectedStyle,  // Backend expects snake_case
            auto_summarize_enabled: false,
            notifications_enabled: true
          }
        }, function(response) {
          if (response && response.success) {
            console.log('✅ Preferences saved to backend successfully');
          } else {
            console.log('⚠️ Could not save to backend, will retry on next login:', response?.error);
          }
          // Move to completion step regardless of backend save result
          showStep(3);
        });
      });
    });
  }
  
  function completeOnboarding() {
    // Mark onboarding as completed
    chrome.storage.sync.set({ 
      onboardingCompleted: true 
    }, function() {
      console.log('Onboarding completed');
      
      // Close onboarding and return to main extension
      window.close();
      
      // Send message to background to refresh sidepanel
      chrome.runtime.sendMessage({
        action: 'onboardingCompleted'
      });
    });
  }
  
  // Initialize onboarding
  function initializeOnboarding() {
    // Check if we're resuming from a specific step
    chrome.storage.local.get(['onboardingStep'], function(result) {
      const step = result.onboardingStep || 1;
      showStep(step);
    });
    
    // Load any existing preferences to pre-select options
    chrome.storage.sync.get(['userPreferences'], function(result) {
      if (result.userPreferences && result.userPreferences.summaryStyle) {
        const styleInput = document.getElementById(result.userPreferences.summaryStyle + 'SummaryOnboard');
        if (styleInput) {
          styleInput.checked = true;
        }
      }
    });
  }
  
  // Save current step when navigating (for persistence)
  function saveCurrentStep() {
    chrome.storage.local.set({ onboardingStep: currentStep });
  }
  
  // Add step saving to navigation buttons
  getStartedBtn.addEventListener('click', saveCurrentStep);
  backBtn.addEventListener('click', saveCurrentStep);
  
  // Initialize when DOM is ready
  initializeOnboarding();
  
  // Handle messages from parent extension
  chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    if (request.action === 'resetOnboarding') {
      // Reset to first step
      chrome.storage.local.remove(['onboardingStep'], function() {
        showStep(1);
        sendResponse({ success: true });
      });
      return true;
    }
  });
});