# app.py (v103.1 - Conversational Onboarding Language Fix)
import os, json, hashlib, google.generativeai as genai, calendar, time, io, csv, uuid, re, secrets
from datetime import datetime, timedelta, timezone
from flask import Flask, Response, render_template, request, jsonify, session, redirect, url_for, send_from_directory, g
from dotenv import load_dotenv, dotenv_values
from markdown_it import MarkdownIt
from google.api_core import exceptions
import dateparser
from difflib import SequenceMatcher
from collections import defaultdict
from werkzeug.utils import secure_filename
from fpdf import FPDF
from fpdf.enums import XPos, YPos # BUG FIX v93.0: Import necessary enums
import jwt
from functools import wraps
from flask_session import Session
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask_sqlalchemy import SQLAlchemy

from user_profiler import create_user_profile, format_profile_for_prompt, LANG_MAP

# Load environment variables from .env file FIRST.
load_dotenv()

# --- Configuration Constants ---
MAX_HISTORY_ENTRIES = 50
GEMINI_MODEL_NAME = 'gemini-2.5-flash-lite-preview-06-17'
CHATBOT_NAME = "Tyra"
REPORT_LIFETIME_HOURS = 36
GOAL_CHECK_IN_DAYS = 7
MAX_CACHE_SIZE = 200
THROTTLE_LIMIT = 20
THROTTLE_PERIOD_SECONDS = 60
OTP_LIFETIME_SECONDS = 300 # 5 minutes
BEHAVIORAL_SYNOPSIS_INTERVAL_DAYS = 3
BEHAVIORAL_SYNOPSIS_MIN_INTERACTIONS = 15
PROGRAM_SUGGESTION_COOLDOWN_DAYS = 3
MAX_CYCLE_HISTORY = 120
MAX_KEY_MEMORIES = 15 # NEW in v102.0

# Secure CORS allow-list for production
ALLOWED_ORIGINS = [
    'http://localhost:8000',
    'https://tribher.com',
    'https://fitcommunity.in'
]

# --- Feature Flags ---
ENABLE_CONVERSATIONAL_ONBOARDING = True # NEW in v103.0: Toggles between chat-based and form-based new user setup.
ENABLE_SQLITE_DATABASE = True # NEW in v101.4: Toggles between SQLite and JSON file storage
ENABLE_MULTI_LANGUAGE = True
ENABLE_TRIBHER_SUGGESTIONS = True
ENABLE_PERIOD_TRACKER = True
ENABLE_PROACTIVE_ASSISTANCE = True
ENABLE_DOCUMENT_UPLOAD = True 
ENABLE_VISUAL_TRIAGE = True
ENABLE_CHART_VISUALIZATION = True
ENABLE_VOICE_INPUT = True
ENABLE_DASHBOARD = True
ENABLE_CUSTOM_REMINDERS = True
ENABLE_EXPANDED_LOGGING = True
ENABLE_INTERACTIVE_DASHBOARD = True
ENABLE_REPORT_EXPORTING = True
ENABLE_CONTEXTUAL_REMINDERS = True
ENABLE_DASHBOARD_CUSTOMIZATION = True
ENABLE_EXPANDED_MOOD_TRACKING = True
ENABLE_SHAREABLE_REPORTS = True
ENABLE_AI_FOLLOW_UP_QUESTIONS = True
ENABLE_MEDICATION_TRACKING = True
ENABLE_GOAL_TRACKING = True
ENABLE_REALTIME_LOG_CONTEXT = True
ENABLE_OVULATION_TRACKER = True
ENABLE_GUEST_MODE = True
ENABLE_LLM_CACHING = True
ENABLE_REQUEST_THROTTLING = True
ENABLE_WIDGET_MODE = True
ENABLE_EMAIL_OTP_VERIFICATION = True
ENABLE_EMAIL_OTP_API_VERIFICATION = True
ENABLE_BEHAVIORAL_SYNOPSIS = True
ENABLE_SECURE_CORS_POLICY = False # !!! SET TO TRUE FOR PRODUCTION DEPLOYMENT !!!
# ---
app = Flask(__name__)

# BUG FIX v94.5: Robustly load config from .env into Flask's config object.
# This is more reliable than depending on os.getenv() which can fail with reloaders.
app.config.update(dotenv_values(".env")) 
app.config['SECRET_KEY'] = app.config.get("FLASK_SECRET_KEY")

# Now, set feature flags in the app config as well for consistency
app.config['ENABLE_WIDGET_MODE'] = ENABLE_WIDGET_MODE
app.config['ENABLE_EMAIL_OTP_VERIFICATION'] = ENABLE_EMAIL_OTP_VERIFICATION
app.config['ENABLE_EMAIL_OTP_API_VERIFICATION'] = ENABLE_EMAIL_OTP_API_VERIFICATION
app.config['ENABLE_CONVERSATIONAL_ONBOARDING'] = ENABLE_CONVERSATIONAL_ONBOARDING # NEW in v103.0

# --- DUAL-BACKEND PERSISTENT STORAGE CONFIGURATION (v101.4) ---
# Check for a persistent storage path from an environment variable (set in Render).
DATA_BASE_PATH = os.environ.get('PERSISTENT_DATA_PATH', '.')

# Configure Server-Side Sessions for Monolith Mode (Production Ready)
SESSION_DIR = os.path.join(DATA_BASE_PATH, "flask_session")
os.makedirs(SESSION_DIR, exist_ok=True)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = SESSION_DIR
Session(app)

# --- Conditional Backend Setup ---
if ENABLE_SQLITE_DATABASE:
    # --- SQLITE DATABASE CONFIGURATION ---
    DATABASE_FILE = 'tyra_prod.db'
    DATABASE_PATH = os.path.join(DATA_BASE_PATH, DATABASE_FILE)

    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)

    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        profile_hash = db.Column(db.String(64), unique=True, nullable=False, index=True) 
        profile_json = db.Column(db.Text, nullable=False)
        def to_dict(self): return json.loads(self.profile_json)

    with app.app_context():
        db.create_all()
    # --- END SQLITE CONFIGURATION ---
else:
    # --- JSON FILE STORAGE CONFIGURATION (Legacy Fallback) ---
    PROFILES_DIR = os.path.join(DATA_BASE_PATH, "user_profiles")
    os.makedirs(PROFILES_DIR, exist_ok=True)
    # --- END JSON FILE CONFIGURATION ---

# Define other persistent data paths
UPLOADS_DIR = os.path.join(DATA_BASE_PATH, "temp_uploads")
SHARED_REPORTS_DIR = os.path.join(DATA_BASE_PATH, "shared_reports")
TRIBHER_DATA_FILE = os.path.join(DATA_BASE_PATH, "tribher_data_final.json")
MILESTONES_DATA_FILE = os.path.join(DATA_BASE_PATH, "milestones_data.json")

# Define static directories separately as they are part of the app package
STATIC_CSS_DIR = os.path.join('static', 'css')
STATIC_JS_DIR = os.path.join('static', 'js')
LOCALES_DIR = "locales"

# Create all necessary non-profile directories
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(SHARED_REPORTS_DIR, exist_ok=True)
SHARED_REPORTS_DB_FILE = os.path.join(SHARED_REPORTS_DIR, "shared_reports_db.json")
os.makedirs(STATIC_CSS_DIR, exist_ok=True)
os.makedirs(STATIC_JS_DIR, exist_ok=True)
os.makedirs(LOCALES_DIR, exist_ok=True)
# --- End of Storage Configuration ---

TRIBHER_DATA = None
MILESTONES_DATA = None
gemini_model = None
llm_response_cache = {}
ip_request_timestamps = {}
api_otp_store = {}


# --- FIX v100.9: Add CORS headers to non-preflight requests, respecting the feature flag ---
@app.after_request
def after_request(response):
    if app.config['ENABLE_WIDGET_MODE']:
        if ENABLE_SECURE_CORS_POLICY:
            origin = request.headers.get('Origin')
            if origin in ALLOWED_ORIGINS:
                response.headers['Access-Control-Allow-Origin'] = origin
        else:
            # Insecure mode for testing
            response.headers['Access-Control-Allow-Origin'] = '*'

        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS, PUT, DELETE'
    return response

# --- Token Helper Functions (for Widget Mode) ---
def generate_token(profile_hash, is_guest=False, expires_in_minutes=None, additional_claims=None):
    if expires_in_minutes:
        expiry = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    else:
        expiry = datetime.now(timezone.utc) + timedelta(days=90 if not is_guest else 1)
    
    payload = {'sub': profile_hash, 'is_guest': is_guest, 'iat': datetime.now(timezone.utc), 'exp': expiry}
    if additional_claims:
        payload.update(additional_claims)
        
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def decode_token(token):
    try:
        return jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization token is missing or invalid!'}), 401
        
        token = auth_header.split(" ")[1]
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': 'Token is invalid or expired!'}), 401
        
        # NEW in v103.0: Check if it's a special-purpose token
        if payload.get('purpose') == 'onboarding':
            g.profile_hash = payload['sub']
            g.onboarding_data = payload.get('onboarding_data', {})
            g.is_onboarding_token = True
            g.profile = None # No full profile exists yet
            g.is_guest = False
        else:
            g.is_onboarding_token = False
            g.profile_hash = payload['sub']
            g.is_guest = payload.get('is_guest', False)
            g.profile = None if g.is_guest else load_profile(g.profile_hash)
            if not g.is_guest and not g.profile:
                return jsonify({'error': 'Profile associated with this token not found.'}), 404
            
        return f(*args, **kwargs)
    return decorated_function

# --- FIX v100.9: Handle CORS Preflight & Throttling, respecting the feature flag ---
@app.before_request
def before_request_handler():
    # 1. Handle CORS Preflight (OPTIONS) requests
    if request.method.upper() == 'OPTIONS':
        resp = Response(status=200)

        if ENABLE_SECURE_CORS_POLICY:
            origin = request.headers.get('Origin')
            if origin in ALLOWED_ORIGINS:
                resp.headers['Access-Control-Allow-Origin'] = origin
        else:
            # Insecure mode for testing
            resp.headers['Access-Control-Allow-Origin'] = '*'

        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS, PUT, DELETE'

        return resp

    # 2. Handle Throttling for all other (non-OPTIONS) requests
    if not ENABLE_REQUEST_THROTTLING:
        return

    ip = request.remote_addr
    now = time.time()
    timestamps = ip_request_timestamps.get(ip, [])
    # Filter timestamps to only include those within the throttling period
    recent_timestamps = [t for t in timestamps if now - t < THROTTLE_PERIOD_SECONDS]
    
    if len(recent_timestamps) >= THROTTLE_LIMIT:
        return jsonify({"error": "Too many requests. Please wait a moment."}), 429
        
    recent_timestamps.append(now)
    ip_request_timestamps[ip] = recent_timestamps


# --- NEW: OTP Email Helper ---
def send_otp_email(to_email, otp):
    # BUG FIX v94.5: Use app.config which is now the reliable source
    sendgrid_api_key = app.config.get("SENDGRID_API_KEY")
    sender_email = app.config.get("SENDER_EMAIL")
    
    if not sendgrid_api_key or not sender_email:
        print("!!! CRITICAL ERROR: SendGrid API Key or Sender Email not configured in app.config.")
        return False
    
    message = Mail(
        from_email=sender_email,
        to_emails=to_email,
        subject='Your Tyra Verification Code',
        html_content=f'<strong>Your one-time verification code is: {otp}</strong><br>This code will expire in 5 minutes.'
    )
    try:
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        print(f"!!! SendGrid Error: {e}")
        return False

# --- All original helper functions ---
def load_report_db():
    if not os.path.exists(SHARED_REPORTS_DB_FILE): return {}
    try:
        with open(SHARED_REPORTS_DB_FILE, 'r') as f: return json.load(f)
    except json.JSONDecodeError: return {}

def save_report_db(db):
    with open(SHARED_REPORTS_DB_FILE, 'w') as f: json.dump(db, f, indent=4)

def cleanup_expired_reports():
    if not os.path.exists(SHARED_REPORTS_DB_FILE): return
    db, now = load_report_db(), datetime.now().timestamp()
    expired_ids = [k for k, v in db.items() if now - v.get('created_at', 0) > REPORT_LIFETIME_HOURS * 3600]
    if expired_ids:
        for report_id in expired_ids:
            del db[report_id]
            # Use os.path.basename to get just the filename for the send_from_directory path
            filepath = os.path.join(SHARED_REPORTS_DIR, f"{report_id}.pdf")
            if os.path.exists(filepath): os.remove(filepath)
        save_report_db(db)

def load_language_data(lang_code='en'):
    lang_file = os.path.join(LOCALES_DIR, f"{lang_code}.json")
    fallback_file = os.path.join(LOCALES_DIR, 'en.json')
    file_to_load = lang_file if os.path.exists(lang_file) else fallback_file
    if not os.path.exists(file_to_load): return {}
    try:
        with open(file_to_load, 'r', encoding='utf-8') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return {}

def configure_ai():
    global gemini_model
    try:
        # BUG FIX v94.5: Use app.config which is now the reliable source
        gemini_api_key = app.config.get("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in configuration.")
        genai.configure(api_key=gemini_api_key)
        gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    except Exception as e:
        gemini_model = None
        print(f"!!! CRITICAL ERROR: Failed to configure Google AI. Error: {e}")

