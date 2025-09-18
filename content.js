// Content script that runs on every page
console.log('🔧 Content script loaded on:', window.location.href);

chrome.storage.local.get(['extensionEnabled'], function(result) {
  const isEnabled = result.extensionEnabled !== false;
  
  if (isEnabled) {
    // Send page title to background script
    chrome.runtime.sendMessage({
      action: 'pageLoaded',
      title: document.title,
      url: window.location.href
    });
    
    // Extension active indicator removed - no popup notification needed
  }
});

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'buttonClicked') {
    sendResponse({status: 'Page title: ' + document.title});
  } else if (request.action === 'getPageInfo') {
    sendResponse({
      title: document.title,
      url: window.location.href
    });
  } else if (request.action === 'checkContent') {
    // Check if page has analyzable content
    const bodyText = document.body.innerText || document.body.textContent || '';
    const textLength = bodyText.trim().length;
    const hasText = textLength > 10;
    
    sendResponse({
      textLength: textLength,
      hasText: hasText,
      title: document.title,
      url: window.location.href
    });
  } else if (request.action === 'highlightFirstSentence') {
    const highlightedSentence = highlightFirstSentence();
    sendResponse({
      status: 'First sentence highlighted!',
      sentence: highlightedSentence
    });
  } else if (request.action === 'getHTML') {
    // Return the HTML content of the page
    sendResponse({
      html: document.documentElement.outerHTML,
      url: window.location.href,
      title: document.title
    });
  }
});

// Function to highlight the first sentence on the page
function highlightFirstSentence() {
  // Remove any existing highlights first
  const existingHighlights = document.querySelectorAll('.chrome-ext-highlight');
  existingHighlights.forEach(el => {
    const parent = el.parentNode;
    while (el.firstChild) {
      parent.insertBefore(el.firstChild, el);
    }
    parent.removeChild(el);
  });

  let highlightedText = null;

  // Get all text content from body, excluding certain tags
  const excludedTags = ['SCRIPT', 'STYLE', 'NOSCRIPT', 'IFRAME', 'OBJECT'];
  let allText = '';
  let firstSentenceNode = null;
  let sentenceStartOffset = 0;

  // Walk through all text nodes in body
  const walker = document.createTreeWalker(
    document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode: function(node) {
        // Skip excluded elements
        let parent = node.parentElement;
        while (parent) {
          if (excludedTags.includes(parent.tagName)) {
            return NodeFilter.FILTER_REJECT;
          }
          parent = parent.parentElement;
        }
        
        // Skip whitespace-only nodes
        if (!node.textContent.trim()) {
          return NodeFilter.FILTER_SKIP;
        }
        
        return NodeFilter.FILTER_ACCEPT;
      }
    }
  );

  // Collect text until we find a complete sentence
  let currentNode;
  while (currentNode = walker.nextNode()) {
    const nodeText = currentNode.textContent;
    const previousLength = allText.length;
    allText += nodeText;
    
    // Check if we now have a complete sentence
    const sentenceMatch = allText.match(/[^.!?]*[.!?]/);
    if (sentenceMatch && !firstSentenceNode) {
      const sentenceEnd = sentenceMatch.index + sentenceMatch[0].length;
      
      // Check if the sentence ends in this node
      if (sentenceEnd > previousLength) {
        firstSentenceNode = currentNode;
        sentenceStartOffset = Math.max(0, previousLength);
        break;
      }
    }
  }

  if (firstSentenceNode && allText) {
    // Extract the complete first sentence
    const sentenceMatch = allText.match(/[^.!?]*[.!?]/);
    if (sentenceMatch) {
      const fullSentence = sentenceMatch[0].trim();
      highlightedText = fullSentence;
      
      // Find where in the current node the sentence starts/ends
      const nodeText = firstSentenceNode.textContent;
      const nodeStartInFullText = allText.indexOf(nodeText, sentenceStartOffset);
      const sentenceEndInFullText = sentenceMatch.index + sentenceMatch[0].length;
      const sentenceEndInNode = sentenceEndInFullText - nodeStartInFullText;
      
      // Create highlighted span
      const highlightSpan = document.createElement('span');
      highlightSpan.className = 'chrome-ext-highlight';
      highlightSpan.style.cssText = 'background-color: yellow; padding: 2px 4px; border-radius: 3px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);';
      
      // Handle the case where sentence might span multiple nodes
      if (sentenceEndInNode <= nodeText.length) {
        // Sentence ends in this node
        const sentenceText = nodeText.substring(0, sentenceEndInNode);
        const afterSentence = nodeText.substring(sentenceEndInNode);
        
        highlightSpan.textContent = sentenceText;
        
        const parent = firstSentenceNode.parentNode;
        parent.insertBefore(highlightSpan, firstSentenceNode);
        firstSentenceNode.textContent = afterSentence;
      } else {
        // For simplicity, just highlight what we can in this node
        highlightSpan.textContent = nodeText;
        const parent = firstSentenceNode.parentNode;
        parent.insertBefore(highlightSpan, firstSentenceNode);
        firstSentenceNode.textContent = '';
      }
    }
  }
  
  return highlightedText;
}



