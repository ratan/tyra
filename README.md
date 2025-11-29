Of course. This is the perfect way to consolidate all the deployment knowledge into a single, comprehensive guide. By combining the local setup instructions with the production roadmap, we can create a definitive document for running the application anywhere.

I will create a detailed, step-by-step markdown guide that covers both local development on Ubuntu and a production deployment on Render.com, incorporating all the specific settings you've listed.

***

### **Tyra Application Setup & Deployment Guide (v101.4)**

This guide provides complete instructions for setting up, configuring, and running the Tyra application. It is divided into two parts:
*   **Part 1:** Setting up a local development environment on Ubuntu.
*   **Part 2:** Deploying the application to a production-grade cloud server on Render.com.

---

### **Part 1: Local Development Setup (Ubuntu)**

Follow these steps to run the application on your local machine for development and testing.

#### **Step 1: Prerequisites & File Structure**
Ensure all project files are in a single directory. You will also need to create a `requirements.txt` file.

**1. Create the `requirements.txt` file:**
In your main project directory, create a file named `requirements.txt`. This file tells Python which libraries are needed. Copy and paste the following content into it:

```
# requirements.txt
flask
python-dotenv
google-generativeai
markdown-it-py
dateparser
fpdf2
pyjwt
flask-session
sendgrid
gunicorn
Flask-SQLAlchemy
```
*Note: We include `gunicorn` and `Flask-SQLAlchemy` here to match the production environment as closely as possible.*

#### **Step 2: Create and Activate a Python Virtual Environment**
This creates an isolated environment for the project's dependencies.

**1. Open a terminal** in your project directory.

**2. Create the virtual environment:**
```bash
python3 -m venv venv
python3.12 -m venv venv
```

**3. Activate the environment:**
```bash
source venv/bin/activate
```
Your terminal prompt will now start with `(venv)`.

**4. Install the required libraries:**
```bash
pip3 install -r requirements.txt
pip install -r requirements.txt
```

Check that you are using correct python from virtual env and not system env
```bash
which python
/Users/ankita/Documents/my_work/women_health_chatbot/venv/bin/python
```

#### **Step 3: Configure Local Environment Variables**
The `.env` file holds your secret keys for local development.

**1. Edit the `.env` file.**

**2. Fill in your credentials:**
   *   Generate a `FLASK_SECRET_KEY` by running this in your terminal: `python3 -c 'import secrets; print(secrets.token_hex(24))'`
   *   Add your `GEMINI_API_KEY` from Google AI Studio. Currently it is linked with GEMINI API dummy project.
   *   https://aistudio.google.com/ -> Get API Key -> Project -> Import Project -> Gemini API -> Key (Select API Key) (Later Set Up billing)
   *   Add your `SENDGRID_API_KEY` and verified `SENDER_EMAIL` from SendGrid.
   *   Add a temporary `ADMIN_SECRET_KEY` for local testing of the download endpoint.

Your `.env` file should look like this:
```
# .env
FLASK_SECRET_KEY="a_long_random_hex_string_generated_by_the_command"
GEMINI_API_KEY="AIzaSy...your_gemini_key"
SENDGRID_API_KEY="SG.AbCd...your_sendgrid_key"
SENDER_EMAIL="your_verified_email@example.com"
ADMIN_SECRET_KEY="a_temporary_secret_for_local_testing"
```
**Note:** You do **not** need to set `PERSISTENT_DATA_PATH` locally. The application code will correctly default to using the current directory.

#### **Step 4: Run and Test the Application Locally**

**1. Run the Flask Development Server:**
With your virtual environment active, run:
```bash
python3 app.py
```
The server will start on `http://127.0.0.1:5000`. When you run it for the first time, you will see a new file named `tyra_prod.db` appear in your project folder. This is your local SQLite database.

**2. Test the Monolith Version:**
*   Open your browser and go to **http://127.0.0.1:5000**
*   You should see the full Tyra web application.

