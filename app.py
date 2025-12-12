# app.py (v121.0 - Lifecycle Companion: Deep Postnatal & Granular Proactive Logic)
import os, json, hashlib, google.generativeai as genai, calendar, time, io, csv, uuid, re, secrets, random, requests
from datetime import datetime, timedelta, timezone, date
from flask import Flask, Response, render_template, request, jsonify, session, redirect, url_for, send_from_directory, g
from dotenv import load_dotenv
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
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageDraw, ImageFont # NEW in v117.0
import textwrap # NEW in v117.3

from user_profiler import create_user_profile, format_profile_for_prompt, LANG_MAP

# Load environment variables from .env file FIRST. This is safe for production.
# On Render, it does nothing. On local, it loads the .env file into the OS environment.
load_dotenv()

# --- Configuration Constants ---
MAX_HISTORY_ENTRIES = 50
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
MAX_CHAT_LOG_ENTRIES = 50 # NEW in v108.0: Limit size of persisted chat log
MEMORY_CHECK_IN_WINDOW_DAYS = 14 # NEW in v115.0: Window for proactive memory check-ins
INSIGHT_COOLDOWN_DAYS = 7 # NEW in v117.0
BURN_WINDOW_HOURS = 24 # NEW in v119.1: Time window for Burner Mode
PROACTIVE_GREET_COOLDOWN_HOURS = 2 # NEW in v120.0: Anti-spam cooldown for proactive greeting

# NEW in v105.4: Define an ordered list of models for fallback on rate limiting.
GEMINI_MODEL_CASCADE_LIST = [
    'gemini-2.5-flash-lite',    # Primary model
    'gemini-2.0-flash-lite',    # First fallback
    'gemini-2.0-flash',         # Second fallback (text-only)
    'gemini-2.5-flash'          # Third fallback (text-only)
]

# NEW in v105.0: Badge Definitions
BADGE_DEFINITIONS = [
    {"id": "usage_3_day", "name": "3-Day Explorer", "days": 3},
    {"id": "usage_7_day", "name": "7-Day Consistent", "days": 7},
    {"id": "usage_15_day", "name": "15-Day Habit", "days": 15},
    {"id": "usage_30_day", "name": "30-Day Milestone", "days": 30},
    {"id": "usage_60_day", "name": "60-Day Pro", "days": 60},
    {"id": "usage_90_day", "name": "90-Day Master", "days": 90},
    {"id": "usage_6_month", "name": "6-Month Companion", "days": 180},
    {"id": "usage_1_year", "name": "1-Year Anniversary", "days": 365}
]


# Secure CORS allow-list for production
ALLOWED_ORIGINS = [
    'http://localhost:8000',
    'https://tribher.com',
    'https://fitcommunity.in'
]

# --- Feature Flags ---
ENABLE_DEEP_LIFECYCLE_ENGINE = True # NEW in v121.0: Enables granular postnatal & age-specific logic (Vaccines, Indian context)
ENABLE_PROACTIVE_GREETING = True # NEW in v120.0: Enables the system to initiate conversation.
ENABLE_CYCLE_SYNCED_UI = True # NEW in v119.5: Enables automatic theme switching based on cycle phase.
ENABLE_NATIVE_APP_AUTH = True # NEW in v118.0: Enables a secure endpoint for an authenticated native app to get a token.
ENABLE_SHAREABLE_INSIGHTS = True # NEW in v117.0
ENABLE_GAMIFICATION_STREAKS = True # NEW in v116.0: Enables daily check-in streaks.
ENABLE_VIDEO_SUGGESTIONS = True # NEW in v106.0: Enables in-chat YouTube video suggestions for wellness.
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

# MODIFIED in v110.2: Load config directly from the OS environment, which `load_dotenv` populates.
app.config.from_mapping(os.environ)

# --- NEW in v110.2: Sanitize environment variables to remove extra quotes ---
# This handles inconsistencies between local .env file parsing and cloud provider environments (like Render).
for key in ['FLASK_SECRET_KEY', 'GEMINI_API_KEY', 'ZEPTOMAIL_TOKEN', 'SENDER_EMAIL', 'NATIVE_APP_SECRET_KEY']:
    if key in app.config and isinstance(app.config[key], str):
        app.config[key] = app.config[key].strip('\'"')
# --- End Sanitize ---

app.config['SECRET_KEY'] = app.config.get("FLASK_SECRET_KEY")

# Now, set feature flags in the app config as well for consistency
app.config['ENABLE_WIDGET_MODE'] = ENABLE_WIDGET_MODE
app.config['ENABLE_EMAIL_OTP_VERIFICATION'] = ENABLE_EMAIL_OTP_VERIFICATION
app.config['ENABLE_EMAIL_OTP_API_VERIFICATION'] = ENABLE_EMAIL_OTP_API_VERIFICATION
app.config['ENABLE_CONVERSATIONAL_ONBOARDING'] = ENABLE_CONVERSATIONAL_ONBOARDING # NEW in v103.0
app.config['ENABLE_NATIVE_APP_AUTH'] = ENABLE_NATIVE_APP_AUTH # NEW in v118.0
app.config['ENABLE_PROACTIVE_GREETING'] = ENABLE_PROACTIVE_GREETING # NEW in v120.0

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
SHARED_INSIGHTS_DIR = os.path.join(DATA_BASE_PATH, "shared_insights") # NEW in v117.0
TRIBHER_DATA_FILE = os.path.join(DATA_BASE_PATH, "tribher_data_final.json")
MILESTONES_DATA_FILE = os.path.join(DATA_BASE_PATH, "milestones_data.json")
EDUCATION_DATA_FILE = os.path.join(DATA_BASE_PATH, "education_tidbits.json") # FIX in v104.4
WELLNESS_VIDEOS_FILE = os.path.join(DATA_BASE_PATH, "wellness_videos.json") # NEW in v106.0

# Define static directories separately as they are part of the app package
STATIC_CSS_DIR = os.path.join('static', 'css')
STATIC_JS_DIR = os.path.join('static', 'js')
STATIC_FONTS_DIR = os.path.join('static', 'fonts') # NEW in v117.0
LOCALES_DIR = "locales"

# Create all necessary non-profile directories
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(SHARED_REPORTS_DIR, exist_ok=True)
os.makedirs(SHARED_INSIGHTS_DIR, exist_ok=True) # NEW in v117.0
SHARED_REPORTS_DB_FILE = os.path.join(SHARED_REPORTS_DIR, "shared_reports_db.json")
os.makedirs(STATIC_CSS_DIR, exist_ok=True)
os.makedirs(STATIC_JS_DIR, exist_ok=True)
os.makedirs(STATIC_FONTS_DIR, exist_ok=True) # NEW in v117.0
os.makedirs(LOCALES_DIR, exist_ok=True)
# --- End of Storage Configuration ---

TRIBHER_DATA = None
MILESTONES_DATA = None
EDUCATION_DATA = None # NEW in v104.2
WELLNESS_VIDEO_DATA = None # NEW in v106.0
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

        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-App-Secret-Key'
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

        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-App-Secret-Key'
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


# MODIFIED in v110.0: Switched from SendGrid to ZeptoMail for OTP
def send_otp_email(to_email, otp):
    """Sends an OTP email using the ZeptoMail API."""
    zeptomail_token = app.config.get("ZEPTOMAIL_TOKEN")
    sender_email = app.config.get("SENDER_EMAIL")

    if not zeptomail_token or not sender_email:
        print("!!! CRITICAL ERROR: ZeptoMail Token or Sender Email not configured in app.config.")
        return False

    url = "https://api.zeptomail.in/v1.1/email"
    
    # The name for the recipient can be generic, as we only have the email.
    recipient_name = to_email.split('@')[0].capitalize()

    payload = {
        "from": {"address": sender_email},
        "to": [{"email_address": {"address": to_email, "name": recipient_name}}],
        "subject": "Your Tyra Verification Code",
        "htmlbody": f"<div><b>Your one-time verification code is: {otp}</b><br>This code will expire in 5 minutes.</div>"
    }

    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'authorization': zeptomail_token,
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        # This will raise an exception for 4xx and 5xx status codes.
        # Any 2xx code (like 200 OK or 201 Created) will pass.
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"!!! ZeptoMail Error: {e}")
        # Log the response text if available, as it often contains useful error details from the API
        if e.response is not None:
            print(f"!!! ZeptoMail Response: {e.response.text}")
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

# MODIFIED in v105.4: Simplified to only configure the API key.
def configure_ai():
    """Configures the Google AI API key. Models are now instantiated on demand."""
    try:
        gemini_api_key = app.config.get("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in configuration.")
        genai.configure(api_key=gemini_api_key)
        print("--- Google AI configured successfully. ---")
    except Exception as e:
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

# NEW in v104.2
def load_education_data():
    global EDUCATION_DATA
    try:
        with open(EDUCATION_DATA_FILE, 'r') as f: EDUCATION_DATA = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): EDUCATION_DATA = None

# NEW in v106.0
def load_wellness_videos():
    global WELLNESS_VIDEO_DATA
    try:
        with open(WELLNESS_VIDEOS_FILE, 'r') as f: WELLNESS_VIDEO_DATA = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): WELLNESS_VIDEO_DATA = []

load_tribher_data()
load_milestones_data()
load_education_data() # NEW in v104.2
load_wellness_videos() # NEW in v106.0
configure_ai()
md = MarkdownIt()

# NEW in v105.4: Centralized LLM call function with cascading fallback
def _call_llm_with_fallback(*prompt_parts):
    """
    Calls the Gemini API with a prompt, trying models from the cascade list.
    Falls back to the next model ONLY on ResourceExhausted (rate limit) errors.
    Accepts one or more arguments to be passed to generate_content.
    """
    for model_name in GEMINI_MODEL_CASCADE_LIST:
        try:
            print(f"--- Attempting LLM call with model: {model_name} ---")
            # Instantiate the model for this attempt
            model = genai.GenerativeModel(model_name)
            # Make the API call
            response = model.generate_content(prompt_parts)
            print(f"--- Call with {model_name} successful. ---")
            return response
        except exceptions.ResourceExhausted as e:
            print(f"!!! WARNING: Model {model_name} is rate-limited. Trying next model. Error: {e}")
            time.sleep(1) # Add a small delay before retrying
            continue # Go to the next model in the list
        except Exception as e:
            # For any other error (safety, invalid args, etc.), fail immediately.
            print(f"!!! CRITICAL: Non-recoverable API error with {model_name}. Halting fallback. Error: {e}")
            return None
    
    # If the loop completes without returning, all models failed.
    print("!!! CRITICAL: All models in the cascade list failed due to rate limiting.")
    return None

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

