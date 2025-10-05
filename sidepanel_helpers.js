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
  console.log('📋 Formatting summary with quotes:');
  console.log('📋 Full summary text:', summaryText);
  console.log('📋 Summary length:', summaryText.length);
  console.log('📋 Contains SUMMARY:', summaryText.includes('SUMMARY:'));
  console.log('📋 Contains bullet (•):', summaryText.includes('•'));
  console.log('📋 Contains QUOTES:', summaryText.includes('QUOTES:'));

  let lines = summaryText.split('\n');
  console.log('📋 Split into', lines.length, 'lines:', lines);
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
      formattedHTML += `</div>`; // Close bullet-main

      // Look for QUOTES in the next few lines (handle various formatting)
      let quotesFound = false;
      let quotesLine = '';

      // Check next 3 lines for QUOTES (sometimes there might be empty lines)
      for (let j = 1; j <= 3 && i + j < lines.length; j++) {
        let nextLine = lines[i + j]; // Don't trim yet, keep original spacing
        let trimmedLine = nextLine.trim();

        console.log(`🔍 Checking line ${i+j}: "${nextLine}" (trimmed: "${trimmedLine}")`);

        if (trimmedLine.includes('QUOTES:') || nextLine.includes('QUOTES:')) {
          quotesFound = true;
          quotesLine = trimmedLine;
          console.log(`✅ QUOTES found for bullet ${bulletCounter}: "${quotesLine}"`);

          formattedHTML += `<button class="quote-toggle" data-bullet="${bulletCounter}" onclick="toggleQuotes(${bulletCounter})" title="Show supporting quotes"><span class="toggle-icon">📖</span> Show Quotes</button>`;

          // Extract quotes content - handle both trimmed and untrimmed
          let quotesContent = quotesLine.replace(/^.*QUOTES:\s*/, '').trim();
          console.log(`📝 Extracted quotes content: "${quotesContent}"`);

          // Parse quotes - they're comma-separated and in quotes
          let quotes = quotesContent.match(/"([^"]*)"/g) || [];
          console.log(`📖 Parsed ${quotes.length} quotes for bullet ${bulletCounter}:`, quotes);

          formattedHTML += `<div class="quotes-section hidden" id="quotes-${bulletCounter}">`;
          formattedHTML += `<div class="quotes-header">Page Quotes:</div>`;

          if (quotes.length === 0 && quotesContent) {
            // If no quotes found in proper format, show the raw content
            console.log(`⚠️ No quotes parsed, showing raw content: "${quotesContent}"`);
            // Only add quotes if they don't already exist
            const hasQuotes = quotesContent.startsWith('"') || quotesContent.startsWith('"');
            formattedHTML += `<blockquote class="article-quote">${hasQuotes ? quotesContent : '"' + quotesContent + '"'}</blockquote>`;
          } else {
            quotes.forEach((quote, idx) => {
              // Remove surrounding quotes
              let cleanQuote = quote.slice(1, -1);
              console.log(`📝 Quote ${idx + 1}: "${cleanQuote}"`);
              // Only add quotes if they don't already exist
              const hasQuotes = cleanQuote.startsWith('"') || cleanQuote.startsWith('"');
              formattedHTML += `<blockquote class="article-quote">${hasQuotes ? cleanQuote : '"' + cleanQuote + '"'}</blockquote>`;
            });
          }

          formattedHTML += `</div>`; // Close quotes-section
          i += j; // Skip the lines we've processed
          break;
        }

        // Stop looking if we hit another bullet point
        if (trimmedLine.startsWith('•')) {
          console.log(`🛑 Hit another bullet point, stopping search`);
          break;
        }
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
      toggleButton.innerHTML = '<span class="toggle-icon">📕</span> Hide Quotes';
      toggleButton.title = 'Hide supporting quotes';
    } else {
      quotesSection.classList.add('hidden');
      toggleButton.innerHTML = '<span class="toggle-icon">📖</span> Show Quotes';
      toggleButton.title = 'Show supporting quotes';
    }
  }
}

// Function to format structured summary data from backend
function formatStructuredSummary(summaryData) {
  console.log('📋 Formatting structured summary:', summaryData);
  let formattedHTML = '';
  let bulletCounter = 0;

  // Add summary sentence
  if (summaryData.summary) {
    let summaryText = summaryData.summary.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formattedHTML += `<div class="summary-sentence">${summaryText}</div>`;
  }

  // Add bullet points with quotes
  if (summaryData.points && summaryData.points.length > 0) {
    summaryData.points.forEach(point => {
      bulletCounter++;
      let bulletText = point.text || point.point || String(point);

      // First convert markdown bold to HTML
      bulletText = bulletText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

      // Then apply bold from the "bold" field if provided
      if (point.bold && bulletText.includes(point.bold)) {
        // Escape regex special characters in the bold phrase
        const escapedBold = point.bold.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        // Create regex to match the exact phrase (case-sensitive)
        const boldRegex = new RegExp(`(${escapedBold})`, 'g');
        // Wrap the phrase in <strong> tags with emphasis class
        bulletText = bulletText.replace(boldRegex, '<strong class="key-emphasis">$1</strong>');
      }

      formattedHTML += `<div class="bullet-item">`;
      formattedHTML += `<div class="bullet-main">`;
      formattedHTML += `<span class="bullet-point">•</span> ${bulletText}`;
      formattedHTML += `</div>`; // Close bullet-main

      // Check if this point has quotes
      let quotes = point.quotes || point.QUOTES || [];
      if (quotes && quotes.length > 0) {
        console.log(`📖 Point ${bulletCounter} has ${quotes.length} quotes:`, quotes);

        formattedHTML += `<button class="quote-toggle" data-bullet="${bulletCounter}" onclick="toggleQuotes(${bulletCounter})" title="Show supporting quotes"><span class="toggle-icon">📖</span> Show Quotes</button>`;

        formattedHTML += `<div class="quotes-section hidden" id="quotes-${bulletCounter}">`;
        formattedHTML += `<div class="quotes-header">Page Quotes:</div>`;

        quotes.forEach(quote => {
          // Only add quotes if they don't already exist
          const hasQuotes = quote.startsWith('"') || quote.startsWith('"');
          formattedHTML += `<blockquote class="article-quote">${hasQuotes ? quote : '"' + quote + '"'}</blockquote>`;
        });

        formattedHTML += `</div>`; // Close quotes-section
      } else {
        console.log(`📝 Point ${bulletCounter} has no quotes`);
      }

      formattedHTML += `</div>`; // Close bullet-item
    });
  }

  console.log(`✅ Generated HTML for ${bulletCounter} bullet points`);
  return formattedHTML;
}

// Export functions for use in sidepanel.js
window.showMessage = showMessage;
window.hideMessage = hideMessage;
window.setMessageColor = setMessageColor;
window.formatSummaryWithQuotes = formatSummaryWithQuotes;
window.formatStructuredSummary = formatStructuredSummary;
window.toggleQuotes = toggleQuotes;

// Override the style.color setter to use our classes instead
Object.defineProperty(HTMLElement.prototype, 'messageColor', {
  set: function(color) {
    if (this.id === 'message') {
      setMessageColor(this, this.textContent, color);
    }
  }
});