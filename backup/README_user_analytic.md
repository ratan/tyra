Of course. It's a great idea to have this entire workflow documented in a single, clear guide.

Here is the updated, comprehensive summary covering why free users cannot be captured with the current design, and the step-by-step process for downloading the database and running the improved analytics script.

***

### **Guide to Generating User Analytics Reports (v1.2)**

This guide explains how to extract and analyze user engagement data from your live Tyra application.

#### **Important Prerequisite: Why "Free Users" (Guests) Cannot Be Tracked**

In the current architecture, the application is designed to respect user privacy and maintain a clean database.
*   **Guest Sessions are Ephemeral:** When a user browses as a "guest," their session is temporary and their interactions are **not** written to the persistent SQLite database.
*   **Design Choice:** This is a deliberate decision. Storing data for every anonymous visitor would fill the database with low-value, non-repeatable interactions and raise privacy concerns.
*   **What This Report Measures:** Therefore, this analytics script focuses exclusively on the valuable data from your **signed-up, registered users**. It answers questions about how your committed user base is engaging with the platform over time.

---

### **Step 1: Download the Live Database from Render**

First, you need to get a secure copy of your production database file. You will use the secret admin endpoint we created for this purpose.

**1. Find Your Application URL:**
   This is the public URL for your service on Render (e.g., `https://tyra-chat-app.onrender.com`).

**2. Find Your Admin Secret Key:**
   *   Log in to your Render.com dashboard.
   *   Navigate to your Tyra web service.
   *   Go to the **"Environment"** tab.
   *   Find the key named `ADMIN_SECRET_KEY` and securely copy its value.

**3. Construct the Download URL:**
   Combine the parts into a single URL in this format:
   `https://<your-render-app-url>/admin/backup/download_db/<your-admin-secret-key>`

   **Example:**
   If your app URL is `https://tyra-chat-app.onrender.com` and your key is `a_very_long_and_random_secret_string_12345`, the full URL would be:
   `https://tyra-chat-app.onrender.com/admin/backup/download_db/a_very_long_and_random_secret_string_12345`

**4. Download the File:**
   *   Paste the complete URL into your web browser and press Enter.
   *   Your browser will begin downloading the database file, which will likely be named `tyra_prod.db`.
   *   Save this file inside your local project directory. You can rename it for clarity if you wish (e.g., `tyra_backup_aug15.db`).

---

### **Step 2: How to Use the Analytics Script**

Now that you have the database file locally, you can run the `user_analytics.py` script against it.

**1. Open Your Terminal:**
   Navigate to your project directory.

**2. Activate Your Virtual Environment:**
   If it's not already active, run:
   ```bash
   source .venv/bin/activate
   ```

**3. Run the Script with the Database File as an Argument:**
   Execute the script, providing the name of the file you just downloaded.
   ```bash
   python3 user_analytics.py <name_of_your_downloaded_db_file>
   ```

   **Example Usages:**
   If your downloaded file is named `tyra_prod.db`:
   ```bash
   python3 user_analytics.py tyra_prod.db
   ```
   If you renamed it to `tyra_backup_aug15.db`:
   ```bash
   python3 user_analytics.py tyra_backup_aug15.db
   ```

---

### **Step 3: Understanding the Expected Output**

The script will print a detailed report directly to your terminal. Because we updated the logic, the engagement categories are now **mutually exclusive**—a user will only be counted in their most recent activity bucket.

Here is a sample of the expected output:

```
--- Tyra User Activity Report ---
Analyzing database file: 'tyra_prod.db'
Generated on: 2025-08-15 10:30:00
-----------------------------------
1. Total Registered Users: 152

--- User Engagement (Mutually Exclusive) ---
   - Active in last 24 hours:       18
   - Active 1-3 days ago:           27
   - Active 3-7 days ago:           33
   - Active 7-30 days ago:          37
   - Lapsed (no activity >30 days): 37
   ---------------------------------------
   Sum of Categories:             152 (Should match total users)

--- User Frequency (Last 30 Days) ---
   - Users with 2+ sessions:      62

--- Report Complete ---
```

**How to Interpret the Report:**
*   **Total Registered Users:** The total number of accounts ever created.
*   **User Engagement:** This section shows a funnel of user retention. The sum of these five categories will always equal your total registered users.
*   **User Frequency:** This is a separate metric that overlaps with the engagement numbers. It specifically measures how many of your *monthly active* users are returning more than once.