# MODIFIED in v120.1: Enhanced Intent Recognition for Pregnancy Updates
def get_conversation_summary(user_message):
    today_date = datetime.now().strftime('%Y-%m-%d')
    summary_prompt = f"""
You are an expert tool for converting natural language into a structured JSON object.
Your output MUST be a single, raw, valid JSON object.
Today's date is {today_date}. Resolve all relative dates to 'YYYY-MM-DD' format.

**CRITICAL RULES & INTENTS (In Order of Priority):**
1.  **UPDATE PREGNANCY (Highest Priority):** If the user states exactly how many weeks pregnant they are (e.g., "I am 32 weeks pregnant", "32 weeks", "I'm 10 weeks along"), you MUST return an `update_pregnancy_weeks` type inside `life_event_update`.
2.  **ACCEPT WEEKLY INSIGHT:** If the user agrees to see their summary (e.g., "yes show me", "sure", "show me my summary"), return `accept_weekly_insight`.
3.  **REAL TALK:** For phrases indicating a desire for a frank or confidential chat (e.g., "can I ask something personal", "real talk"), return a `request_real_talk` intent.
4.  **LIFE EVENT UPDATE:** If the user announces a new life stage like pregnancy or perimenopause, or the end of one (giving birth), return a `life_event_update` intent.
5.  **PROVIDE DOB:** If the user explicitly states their date of birth ("my dob is", "I was born on"), you MUST return a `provide_dob` intent.
6.  **REMINDERS & MEMORIES:** For future events mentioned conversationally (e.g., "I have an appointment on Friday", "I have a huge exam next week"), you MUST include BOTH of the following:
    a. A `potential_reminder` object with `text` and `date`.
    b. A `suggested_memory` string containing the full fact (e.g., "User has an appointment on Friday").
7.  **CHARTING OVERRIDE:** If the message contains 'chart', 'calendar', 'graph', or 'visualize', you MUST return a `query_chart` intent.
8.  **SET GOAL:** For phrases like "my goal is..." or "I want to start...", return a `set_goal` intent.
9.  **MEDICATION LOG:** For phrases about taking or logging medicine, return `medication_log`.
10. **REMINDERS (EXPLICIT):** For command-like phrases ("remind me to", "set a reminder"), return `reminder_action`.
11. **INTERACTIVE TOOLS (NEW):**
    a. If the user feels "overwhelmed", "panicked", "stressed", or asks to "breathe" or "calm down", return `request_breathing_tool`.
    b. If the user explicitly asks for a "list" or "checklist" (e.g., "checklist for vaccines", "hospital bag list"), return `request_checklist` with a `topic`.
12. **OTHER ACTIONS:** Process `health_log`, `period_action`, or `ambiguous_log` as normal.
13. **GENERAL CHAT / QUESTIONS:** For anything else, return an empty JSON object `{{}}`.


--- EXAMPLES ---
User: 'I am feeling incredibly overwhelmed and stressed right now.'
{{"request_breathing_tool": true, "health_log": {{"category": "stress", "value": "high"}}}}

User: 'Can you give me a list of the vaccines due now?'
{{"request_checklist": {{"topic": "vaccines due now"}}}}

User: 'Create a checklist for my hospital bag.'
{{"request_checklist": {{"topic": "hospital bag"}}}}

User: 'I am 32 weeks pregnant'
{{"life_event_update": {{"type": "update_pregnancy_weeks", "weeks": 32}}}}

User: 'I think I am about 10 weeks pregnant'
{{"life_event_update": {{"type": "update_pregnancy_weeks", "weeks": 10}}}}

User: 'yes, show me my summary'
{{"accept_weekly_insight": true}}

User: 'real talk, i'm feeling really weird about my body'
{{"request_real_talk": true}}

User: 'can I ask you something personal?'
{{"request_real_talk": true}}

User: 'I have a huge final exam next Friday.'
{{"potential_reminder": {{"text": "huge final exam", "date": "{(datetime.now() + timedelta(days=(4 - datetime.now().weekday() + 7) % 7)).strftime('%Y-%m-%d')}" }}, "suggested_memory": "User has a huge final exam next Friday."}}

User: 'My follow-up appointment is next Tuesday.'
{{"potential_reminder": {{"text": "follow-up appointment", "date": "{(datetime.now() + timedelta(days=(1 - datetime.now().weekday() + 7) % 7)).strftime('%Y-%m-%d')}" }}, "suggested_memory": "User has a follow-up appointment next Tuesday."}}

User: 'I had my baby on Tuesday!'
{{"life_event_update": {{"type": "pregnancy_to_parenting", "date": "{(datetime.now() - timedelta(days=(datetime.now().weekday() - 1) % 7)).strftime('%Y-%m-%d')}"}}}}

User: 'Good news, I am pregnant!'
{{"life_event_update": {{"type": "start_pregnancy"}}}}

User: 'I think I am starting perimenopause.'
{{"life_event_update": {{"type": "start_perimenopause"}}}}

User: 'my date of birth is 1st feb 1992'
{{"provide_dob": {{"date": "1992-02-01"}}}}

User: 'my period started on july 1st'
{{"period_action": {{"type": "log_period_start", "date": "{datetime.now().year}-07-01"}}}}

User: 'graph my period length over the last few months'
{{"query_chart": {{"type": "cycle_length"}}}}

User: 'show my period calendar for june month'
{{"query_chart": {{"type": "cycle_calendar", "target_date": "{datetime.now().year}-06-01"}}}}

User: 'Remind me to call the doctor tomorrow.'
{{"reminder_action": {{"text": "call the doctor", "due_date": "{(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}"}}}}

User: 'Log that I am taking Vitamin D 500mg daily.'
{{"medication_log": {{"name": "Vitamin D", "dosage": "500mg", "frequency": "daily"}}}}

User: 'Do you have any yoga videos for the first trimester?'
{{}}

User: 'show me some postnatal exercises'
{{}}

User: 'visualize my cycle length'
{{"query_chart": {{"type": "cycle_length"}}}}

User: 'I have a headache'
{{"health_log": {{"category": "physical_symptom", "value": "headache"}}}}

User: 'what should I do for period cramps?'
{{}}

User: 'My goal is to exercise 3 times a week.'
{{"set_goal": {{"text": "exercise 3 times a week"}}}}

User: 'what should I do for period cramps?'
{{}}
--- END EXAMPLES ---

Now, process this user message:
'{user_message}'
"""
    response = _call_llm_with_fallback(summary_prompt)
    if response is None:
        print("!!! LLM call failed in get_conversation_summary after all fallbacks.")
        return {"error": "llm_call_failed"}

    try:
        cleaned_response = response.text.strip().lstrip("```json").rstrip("```").strip()
        return json.loads(cleaned_response)
    except json.JSONDecodeError as e:
        print(f"!!! JSONDecodeError during summarization: {e}")
        print(f"Faulty AI response from model: {response.text}")
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
        # Check if it's a simple string or a dictionary (v121.0 structure)
        if isinstance(milestone_text, dict):
             description = milestone_text.get('description', '')
             response = f"Of course! At {weeks} weeks pregnant: {description}"
        else:
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

# NEW in v107.6: Handle DOB updates
def _handle_dob_update(action, profile):
    """Updates the user's DOB and recalculates their age."""
    date_str = action.get("date")
    if not date_str:
        return profile, "I'm sorry, I couldn't quite understand that date. Could you try again?", None
    
    profile["dob"] = date_str
    profile["dob_source"] = "user_provided"
    
    # Immediately update age based on new, accurate DOB
    profile = _recalculate_age_dependent_categories(profile)
    
    reply = f"Thank you for sharing! I've updated your date of birth to {date_str} and recalculated your age to {profile.get('age')}."
    return profile, reply, None

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

# MODIFIED in v115.0: Add proactive memory check-ins
def get_proactive_context(profile):
    if not ENABLE_PROACTIVE_ASSISTANCE: return None
    today_dt = datetime.now(timezone.utc) # Use timezone-aware datetime
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
                if (today_dt.replace(tzinfo=None) - last_check_in_dt).days >= GOAL_CHECK_IN_DAYS:
                    goal["last_check_in_date"] = today_str
                    return {"type": "goal_check_in", "text": goal.get("text")}

    # NEW in v115.0: Memory Check-in Logic
    for memory in profile.get("key_memories", []):
        if memory.get("check_in_sent"):
            continue # Already checked in about this memory
        try:
            memory_dt = dateparser.parse(memory.get("timestamp")).replace(tzinfo=timezone.utc)
            days_since_memory = (today_dt - memory_dt).days
            
            # Check if the memory occurred within our window for a follow-up
            if 1 <= days_since_memory <= MEMORY_CHECK_IN_WINDOW_DAYS:
                memory["check_in_sent"] = True # Mark as checked-in to prevent re-asking
                return {"type": "memory_check_in", "text": memory["memory"]}
        except (ValueError, TypeError):
            continue # Skip if timestamp is malformed

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
    
    # v120.1 FIX: Check if we have weeks directly first, before relying on LMP
    if details.get("weeks_gestation") and details.get("is_pregnant"):
        weeks = details.get("weeks_gestation")
        trimester = "TR1" if weeks <= 13 else "TR2" if 14 <= weeks <= 27 else "TR3"
        # Only update if changed
        if details.get("current_trimester") != trimester:
            details["current_trimester"] = trimester
            return True
        return False
        
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
# MODIFIED in v105.4: Replaced direct LLM call with fallback function
def _generate_behavioral_synopsis(profile):
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
    
    response = _call_llm_with_fallback(synopsis_prompt)
    if response is None:
        print("!!! LLM call failed in _generate_behavioral_synopsis after all fallbacks.")
        return None

    try:
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

# MODIFIED in v105.4: Replaced direct LLM call with fallback function
def _handle_upload_logic(file, user_query):
    if not file:
        return {'error': 'No file provided'}, 400
    
    temp_path, uploaded_file = None, None
    try:
        temp_path = os.path.join(UPLOADS_DIR, secure_filename(file.filename))
        file.save(temp_path)
        
        # This part of the GenAI API does not use the fallback logic, it's a file service.
        uploaded_file = genai.upload_file(path=temp_path, mime_type=file.mimetype)
        if not wait_for_file_to_be_active(uploaded_file.name):
            raise Exception("File processing timeout")
        
        final_prompt = None
        if file.mimetype.startswith('image/') and ENABLE_VISUAL_TRIAGE:
            final_prompt = get_visual_triage_prompt(user_query, uploaded_file)
        elif ENABLE_DOCUMENT_UPLOAD:
            # The OCR call is an LLM call, so it needs the fallback
            ocr_response = _call_llm_with_fallback("Extract all text from this document.", uploaded_file)
            if ocr_response is None:
                return {'error': 'Failed to extract text from document.'}, 500
            final_prompt = get_holistic_report_summary_prompt(user_query, ocr_response.text)
        else:
            return {'error': 'Unsupported file type or feature disabled'}, 400
        
        # The final summarization call also needs the fallback
        final_response = _call_llm_with_fallback(*final_prompt if isinstance(final_prompt, list) else [final_prompt])
        if final_response is None:
            return {'error': 'Failed to analyze the document after text extraction.'}, 500
        
        return {"reply": md.render(final_response.text)}, 200
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        if temp_path and os.path.exists(temp_path): os.remove(temp_path)
        if uploaded_file:
            try: genai.delete_file(uploaded_file.name)
            except exceptions.NotFound: pass