**3. Test the Embeddable Widget Version (Requires two terminals):**
*   **Terminal 1:** Keep the Flask server from Step 1 running.
*   **Terminal 2:** Open a *new terminal window*, navigate to the same project directory, and run this simple web server:
    ```bash
    python3 -m http.server 8000
    ```
*   **In your browser, go to:** **http://localhost:8000/embedding_test.html**
*   You should see the test page with the purple Tyra widget launcher in the bottom-right corner.


### **Part 2: Production Deployment Setup (Render.com)**

Follow these steps to deploy the application to a scalable, persistent cloud environment. This guide assumes you have a Render account and have connected it to a Git repository (GitHub, GitLab, etc.) containing the project code.

#### **Step 1: Create a New Web Service**
1.  In your Render Dashboard, click **"New +"** and select **"Web Service"**.
2.  Connect your Git repository and select the correct repository for Tyra.
3.  Give your service a unique name (e.g., `tyra-chat-app`).
4.  Select the region closest to your users.
5.  Ensure the **Runtime** is set to **Python 3**.

#### **Step 2: Configure the Persistent Disk**
This is the most critical step for ensuring your data is not lost on restarts.
1.  Scroll down to the **"Disks"** section.
2.  Click **"Add Disk"**.
3.  Fill in the details:
    *   **Name:** `tyra-data` (or any name you prefer) PERSISTENT_DATA_PATH
    *   **Mount Path:** `/data/tyra`
    *   **Size:** Start with `1 GB`.
4.  Click **"Add Disk"** to save.

#### **Step 3: Configure Environment Variables**
This is where you will securely store your secret keys and tell the application where the persistent disk is.
1.  Go to the **"Environment"** tab for your new service.
2.  Click **"Add Environment Variable"** for each of the following keys, filling in your **production-level** values.

| Key                         | Value                                         | Description                                                                 |
| --------------------------- | --------------------------------------------- | --------------------------------------------------------------------------- |
| `PYTHON_VERSION`            | `3.12`                                        | Specifies the Python version Render should use.                             |
| `PERSISTENT_DATA_PATH`      | `/data/tyra`                                  | **Crucial:** Must exactly match the Disk Mount Path from Step 2.            |
| `FLASK_SECRET_KEY`          | *Your long, random secret key*                | A unique, secure key for signing sessions.                                  |
| `GEMINI_API_KEY`            | *Your Google AI Studio API Key*               | Your production key for the Gemini model.                                   |
| `SENDGRID_API_KEY`          | *Your SendGrid API Key*                       | Your production key for sending OTP emails.                                 |
| `SENDER_EMAIL`              | *your_verified_email@example.com*             | The "From" email address verified in SendGrid.                              |
| `ADMIN_SECRET_KEY`          | *A new, very long, unpredictable secret*      | The secret "password" for accessing the database download endpoint.         |
| `ZEPTOMAIL_TOKEN`           | *Your ZeptoMail API Key*                      | Your production key for sending OTP emails.                                 |

We are using ZEPTOMAIL_TOKEN instead of SENDGRID_API_KEY now.

#### **Step 4: Configure Build and Start Commands**
1.  Go back to the service's **"Settings"** tab.
2.  Find the **"Build & Deploy"** section.
3.  Set the following commands:
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `gunicorn --bind 0.0.0.0:$PORT --worker-tmp-dir /dev/shm app:app`

#### **Step 5: Configure the Health Check**
1.  In the **"Settings"** tab, scroll down to the **"Health Check"** section.
2.  Set the **Health Check Path** to: `/health`

#### **Step 6: Deploy and Verify**
1.  At the bottom of the page, click **"Create Web Service"**.
2.  Render will now start the first deployment. You can monitor its progress in the **"Events"** or **"Logs"** tab.
3.  **Verification:**
    *   Once the deployment is live, check the logs. You should not see any errors.
    *   Access your application at the public URL provided by Render (e.g., `https://tyra-chat-app.onrender.com`).
    *   Test the functionality to ensure everything is working as expected. Your data will now be safely stored on the persistent disk.