def load_tribher_data():
    global TRIBHER_DATA
    try:
        with open(TRIBHER_DATA_FILE, 'r') as f: TRIBHER_DATA = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): TRIBHER_DATA = None

def load_milestones_data():
    global MILESTONES_DATA
    try:
        with open(MILESTONES_DATA_FILE, 'r') as f: MILESTONES_DATA = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): MILESTONES_DATA = None

load_tribher_data()
load_milestones_data()
configure_ai()
md = MarkdownIt()

def wait_for_file_to_be_active(file_name, timeout_seconds=120):
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            file_info = genai.get_file(name=file_name)
            if file_info.state.name == "ACTIVE": return True
            if file_info.state.name == "FAILED": return False
        except Exception: pass
        time.sleep(2)
    return False

def normalize_date_string(date_str: str) -> str:
    if not date_str: return datetime.now().strftime("%Y-%m-%d")
    parsed_date = dateparser.parse(date_str, settings={'PREFER_DATES_FROM': 'past'})
    return parsed_date.strftime("%Y-%m-%d") if parsed_date else datetime.now().strftime("%Y-%m-%d")

def get_conversation_summary(user_message):
    today_date = datetime.now().strftime('%Y-%m-%d')
    # FIX v95.8: Added new example to handle "period length" synonym for "cycle length"
    # FIX v98.7: Restored contextual reminder logic
    summary_prompt = f"""
You are an expert tool for converting natural language into a structured JSON object.
Your output MUST be a single, raw, valid JSON object.
Today's date is {today_date}. Resolve all relative dates to 'YYYY-MM-DD' format.

**CRITICAL RULES & INTENTS:**
1.  **CHARTING OVERRIDE:** This is your highest priority. If the message contains 'chart', 'calendar', 'graph', or 'visualize', you MUST return a `query_chart` intent.
2.  **SET GOAL:** For phrases like "my goal is..." or "I want to start...", return a `set_goal` intent with the full goal text.
3.  **MEDICATION LOG:** For phrases about taking or logging medicine, return `medication_log` with `name`, `dosage`, and `frequency`.
4.  **REMINDERS (EXPLICIT):** For command-like phrases ("remind me to", "set a reminder"), return `reminder_action` with the `text` and `due_date`.
5.  **REMINDERS (CONTEXTUAL):** For future events mentioned conversationally (e.g., "I have an appointment on Friday"), return `potential_reminder` with `text` and `date`.
6.  **OTHER ACTIONS:** Process `health_log`, `period_action`, or `ambiguous_log` as normal.
7.  **GENERAL CHAT:** For anything else, return an empty JSON object `{{}}`.

--- EXAMPLES ---
User: 'my period started on july 1st'
{{"period_action": {{"type": "log_period_start", "date": "{datetime.now().year}-07-01"}}}}

User: 'visualize my cycle length'
{{"query_chart": {{"type": "cycle_length"}}}}

User: 'graph my period length over the last few months'
{{"query_chart": {{"type": "cycle_length"}}}}

User: 'show my period calendar for june month'
{{"query_chart": {{"type": "cycle_calendar", "target_date": "{datetime.now().year}-06-01"}}}}

User: 'Remind me to call the doctor tomorrow.'
{{"reminder_action": {{"text": "call the doctor", "due_date": "{(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}"}}}}

User: 'My follow-up appointment is next Tuesday.'
{{"potential_reminder": {{"text": "follow-up appointment", "date": "{(datetime.now() + timedelta(days=(8 - datetime.now().isoweekday() + 1) % 7)).strftime('%Y-%m-%d')}" }}}}

User: 'Log that I am taking Vitamin D 500mg daily.'
{{"medication_log": {{"name": "Vitamin D", "dosage": "500mg", "frequency": "daily"}}}}

User: 'My goal is to exercise 3 times a week.'
{{"set_goal": {{"text": "exercise 3 times a week"}}}}
--- END EXAMPLES ---

Now, process this user message:
'{user_message}'
"""
    response = None
    try:
        if not gemini_model: raise Exception("Gemini model is not configured.")
        response = gemini_model.generate_content(summary_prompt)
        cleaned_response = response.text.strip().lstrip("```json").rstrip("```").strip()
        return json.loads(cleaned_response)
    except json.JSONDecodeError as e:
        print(f"!!! JSONDecodeError during summarization: {e}")
        if response: print(f"Faulty AI response from model: {response.text}")
        return {"error": "json_parse_failed"}
    except Exception as e:
        print(f"Error during summarization: {e}")
        return {"error": "unknown_summarization_error"}

def get_holistic_report_summary_prompt(user_query, extracted_text):
    return (
        "You are an AI assistant specializing in summarizing medical lab reports for patients in an easy-to-understand way.\n"
        "You will be given the full text extracted from a lab report and a user's question.\n\n"
        "--- YOUR TASK ---\n"
        "Your goal is to provide a holistic summary of the report's key findings. You must connect the test results with the reference ranges and interpretation tables provided *within the report itself*.\n\n"
        "--- STEP-BY-STEP INSTRUCTIONS ---\n"
        "1. Go through the report section by section (e.g., Biochemistry, Lipid Profile).\n"
        "2. For each significant test, state the result clearly.\n"
        "3. Compare the result to the provided 'Bio. Ref. Interval' or any interpretation tables (like for glucose or cholesterol).\n"
        "4. State how the result compares to the reference (e.g., 'within the normal range', 'above the reference interval', 'in the prediabetes range as defined by the report').\n"
        "5. Structure your response with clear markdown headings for each section (e.g., `### Blood Sugar (Glucose)`, `### Cholesterol / Lipid Profile`).\n"
        "6. Keep the tone informative and neutral.\n\n"
        "--- STRICT SAFETY RULES ---\n"
        "- **DO NOT** provide a diagnosis. Instead of saying 'You have prediabetes', say 'The report indicates a fasting glucose level in the 'Prediabetes' range'.\n"
        "- **DO NOT** give medical advice (e.g., 'you should eat less sugar' or 'you need to take medication').\n"
        "- **DO NOT** speculate on the causes or recommend treatments.\n"
        "- Base your entire summary **ONLY** on the information and tables present in the provided text. Do not use external knowledge to interpret values.\n"
        "- If a value is outside the reference range, simply state that it is 'higher than' or 'lower than' the reference interval.\n"
        "- Always conclude your summary by strongly recommending the user discuss the results with their healthcare provider.\n\n"
        "--- USER REQUEST ---\n"
        f"User's Question: \"{user_query}\"\n"
        f"Extracted Document Text:\n---\n{extracted_text}\n---"
    )

# --- FIX v98.4: Corrected prompt to prevent instruction leakage ---
def get_visual_triage_prompt(user_query, image_file):
    return [
        "You are a Cautious Health Information Assistant. Your task is to analyze a user's image of a physical symptom and generate a helpful, safe, and non-diagnostic response formatted in Markdown. \n\n"
        "--- RESPONSE STRUCTURE ---\n"
        "Your final output MUST be structured with the following user-facing Markdown headings. Do NOT include the internal step names (like 'INTERNAL STEP 1') in your response.\n"
        "1. `### Visual Description`\n"
        "2. `### General Information`\n"
        "3. `### What to Monitor`\n"
        "4. `### When to Seek Immediate Care`\n\n"
        "--- INTERNAL INSTRUCTIONS ---\n"
        "**INTERNAL STEP 1: Describe the Image Objectively.**\n"
        "Under the `### Visual Description` heading, describe the visual characteristics of the image in neutral, factual terms. AVOID medical jargon.\n"
        "Good examples: 'The image shows an area of skin with red patches.', 'I can see small, raised bumps in the photo.'\n"
        "Bad example: 'The patient presents with erythematous papules.'\n\n"
        "**INTERNAL STEP 2: Provide General Educational Information.**\n"
        "Under the `### General Information` heading, provide a brief, general overview of common *categories* of skin conditions. DO NOT suggest the user's image belongs to any of these categories. This section is for general knowledge only.\n"
        "Example: 'In general, skin issues can arise from many sources. Some common categories include inflammatory conditions (like eczema or psoriasis), allergic reactions (like hives), and infections...'\n\n"
        "**INTERNAL STEP 3: Guide the User on What to Monitor.**\n"
        "Under the `### What to Monitor` heading, provide a clear, bulleted list of symptoms or changes the user should pay attention to.\n"
        "Example: 'When you speak with a doctor, it is helpful to provide them with information such as:\\n*   When did it first appear?\\n*   Is it itchy, painful, or burning?...'\n\n"
        "**INTERNAL STEP 4: State Clear 'Red Flag' Conditions.**\n"
        "Under the `### When to Seek Immediate Care` heading, provide a clear, bolded list of 'red flag' symptoms that warrant seeking immediate medical attention.\n"
        "Example: '**Please seek immediate medical attention if you experience any of the following:**\\n*   The rash is accompanied by a fever.\\n*   You have difficulty breathing...'\n\n"
        "--- CRITICAL SAFETY OVERRIDE ---\n"
        "**NEVER, EVER:**\n"
        "- **Name a specific condition** for the user's image (e.g., 'This looks like psoriasis').\n"
        "- **Suggest any treatments,** including over-the-counter creams or home remedies.\n"
        "- **Minimize the situation** (e.g., 'It's probably nothing to worry about.').\n\n"
        f"--- USER'S QUESTION ---\n"
        f"'{user_query}'\n\n"
        "Now, analyze the following image and generate the response based on these instructions:",
        image_file
    ]

def analyze_general_correlations(profile):
    if not ENABLE_EXPANDED_LOGGING: return None
    today_str = datetime.now().strftime('%Y-%m-%d')
    proactive_data = profile.get("proactive_assistance", {})
    if proactive_data.get("last_general_analysis_date") == today_str: return None
    health_logs = profile.get("health_logs", [])
    if len(health_logs) < 4: return None
    proactive_data["last_general_analysis_date"] = today_str
    recent_logs = health_logs[:20]
    stress_days = {dateparser.parse(log['timestamp']).date() for log in recent_logs if log.get('category') == 'stress' and log.get('value') == 'high'}
    correlation_count = 0
    for log in recent_logs:
        if log.get('category') == 'sleep' and log.get('value') in ['poor', 'terrible']:
            log_date = dateparser.parse(log['timestamp']).date()
            if log_date in stress_days or (log_date - timedelta(days=1)) in stress_days:
                correlation_count += 1
    if correlation_count >= 2:
        return {"type": "symptom_correlation", "text": "I've noticed a potential link: on days you've reported high stress, your sleep quality sometimes seems to be lower."}
    return None

def analyze_symptom_correlations(profile):
    if not ENABLE_EXPANDED_LOGGING: return None
    today_str = datetime.now().strftime('%Y-%m-%d')
    proactive_data = profile.get("proactive_assistance", {})
    if proactive_data.get("last_symptom_analysis_date") == today_str: return None
    cycles = profile.get("period_data", {}).get("cycles", [])
    history = profile.get("conversation_history", [])
    if len(cycles) < 3 or len(history) < 5: return None
    proactive_data["last_symptom_analysis_date"] = today_str
    cycle_start_dates = {datetime.strptime(c['start_date'], '%Y-%m-%d').date() for c in cycles if 'start_date' in c}
    symptom_counts = defaultdict(int)
    symptom_to_cycle_map = defaultdict(set)
    for entry in history:
        insights = entry.get("insights", {})
        symptoms = insights.get("health_symptoms", []) + insights.get("mood_log", [])
        if not symptoms: continue
        try: entry_date = datetime.fromisoformat(entry['timestamp']).date()
        except (ValueError, TypeError): continue
        for cycle_date in cycle_start_dates:
            days_before = (cycle_date - entry_date).days
            if 1 <= days_before <= 3:
                for symptom in symptoms:
                    if cycle_date not in symptom_to_cycle_map[symptom]:
                        symptom_counts[symptom] += 1
                        symptom_to_cycle_map[symptom].add(cycle_date)
    correlated_symptoms = [s for s, count in symptom_counts.items() if count >= 3]
    if not correlated_symptoms: return None
    symptom_str = ", ".join([f"'{s}'" for s in correlated_symptoms])
    return f"By the way, I've noticed a pattern. It looks like you've mentioned feeling {symptom_str} a day or two before your last few periods."

def handle_milestone_query(action, profile):
    if not MILESTONES_DATA: return profile, "I'm sorry, my milestone information isn't available right now.", None
    details = profile.get("secondary_details", {})
    if not details.get("is_pregnant"): return profile, "It looks like you're not tracking a pregnancy with me right now.", None
    weeks = details.get("weeks_gestation")
    if not weeks: return profile, "I can't seem to find your current week of gestation.", None
    pregnancy_milestones = MILESTONES_DATA.get("pregnancy_by_week", {})
    milestone_text = pregnancy_milestones.get(str(weeks), pregnancy_milestones.get("default"))
    if milestone_text:
        response = f"Of course! At {weeks} weeks pregnant, here's a typical milestone: {milestone_text}"
    else:
        response = f"I don't have a specific milestone recorded for week {weeks}."
    return profile, response, None