# MODIFIED in v105.4: Replaced direct LLM call with fallback function
def _handle_transcription_logic(file):
    if not file:
        return {'error': 'No file provided'}, 400

    temp_path, uploaded_file = None, None
    try:
        temp_path = os.path.join(UPLOADS_DIR, "voice_note.webm")
        file.save(temp_path)
        
        # File upload is not an LLM call
        uploaded_file = genai.upload_file(path=temp_path, mime_type="audio/webm")
        if not wait_for_file_to_be_active(uploaded_file.name):
            raise Exception("File processing timeout")
        
        # Transcription is an LLM call
        response = _call_llm_with_fallback("Transcribe this audio.", uploaded_file)
        if response is None:
            return {'error': 'Transcription failed after all fallbacks.'}, 500
            
        return {"transcribed_text": response.text.strip()}, 200
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        if temp_path and os.path.exists(temp_path): os.remove(temp_path)
        if uploaded_file:
            try: genai.delete_file(uploaded_file.name)
            except exceptions.NotFound: pass


# MODIFIED in v105.4: Replaced direct LLM call with fallback function
def _process_quick_log_response(profile, category, value):
    """
    Handles logging, context generation, and AI call for quick log buttons.
    """
    # 1. Save the log to the profile immediately.
    profile.setdefault('health_logs', []).insert(0, {"timestamp": datetime.now().isoformat(), "category": category, "value": value})
    
    # 2. Determine if a special follow-up is needed.
    negative_log_values = [
        'high', 'poor', 'terrible', 'anxious', 'sad', 'stressed', 
        'overwhelmed', 'exhausted', 'headache', 'cramps', 'painful'
    ]
    is_negative = value in negative_log_values

    # 3. Create the special context for the prompt.
    special_context = {
        "type": "dynamic_confirmation",
        "log_details": {"category": category, "value": value},
        "is_negative": is_negative
    }
    
    # 4. Format the full prompt and make the AI call.
    context_prompt = format_profile_for_prompt(
        profile,
        chatbot_name=CHATBOT_NAME,
        special_context=special_context,
        milestones_data=MILESTONES_DATA # NEW in v121.0: Ensure persona has full context
    )
    
    # We pass a simple placeholder message as the user input is implicit (the button click)
    response = _call_llm_with_fallback(f"{context_prompt}\n(User just clicked a quick log button)")

    if response is None:
        lang_data = load_language_data(profile.get('language', 'en'))
        reply = lang_data.get("quick_log_confirm_fallback", "Okay, I've logged that for you.")
    else:
        reply = response.text.strip()

    # NEW in v108.0: Also log the interaction to the chat_log for UI persistence.
    rendered_reply = md.render(reply)
    profile.setdefault("chat_log", []).extend([
        {'role': 'user', 'content': f"Quick Log: {category.title()} - {value.title()}"},
        {'role': 'assistant', 'content': rendered_reply}
    ])
    profile['chat_log'] = profile['chat_log'][-MAX_CHAT_LOG_ENTRIES:]
    
    return {"reply": rendered_reply}


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