4. **Download sqlite database:**
    *   Use the admin/backup/download_db method to download the sqlite DB
    *   command to use:  https://tyra-ai.onrender.com/admin/backup/download_db/<secret_key>
    *   X7kP9mW3qT8rY2nF6vL4zJ0hB5tN1cD8wQ2xM9pA3gR7yU5iK
5. **User Engagement:**
    *   cd backup
    *   python3 user_analytics.py tyra_backup_aug14.db
    *   Read details in backup/README_user_analytic.md
    *   python3 user_analytics.py -h
6. **Persistent Disk Data:**
    *   Files and folders present in /data/tyra
    *   ls -lrt
    *   total 96
    *   File: tribher_data_final.json
    *   Folder: user_profiles
    *   Folder: shared_reports
    *   Folder: temp_uploads
    *   File: milestones_data.json
    *   File: tyra_prod.db
    *   Folder: flask_session
    *   File: education_tidbits.json
    *   File: wellness_videos.json
***

### **Miscelleneous Points (v101.4)**

This sectoion covers the other miscelleneous points here.
1. Privacy Policy
   tyra_widget.js
   <a href="https://fitcommunity.in/privacyPolicy.php" target="_blank" rel="noopener noreferrer">Privacy Policy</a>
2. Changes done in v117.4
    1.  Save the avatar image provided into `static/images/` and name it `tyra_avatar.png`. (Already done in previous version)
    2.  Create a 1000x1000px background image (e.g., with a purple-to-pink gradient), save it to `static/images/`, and name it `insight_template.png`.
    There is script which can create insight_template.png:
    cd backup
    python create_template.py
    3.  Download the "Poppins" font family from Google Fonts, and place the `Poppins-Bold.ttf` file into the `static/fonts/` directory.
3. TBD
---

#### **Point 1: Exact Command to download DB**
The exact URL you would paste into your browser to download the database would be:
https://tyra-ai.onrender.com/admin/backup/download_db/X7kP9mW3qT8rY2nF6vL4zJ0hB5tN1cD8wQ2xM9pA3gR7yU5iK


#### **Point 2: Scrapper**
1.  How to Use:
2.  Save the Code: Save the code below as scrape_tribher_final.py.
3.  Install Libraries: pip install requests beautifulsoup4
4.  Run the Script: python scrape_tribher_final.py
5.  Check the Output: A file named tribher_data_final.json will be created with the correctly structured data.


#### **Point 3: Health data**
1.  https://www.healthyapps.dev/developers
2.  https://sahha.ai/pricing


#### **Point 4: Milestones**
1.  Monolith Final: Feature_Comp_monolith_24Jul_5_women_health_chatbot/ (Jul 24)
2.  Guest Mode: Feature_Comp_22Jul_1_women_health_chatbot/ (Jul 22)
3.  Fertility: 21Jul_2_women_health_chatbot/
4.  Tyra Avatar, Privacy Policy: Feature_comp_12Oct25_1_privacy_tyra_avatar__women_health_chatbot
5.  Sharable Insights: Feature_comp_24oct25_1_sharable_insights_women_health_chatbot
6.  Easter Egg, Discrete Icon: Feature_comp_21Nov25_1_easter_egg_discrete_mode_women_health_chatbot
7.  Burn Mode: Feature_comp_21Nov25_2_burn_mode_women_health_chatbot
8.  Cycle Sync: Feature_comp_24Nov25_1_cycle_sync_women_health_chatbot


#### **Point 5: Pending Item**
1.  ENABLE_SECURE_CORS_POLICY=True (Once Tribher is connected)  
2.  Add video in youtube and make them Public but dont list in channel (check app too)
3.  Redis support
4.  TBD

#### **Point 6: SCP to Render**
1.  From Render, Shell, SSH Address: ssh srv-d2675ure5dus73d8l7qg@ssh.singapore.render.com
2.  ssh srv-d2675ure5dus73d8l7qg@ssh.singapore.render.com
3.  When asked, enter yes
4.  cd /data/tyra/
5.  You can see all the persistant files
6.  scp -r milestones_data.json srv-d2675ure5dus73d8l7qg@ssh.singapore.render.com:/data/tyra

