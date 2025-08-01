(function() {
    'use strict';

    // --- STATE MANAGEMENT ---
    let state = {
        apiUrl: '',
        targetElement: null,
        jwtToken: null,
        verificationToken: null,
        userEmail: '',
        currentView: 'loading', // loading, email_entry, otp_entry, profile_creation, chat
        userName: ''
    };

    // --- HTML TEMPLATES ---
    const templates = {
        widgetShell: `
            <div class="tyra-widget-container">
                <div class="tyra-widget-header">
                    <span>Tyra Health Companion</span>
                    <div class="tyra-header-controls"></div>
                </div>
                <div class="tyra-view-container"></div>
            </div>`,
        headerControls: `
            <button class="tyra-settings-btn" title="Settings">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
            </button>
            <div class="tyra-settings-menu">
                <button id="tyra-dashboard-btn">Dashboard</button>
                <button id="tyra-logout-btn">Logout</button>
            </div>
            `,
        emailEntryView: `
            <div class="tyra-form-view">
                <h2>Welcome!</h2>
                <p>Please enter your email to begin or continue your conversation.</p>
                <form id="tyra-email-form">
                    <label for="tyra-email-input">Email Address</label>
                    <input type="email" id="tyra-email-input" placeholder="you@example.com" required>
                    <div class="tyra-form-error"></div>
                    <button type="submit">Continue</button>
                </form>
            </div>`,
        otpEntryView: `
            <div class="tyra-form-view">
                <h2>Check your email</h2>
                <p>We've sent a 6-digit code to <strong>${() => state.userEmail}</strong>. The code expires shortly.</p>
                <form id="tyra-otp-form">
                    <label for="tyra-otp-input">Verification Code</label>
                    <input type="text" id="tyra-otp-input" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" required>
                    <div class="tyra-form-error"></div>
                    <button type="submit">Verify</button>
                </form>
            </div>`,
        profileCreationView: `
            <div class="tyra-form-view">
                <h2>Create your profile</h2>
                <p>Just a few more details to get you started.</p>
                <form id="tyra-profile-form">
                    <label for="tyra-name-input">Name</label>
                    <input type="text" id="tyra-name-input" required>
                    <label for="tyra-age-input">Age</label>
                    <input type="number" id="tyra-age-input" min="13" max="100" required>
                    <div class="tyra-form-error"></div>
                    <button type="submit">Start Chatting</button>
                </form>
            </div>`,
        chatView: `
            <div class="tyra-chat-log"></div>
            <form class="tyra-chat-form">
                <input type="text" placeholder="Ask a question..." autocomplete="off" required>
                <button type="submit">Send</button>
            </form>`
    };

    // --- RENDER & DOM FUNCTIONS ---
    function render() {
        const container = state.targetElement.querySelector('.tyra-view-container');
        if (!container) return;

        let viewHTML = '';
        switch (state.currentView) {
            case 'email_entry':
                viewHTML = templates.emailEntryView;
                break;
            case 'otp_entry':
                viewHTML = templates.otpEntryView.replace('${() => state.userEmail}', state.userEmail);
                break;
            case 'profile_creation':
                viewHTML = templates.profileCreationView;
                break;
            case 'chat':
                viewHTML = templates.chatView;
                break;
            default:
                viewHTML = '<div class="tyra-form-view"><p>Loading...</p></div>';
        }
        container.innerHTML = viewHTML;
        
        const headerControls = state.targetElement.querySelector('.tyra-header-controls');
        headerControls.innerHTML = (state.currentView === 'chat' && state.jwtToken) ? templates.headerControls : '';

        bindEventListeners();
        if (state.currentView === 'chat') {
            const welcomeMessage = state.userName 
                ? `Welcome back, ${state.userName}! How can I assist you today?`
                : 'Welcome! I am Tyra. Feel free to ask me anything.';
            addMessage(welcomeMessage, 'ai');
        }
    }

    function addMessage(text, sender) {
        const chatLog = state.targetElement.querySelector('.tyra-chat-log');
        if (!chatLog) return;
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('tyra-message', `tyra-${sender}-message`);
        messageDiv.textContent = text;
        chatLog.appendChild(messageDiv);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    function setFormError(formId, message) {
        const errorDiv = state.targetElement.querySelector(`#${formId} .tyra-form-error`);
        if (errorDiv) {
            errorDiv.textContent = message;
        }
    }
    
    // --- API CALLS ---
    async function getApiConfig() {
        const response = await fetch(`${state.apiUrl}/api/v1/config`);
        if (!response.ok) throw new Error('Could not fetch API config');
        return response.json();
    }
    
    async function authenticateAsGuest() {
        const response = await fetch(`${state.apiUrl}/api/v1/auth/guest`, { method: 'POST' });
        if (!response.ok) throw new Error('Guest authentication failed');
        return response.json();
    }
    
    async function getDashboardToken() {
        const response = await fetch(`${state.apiUrl}/api/v1/auth/dashboard_token`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${state.jwtToken}` }
        });
        if (!response.ok) throw new Error('Could not get dashboard token');
        return response.json();
    }

    async function requestOtp(email) {
        const response = await fetch(`${state.apiUrl}/api/v1/auth/request_otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        return response.json();
    }
    
    async function verifyOtp(email, otp) {
        const response = await fetch(`${state.apiUrl}/api/v1/auth/verify_otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, otp })
        });
        return { ok: response.ok, data: await response.json() };
    }

    async function createProfile(name, age) {
        const response = await fetch(`${state.apiUrl}/api/v1/auth/create_profile`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.verificationToken}`
            },
            body: JSON.stringify({ name, age })
        });
        return { ok: response.ok, data: await response.json() };
    }

    async function sendChatMessage(message) {
        const response = await fetch(`${state.apiUrl}/api/v1/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.jwtToken}`
            },
            body: JSON.stringify({ message })
        });
        return { ok: response.ok, data: await response.json() };
    }

    // --- EVENT HANDLERS ---
    function onLogout() {
        state.jwtToken = null;
        state.verificationToken = null;
        state.userName = '';
        state.userEmail = '';
        state.currentView = 'email_entry'; // Or guest, based on config
        window.TyraWidget.init({ // Re-initialize to respect config
            targetElementId: state.targetElement.id,
            apiUrl: state.apiUrl
        });
    }

    async function onDashboardClick() {
        try {
            const data = await getDashboardToken();
            if (data.token) {
                const dashboardUrl = `${state.apiUrl}/dashboard?token=${data.token}`;
                window.open(dashboardUrl, '_blank');
            }
        } catch (error) {
            console.error("Dashboard link error:", error);
            addMessage("Sorry, couldn't open the dashboard right now.", 'ai');
        }
    }

    async function onEmailSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const button = form.querySelector('button');
        button.disabled = true;
        setFormError('tyra-email-form', '');
        
        state.userEmail = form.querySelector('input').value.trim();
        const result = await requestOtp(state.userEmail);

        if (result.status === 'success') {
            state.currentView = 'otp_entry';
            render();
        } else {
            setFormError('tyra-email-form', result.message || 'An error occurred.');
            button.disabled = false;
        }
    }
    
    async function onOtpSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const button = form.querySelector('button');
        button.disabled = true;
        setFormError('tyra-otp-form', '');

        const otp = form.querySelector('input').value.trim();
        const { ok, data } = await verifyOtp(state.userEmail, otp);

        if (ok) {
            if (data.status === 'exists') {
                state.jwtToken = data.token;
                state.userName = data.name.split(' ')[0];
                state.currentView = 'chat';
            } else if (data.status === 'new_user_needed') {
                state.verificationToken = data.verification_token;
                state.currentView = 'profile_creation';
            }
            render();
        } else {
            setFormError('tyra-otp-form', data.message || 'Verification failed.');
            button.disabled = false;
        }
    }
    
    async function onProfileSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const button = form.querySelector('button');
        button.disabled = true;
        setFormError('tyra-profile-form', '');
        
        const name = form.querySelector('#tyra-name-input').value.trim();
        const age = form.querySelector('#tyra-age-input').value.trim();
        
        const { ok, data } = await createProfile(name, age);
        
        if (ok && data.status === 'created') {
            state.jwtToken = data.token;
            state.userName = data.name.split(' ')[0];
            state.currentView = 'chat';
            render();
        } else {
            setFormError('tyra-profile-form', data.message || 'Could not create profile.');
            button.disabled = false;
        }
    }
    
    async function onChatSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const input = form.querySelector('input');
        const button = form.querySelector('button');
        
        const messageText = input.value.trim();
        if (!messageText) return;
        
        addMessage(messageText, 'user');
        input.value = '';
        input.disabled = true;
        button.disabled = true;

        const { ok, data } = await sendChatMessage(messageText);

        if (ok) {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = data.reply;
            addMessage(tempDiv.textContent || tempDiv.innerText, 'ai');
        } else {
            addMessage(data.error || 'Sorry, an error occurred.', 'ai');
        }

        input.disabled = false;
        button.disabled = false;
        input.focus();
    }

    function bindEventListeners() {
        const emailForm = state.targetElement.querySelector('#tyra-email-form');
        if (emailForm) emailForm.addEventListener('submit', onEmailSubmit);

        const otpForm = state.targetElement.querySelector('#tyra-otp-form');
        if (otpForm) otpForm.addEventListener('submit', onOtpSubmit);
        
        const profileForm = state.targetElement.querySelector('#tyra-profile-form');
        if (profileForm) profileForm.addEventListener('submit', onProfileSubmit);

        const chatForm = state.targetElement.querySelector('.tyra-chat-form');
        if (chatForm) chatForm.addEventListener('submit', onChatSubmit);
        
        const settingsBtn = state.targetElement.querySelector('.tyra-settings-btn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                const menu = state.targetElement.querySelector('.tyra-settings-menu');
                menu.classList.toggle('visible');
            });
        }
        
        const logoutBtn = state.targetElement.querySelector('#tyra-logout-btn');
        if (logoutBtn) logoutBtn.addEventListener('click', onLogout);
        
        const dashboardBtn = state.targetElement.querySelector('#tyra-dashboard-btn');
        if (dashboardBtn) dashboardBtn.addEventListener('click', onDashboardClick);
    }
    
    // --- INITIALIZATION ---
    window.TyraWidget = {
        init: async function(options) {
            if (!options.targetElementId || !options.apiUrl) {
                return console.error("Tyra Widget: 'targetElementId' and 'apiUrl' are required.");
            }
            state.targetElement = document.getElementById(options.targetElementId);
            state.apiUrl = options.apiUrl.replace(/\/$/, '');

            if (!state.targetElement) {
                return console.error(`Tyra Widget: Target element "#${options.targetElementId}" not found.`);
            }

            state.targetElement.innerHTML = templates.widgetShell;
            
            try {
                const config = await getApiConfig();
                if (config.auth_mode === 'otp') {
                    state.currentView = 'email_entry';
                } else { // Default to guest mode
                    const guestData = await authenticateAsGuest();
                    state.jwtToken = guestData.token;
                    state.currentView = 'chat';
                }
            } catch (error) {
                console.error("Tyra Widget Init Error:", error);
                // Graceful fallback to guest mode if config fails
                try {
                    const guestData = await authenticateAsGuest();
                    state.jwtToken = guestData.token;
                    state.currentView = 'chat';
                } catch (guestError) {
                    state.currentView = 'error'; // A view to show a fatal error
                }
            }
            render();
        }
    };
})();