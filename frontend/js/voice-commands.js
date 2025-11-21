// ===== VOICE RECOGNITION SETUP =====
let recognition = null;
let isListening = false;

// Initialize Speech Recognition
function initVoiceRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.log('Speech recognition not supported');
        return null;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    
    recognition.onstart = () => {
        isListening = true;
        showVoiceIndicator();
        console.log('Voice recognition started');
    };
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript.toLowerCase();
        console.log('Recognized:', transcript);
        processVoiceCommand(transcript);
    };
    
    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        hideVoiceIndicator();
        
        if (event.error === 'no-speech') {
            showNotification('No speech detected. Please try again.', 'error');
        } else if (event.error === 'not-allowed') {
            showNotification('Microphone access denied. Please enable it in settings.', 'error');
        } else {
            showNotification('Voice recognition error. Please try again.', 'error');
        }
        
        isListening = false;
    };
    
    recognition.onend = () => {
        isListening = false;
        hideVoiceIndicator();
        console.log('Voice recognition ended');
    };
    
    return recognition;
}

// ===== START VOICE COMMAND =====
function startVoiceCommand() {
    if (!recognition) {
        recognition = initVoiceRecognition();
        if (!recognition) {
            showNotification('Voice commands not supported in this browser', 'error');
            return;
        }
    }
    
    if (isListening) {
        recognition.stop();
        return;
    }
    
    try {
        recognition.start();
    } catch (error) {
        console.error('Error starting voice recognition:', error);
        showNotification('Could not start voice recognition', 'error');
    }
}

// ===== PROCESS VOICE COMMANDS =====
function processVoiceCommand(command) {
    hideVoiceIndicator();
    
    // Navigation commands
    if (command.includes('dashboard') || command.includes('home')) {
        navigateToSection('dashboard');
        speak('Showing dashboard');
    }
    else if (command.includes('camera') || command.includes('cameras')) {
        navigateToSection('cameras');
        speak('Showing cameras');
    }
    else if (command.includes('alert') || command.includes('alerts')) {
        navigateToSection('alerts');
        speak('Showing alerts');
    }
    else if (command.includes('report') || command.includes('reports')) {
        navigateToSection('reports');
        speak('Showing reports');
    }
    
    // Theme commands
    else if (command.includes('dark mode') || command.includes('dark theme')) {
        if (!document.body.classList.contains('dark-theme')) {
            toggleTheme();
            speak('Dark mode activated');
        } else {
            speak('Dark mode is already active');
        }
    }
    else if (command.includes('light mode') || command.includes('light theme')) {
        if (document.body.classList.contains('dark-theme')) {
            toggleTheme();
            speak('Light mode activated');
        } else {
            speak('Light mode is already active');
        }
    }
    
    // Data retrieval commands
    else if (command.includes('how many alert') || command.includes('number of alert')) {
        const count = document.getElementById('anomaliesDetected').textContent;
        speak(`There are ${count} alerts today`);
    }
    else if (command.includes('how many camera') || command.includes('number of camera')) {
        const count = document.getElementById('activeCameras').textContent;
        speak(`There are ${count} active cameras`);
    }
    else if (command.includes('how many people') || command.includes('people detected')) {
        const count = document.getElementById('peopleDetected').textContent;
        speak(`${count} people have been detected today`);
    }
    
    // Action commands
    else if (command.includes('generate report')) {
        openReportGenerator();
        speak('Opening report generator');
    }
    else if (command.includes('upload video') || command.includes('upload file')) {
        openUploadModal();
        speak('Opening upload dialog');
    }
    else if (command.includes('show today') || command.includes('todays') || command.includes("today's")) {
        if (command.includes('anomal') || command.includes('alert')) {
            navigateToSection('alerts');
            speak('Showing today\'s anomalies');
        } else {
            navigateToSection('dashboard');
            speak('Showing today\'s overview');
        }
    }
    else if (command.includes('show yesterday')) {
        showNotification('Showing yesterday\'s data', 'info');
        speak('Loading yesterday\'s data');
    }
    else if (command.includes('refresh') || command.includes('reload')) {
        loadDashboardData();
        speak('Refreshing dashboard');
    }
    
    // Status commands
    else if (command.includes('what') && (command.includes('status') || command.includes('happening'))) {
        const alerts = document.getElementById('anomaliesDetected').textContent;
        const cameras = document.getElementById('activeCameras').textContent;
        speak(`System status: ${cameras} cameras online, ${alerts} alerts today`);
    }
    
    // Help command
    else if (command.includes('help') || command.includes('what can you do')) {
        speak('You can say: show dashboard, show cameras, show alerts, generate report, how many alerts, dark mode, or light mode');
        showNotification('Voice Commands Help', 'info');
        setTimeout(() => {
            showVoiceCommandsHelp();
        }, 500);
    }
    
    // Unknown command
    else {
        speak('Sorry, I didn\'t understand that command. Say help to see available commands.');
        showNotification('Command not recognized. Say "help" for available commands.', 'error');
    }
}