#### **Point 7: Language Support**
```html
<select name="language" id="language" required>
    <option value="en" selected>English</option>
    <option value="bn">বাংলা (Bengali)</option>
    <option value="gu">ગુજરાતી (Gujarati)</option>
    <option value="hi">हिन्दी (Hindi)</option>
    <option value="kn">ಕನ್ನಡ (Kannada)</option>
    <option value="ml">മലയാളം (Malayalam)</option>
    <option value="mr">मराठी (Marathi)</option>
    <option value="or">ଓଡ଼ିଆ (Odia)</option>
    <option value="pa">ਪੰਜਾਬੀ (Punjabi)</option>
    <option value="ta">தமிழ் (Tamil)</option>
    <option value="te">తెలుగు (Telugu)</option>
    <option value="ur">اردو (Urdu)</option>
    <option value="ar">العربية (Arabic)</option>
</select>
```


### **Utility or Helper tools**

This sectoion list few of helper or utility tools or functions needed for Tyra.

#### **1: Available Models for generatation**
List the Available Gemini Models for generatation

```bash
cd backup/
python list_google_models.py
```
This will list of acive gemini models.
Use/Update the appropriate models in GEMINI_MODEL_CASCADE_LIST in app.py.

#### **2: Gemini Rate Limit**
https://ai.google.dev/gemini-api/docs/rate-limits#free-tier

We are using Free Tier right now, later move to  Tier 1.

* How to Correlate

```bash
cd backup
python list_google_models.py 

list two models:
models/gemini-2.5-flash-lite-preview-06-17
models/gemini-2.5-flash-lite-preview-09-2025
```

The rate limit for "Gemini 2.5 Flash-Lite Preview" applies to both of the specific models you listed above.

Best Practice: You should generally use the most recent version available from the API, which in your list would be `models/gemini-2.5-flash-lite-preview-09-2025`. This ensures you are using the latest iteration of the preview model.

#### **3: Tribher Pricing Plan**

```bash
cd backup/
python scrape_tribher_final.py
```
This script generates `tribher_data_final.json` file which is used by Tyra to suggest about Tribher Programs and pricing.

* How to Update

Update `scrape_tribher_final.py` carefully. As Tribher.com was not allowing the general web scrapping, we had to manually update `scrape_tribher_final.py` file with all the contents, plans, pricing. Do it carefully as json format is important for Tyra.

#### **4: Generate Discrete Icon**

Idea for privacy-conscious users (school/work environments).

The Concept: Allow the user to change the floating launcher icon from the Tyra Avatar to a generic "Calculator," "Notes," or "Weather" or "Journal" or "Calendar" icon so it looks inconspicuous on their screen

```bash
cd backup/
python generate_assets.py

This script generates following images:
├── static
│   ├── css
│   ├── images
│   │   ├── tyra_avatar.png
│   │   ├── icon_notes.png    <-- Generated by script
│   │   ├── icon_weather.png  <-- Generated by script
│   │   ├── icon_calendar.png <-- Generated by script
│   │   └── icon_journal.png  <-- Generated by script

```

### **New Important Feature Added**

This sectoion list few of the newer feature added to Tyra.

#### **1. The "Easter Egg" Animations (Easiest)**
**Complexity:** ⭐ (Frontend Only)
**Impact:** High "Delight" factor.
**Why it's easy:** It requires zero backend changes. It is purely JavaScript logic detecting specific keywords and triggering CSS animations.

*   **The Concept:** When a user types "congrats," "yay," or "streak," confetti falls. If they type "period," "cramps," or "sad," the background color shifts slightly to a comforting tone.
*   **Implementation:**
    1.  **CSS:** Add keyframe animations for confetti or background transitions in `tyra_widget.css`.
    2.  **JS:** In `onChatSubmit` (`tyra_widget.js`), regex match the user's message. If a keyword matches, inject a temporary `div` with the animation class.

#### **2. Discreet Mode / Icon Customization**
**Complexity:** ⭐⭐ (Frontend + Minimal Settings Logic)
**Impact:** High for privacy-conscious users (school/work environments).
**Why it's easy:** We already have a Settings Menu (v114.0). We just need to swap an image source.