def handle_delete_reminder(action, profile):
    if not ENABLE_PROACTIVE_ASSISTANCE: return profile, "Reminder feature is disabled.", None
    text_to_delete = action.get('text', '').lower().strip()
    reminders = profile.get("proactive_assistance", {}).get("reminders", [])
    if not reminders: return profile, "You don't have any reminders to delete.", None
    
    match_to_delete = next((r for r in reminders if text_to_delete in r.get('text', '').lower()), None)
    if match_to_delete:
        reminders[:] = [r for r in reminders if r.get('id') != match_to_delete.get('id')]
        return profile, f"Okay, I've deleted the reminder: '{match_to_delete['text']}'.", None
    else:
        return profile, f"I couldn't find a reminder that sounds like '{action.get('text')}'.", None

def handle_reminder_action(action, profile):
    if not ENABLE_PROACTIVE_ASSISTANCE: return profile, "Reminder feature is disabled.", None
    profile.setdefault("proactive_assistance", {}).setdefault("reminders", [])
    reminders = profile["proactive_assistance"]["reminders"]
    text = action.get('text')
    if not text: return profile, "I didn't quite catch what to remind you of.", None
    if any(r.get('text').lower() == text.lower() for r in reminders):
        return profile, f"You already have a reminder for '{text}'.", None
    new_reminder = { "id": f"rem_{int(time.time())}", "text": text, "start_date": action.get("due_date", datetime.now().strftime("%Y-%m-%d")), "recurrence_rule": {"frequency": "once"} }
    reminders.insert(0, new_reminder) # FIX v100.0: Use insert(0) for newest-first
    return profile, f"Okay, I've set a reminder for: '{text}'.", None

def handle_medication_log(action, profile):
    if not ENABLE_MEDICATION_TRACKING: return profile, "Medication tracking is disabled.", None
    profile.setdefault("medication_log", [])
    name = action.get("name")
    if not name: return profile, "I didn't catch the name of the medication. Could you please tell me again?", None
    dosage = action.get("dosage", "N/A")
    frequency = action.get("frequency", "as needed")
    new_med = {"name": name, "dosage": dosage, "frequency": frequency, "logged_date": datetime.now().isoformat()}
    profile["medication_log"].insert(0, new_med) # FIX v100.0: Use insert(0) for newest-first
    reminder_text = f"Take {name} ({dosage})"
    reminder_action = {"text": reminder_text}
    if "daily" in frequency.lower() or "every morning" in frequency.lower():
        reminder_action["recurrence_rule"] = {"frequency": "daily", "interval": 1}
    profile, reminder_response, _ = handle_reminder_action(reminder_action, profile)
    return profile, f"Okay, I've logged that you're taking **{name} ({dosage})**. {reminder_response}", None

def handle_set_goal(action, profile):
    if not ENABLE_GOAL_TRACKING: return profile, "Goal tracking is disabled.", None
    profile.setdefault("goals", [])
    goal_text = action.get("text")
    if not goal_text: return profile, "I didn't quite catch that goal.", None
    if any(g.get('text', '').lower() == goal_text.lower() for g in profile["goals"]):
        return profile, f"It looks like you already have a goal to '{goal_text}'.", None
    new_goal = {"text": goal_text, "created_date": datetime.now().strftime("%Y-%m-%d"), "last_check_in_date": datetime.now().strftime("%Y-%m-%d")}
    profile["goals"].insert(0, new_goal) # FIX v100.0: Use insert(0) for newest-first
    return profile, f"That's a great goal! I've saved it for you: **'{goal_text}'**.", None

def handle_period_action(action, profile):
    if not ENABLE_PERIOD_TRACKER: return profile, None, None
    lang_data = load_language_data(profile.get('language', 'en'))
    action_type = action.get('type')
    if not action_type and action.get('date'):
        action_type = 'log_period_start'
    if "period_data" not in profile: profile["period_data"] = {"cycles": []}
    response_message, pending_question_state = "", None

    if action_type == 'clarify_period_start':
        response_message = lang_data.get('ask_period_start_date')
        pending_question_state = 'log_period_start'
    elif action_type == 'enable_tracking':
        profile["period_data"]["tracking_enabled"] = True
        profile["period_data"]["has_been_offered_tracking"] = True
        response_message = lang_data.get('period_tracking_enabled')
        pending_question_state = 'log_period_start'
    elif action_type == 'disable_tracking':
        profile["period_data"]["tracking_enabled"] = False
        response_message = lang_data.get('period_tracking_disabled')
    elif action_type == 'log_period_start':
        profile.setdefault("period_data", {})["tracking_enabled"] = True
        profile["period_data"]["has_been_offered_tracking"] = True
        date_str = normalize_date_string(action.get('date'))
        if not any(c.get('start_date') == date_str for c in profile["period_data"].get("cycles", [])):
            profile["period_data"].setdefault("cycles", []).insert(0, {"start_date": date_str})
            profile = update_and_predict_cycles(profile, enable_ovulation_tracker=ENABLE_OVULATION_TRACKER)
            avg_length = profile.get("period_data", {}).get("average_period_length")
            if avg_length and avg_length > 0:
                start_date = datetime.strptime(date_str, "%Y-%m-%d")
                predicted_end = start_date + timedelta(days=avg_length - 1)
                response_message = lang_data.get('period_log_start_confirm_predict_end').format(start_date=date_str, end_date=predicted_end.strftime('%Y-%m-%d'))
            else:
                response_message = lang_data.get('period_log_start_confirm').format(date=date_str)
            pending_question_state = 'log_period_end'
        else:
            response_message = lang_data.get('period_already_exists').format(date=date_str)
    elif action_type == 'log_period_end':
        date_str = normalize_date_string(action.get('date'))
        active_cycle = next((c for c in profile["period_data"].get("cycles", []) if 'end_date' not in c), None)
        if active_cycle:
            active_cycle['end_date'] = date_str
            start_d = datetime.strptime(active_cycle['start_date'], "%Y-%m-%d")
            end_d = datetime.strptime(date_str, "%Y-%m-%d")
            active_cycle['period_length'] = (end_d - start_d).days + 1
            profile = update_and_predict_cycles(profile, enable_ovulation_tracker=ENABLE_OVULATION_TRACKER)
            response_message = lang_data.get('period_log_end_confirm').format(date=date_str)
            pending_question_state = 'log_symptoms_or_flow'
        else:
            response_message = lang_data.get('period_no_active_cycle')
    elif action_type == 'log_symptoms' or action_type == 'log_flow':
        active_cycle = profile["period_data"]["cycles"][0] if profile["period_data"].get("cycles") else None
        if active_cycle:
            if 'symptoms' in action:
                symptom_list_str = ', '.join(action['symptoms'])
                active_cycle.setdefault('symptoms', []).extend(action['symptoms'])
                response_message = lang_data.get('period_symptoms_added').format(symptoms=symptom_list_str)
            if 'flow' in action:
                active_cycle['flow'] = action['flow']
                response_message = lang_data.get('period_flow_added').format(flow=action['flow'])
        else:
            response_message = lang_data.get('period_log_first')
    elif action_type == 'predict_period':
        predicted_date = profile.get("period_data", {}).get("predicted_next_start_date")
        if predicted_date:
            response_message = lang_data.get('period_predict_next').format(date=predicted_date)
        else:
            response_message = lang_data.get('period_predict_not_enough_data')
    return profile, response_message, pending_question_state

def is_reminder_due(reminder, check_date_dt):
    if not ENABLE_CUSTOM_REMINDERS:
        due_date_str = reminder.get('due_date')
        return due_date_str == check_date_dt.strftime('%Y-%m-%d')
    rule = reminder.get('recurrence_rule', {})
    frequency = rule.get('frequency')
    start_date_dt = datetime.strptime(reminder.get('start_date'), '%Y-%m-%d')
    if check_date_dt.date() < start_date_dt.date():
        return False
    if frequency == 'once':
        return start_date_dt.date() == check_date_dt.date()
    if frequency == 'daily':
        interval = rule.get('interval', 1)
        delta_days = (check_date_dt.date() - start_date_dt.date()).days
        return delta_days >= 0 and delta_days % interval == 0
    return False

def get_proactive_context(profile):
    if not ENABLE_PROACTIVE_ASSISTANCE: return None
    today_dt = datetime.now()
    today_str = today_dt.strftime('%Y-%m-%d')
    proactive_data = profile.get("proactive_assistance", {})
    if ENABLE_CUSTOM_REMINDERS:
        for reminder in proactive_data.get("reminders", []):
            if reminder.get("last_triggered_date") == today_str: continue
            if is_reminder_due(reminder, today_dt):
                reminder["last_triggered_date"] = today_str
                return {"type": "reminder", "text": reminder["text"]}
    if ENABLE_GOAL_TRACKING:
        for goal in profile.get("goals", []):
            if goal.get("last_check_in_date"):
                last_check_in_dt = datetime.strptime(goal.get("last_check_in_date"), "%Y-%m-%d")
                if (today_dt - last_check_in_dt).days >= GOAL_CHECK_IN_DAYS:
                    goal["last_check_in_date"] = today_str
                    return {"type": "goal_check_in", "text": goal.get("text")}
    return None

def update_and_predict_cycles(profile, enable_ovulation_tracker=False):
    if "period_data" not in profile or "cycles" not in profile["period_data"]: return profile
    
    period_data = profile["period_data"]
    cycles = period_data.get("cycles", [])
    
    for key in ['predicted_next_start_date', 'predicted_ovulation_date', 'predicted_fertile_start', 'predicted_fertile_end']:
        period_data.pop(key, None)

    valid_cycles = [c for c in cycles if c.get('start_date') and isinstance(c['start_date'], str)]
    valid_cycles.sort(key=lambda x: x['start_date'], reverse=True)
    
    for i in range(len(valid_cycles) - 1):
        try:
            start_current = datetime.strptime(valid_cycles[i]['start_date'], "%Y-%m-%d")
            start_previous = datetime.strptime(valid_cycles[i+1]['start_date'], "%Y-%m-%d")
            valid_cycles[i]['cycle_length'] = (start_current - start_previous).days
        except (ValueError, KeyError):
            continue

    if not valid_cycles:
        return profile

    typical_cycle_lengths = [c.get('cycle_length') for c in valid_cycles if c.get('cycle_length') and 20 < c.get('cycle_length') < 45]
    avg_cycle_length = sum(typical_cycle_lengths) // len(typical_cycle_lengths) if typical_cycle_lengths else 28
    
    period_lengths = [c.get('period_length', 0) for c in valid_cycles if c.get('period_length')]
    avg_period_length = sum(period_lengths) // len(period_lengths) if period_lengths else 5
    
    period_data["average_cycle_length"] = avg_cycle_length
    period_data["average_period_length"] = avg_period_length

    if enable_ovulation_tracker:
        for cycle in valid_cycles:
            try:
                cycle_len = cycle.get('cycle_length', avg_cycle_length)
                start_dt = datetime.strptime(cycle['start_date'], "%Y-%m-%d")
                
                next_period_start_dt = start_dt + timedelta(days=cycle_len)
                ovulation_dt = next_period_start_dt - timedelta(days=14)
                
                cycle["ovulation_date"] = ovulation_dt.strftime("%Y-%m-%d")
                cycle["fertile_start"] = (ovulation_dt - timedelta(days=5)).strftime("%Y-%m-%d")
                cycle["fertile_end"] = (ovulation_dt + timedelta(days=1)).strftime("%Y-%m-%d")
            except (ValueError, KeyError):
                continue

    most_recent_start = datetime.strptime(valid_cycles[0]['start_date'], "%Y-%m-%d")
    predicted_date = most_recent_start + timedelta(days=avg_cycle_length)
    period_data["predicted_next_start_date"] = predicted_date.strftime("%Y-%m-%d")
    
    if enable_ovulation_tracker:
        predicted_ovulation_dt = predicted_date - timedelta(days=14)
        period_data["predicted_ovulation_date"] = predicted_ovulation_dt.strftime("%Y-%m-%d")
        period_data["predicted_fertile_start"] = (predicted_ovulation_dt - timedelta(days=5)).strftime("%Y-%m-%d")
        period_data["predicted_fertile_end"] = (predicted_ovulation_dt + timedelta(days=1)).strftime("%Y-%m-%d")

    period_data["cycles"] = valid_cycles[:MAX_CYCLE_HISTORY]
    return profile

# --- BUG FIX v97.1 & v97.5: Overhauled suggestion and follow-up logic ---

def handle_follow_up_request(profile, user_message):
    """
    Checks if the user is affirmatively responding to a pending program offer.
    Uses the persistent profile for state, not the session.
    """
    proactive_assistance = profile.get("proactive_assistance", {})
    pending_offer = proactive_assistance.get("pending_program_offer")
    
    if not pending_offer:
        return None, profile # No offer is pending

    affirmative_keywords = ['yes', 'tell me more', 'sure', 'ok', 'okay', 'please do', 'more about it', 'more about tribher', 'about the program']
    
    # Check if any part of the affirmative keywords list matches the user message
    if any(keyword in user_message.lower() for keyword in affirmative_keywords):
        # Clear the pending offer to prevent re-triggering
        proactive_assistance["pending_program_offer"] = None
        # Return the program object to be described
        return next((p for p in TRIBHER_DATA["programs"] if p["name"] == pending_offer), None), profile
    
    # If the user says something else, clear the pending offer so we don't get stuck
    proactive_assistance["pending_program_offer"] = None
    return None, profile

