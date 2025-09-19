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


// Function to format summary with expandable quotes
function formatSummaryWithQuotes(summaryText) {
  let lines = summaryText.split('\n');
  let formattedHTML = '';
  let bulletCounter = 0;

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i].trim();

    // Handle SUMMARY line
    if (line.startsWith('SUMMARY:')) {
      formattedHTML += `<div class="summary-sentence">${line.replace('SUMMARY:', '').trim()}</div>`;
    }
    // Handle bullet points
    else if (line.startsWith('•')) {
      bulletCounter++;
      let bulletContent = line.substring(1).trim();
      // Convert markdown bold to HTML
      bulletContent = bulletContent.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

      formattedHTML += `<div class="bullet-item">`;
      formattedHTML += `<div class="bullet-main">`;
      formattedHTML += `<span class="bullet-point">•</span> ${bulletContent}`;

      // Check if next line contains QUOTES
      if (i + 1 < lines.length && lines[i + 1].trim().startsWith('QUOTES:')) {
        formattedHTML += ` <button class="quote-toggle" data-bullet="${bulletCounter}" onclick="toggleQuotes(${bulletCounter})" title="Show supporting quotes">📖</button>`;
        formattedHTML += `</div>`; // Close bullet-main

        // Add the quotes section (hidden by default)
        let quotesLine = lines[i + 1].trim().replace('QUOTES:', '').trim();
        // Parse quotes - they're comma-separated and in quotes
        let quotes = quotesLine.match(/"([^"]*)"/g) || [];

        formattedHTML += `<div class="quotes-section hidden" id="quotes-${bulletCounter}">`;
        formattedHTML += `<div class="quotes-header">Supporting Evidence:</div>`;
        quotes.forEach(quote => {
          // Remove surrounding quotes
          let cleanQuote = quote.slice(1, -1);
          formattedHTML += `<blockquote class="article-quote">${cleanQuote}</blockquote>`;
        });
        formattedHTML += `</div>`; // Close quotes-section

        i++; // Skip the QUOTES line since we've processed it
      } else {
        formattedHTML += `</div>`; // Close bullet-main if no quotes
      }

      formattedHTML += `</div>`; // Close bullet-item
    }
    // Handle empty lines
    else if (line === '') {
      // Skip empty lines
    }
  }

  return formattedHTML;
}

// Toggle quotes visibility function
function toggleQuotes(bulletId) {
  const quotesSection = document.getElementById(`quotes-${bulletId}`);
  const toggleButton = document.querySelector(`[data-bullet="${bulletId}"]`);

  if (quotesSection) {
    if (quotesSection.classList.contains('hidden')) {
      quotesSection.classList.remove('hidden');
      toggleButton.textContent = '📕';
      toggleButton.title = 'Hide supporting quotes';
    } else {
      quotesSection.classList.add('hidden');
      toggleButton.textContent = '📖';
      toggleButton.title = 'Show supporting quotes';
    }
  }
}

// Export functions for use in sidepanel.js
window.showMessage = showMessage;
window.hideMessage = hideMessage;
window.setMessageColor = setMessageColor;
window.formatSummaryWithQuotes = formatSummaryWithQuotes;
window.toggleQuotes = toggleQuotes;

// Override the style.color setter to use our classes instead
Object.defineProperty(HTMLElement.prototype, 'messageColor', {
  set: function(color) {
    if (this.id === 'message') {
      setMessageColor(this, this.textContent, color);
    }
  }
});