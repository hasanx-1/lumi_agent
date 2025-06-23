document.addEventListener('DOMContentLoaded', async function() {
    // DOM elements
    const messagesEl = document.getElementById('messages');
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('messageInput');
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const reservationsListEl = document.getElementById('reservationsList');
    
    // Log DOM elements for debugging
    console.log('DOM elements:', {
        messagesEl: !!messagesEl,
        messageForm: !!messageForm,
        messageInput: !!messageInput,
        menuToggle: !!menuToggle,
        sidebar: !!sidebar,
        reservationsListEl: !!reservationsListEl
    });
    // State variables
    let currentUser = null;
    let currentChat = null;
    let isWaitingForResponse = false;
    
    // Initialize the app
    async function initApp() {
        console.log('Initializing app...');
        try {
            // Get or create user ID
            currentUser = await getOrCreateUserId();
            if (!currentUser) {
                throw new Error('Failed to get user ID');
            }
            console.log(`User ID: ${currentUser}`);
            //ocument.getElementById('userInfo').textContent = `${currentUser.slice(0, 8)}...`;
            
            // Create a chat for the user
            const response = await fetch(`/create_chat/${currentUser}`, {
                credentials: 'include'
            });
            if (!response.ok) {
                throw new Error(`Failed to create chat: ${response.statusText}`);
            }
            const data = await response.json();
            currentChat = data.chat_id;
            console.log(`Chat created with ID: ${currentChat}`);
            
            // Load chat messages
            await loadChatMessages(currentChat);
            
            // Load reservations
            await loadReservations();
            
            // Setup event listeners
            setupEventListeners();
        } catch (error) {
            console.error('Initialization error:', error);
            addMessageToUI('Error initializing the app. Please refresh the page.', 'received');
        }
    }
    
    // Get or create user ID from cookies/backend
    async function getOrCreateUserId() {
        try {
            const response = await fetch('/get_user_id', {
                credentials: 'include'
            });
            if (!response.ok) {
                throw new Error(`Failed to get user ID: ${response.statusText}`);
            }
            const data = await response.json();
            console.log(`User ID received: ${data.user_id}`);
            return data.user_id;
        } catch (error) {
            console.error('Error getting user ID:', error);
            addMessageToUI('Failed to connect to the server. Please try again.', 'received');
            return null;
        }
    }
    
    // Load reservations for the user with retry
    async function loadReservations(retryCount = 3, delay = 1000) {
        if (!currentUser) {
            console.error('Cannot load reservations: currentUser is null');
            reservationsListEl.innerHTML = '<p class="no-reservations">Error: User not initialized.</p>';
            return;
        }

        try {
            console.log(`Loading reservations for user: ${currentUser}`);
            const response = await fetch(`/reservations/${currentUser}`, {
                credentials: 'include',
                headers: {
                    'Accept': 'application/json'
                }
            });
            if (!response.ok) {
                throw new Error(`Failed to load reservations: ${response.status} - ${response.statusText}`);
            }
            const data = await response.json();
            console.log('Reservations data:', data);
            
            reservationsListEl.innerHTML = '';
            
            if (data.reservations && data.reservations.length > 0) {
                data.reservations.forEach((reservation, index) => {
                    const reservationEl = document.createElement('div');
                    reservationEl.className = 'reservation-item';
                    reservationEl.dataset.reservationId = `res-${index}`; // Placeholder ID
                    
                    const date = new Date(reservation.day);
                    const formattedDate = date.toLocaleDateString('en-US', {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric'
                    });
                    
                    reservationEl.innerHTML = `
                        <div class="reservation-details">
                            <span class="label">Date:</span>
                            <span class="value">${formattedDate}</span>
                            <span class="label">Time:</span>
                            <span class="value">${reservation.time}</span>
                        </div>
                        <span class="status">Confirmed</span>
                    `;
                    reservationsListEl.appendChild(reservationEl);
                    
                    // Add click event for interactivity
                    //reservationEl.addEventListener('click', () => {
                    //    console.log(`Clicked reservation: ${reservationEl.dataset.reservationId}`, {
                    //        date: formattedDate,
                     //       time: reservation.time
                    //    });
                        // Placeholder for future actions (e.g., cancel)
                    //    addMessageToUI('Reservation details clicked. Action coming soon!', 'received');
                    //});
                });
            } else {
                reservationsListEl.innerHTML = '<p class="no-reservations">No reservations found.</p>';
            }
        } catch (error) {
            console.error(`Error loading reservations (attempt ${4 - retryCount}/3):`, error);
            if (retryCount > 1) {
                await new Promise(resolve => setTimeout(resolve, delay));
                return loadReservations(retryCount - 1, delay * 2);
            }
            reservationsListEl.innerHTML = '<p class="no-reservations">Error loading reservations. Please try again.</p>';
            addMessageToUI('Failed to load reservations. Please try again later.', 'received');
        }
    }
    
    // Load messages for the chat
    async function loadChatMessages(chatId) {
        currentChat = chatId;
        messagesEl.innerHTML = '';
        console.log('Loading messages for chat:', chatId);
        
        try {
            const response = await fetch(`/chat/${chatId}/messages`, {
                credentials: 'include'
            });
            if (!response.ok) {
                throw new Error(`Failed to load messages: ${response.statusText}`);
            }
            const data = await response.json();
            
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => {
                    addMessageToUI(msg.text, msg.type);
                });
                
                messagesEl.scrollTop = messagesEl.scrollHeight;
            } else {
                addMessageToUI('Hello! How can I help you today?', 'received');
            }
        } catch (error) {
            console.error('Error loading chat messages:', error);
            addMessageToUI(`Error loading messages: ${error.message}`, 'received');
        }
    }
    
    // Add a message to the UI
    function addMessageToUI(text, type) {
        const welcomeMsg = document.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }
        
        const messageEl = document.createElement('div');
        messageEl.className = `message ${type}`;
        
        const messageText = document.createElement('div');
        messageText.textContent = text;
        
        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageEl.appendChild(messageText);
        messageEl.appendChild(messageTime);
        messagesEl.appendChild(messageEl);
        
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }
    
    // Handle message submission
    async function handleMessageSubmit(e) {
        e.preventDefault();
        console.log('handleMessageSubmit triggered');
        
        const message = messageInput.value.trim();
        console.log('Message submission check:', {
            message: !!message,
            currentChat: !!currentChat,
            isWaitingForResponse
        });
        
        if (!message || !currentChat || isWaitingForResponse) {
            return;
        }
        
        console.log(`Sending message: ${message}`);
        addMessageToUI(message, 'sent');
        messageInput.value = '';
        
        isWaitingForResponse = true;
        const loadingEl = document.createElement('div');
        loadingEl.className = 'message received';
        loadingEl.innerHTML = '<div class="loading"></div>';
        messagesEl.appendChild(loadingEl);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        
        try {
            const response = await fetch(`/chat/${currentUser}/${currentChat}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    question: message
                }),
                credentials: 'include'
            });
            
            console.log(`Response status: ${response.status}`);
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server error: ${response.status} - ${errorText}`);
            }
            
            const data = await response.json();
            console.log('Response data:', data);
            
            messagesEl.removeChild(loadingEl);
            if (data.response) {
                addMessageToUI(data.response, 'received');
                console.log('Reloading reservations after message');
                await loadReservations();
            } else {
                addMessageToUI('Sorry, I couldn\'t process your request.', 'received');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            messagesEl.removeChild(loadingEl);
            addMessageToUI(`Error: ${error.message || 'Failed to connect to the server. Please try again.'}`, 'received');
        } finally {
            isWaitingForResponse = false;
        }
    }
    
    // Toggle sidebar on mobile
    function toggleSidebar() {
        console.log('toggleSidebar triggered');
        sidebar.classList.toggle('open');
    }
    
    // Setup all event listeners
    function setupEventListeners() {
        console.log('Setting up event listeners');
        messageForm.addEventListener('submit', handleMessageSubmit);
        menuToggle.addEventListener('click', toggleSidebar);
        
        document.addEventListener('click', (e) => {
            console.log('Click outside check:', {
                isMobile: window.innerWidth <= 768,
                sidebarContains: sidebar.contains(e.target),
                menuToggleContains: menuToggle.contains(e.target),
                isSidebarOpen: sidebar.classList.contains('open')
            });
            if (window.innerWidth <= 768 && 
                !sidebar.contains(e.target) && 
                !menuToggle.contains(e.target) &&
                sidebar.classList.contains('open')) {
                toggleSidebar();
            }
        });
    }
    
    // Initialize the app
    initApp();
});