def get_program_suggestion(profile, user_message):
    """
    Finds a program suggestion ONLY if relevant keywords are in the user's message
    AND the cooldown period has passed (with exceptions for direct questions).
    """
    if not TRIBHER_DATA or not ENABLE_TRIBHER_SUGGESTIONS:
        return None

    proactive_assistance = profile.get("proactive_assistance", {})
    
    # 1. Keyword-driven matching (more opportunistic)
    KEYWORD_TO_PROGRAM_NAME = {
        "exercise": "Postnatal / Post Pregnancy Programs", "lose weight": "Postnatal / Post Pregnancy Programs",
        "preconception": "Pre-conception Programs", "conceive": "Pre-conception Programs", "fertility": "Pre-conception Programs",
        "prenatal": "Prenatal / Pregnancy Programs", "pregnant": "Prenatal / Pregnancy Programs", "pregnancy": "Prenatal / Pregnancy Programs", "expecting": "Prenatal / Pregnancy Programs",
        "postnatal": "Postnatal / Post Pregnancy Programs", "postpartum": "Postnatal / Post Pregnancy Programs", "mummy tummy": "Postnatal / Post Pregnancy Programs", "diastasis recti": "Postnatal / Post Pregnancy Programs",
        "menopause": "StrongHer 40+ Programs", "perimenopause": "StrongHer 40+ Programs", "over 40": "StrongHer 40+ Programs"
    }
    
    found_program_name = None
    for keyword, program_name in KEYWORD_TO_PROGRAM_NAME.items():
        if keyword in user_message.lower():
            found_program_name = program_name
            break

    if not found_program_name:
        return None

    # 2. Cooldown Check (with an exception for direct questions)
    is_direct_question = any(q_word in user_message.lower() for q_word in ["what is", "explain", "tell me about"])
    
    last_suggestion_ts = proactive_assistance.get("last_program_suggestion_ts")
    if last_suggestion_ts and not is_direct_question:
        last_suggestion_dt = datetime.fromisoformat(last_suggestion_ts)
        if (datetime.now(timezone.utc) - last_suggestion_dt).days < PROGRAM_SUGGESTION_COOLDOWN_DAYS:
            return None # Still in cooldown period and not a direct question

    return next((p for p in TRIBHER_DATA.get("programs", []) if p.get("name") == found_program_name), None)

def calculate_trimester(profile):
    details = profile.get("secondary_details", {})
    lmp_str = details.get("lmp_date")
    if not lmp_str or not details.get("is_pregnant"): return False
    try:
        lmp_date = datetime.strptime(lmp_str, "%Y-%m-%d")
        weeks_gestation = (datetime.now() - lmp_date).days // 7
        trimester = "TR1" if weeks_gestation <= 13 else "TR2" if 14 <= weeks_gestation <= 27 else "TR3"
        if details.get("weeks_gestation") != weeks_gestation or details.get("current_trimester") != trimester:
            details["weeks_gestation"], details["current_trimester"] = weeks_gestation, trimester
            return True
    except (ValueError, TypeError): return False
    return False