*   **The Concept:** Allow the user to change the floating launcher icon from the Tyra Avatar to a generic "Calculator," "Notes," or "Flower" icon so it looks inconspicuous on their screen.
*   **Implementation:**
    1.  **Assets:** Add 2-3 generic icons to `static/images/`.
    2.  **JS:** Add a "Change Icon" option in the Settings dropdown.
    3.  **Logic:** When clicked, update the `src` of `.tyra-launcher img`. Save this preference to `localStorage` (no need to save to backend database yet).


#### **3: Aesthetic Theming Engine (The "Vibe" Check)**

**Complexity:** ⭐⭐ (Moderate - CSS Refactoring)
**Impact:** Very High (Identity & Daily Usage)

#### **Why this is the next step:**
1.  **Standard Expectation:** For Gen Z and Millennials, **Dark Mode** isn't a feature; it's a requirement. Lack of it feels outdated.
2.  **Self-Expression:** Users treat their phone interfaces like digital fashion. Allowing them to switch from "Clinical Purple" to "Cottagecore Green" or "Cyberpunk Neon" makes the app feel like *theirs*.
3.  **Technical Synergy:** We just implemented `localStorage` persistence for the Icon. We can reuse the exact same logic to persist the **Theme**.
4.  **Proposed Themes:**
    *   **Default:** (Existing Purple/Rose)
    *   **The "Midnight"** (Dark Mode)
    *   **The "Coquette"**  (Soft Girl)
    *   **The "Matcha"** (Wellness/Clean Girl)
    *   **The "Ocean"** (Calm Blue)
    *   **The "Sunset"** (Dopamine)


#### **4: "Burner Mode" (The Panic Button)**.

**Complexity:** ⭐⭐ (Backend Logic + UI Button)
**Impact:** Extremely High for Trust & Safety.

#### **Why this is next:**
1.  **Completes the "Discreet" Arc:** You just gave them a way to hide the app icon (Discreet Mode). Now, give them a way to **hide the conversation**.
2.  **The Use Case:** A user is chatting about a sensitive topic (e.g., pregnancy scare, UTI) in a semi-public place. They want to close the app and ensure that if they open it again 5 minutes later (or if someone else does), that specific conversation is **gone**.
3.  **Gen Z Value:** This demographic values "ephemeral" messaging (like Snapchat). Knowing they can "burn" the chat history instantly creates massive trust.

4.  **Implementation** We will add a "🔥 Burn History" button to the Settings menu. When clicked, it will strictly wipe the **Chat UI** immediately and tell the **Backend** to forget the last 24 hours of logs.

    *   app.py: Added BURN_WINDOW_HOURS = 24 and a new endpoint /api/v1/privacy/burn_history. This endpoint wipes the persisted chat_log (UI state) entirely and filters the interaction_log (AI context) to remove entries from the last 24 hours.

    *   tyra_widget.js: Added the "🔥 Burn History" button to the Settings dropdown template. Implemented the onBurnHistoryClick handler which calls the API and immediately clears the chat DOM with a visual message.

    *   tyra_widget.css: Added styling for .tyra-danger-btn to make the button distinct (using the existing --error-color variable).


#### **5: Dynamic Persona Switching ("The Vibe Check")**.

**Complexity:** ⭐⭐⭐ (Moderate - Backend Prompt Logic + UI)
**Impact:** High for retention and emotional connection.

#### **Why this is next:**
1.  **Personalization Depth:** We've let users change how Tyra *looks* (Themes). Now we let them change how Tyra *sounds*.
2.  **Demographic Variance:**
    *   Gen Z users often prefer the "Big Sister" vibe (emojis, validation, casual).
    *   Older Millennials or users in a medical crisis often prefer the "Doctor" vibe (concise, factual, serious).
    *   Fitness-focused users want the "Coach" vibe (high energy, accountability).
3.  **Foundation Exists:** We already have a basic "Real Talk" mode (v115.0), but that is a temporary trigger. This feature makes the persona **persistent**.

