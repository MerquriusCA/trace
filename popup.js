document.addEventListener('DOMContentLoaded', function() {
  const actionButton = document.getElementById('actionButton');
  const messageDiv = document.getElementById('message');
  const toggleSwitch = document.getElementById('toggleSwitch');
  const statusText = document.getElementById('statusText');
  const pageInfo = document.getElementById('pageInfo');

  // Load saved state
  chrome.storage.local.get(['extensionEnabled'], function(result) {
    const isEnabled = result.extensionEnabled !== false; // Default to true
    toggleSwitch.checked = isEnabled;
    updateStatus(isEnabled);
    if (isEnabled) {
      displayCurrentPageInfo();
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
      } else {
        pageInfo.classList.remove('visible');
      }
    });
  });

  // Update UI based on status
  function updateStatus(isEnabled) {
    statusText.textContent = isEnabled ? 'ON' : 'OFF';
    statusText.style.color = isEnabled ? '#4CAF50' : '#666';
    actionButton.disabled = !isEnabled;
    actionButton.style.opacity = isEnabled ? '1' : '0.5';
    actionButton.style.cursor = isEnabled ? 'pointer' : 'not-allowed';
  }

  actionButton.addEventListener('click', function() {
    if (actionButton.disabled) return;
    
    messageDiv.textContent = 'Button clicked!';
    messageDiv.style.color = '#4CAF50';
    
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      chrome.tabs.sendMessage(tabs[0].id, {action: "buttonClicked"}, function(response) {
        if (chrome.runtime.lastError) {
          // No content script is listening, just show a message
          messageDiv.textContent = 'Extension is active!';
          messageDiv.style.color = '#4CAF50';
        } else if (response && response.status) {
          messageDiv.textContent = 'Action completed: ' + response.status;
        }
      });
    });
    
    setTimeout(() => {
      messageDiv.textContent = '';
    }, 3000);
  });

  // Function to display current page info
  function displayCurrentPageInfo() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      if (tabs[0]) {
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
    pageInfo.innerHTML = `
      <h3>Current Page:</h3>
      <p>${title || 'Unable to get page title'}</p>
    `;
    pageInfo.classList.add('visible');
  }
});