def calculate_child_ages(profile):
    details = profile.get("secondary_details", {})
    dob_list = details.get("child_dobs")
    if not dob_list: return
    now = datetime.now(); calculated_ages = []
    for dob_str in dob_list:
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d")
            total_months = (now.year - dob.year) * 12 + now.month - dob.month - (1 if now.day < dob.day else 0)
            calculated_ages.append({"years": total_months // 12, "months": total_months % 12})
        except ValueError: continue
    details['calculated_child_ages'] = calculated_ages
    if calculated_ages:
        min_total_months = min((age['years'] * 12 + age['months'] for age in calculated_ages))
        details['last_child_birth_ago'] = f"{min_total_months // 12} years, {min_total_months % 12} months"

def get_profile_hash(identifier): return hashlib.sha256(identifier.strip().lower().encode()).hexdigest()

# --- DATABASE/FILE DISPATCHER FUNCTIONS (v101.4) ---
def save_profile(profile_hash, data):
    """Dispatcher function to save a profile to the configured backend."""
    if ENABLE_SQLITE_DATABASE:
        user = User.query.filter_by(profile_hash=profile_hash).first()
        profile_as_string = json.dumps(data, indent=4)
        if user:
            user.profile_json = profile_as_string
        else:
            user = User(profile_hash=profile_hash, profile_json=profile_as_string)
            db.session.add(user)
        db.session.commit()
    else: # Fallback to JSON file storage
        with open(os.path.join(PROFILES_DIR, f"{profile_hash}.json"), 'w') as f:
            json.dump(data, f, indent=4)

def load_profile(profile_hash):
    """Dispatcher function to load a profile from the configured backend."""
    if ENABLE_SQLITE_DATABASE:
        user = User.query.filter_by(profile_hash=profile_hash).first()
        if user:
            return user.to_dict()
        return None
    else: # Fallback to JSON file storage
        filepath = os.path.join(PROFILES_DIR, f"{profile_hash}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return None
        return None

# --- NEW: BEHAVIORAL SYNOPSIS LOGIC ---
def _generate_behavioral_synopsis(profile):
    if not gemini_model: return None
    
    log = profile.get("interaction_log", [])[:100] # Analyze last 100 interactions
    if not log: return None

    intent_counts = defaultdict(int)
    entities = defaultdict(list)

    for entry in log:
        intent = entry.get("extracted_intent", {})
        if not intent: continue
        
        for key, value in intent.items():
            intent_counts[key] += 1
            if key == 'medication_log' and 'name' in value:
                entities['medications'].append(value['name'])
            if key == 'query_chart' and 'type' in value:
                 entities['charts'].append(value['type'])
            if key == 'set_goal' and 'text' in value:
                entities['goals'].append(value['text'])

    if not intent_counts: return None

    # Create a raw summary of actions
    analysis_lines = ["User Action Log Summary:"]
    for intent, count in intent_counts.items():
        analysis_lines.append(f"- Used '{intent}' {count} time(s).")
    
    if entities['medications']:
        analysis_lines.append(f"- Logged medications: {', '.join(list(set(entities['medications']))[:3])}.")
    if entities['charts']:
        analysis_lines.append(f"- Viewed charts: {', '.join(list(set(entities['charts']))[:3])}.")
    if entities['goals']:
        analysis_lines.append(f"- Set goals like: '{list(set(entities['goals']))[0]}'.")

    analysis_text = "\n".join(analysis_lines)
    
    synopsis_prompt = f"""
    You are a user behavior analyst. Based on the following summary of a user's actions, generate a concise, structured JSON list of 2-3 bullet points describing their primary focus and recent behavior. The tone should be neutral and factual.

    **Example Input:**
    User Action Log Summary:
    - Used 'period_action' 8 time(s).
    - Used 'query_chart' 4 time(s).
    - Viewed charts: cycle_calendar, cycle_length.

    **Example Output:**
    ```json
    [
        "Frequently uses period tracking features.",
        "Shows a strong interest in visualizing her cycle via the calendar and charts."
    ]
    ```

    ---
    **Now, analyze this user log:**
    {analysis_text}
    """
    
    try:
        response = gemini_model.generate_content(synopsis_prompt)
        cleaned_response = response.text.strip().lstrip("```json").rstrip("```").strip()
        synopsis = json.loads(cleaned_response)
        return synopsis if isinstance(synopsis, list) else None
    except Exception as e:
        print(f"!!! Could not generate behavioral synopsis: {e}")
        return None

def _update_synopsis_if_needed(profile):
    if not ENABLE_BEHAVIORAL_SYNOPSIS: return profile

    synopsis_data = profile.get("behavioral_synopsis", {})
    interaction_log = profile.get("interaction_log", [])
    
    last_gen_str = synopsis_data.get("generated_at")
    last_interaction_count = synopsis_data.get("last_interaction_count", 0)
    
    needs_update = False
    
    # Condition 1: Time-based update
    if last_gen_str:
        last_gen_dt = datetime.fromisoformat(last_gen_str)
        if (datetime.now(timezone.utc) - last_gen_dt).days >= BEHAVIORAL_SYNOPSIS_INTERVAL_DAYS:
            needs_update = True
    else: # No synopsis exists yet
        needs_update = True
        
    # Condition 2: Interaction-count-based update
    if len(interaction_log) - last_interaction_count >= BEHAVIORAL_SYNOPSIS_MIN_INTERACTIONS:
        needs_update = True

    if needs_update and len(interaction_log) > 0:
        print("--- Generating new behavioral synopsis ---")
        new_synopsis = _generate_behavioral_synopsis(profile)
        if new_synopsis:
            profile["behavioral_synopsis"] = {
                "synopsis": new_synopsis,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "last_interaction_count": len(interaction_log)
            }
            
    return profile

# --- SHARED BUSINESS LOGIC HELPERS ---

# Refactored logic to be callable by both monolith and API
def _handle_upload_logic(file, user_query):
    if not file or not gemini_model:
        return {'error': 'Server not configured for uploads'}, 500
    
    temp_path, uploaded_file = None, None
    try:
        temp_path = os.path.join(UPLOADS_DIR, secure_filename(file.filename))
        file.save(temp_path)
        uploaded_file = genai.upload_file(path=temp_path, mime_type=file.mimetype)
        if not wait_for_file_to_be_active(uploaded_file.name):
            raise Exception("File processing timeout")
        
        final_prompt = None
        if file.mimetype.startswith('image/') and ENABLE_VISUAL_TRIAGE:
            final_prompt = get_visual_triage_prompt(user_query, uploaded_file)
        elif ENABLE_DOCUMENT_UPLOAD:
            ocr_response = gemini_model.generate_content(["Extract all text from this document.", uploaded_file])
            final_prompt = get_holistic_report_summary_prompt(user_query, ocr_response.text)
        else:
            return {'error': 'Unsupported file type or feature disabled'}, 400
        
        final_response = gemini_model.generate_content(final_prompt)
        return {"reply": md.render(final_response.text)}, 200
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        if temp_path and os.path.exists(temp_path): os.remove(temp_path)
        if uploaded_file:
            try: genai.delete_file(uploaded_file.name)
            except exceptions.NotFound: pass # File might already be gone


def _handle_transcription_logic(file):
    if not file or not gemini_model:
        return {'error': 'Server not configured for transcription'}, 500

    temp_path, uploaded_file = None, None
    try:
        temp_path = os.path.join(UPLOADS_DIR, "voice_note.webm")
        file.save(temp_path)
        uploaded_file = genai.upload_file(path=temp_path, mime_type="audio/webm")
        if not wait_for_file_to_be_active(uploaded_file.name):
            raise Exception("File processing timeout")
        response = gemini_model.generate_content(["Transcribe this audio.", uploaded_file])
        return {"transcribed_text": response.text.strip()}, 200
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        if temp_path and os.path.exists(temp_path): os.remove(temp_path)
        if uploaded_file:
            try: genai.delete_file(uploaded_file.name)
            except exceptions.NotFound: pass

def _handle_quick_log_logic(profile, category, value):
    profile.setdefault('health_logs', []).insert(0, {"timestamp": datetime.now().isoformat(), "category": category, "value": value})
    lang_data = load_language_data(profile.get('language', 'en'))
    confirmation_key = f"quick_log_confirm_{value.replace(' ', '_')}_{category}"
    response_message = lang_data.get(confirmation_key, lang_data.get("quick_log_confirm_fallback"))
    return {"reply": md.render(response_message)}

def _get_dashboard_data(profile):
    lang_code = profile.get('language', 'en') if ENABLE_MULTI_LANGUAGE else 'en'
    lang_data = load_language_data(lang_code)

    dashboard_data = {"name": profile.get("name", "User").split(" ")[0], "reminders": [], "cycle_stats": {}, "health_logs": [], "medications": [], "goals": []}
    
    if ENABLE_CUSTOM_REMINDERS:
        reminders, upcoming_reminders = profile.get("proactive_assistance", {}).get("reminders", []), []
        check_date = datetime.now()
        for _ in range(90):
            if len(upcoming_reminders) >= 5: break
            for r in reminders:
                if is_reminder_due(r, check_date) and not any(u['id'] == r.get('id') and u['date'] == check_date.strftime('%Y-%m-%d') for u in upcoming_reminders):
                    upcoming_reminders.append({"id": r.get('id'), "text": r['text'], "date": check_date.strftime('%Y-%m-%d')})
            check_date += timedelta(days=1)
        dashboard_data["reminders"] = upcoming_reminders

    if ENABLE_PERIOD_TRACKER:
        period_data = profile.get("period_data", {})
        if period_data.get("tracking_enabled"):
            today = datetime.now().date()
            if period_data.get("cycles"):
                last_start_str = period_data.get("cycles", [{}])[0].get("start_date")
                if last_start_str:
                    last_start_dt = datetime.strptime(last_start_str, "%Y-%m-%d").date()
                    dashboard_data["cycle_stats"]["current_day"] = (today - last_start_dt).days + 1
            dashboard_data["cycle_stats"]["predicted_next"] = period_data.get("predicted_next_start_date")
            dashboard_data["cycle_stats"]["avg_cycle_length"] = period_data.get("average_cycle_length")
    
    if ENABLE_EXPANDED_LOGGING:
        # Data is now stored newest-first, so sorting is no longer needed. Just slice.
        for log in profile.get("health_logs", [])[:5]:
            log_date = dateparser.parse(log['timestamp']).strftime('%b %d')
            category = log.get('category', 'log')
            value = log.get('value', 'entry')
            key = f"log_item_{category}"
            fallback_key = "log_item_default"
            template_str = lang_data.get(key, lang_data.get(fallback_key, "{date}: {value} {category}"))
            log_text = template_str.format(date=log_date, value=value, category=category)
            dashboard_data["health_logs"].append({"text": log_text})

    if ENABLE_MEDICATION_TRACKING: dashboard_data["medications"] = profile.get("medication_log", [])[:5]
    if ENABLE_GOAL_TRACKING: dashboard_data["goals"] = profile.get("goals", [])[:5]
    
    return dashboard_data

def _handle_profile_check_or_creation(data, is_api_call=False):
    identifier = data.get('identifier')
    if not is_api_call:
        if data.get('identifier'):
            session['login_identifier'] = data.get('identifier').strip()
        identifier = identifier or session.get('login_identifier')

    if not identifier: 
        return jsonify({"status": "error", "message": "Identifier is required."}), 400

    profile_hash = get_profile_hash(identifier)
    existing_profile = load_profile(profile_hash)
    if existing_profile:
        if is_api_call:
            token = generate_token(profile_hash)
            return jsonify({"status": "exists", "token": token, "name": existing_profile.get('name')})
        else:
            session.clear()
            session['profile_hash'] = profile_hash
            return jsonify({"status": "exists", "profile": existing_profile})

    name, age_str = data.get('name'), data.get('age')
    if name and age_str:
        try:
            phone = identifier if '@' not in identifier else ''
            primary_email = identifier if '@' in identifier else data.get('email', '')
            details = data.get('details', {})
            lang_code = data.get('language', 'en') if ENABLE_MULTI_LANGUAGE else 'en'
            
            new_profile = create_user_profile(name, primary_email, phone, int(age_str), details, lang_code)
            calculate_trimester(new_profile)
            calculate_child_ages(new_profile)
            save_profile(profile_hash, new_profile)

            if is_api_call:
                token = generate_token(profile_hash)
                return jsonify({"status": "created", "token": token, "name": new_profile.get('name')})
            else:
                session.clear()
                session['profile_hash'] = profile_hash
                session.pop('login_identifier', None)
                return jsonify({"status": "created", "profile": new_profile})
        except (ValueError, TypeError) as e:
            return jsonify({"status": "error", "message": f"Invalid data: {e}"}), 400
    else:
        # MODIFIED in v103.0: This is now the entrypoint for conversational onboarding.
        # This function no longer handles it directly, just signals the frontend.
        return jsonify({"status": "new_user_needed"})


def _process_chat_message_for_auth_user(user_message, profile, profile_hash):
    # Recalculate dynamic and analytical data on every interaction.
    calculate_child_ages(profile)
    calculate_trimester(profile)
    profile = _update_synopsis_if_needed(profile)

    insights = get_conversation_summary(user_message)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_message": user_message,
        "extracted_intent": insights if insights and 'error' not in insights else {}
    }
    profile.setdefault("interaction_log", []).insert(0, log_entry)
    
    # --- BUG FIX v97.3: Detect summary requests ---
    summary_keywords = ["about me", "my profile", "my summary", "what do you know"]
    is_summary_request = any(keyword in user_message.lower() for keyword in summary_keywords)


    if insights.get('error'): return jsonify({"reply": md.render("I'm having a little trouble understanding. Please rephrase.")})

    if ENABLE_CHART_VISUALIZATION and insights.get('query_chart'):
        chart_query = insights.get('query_chart')
        json_response = {"reply": md.render("Of course, here is the visualization you requested."), "chart_type": chart_query.get('type')}
        if chart_query.get('target_date'):
            json_response["target_date"] = chart_query.get('target_date')
        save_profile(profile_hash, profile)
        return jsonify(json_response)
        
    # --- RESTORED v98.7: Contextual Reminder & Pending Question Logic ---
    # This logic is session-dependent and primarily for the monolith experience.
    pending_question = session.get('pending_question')
    if pending_question:
        session.pop('pending_question', None) # Consume the pending question
        
        if pending_question == 'clarify_reminder_creation':
            potential_reminder_context = session.pop('pending_action_context', None)
            affirmative_keywords = ['yes', 'sure', 'ok', 'okay', 'please', 'do it']
            if any(keyword in user_message.lower() for keyword in affirmative_keywords) and potential_reminder_context:
                # Create a standard reminder action from the context
                action_to_create = {
                    "text": potential_reminder_context.get('text'),
                    "due_date": potential_reminder_context.get('date')
                }
                profile, action_response, _ = handle_reminder_action(action_to_create, profile)
            else:
                action_response = "Okay, no problem. I won't set a reminder this time."
        
        # If a response was generated, save and return it.
        if action_response:
            save_profile(profile_hash, profile)
            return jsonify({"reply": md.render(action_response)})
    # --- End of Restore ---

    action_response = None
    new_pending_question = None
    special_context = None # RESTORED v98.8
    action_handlers = {'medication_log': handle_medication_log, 'period_action': handle_period_action, 'set_goal': handle_set_goal, 'reminder_action': handle_reminder_action}
    
    for action_type, handler in action_handlers.items():
        if insights.get(action_type):
            profile, action_response, new_pending_question = handler(insights[action_type], profile)
            break
            
    # --- RESTORED v98.7: Check for new potential reminders ---
    if not action_response and ENABLE_CONTEXTUAL_REMINDERS and insights.get('potential_reminder'):
        potential_reminder_data = insights.pop('potential_reminder')
        session['pending_question'] = 'clarify_reminder_creation'
        session['pending_action_context'] = potential_reminder_data
        action_response = f"I noticed you mentioned your '{potential_reminder_data.get('text')}'. Would you like me to set a reminder for that?"

    # --- RESTORED v98.8 & ENHANCED v101.9: AI Follow-up Questions for Negative Logs ---
    if not action_response and ENABLE_EXPANDED_LOGGING and insights.get('health_log'):
        log_data = insights['health_log']
        profile.setdefault('health_logs', []).insert(0, {"timestamp": datetime.now().isoformat(), **log_data})
        
        category, value = log_data.get('category'), log_data.get('value')
        
        # --- BUG FIX v102.1: Add a guard clause ---
        # Check if both category and value were successfully extracted by the AI.
        # If not, skip this block and fall through to the general AI response.
        if category and value:
            lang_data = load_language_data(profile.get('language', 'en'))
            confirmation_key = f"quick_log_confirm_{value.replace(' ', '_')}_{category}"
            confirmation_message = lang_data.get(confirmation_key, lang_data.get("quick_log_confirm_fallback"))
            
            # --- NEW v101.9: Expanded list of empathetic triggers ---
            negative_log_values = [
                'high', 'poor', 'terrible', 'anxious', 'sad', 'stressed', 
                'overwhelmed', 'exhausted', 'headache', 'cramps', 'painful'
            ]
            if ENABLE_AI_FOLLOW_UP_QUESTIONS and value in negative_log_values:
                special_context = {
                    "type": "empathetic_follow_up",
                    "confirmation_message": confirmation_message,
                    "log_details": log_data
                }
            else:
                action_response = confirmation_message

    if new_pending_question:
        session['pending_question'] = new_pending_question
        
    if action_response:
        save_profile(profile_hash, profile)
        return jsonify({"reply": md.render(action_response)})
    
    # --- BUG FIX v97.1 & v97.4: Overhauled Suggestion/Follow-up Logic ---
    is_follow_up = False
    last_discussed_program_context = None
    suggested_program_object = None

    # 1. Check if this is a follow-up to a pending offer.
    follow_up_program, profile = handle_follow_up_request(profile, user_message)
    if follow_up_program:
        is_follow_up = True
        suggested_program_object = follow_up_program
    else:
        # 2. If not a follow-up, check if we should make a new suggestion.
        new_suggestion = get_program_suggestion(profile, user_message)
        if new_suggestion:
            suggested_program_object = new_suggestion
            profile.setdefault("proactive_assistance", {})["pending_program_offer"] = new_suggestion['name']
            profile["proactive_assistance"]["last_program_suggestion_ts"] = datetime.now(timezone.utc).isoformat()
            
            # 3. Check if the user is asking directly about the topic we just found
            question_is_about_suggestion = any(keyword in user_message.lower() for keyword in ["what is", "tell me about", "explain"])
            if question_is_about_suggestion:
                 special_context = {
                    "type": "explain_and_offer_program",
                    "program_name": new_suggestion['name']
                }

    
    proactive_context = get_proactive_context(profile)
    context_prompt = format_profile_for_prompt(
        profile, 
        chatbot_name=CHATBOT_NAME, 
        proactive_context=proactive_context, 
        suggested_program_object=suggested_program_object, 
        is_follow_up=is_follow_up,
        last_discussed_program_context=last_discussed_program_context,
        enable_ovulation_tracker=ENABLE_OVULATION_TRACKER,
        enable_realtime_log_context=ENABLE_REALTIME_LOG_CONTEXT,
        is_summary_request=is_summary_request,
        special_context=special_context
    )
    
    try:
        response = gemini_model.generate_content(f"{context_prompt}\n{user_message}")
        raw_reply = response.text
        
        # --- NEW in v102.0: Conversational Memory Processing ---
        memory_match = re.search(r"\[SUGGEST_MEMORY:\s*(.*?)\]", raw_reply)
        if memory_match:
            memory_text = memory_match.group(1).strip()
            if memory_text:
                profile.setdefault("key_memories", [])
                new_memory = {
                    "memory": memory_text,
                    "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d')
                }
                # Avoid duplicate memories
                if not any(mem['memory'] == new_memory['memory'] for mem in profile["key_memories"]):
                    profile["key_memories"].insert(0, new_memory)
                    # Prune old memories if list is too long
                    profile["key_memories"] = profile["key_memories"][:MAX_KEY_MEMORIES]
            # Clean the tag from the reply that will be sent to the user
            reply = re.sub(r"\[SUGGEST_MEMORY:\s*(.*?)\]", "", raw_reply).strip()
        else:
            reply = raw_reply

    except Exception as e:
        reply = f"Sorry, an error occurred: {e}"
    
    save_profile(profile_hash, profile)
    return jsonify({"reply": md.render(reply)})


# --- ROUTES ---

# NEW in v100.3: Health Check Endpoint for Production
@app.route('/health')
def health_check():
    """Endpoint for cloud provider health checks."""
    return jsonify({"status": "ok"}), 200

@app.route('/')
def index():
    if app.config['ENABLE_WIDGET_MODE']:
        return jsonify({"status": "success", "message": "Tyra API is active in Widget Mode."})

    # BUG FIX v94.5: Defensively clear any invalid "ghost" sessions.
    if session and not ('profile_hash' in session or session.get('is_guest')):
        session.clear()

    is_session_active = 'profile_hash' in session or session.get('is_guest')
    user_name = ''
    lang_code = 'en'
    if 'profile_hash' in session:
        profile = load_profile(session['profile_hash'])
        if profile: 
            user_name = profile.get('name', '')
            lang_code = profile.get('language', 'en')
    lang_data = load_language_data(lang_code)
    is_rtl = lang_code in ['ur', 'ar']
    
    js_config = {
        'ENABLE_EMAIL_OTP_VERIFICATION': app.config.get('ENABLE_EMAIL_OTP_VERIFICATION'),
        'ENABLE_CONVERSATIONAL_ONBOARDING': app.config.get('ENABLE_CONVERSATIONAL_ONBOARDING') # NEW in v103.0
    }

    return render_template(
        'index.html', 
        is_session_active=is_session_active, 
        user_name=user_name, 
        lang=lang_data, 
        is_rtl=is_rtl,
        config=js_config,
        chatbot_name=CHATBOT_NAME,
        enable_document_upload=ENABLE_DOCUMENT_UPLOAD,
        enable_visual_triage=ENABLE_VISUAL_TRIAGE,
        enable_chart_visualization=ENABLE_CHART_VISUALIZATION,
        enable_voice_input=ENABLE_VOICE_INPUT,
        enable_dashboard=ENABLE_DASHBOARD,
        enable_guest_mode=ENABLE_GUEST_MODE,
        enable_multi_language=ENABLE_MULTI_LANGUAGE,
        enable_conversational_onboarding=app.config.get('ENABLE_CONVERSATIONAL_ONBOARDING') # NEW in v103.0
    )

@app.route('/dashboard')
def dashboard():
    if not ENABLE_DASHBOARD: return "Not Found", 404
    profile_hash = None
    is_widget_context = False # CRITICAL FIX: Flag to control template rendering
    token_for_template = None
    
    token = request.args.get('token')
    if token:
        payload = decode_token(token)
        if payload and not payload.get('is_guest'):
            profile_hash = payload['sub']
            is_widget_context = True # Authenticated via token
            token_for_template = token
    else:
        profile_hash = session.get('profile_hash') # Authenticated via session
    
    if not profile_hash: return redirect(url_for('index'))
    profile = load_profile(profile_hash)
    if not profile: return redirect(url_for('index'))
    
    dashboard_data = _get_dashboard_data(profile) # Use the shared helper
    lang_code = profile.get('language', 'en') if ENABLE_MULTI_LANGUAGE else 'en'
    lang_data = load_language_data(lang_code)
    is_rtl = lang_code in ['ur', 'ar']
    
    return render_template(
        'dashboard.html', 
        data=dashboard_data, 
        lang=lang_data, 
        is_rtl=is_rtl,
        is_widget_context=is_widget_context, # Pass the flag to the template
        auth_token=token_for_template, # Pass the token for client-side JS
        enable_dashboard_customization=ENABLE_DASHBOARD_CUSTOMIZATION,
        enable_shareable_reports=ENABLE_SHAREABLE_REPORTS,
        enable_medication_tracking=ENABLE_MEDICATION_TRACKING,
        enable_goal_tracking=ENABLE_GOAL_TRACKING,
        enable_ovulation_tracker=ENABLE_OVULATION_TRACKER,
        # RESTORED v98.8: Pass mood tracking flag to template
        enable_expanded_mood_tracking=ENABLE_EXPANDED_MOOD_TRACKING
    )

# --- WIDGET API ROUTES ---
if app.config['ENABLE_WIDGET_MODE']:
    @app.route('/api/v1/config')
    @token_required
    def api_config():
        auth_mode = "otp" if app.config.get('ENABLE_EMAIL_OTP_API_VERIFICATION') else "guest"
        # For authenticated users, load their specific language file
        lang_code = 'en'
        if g.profile and not g.is_guest:
            lang_code = g.profile.get('language', 'en')
        
        lang_data = load_language_data(lang_code)

        return jsonify({
            "auth_mode": auth_mode,
            "lang": lang_data
        })

    # The config route for a user who is not yet authenticated
    @app.route('/api/v1/config/initial')
    def api_config_initial():
         auth_mode = "otp" if app.config.get('ENABLE_EMAIL_OTP_API_VERIFICATION') else "guest"
         return jsonify({
            "auth_mode": auth_mode,
            "lang": load_language_data('en') # Default to English before profile is loaded
        })

    @app.route('/api/v1/auth/guest', methods=['POST'])
    def api_guest_auth():
        guest_hash = f"guest_{uuid.uuid4().hex}"
        token = generate_token(guest_hash, is_guest=True)
        return jsonify({"status": "success", "token": token, "is_guest": True})
    
    if app.config.get('ENABLE_EMAIL_OTP_API_VERIFICATION'):
        @app.route('/api/v1/auth/request_otp', methods=['POST'])
        def api_request_otp():
            email = request.json.get('email', '').strip().lower()
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                return jsonify({"status": "error", "message": "Invalid email format."}), 400
            
            otp = str(secrets.randbelow(900000) + 100000)
            api_otp_store[email] = {'otp': otp, 'timestamp': time.time()}
            
            if send_otp_email(email, otp):
                return jsonify({"status": "success", "message": "OTP sent."})
            else:
                return jsonify({"status": "error", "message": "Failed to send OTP email."}), 500

        @app.route('/api/v1/auth/verify_otp', methods=['POST'])
        def api_verify_otp():
            data = request.json
            email = data.get('email', '').strip().lower()
            otp = data.get('otp', '')
            
            stored = api_otp_store.get(email)
            if not stored:
                return jsonify({"status": "error", "message": "No OTP request found. Please start over."}), 400
            
            if time.time() - stored['timestamp'] > OTP_LIFETIME_SECONDS:
                del api_otp_store[email]
                return jsonify({"status": "error", "message": "OTP has expired. Please request a new one."}), 400
            
            if stored['otp'] != otp:
                return jsonify({"status": "error", "message": "Invalid OTP."}), 400
            
            del api_otp_store[email] # OTP is single-use
            
            profile_hash = get_profile_hash(email)
            existing_profile = load_profile(profile_hash)
            
            if existing_profile:
                token = generate_token(profile_hash)
                return jsonify({"status": "exists", "token": token, "name": existing_profile.get("name"), "is_guest": False})
            else:
                # --- NEW in v103.0: Conversational Onboarding Flow ---
                if app.config.get('ENABLE_CONVERSATIONAL_ONBOARDING'):
                    lang_data = load_language_data('en') # Start with default lang
                    onboarding_data = {'step': 'awaiting_name', 'email': email, 'lang_code': 'en', 'profile_data': {}}
                    onboarding_token = generate_token(
                        profile_hash,
                        expires_in_minutes=15,
                        additional_claims={'purpose': 'onboarding', 'onboarding_data': onboarding_data}
                    )
                    return jsonify({
                        "status": "onboarding_started",
                        "onboarding_token": onboarding_token,
                        "reply": md.render(lang_data.get('onboarding_ask_name', ''))
                    })
                else: # Fallback to v102.1 form-based flow
                    verification_token = generate_token(
                        profile_hash, 
                        expires_in_minutes=10, 
                        additional_claims={'verified_email': email, 'purpose': 'create_profile'}
                    )
                    return jsonify({"status": "new_user_needed", "verification_token": verification_token})

        @app.route('/api/v1/auth/create_profile', methods=['POST'])
        def api_create_profile():
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Verification token is missing!'}), 401
            
            token = auth_header.split(" ")[1]
            payload = decode_token(token)
            
            if not payload or payload.get('purpose') != 'create_profile':
                return jsonify({'error': 'Invalid or expired verification token.'}), 403
                
            verified_email = payload.get('verified_email')
            profile_hash = get_profile_hash(verified_email)
            
            data = request.json
            name, age_str = data.get('name'), data.get('age')
            if not name or not age_str:
                return jsonify({"status": "error", "message": "Name and age are required."}), 400
                
            try:
                new_profile = create_user_profile(
                    name=name,
                    email=verified_email,
                    phone='',
                    age=int(age_str),
                    details=data.get('details', {}),
                    lang_code=data.get('language', 'en')
                )
                save_profile(profile_hash, new_profile)
                
                # Grant a full-access, long-lived token
                final_token = generate_token(profile_hash)
                return jsonify({"status": "created", "token": final_token, "name": new_profile.get("name"), "is_guest": False})
                
            except (ValueError, TypeError) as e:
                return jsonify({"status": "error", "message": f"Invalid data: {e}"}), 400
    
    # --- NEW in v103.0: Conversational Onboarding Endpoint for Widget ---
    @app.route('/api/v1/auth/onboard/step', methods=['POST'])
    @token_required
    def api_onboard_step():
        if not g.is_onboarding_token:
            return jsonify({"error": "Invalid token for onboarding."}), 403
        
        user_message = request.json.get('message', '')
        response = _handle_onboarding_step(
            profile_hash=g.profile_hash,
            user_message=user_message,
            onboarding_data=g.onboarding_data,
            is_api_call=True
        )
        return response

    @app.route('/api/v1/chat', methods=['POST'])
    @token_required
    def api_chat():
        if g.is_guest and app.config.get('ENABLE_EMAIL_OTP_API_VERIFICATION'):
            insights = get_conversation_summary(request.json['message'])
            if insights.get('period_action') or insights.get('reminder_action'):
                return jsonify({"reply": "To use this feature, please create an account.", "action": "prompt_signup"})
        
        # In non-OTP guest mode, we allow the chat to proceed
        if g.is_guest:
             response = gemini_model.generate_content(f"You are a helpful assistant. Answer the user's question: {request.json['message']}")
             return jsonify({"reply": md.render(response.text)})

        return _process_chat_message_for_auth_user(request.json['message'], g.profile, g.profile_hash)

    # --- NEW API ENDPOINTS FOR FULL-FEATURED WIDGET ---
    @app.route('/api/v1/upload', methods=['POST'])
    @token_required
    def api_upload():
        if g.is_guest: return jsonify({'error': 'This feature requires an account.'}), 403
        if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '': return jsonify({'error': 'No selected file'}), 400
        user_query = request.form.get('message', "Can you tell me about this file?")
        
        response, status_code = _handle_upload_logic(file, user_query)
        return jsonify(response), status_code
        
    @app.route('/api/v1/transcribe', methods=['POST'])
    @token_required
    def api_transcribe():
        if g.is_guest: return jsonify({'error': 'This feature requires an account.'}), 403
        if 'audio_file' not in request.files: return jsonify({'error': 'No audio file part'}), 400
        file = request.files['audio_file']
        if file.filename == '': return jsonify({'error': 'No selected file'}), 400

        response, status_code = _handle_transcription_logic(file)
        return jsonify(response), status_code

    @app.route('/api/v1/quick_log', methods=['POST'])
    @token_required
    def api_quick_log():
        if g.is_guest: return jsonify({"error": "This feature requires an account."}), 403
        data = request.get_json()
        category, value = data.get('category'), data.get('value')
        if not category or not value: return jsonify({"error": "Invalid log data."}), 400
        
        response = _handle_quick_log_logic(g.profile, category, value)
        save_profile(g.profile_hash, g.profile)
        return jsonify(response)
        
    @app.route('/api/v1/dashboard_data', methods=['GET'])
    @token_required
    def api_dashboard_data():
        if g.is_guest: return jsonify({"error": "This feature requires an account."}), 403
        data = _get_dashboard_data(g.profile)
        return jsonify(data)

    @app.route('/api/v1/reminders/delete', methods=['POST'])
    @token_required
    def api_delete_reminder():
        if g.is_guest: return jsonify({"error": "This feature requires an account."}), 403
        reminder_id = request.json.get('reminder_id')
        if not reminder_id: return jsonify({"error": "ID required"}), 400
        reminders = g.profile.get("proactive_assistance", {}).get("reminders", [])
        initial_length = len(reminders)
        reminders[:] = [r for r in reminders if r.get('id') != reminder_id]
        if len(reminders) < initial_length:
            save_profile(g.profile_hash, g.profile)
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Reminder not found"}), 404
        
    # Chart data endpoint for API is the same as for monolith, just token-protected
    @app.route('/api/v1/chart_data', methods=['GET'])
    @token_required
    def api_chart_data():
        if g.is_guest: return jsonify({"error": "This feature requires an account."}), 403
        # The logic is identical, so we reuse the monolith endpoint's function
        return chart_data(g.profile)

# --- ROUTES SHARED BY MONOLITH & API LOGIC ---

# This function can now be called directly by the API route
@app.route('/chart_data', methods=['GET'])
def chart_data(profile_override=None):
    if not ENABLE_CHART_VISUALIZATION:
        return jsonify({"error": "Chart visualization feature is disabled."}), 403

    # In monolith mode, get profile from session. In API mode, profile is passed in.
    if profile_override:
        profile = profile_override
    else:
        profile_hash = session.get('profile_hash')
        if not profile_hash: return jsonify({"error": "No active session."}), 403
        profile = load_profile(profile_hash)
        if not profile: return jsonify({"error": "Profile not found."}), 404

    chart_type = request.args.get('type')
    
    if chart_type == 'cycle_length':
        cycles = profile.get("period_data", {}).get("cycles", [])
        cycles_with_length = [c for c in cycles if 'cycle_length' in c]
        if len(cycles_with_length) < 1:
            return jsonify({"error": "Not enough cycle data to generate a chart."}), 400
        
        cycles_with_length.sort(key=lambda x: x['start_date'])
        
        labels = [datetime.strptime(c['start_date'], '%Y-%m-%d').strftime('%b %Y') for c in cycles_with_length]
        cycle_lengths = [c['cycle_length'] for c in cycles_with_length]
        
        return jsonify({
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [{"label": "Cycle Length (Days)", "data": cycle_lengths, "backgroundColor": "rgba(168, 85, 168, 0.7)"}]
            },
            "options": {
                "scales": {"y": {"beginAtZero": False, "title": {"display": True, "text": "Days"}}}
            }
        })

    elif chart_type == 'interaction_time':
        history = profile.get("interaction_log", [])
        if not history:
            return jsonify({"error": "No interaction history to display."}), 400
        
        interactions_per_day = defaultdict(int)
        for entry in history:
            try:
                entry_date_str = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d')
                interactions_per_day[entry_date_str] += 1
            except (ValueError, KeyError):
                continue
        
        sorted_dates = sorted(interactions_per_day.keys())
        labels = [datetime.strptime(d, '%Y-%m-%d').strftime('%b %d') for d in sorted_dates]
        interaction_counts = [interactions_per_day[d] for d in sorted_dates]
        
        return jsonify({
            "type": "line",
            "data": {
                "labels": labels,
                "datasets": [{"label": "Interactions", "data": interaction_counts, "fill": True, "borderColor": "rgba(139, 74, 156, 1)", "backgroundColor": "rgba(168, 85, 156, 0.5)"}]
            },
            "options": {
                "scales": {"y": {"beginAtZero": True, "ticks": {"stepSize": 1}, "title": {"display": True, "text": "Count"}}}
            }
        })
    elif chart_type == 'cycle_calendar':
        period_data = profile.get("period_data", {})
        target_date_str = request.args.get('target_date')
        today = datetime.today()

        if target_date_str:
            target_date = dateparser.parse(target_date_str, settings={'RELATIVE_BASE': datetime.now()})
            if not target_date: target_date = today
        else:
            target_date = today

        year, month = target_date.year, target_date.month
        
        predicted_days, fertile_days, logged_days = [], [], []
        avg_period = period_data.get("average_period_length") or 5
        avg_cycle = period_data.get("average_cycle_length") or 28
        cycles = period_data.get("cycles", [])

        # --- BUG FIX v96.0: RENDER LOGGED AND FERTILE DAYS CORRECTLY ---
        # A "logged" cycle is one that exists in the cycles list. We visualize its
        # period and fertile window based on stored data.
        for cycle in cycles:
            if 'start_date' not in cycle:
                continue

            # --- Populate Logged Days (Period) ---
            start_dt = datetime.strptime(cycle['start_date'], '%Y-%m-%d')
            # Use actual end date if available, or fall back to the average for visualization
            if 'end_date' in cycle:
                end_dt = datetime.strptime(cycle['end_date'], '%Y-%m-%d')
            else:
                end_dt = start_dt + timedelta(days=avg_period - 1)
            
            current = start_dt
            while current <= end_dt:
                if current.year == year and current.month == month:
                    if current.day not in logged_days:
                        logged_days.append(current.day)
                current += timedelta(days=1)
            
            # --- Populate Fertile Days for this logged cycle if data exists ---
            if ENABLE_OVULATION_TRACKER and 'fertile_start' in cycle and 'fertile_end' in cycle:
                f_start = datetime.strptime(cycle['fertile_start'], '%Y-%m-%d')
                f_end = datetime.strptime(cycle['fertile_end'], '%Y-%m-%d')
                current = f_start
                while current <= f_end:
                    if current.year == year and current.month == month:
                         if current.day not in fertile_days:
                            fertile_days.append(current.day)
                    current += timedelta(days=1)
        
        # --- RENDER PREDICTED future cycles ---
        # This part only projects forward from the last known cycle's predicted next start.
        next_pred_start_str = period_data.get("predicted_next_start_date")
        if next_pred_start_str:
            current_pred_start = datetime.strptime(next_pred_start_str, '%Y-%m-%d')
            
            for _ in range(12): # Project up to 12 months forward
                # Render predicted period
                for i in range(avg_period):
                    day = current_pred_start + timedelta(days=i)
                    if day.year == year and day.month == month: 
                        if day.day not in logged_days and day.day not in predicted_days:
                             predicted_days.append(day.day)

                # Render predicted fertile window for the cycle starting on `current_pred_start`
                if ENABLE_OVULATION_TRACKER:
                    # Ovulation for this cycle occurs ~14 days before the *next* one starts.
                    next_cycle_start = current_pred_start + timedelta(days=avg_cycle)
                    ovulation_dt = next_cycle_start - timedelta(days=14)
                    f_start = ovulation_dt - timedelta(days=5)
                    f_end = ovulation_dt + timedelta(days=1)
                    current = f_start
                    while current <= f_end:
                        if current.year == year and current.month == month:
                            if current.day not in logged_days and current.day not in fertile_days:
                                fertile_days.append(current.day)
                        current += timedelta(days=1)

                current_pred_start += timedelta(days=avg_cycle)

        return jsonify({
            "type": "calendar",
            "data": {
                "year": year,
                "month": month,
                "month_name": calendar.month_name[month],
                "predicted_days": sorted(list(set(predicted_days))),
                "logged_days": sorted(list(set(logged_days))),
                "fertile_days": sorted(list(set(fertile_days))),
                "current_day": today.day if today.year == year and today.month == month else None
            }
        })
    else:
        return jsonify({"error": "Invalid chart type requested."}), 400


# --- REFACTORED SHARED EXPORT/SHARE LOGIC ---

def _generate_pdf_report(profile):
    user_name = profile.get("name", "User")
    def sanitize(text): return str(text).encode('latin-1', 'replace').decode('latin-1')
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=16)
    pdf.cell(0, 10, text=sanitize(f"{user_name}'s Health Report"), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.set_font("Helvetica", 'I', 8)
    pdf.cell(0, 10, text=f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(10)

    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, text="Upcoming Reminders", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", '', 10)
    reminders = profile.get("proactive_assistance", {}).get("reminders", [])
    if reminders:
        for r in reminders:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5, text=sanitize(f"- {r.get('text')}"))
    else:
        pdf.multi_cell(0, 5, text="No reminders set.")
    pdf.ln(5)

    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, text="Recent Health Logs", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", '', 10)
    logs = profile.get("health_logs", [])
    if logs:
        for log in logs[:15]:
            log_date = dateparser.parse(log['timestamp']).strftime('%Y-%m-%d')
            log_text = f"- {log_date}: Noted {log.get('value')} for {log.get('category')}"
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5, text=sanitize(log_text))
    else:
        pdf.multi_cell(0, 5, text="No health logs recorded.")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, text="Medications & Supplements", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", '', 10)
    meds = profile.get("medication_log", [])
    if meds:
        for med in meds:
            med_text = f"- {med.get('name')} (Dosage: {med.get('dosage', 'N/A')}, Freq: {med.get('frequency', 'N/A')})"
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5, text=sanitize(med_text))
    else:
        pdf.multi_cell(0, 5, text="No medications logged.")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, text="Cycle History", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", '', 10)
    cycles = profile.get("period_data", {}).get("cycles", [])
    if cycles:
        for c in cycles[:12]:
            start = c.get('start_date', 'N/A')
            length = c.get('cycle_length', 'N/A')
            cycle_text = f"- Cycle started {start}, lasted {length} days."
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5, text=sanitize(cycle_text))
    else:
        pdf.multi_cell(0, 5, text="No cycle data recorded.")
    pdf.ln(5)

    return bytes(pdf.output())