#### **Implementation Plan for v119.2**

We will add a "✨ Change Vibe" option to the Settings menu, allowing the user to select Tyra's personality.

##### **1. The Personas**
*   **💜 The Bestie (Default):** Warm, empathetic, uses emojis, validating. *"I got you, that sounds tough. 🥺"*
*   **👩‍⚕️ The Professional:** Clinical, concise, factual, no emojis. *"Based on your symptoms, here is the data."*
*   **⚡ The Coach:** High energy, motivational, action-oriented. *"Let's crush this goal! You're doing great!"*

##### **2. Technical Changes**

*   **Backend (`user_profiler.py`):**
    *   Update `format_profile_for_prompt` to check a `persona` field in the profile.
    *   Inject a strong system instruction block that overrides the default tone based on this selection.

*   **Backend (`app.py`):**
    *   Update `/api/v1/config` to return the current persona.
    *   Add/Update logic to save `persona_preference` in the user profile.

*   **Frontend (`tyra_widget.js`):**
    *   Add "✨ Change Vibe" to the Settings dropdown.
    *   Create a new Modal (similar to Theme/Icon pickers) to select the persona.
    *   Persist the selection via API.


#### **6: Cycle-Synced Interface ("Bio-Adaptive UI")**

**Complexity:** ⭐⭐ (Low/Moderate - Logic connection)
**Impact:** Very High for "Alive Factor" & Daily Engagement.

#### **Why this is next:**
1.  **Bio-Feedback Loop:** Young users want technology that feels connected to their biology. This feature transforms the app from a static tool into a "living" accessory that mirrors their body's internal state.
2.  **Leverages Existing Assets:** We already built the *Period Tracker* (Backend) and the *Theming Engine* (Frontend). This feature bridges the gap, making them work together automatically.
3.  **Magical UX:** Having the app automatically shift from *High-Energy Orange* (Ovulation) to *Cozy Pink* (Menstrual) without user input creates a "wow" moment that feels highly personalized.

#### **Implementation Plan for v119.5 - v119.7**

We will add a "🔄 Cycle Sync" toggle to the Settings menu. When enabled, the app's color theme will automatically update based on the user's current biological phase.

##### **1. The Phase-to-Theme Mapping**
*   **🌸 Menstrual (Days 1-5):** **Coquette Theme** (Soft Pink/Comforting)
*   **🌿 Follicular (Days 6-13):** **Matcha Theme** (Fresh Green/New Beginnings)
*   **🟠 Ovulation (Days 14-17):** **Sunset Theme** (Vibrant Orange/High Energy)
*   **🌙 Luteal (Days 18+):** **Midnight Theme** (Dark Purple/Inward/Restorative)

##### **2. Technical Changes**

*   **Backend (`app.py`):**
    *   Create a helper function `_calculate_cycle_phase(profile)` that determines the phase based on the last logged period start date.
    *   Update the `/api/v1/config` endpoint to calculate and return `current_phase` in the JSON response.
    *   Add `ENABLE_CYCLE_SYNCED_UI` feature flag.

*   **Frontend (`tyra_widget.js`):**
    *   Define `PHASE_THEMES` constant mapping biological phases to theme keys.
    *   Add "🔄 Cycle Sync" toggle button to the Settings dropdown.
    *   Implement logic in `initializeAuthenticatedSession` to check the preference and auto-apply the theme.
    *   Implement **Smart Override**: If the user manually changes the theme while Sync is ON, automatically turn Sync OFF to respect their choice.

*   **Backend (`user_profiler.py`):**
    *   Update the system prompt (`ui_context`) to make Tyra "self-aware" of this new feature so she can explain it to users.


### **7: "Spotify Wrapped" Style Graphic Generation (Health Aura)**
**Complexity:** ⭐⭐⭐⭐⭐ (High - Advanced Python Image Processing + Data Aggregation)
**Impact:** ⭐⭐⭐⭐⭐ (Viral - The primary driver for social sharing and user acquisition).

