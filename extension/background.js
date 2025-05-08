// Session management
let currentVideoId = null;

// Handle messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.action) {
    case 'getVideoId':
      chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
        if (tabs[0] && tabs[0].url.includes('youtube.com/watch')) {
          const url = new URL(tabs[0].url);
          currentVideoId = url.searchParams.get('v');
          sendResponse({videoId: currentVideoId});
        } else {
          sendResponse({videoId: null});
        }
      });
      return true; // Required for async response
    
    case 'clearCache':
      fetch('http://localhost:5000/api/clear_cache', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({videoId: currentVideoId})
      });
      break;
  }
});

// Listen for tab updates to detect YouTube video changes
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url) {
    const url = new URL(changeInfo.url);
    if (url.hostname.includes('youtube.com') && url.searchParams.get('v')) {
      currentVideoId = url.searchParams.get('v');
    }
  }
});