def _generate_csv_response(profile):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Log Type", "Date", "Detail 1", "Detail 2"])
    for log in profile.get("health_logs", []):
        writer.writerow(["Health Log", log.get('timestamp'), log.get('category'), log.get('value')])
    for cycle in profile.get("period_data", {}).get("cycles", []):
        writer.writerow(["Cycle", cycle.get('start_date'), f"Cycle Length: {cycle.get('cycle_length', 'N/A')}", f"Period Ends: {cycle.get('end_date', 'N/A')}"])
    for r in profile.get("proactive_assistance", {}).get("reminders", []):
        writer.writerow(["Reminder", r.get('start_date'), r.get('text'), ""])
    for med in profile.get("medication_log", []):
        writer.writerow(["Medication", med.get('logged_date'), med.get('name'), f"Dosage: {med.get('dosage')}"])
    
    csv_bytes = output.getvalue().encode('utf-8')
    user_name = profile.get("name", "User")
    return Response(csv_bytes, mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename={user_name}_health_report.csv"})

def _generate_shareable_report(profile):
    cleanup_expired_reports()
    report_id = uuid.uuid4().hex
    filepath = os.path.join(SHARED_REPORTS_DIR, f"{report_id}.pdf")
    try:
        pdf_bytes = _generate_pdf_report(profile)
        with open(filepath, 'wb') as f:
            f.write(pdf_bytes)
        
        db = load_report_db()
        db[report_id] = {"filepath": f"{report_id}.pdf", "created_at": datetime.now().timestamp()}
        save_report_db(db)
        share_url = url_for('view_report', report_id=report_id, _external=True)
        return {"status": "success", "share_url": share_url}
    except Exception as e:
        print(f"Error generating shareable report: {e}")
        return {"error": "Could not generate report."}


# --- NEW WIDGET API EXPORT ROUTES ---
if app.config['ENABLE_WIDGET_MODE']:
    @app.route('/api/v1/export/pdf', methods=['GET'])
    @token_required
    def api_export_pdf():
        if g.is_guest: return jsonify({'error': 'This feature requires an account.'}), 403
        pdf_bytes = _generate_pdf_report(g.profile)
        user_name = g.profile.get("name", "User")
        return Response(pdf_bytes, mimetype="application/pdf", headers={"Content-Disposition": f"attachment;filename={user_name}_health_report.pdf"})
    
    @app.route('/api/v1/export/csv', methods=['GET'])
    @token_required
    def api_export_csv():
        if g.is_guest: return jsonify({'error': 'This feature requires an account.'}), 403
        return _generate_csv_response(g.profile)

    @app.route('/api/v1/share_report', methods=['POST'])
    @token_required
    def api_share_report():
        if g.is_guest: return jsonify({'error': 'This feature requires an account.'}), 403
        result = _generate_shareable_report(g.profile)
        if "error" in result:
            return jsonify(result), 500
        return jsonify(result)

# --- MONOLITH-ONLY ROUTES ---
if not app.config['ENABLE_WIDGET_MODE']:
    # --- BEGIN AUTHENTICATION FLOW ROUTING ---
    if not app.config.get('ENABLE_EMAIL_OTP_VERIFICATION'):
        @app.route('/check_or_create_profile', methods=['POST'])
        def check_or_create_profile():
            return _handle_profile_check_or_creation(request.get_json(), is_api_call=False)
    else:
        @app.route('/request_otp', methods=['POST'])
        def request_otp():
            email = request.json.get('email', '').strip().lower()
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                return jsonify({"status": "error", "message": "Invalid email format."}), 400
            
            otp = secrets.randbelow(900000) + 100000
            session['otp_data'] = { 'email': email, 'otp': str(otp), 'timestamp': time.time() }
            
            if send_otp_email(email, otp):
                return jsonify({"status": "success", "message": "OTP sent."})
            else:
                return jsonify({"status": "error", "message": "Failed to send OTP email."}), 500

        @app.route('/verify_otp', methods=['POST'])
        def verify_otp():
            data = request.get_json()
            email = data.get('email', '').strip().lower()
            otp = data.get('otp', '')
            otp_data = session.get('otp_data')

            if not otp_data or otp_data['email'] != email:
                return jsonify({"status": "error", "message": "No OTP request found. Please start over."}), 400
            
            if time.time() - otp_data['timestamp'] > OTP_LIFETIME_SECONDS:
                session.pop('otp_data', None)
                return jsonify({"status": "error", "message": "OTP has expired. Please request a new one."}), 400
            
            if otp_data['otp'] != otp:
                return jsonify({"status": "error", "message": "Invalid OTP."}), 400
            
            session['otp_verified_email'] = email
            profile_hash = get_profile_hash(email)
            existing_profile = load_profile(profile_hash)

            if existing_profile:
                session.clear()
                session['profile_hash'] = profile_hash
                return jsonify({"status": "exists", "profile": existing_profile})
            else:
                # --- NEW in v103.0: Conversational Onboarding Flow ---
                if app.config.get('ENABLE_CONVERSATIONAL_ONBOARDING'):
                    session['onboarding_state'] = { 'step': 'awaiting_name', 'profile_hash': profile_hash, 'email': email, 'lang_code': 'en', 'profile_data': {} }
                    lang_data = load_language_data('en')
                    return jsonify({
                        "status": "onboarding_started",
                        "reply": md.render(lang_data.get('onboarding_ask_name', ''))
                    })
                else: # Fallback to v102.1 form-based flow
                    return jsonify({"status": "new_user_needed"})

        @app.route('/create_profile_with_otp', methods=['POST'])
        def create_profile_with_otp():
            verified_email = session.get('otp_verified_email')
            if not verified_email:
                return jsonify({"status": "error", "message": "OTP not verified. Please start over."}), 403

            data = request.json
            name, age_str = data.get('name'), data.get('age')
            if not name or not age_str:
                return jsonify({"status": "error", "message": "Name and age are required."}), 400
            
            try:
                profile_hash = get_profile_hash(verified_email)
                details = data.get('details', {})
                lang_code = data.get('language', 'en') if ENABLE_MULTI_LANGUAGE else 'en'
                
                new_profile = create_user_profile(name, verified_email, '', int(age_str), details, lang_code)
                calculate_trimester(new_profile)
                calculate_child_ages(new_profile)
                save_profile(profile_hash, new_profile)

                session.clear()
                session['profile_hash'] = profile_hash
                return jsonify({"status": "created", "profile": new_profile})
            except (ValueError, TypeError) as e:
                return jsonify({"status": "error", "message": f"Invalid data: {e}"}), 400
    # --- END AUTHENTICATION FLOW ROUTING ---

    @app.route('/chat', methods=['POST'])
    def chat():
        # --- NEW in v103.0: Intercept for conversational onboarding ---
        if 'onboarding_state' in session:
            user_message = request.json.get('message', '')
            response = _handle_onboarding_step(
                profile_hash=session['onboarding_state']['profile_hash'],
                user_message=user_message,
                onboarding_data=session['onboarding_state'],
                is_api_call=False
            )
            # Update session state if a new state was returned
            if 'onboarding_state' in response.get_json():
                session['onboarding_state'] = response.get_json()['onboarding_state']
            else: # Onboarding finished or failed, clear the state
                session.pop('onboarding_state', None)

            return response
        
        if 'profile_hash' in session:
            profile = load_profile(session['profile_hash'])
            if not profile: return jsonify({"error": "Profile not found"}), 404
            
            return _process_chat_message_for_auth_user(request.json['message'], profile, session['profile_hash'])
        
        elif session.get('is_guest'):
            user_message = request.json.get('message', '')
            # --- RESTORED v98.8: LLM Caching for Guests ---
            if ENABLE_LLM_CACHING:
                cache_key = re.sub(r'[^\w\s]', '', user_message).lower().strip()
                if cache_key in llm_response_cache:
                    cached_reply = llm_response_cache[cache_key]
                    return jsonify({"reply": md.render(cached_reply)})

            insights = get_conversation_summary(user_message)
            if insights.get('period_action') or insights.get('reminder_action'):
                return jsonify({"reply": "To use this feature, please create an account.", "action": "prompt_signup"})
            
            response = gemini_model.generate_content(f"You are a helpful assistant. Answer the user's question: {user_message}")
            reply_text = response.text

            if ENABLE_LLM_CACHING:
                if len(llm_response_cache) > MAX_CACHE_SIZE:
                    llm_response_cache.clear()
                llm_response_cache[cache_key] = reply_text
            
            return jsonify({"reply": md.render(reply_text)})
        return jsonify({"error": "No active session"})
    
    @app.route('/logout', methods=['POST'])
    def logout():
        session.clear()
        return jsonify({"status": "success"})
        
    @app.route('/start_guest', methods=['POST'])
    def start_guest():
        if not ENABLE_GUEST_MODE: return jsonify({"status": "error"}), 403
        session.clear()
        session['is_guest'] = True
        return jsonify({"status": "success"})

    @app.route('/quick_log', methods=['POST'])
    def quick_log():
        if 'profile_hash' not in session: return jsonify({"error": "Authentication required."}), 403
        profile_hash = session.get('profile_hash')
        profile = load_profile(profile_hash)
        if not profile: return jsonify({"error": "Profile not found."}), 404
        data = request.get_json()
        category, value = data.get('category'), data.get('value')
        if not category or not value: return jsonify({"error": "Invalid log data."}), 400
        
        response = _handle_quick_log_logic(profile, category, value)
        save_profile(profile_hash, profile)
        return jsonify(response)

    @app.route('/upload', methods=['POST'])
    def upload():
        if not ('profile_hash' in session or session.get('is_guest')): return jsonify({"error": "No active session."}), 403
        if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '': return jsonify({'error': 'No selected file'}), 400
        user_query = request.form.get('message', "Can you tell me about this file?")

        response, status_code = _handle_upload_logic(file, user_query)
        return jsonify(response), status_code
        
    @app.route('/transcribe', methods=['POST'])
    def transcribe_audio():
        if not ENABLE_VOICE_INPUT: return jsonify({"error": "Voice input feature is disabled."}), 403
        if not ('profile_hash' in session or session.get('is_guest')): return jsonify({"error": "Authentication required."}), 401
        if 'audio_file' not in request.files: return jsonify({'error': 'No audio file part'}), 400
        file = request.files['audio_file']
        if file.filename == '': return jsonify({'error': 'No selected file'}), 400

        response, status_code = _handle_transcription_logic(file)
        return jsonify(response), status_code

    @app.route('/delete_reminder', methods=['POST'])
    def delete_reminder():
        if not ENABLE_INTERACTIVE_DASHBOARD: return jsonify({"error": "Feature disabled"}), 403
        profile_hash = session.get('profile_hash')
        if not profile_hash: return jsonify({"error": "No active session"}), 403
        profile = load_profile(profile_hash)
        if not profile: return jsonify({"error": "Profile not found"}), 404
        reminder_id = request.json.get('reminder_id')
        if not reminder_id: return jsonify({"error": "ID required"}), 400
        reminders = profile.get("proactive_assistance", {}).get("reminders", [])
        initial_length = len(reminders)
        reminders[:] = [r for r in reminders if r.get('id') != reminder_id]
        if len(reminders) < initial_length:
            save_profile(profile_hash, profile)
            return jsonify({"status": "success"})
        return jsonify({"status": "error"}), 404

    @app.route('/export', methods=['POST'])
    def export():
        if not ENABLE_REPORT_EXPORTING: return "Not Found", 404
        profile_hash = session.get('profile_hash')
        if not profile_hash: return redirect(url_for('index'))
        profile = load_profile(profile_hash)
        if not profile: return redirect(url_for('index'))
        export_format = request.form.get('format', 'pdf')

        if export_format == 'pdf':
            pdf_bytes = _generate_pdf_report(profile)
            user_name = profile.get("name", "User")
            return Response(pdf_bytes, mimetype="application/pdf", headers={"Content-Disposition": f"attachment;filename={user_name}_health_report.pdf"})
        
        elif export_format == 'csv':
            return _generate_csv_response(profile)
        return "Invalid format", 400

    @app.route('/share_report', methods=['POST'])
    def share_report():
        if not ENABLE_SHAREABLE_REPORTS: return jsonify({"error": "Feature disabled"}), 403
        profile_hash = session.get('profile_hash')
        if not profile_hash: return jsonify({"error": "Authentication required"}), 401
        profile = load_profile(profile_hash)
        if not profile: return jsonify({"error": "Profile not found"}), 404
        
        result = _generate_shareable_report(profile)
        if "error" in result:
            return jsonify(result), 500
        return jsonify(result)

# This route must be accessible in both modes
@app.route('/view_report/<report_id>')
def view_report(report_id):
    if not ENABLE_SHAREABLE_REPORTS: return "Feature disabled", 404
    db = load_report_db()
    report_data = db.get(report_id)
    if not report_data or datetime.now().timestamp() - report_data.get('created_at', 0) > REPORT_LIFETIME_HOURS * 3600:
        return "Report not found or has expired.", 404

    # CORRECT WAY: Use os.path.basename to get just the filename.
    # This securely serves the file from the absolute path directory.
    filename = os.path.basename(report_data['filepath'])
    return send_from_directory(SHARED_REPORTS_DIR, filename)

# --- ADMIN DEBUG ENDPOINT (NEW for v101.4) ---
# This route is only active when the SQLite backend is enabled
if ENABLE_SQLITE_DATABASE:
    # WARNING: This endpoint provides direct download access to the production database.
    # It MUST be protected by a strong, unpredictable secret key set as an environment variable.
    @app.route('/admin/backup/download_db/<secret_key>')
    def download_database(secret_key):
        # Load the secret key from the environment variables
        correct_key = os.environ.get('ADMIN_SECRET_KEY')
        
        # 1. Check if a key is configured and if the provided key matches
        if not correct_key or secret_key != correct_key:
            return "Unauthorized", 401

        # 2. Use the persistent path to find the database file
        # (The same path variables we defined at the top of the file)
        db_directory = DATA_BASE_PATH
        db_filename = DATABASE_FILE

        # 3. Securely send the file for download
        try:
            return send_from_directory(db_directory, db_filename, as_attachment=True)
        except FileNotFoundError:
            return "Database file not found on the server.", 404

# --- NEW in v103.0: Conversational Onboarding Logic ---
def _parse_life_events_from_text(user_text, age):
    """Uses AI to parse natural language into structured secondary_details."""
    if not gemini_model: return {}

    prompt = f"""
    You are an expert data extraction tool. Your task is to analyze a user's free-text description of their life stage and convert it into a structured JSON object.

    The user is {age} years old. Use this age to inform your interpretation.

    **Possible JSON output fields (all boolean):**
    - "is_trying_to_conceive"
    - "is_pregnant"
    - "is_parent"
    - "is_perimenopausal"
    - "is_menopausal"

    **CRITICAL RULES:**
    1.  Your output MUST be a single, raw, valid JSON object and nothing else.
    2.  Only include fields that are strongly implied by the user's text.
    3.  If the user's text is vague or doesn't match any category, return an empty JSON object `{{}}`.

    --- EXAMPLES ---
    User Text: "I'm trying to have a baby."
    {{ "is_trying_to_conceive": true }}

    User Text: "I'm 14 weeks pregnant and I already have a two year old."
    {{ "is_pregnant": true, "is_parent": true }}

    User Text: "I think I'm starting perimenopause, the symptoms are crazy."
    {{ "is_perimenopausal": true }}
    
    User Text: "I'm not really focused on anything specific right now"
    {{}}

    User Text: "My period is irregular."
    {{}}

    ---
    Now, process this user's text: "{user_text}"
    """
    try:
        response = gemini_model.generate_content(prompt)
        cleaned_response = response.text.strip().lstrip("```json").rstrip("```").strip()
        return json.loads(cleaned_response)
    except Exception:
        return {} # Return empty on any failure

def _handle_onboarding_step(profile_hash, user_message, onboarding_data, is_api_call=False):
    """
    State machine for handling the multi-step conversational onboarding process.
    Works for both monolith (session) and widget (token) modes.
    """
    step = onboarding_data.get('step')
    profile_data = onboarding_data.get('profile_data', {})
    lang_code = onboarding_data.get('lang_code', 'en')
    
    next_step = step
    next_question = ''
    response_payload = {} # Start with an empty payload

    if step == 'awaiting_name':
        if len(user_message) < 2:
            lang_data = load_language_data(lang_code)
            next_question = lang_data.get('onboarding_invalid_name', 'That seems a bit short. Could you please provide your name?')
        else:
            profile_data['name'] = user_message
            lang_data = load_language_data(lang_code)
            next_question = lang_data.get('onboarding_ask_language', '').format(name=user_message.split(' ')[0])
            response_payload['reply_type'] = 'language_picker' # FIX v103.1
            next_step = 'awaiting_language'

    elif step == 'awaiting_language': # NEW STEP in v103.1
        if user_message in LANG_MAP:
            lang_code = user_message
            onboarding_data['lang_code'] = lang_code
            lang_data = load_language_data(lang_code)
            next_question = lang_data.get('onboarding_ask_age', '').format(name=profile_data['name'].split(' ')[0])
            next_step = 'awaiting_age'
        else:
            lang_data = load_language_data(lang_code)
            next_question = "I'm sorry, I didn't recognize that language. Please select one from the list."
            response_payload['reply_type'] = 'language_picker'

    elif step == 'awaiting_age':
        lang_data = load_language_data(lang_code) # Use the chosen language
        try:
            age = int(user_message)
            if 13 <= age <= 100:
                profile_data['age'] = age
                if age < 20: key = 'onboarding_ask_details_teen'
                elif age > 50: key = 'onboarding_ask_details_senior'
                else: key = 'onboarding_ask_details_adult'
                next_question = lang_data.get(key, '')
                next_step = 'awaiting_details'
            else:
                next_question = lang_data.get('onboarding_invalid_age', 'Please enter a valid age between 13 and 100.')
        except ValueError:
            next_question = lang_data.get('onboarding_invalid_age', 'Please enter a valid age between 13 and 100.')

    elif step == 'awaiting_details':
        lang_data = load_language_data(lang_code)
        age = profile_data.get('age')
        secondary_details = _parse_life_events_from_text(user_message, age)
        
        # Create and save the full profile
        new_profile = create_user_profile(
            name=profile_data['name'],
            email=onboarding_data.get('email', ''),
            phone='',
            age=age,
            details=secondary_details,
            lang_code=lang_code
        )
        save_profile(profile_hash, new_profile)
        
        # Prepare final response
        final_reply = lang_data.get('onboarding_complete', '').format(name=profile_data['name'].split(' ')[0])
        
        if is_api_call:
            final_token = generate_token(profile_hash)
            return jsonify({
                "status": "created",
                "token": final_token,
                "name": new_profile.get("name"),
                "is_guest": False,
                "reply": md.render(final_reply)
            })
        else: # Monolith
            session.clear() # Clear onboarding and OTP data
            session['profile_hash'] = profile_hash
            return jsonify({
                "status": "created", 
                "profile": new_profile, 
                "reply": md.render(final_reply)
            })
    
    # If onboarding is not finished, update the state and prepare the response
    onboarding_data['step'] = next_step
    onboarding_data['profile_data'] = profile_data
    response_payload['reply'] = md.render(next_question)

    if is_api_call:
        new_token = generate_token(
            profile_hash,
            expires_in_minutes=15,
            additional_claims={'purpose': 'onboarding', 'onboarding_data': onboarding_data}
        )
        response_payload['status'] = "onboarding_inprogress"
        response_payload['onboarding_token'] = new_token
        return jsonify(response_payload)
    else: # Monolith
        response_payload['status'] = "onboarding_inprogress"
        response_payload['onboarding_state'] = onboarding_data
        return jsonify(response_payload)


if __name__ == '__main__':
    if not app.config.get("FLASK_SECRET_KEY"):
        raise ValueError("No FLASK_SECRET_KEY set for Flask application.")
    if app.config.get('ENABLE_EMAIL_OTP_VERIFICATION') and (not app.config.get("SENDGRID_API_KEY") or not app.config.get("SENDER_EMAIL")):
        print("WARNING: ENABLE_EMAIL_OTP_VERIFICATION is True, but SENDGRID_API_KEY or SENDER_EMAIL is not set. OTP emails will fail.")
    app.run(host='0.0.0.0', port=5001, debug=True)