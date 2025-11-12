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

---

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

We are using Free Tier righjt now, later move to  Tier 1.

* How to Correlate

```bash
list_google_models.py list two models:
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