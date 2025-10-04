// Onboarding workflow logic
document.addEventListener('DOMContentLoaded', function() {
  // Get step elements
  const welcomeStep = document.getElementById('welcomeStep');
  const readerTypeStep = document.getElementById('readerTypeStep');
  const readingLevelStep = document.getElementById('readingLevelStep');
  const preferencesStep = document.getElementById('preferencesStep');
  const completionStep = document.getElementById('completionStep');
  
  // Get button elements
  const getStartedBtn = document.getElementById('getStartedBtn');
  const backToWelcomeBtn = document.getElementById('backToWelcomeBtn');
  const continueToLevelBtn = document.getElementById('continueToLevelBtn');
  const backToTypeBtn = document.getElementById('backToTypeBtn');
  const continueToPrefsBtn = document.getElementById('continueToPrefsBtn');
  const backToLevelBtn = document.getElementById('backToLevelBtn');
  const finishOnboardingBtn = document.getElementById('finishOnboardingBtn');
  const startUsingBtn = document.getElementById('startUsingBtn');
  
  // Step management
  let currentStep = 1;
  const steps = [welcomeStep, readerTypeStep, readingLevelStep, preferencesStep, completionStep];
  
  function showStep(stepNumber) {
    // Hide all steps
    steps.forEach(step => step.classList.remove('active'));
    
    // Show current step
    if (steps[stepNumber - 1]) {
      steps[stepNumber - 1].classList.add('active');
    }
    
    currentStep = stepNumber;
  }
  
  // Navigation event listeners
  getStartedBtn.addEventListener('click', function() {
    showStep(2); // Go to reader type
  });
  
  backToWelcomeBtn.addEventListener('click', function() {
    showStep(1); // Back to welcome
  });
  
  continueToLevelBtn.addEventListener('click', function() {
    showStep(3); // Go to reading level
  });
  
  backToTypeBtn.addEventListener('click', function() {
    showStep(2); // Back to reader type
  });
  
  continueToPrefsBtn.addEventListener('click', function() {
    showStep(4); // Go to preferences
  });
  
  backToLevelBtn.addEventListener('click', function() {
    showStep(3); // Back to reading level
  });
  
  finishOnboardingBtn.addEventListener('click', async function() {
    // Collect all preferences
    const selectedStyle = document.querySelector('input[name="summaryStyle"]:checked')?.value || 'eli8';
    const selectedReaderType = document.querySelector('input[name="readerType"]:checked')?.value || 'lifelong_learner';
    const selectedReadingLevel = document.querySelector('input[name="readingLevel"]:checked')?.value || 'balanced';

    const preferences = {
      summary_style: selectedStyle,
      auto_summarize_enabled: false,
      notifications_enabled: true,
      reader_type: selectedReaderType,
      reading_level: selectedReadingLevel
    };

    console.log('💾 Saving onboarding preferences to backend:', preferences);

    try {
      // Mark onboarding as completed in local storage (but don't store preferences locally)
      chrome.storage.local.set({
        onboardingCompleted: true
      }, function() {
        console.log('✅ Onboarding marked as completed');
      });

      // Send preferences to backend via background script (ONLY source of truth)
      chrome.runtime.sendMessage({
        action: 'savePreferences',
        preferences: preferences
      }, function(response) {
        if (response && response.success) {
          console.log('✅ Preferences saved to backend:', response.preferences);

          // Notify sidepanel to refresh the profile display
          chrome.runtime.sendMessage({
            action: 'preferencesUpdated',
            preferences: response.preferences
          });
        } else {
          console.log('⚠️ Failed to save to backend:', response ? response.error : 'No response');
        }
      });

      // Show completion step
      showStep(5);

    } catch (error) {
      console.error('❌ Error saving preferences:', error);
      // Still show completion even if save fails
      showStep(5);
    }
  });
  
  startUsingBtn.addEventListener('click', function() {
    // Close the onboarding window
    window.close();
  });
  
  // Handle radio button changes for visual feedback
  const radioButtons = document.querySelectorAll('input[type="radio"]');
  radioButtons.forEach(radio => {
    radio.addEventListener('change', function() {
      // Update visual state when selection changes
      const parent = this.closest('.preference-option');
      if (parent) {
        // Remove selected class from siblings
        const siblings = parent.parentElement.querySelectorAll('.preference-option');
        siblings.forEach(sibling => sibling.classList.remove('selected'));
        // Add selected class to current
        parent.classList.add('selected');
      }
    });
  });
  
  // Initialize - show welcome step
  showStep(1);
});