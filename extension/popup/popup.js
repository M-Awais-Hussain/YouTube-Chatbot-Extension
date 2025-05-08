document.addEventListener('DOMContentLoaded', async () => {
  const messagesContainer = document.getElementById('messages');
  const userInput = document.getElementById('user-input');
  const sendBtn = document.getElementById('send-btn');
  const micBtn = document.getElementById('mic-btn');
  const statusEl = document.querySelector('.status-text');
  const statusDot = document.querySelector('.status-dot');
  const settingsBtn = document.getElementById('settings-btn');
  const settingsModal = document.getElementById('settings-modal');
  const closeModal = document.querySelector('.close-modal');
  const apiUrlInput = document.getElementById('api-url');
  const darkModeToggle = document.getElementById('dark-mode');
  const clearCacheBtn = document.getElementById('clear-cache');
  const suggestionPills = document.querySelectorAll('.suggestion-pill');

  let videoId = null;
  let API_URL = 'http://localhost:5000';
  let isListening = false;
  let recognition = null;

  // Check and request microphone permission
  async function checkMicrophonePermission() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(track => track.stop());
      return true;
    } catch (error) {
      console.error('Microphone permission denied:', error);
      addAssistantMessage('Please allow microphone access in Chrome settings to use voice input');
      return false;
    }
  }

  // Load settings from storage
  chrome.storage.sync.get(['apiUrl', 'darkMode'], (result) => {
    if (result.apiUrl) {
      API_URL = result.apiUrl;
      apiUrlInput.value = result.apiUrl;
    }

    if (result.darkMode) {
      darkModeToggle.checked = true;
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  });

  // Initialize
  chrome.runtime.sendMessage({ action: 'getVideoId' }, async (response) => {
    if (!response?.videoId) {
      setStatus('Not on YouTube video', 'error');
      disableInput();
      return;
    }

    videoId = response.videoId;
    await processVideo();
  });

  // Process video
  async function processVideo() {
    setStatus('Processing video...', 'thinking');

    try {
      const response = await fetch(`${API_URL}/api/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ videoId })
      });

      const data = await response.json();

      if (data.error) {
        setStatus(`Error: ${data.error}`, 'error');
        disableInput();
      } else {
        setStatus('Ready', 'ready');
        addAssistantMessage('I\'ve analyzed this video. Ask me anything about it!');
      }
    } catch (error) {
      setStatus('Connection failed', 'error');
      console.error('Processing error:', error);
    }
  }

  // ✅ Send message function (added)
  async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;
  
    addUserMessage(message);
    userInput.value = '';
    userInput.style.height = 'auto'; // reset textarea height
  
    setStatus('Thinking...', 'thinking');
  
    try {
      const response = await fetch(`${API_URL}/api/query`, {  // ✅ FIXED endpoint
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ videoId, question: message })
      });
  
      const data = await response.json();
  
      if (data.error) {
        addAssistantMessage(`Error: ${data.error}`);
        setStatus('Error', 'error');
      } else {
        addAssistantMessage(data.answer);
        setStatus('Ready', 'ready');
      }
    } catch (error) {
      console.error('Send message error:', error);
      addAssistantMessage('Failed to get response from server.');
      setStatus('Error', 'error');
    }
  }
  

  // Handle user input
  sendBtn.addEventListener('click', sendMessage);
  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }

    // Auto-resize textarea
    if (e.key === 'Enter' || e.key === 'Backspace') {
      setTimeout(() => {
        userInput.style.height = 'auto';
        userInput.style.height = `${Math.min(userInput.scrollHeight, 120)}px`;
      }, 0);
    }
  });

  // ✅ Handle suggestion clicks → trigger sendMessage
  suggestionPills.forEach(pill => {
    pill.addEventListener('click', () => {
      userInput.value = pill.textContent;
      sendMessage();
    });
  });

  // Voice input with proper permission handling
  micBtn.addEventListener('click', toggleVoiceInput);

  async function toggleVoiceInput() {
    if (!('webkitSpeechRecognition' in window)) {
      addAssistantMessage('Voice input is not supported in your browser');
      return;
    }

    if (isListening) {
      stopVoiceInput();
      return;
    }

    const hasPermission = await checkMicrophonePermission();
    if (!hasPermission) return;

    recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      isListening = true;
      micBtn.classList.add('listening');
      setStatus('Listening...', 'thinking');
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      userInput.value = transcript;
      sendMessage();
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error', event.error);
      let errorMessage = 'Voice input error';

      switch (event.error) {
        case 'not-allowed':
          errorMessage = 'Microphone access denied. Please allow microphone access in Chrome settings.';
          break;
        case 'no-speech':
          errorMessage = 'No speech detected. Please try again.';
          break;
        case 'audio-capture':
          errorMessage = 'Audio capture error. Please check your microphone.';
          break;
        default:
          errorMessage = `Error: ${event.error}`;
      }

      addAssistantMessage(errorMessage);
      stopVoiceInput();
    };

    recognition.onend = () => {
      stopVoiceInput();
    };

    try {
      recognition.start();
    } catch (error) {
      console.error('Recognition start error:', error);
      addAssistantMessage('Error starting voice recognition');
      stopVoiceInput();
    }
  }

  function stopVoiceInput() {
    if (recognition) {
      try {
        recognition.stop();
      } catch (e) {
        console.log('Recognition already stopped');
      }
    }
    isListening = false;
    micBtn.classList.remove('listening');
    setStatus('Ready', 'ready');
  }

  // UI Helpers
  function addUserMessage(text) {
    addMessage('user', text);
  }

  function addAssistantMessage(text) {
    addMessage('assistant', text);
  }

  function addMessage(role, text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;

    // Format timestamps [HH:MM] and make them clickable
    const formattedText = text.replace(
      /\[(\d{1,2}):(\d{2})\]/g,
      '<span class="timestamp" onclick="seekToTimestamp($1, $2)">[$1:$2]</span>'
    );

    messageDiv.innerHTML = formattedText;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function setStatus(text, state) {
    statusEl.textContent = text;
    statusDot.className = 'status-dot';

    switch (state) {
      case 'ready':
        statusDot.classList.add('ready');
        break;
      case 'thinking':
        statusDot.classList.add('thinking');
        break;
      case 'error':
        statusDot.classList.add('error');
        break;
    }
  }

  function disableInput() {
    userInput.disabled = true;
    sendBtn.disabled = true;
    micBtn.disabled = true;
  }
});

// Seek to timestamp in YouTube video
function seekToTimestamp(minutes, seconds) {
  const timeInSeconds = parseInt(minutes) * 60 + parseInt(seconds);
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    chrome.tabs.sendMessage(tabs[0].id, {
      action: 'seekTo',
      time: timeInSeconds
    });
  });
}