### **Why this is next:**
1.  **The "Shareability" Gap:** Currently, Tyra provides text answers. Text is useful, but it isn't posted on Instagram Stories. To reach a younger demographic, the output must be **visual, aesthetic, and identity-affirming**.
2.  **Gamification of Self:** Users love seeing their behaviors reflected back to them as a "personality type" (e.g., MBTI, Astrology, Spotify Wrapped). It turns boring health logs into a "Vibe."
3.  **Technical Foundation Ready:** We have the `PIL` (Pillow) library installed and a basic image route from v117.0. Now we upgrade it from a static template to a **Procedural Art Engine**.

---

### **Implementation Plan for v119.8**
We will transform the "Weekly Summary" into a **"Health Aura" Generator**. Instead of a generic card, Tyra will generate a unique, abstract piece of art based on the user's recent logs.

#### **1. The "Auras" (Logic Mapping)**
We will analyze the last 30 days of logs (`mood`, `sleep`, `stress`) to assign one of three dominant "Vibes."

*   🔮 **Chaos Coordinator**
    *   *Triggers:* High stress, poor sleep, anxious mood.
    *   *Visuals:* Deep Purple, Dark Red, Neon Violet.
    *   *Tagline:* "Survived [N] logs this month."
*   ✨ **Main Character Energy**
    *   *Triggers:* Energetic mood, good sleep, consistent activity.
    *   *Visuals:* Bright Orange, Hot Pink, Coral (Sunset gradients).
    *   *Tagline:* "Radiating good vibes."
*   🌿 **Zen Master**
    *   *Triggers:* Calm mood, low stress, "good" sleep.
    *   *Visuals:* Sage Green, Teal, Soft Blue.
    *   *Tagline:* "Unbothered & flourishing."

#### **2. Technical Changes**

**Backend (`app.py`):**
*   **New Logic Function:** Implement `_calculate_monthly_vibe(profile)`.
    *   It must filter `health_logs` for the last 30 days.
    *   It counts frequencies of specific values (e.g., "anxious", "energetic") to determine the dominant Aura.
    *   It returns a **Color Palette** (List of 3 Hex codes) and a **Title** string.
*   **Procedural Art Engine:** Upgrade `_generate_insight_image`:
    *   **Canvas:** Create a 1080x1920 (Story size) blank canvas using `PIL.Image.new`.
    *   **Background:** Instead of loading a static image, use `ImageDraw.ellipse` to draw 5-7 semi-transparent "Orbs" at random X/Y coordinates.
    *   **Coloring:** Fill these orbs using the specific **Color Palette** returned by the logic function.
    *   **Typography:** Use `textwrap` to center and bold the Aura Title (e.g., "MAIN / CHARACTER / ENERGY") so it looks like a poster.

**Frontend (`tyra_widget.js`):**
*   **Conversation Trigger:** The feature is triggered conversationally ("show my summary").
*   **UI Component:** Render the `weekly_insight_card`.
*   **Download Logic:** Ensure the "Download Image" button handles the binary blob correctly so the user saves a high-quality `.png` to their phone's gallery, ready for Instagram/TikTok.

---

### **Visual Concept (Code vs. Result)**

| Aspect | v117.0 (Old MVP) | v119.8 (New Wrapped Engine) |
| :--- | :--- | :--- |
| **Background** | Static `.png` file loaded from disk. | **Dynamic:** Python draws random shapes every time. |
| **Color** | Always Purple/White. | **Adaptive:** Changes based on user's stress/mood. |
| **Text** | Simple paragraph summary. | **Poster Style:** Huge, bold typography ("CHAOS COORDINATOR"). |
| **Format** | Square (1:1) | **Story (9:16)** - Full screen mobile. |


Here is the structured detail for the new **Feature #7: Proactive Engagement Engine**.

***

### **8: "Proactive Engagement Engine" (Context-Aware Greeting)**
**Complexity:** ⭐⭐⭐ (Moderate - Backend Logic Tree + Frontend Hooks)
**Impact:** ⭐⭐⭐⭐⭐ (Retention - Transforms the bot from "reactive tool" to "caring companion").

