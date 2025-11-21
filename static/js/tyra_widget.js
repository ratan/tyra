// static/js/tyra_widget.js (v118.3 - Link Quick Logs to Animations)
(function() {
    'use strict';

    // --- STATE MANAGEMENT ---
    let state = {
        apiUrl: '',
        targetElement: null,
        jwtToken: null,
        onboardingToken: null, // NEW in v103.0
        isGuest: false, 
        userEmail: '',
        currentView: 'loading', // loading, email_entry, otp_entry, profile_creation, chat, dashboard
        userName: '',
        lang: {},
        dashboardData: null,
        mediaRecorder: null,
        audioChunks: [],
        childDobs: [], // For profile creation form
        isDashboardStale: false, // FIX v100.2: Flag to signal dashboard needs a refresh
        isSettingsMenuOpen: false, // NEW in v114.0
        streaks: { current: 0 } // NEW in v116.0
    };

    // --- CONSTANTS ---
    // MODIFIED in v111.1: This will be dynamically constructed in init()
    let TYRA_AVATAR_URL = '';
    
    // --- MODIFIED in v118.3: Expanded Easter Egg Keywords for Quick Logs ---
    const EASTER_EGGS = {
        // Positive / Celebration Triggers
        confetti: [
            'congrats', 'yay', 'woo', 'awesome', 'streak', 'slay', 'queen', 'party', 'amazing',
            'good sleep', 'low stress', 'energetic' // Added Quick Log terms
        ],
        // Negative / Comfort Triggers
        comfort: [
            'sad', 'tired', 'cramps', 'pain', 'period', 'stress', 'anxious', 'ugh', 'lonely', 'overwhelmed',
            'poor sleep', 'headache', 'high stress' // Added Quick Log terms
        ]
    };

    // --- TEMPLATES ---
    const templates = {
        // MODIFIED in v111.5: Simplified launcher HTML structure
        launcher: () => `<div class="tyra-launcher">
                            <img src="${TYRA_AVATAR_URL}" alt="Tyra Avatar">
                         </div>`,
        // MODIFIED in v114.0 & v116.0 & v118.2: Added FX Container for animations
        widgetShell: (title) => `
            <div class="tyra-widget-container">
                <div class="tyra-widget-header">
                    <div class="tyra-header-identity">
                        <img src="${TYRA_AVATAR_URL}" alt="Tyra Avatar" class="tyra-header-avatar">
                        <h3 id="tyra-header-title">${title}</h3>
                    </div>
                    <div class="tyra-header-controls">
                        <div id="tyra-streak-indicator" class="tyra-streak-indicator" style="display: none;"></div>
                        <button id="tyra-dashboard-btn" class="tyra-header-button" style="display: none;"></button>
                        <button id="tyra-settings-btn" class="tyra-settings-btn" style="display: none;">⋮</button>
                        <div id="tyra-settings-dropdown" class="tyra-settings-dropdown">
                            <a href="https://fitcommunity.in/privacyPolicy.php" target="_blank" rel="noopener noreferrer">Privacy Policy</a>
                            <a href="#" id="tyra-logout-link">Logout</a>
                        </div>
                        <button id="tyra-close-btn" class="tyra-close-btn">×</button>
                    </div>
                </div>
                <div class="tyra-view-container">
                    <!-- NEW in v118.2: Containers for visual effects -->
                    <div id="tyra-fx-container" class="tyra-fx-container"></div>
                    <div id="tyra-comfort-overlay" class="tyra-comfort-overlay"></div>
                </div>
            </div>`,
        emailEntryView: () => `
            <div class="tyra-form-view">
                <h2>${state.lang.welcome_text || 'Welcome!'}</h2>
                <p>Please enter your email to begin or continue your conversation.</p>
                <form id="tyra-email-form">
                    <label for="tyra-email-input">${state.lang.identifier_email_label || 'Email Address'}</label>
                    <input type="email" id="tyra-email-input" placeholder="you@example.com" required>
                    <div class="tyra-form-error"></div>
                    <button type="submit">${state.lang.button_continue || 'Continue'}</button>
                </form>
                <div class="tyra-or-separator">or</div>
                <button type="button" id="tyra-guest-btn" class="tyra-guest-button">${state.lang.guest_mode_link || 'Continue as a Guest'}</button>
            </div>`,
        otpEntryView: () => `
            <div class="tyra-form-view">
                <h2>Check your email</h2>
                <p>${(state.lang.otp_sent_message || 'We sent a code to {email}.').replace('{email}', `<strong>${state.userEmail}</strong>`)}</p>
                <form id="tyra-otp-form">
                    <label for="tyra-otp-input">${state.lang.otp_label || 'Verification Code'}</label>
                    <input type="text" id="tyra-otp-input" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" required>
                    <div class="tyra-form-error"></div>
                    <button type="submit">${state.lang.button_verify_otp || 'Verify'}</button>
                </form>
            </div>`,
        profileCreationView: () => `
            <div class="tyra-form-view tyra-profile-view">
                <h2>${state.lang.new_user_welcome || 'Create your profile'}</h2>
                <form id="tyra-profile-form">
                    <label for="tyra-name-input">${state.lang.label_name || 'Name'}</label>
                    <input type="text" id="tyra-name-input" required>
                    
                    <label for="tyra-age-input">${state.lang.label_age || 'Age'}</label>
                    <input type="number" id="tyra-age-input" min="13" max="100" required>

                    <label for="tyra-language-select">${state.lang.label_language || 'Language'}</label>
                    <select id="tyra-language-select">
                        <option value="en" selected>English</option><option value="bn">বাংলা (Bengali)</option><option value="gu">ગુજરાતી (Gujarati)</option><option value="hi">हिन्दी (Hindi)</option><option value="kn">ಕನ್ನಡ (Kannada)</option><option value="ml">മലയാളം (Malayalam)</option><option value="mr">मराठी (Marathi)</option><option value="or">ଓଡ଼ିଆ (Odia)</option><option value="pa">ਪੰਜਾਬੀ (Punjabi)</option><option value="ta">தமிழ் (Tamil)</option><option value="te">తెలుగు (Telugu)</option><option value="ur">اردو (Urdu)</option><option value="ar">العربية (Arabic)</option>
                    </select>

                    <fieldset id="tyra-adult-profile-section" class="hidden"><legend>Key Life Events</legend>
                        <div class="tyra-checkbox-group"><input type="checkbox" id="cb-ttc" value="is_trying_to_conceive"><label for="cb-ttc">Trying to conceive</label></div>
                        <div class="tyra-sub-group hidden"><label>For how many months?</label><input type="number" id="months_trying"></div>
                        
                        <div class="tyra-checkbox-group"><input type="checkbox" id="cb-pregnant" value="is_pregnant"><label for="cb-pregnant">Currently pregnant</label></div>
                        <div class="tyra-sub-group hidden"><label>Last Menstrual Period (LMP)</label><input type="date" id="lmp_date"></div>

                        <div class="tyra-checkbox-group"><input type="checkbox" id="cb-parent" value="is_parent"><label for="cb-parent">Parenting / Have Children</label></div>
                        <div class="tyra-sub-group hidden"><label>Child's Date of Birth</label><input type="date" id="child_dob_input"><button type="button" id="add-child-btn">Add</button><div id="added-dobs-display"></div></div>
                    </fieldset>
    
                    <fieldset id="tyra-menopause-profile-section" class="hidden"><legend>Menopause Status</legend>
                        <div class="tyra-checkbox-group"><input type="checkbox" id="cb-peri" value="is_perimenopausal"><label for="cb-peri">Perimenopause symptoms</label></div>
                        <div class="tyra-checkbox-group"><input type="checkbox" id="cb-meno" value="is_menopausal"><label for="cb-meno">In menopause or postmenopausal</label></div>
                    </fieldset>
                    
                    <div class="tyra-form-error"></div>
                    <button type="submit">${state.lang.button_start_chatting || 'Start Chatting'}</button>
                </form>
            </div>`,
        chatView: () => `
            <div class="tyra-chat-log"></div>
            <div class="tyra-chat-form-container">
                 <div class="tyra-quick-log-buttons"></div>
                 <form class="tyra-chat-form">
                    <label for="tyra-file-input" class="tyra-icon-button" title="Upload file">📎</label>
                    <input type="file" id="tyra-file-input" style="display:none;" accept=".pdf,image/*">
                    <input type="text" class="tyra-chat-input" placeholder="${state.lang.ask_question_placeholder || 'Ask a question...'}" autocomplete="off" required>
                    <button type="button" class="tyra-icon-button tyra-voice-btn" title="Record voice">🎤</button>
                    <button type="submit" class="tyra-send-button" aria-label="Send">➤</button>
                </form>
            </div>`,
        dashboardView: () => `<div class="tyra-dashboard-view"></div>`,
        calendar: (data) => {
            const { year, month, month_name, predicted_days, logged_days, fertile_days, current_day } = data;
            let date = new Date(year, month - 1, 1);
            let firstDay = date.getDay();
            let daysInMonth = new Date(year, month, 0).getDate();
            
            let tableHtml = `<h3>${month_name} ${year}</h3><table class="tyra-calendar-table"><thead><tr>`;
            ['S', 'M', 'T', 'W', 'T', 'F', 'S'].forEach(day => { tableHtml += `<th>${day}</th>`; });
            tableHtml += `</tr></thead><tbody><tr>`;
            for (let i = 0; i < firstDay; i++) { tableHtml += `<td></td>`; }
            for (let day = 1; day <= daysInMonth; day++) {
                if ((day + firstDay - 1) % 7 === 0 && day > 1) { tableHtml += `</tr><tr>`; }
                let classes = ['tyra-calendar-day'];
                if (logged_days.includes(day)) { classes.push('logged-day'); } 
                else if (fertile_days && fertile_days.includes(day)) { classes.push('fertile-day'); } 
                else if (predicted_days.includes(day)) { classes.push('predicted-day'); }
                if (day === current_day) { classes.push('current-day'); }
                tableHtml += `<td><span class="${classes.join(' ')}">${day}</span></td>`;
            }
            while ((daysInMonth + firstDay) % 7 !== 0) { tableHtml += `<td></td>`; daysInMonth++; }
            tableHtml += `</tr></tbody></table>`;
    
            let legendHtml = '<div class="tyra-calendar-legend">';
            legendHtml += '<div class="legend-item"><span class="legend-color" style="background-color: var(--logged-day-bg);"></span>Logged</div>';
            legendHtml += '<div class="legend-item"><span class="legend-color" style="background-color: var(--predicted-day-bg);"></span>Predicted</div>';
            legendHtml += '<div class="legend-item"><span class="legend-color" style="background-color: var(--fertile-day-bg);"></span>Fertile</div>';
            legendHtml += '</div>';
    
            return tableHtml + legendHtml;
        }
    };

    // --- NEW in v118.2: Animation Logic Functions ---
    function checkAndTriggerEasterEgg(text) {
        if (!text) return;
        const lower = text.toLowerCase();
        
        if (EASTER_EGGS.confetti.some(k => lower.includes(k))) {
            triggerConfetti();
        } else if (EASTER_EGGS.comfort.some(k => lower.includes(k))) {
            triggerComfortMode();
        }
    }

    function triggerConfetti() {
        const container = state.targetElement.querySelector('#tyra-fx-container');
        if (!container) return;

        const colors = ['#8B4A9C', '#E6A4E6', '#FFD700', '#FF69B4', '#87CEEB'];
        
        for (let i = 0; i < 25; i++) {
            const particle = document.createElement('div');
            particle.classList.add('tyra-confetti');
            particle.style.left = Math.random() * 100 + '%';
            particle.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            // Randomize animation duration for natural feel
            particle.style.animationDuration = (Math.random() * 1.5 + 1.5) + 's';
            
            container.appendChild(particle);
            
            // Clean up
            setTimeout(() => {
                if (container.contains(particle)) container.removeChild(particle);
            }, 3000);
        }
    }

    function triggerComfortMode() {
        const overlay = state.targetElement.querySelector('#tyra-comfort-overlay');
        if (!overlay) return;
        
        overlay.classList.add('active');
        setTimeout(() => {
            overlay.classList.remove('active');
        }, 4000); // Hold glow for 4 seconds then fade out
    }
    // --- End v118.2 Logic ---


    // --- RENDER & DOM FUNCTIONS ---
    function render() {
        const viewContainer = state.targetElement.querySelector('.tyra-view-container');
        if (!viewContainer) return; // The shell might not be rendered yet
        
        // MODIFIED in v114.0 & v116.0: Select new header elements
        const headerTitle = state.targetElement.querySelector('#tyra-header-title');
        const dashboardButton = state.targetElement.querySelector('#tyra-dashboard-btn');
        const settingsButton = state.targetElement.querySelector('#tyra-settings-btn');
        const headerIdentity = state.targetElement.querySelector('.tyra-header-identity');
        const streakIndicator = state.targetElement.querySelector('#tyra-streak-indicator');

        if (!headerTitle || !dashboardButton || !settingsButton || !headerIdentity || !streakIndicator) return;

        let viewHTML = '';
        dashboardButton.style.display = 'none';
        settingsButton.style.display = 'none';
        streakIndicator.style.display = 'none'; // Hide by default
        headerIdentity.style.visibility = 'visible'; 

        switch (state.currentView) {
            case 'email_entry': 
                viewHTML = templates.emailEntryView(); 
                headerIdentity.style.visibility = 'hidden'; 
                break;
            case 'otp_entry': 
                viewHTML = templates.otpEntryView(); 
                headerIdentity.style.visibility = 'hidden';
                break;
            case 'profile_creation': 
                viewHTML = templates.profileCreationView(); 
                headerIdentity.style.visibility = 'hidden';
                break;
            case 'chat':
                viewHTML = templates.chatView();
                headerTitle.textContent = state.lang.app_title || 'Tyra';
                if (state.jwtToken || state.onboardingToken) {
                    settingsButton.style.display = 'block';
                    if (!state.isGuest && !state.onboardingToken) {
                        dashboardButton.textContent = state.lang.dashboard_link || 'Dashboard';
                        dashboardButton.style.display = 'block';
                        // NEW in v116.0: Show streak indicator
                        if (state.streaks && state.streaks.current > 0) {
                            streakIndicator.innerHTML = `🔥 ${state.streaks.current}`;
                            streakIndicator.style.display = 'flex';
                        }
                    }
                }
                break;
            case 'dashboard':
                viewHTML = templates.dashboardView();
                headerTitle.textContent = `${state.userName}'s Dashboard`;
                dashboardButton.textContent = state.lang.back_to_chat_link || 'Back to Chat';
                settingsButton.style.display = 'block';
                dashboardButton.style.display = 'block';
                break;
            default: viewHTML = '<p style="text-align:center;padding:20px;">Loading...</p>';
        }
        
        // MODIFIED in v118.2: Append view HTML but preserve the fixed overlay containers
        viewContainer.innerHTML = viewHTML;
        
        // Re-inject FX containers if they were wiped by innerHTML (surgical fix)
        if (!viewContainer.querySelector('#tyra-fx-container')) {
             const fxDiv = document.createElement('div'); fxDiv.id = 'tyra-fx-container'; fxDiv.className = 'tyra-fx-container';
             const comfortDiv = document.createElement('div'); comfortDiv.id = 'tyra-comfort-overlay'; comfortDiv.className = 'tyra-comfort-overlay';
             viewContainer.appendChild(fxDiv);
             viewContainer.appendChild(comfortDiv);
        }

        bindEventListeners();
        postRenderSetup();
    }
    
    // MODIFIED in v110.3 to prevent race condition
    function postRenderSetup() {
        if (state.currentView === 'chat') {
            // Only load history if we are NOT in the middle of onboarding.
            if (!state.onboardingToken) {
                loadChatHistory();
            }
            populateQuickLogButtons();
        } else if (state.currentView === 'dashboard') {
            renderDashboard();
        } else if (state.currentView === 'profile_creation') {
            initializeProfileFormLogic();
        }
    }
    
    // MODIFIED in v117.4: Handle weekly insight card and robust download
    function addMessage(htmlContent, sender, responseData = {}, doAutoScroll = true) {
        const chatLog = state.targetElement.querySelector('.tyra-chat-log');
        if (!chatLog) return;
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('tyra-message', `tyra-${sender}-message`);
        
        const uiComponent = responseData.ui_component;
        
        if (sender === 'user') {
            // User messages are always simple text
            const p = document.createElement('p');
            p.textContent = htmlContent;
            messageDiv.appendChild(p);
        } else {
            // AI messages can be complex
            const mainText = document.createElement('div');
            mainText.innerHTML = htmlContent;
            messageDiv.appendChild(mainText);
            
            if (uiComponent === 'language_picker') {
                const pickerContainer = document.createElement('div');
                pickerContainer.className = 'tyra-language-picker-container';
                const select = document.createElement('select');
                const languages = { "en": "English", "hi": "हिन्दी (Hindi)", "bn": "বাংলা (Bengali)", "te": "తెలుగు (Telugu)", "mr": "मराठी (Marathi)", "ta": "தமிழ் (Tamil)", "gu": "ગુજરાતી (Gujarati)", "ur": "اردو (Urdu)", "kn": "ಕನ್ನಡ (Kannada)", "or": "ଓଡ଼ିଆ (Odia)", "ml": "മലയാളം (Malayalam)", "pa": "ਪੰਜਾਬੀ (Punjabi)", "ar": "العربية (Arabic)" };
                let optionsHtml = `<option value="">${state.lang.onboarding_language_select_placeholder || 'Select your language...'}</option>`;
                for (const [code, name] of Object.entries(languages)) {
                    optionsHtml += `<option value="${code}">${name}</option>`;
                }
                select.innerHTML = optionsHtml;
                select.addEventListener('change', (e) => {
                    if (e.target.value) {
                         onChatSubmit({ preventDefault: () => {} }, { message: e.target.value });
                        e.target.disabled = true;
                    }
                });
                pickerContainer.appendChild(select);
                messageDiv.appendChild(pickerContainer);
            }
            else if (['bar', 'line'].includes(responseData.chart_type)) {
                messageDiv.classList.add('tyra-chart-container');
                const canvas = document.createElement('canvas');
                messageDiv.innerHTML = ''; // Clear the text content
                messageDiv.appendChild(canvas);
                new Chart(canvas.getContext('2d'), responseData);
            } else if (responseData.chart_type === 'calendar') {
                 messageDiv.classList.add('tyra-calendar-container');
                 messageDiv.innerHTML = templates.calendar(responseData.data);
            }
            else if (uiComponent === 'category_picker') {
                const pickerContainer = document.createElement('div');
                pickerContainer.className = 'tyra-category-picker';
                responseData.data.categories.forEach(cat => {
                    const button = document.createElement('button');
                    button.textContent = `${cat.name} (${cat.count} videos)`;
                    button.dataset.category = cat.name.toLowerCase();
                    button.addEventListener('click', () => {
                        onChatSubmit({ preventDefault: () => {} }, { action: 'select_video_category', category: cat.name.toLowerCase() });
                        pickerContainer.innerHTML = ''; // Hide buttons after click
                    });
                    pickerContainer.appendChild(button);
                });
                messageDiv.appendChild(pickerContainer);
            } else if (uiComponent === 'video_carousel') {
                const carousel = document.createElement('div');
                carousel.className = 'tyra-video-carousel-container';
                responseData.data.videos.forEach(video => {
                    const card = document.createElement('div');
                    card.className = 'tyra-video-card';
                    card.innerHTML = `<img src="${video.youtube_thumbnail_url}" alt="Thumbnail for ${video.title}"><div class="tyra-video-card-title">${video.title}</div>`;
                    card.addEventListener('click', () => {
                        const safetyDisclaimer = "Of course! Here is a video that might be helpful. **Please remember to consult with your doctor before starting any new exercise routine.**";
                        const videoReply = `${safetyDisclaimer}\n\n**${video.title}**: ${video.description}`;
                        addMessage(videoReply, 'ai', { video_embed: { type: 'youtube', video_id: video.youtube_video_id }});
                    });
                    carousel.appendChild(card);
                });
                messageDiv.appendChild(carousel);
            }
            else if (responseData.video_embed && responseData.video_embed.type === 'youtube') {
                const videoContainer = document.createElement('div');
                videoContainer.className = 'tyra-video-container';
                const iframe = document.createElement('iframe');
                iframe.src = `https://www.youtube.com/embed/${responseData.video_embed.video_id}`;
                iframe.frameBorder = '0';
                iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
                iframe.allowFullscreen = true;
                videoContainer.appendChild(iframe);
                messageDiv.appendChild(videoContainer);
            }
            else if (uiComponent === 'weekly_insight_card') {
                const card = document.createElement('div');
                card.className = 'tyra-insight-card';
                card.innerHTML = `
                    <img src="${state.apiUrl}${responseData.data.image_url}" alt="Your weekly insight">
                    <button class="tyra-download-insight-btn">Download Image</button>
                `;
                // BUGFIX in v117.4: Implement robust download for cross-origin images
                card.querySelector('button').addEventListener('click', async (e) => {
                    const btn = e.target;
                    btn.textContent = 'Downloading...';
                    btn.disabled = true;
                    try {
                        const imageUrl = `${state.apiUrl}${responseData.data.image_url}`;
                        const response = await fetch(imageUrl);
                        const blob = await response.blob();
                        const objectUrl = URL.createObjectURL(blob);
                        
                        const link = document.createElement('a');
                        link.href = objectUrl;
                        link.download = `tyra-weekly-insight.png`;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        
                        URL.revokeObjectURL(objectUrl);
                    } catch (err) {
                        console.error("Download failed:", err);
                        btn.textContent = 'Download Failed';
                    } finally {
                        setTimeout(() => {
                            btn.textContent = 'Download Image';
                            btn.disabled = false;
                        }, 2000);
                    }
                });
                messageDiv.appendChild(card);
            }
        }
        
        chatLog.appendChild(messageDiv);
        if (doAutoScroll) {
            chatLog.scrollTop = chatLog.scrollHeight;
        }
        return messageDiv;
    }

    // NEW in v108.0: Smart scroll function
    function smartScroll(userMessageElement, aiMessageElement) {
        const chatLog = state.targetElement.querySelector('.tyra-chat-log');
        if (!chatLog) return;
        
        if (!userMessageElement || !aiMessageElement) {
            chatLog.scrollTop = chatLog.scrollHeight; // Fallback to simple scroll
            return;
        }

        const containerHeight = chatLog.clientHeight;
        const lastTwoMessagesHeight = userMessageElement.offsetHeight + aiMessageElement.offsetHeight + 20; // Add gap

        if (lastTwoMessagesHeight > containerHeight) {
            // If they don't fit, scroll to the top of the user's message
            userMessageElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            // If they fit, scroll to the bottom to ensure everything is visible
            chatLog.scrollTop = chatLog.scrollHeight;
        }
    }

    function setFormError(formId, message) {
        const errorDiv = state.targetElement.querySelector(`#${formId} .tyra-form-error`);
        if (errorDiv) errorDiv.textContent = message;
    }

    // --- API & DATA HANDLING ---
    const api = {
        async get(endpoint, params = {}, isBlob = false) {
            const token = state.jwtToken;
            const headers = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            const url = new URL(`${state.apiUrl}/api/v1/${endpoint}`);
            url.search = new URLSearchParams(params).toString();

            const response = await fetch(url, { headers });
            if (!response.ok) throw new Error(`API GET ${endpoint} failed with status ${response.status}`);
            return isBlob ? response.blob() : response.json();
        },
        async post(endpoint, body, isFormData = false) {
            const token = endpoint.startsWith('auth/onboard') ? state.onboardingToken : state.jwtToken;
            const headers = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            if (!isFormData) headers['Content-Type'] = 'application/json';
            
            const response = await fetch(`${state.apiUrl}/api/v1/${endpoint}`, {
                method: 'POST',
                headers,
                body: isFormData ? body : JSON.stringify(body)
            });
            return { ok: response.ok, data: await response.json() };
        },
        async initialConfig() {
            const response = await fetch(`${state.apiUrl}/api/v1/config/initial`);
            if (!response.ok) throw new Error('Could not fetch initial config');
            return response.json();
        },
        async guestAuth() {
            const response = await fetch(`${state.apiUrl}/api/v1/auth/guest`, { method: 'POST' });
            if (!response.ok) throw new Error('Guest auth failed');
            return response.json();
        },
        async verifyOtp(email, otp) {
            const { ok, data } = await fetch(`${state.apiUrl}/api/v1/auth/verify_otp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, otp })
            }).then(async res => ({ ok: res.ok, data: await res.json() }));
            return { ok, data };
        },
        async createProfile(payload) {
            // DEPRECATED in v103.0 for conversational onboarding
            const headers = {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.verificationToken}` // This token no longer exists in new flow
            };
            const response = await fetch(`${state.apiUrl}/api/v1/auth/create_profile`, {
                method: 'POST', headers, body: JSON.stringify(payload)
            });
            return { ok: response.ok, data: await response.json() };
        }
    };

    // --- EVENT HANDLERS & LOGIC ---
    function bindEventListeners() {
        // MODIFIED in v114.0: Bind to new/changed header buttons
        const dashboardButton = state.targetElement.querySelector('#tyra-dashboard-btn');
        if (dashboardButton) dashboardButton.addEventListener('click', onNavButtonClick);

        const settingsButton = state.targetElement.querySelector('#tyra-settings-btn');
        if (settingsButton) settingsButton.addEventListener('click', onSettingsClick);
        
        const logoutLink = state.targetElement.querySelector('#tyra-logout-link');
        if (logoutLink) logoutLink.addEventListener('click', onLogout);
        
        const emailForm = state.targetElement.querySelector('#tyra-email-form');
        if (emailForm) emailForm.addEventListener('submit', onEmailSubmit);
        
        const guestBtn = state.targetElement.querySelector('#tyra-guest-btn');
        if (guestBtn) guestBtn.addEventListener('click', onGuestButtonClick);

        const otpForm = state.targetElement.querySelector('#tyra-otp-form');
        if (otpForm) otpForm.addEventListener('submit', onOtpSubmit);
        
        const profileForm = state.targetElement.querySelector('#tyra-profile-form');
        if (profileForm) profileForm.addEventListener('submit', onProfileSubmit);

        const chatForm = state.targetElement.querySelector('.tyra-chat-form');
        if (chatForm) chatForm.addEventListener('submit', onChatSubmit);

        const fileInput = state.targetElement.querySelector('#tyra-file-input');
        if (fileInput) fileInput.addEventListener('change', onFileSelect);

        const voiceBtn = state.targetElement.querySelector('.tyra-voice-btn');
        if (voiceBtn) voiceBtn.addEventListener('click', onVoiceButtonClick);

        const quickLogContainer = state.targetElement.querySelector('.tyra-quick-log-buttons');
        if (quickLogContainer) quickLogContainer.addEventListener('click', onQuickLogClick);
        
        const dashboardContainer = state.targetElement.querySelector('.tyra-dashboard-view');
        if(dashboardContainer) {
            dashboardContainer.addEventListener('click', onDashboardActionClick);
        }
    }
    
    function onNavButtonClick() {
        if (state.currentView === 'chat') {
            state.currentView = 'dashboard';
        } else if (state.currentView === 'dashboard') {
            state.currentView = 'chat';
        }
        render();
    }
    
    // MODIFIED in v114.0
    function onLogout(e) {
        if (e) e.preventDefault();
        toggleSettingsMenu(false); // Close menu if it's open
        state.jwtToken = null;
        state.onboardingToken = null;
        state.userName = '';
        state.isGuest = false;
        state.dashboardData = null;
        state.userEmail = '';
        state.currentView = 'email_entry'; // Go back to the start
        state.streaks = { current: 0 }; // NEW in v116.0: Reset streaks on logout
        render();
    }

    // --- NEW in v114.0: Settings Menu Logic ---
    function onSettingsClick() {
        toggleSettingsMenu();
    }

    function toggleSettingsMenu(forceState) {
        const dropdown = state.targetElement.querySelector('#tyra-settings-dropdown');
        if (!dropdown) return;
        
        state.isSettingsMenuOpen = typeof forceState === 'boolean' ? forceState : !state.isSettingsMenuOpen;
        dropdown.style.display = state.isSettingsMenuOpen ? 'block' : 'none';

        // Add a listener to close the menu if clicking outside of it
        if (state.isSettingsMenuOpen) {
            document.addEventListener('click', handleOutsideClick, true);
        } else {
            document.removeEventListener('click', handleOutsideClick, true);
        }
    }

    function handleOutsideClick(event) {
        const controls = state.targetElement.querySelector('.tyra-header-controls');
        if (controls && !controls.contains(event.target)) {
            toggleSettingsMenu(false);
        }
    }
    // --- End v114.0 Logic ---

    async function onEmailSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const button = form.querySelector('button');
        button.disabled = true;
        setFormError('tyra-email-form', '');
        
        state.userEmail = form.querySelector('input').value.trim();
        const { ok, data } = await fetch(`${state.apiUrl}/api/v1/auth/request_otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: state.userEmail })
        }).then(async res => ({ ok: res.ok, data: await res.json() }));

        if (ok) {
            state.currentView = 'otp_entry';
            render();
        } else {
            setFormError('tyra-email-form', data.message || 'An error occurred.');
            button.disabled = false;
        }
    }
    
    async function onGuestButtonClick(e) {
        e.target.disabled = true;
        try {
            const guestData = await api.guestAuth();
            state.jwtToken = guestData.token;
            state.isGuest = guestData.is_guest;
            state.currentView = 'chat';
            await initializeAuthenticatedSession();
        } catch (error) {
            e.target.disabled = false;
            setFormError('tyra-email-form', 'Guest mode failed. Please try again.');
        }
    }
    
    async function onOtpSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const button = form.querySelector('button');
        button.disabled = true;
        setFormError('tyra-otp-form', '');

        const otp = form.querySelector('input').value.trim();
        const { ok, data } = await api.verifyOtp(state.userEmail, otp);

        if (ok) {
            state.isGuest = data.is_guest;
            if (data.status === 'exists') {
                state.jwtToken = data.token;
                state.userName = data.name.split(' ')[0];
                state.currentView = 'chat';
                await initializeAuthenticatedSession();
            } else if (data.status === 'onboarding_started') { // NEW in v103.0
                state.onboardingToken = data.onboarding_token;
                state.currentView = 'chat';
                render(); // Render the chat view
                addMessage(data.reply, 'ai', data); // Display the first onboarding question
            } else if (data.status === 'new_user_needed') { // Fallback for v102.1
                state.verificationToken = data.verification_token;
                state.currentView = 'profile_creation';
                render();
            }
        } else {
            setFormError('tyra-otp-form', data.message || 'Verification failed.');
            button.disabled = false;
        }
    }
    
    async function onProfileSubmit(e) { // Only used if conversational onboarding is OFF
        e.preventDefault();
        // ... (This function is now legacy and will not be triggered in the v117.0 default flow)
    }
    
    // MODIFIED in v108.0 for smart scroll
    async function onChatSubmit(e, internalAction = null) {
        e.preventDefault();
        
        let messagePayload = {};
        let userMessageToDisplay = '';
        const input = state.targetElement.querySelector('.tyra-chat-input');
        let userMessageElement = null;

        if (internalAction) {
            messagePayload = internalAction;
        } else {
            const messageText = input.value.trim();
            if (!messageText) return;
            
            // NEW in v118.2: Check and trigger animations instantly
            checkAndTriggerEasterEgg(messageText);
            
            messagePayload = { message: messageText };
            userMessageToDisplay = messageText;
        }
        
        if (userMessageToDisplay) {
            userMessageElement = addMessage(userMessageToDisplay, 'user', {}, false);
        }
        if (input) {
            input.value = '';
            input.disabled = true;
        }

        let responseData;
        const endpoint = state.onboardingToken ? 'auth/onboard/step' : 'chat';
        const { ok, data } = await api.post(endpoint, messagePayload);

        if (ok) {
            responseData = data;
            if (data.status === 'onboarding_inprogress') {
                state.onboardingToken = data.onboarding_token;
            } else if (data.status === 'created') {
                state.onboardingToken = null;
                state.jwtToken = data.token;
                state.userName = data.name.split(' ')[0];
                state.isGuest = false;
                await initializeAuthenticatedSession();
            } else if (!state.onboardingToken) {
                state.isDashboardStale = true;
            }
        } else {
            responseData = { reply: data.error || 'Sorry, an error occurred.' };
        }

        if (responseData) {
            if (responseData.proactive_summary) {
                addMessage(responseData.proactive_summary, 'ai');
            }
            const aiMessageElement = addMessage(responseData.reply || '', 'ai', responseData, false);
            smartScroll(userMessageElement, aiMessageElement);
        }

        if (input) {
            input.disabled = false;
            input.focus();
        }
    }


    async function onFileSelect(e) {
        if (state.isGuest || state.onboardingToken) { // MODIFIED v103.0
            addMessage("This feature is available after setup is complete. Please finish creating your profile first.", "ai", {});
            return;
        }
        const file = e.target.files[0];
        if (!file) return;

        addMessage(`Uploading ${file.name}...`, 'user', {});
        const formData = new FormData();
        formData.append('file', file);
        
        const { ok, data } = await api.post('upload', formData, true);
        if (ok) {
            addMessage(data.reply, 'ai', data);
        } else {
            addMessage(data.error || 'File processing failed.', 'ai', data);
        }
    }

    function onVoiceButtonClick(e) {
        if (state.isGuest || state.onboardingToken) { // MODIFIED v103.0
             addMessage("This feature is available after setup is complete. Please finish creating your profile first.", "ai", {});
            return;
        }
        const btn = e.target.closest('button');
        if (state.mediaRecorder && state.mediaRecorder.state === 'recording') {
            state.mediaRecorder.stop();
            btn.classList.remove('recording');
        } else {
            navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
                state.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
                state.audioChunks = [];
                state.mediaRecorder.ondataavailable = event => state.audioChunks.push(event.data);
                state.mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(state.audioChunks, { type: 'audio/webm' });
                    if (audioBlob.size > 500) {
                        const formData = new FormData();
                        formData.append('audio_file', audioBlob);
                        const { ok, data } = await api.post('transcribe', formData, true);
                        if (ok) state.targetElement.querySelector('.tyra-chat-input').value = data.transcribed_text;
                    }
                    stream.getTracks().forEach(track => track.stop());
                };
                state.mediaRecorder.start();
                btn.classList.add('recording');
            }).catch(err => console.error("Mic access error:", err));
        }
    }

    async function onQuickLogClick(e) {
        const button = e.target.closest('.tyra-quick-log-btn');
        if (!button) return;
        if (state.onboardingToken) return; // Don't allow during onboarding
        const { logCategory, logValue, logLabel } = button.dataset;

        state.isDashboardStale = true;

        // --- NEW in v118.3: Trigger animation on button click ---
        // We pass the log label (e.g., "😴 Good Sleep") to the checker, 
        // which now includes these phrases in its list.
        checkAndTriggerEasterEgg(logLabel);
        // --------------------------------------------------------

        const userMsgEl = addMessage(logLabel, 'user', {}, false);
        const { ok, data } = await api.post('quick_log', { category: logCategory, value: logValue });
        if (ok) {
            const aiMsgEl = addMessage(data.reply, 'ai', data, false);
            smartScroll(userMsgEl, aiMsgEl);
        }
    }

    // NEW in v108.0: Load and render chat history.
    async function loadChatHistory() {
        if (state.isGuest) {
            addMessage(state.lang.welcome_message_guest, 'ai');
            return;
        }
        try {
            const history = await api.get('chat_history');
            const chatLog = state.targetElement.querySelector('.tyra-chat-log');
            if (history && history.length > 0) {
                chatLog.innerHTML = ''; // Clear any existing messages
                history.forEach(item => {
                    addMessage(item.content, item.role, {}, false);
                });
                chatLog.scrollTop = chatLog.scrollHeight; // Scroll to bottom after load
            } else {
                const welcomeMessage = (state.lang.welcome_message_return || 'Welcome back, {name}!').replace('{name}', state.userName);
                addMessage(welcomeMessage, 'ai', {});
            }
        } catch(e) {
             console.error('Failed to load chat history:', e);
             const welcomeMessage = (state.lang.welcome_message_return || 'Welcome back, {name}!').replace('{name}', state.userName);
             addMessage(welcomeMessage, 'ai', {});
        }
    }

    // MODIFIED in v116.0: Fetch and store streak data
    async function initializeAuthenticatedSession() {
        try {
            const config = await api.get('config');
            state.lang = config.lang || {};
            if(config.streaks) {
                state.streaks = config.streaks;
            }
            render();
        } catch (e) {
            console.error("Failed to load config for authenticated user:", e);
            render(); 
        }
    }
    
    function initializeProfileFormLogic() {
        const form = state.targetElement.querySelector('#tyra-profile-form');
        if (!form) return;
        const ageInput = form.querySelector('#tyra-age-input');
        const adultSection = form.querySelector('#tyra-adult-profile-section');
        const menopauseSection = form.querySelector('#tyra-menopause-profile-section');
        ageInput.addEventListener('input', () => {
            const age = parseInt(ageInput.value, 10) || 0;
            adultSection.classList.toggle('hidden', age < 20 || age > 50);
            menopauseSection.classList.toggle('hidden', age < 40);
        });
        form.querySelectorAll('.tyra-checkbox-group input').forEach(cb => {
            cb.addEventListener('change', e => {
                const subGroup = e.target.closest('.tyra-checkbox-group').nextElementSibling;
                if (subGroup && subGroup.classList.contains('tyra-sub-group')) {
                    subGroup.classList.toggle('hidden', !e.target.checked);
                }
            });
        });
        const addChildBtn = form.querySelector('#add-child-btn');
        addChildBtn.addEventListener('click', () => {
            const dobInput = form.querySelector('#child_dob_input');
            if (dobInput.value) {
                state.childDobs.push(dobInput.value);
                form.querySelector('#added-dobs-display').textContent = `Added: ${state.childDobs.join(', ')}`;
                dobInput.value = '';
            }
        });
    }

    function populateQuickLogButtons() {
        if (state.isGuest || state.onboardingToken) return; // MODIFIED v103.0
        const container = state.targetElement.querySelector('.tyra-quick-log-buttons');
        if (!container || !state.lang.quick_log_buttons) return;
        container.innerHTML = (state.lang.quick_log_buttons || []).map(item =>
            `<button class="tyra-quick-log-btn" data-log-category="${item.category}" data-log-value="${item.value}" data-log-label="${item.label}">${item.label}</button>`
        ).join('');
    }

    async function renderChartInChat(chartType, targetDate) {
        if (state.isGuest || state.onboardingToken) return; // MODIFIED v103.0
        const params = { type: chartType };
        if (targetDate) params.target_date = targetDate;
        try {
            const config = await api.get('chart_data', params);
            if(config.type) {
                addMessage('', 'ai', { ...config, chart_type: config.type });
            }
        } catch (e) {
            addMessage('Could not load visualization.', 'ai');
        }
    }
    
    // --- DASHBOARD-SPECIFIC RENDERING ---
    async function renderDashboard() {
        const container = state.targetElement.querySelector('.tyra-dashboard-view');
        container.innerHTML = '<p>Loading dashboard...</p>';
        try {
            if (state.isDashboardStale || !state.dashboardData) {
                state.dashboardData = await api.get('dashboard_data');
                state.isDashboardStale = false;
            }
            const data = state.dashboardData;
            
            const widgets = {
                cycle: () => {
                    if (!data.cycle_stats || Object.keys(data.cycle_stats).length === 0) return '';
                    let w = `<div class="tyra-widget tyra-cycle-stats"><h4>${state.lang.widget_title_cycle || 'Cycle'}</h4>`;
                    if(data.cycle_stats.current_day) w += `<p>${(state.lang.cycle_current_day_p1 || "You are on")} <span class="stat-value">${(state.lang.cycle_day_N || "Day {day}").replace("{day}", data.cycle_stats.current_day)}</span></p>`;
                    if(data.cycle_stats.predicted_next) w += `<p>${state.lang.cycle_predicted_next || 'Next Period'}: <strong>${data.cycle_stats.predicted_next}</strong></p>`;
                    if(data.cycle_stats.avg_cycle_length) w += `<p>${state.lang.cycle_avg_length || 'Avg. Length'}: <strong>${data.cycle_stats.avg_cycle_length} days</strong></p>`;
                    return w + '</div>';
                },
                reminders: () => {
                    let w = `<div class="tyra-widget"><h4>${state.lang.widget_title_reminders || 'Reminders'}</h4><ul>`;
                    (data.reminders.length > 0 ? data.reminders : [{text: state.lang.no_reminders_text || 'No reminders.'}]).forEach(r => {
                        w += `<li class="tyra-reminder-item"><span><strong>${r.text}</strong><br><small>${r.id ? new Date(r.date).toDateString() : ''}</small></span>${r.id ? `<button data-id="${r.id}">✓</button>` : ''}</li>`;
                    });
                    return w + '</ul></div>';
                },
                meds: () => {
                    let w = `<div class="tyra-widget"><h4>${state.lang.widget_title_meds || 'Medications'}</h4><ul>`;
                    (data.medications.length > 0 ? data.medications : [{name: state.lang.no_meds_logged || 'No medications logged.'}]).forEach(m => {
                        w += `<li><strong>${m.name}</strong>${m.dosage ? `<span class="meds-details">${m.dosage}, ${m.frequency}</span>` : ''}</li>`;
                    });
                    return w + '</ul></div>';
                },
                goals: () => {
                    let w = `<div class="tyra-widget"><h4>${state.lang.widget_title_goals || 'Goals'}</h4><ul>`;
                    (data.goals.length > 0 ? data.goals : [{text: state.lang.no_goals_set || 'No goals set.'}]).forEach(g => { w += `<li>${g.text}</li>`; });
                    return w + '</ul></div>';
                },
                logs: () => {
                    let w = `<div class="tyra-widget"><h4>${state.lang.widget_title_health_logs || 'Recent Logs'}</h4><ul>`;
                    (data.health_logs.length > 0 ? data.health_logs : [{text: state.lang.no_logs_text || 'No logs recorded.'}]).forEach(l => { w += `<li>${l.text}</li>`; });
                    return w + '</ul></div>';
                },
                charts: () => `
                    <div class="tyra-widget tyra-chart-widget"><h4>${state.lang.widget_title_cycle_history || 'Cycle History'}</h4><canvas id="tyra-cycle-chart"></canvas></div>
                    <div class="tyra-widget tyra-chart-widget"><h4>${state.lang.widget_title_interaction || 'Interaction History'}</h4><canvas id="tyra-interaction-chart"></canvas></div>
                `,
                export: () => `
                    <div class="tyra-widget tyra-export-widget">
                        <h4>${state.lang.widget_title_export || 'Export & Share'}</h4>
                        <p>${state.lang.export_description || 'Download or share your health report.'}</p>
                        <div class="tyra-export-buttons">
                            <button data-action="export-pdf">${state.lang.export_pdf_button || 'Download PDF'}</button>
                            <button data-action="export-csv">${state.lang.export_csv_button || 'Download CSV'}</button>
                            <button data-action="share">${state.lang.share_report_button || 'Get Share Link'}</button>
                        </div>
                        <div class="tyra-share-link-container hidden">
                            <input type="text" readonly>
                            <button data-action="copy">${state.lang.copy_button || 'Copy'}</button>
                        </div>
                    </div>`
            };
            
            container.innerHTML = Object.values(widgets).map(w => w()).join('');
            
            container.querySelectorAll('.tyra-reminder-item button').forEach(btn => btn.addEventListener('click', onReminderDoneClick));
            renderDashboardCharts();

        } catch (e) {
            console.error("Dashboard render error:", e);
            container.innerHTML = '<p>Could not load dashboard data.</p>';
        }
    }
    
    async function renderDashboardCharts() {
        try {
            const cycleChartConfig = await api.get('chart_data', { type: 'cycle_length' });
            new Chart(document.getElementById('tyra-cycle-chart').getContext('2d'), cycleChartConfig);
        } catch(e) { console.error("Could not render cycle chart:", e); }
        try {
            const interactionChartConfig = await api.get('chart_data', { type: 'interaction_time' });
            new Chart(document.getElementById('tyra-interaction-chart').getContext('2d'), interactionChartConfig);
        } catch(e) { console.error("Could not render interaction chart:", e); }
    }

    async function onDashboardActionClick(e) {
        const button = e.target.closest('button');
        if (!button) return;
        const action = button.dataset.action;
        if (!action) return;

        if (action === 'export-pdf' || action === 'export-csv') {
            const format = action.split('-')[1];
            button.textContent = 'Generating...';
            button.disabled = true;
            try {
                const blob = await api.get(`export/${format}`, {}, true);
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `tyra_health_report.${format}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
            } catch (err) {
                console.error(`Export failed for ${format}`, err);
            } finally {
                button.textContent = `Download ${format.toUpperCase()}`;
                button.disabled = false;
            }
        } else if (action === 'share') {
            button.textContent = 'Generating...';
            button.disabled = true;
            const { ok, data } = await api.post('share_report');
            if(ok) {
                const container = state.targetElement.querySelector('.tyra-share-link-container');
                container.classList.remove('hidden');
                container.querySelector('input').value = data.share_url;
            }
            button.textContent = state.lang.share_report_button || 'Get Share Link';
            button.disabled = false;
        } else if (action === 'copy') {
            const input = state.targetElement.querySelector('.tyra-share-link-container input');
            navigator.clipboard.writeText(input.value);
            button.textContent = 'Copied!';
            setTimeout(() => { button.textContent = state.lang.copy_button || 'Copy'; }, 2000);
        }
    }

    async function onReminderDoneClick(e) {
        const btn = e.target;
        const reminderId = btn.dataset.id;
        btn.disabled = true;
        const {ok} = await api.post('reminders/delete', { reminder_id: reminderId });
        if(ok) {
            btn.closest('li').style.display = 'none';
        } else {
            btn.disabled = false;
        }
    }

    // --- INITIALIZATION ---
    window.TyraWidget = {
        init: async function(options) {
            if (!options.targetElementId || !options.apiUrl) return console.error("Tyra Widget: 'targetElementId' and 'apiUrl' are required.");
            
            // MODIFIED in v118.1: Accept authToken and forceOpen options
            const { apiUrl, targetElementId, authToken, forceOpen } = options;

            Object.assign(state, { 
                apiUrl: apiUrl.replace(/\/$/, ''), 
                targetElement: document.getElementById(targetElementId),
                jwtToken: authToken || null, // Use the provided token if it exists
                onboardingToken: null, 
                isGuest: false, 
                userEmail: '',
                currentView: 'loading',
                userName: '',
                lang: {},
                dashboardData: null,
                childDobs: [],
                isDashboardStale: false,
                streaks: { current: 0 }
            });

            TYRA_AVATAR_URL = `${state.apiUrl}/static/images/tyra_avatar.png`;

            // MODIFIED in v118.1: Handle forced open state for native app
            if (forceOpen) {
                // Directly render the widget shell without the launcher
                state.targetElement.innerHTML = templates.widgetShell('Tyra');
                const widgetContainer = state.targetElement.querySelector('.tyra-widget-container');
                widgetContainer.classList.add('open');
                // Remove the close button as the native app will handle closing the view
                const closeBtn = state.targetElement.querySelector('#tyra-close-btn');
                if(closeBtn) closeBtn.style.display = 'none';
            } else {
                // Original web flow with launcher
                state.targetElement.innerHTML = templates.launcher() + templates.widgetShell('Tyra');
                const launcher = state.targetElement.querySelector('.tyra-launcher');
                const widgetContainer = state.targetElement.querySelector('.tyra-widget-container');
                const closeBtn = state.targetElement.querySelector('#tyra-close-btn');

                launcher.addEventListener('click', () => {
                    widgetContainer.classList.add('open');
                    launcher.classList.add('hidden');
                });
                closeBtn.addEventListener('click', () => {
                    widgetContainer.classList.remove('open');
                    launcher.classList.remove('hidden');
                });
            }

            // MODIFIED in v118.1: Check if we already have a token
            if (state.jwtToken) {
                // If a token was provided, we are already authenticated.
                state.currentView = 'chat';
                await initializeAuthenticatedSession(); // Fetches config and renders the chat view
            } else {
                // Original flow for web users without a token
                try {
                    const config = await api.initialConfig();
                    state.lang = config.lang;
                    state.targetElement.querySelector('#tyra-header-title').textContent = state.lang.app_title || 'Tyra';
                    
                    if (config.auth_mode === 'otp') {
                        state.currentView = 'email_entry';
                    } else {
                        await onGuestButtonClick({target: document.createElement('button')});
                    }
                } catch (error) {
                    console.error("Tyra Init Error:", error);
                    state.lang = { app_title: 'Tyra', welcome_message_guest: 'Chat is temporarily unavailable.' };
                    state.currentView = 'error';
                }
                render();
            }
        }
    };
})();