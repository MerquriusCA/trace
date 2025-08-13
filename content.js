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
  } else if (request.action === 'highlightSentences') {
    const result = highlightMultipleSentences(request.sentences);
    sendResponse({
      status: 'Sentences highlighted!',
      count: result.highlighted,
      total: request.sentences.length,
      debug: result.debug
    });
  } else if (request.action === 'scrollToSentence') {
    const result = scrollToSentence(request.sentenceIndex);
    sendResponse(result);
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

// Function to highlight multiple sentences on the page
function highlightMultipleSentences(sentences) {
  console.log('Highlighting sentences:', sentences);
  
  const debugInfo = {
    pageLength: document.body.innerText.length,
    sentences: sentences.length,
    strategies: []
  };
  
  // Remove any existing highlights first
  const existingHighlights = document.querySelectorAll('.chrome-ext-highlight, .chrome-ext-multi-highlight');
  existingHighlights.forEach(el => {
    const parent = el.parentNode;
    while (el.firstChild) {
      parent.insertBefore(el.firstChild, el);
    }
    parent.removeChild(el);
  });
  
  // Clean sentences by removing leading numbers and normalizing whitespace
  const cleanedSentences = sentences.map(s => {
    return s.replace(/^\d+\.\s*/, '').trim();
  });
  
  console.log('Cleaned sentences:', cleanedSentences);
  
  // Different colors for each sentence
  const colors = ['#ffeb3b', '#ff9800', '#4caf50', '#2196f3', '#e91e63'];
  let highlightedCount = 0;
  
  // Process each sentence
  cleanedSentences.forEach((sentence, index) => {
    if (!sentence) return;
    
    console.log(`Searching for sentence ${index + 1}: "${sentence}"`);
    
    // Find and highlight exact matches
    const found = findAndHighlightExactText(sentence, index + 1, colors[index % colors.length]);
    
    if (found) {
      highlightedCount++;
      debugInfo.strategies.push(`Sentence ${index + 1}: Found and highlighted exact match`);
      console.log(`Successfully highlighted sentence ${index + 1}`);
    } else {
      debugInfo.strategies.push(`Sentence ${index + 1}: Not found in page`);
      console.log(`Sentence ${index + 1} not found on page`);
    }
  });
  
  console.log(`Highlighting complete. Highlighted ${highlightedCount}/${cleanedSentences.length} sentences`);
  
  return {
    highlighted: highlightedCount,
    debug: debugInfo
  };
}

// Function to find and highlight exact text matches
function findAndHighlightExactText(searchText, sentenceIndex, color) {
  // Normalize the search text (preserve original spacing but trim)
  const normalizedSearchText = searchText.trim();
  
  // Get all text nodes in the document
  const textNodes = getAllTextNodes();
  
  // Search through all text nodes for exact matches
  for (const node of textNodes) {
    const nodeText = node.textContent;
    
    // Look for exact match (case-insensitive)
    const lowerNodeText = nodeText.toLowerCase();
    const lowerSearchText = normalizedSearchText.toLowerCase();
    const matchIndex = lowerNodeText.indexOf(lowerSearchText);
    
    if (matchIndex !== -1) {
      // Found exact match - highlight it
      return highlightTextInNode(node, matchIndex, normalizedSearchText.length, sentenceIndex, color);
    }
  }
  
  // If no exact match found, try partial matching with consecutive text nodes
  return findAndHighlightAcrossNodes(normalizedSearchText, sentenceIndex, color, textNodes);
}

// Function to get all text nodes in the document (excluding scripts, styles, etc.)
function getAllTextNodes() {
  const textNodes = [];
  const excludedTags = ['SCRIPT', 'STYLE', 'NOSCRIPT', 'IFRAME', 'OBJECT'];
  
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
  
  let node;
  while (node = walker.nextNode()) {
    textNodes.push(node);
  }
  
  return textNodes;
}

// Function to highlight text within a single text node
function highlightTextInNode(textNode, startIndex, length, sentenceIndex, color) {
  const parent = textNode.parentNode;
  const fullText = textNode.textContent;
  
  // Split the text into before, match, and after
  const beforeText = fullText.substring(0, startIndex);
  const matchText = fullText.substring(startIndex, startIndex + length);
  const afterText = fullText.substring(startIndex + length);
  
  // Create the highlight span
  const highlightSpan = document.createElement('span');
  highlightSpan.className = 'chrome-ext-multi-highlight';
  highlightSpan.setAttribute('data-sentence-index', sentenceIndex);
  highlightSpan.style.cssText = `background-color: ${color}; padding: 2px 4px; border-radius: 3px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); font-weight: bold;`;
  highlightSpan.textContent = matchText;
  
  // Replace the original text node with the three parts
  if (beforeText) {
    parent.insertBefore(document.createTextNode(beforeText), textNode);
  }
  parent.insertBefore(highlightSpan, textNode);
  
  if (afterText) {
    textNode.textContent = afterText;
  } else {
    parent.removeChild(textNode);
  }
  
  console.log(`Highlighted exact match: "${matchText}"`);
  return true;
}

// Function to find and highlight text that might span across multiple text nodes
function findAndHighlightAcrossNodes(searchText, sentenceIndex, color, textNodes) {
  const lowerSearchText = searchText.toLowerCase();
  
  // Build a continuous text string from consecutive nodes and track their positions
  for (let startNodeIndex = 0; startNodeIndex < textNodes.length; startNodeIndex++) {
    let combinedText = '';
    let nodeInfos = [];
    
    // Combine text from consecutive nodes (up to a reasonable limit)
    for (let endNodeIndex = startNodeIndex; endNodeIndex < Math.min(startNodeIndex + 10, textNodes.length); endNodeIndex++) {
      const node = textNodes[endNodeIndex];
      const nodeText = node.textContent;
      
      nodeInfos.push({
        node: node,
        startPos: combinedText.length,
        endPos: combinedText.length + nodeText.length,
        text: nodeText
      });
      
      combinedText += nodeText;
      
      // Check if we now have our search text in the combined string
      const lowerCombinedText = combinedText.toLowerCase();
      const matchIndex = lowerCombinedText.indexOf(lowerSearchText);
      
      if (matchIndex !== -1) {
        // Found the text spanning across nodes - highlight it
        return highlightAcrossMultipleNodes(nodeInfos, matchIndex, searchText.length, sentenceIndex, color);
      }
    }
  }
  
  return false;
}

// Function to highlight text that spans across multiple text nodes
function highlightAcrossMultipleNodes(nodeInfos, matchStartPos, matchLength, sentenceIndex, color) {
  const matchEndPos = matchStartPos + matchLength;
  
  // Find which nodes the match spans across
  const affectedNodes = nodeInfos.filter(info => 
    (info.startPos < matchEndPos && info.endPos > matchStartPos)
  );
  
  if (affectedNodes.length === 0) return false;
  
  // Process nodes in reverse order to avoid DOM position issues
  for (let i = affectedNodes.length - 1; i >= 0; i--) {
    const nodeInfo = affectedNodes[i];
    const node = nodeInfo.node;
    const parent = node.parentNode;
    
    // Calculate what part of this node should be highlighted
    const nodeMatchStart = Math.max(0, matchStartPos - nodeInfo.startPos);
    const nodeMatchEnd = Math.min(nodeInfo.text.length, matchEndPos - nodeInfo.startPos);
    
    if (nodeMatchStart >= nodeMatchEnd) continue;
    
    const beforeText = nodeInfo.text.substring(0, nodeMatchStart);
    const matchText = nodeInfo.text.substring(nodeMatchStart, nodeMatchEnd);
    const afterText = nodeInfo.text.substring(nodeMatchEnd);
    
    // Create highlight span
    const highlightSpan = document.createElement('span');
    highlightSpan.className = 'chrome-ext-multi-highlight';
    highlightSpan.setAttribute('data-sentence-index', sentenceIndex);
    highlightSpan.style.cssText = `background-color: ${color}; padding: 2px 4px; border-radius: 3px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); font-weight: bold;`;
    highlightSpan.textContent = matchText;
    
    // Replace the node content
    if (beforeText) {
      parent.insertBefore(document.createTextNode(beforeText), node);
    }
    parent.insertBefore(highlightSpan, node);
    
    if (afterText) {
      node.textContent = afterText;
    } else {
      parent.removeChild(node);
    }
  }
  
  console.log(`Highlighted text across ${affectedNodes.length} nodes`);
  return true;
}


// Function to scroll to a specific highlighted sentence
function scrollToSentence(sentenceIndex) {
  console.log(`Scrolling to sentence ${sentenceIndex}`);
  
  // Find the highlighted element with the matching data attribute
  const highlightedElement = document.querySelector(`.chrome-ext-multi-highlight[data-sentence-index="${sentenceIndex}"]`);
  
  if (!highlightedElement) {
    console.log(`Highlighted sentence ${sentenceIndex} not found on page`);
    return { success: false, message: 'Sentence not found on page' };
  }
  
  console.log('Found highlighted element:', highlightedElement);
  
  // Add a temporary pulsing animation to make it more visible
  const originalTransition = highlightedElement.style.transition;
  const originalTransform = highlightedElement.style.transform;
  
  highlightedElement.style.transition = 'all 0.3s ease-in-out';
  highlightedElement.style.transform = 'scale(1.05)';
  highlightedElement.style.boxShadow = '0 4px 8px rgba(0,0,0,0.3)';
  
  // Scroll to the element with smooth behavior
  highlightedElement.scrollIntoView({ 
    behavior: 'smooth', 
    block: 'center',
    inline: 'nearest'
  });
  
  // Reset the animation after a delay
  setTimeout(() => {
    highlightedElement.style.transition = originalTransition;
    highlightedElement.style.transform = originalTransform;
    highlightedElement.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
  }, 1000);
  
  // Add a brief pulse effect
  setTimeout(() => {
    highlightedElement.style.transition = 'background-color 0.2s ease-in-out';
    const originalBg = highlightedElement.style.backgroundColor;
    highlightedElement.style.backgroundColor = '#ff0080';
    
    setTimeout(() => {
      highlightedElement.style.backgroundColor = originalBg;
      highlightedElement.style.transition = originalTransition;
    }, 200);
  }, 500);
  
  return { 
    success: true, 
    message: `Scrolled to sentence ${sentenceIndex}`,
    element: highlightedElement.textContent.substring(0, 50) + '...'
  };
}