# --- NEW in v119.5: Cycle Phase Calculation Helper ---
def _calculate_cycle_phase(profile):
    """
    Determines the current biological cycle phase based on the last logged period.
    Returns: 'menstrual', 'follicular', 'ovulation', 'luteal', or None
    """
    period_data = profile.get("period_data", {})
    cycles = period_data.get("cycles", [])
    
    if not cycles:
        return None
        
    last_start_str = cycles[0].get("start_date")
    if not last_start_str:
        return None
        
    try:
        last_start_dt = datetime.strptime(last_start_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        cycle_day = (today - last_start_dt).days + 1
        
        if cycle_day < 1: return None # Future date or error
        
        # Standard Phase Approximation (Assuming ~28 day cycle)
        if 1 <= cycle_day <= 5:
            return 'menstrual'
        elif 6 <= cycle_day <= 13:
            return 'follicular'
        elif 14 <= cycle_day <= 17:
            return 'ovulation'
        elif cycle_day >= 18:
            # Cap it reasonably at 45 days to avoid "Luteal" forever if they miss logging
            if cycle_day < 45:
                return 'luteal'
            else:
                return None # Cycle too long/missed logging
                
    except (ValueError, TypeError):
        return None
    
    return None

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

# NEW in v105.5: Automatically update age-based profile data
def _recalculate_age_dependent_categories(profile):
    """
    Recalculates user's age and primary category based on their DOB.
    This ensures the profile evolves as the user gets older.
    """
    dob_str = profile.get("dob")
    if not dob_str:
        return profile # Cannot proceed without DOB, handles legacy profiles

    try:
        dob = date.fromisoformat(dob_str)
        today = date.today()
        # Calculate current age
        current_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        # Determine the correct primary category based on current age
        if current_age <= 19: correct_category = "Adolescence/Teen"
        elif 20 <= current_age <= 39: correct_category = "Young Adulthood"
        elif 40 <= current_age <= 59: correct_category = "Middle Adulthood"
        else: correct_category = "Senior/Postmenopausal Life"

        # Update profile only if there's a change
        if profile.get("age") != current_age or profile.get("primary_category") != correct_category:
            print(f"--- Updating user age from {profile.get('age')} to {current_age} and category from '{profile.get('primary_category')}' to '{correct_category}' ---")
            profile["age"] = current_age
            profile["primary_category"] = correct_category
    except (ValueError, TypeError):
        # Handles cases where DOB might be improperly formatted
        pass
        
    return profile


# NEW in v107.0 to handle internal actions
def _handle_internal_action(action_data, profile):
    """Handles non-chat, UI-driven actions like button clicks."""
    action_type = action_data.get('action')
    
    if action_type == 'select_video_category':
        selected_category = action_data.get('category')
        response_data = _handle_video_suggestion(profile, selected_category=selected_category)
        # No need to save profile here as video suggestion logic doesn't modify it
        return jsonify(response_data)

    # Fallback for unknown actions
    return jsonify({"reply": "I'm sorry, I didn't understand that action."})

# MODIFIED in v116.1: Move streak update and save_profile to the end for consistency
def _process_chat_message_for_auth_user(user_message, profile, profile_hash):
    # Recalculate dynamic and analytical data on every interaction.
    profile = _recalculate_age_dependent_categories(profile)
    calculate_child_ages(profile)
    calculate_trimester(profile)
    profile = _update_synopsis_if_needed(profile)
    
    proactive_summary = _check_and_generate_monthly_summary(profile)

    insights = get_conversation_summary(user_message)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_message": user_message,
        "extracted_intent": insights if insights and 'error' not in insights else {}
    }
    profile.setdefault("interaction_log", []).insert(0, log_entry)
    
    summary_keywords = ["about me", "my profile", "my summary", "what do you know"]
    is_summary_request = any(keyword in user_message.lower() for keyword in summary_keywords)


    if insights.get('error'): return jsonify({"reply": md.render("I'm having a little trouble understanding. Please rephrase.")})

    # --- BUGFIX in v115.1: Immediately save suggested memory to decouple features ---
    if insights.get("suggested_memory"):
        memory_text = insights.get("suggested_memory")
        profile.setdefault("key_memories", [])
        new_memory = {"memory": memory_text, "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d')}
        if not any(mem['memory'] == new_memory['memory'] for mem in profile["key_memories"]):
            profile["key_memories"].insert(0, new_memory)
            profile["key_memories"] = profile["key_memories"][:MAX_KEY_MEMORIES]
    # --- End BUGFIX ---

    # --- Start of Core Action Handlers ---

    if ENABLE_CHART_VISUALIZATION and insights.get('query_chart'):
        chart_query = insights.get('query_chart')
        json_response = {"reply": md.render("Of course, here is the visualization you requested."), "chart_type": chart_query.get('type')}
        if chart_query.get('target_date'):
            json_response["target_date"] = chart_query.get('target_date')
        if proactive_summary:
            json_response["proactive_summary"] = proactive_summary

        profile.setdefault("chat_log", []).extend([
            {'role': 'user', 'content': user_message},
            {'role': 'assistant', 'content': json_response['reply']}
        ])
        profile['chat_log'] = profile['chat_log'][-MAX_CHAT_LOG_ENTRIES:]
        # BUGFIX in v116.1: Moved streak update and save to end of function
        
    pending_question = session.get('pending_question')
    if pending_question:
        affirmative_keywords = ['yes', 'sure', 'ok', 'okay', 'please', 'do it']
        is_affirmative = any(keyword in user_message.lower() for keyword in affirmative_keywords)
        action_response = None
        
        # MODIFIED in v115.1: Make reminder clarification more robust
        if pending_question == 'clarify_reminder_creation':
            potential_reminder_context = session.pop('pending_action_context', None)
            session.pop('pending_question', None) # Clear immediately to prevent loops
            if is_affirmative and potential_reminder_context:
                action_to_create = {
                    "text": potential_reminder_context.get('text'), 
                    "due_date": potential_reminder_context.get('date')
                }
                # If the user provides more text, let the LLM parse it for better context
                if user_message.lower() not in affirmative_keywords:
                    insights = get_conversation_summary(f"remind me about {user_message}")
                    if insights.get('reminder_action'):
                        action_to_create['text'] = insights['reminder_action'].get('text', action_to_create['text'])
                        action_to_create['due_date'] = insights['reminder_action'].get('due_date', action_to_create['due_date'])

                profile, action_response, _ = handle_reminder_action(action_to_create, profile)
            else:
                action_response = "Okay, no problem. I won't set a reminder this time."
        
        elif pending_question == 'confirm_life_event_update': # Handles end of pregnancy
            life_event_context = session.pop('pending_action_context', None)
            if is_affirmative and life_event_context:
                profile['secondary_details']['is_pregnant'] = False
                profile['secondary_details']['is_parent'] = True
                
                provided_date = life_event_context.get('date')
                if provided_date:
                    dob_str = normalize_date_string(provided_date)
                    profile['secondary_details'].setdefault('child_dobs', []).append(dob_str)
                    profile['secondary_details']['num_children'] = len(profile['secondary_details']['child_dobs'])
                    action_response = "Thank you! I've updated your profile to reflect your new parenthood journey and noted the date. Congratulations again!"
                else:
                    session['pending_question'] = 'get_newborn_dob'
                    action_response = "That's wonderful! I've updated your profile. To help keep track, could you share your baby's date of birth?"
            else:
                 action_response = "Okay, I won't make any changes to your profile for now."
                 
        elif pending_question == 'get_newborn_dob': # NEW in v105.5
            dob_str = normalize_date_string(user_message)
            profile['secondary_details'].setdefault('child_dobs', []).append(dob_str)
            profile['secondary_details']['num_children'] = len(profile['secondary_details']['child_dobs'])
            action_response = f"Got it, I've added {dob_str} to your profile. Thank you for sharing!"

        elif pending_question == 'confirm_start_pregnancy': # NEW in v105.6
            if is_affirmative:
                profile['secondary_details']['is_pregnant'] = True
                session['pending_question'] = 'get_lmp_date'
                action_response = "Okay, I've updated your profile. To help calculate your gestation and provide timely milestones, could you please share the first day of your last menstrual period (LMP)?"
            else:
                action_response = "No problem. I won't update your profile. How else can I help?"

        elif pending_question == 'get_lmp_date': # NEW in v105.6
            lmp_date_str = normalize_date_string(user_message)
            profile['secondary_details']['lmp_date'] = lmp_date_str
            action_response = f"Thank you! I've saved that date. Based on that, I'll keep you updated on your pregnancy journey."

        elif pending_question == 'confirm_start_perimenopause': # NEW in v105.6
            if is_affirmative:
                profile['secondary_details']['is_perimenopausal'] = True
                action_response = "Thank you. I've updated your profile. Please know you can always talk to me about any symptoms or feelings you're experiencing."
            else:
                action_response = "Understood. I will not update your profile. What's on your mind?"

        if 'pending_question' not in session:
            session.pop('pending_question', None)
            session.pop('pending_action_context', None)
            
        if action_response:
            response_payload = {"reply": md.render(action_response)}
            if proactive_summary:
                response_payload["proactive_summary"] = proactive_summary
            profile.setdefault("chat_log", []).extend([
                {'role': 'user', 'content': user_message},
                {'role': 'assistant', 'content': response_payload['reply']}
            ])
            profile['chat_log'] = profile['chat_log'][-MAX_CHAT_LOG_ENTRIES:]
            # BUGFIX in v116.1: Moved streak update and save to end of function

    action_response = None
    new_pending_question = None
    special_context = None 
    education_tidbit = None 
    action_handlers = {'medication_log': handle_medication_log, 'period_action': handle_period_action, 'set_goal': handle_set_goal, 'reminder_action': handle_reminder_action}
    
    # NEW in v115.0: Handle "Real Talk" mode as a special context override
    if insights.get('request_real_talk'):
        special_context = {"type": "real_talk_mode"}
    # NEW in v117.0: Handle accepting a weekly insight
    elif insights.get('accept_weekly_insight'):
        insight_text, image_url = _generate_and_save_insight_image(profile)
        if image_url:
            response_payload = {
                "reply": "Here is your weekly insight! ✨",
                "ui_component": "weekly_insight_card",
                "data": {
                    "image_url": image_url,
                    "insight_text": insight_text
                }
            }
        else:
            response_payload = {"reply": "I couldn't generate your insight right now, but let's try again later!"}
        # This is a final action, so we can save and return directly
        profile.setdefault("chat_log", []).extend([
            {'role': 'user', 'content': user_message},
            {'role': 'assistant', 'content': response_payload['reply']}
        ])
        profile['chat_log'] = profile['chat_log'][-MAX_CHAT_LOG_ENTRIES:]
        profile = _update_daily_streak(profile)
        save_profile(profile_hash, profile)
        return jsonify(response_payload)

    # --- NEW v121.0: Interactive Tool Handlers ---
    if not action_response and insights.get('request_breathing_tool'):
        # 1. Immediate Empathy via LLM
        context_prompt = format_profile_for_prompt(profile, chatbot_name=CHATBOT_NAME, special_context={"type": "dynamic_confirmation", "log_details": {"category": "stress", "value": "high"}, "is_negative": True}, milestones_data=MILESTONES_DATA)
        response = _call_llm_with_fallback(f"{context_prompt}\nUser says: '{user_message}'. Respond with deep empathy, then invite them to follow the breathing bubble.")
        reply_text = response.text.strip() if response else "I hear you. Let's take a moment to breathe together."
        
        response_payload = {
            "reply": md.render(reply_text),
            "ui_component": "breathing_tool" # This triggers the JS animation
        }
        
        # Save to logs and return
        profile.setdefault("chat_log", []).extend([
            {'role': 'user', 'content': user_message},
            {'role': 'assistant', 'content': response_payload['reply']}
        ])
        profile['chat_log'] = profile['chat_log'][-MAX_CHAT_LOG_ENTRIES:]
        save_profile(profile_hash, profile)
        return jsonify(response_payload)

    elif not action_response and insights.get('request_checklist'):
        topic = insights['request_checklist'].get('topic', 'checklist')
        checklist_items = []
        checklist_title = f"{topic.title()} Checklist"

        # Special Case: Vaccines (Pull from Data)
        if "vaccine" in topic.lower() or "shot" in topic.lower():
            # Try to get age-specific vaccines
            from user_profiler import calculate_baby_age_details
            age_details = calculate_baby_age_details(profile)
            if age_details and MILESTONES_DATA:
                bucket_data = MILESTONES_DATA.get("postnatal_by_age", {}).get(age_details['bucket_key'])
                if bucket_data and bucket_data.get('vaccinations'):
                    checklist_items = bucket_data['vaccinations']
                    checklist_title = f"Vaccines due at {bucket_data.get('title')}"

        # General Case: Ask LLM to generate list items
        if not checklist_items:
            list_prompt = f"Generate a concise list of 5-10 essential items for a '{topic}'. Return ONLY a raw JSON list of strings. Example: [\"Item 1\", \"Item 2\"]."
            list_response = _call_llm_with_fallback(list_prompt)
            try:
                cleaned_list = list_response.text.strip().lstrip("```json").rstrip("```").strip()
                checklist_items = json.loads(cleaned_list)
            except:
                checklist_items = ["Notebook", "Water", "Essentials"] # Fallback

        response_payload = {
            "reply": f"Here is a checklist for **{topic}**. You can check them off as you go!",
            "ui_component": "checklist",
            "data": {
                "title": checklist_title,
                "items": checklist_items
            }
        }
        
        # Save and return
        profile.setdefault("chat_log", []).extend([
            {'role': 'user', 'content': user_message},
            {'role': 'assistant', 'content': response_payload['reply']}
        ])
        profile['chat_log'] = profile['chat_log'][-MAX_CHAT_LOG_ENTRIES:]
        save_profile(profile_hash, profile)
        return jsonify(response_payload)
    # ---------------------------------------------

    if not special_context:
        for action_type, handler in action_handlers.items():
            if insights.get(action_type):
                profile, action_response, new_pending_question = handler(insights[action_type], profile)
                break

    if not action_response and not special_context and insights.get('provide_dob'):
        profile, action_response, new_pending_question = _handle_dob_update(insights['provide_dob'], profile)
            
    # --- v120.1: ROBUST PREGNANCY UPDATE HANDLER ---
    if not action_response and not special_context and insights.get('life_event_update'):
        event_data = insights.pop('life_event_update')
        event_type = event_data.get('type')

        if event_type == 'update_pregnancy_weeks':
            weeks = event_data.get('weeks')
            if weeks:
                profile.setdefault('secondary_details', {})
                profile['secondary_details']['is_pregnant'] = True
                profile['secondary_details']['weeks_gestation'] = weeks
                
                # MATHEMATICAL BACK-CALCULATION of LMP
                # LMP = Today - (Weeks * 7) days
                estimated_lmp = datetime.now() - timedelta(weeks=weeks)
                profile['secondary_details']['lmp_date'] = estimated_lmp.strftime('%Y-%m-%d')
                
                calculate_trimester(profile) # Update trimester immediately
                
                action_response = f"Got it! I've updated your profile to **{weeks} weeks pregnant**. (I've estimated your start date based on this so I can keep tracking for you!)"
        
        elif event_type == 'start_pregnancy' and not profile.get('secondary_details', {}).get('is_pregnant'):
            session['pending_question'] = 'confirm_start_pregnancy'
            action_response = "That's wonderful news! To help me provide the most relevant information, may I update your profile to reflect that you are pregnant?"
        elif event_type == 'start_perimenopause' and not profile.get('secondary_details', {}).get('is_perimenopausal'):
            session['pending_question'] = 'confirm_start_perimenopause'
            action_response = "Thank you for sharing that. It can be a confusing time. To help me offer more relevant support, would you like me to update your profile to note that you are navigating perimenopause?"
        elif event_type == 'pregnancy_to_parenting' and profile.get('secondary_details', {}).get('is_pregnant'):
            session['pending_question'] = 'confirm_life_event_update'
            session['pending_action_context'] = event_data
            action_response = "That's wonderful news! It sounds like you've welcomed your baby. Shall I update your profile to reflect that you are now parenting?"
        else:
             action_response = None
    # -----------------------------------------------

    if not action_response and not special_context and ENABLE_CONTEXTUAL_REMINDERS and insights.get('potential_reminder'):
        potential_reminder_data = insights.pop('potential_reminder')
        session['pending_question'] = 'clarify_reminder_creation'
        session['pending_action_context'] = potential_reminder_data
        action_response = f"I noticed you mentioned your '{potential_reminder_data.get('text')}'. Would you like me to set a reminder for that?"

    if not action_response and not special_context and ENABLE_EXPANDED_LOGGING and insights.get('health_log'):
        log_data = insights['health_log']
        profile.setdefault('health_logs', []).insert(0, {"timestamp": datetime.now().isoformat(), **log_data})
        
        category, value = log_data.get('category'), log_data.get('value')
        
        if category and value:
            negative_log_values = ['high', 'poor', 'terrible', 'anxious', 'sad', 'stressed', 'overwhelmed', 'exhausted', 'headache', 'cramps', 'painful']
            is_negative = value in negative_log_values
            special_context = {"type": "dynamic_confirmation", "log_details": log_data, "is_negative": is_negative}

    if new_pending_question:
        session['pending_question'] = new_pending_question
        
    if action_response:
        response_payload = {"reply": md.render(action_response)}
        if proactive_summary:
            response_payload["proactive_summary"] = proactive_summary
        profile.setdefault("chat_log", []).extend([
            {'role': 'user', 'content': user_message},
            {'role': 'assistant', 'content': response_payload['reply']}
        ])
        profile['chat_log'] = profile['chat_log'][-MAX_CHAT_LOG_ENTRIES:]
        # BUGFIX in v116.1: Moved streak update and save to end of function
    
    # --- End of Core Action Handlers ---

    # Re-use json_response if it was generated by chart logic but didn't return
    if 'json_response' in locals() and not action_response and not special_context:
        pass # Let it fall through to the final save and return

    is_follow_up = False
    last_discussed_program_context = None
    suggested_program_object = None

    follow_up_program, profile = handle_follow_up_request(profile, user_message)
    if follow_up_program:
        is_follow_up = True
        suggested_program_object = follow_up_program
    else:
        new_suggestion = get_program_suggestion(profile, user_message)
        if new_suggestion:
            suggested_program_object = new_suggestion
            profile.setdefault("proactive_assistance", {})["pending_program_offer"] = new_suggestion['name']
            profile["proactive_assistance"]["last_program_suggestion_ts"] = datetime.now(timezone.utc).isoformat()
            
            question_is_about_suggestion = any(keyword in user_message.lower() for keyword in ["what is", "tell me about", "explain"])
            if question_is_about_suggestion:
                 special_context = { "type": "explain_and_offer_program", "program_name": new_suggestion['name']}
    
    if not suggested_program_object:
        video_keywords = ["video", "yoga", "exercise", "workout", "routine"]
        if any(keyword in user_message.lower() for keyword in video_keywords):
            response_payload = _handle_video_suggestion(profile)
            if proactive_summary:
                response_payload["proactive_summary"] = proactive_summary

            profile.setdefault("chat_log", []).extend([
                {'role': 'user', 'content': user_message},
                {'role': 'assistant', 'content': response_payload.get('reply', 'Here are some videos for you.')}
            ])
            profile['chat_log'] = profile['chat_log'][-MAX_CHAT_LOG_ENTRIES:]
            # BUGFIX in v116.1: Moved streak update and save to end of function

    # NEW in v117.0: Proactively offer weekly insight
    if not special_context and not action_response and not ('response_payload' in locals()):
        if _should_offer_weekly_insight(profile):
            special_context = {"type": "offer_weekly_summary"}
            profile.setdefault("proactive_assistance", {})["last_insight_offered_date"] = datetime.now(timezone.utc).strftime('%Y-%m-%d')


    if not special_context: 
        tidbit_text, tidbit_id = _get_relevant_education_tidbit(profile, user_message)
        if tidbit_text:
            education_tidbit = tidbit_text
            profile.setdefault("shown_education_tidbits", []).append(tidbit_id)
            
    if not special_context:
        newly_unlocked_badges = _check_for_new_achievements(profile)
        if newly_unlocked_badges:
            special_context = {"type": "achievement_unlocked", "badges": newly_unlocked_badges}


    proactive_context = get_proactive_context(profile)
    
    # MODIFIED in v121.0: Added milestones_data to prompt
    context_prompt = format_profile_for_prompt(
        profile, chatbot_name=CHATBOT_NAME, proactive_context=proactive_context, suggested_program_object=suggested_program_object, is_follow_up=is_follow_up,
        last_discussed_program_context=last_discussed_program_context, enable_ovulation_tracker=ENABLE_OVULATION_TRACKER, enable_realtime_log_context=ENABLE_REALTIME_LOG_CONTEXT,
        is_summary_request=is_summary_request, special_context=special_context, education_tidbit=education_tidbit,
        milestones_data=MILESTONES_DATA # NEW in v121.0
    )
    
    # If an action response was generated, use it. Otherwise, call the LLM.
    if 'response_payload' in locals() and response_payload:
        pass
    elif 'json_response' in locals() and json_response:
        response_payload = json_response
    elif action_response:
        response_payload = {"reply": md.render(action_response)}
    else:
        response = _call_llm_with_fallback(f"{context_prompt}\n{user_message}")

        if response is None:
            reply = "I'm sorry, but I'm currently unable to process your request right now. Please try again in a moment."
        else:
            raw_reply = response.text
            memory_match = re.search(r"\[SUGGEST_MEMORY:\s*(.*?)\]", raw_reply)
            if memory_match:
                reply = re.sub(r"\[SUGGEST_MEMORY:\s*(.*?)\]", "", raw_reply).strip()
            else:
                reply = raw_reply
                
        rendered_reply = md.render(reply)
        response_payload = {"reply": rendered_reply}

    # Finalize and Save
    profile.setdefault("chat_log", []).extend([
        {'role': 'user', 'content': user_message},
        {'role': 'assistant', 'content': response_payload.get('reply', '...')}
    ])
    profile['chat_log'] = profile['chat_log'][-MAX_CHAT_LOG_ENTRIES:]

    # BUGFIX in v116.1: Ensure streak is updated and profile is saved on EVERY interaction.
    profile = _update_daily_streak(profile)
    save_profile(profile_hash, profile)
    
    if proactive_summary and "proactive_summary" not in response_payload:
        response_payload["proactive_summary"] = proactive_summary
        
    return jsonify(response_payload)


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

    # NEW in v118.1: A dedicated route to serve the hosting page for the native app's WebView
    @app.route('/embed/native')
    def native_embed():
        return render_template('native_embed.html')
        
    # MODIFIED in v116.0: Add streak data to config payload
    # MODIFIED in v119.2: Return current persona in config
    # MODIFIED in v119.5: Return current cycle phase for UI syncing
    @app.route('/api/v1/config')
    @token_required
    def api_config():
        auth_mode = "otp" if app.config.get('ENABLE_EMAIL_OTP_API_VERIFICATION') else "guest"
        lang_code = 'en'
        streak_data = {"current": 0} # Default for guests
        persona = "bestie" # Default persona
        current_phase = None # NEW in v119.5

        if g.profile and not g.is_guest:
            lang_code = g.profile.get('language', 'en')
            persona = g.profile.get('persona', 'bestie') # Load persona
            if ENABLE_GAMIFICATION_STREAKS:
                streak_data = g.profile.get("streaks", {"current": 0})
            if ENABLE_CYCLE_SYNCED_UI:
                current_phase = _calculate_cycle_phase(g.profile) # Calculate phase
        
        lang_data = load_language_data(lang_code)

        return jsonify({
            "auth_mode": auth_mode,
            "lang": lang_data,
            "streaks": streak_data,
            "persona": persona,
            "current_phase": current_phase # Return to frontend
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
    
    # NEW in v118.0: Secure endpoint for the authenticated native mobile app
    if app.config.get('ENABLE_NATIVE_APP_AUTH'):
        @app.route('/api/v1/auth/native_app_session', methods=['POST'])
        def api_native_app_session():
            app_secret_key = request.headers.get('X-App-Secret-Key')
            correct_key = app.config.get('NATIVE_APP_SECRET_KEY')

            if not correct_key or not app_secret_key or not secrets.compare_digest(app_secret_key, correct_key):
                return jsonify({"error": "Unauthorized: Invalid application secret key."}), 401
            
            data = request.json
            identifier = data.get('identifier')
            if not identifier:
                return jsonify({"error": "User identifier is required."}), 400
            
            profile_hash = get_profile_hash(identifier)
            profile = load_profile(profile_hash)

            if not profile:
                # If the user doesn't exist, create a profile for them on the fly
                name = data.get('name')
                age_str = data.get('age')
                if not name or not age_str:
                    return jsonify({"error": "Name and age are required for new user creation."}), 400
                
                try:
                    phone = identifier if '@' not in identifier else ''
                    primary_email = identifier if '@' in identifier else ''
                    
                    profile = create_user_profile(name, primary_email, phone, int(age_str), {}, 'en')
                    save_profile(profile_hash, profile)
                except (ValueError, TypeError) as e:
                    return jsonify({"error": f"Invalid data for profile creation: {e}"}), 400

            # If profile exists or was just created, issue a long-lived token
            token = generate_token(profile_hash)
            return jsonify({"status": "success", "token": token})

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
        request_data = request.get_json()
        
        # --- NEW in v107.0: Handle internal UI actions ---
        if 'action' in request_data:
            return _handle_internal_action(request_data, g.profile)

        user_message = request_data.get('message', '')
        if not user_message:
            return jsonify({"error": "Message cannot be empty."}), 400
        
        if g.is_guest and app.config.get('ENABLE_EMAIL_OTP_API_VERIFICATION'):
            insights = get_conversation_summary(user_message)
            if insights.get('period_action') or insights.get('reminder_action'):
                return jsonify({"reply": "To use this feature, please create an account.", "action": "prompt_signup"})
        
        if g.is_guest:
             response = _call_llm_with_fallback(f"You are a helpful assistant. Answer the user's question: {user_message}")
             if response is None:
                 return jsonify({"reply": "Sorry, I'm unable to process your request right now."})
             return jsonify({"reply": md.render(response.text)})

        return _process_chat_message_for_auth_user(user_message, g.profile, g.profile_hash)

    # NEW in v108.0: Endpoint to fetch recent chat history for UI persistence.
    @app.route('/api/v1/chat_history', methods=['GET'])
    @token_required
    def api_chat_history():
        if g.is_guest:
            return jsonify([]) # Guests have no server-side history
        chat_log = g.profile.get('chat_log', [])
        return jsonify(chat_log)

    # --- NEW in v120.0: Proactive Greeting Endpoint ---
    @app.route('/api/v1/greet', methods=['POST'])
    @token_required
    def api_greet():
        if not ENABLE_PROACTIVE_GREETING:
            return jsonify({"status": "no_greet", "reason": "disabled"})
            
        if g.is_guest:
            # Guests don't have enough data for a personalized greeting usually
            return jsonify({"status": "no_greet", "reason": "guest_mode"})

        profile = g.profile
        proactive_data = profile.setdefault("proactive_assistance", {})
        last_greet_str = proactive_data.get("last_proactive_greet_ts")
        
        # 1. Spam Check: Don't greet if we greeted (or user chatted) recently
        now = datetime.now(timezone.utc)
        
        # Also check last interaction time to avoid greeting someone who just spoke
        interaction_log = profile.get("interaction_log", [])
        if interaction_log:
            last_interaction_str = interaction_log[0].get("timestamp")
            try:
                last_interaction_dt = dateparser.parse(last_interaction_str)
                # Normalize naive/aware datetimes
                if last_interaction_dt.tzinfo is None: last_interaction_dt = last_interaction_dt.replace(tzinfo=timezone.utc)
                
                # If user spoke within the window, don't interrupt
                if (now - last_interaction_dt).total_seconds() < (PROACTIVE_GREET_COOLDOWN_HOURS * 3600):
                    return jsonify({"status": "no_greet", "reason": "recent_interaction"})
            except: pass

        if last_greet_str:
            try:
                last_greet_dt = dateparser.parse(last_greet_str)
                if last_greet_dt.tzinfo is None: last_greet_dt = last_greet_dt.replace(tzinfo=timezone.utc)
                if (now - last_greet_dt).total_seconds() < (PROACTIVE_GREET_COOLDOWN_HOURS * 3600):
                    return jsonify({"status": "no_greet", "reason": "cooldown"})
            except: pass

        # 2. Generate Greeting
        greeting_text = _process_proactive_greeting(profile)
        
        # 3. Update State
        proactive_data["last_proactive_greet_ts"] = now.isoformat()
        
        # 4. Save to Chat Log (so it persists in history)
        rendered_reply = md.render(greeting_text)
        profile.setdefault("chat_log", []).append({'role': 'assistant', 'content': rendered_reply})
        profile['chat_log'] = profile['chat_log'][-MAX_CHAT_LOG_ENTRIES:]
        
        save_profile(g.profile_hash, profile)
        
        return jsonify({"status": "success", "reply": rendered_reply})

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

    # MODIFIED in v104.1 to use the new AI-powered response generator
    @app.route('/api/v1/quick_log', methods=['POST'])
    @token_required
    def api_quick_log():
        if g.is_guest: return jsonify({"error": "This feature requires an account."}), 403
        data = request.get_json()
        category, value = data.get('category'), data.get('value')
        if not category or not value: return jsonify({"error": "Invalid log data."}), 400
        
        response = _process_quick_log_response(g.profile, category, value)
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

    # NEW in v119.1: Burner Mode Endpoint
    @app.route('/api/v1/privacy/burn_history', methods=['POST'])
    @token_required
    def api_burn_history():
        """
        Privacy feature to 'burn' recent chat history.
        1. Clears the persistable 'chat_log' (used for UI history) completely.
        2. Filters the 'interaction_log' (used for AI context) to remove entries from the last 24 hours.
        """
        if g.is_guest: 
            return jsonify({'error': 'Feature not available for guests.'}), 403
        
        # 1. Clear UI Chat Log completely to ensure immediate visual privacy
        g.profile['chat_log'] = []
        
        # 2. Filter Interaction Log (Backend Memory) for the burn window
        # We use simple naive comparison because stored timestamps are typically naive ISO (local time)
        now = datetime.now()
        cutoff = now - timedelta(hours=BURN_WINDOW_HOURS)
        
        original_log = g.profile.get('interaction_log', [])
        filtered_log = []
        
        for entry in original_log:
            try:
                # Parse the timestamp. Assuming stored format matches datetime.now().isoformat()
                entry_dt = dateparser.parse(entry['timestamp'])
                
                # Normalize timezone info for comparison if necessary
                # If stored is naive and cutoff is naive, we are good.
                # If one is aware, we strip tz from it to compare loosely (safest for this 'panic button' logic)
                if entry_dt.tzinfo and not cutoff.tzinfo:
                    entry_dt = entry_dt.replace(tzinfo=None)
                elif not entry_dt.tzinfo and cutoff.tzinfo:
                    cutoff = cutoff.replace(tzinfo=None)

                # Keep only entries OLDER than the cutoff
                if entry_dt < cutoff:
                    filtered_log.append(entry)
                    
            except (ValueError, TypeError):
                # If we can't parse the date, keep the entry to be safe/conservative, 
                # or delete it? For 'Burner', safer to delete malformed recent-looking data, 
                # but here we preserve data integrity.
                filtered_log.append(entry)
        
        g.profile['interaction_log'] = filtered_log
        
        # 3. Save the sanitized profile
        save_profile(g.profile_hash, g.profile)
        
        return jsonify({"status": "success", "message": "Recent history incinerated."})

    # NEW in v119.2: Endpoint to set persona
    @app.route('/api/v1/set_persona', methods=['POST'])
    @token_required
    def api_set_persona():
        if g.is_guest: 
            return jsonify({'error': 'Guest users cannot change persona.'}), 403
        
        data = request.json
        new_persona = data.get('persona')
        
        if new_persona not in ['bestie', 'professional', 'coach']:
            return jsonify({'error': 'Invalid persona selected.'}), 400
            
        g.profile['persona'] = new_persona
        save_profile(g.profile_hash, g.profile)
        
        return jsonify({"status": "success", "persona": new_persona})


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
            data = request.json
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
        request_data = request.get_json()
        
        # --- NEW in v107.0: Handle internal UI actions ---
        if 'action' in request_data:
            profile_hash = session.get('profile_hash')
            if not profile_hash: return jsonify({"error": "Authentication required."}), 403
            profile = load_profile(profile_hash)
            if not profile: return jsonify({"error": "Profile not found."}), 404
            return _handle_internal_action(request_data, profile)

        user_message = request_data.get('message', '')
        if not user_message:
            return jsonify({"error": "Message cannot be empty."}), 400
        
        if 'onboarding_state' in session:
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
            
            return _process_chat_message_for_auth_user(user_message, profile, session['profile_hash'])
        
        elif session.get('is_guest'):
            # --- RESTORED v98.8: LLM Caching for Guests ---
            if ENABLE_LLM_CACHING:
                cache_key = re.sub(r'[^\w\s]', '', user_message).lower().strip()
                if cache_key in llm_response_cache:
                    cached_reply = llm_response_cache[cache_key]
                    return jsonify({"reply": md.render(cached_reply)})

            insights = get_conversation_summary(user_message)
            if insights.get('period_action') or insights.get('reminder_action'):
                return jsonify({"reply": "To use this feature, please create an account.", "action": "prompt_signup"})
            
            response = _call_llm_with_fallback(f"You are a helpful assistant. Answer the user's question: {user_message}")
            if response is None:
                return jsonify({"reply": "Sorry, I'm unable to process your request right now."})

            reply_text = response.text

            if ENABLE_LLM_CACHING:
                if len(llm_response_cache) > MAX_CACHE_SIZE:
                    llm_response_cache.clear()
                llm_response_cache[cache_key] = reply_text
            
            return jsonify({"reply": md.render(reply_text)})
        return jsonify({"error": "No active session"})
    
    # NEW in v108.0: Endpoint to fetch recent chat history for UI persistence.
    @app.route('/chat_history', methods=['GET'])
    def chat_history():
        profile_hash = session.get('profile_hash')
        if not profile_hash:
            return jsonify([]) # No session, no history
        
        profile = load_profile(profile_hash)
        if not profile:
            return jsonify([])
        
        chat_log = profile.get('chat_log', [])
        return jsonify(chat_log)

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

    # MODIFIED in v104.1 to use the new AI-powered response generator
    @app.route('/quick_log', methods=['POST'])
    def quick_log():
        if 'profile_hash' not in session: return jsonify({"error": "Authentication required."}), 403
        profile_hash = session.get('profile_hash')
        profile = load_profile(profile_hash)
        if not profile: return jsonify({"error": "Profile not found."}), 404
        data = request.get_json()
        category, value = data.get('category'), data.get('value')
        if not category or not value: return jsonify({"error": "Invalid log data."}), 400
        
        response = _process_quick_log_response(profile, category, value)
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

# --- NEW in v117.0: Endpoint to serve generated insight images ---
@app.route('/shared_insights/<filename>')
def shared_insight(filename):
    return send_from_directory(SHARED_INSIGHTS_DIR, filename)

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
# MODIFIED in v107.1 for reliability
def _parse_life_events_from_text(user_text, age):
    """Uses AI to parse natural language into structured secondary_details."""
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
    3.  If the user mentions being a parent, a new mom, or having a child, you MUST include `"is_parent": true`.
    4.  DO NOT attempt to extract the child's age or any other numeric data. Focus only on the boolean life stage.
    5.  If the user's text is vague or doesn't match any category, return an empty JSON object `{{}}`.

    --- EXAMPLES ---
    User Text: "I'm trying to have a baby."
    {{ "is_trying_to_conceive": true }}

    User Text: "I'm 14 weeks pregnant and I already have a two year old."
    {{ "is_pregnant": true, "is_parent": true }}
    
    User Text: "I am a new mom, my baby is 3 months old."
    {{ "is_parent": true }}

    User Text: "I think I'm starting perimenopause, the symptoms are crazy."
    {{ "is_perimenopausal": true }}
    
    User Text: "I'm not really focused on anything specific right now"
    {{}}
    ---
    Now, process this user's text: "{user_text}"
    """
    response = _call_llm_with_fallback(prompt)
    if response is None:
        return {} # Return empty on LLM failure
        
    try:
        cleaned_response = response.text.strip().lstrip("```json").rstrip("```").strip()
        return json.loads(cleaned_response)
    except Exception:
        return {} # Return empty on any parsing failure

# MODIFIED in v107.3 to fix onboarding data flow
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
            response_payload['ui_component'] = 'language_picker' # FIX v107.2
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
            response_payload['ui_component'] = 'language_picker' # FIX v107.2

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
        profile_data['secondary_details'] = secondary_details

        # --- FIX v106.1 & v107.1: Robustly check if we need to ask for a DOB ---
        if secondary_details.get('is_parent'):
            next_question = lang_data.get('onboarding_ask_child_dob', '')
            next_step = 'awaiting_child_dob'
        else:
            # If not a parent, finalize profile
            return _finalize_onboarding(profile_hash, onboarding_data, is_api_call)
    
    elif step == 'awaiting_child_dob': # NEW state in v106.1
        dob_str = normalize_date_string(user_message)
        # --- FIX v107.3: Correctly merge DOB into profile_data before finalizing ---
        profile_data.setdefault('secondary_details', {}).setdefault('child_dobs', []).append(dob_str)
        profile_data['secondary_details']['num_children'] = len(profile_data['secondary_details']['child_dobs'])
        # Now that we have the final piece of info, finalize the profile
        return _finalize_onboarding(profile_hash, onboarding_data, is_api_call)

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

# MODIFIED in v110.3: Fix onboarding race condition by pre-populating chat log.
def _finalize_onboarding(profile_hash, onboarding_data, is_api_call=False):
    """Creates, saves, and returns the final response for a new user profile."""
    profile_data = onboarding_data.get('profile_data', {})
    lang_code = onboarding_data.get('lang_code', 'en')
    lang_data = load_language_data(lang_code)

    new_profile = create_user_profile(
        name=profile_data['name'],
        email=onboarding_data.get('email', ''),
        phone='',
        age=profile_data.get('age'),
        details=profile_data.get('secondary_details', {}),
        lang_code=lang_code
    )
    # Perform initial calculations
    calculate_child_ages(new_profile)
    calculate_trimester(new_profile)

    # Choose the correct completion message
    final_reply_key = 'onboarding_complete_parent' if new_profile.get('secondary_details', {}).get('is_parent') else 'onboarding_complete'
    final_reply = lang_data.get(final_reply_key, '').format(name=profile_data['name'].split(' ')[0])
    
    # Pre-populate the chat log with the final welcome message to prevent a race condition on the frontend.
    new_profile['chat_log'] = [{'role': 'assistant', 'content': md.render(final_reply)}]
    
    save_profile(profile_hash, new_profile)
    
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

# MODIFIED in v116.0: Expanded keyword map for targeted content
def _get_relevant_education_tidbit(profile, user_message):
    if not EDUCATION_DATA:
        return None, None

    KEYWORD_MAP = {
        "period_cramps": ["cramp", "cramps", "period pain", "menstrual pain"],
        "sleep": ["sleep", "insomnia", "couldn't sleep", "woke up"],
        "stress": ["stress", "anxiety", "anxious", "overwhelmed"],
        "body_image": ["fat", "ugly", "hate my body", "look weird", "body changes"],
        "contraception": ["birth control", "condom", "pill", "iud", "contraceptive"],
        "mental_health_basics": ["sad", "depressed", "lonely", "not okay"]
    }

    user_message_lower = user_message.lower()
    found_topic = None
    for topic, keywords in KEYWORD_MAP.items():
        # Build a regex pattern that looks for any of the keywords as whole words
        pattern = r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b'
        if re.search(pattern, user_message_lower):
            found_topic = topic
            break
    
    if not found_topic:
        return None, None
    
    age = profile.get("age", 30)
    age_group = "teen" if age <= 19 else "adult"
    
    tidbits_for_topic = EDUCATION_DATA.get(found_topic, {}).get(age_group, [])
    if not tidbits_for_topic:
        # Fallback to adult content if teen-specific content doesn't exist for the topic
        tidbits_for_topic = EDUCATION_DATA.get(found_topic, {}).get("adult", [])
        if not tidbits_for_topic:
            return None, None
    
    if "shown_education_tidbits" not in profile:
        profile["shown_education_tidbits"] = []
        
    shown_tidbits = profile["shown_education_tidbits"]
    available_tidbits = [t for t in tidbits_for_topic if t.get("id") not in shown_tidbits]
    
    if not available_tidbits:
        # If all tidbits for this topic have been shown, reset the list for this topic
        profile["shown_education_tidbits"] = [tid for tid in shown_tidbits if tid not in [t['id'] for t in tidbits_for_topic]]
        available_tidbits = tidbits_for_topic
    
    selected_tidbit = random.choice(available_tidbits)
    
    return selected_tidbit.get("text"), selected_tidbit.get("id")

# NEW in v105.0
def _check_for_new_achievements(profile):
    """
    Checks the user's interaction history to unlock new usage-based badges.
    Returns a list of newly unlocked badge objects, or an empty list.
    """
    # Use setdefault to gracefully handle old profiles gracefully
    achievements = profile.setdefault("achievements", {"unlocked_badges": {}})
    unlocked_ids = achievements["unlocked_badges"].keys()

    interaction_log = profile.get("interaction_log", [])
    if not interaction_log:
        return []

    # Calculate the number of unique days the user has interacted
    unique_interaction_days = set(
        datetime.fromisoformat(entry["timestamp"]).date() for entry in interaction_log
    )
    num_unique_days = len(unique_interaction_days)

    newly_unlocked = []
    for badge in BADGE_DEFINITIONS:
        if badge["id"] not in unlocked_ids and num_unique_days >= badge["days"]:
            # Unlock the badge
            achievements["unlocked_badges"][badge["id"]] = {
                "name": badge["name"],
                "unlocked_at": datetime.now(timezone.utc).isoformat()
            }
            newly_unlocked.append(badge)
            
    return newly_unlocked

# MODIFIED in v105.4: Replaced direct LLM call with fallback function
def _generate_monthly_summary(profile):
    """
    Uses AI to generate a personalized wellness summary for the previous month.
    """
    name = profile.get("name", "User").split(" ")[0]
    today = datetime.now(timezone.utc)
    first_day_of_current_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    first_day_of_previous_month = last_day_of_previous_month.replace(day=1)
    previous_month_name = first_day_of_previous_month.strftime("%B")
    current_month_name = first_day_of_current_month.strftime("%B")


    # Gather data from the previous month
    health_logs = [log for log in profile.get("health_logs", []) if first_day_of_previous_month <= dateparser.parse(log['timestamp']).replace(tzinfo=timezone.utc) <= first_day_of_current_month]
    goals = profile.get("goals", [])

    if not health_logs: return None # Don't generate a summary if there's no activity

    # Format the data for the prompt
    summary_data = [f"Summary for {name} for the month of {previous_month_name}:"]
    moods = defaultdict(int)
    symptoms = defaultdict(int)
    for log in health_logs:
        if log.get('category') == 'mood':
            moods[log.get('value')] += 1
        elif log.get('category') == 'physical_symptom':
            symptoms[log.get('value')] += 1
    
    if moods:
        summary_data.append(f"- Moods Logged: {', '.join([f'{k} ({v} times)' for k, v in moods.items()])}")
    if symptoms:
        summary_data.append(f"- Symptoms Logged: {', '.join([f'{k} ({v} times)' for k, v in symptoms.items()])}")
    if goals:
        summary_data.append(f"- Current Goals: {', '.join([g['text'] for g in goals])}")

    summary_prompt = (
        f"You are Tyra, an empathetic wellness companion. It is the first day of {current_month_name}. "
        f"Based on the following data points from last month ({previous_month_name}), "
        f"write a short (2-3 sentences), warm, and encouraging proactive summary for {name}. "
        f"Your response MUST start with 'Happy {current_month_name}!' and explicitly mention it's a look back at {previous_month_name}. "
        "Highlight a positive trend or their consistency if possible. Conclude by asking an open-ended question about their goals or feelings for the month ahead.\n\n"
        "Data:\n" + "\n".join(summary_data)
    )

    response = _call_llm_with_fallback(summary_prompt)
    if response is None:
        print(f"!!! Could not generate monthly summary after all fallbacks.")
        return None
        
    return md.render(response.text.strip())


# NEW in v105.1, MODIFIED in v105.2
def _check_and_generate_monthly_summary(profile):
    """
    Checks if a monthly summary is due and generates it if needed.
    """
    # Use setdefault to gracefully handle old profiles that don't have this structure
    proactive_data = profile.setdefault("proactive_assistance", {})
    last_summary_str = proactive_data.get("last_summary_date")
    today = datetime.now().date()
    
    # Check if this is the first interaction of a new month
    if last_summary_str:
        try:
            last_summary_date = dateparser.parse(last_summary_str).date()
            if last_summary_date.month == today.month and last_summary_date.year == today.year:
                return None # Summary already generated for this month
        except (ValueError, TypeError):
             # If the date is invalid for some reason, we can proceed to generate a new one
             pass

    # If no summary this month, generate one
    summary = _generate_monthly_summary(profile)
    if summary:
        proactive_data["last_summary_date"] = today.isoformat()
        return summary
        
    return None

# MODIFIED in v107.4 for robust filtering
def _handle_video_suggestion(profile, selected_category=None):
    if not ENABLE_VIDEO_SUGGESTIONS or not WELLNESS_VIDEO_DATA:
        return {"reply": "Sorry, the video library is currently unavailable."}

    details = profile.get("secondary_details", {})
    is_pregnant = details.get("is_pregnant", False)
    is_parent = details.get("is_parent", False)
    
    suitable_videos = []
    
    if is_pregnant:
        weeks_gestation = details.get("weeks_gestation", 0)
        suitable_videos = [v for v in WELLNESS_VIDEO_DATA if v["category"].startswith("prenatal_") and v["suitability"].get("min_weeks_gestation", 0) <= weeks_gestation and v["suitability"].get("max_weeks_gestation", 99) >= weeks_gestation]
    elif is_parent and details.get("child_dobs"):
        try:
            last_dob_str = max(details["child_dobs"])
            last_dob = datetime.strptime(last_dob_str, "%Y-%m-%d")
            weeks_postpartum = (datetime.now() - last_dob).days // 7
            suitable_videos = [v for v in WELLNESS_VIDEO_DATA if v["category"].startswith("postnatal_") and v["suitability"].get("min_weeks_postpartum", 0) <= weeks_postpartum and v["suitability"].get("max_weeks_postpartum", 999) >= weeks_postpartum]
        except (ValueError, TypeError): pass

    if not suitable_videos:
        return {"reply": "I don't have a specific video for your current stage, but I can answer questions about general wellness!"}

    if selected_category:
        # User has selected a category, return the carousel
        videos_in_category = [v for v in suitable_videos if v.get("primary_category") == selected_category]
        return {
            "reply": f"Great choice! Here are the {selected_category} videos. Tap one to play it here.",
            "ui_component": "video_carousel",
            "data": { "videos": videos_in_category }
        }
    else:
        # First request: determine categories and counts
        categories = defaultdict(list)
        for v in suitable_videos:
            categories[v.get("primary_category", "general")].append(v)
        
        if len(categories) == 1:
            # Only one category, so just show the carousel directly
            category_name = list(categories.keys())[0]
            return {
                "reply": "Of course! Here are some videos that might be helpful. Tap one to play it here.",
                "ui_component": "video_carousel",
                "data": { "videos": categories[category_name] }
            }
        elif len(categories) > 1:
            # Multiple categories, so show the picker
            category_data = [{"name": name.capitalize(), "count": len(videos)} for name, videos in categories.items()]
            return {
                "reply": "I've found a few options for you! What are you in the mood for?",
                "ui_component": "category_picker",
                "data": { "categories": category_data }
            }
        else:
            # Should not happen if suitable_videos is not empty, but a safe fallback
            return {"reply": "I couldn't find any suitable videos for you right now, but I can help with other questions!"}

# NEW in v116.0: Logic for calculating and updating user streaks
def _update_daily_streak(profile):
    if not ENABLE_GAMIFICATION_STREAKS: return profile
    
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    streaks_data = profile.setdefault("streaks", {"current": 0, "last_log_date": None})
    
    if streaks_data["last_log_date"] == today_str:
        return profile # Already interacted today

    last_log_dt = dateparser.parse(streaks_data["last_log_date"]) if streaks_data["last_log_date"] else None
    
    if last_log_dt and (datetime.now(timezone.utc).date() - last_log_dt.date()).days == 1:
        streaks_data["current"] += 1 # Continue streak
    else:
        streaks_data["current"] = 1 # Start a new or reset streak
        
    streaks_data["last_log_date"] = today_str
    return profile

# --- NEW in v117.0: Shareable Insight Functions ---
# BUGFIX in v117.1: Added missing function _should_offer_weekly_insight
def _should_offer_weekly_insight(profile):
    if not ENABLE_SHAREABLE_INSIGHTS:
        return False

    proactive_data = profile.setdefault("proactive_assistance", {})
    last_offered_str = proactive_data.get("last_insight_offered_date")
    
    # Cooldown Check: Don't offer if one was offered recently.
    if last_offered_str:
        try:
            last_offered_dt = date.fromisoformat(last_offered_str)
            if (date.today() - last_offered_dt).days < INSIGHT_COOLDOWN_DAYS:
                return False
        except (ValueError, TypeError):
            pass # Ignore malformed dates

    # Activity Check: Count unique interaction days in the last 7 days.
    interaction_log = profile.get("interaction_log", [])
    if not interaction_log:
        return False

    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_interaction_days = set()
    for entry in interaction_log:
        try:
            entry_dt = dateparser.parse(entry["timestamp"]).replace(tzinfo=timezone.utc)
            if entry_dt > seven_days_ago:
                recent_interaction_days.add(entry_dt.date())
        except (ValueError, TypeError):
            continue
    
    # Trigger if active on 5 or more of the last 7 days.
    return len(recent_interaction_days) >= 5

def _analyze_last_7_days(profile):
    interaction_log = profile.get("interaction_log", [])
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_interactions = [e for e in interaction_log if dateparser.parse(e["timestamp"]).replace(tzinfo=timezone.utc) > seven_days_ago]
    
    if not recent_interactions:
        return "You had a quiet week, but it's great to see you back!", None

    # Simple Insight Logic: Check for the most frequent activity
    intent_counts = defaultdict(int)
    for interaction in recent_interactions:
        intent = interaction.get("extracted_intent", {})
        if intent.get("health_log"):
            intent_counts[intent["health_log"]["category"]] += 1
        elif intent.get("period_action"):
            intent_counts["period_tracking"] += 1
    
    if intent_counts:
        most_common_activity = max(intent_counts, key=intent_counts.get).replace("_", " ")
        return f"This week, you were really focused on your {most_common_activity}!", None
        
    # Fallback insight
    day_count = len(set(dateparser.parse(e["timestamp"]).date() for e in recent_interactions))
    return f"This week, you were active on {day_count} different days. Keep it up!", None

# BUGFIX in v117.1: Added missing function _generate_and_save_insight_image
def _generate_and_save_insight_image(profile):
    name = profile.get("name", "User").split(" ")[0]
    insight_text, _ = _analyze_last_7_days(profile)
    image_url = _generate_insight_image(name, insight_text)
    return insight_text, image_url

# --- NEW in v120.0: Proactive Greeting Logic ---
def _process_proactive_greeting(profile):
    """Generates the greeting using the logic tree and LLM."""
    # This formats the prompt with the is_proactive_greeting=True flag, 
    # which tells user_profiler.py to generate the specific 'hook' instruction.
    context_prompt = format_profile_for_prompt(
        profile,
        chatbot_name=CHATBOT_NAME,
        is_proactive_greeting=True,
        milestones_data=MILESTONES_DATA # NEW in v121.0
    )
    
    # We pass an empty string as user message because Tyra is speaking first
    # The prompt already contains the "Initiate conversation" instruction.
    response = _call_llm_with_fallback(f"{context_prompt}")
    
    if response is None:
        # Fallback if LLM fails
        return "Hello! How are you doing today?"
        
    return response.text.strip()

# --- UPGRADED "WRAPPED" ENGINE (v119.8) ---
def _calculate_monthly_vibe(profile):
    """
    Analyzes last 30 days of logs to determine the user's 'Aura'.
    Returns: { 'title': str, 'palette': [colors], 'stat_text': str }
    """
    health_logs = profile.get("health_logs", [])
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    
    recent_logs = []
    for log in health_logs:
        try:
            log_dt = dateparser.parse(log['timestamp'])
            if log_dt.tzinfo is None: log_dt = log_dt.replace(tzinfo=timezone.utc)
            if log_dt > thirty_days_ago: recent_logs.append(log)
        except: continue

    if not recent_logs:
        return {
            "title": "Clean Slate",
            "palette": ["#E0E0E0", "#F5F5F5", "#FFFFFF"], # Grey/White
            "stat_text": "Ready to start tracking!"
        }

    # Analyze Vibe
    moods = [l['value'] for l in recent_logs if l['category'] == 'mood']
    sleeps = [l['value'] for l in recent_logs if l['category'] == 'sleep']
    stress = [l['value'] for l in recent_logs if l['category'] == 'stress']
    
    # 1. Chaos Coordinator (High Stress / Poor Sleep)
    if 'high' in stress or 'poor' in sleeps or 'anxious' in moods:
        return {
            "title": "Chaos Coordinator",
            "palette": ["#41295a", "#2F0743", "#A855A8"], # Deep Purple/Red
            "stat_text": f"Survived {len(recent_logs)} logs this month."
        }
    
    # 2. Main Character Energy (Energetic / Good Sleep)
    if 'energetic' in moods or 'good' in sleeps:
        return {
            "title": "Main Character Energy",
            "palette": ["#FF512F", "#DD2476", "#FF7043"], # Orange/Pink
            "stat_text": "Radiating good vibes."
        }
        
    # 3. Zen Master (Low Stress / Calm)
    if 'low' in stress or 'calm' in moods:
        return {
            "title": "Zen Master",
            "palette": ["#11998e", "#38ef7d", "#AED581"], # Green/Teal
            "stat_text": "Unbothered & flourishing."
        }

    # Default: The Consistent Queen
    return {
        "title": "Consistent Queen",
        "palette": ["#8B4A9C", "#BC9AC8", "#E6B0AA"], # Tyra Default
        "stat_text": "Keeping it steady."
    }

def _generate_insight_image(name, insight_text_unused):
    """
    Generates a procedural 'Spotify Wrapped' style image based on user's Vibe.
    """
    try:
        # Load User Context
        profile_hash = session.get('profile_hash') or g.profile_hash
        profile = load_profile(profile_hash)
        vibe = _calculate_monthly_vibe(profile)
        
        # Canvas Setup
        W, H = 1080, 1920 # Instagram Story Aspect Ratio
        img = Image.new('RGBA', (W, H), color=vibe['palette'][0])
        draw = ImageDraw.Draw(img)
        
        # --- 1. PROCEDURAL BACKGROUND ART ---
        # Draw random orbs using the palette to create an abstract "Aura"
        for _ in range(5):
            color = random.choice(vibe['palette'])
            x = random.randint(-200, W)
            y = random.randint(-200, H)
            size = random.randint(400, 900)
            # Draw semi-transparent circle
            overlay = Image.new('RGBA', (W, H), (0,0,0,0))
            draw_overlay = ImageDraw.Draw(overlay)
            draw_overlay.ellipse((x, y, x+size, y+size), fill=color)
            # Blend it
            img = Image.alpha_composite(img, overlay)
            
        draw = ImageDraw.Draw(img) # Refresh draw object for text
        
        # --- 2. TEXT ASSETS ---
        try:
            font_path = os.path.join('static', 'fonts', 'Poppins-Bold.ttf')
            title_font = ImageFont.truetype(font_path, 120)
            vibe_font = ImageFont.truetype(font_path, 90)
            stat_font = ImageFont.truetype(font_path, 60)
        except:
            title_font = ImageFont.load_default()
            vibe_font = ImageFont.load_default()
            stat_font = ImageFont.load_default()

        # --- 3. DRAW CONTENT ---
        # Avatar is drawn at Y=100 and height is 200, so it ends at Y=300.
        # We need to start text BELOW Y=300.
        
        # User Name (Moved down to 360 to clear avatar)
        draw.text((W//2, 360), f"{name}'s", font=title_font, fill="white", anchor="ms")
        
        # "Health Aura" label (Moved down to 450)
        draw.text((W//2, 450), "HEALTH AURA", font=stat_font, fill="white", anchor="ms")
        
        # The Vibe Title (Centerpiece)
        # FIX: Wrap the title text so "MAIN CHARACTER ENERGY" doesn't cut off
        # width=12 characters usually breaks "Main Character" nicely
        wrapped_title = textwrap.fill(vibe['title'].upper(), width=12)
        draw.multiline_text((W//2, H//2), wrapped_title, font=vibe_font, fill="white", anchor="mm", align="center", spacing=20)
        
        # The Stat (Moved down slightly to accommodate multi-line title)
        draw.text((W//2, H//2 + 250), vibe['stat_text'], font=stat_font, fill="white", anchor="mm")
        
        # Tyra Footer
        draw.text((W//2, H - 150), "Generated by Tyra", font=stat_font, fill=(255, 255, 255, 180), anchor="ms")
        
        # --- 4. AVATAR COMPOSITE ---
        avatar_path = os.path.join('static', 'images', 'tyra_avatar.png')
        if os.path.exists(avatar_path):
            avatar = Image.open(avatar_path).convert("RGBA").resize((200, 200))
            mask = Image.new("L", (200, 200), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 200, 200), fill=255)
            img.paste(avatar, ((W - 200)//2, 100), mask)

        # Save
        filename = f"wrapped_{uuid.uuid4().hex[:8]}.png"
        save_path = os.path.join(SHARED_INSIGHTS_DIR, filename)
        img.save(save_path)
        
        return url_for('shared_insight', filename=filename, _external=False)

    except Exception as e:
        print(f"!!! ERROR generating Wrapped image: {e}")
        return None

if __name__ == '__main__':
    if not app.config.get("FLASK_SECRET_KEY"):
        raise ValueError("No FLASK_SECRET_KEY set for Flask application.")
    # MODIFIED in v110.0: Check for ZeptoMail token instead of SendGrid
    if app.config.get('ENABLE_EMAIL_OTP_VERIFICATION') and (not app.config.get("ZEPTOMAIL_TOKEN") or not app.config.get("SENDER_EMAIL")):
        print("WARNING: ENABLE_EMAIL_OTP_VERIFICATION is True, but ZEPTOMAIL_TOKEN or SENDER_EMAIL is not set. OTP emails will fail.")
    # NEW in v118.0: Check for the native app secret key if the feature is enabled
    if app.config.get('ENABLE_NATIVE_APP_AUTH') and not app.config.get('NATIVE_APP_SECRET_KEY'):
        print("WARNING: ENABLE_NATIVE_APP_AUTH is True, but NATIVE_APP_SECRET_KEY is not set. Native app authentication will fail.")
    app.run(host='0.0.0.0', port=5001, debug=True)