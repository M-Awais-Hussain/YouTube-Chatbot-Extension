// content.js - This runs in the context of YouTube pages
console.log("YouTube RAG Assistant content script loaded");

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getVideoId') {
    const videoId = new URLSearchParams(window.location.search).get('v');
    sendResponse({ videoId });
  }
  
  if (request.action === 'seekTo') {
    const video = document.querySelector('video');
    if (video) {
      video.currentTime = request.time;
      sendResponse({ success: true });
    } else {
      sendResponse({ success: false });
    }
  }
});