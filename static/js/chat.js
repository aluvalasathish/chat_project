let selectedUserId = null;
let chatSocket = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
let isConnecting = false;
let intentionalClose = false;

// DOM Elements
const messagesList = document.getElementById('messagesList');
const messageForm = document.getElementById('messageForm');
const messageInput = document.getElementById('messageInput');
const selectedUserHeader = document.getElementById('selectedUser');
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');

// Initialize UI state
if (messageInput) messageInput.disabled = true;
if (messageForm) {
    const submitButton = messageForm.querySelector('button');
    if (submitButton) submitButton.disabled = true;
}
if (selectedUserHeader) selectedUserHeader.textContent = 'Select a user to start chatting';
if (messagesList) {
    messagesList.innerHTML = `
        <div class="flex flex-col items-center justify-center h-full space-y-4">
            <div class="bg-gray-100 text-gray-600 px-6 py-3 rounded-lg text-center">
                <h3 class="font-medium mb-2">Welcome to ChatApp!</h3>
                <p class="text-sm">Select a user from the sidebar to start a conversation</p>
            </div>
        </div>
    `;
}

function connectWebSocket() {
    if (isConnecting) return; // Prevent multiple connection attempts
    if (chatSocket && chatSocket.readyState === WebSocket.OPEN) return;

    isConnecting = true;
    intentionalClose = false;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8001/ws/chat/`;
    
    console.log('Attempting to connect to:', wsUrl);
    
    try {
        if (chatSocket) {
            chatSocket.close();
        }

        chatSocket = new WebSocket(wsUrl);

        chatSocket.onopen = function() {
            console.log('WebSocket connection established');
            isConnecting = false;
            reconnectAttempts = 0;
            
            // Only show connection message if a user is selected
            if (selectedUserId) {
                messagesList.innerHTML = `
                    <div class="flex justify-center">
                        <div class="bg-green-100 text-green-700 px-4 py-2 rounded-full text-sm">
                            Connected to chat server
                        </div>
                    </div>
                `;
                // Reload messages if a user was selected
                loadMessageHistory(selectedUserId);
            }
        };

        chatSocket.onmessage = function(e) {
            try {
                const data = JSON.parse(e.data);
                console.log('Received message:', data);
                
                // Only process messages if they contain an error or if a user is selected
                if (data.error) {
                    console.error('Received error:', data.error);
                    if (selectedUserId) {  // Only show errors if a user is selected
                        messagesList.innerHTML = `<div class="text-center text-red-500 p-2">${data.error}</div>`;
                    }
                } else if (selectedUserId) {  // Only process messages if a user is selected
                    addMessage(data);
                }
            } catch (error) {
                console.error('Error processing message:', error);
            }
        };

        chatSocket.onclose = function(e) {
            console.log('WebSocket connection closed. Code:', e.code, 'Reason:', e.reason);
            isConnecting = false;
            
            if (e.code === 4001) {
                messagesList.innerHTML = '<div class="text-center text-red-500 p-2">Authentication required</div>';
                return;
            }

            if (intentionalClose) {
                console.log('Connection closed intentionally');
                return;
            }

            messagesList.innerHTML = '<div class="text-center text-yellow-500 p-2">Disconnected from chat server</div>';
            
            if (reconnectAttempts < maxReconnectAttempts) {
                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
                console.log(`Reconnecting in ${delay/1000} seconds...`);
                setTimeout(() => {
                    console.log('Attempting to reconnect...');
                    reconnectAttempts++;
                    connectWebSocket();
                }, delay);
            } else {
                console.log('Max reconnection attempts reached');
                messagesList.innerHTML = `
                    <div class="flex justify-center">
                        <div class="bg-red-100 text-red-700 px-4 py-2 rounded-full text-sm">
                            Unable to connect to chat server. Please refresh the page.
                        </div>
                    </div>
                `;
            }
        };

        chatSocket.onerror = function(e) {
            console.error('WebSocket error:', e);
            isConnecting = false;
        };

    } catch (error) {
        console.error('Error creating WebSocket:', error);
        isConnecting = false;
        messagesList.innerHTML = '<div class="text-center text-red-500 p-2">Failed to create WebSocket connection</div>';
    }
}

// Connect to WebSocket when page loads
document.addEventListener('DOMContentLoaded', function() {
    connectWebSocket();
    setupUserSelection();
    setupMessageForm();
});

// Add user search functionality
const userSearch = document.getElementById('userSearch');
const allUsersList = document.getElementById('allUsersList');
const userButtons = document.querySelectorAll('.user-button');

if (userSearch) {
    userSearch.addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        
        userButtons.forEach(button => {
            const username = button.dataset.username.toLowerCase();
            const shouldShow = username.includes(searchTerm);
            button.style.display = shouldShow ? 'flex' : 'none';
        });
    });
}

// Enhance user selection with active state
function setupUserSelection() {
    const userButtons = document.querySelectorAll('.user-button');
    let activeChat = null;

    userButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active state from previous chat
            if (activeChat) {
                activeChat.classList.remove('bg-blue-50', 'border-blue-500');
            }

            // Add active state to current chat
            this.classList.add('bg-blue-50', 'border-blue-500');
            activeChat = this;

            // Set up chat
            selectedUserId = this.dataset.userId;
            const username = this.dataset.username;
            
            // Update UI
            selectedUserHeader.textContent = username;
            messageInput.disabled = false;
            messageForm.querySelector('button').disabled = false;
            
            // Load messages
            messagesList.innerHTML = '<div class="text-center text-gray-500">Loading messages...</div>';
            loadMessageHistory(selectedUserId);

            // Close sidebar on mobile
            if (window.innerWidth < 768) {
                sidebar.classList.add('-translate-x-full');
            }
        });
    });
}

// Setup message form
function setupMessageForm() {
    messageForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = messageInput.value.trim();
        
        if (message && selectedUserId && chatSocket && chatSocket.readyState === WebSocket.OPEN) {
            try {
                chatSocket.send(JSON.stringify({
                    'message': message,
                    'recipient_id': selectedUserId
                }));
                messageInput.value = '';
            } catch (error) {
                console.error('Error sending message:', error);
            }
        }
    });
}

// Load message history
async function loadMessageHistory(userId) {
    try {
        const response = await fetch(`/api/messages/?user_id=${userId}`);
        const messages = await response.json();
        
        messagesList.innerHTML = '';
        
        if (messages.length === 0) {
            messagesList.innerHTML = `
                <div class="flex justify-center">
                    <div class="bg-gray-100 text-gray-500 px-4 py-2 rounded-full text-sm">
                        No messages yet. Start a conversation!
                    </div>
                </div>
            `;
            return;
        }

        // Group messages by date
        const messagesByDate = messages.reduce((groups, message) => {
            const date = new Date(message.timestamp).toLocaleDateString();
            if (!groups[date]) {
                groups[date] = [];
            }
            groups[date].push(message);
            return groups;
        }, {});

        // Add messages with date separators
        Object.entries(messagesByDate).forEach(([date, dateMessages]) => {
            // Add date separator
            const dateElement = document.createElement('div');
            dateElement.className = 'flex justify-center my-4';
            dateElement.innerHTML = `
                <div class="bg-gray-100 text-gray-500 px-3 py-1 rounded-full text-xs">
                    ${date}
                </div>
            `;
            messagesList.appendChild(dateElement);

            // Add messages for this date
            dateMessages.forEach(message => {
                addMessage({
                    sender: message.sender_username,
                    sender_id: message.sender,
                    content: message.content,
                    timestamp: message.timestamp
                });
            });
        });

        messagesList.scrollTop = messagesList.scrollHeight;
    } catch (error) {
        console.error('Error loading messages:', error);
        messagesList.innerHTML = `
            <div class="flex justify-center">
                <div class="bg-red-100 text-red-500 px-4 py-2 rounded-full text-sm">
                    Error loading messages
                </div>
            </div>
        `;
    }
}

// Add a message to the UI
function addMessage(data) {
    // Don't add messages if no user is selected
    if (!selectedUserId) return;
    
    const isCurrentUser = parseInt(data.sender_id) === parseInt(currentUserId);
    const messageElement = document.createElement('div');
    messageElement.className = `flex ${isCurrentUser ? 'justify-end' : 'justify-start'} mb-4`;
    
    // Get sender name, fallback to sender_username if sender is not available
    const senderName = data.sender || data.sender_username || 'Unknown';
    
    // Validate timestamp before using it
    let timeString = '';
    try {
        const timestamp = new Date(data.timestamp);
        if (!isNaN(timestamp)) {
            timeString = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
    } catch (error) {
        console.error('Invalid timestamp:', error);
    }
    
    const messageContent = `
        <div class="flex flex-col ${isCurrentUser ? 'items-end' : 'items-start'} max-w-[70%]">
            ${!isCurrentUser ? `
                <div class="flex items-center space-x-2 mb-1">
                    <div class="w-6 h-6 rounded-full bg-gray-300 flex items-center justify-center">
                        <span class="text-white text-xs font-medium">${senderName.charAt(0).toUpperCase()}</span>
                    </div>
                    <span class="text-sm text-gray-600">${senderName}</span>
                </div>
            ` : ''}
            <div class="${isCurrentUser ? 'bg-blue-500 text-white ml-auto' : 'bg-gray-200 text-gray-800'} 
                        rounded-2xl px-4 py-2 break-words shadow-sm
                        ${isCurrentUser ? 'rounded-tr-none' : 'rounded-tl-none'}">
                ${data.content}
            </div>
            ${timeString ? `
                <div class="text-xs text-gray-500 mt-1">
                    ${timeString}
                </div>
            ` : ''}
        </div>
    `;
    
    messageElement.innerHTML = messageContent;
    messagesList.appendChild(messageElement);
    messagesList.scrollTop = messagesList.scrollHeight;
}

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden, close connection intentionally
        if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
            intentionalClose = true;
            chatSocket.close();
        }
    } else {
        // Page is visible again, reconnect if needed
        if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) {
            reconnectAttempts = 0;
            connectWebSocket();
        }
    }
});

// Handle page unload
window.addEventListener('beforeunload', function() {
    if (chatSocket) {
        intentionalClose = true;
        chatSocket.close();
    }
});

// Add this function to format the timestamp
function formatTimestamp(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Add sidebar toggle functionality
sidebarToggle.addEventListener('click', function() {
    sidebar.classList.toggle('-translate-x-full');
});

// Add responsive handling
window.addEventListener('resize', function() {
    if (window.innerWidth >= 768) {
        sidebar.classList.remove('-translate-x-full');
    }
});