// ===== SHOW VOICE COMMANDS HELP =====
function showVoiceCommandsHelp() {
    const helpText = `
        <div style="padding: 20px;">
            <h3 style="margin-bottom: 16px;">Available Voice Commands:</h3>
            <div style="display: grid; gap: 12px;">
                <div><strong>Navigation:</strong> "Show dashboard", "Show cameras", "Show alerts", "Show reports"</div>
                <div><strong>Theme:</strong> "Dark mode", "Light mode"</div>
                <div><strong>Information:</strong> "How many alerts", "How many cameras", "How many people"</div>
                <div><strong>Actions:</strong> "Generate report", "Upload video", "Refresh dashboard"</div>
                <div><strong>Status:</strong> "What's the status", "What's happening"</div>
            </div>
        </div>
    `;
    
    // Create a modal or notification with help text
    const helpModal = document.createElement('div');
    helpModal.className = 'modal active';
    helpModal.innerHTML = `
        <div class="modal-content" style="max-width: 600px;">
            <div class="modal-header">
                <h2>Voice Commands</h2>
                <button class="modal-close" onclick="this.closest('.modal').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                ${helpText}
                <button class="btn-primary full-width" onclick="this.closest('.modal').remove()" style="margin-top: 20px;">
                    Got it!
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(helpModal);
}

// ===== TEXT-TO-SPEECH =====
function speak(text) {
    if (!('speechSynthesis' in window)) {
        console.log('Speech synthesis not supported');
        return;
    }
    
    // Cancel any ongoing speech
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;
    utterance.lang = 'en-US';
    
    // Show feedback
    showNotification(text, 'info');
    
    window.speechSynthesis.speak(utterance);
}

// ===== UI INDICATORS =====
function showVoiceIndicator() {
    const indicator = document.getElementById('voiceIndicator');
    indicator.classList.add('active');
    
    // Change button icon
    const voiceBtn = document.querySelector('#voiceBtn i');
    voiceBtn.className = 'fas fa-microphone-slash';
}

function hideVoiceIndicator() {
    const indicator = document.getElementById('voiceIndicator');
    indicator.classList.remove('active');
    
    // Change button icon back
    const voiceBtn = document.querySelector('#voiceBtn i');
    voiceBtn.className = 'fas fa-microphone';
}

// ===== KEYBOARD SHORTCUT =====
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Shift + V to activate voice commands
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'V') {
        e.preventDefault();
        startVoiceCommand();
    }
});

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    // Check if speech recognition is supported
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        console.log('Voice commands are available');
        // Add keyboard shortcut hint
        console.log('Press Ctrl+Shift+V to activate voice commands');
    } else {
        console.log('Voice commands not supported in this browser');
        // Hide voice button if not supported
        const voiceBtn = document.getElementById('voiceBtn');
        if (voiceBtn) {
            voiceBtn.style.display = 'none';
        }
    }
});