### **Why this is next:**
1.  **Breaking the "Empty Chat" Syndrome:** Currently, Tyra waits for the user to speak. This puts the cognitive load on the user. A proactive greeting ("Hi Sarah, how did that exam go?") removes friction and invites interaction.
2.  **Emotional Continuity:** Users feel "heard" when a bot remembers their state from yesterday (e.g., high stress) and follows up. This builds trust faster than any feature.
3.  **Life-Stage Relevance:** A teenager needs a different opening line ("How's school?") than a pregnant woman in her third trimester ("Time for a breathing exercise?"). This makes the app feel bespoke to every user segment.

---

### **Implementation Plan for v120.0**
We will implement a **Decision Tree Logic** that runs *before* the user types anything. When the widget opens, Tyra will "think" and generate a custom opening line.

#### **1. The Logic Tree (Priority Hierarchy)**
The engine evaluates conditions in this strict order. The first match determines the greeting.

1.  🔴 **Safety/Continuity (Highest Priority)**
    *   *Trigger:* User logged "High Stress," "Severe Pain," or "Depression" in the last 24 hours.
    *   *Action:* Gentle, empathetic follow-up. *"I know yesterday was tough. How are you holding up?"*
2.  📅 **Weekly "Value Add" (Once/Week)**
    *   *Trigger:* >7 days since last "Growth" event.
    *   *Action:* Delivers a specific nugget based on persona.
        *   *Pregnant:* "Week 32 Update: Baby is the size of a squash!"
        *   *Teen:* "Myth Buster: Periods don't sync!"
        *   *General:* "Weekly Growth: What's one small win you had?"
3.  👶 **Life Stage Context (The "Care" Layer)**
    *   *Teen:* School/Social check-in.
    *   *Pregnant (30+ wks):* Immediate suggestion for **Physical Relief** (Breathing/Pelvic tilt).
    *   *Menopause:* Check for **Sleep/Hot Flashes**.
    *   *Senior:* Check for **Mobility/Joints**.
4.  🔄 **Cycle Phase (The "Living UI" Hook)**
    *   *Trigger:* None of the above apply, but tracking is enabled.
    *   *Action:* Phase-specific advice. (e.g., Luteal = "Be gentle with yourself today.").
5.  ☀️ **Time of Day (Fallback)**
    *   *Trigger:* No data available.
    *   *Action:* "Good morning/evening."

#### **2. Technical Changes**

**Backend (`app.py`):**
*   **New Route:** `/api/v1/greet` (POST).
*   **New Logic Function:** `_get_proactive_instruction(profile)`. This implements the Decision Tree above and returns a specific *System Instruction string*.
*   **LLM Integration:** The route injects this instruction into a specialized prompt: *"You are initiating the conversation. GOAL: [Instruction]. Keep it under 2 sentences."*
*   **Spam Prevention:** The route checks the last interaction timestamp. If `< 2 hours`, it returns `no_greet_needed` to avoid annoying the user.

**Frontend (`tyra_widget.js`):**
*   **Trigger Hook:** Inside `initSession()` (which runs on load), add a call to `triggerProactiveGreeting()`.
*   **Delay:** Add a `setTimeout(1000ms)` so the chat window opens *before* the message appears, simulating a "typing" effect.

---

### **User Experience (Before vs. After)**

| Scenario | v119.8 (Reactive) | v120.0 (Proactive Engine) |
| :--- | :--- | :--- |
| **High Stress Yesterday** | *User opens app.*<br>(Silence)<br>**User:** "I'm still stressed." | *User opens app.*<br>**Tyra:** "Hey. I know yesterday was really heavy for you. How are you feeling this morning? 💜" |
| **34 Weeks Pregnant** | *User opens app.*<br>(Silence)<br>**User:** "Back hurts." | *User opens app.*<br>**Tyra:** "Hi [Name]! At 34 weeks, that pressure is real. Shall we do a quick 60-second breathing reset together?" |
| **Teenager (Morning)** | *User opens app.*<br>(Silence) | *User opens app.*<br>**Tyra:** "Good morning! ☀️ Ready to slay the day, or do we need a vibe check first?" |