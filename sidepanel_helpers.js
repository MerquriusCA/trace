// Helper functions for displaying messages with simple classes

function showMessage(messageDiv, text, type = 'info') {
  messageDiv.textContent = text;
  messageDiv.classList.remove('hidden');
  
  // Remove all type classes first
  messageDiv.className = messageDiv.className.replace(/\b(success|error|warning|info)\b/g, '');
  
  // Add type-specific class
  messageDiv.classList.add(type);
}

function hideMessage(messageDiv) {
  messageDiv.classList.add('hidden');
}

// Also create a simple message function that works with the current code
function setMessageColor(messageDiv, text, color) {
  messageDiv.textContent = text;
  messageDiv.classList.remove('hidden');
  
  // Map colors to classes
  let cssClass = 'info'; // default
  if (color === '#4CAF50' || color === 'green') cssClass = 'success';
  else if (color === '#f44336' || color === 'red') cssClass = 'error';
  else if (color === '#ff9800' || color === 'orange') cssClass = 'warning';
  else if (color === '#2196f3' || color === 'blue') cssClass = 'info';
  
  // Remove old classes and add new one
  messageDiv.className = messageDiv.className.replace(/\b(success|error|warning|info)\b/g, '');
  messageDiv.classList.add(cssClass);
}

// Export functions for use in sidepanel.js
window.showMessage = showMessage;
window.hideMessage = hideMessage;
window.setMessageColor = setMessageColor;

// Override the style.color setter to use our classes instead
Object.defineProperty(HTMLElement.prototype, 'messageColor', {
  set: function(color) {
    if (this.id === 'message') {
      setMessageColor(this, this.textContent, color);
    }
  }
});