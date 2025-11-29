# user_profiler.py (v120.1 - Refined Logic Tree for Pregnancy)
from datetime import datetime, timedelta
import dateparser 
import random 

PROMPT_HISTORY_LIMIT = 5
RECENT_LOG_LIMIT = 7
KEY_MEMORIES_LIMIT = 5 

# BUG FIX v92.0: Add Arabic to the language map
LANG_MAP = {
    "en": "English", "hi": "Hindi", "bn": "Bengali", "te": "Telugu", "mr": "Marathi",
    "ta": "Tamil", "gu": "Gujarati", "ur": "Urdu", "kn": "Kannada",
    "or": "Odia", "ml": "Malayalam", "pa": "Punjabi", "ar": "Arabic"
}

# NEW in v119.2: Define Persona Prompts
PERSONA_PROMPTS = {
    "bestie": (
        "You are 'Tyra', a supportive, warm, and empathetic best friend. "
        "Use emojis naturally (e.g., 💜, ✨, 🥺). "
        "Your language should be casual, relatable, and validating. "
        "Treat the user like a close sister. If they struggle, validate their feelings first."
    ),
    "professional": (
        "You are 'Tyra', a clinical, objective, and professional health assistant. "
        "DO NOT use emojis. Your tone is calm, factual, and concise. "
        "Focus on clarity and recording data accurately. "
        "Avoid slang (like 'ugh', 'bummer') or overly emotional language. Be efficient."
    ),
    "coach": (
        "You are 'Tyra', a high-energy, motivational wellness coach. "
        "Use emojis like 🔥, 💪, ⚡. Your tone is empowering, action-oriented, and enthusiastic. "
        "Focus on goals, consistency, and resilience. "
        "Reframing negatives into challenges."
    )
}

# MODIFIED in v117.0: Add last_insight_offered_date
def create_user_profile(name, email, phone, age, details, lang_code='en'):
    # Calculate an approximate date of birth from the provided age
    # This makes the profile dynamic over time
    dob = datetime.now() - timedelta(days=age * 365.25)
    
    # NEW in v119.4: Smart Default Persona
    initial_persona = "bestie"

    profile = {
        "name": name, "email": email, "phone": phone, 
        "dob": dob.date().isoformat(), # Store DOB instead of static age
        "dob_source": "tool_provided", # NEW in v107.6
        "age": age, # Store initial age for immediate use
        "language": lang_code,
        "persona": initial_persona, # NEW in v119.2: Saved preference
        "primary_category": None, "secondary_details": details,
        "conversation_history": [],
        "last_seen_timestamp": None,
        "chat_log": [], # NEW in v108.0: For persisting chat UI state
        "period_data": {
            "tracking_enabled": False,
            "has_been_offered_tracking": False,
            "cycles": [],
            "predicted_next_start_date": None,
            "predicted_ovulation_date": None,
            "predicted_fertile_start": None,
            "predicted_fertile_end": None
        },
        "proactive_assistance": {
            "last_milestone_check_date": None,
            "last_shown_milestone": None,
            "reminders": [],
            "last_symptom_analysis_date": None,
            "last_general_analysis_date": None,
            "last_program_suggestion_ts": None,
            "pending_program_offer": None,
            "last_summary_date": None, # NEW in v105.1
            "last_insight_offered_date": None, # NEW in v117.0
            "last_proactive_greet_ts": None # NEW in v120.0: Track last proactive greeting
        },
        "behavioral_synopsis": {},
        "health_logs": [],
        "medication_log": [],
        "goals": [],
        "interaction_log": [],
        "key_memories": [], # NEW in v102.0
        "shown_education_tidbits": [], # NEW in v104.2
        "achievements": { "unlocked_badges": {} }, # NEW in v105.0
        "shown_video_ids": [], # NEW in v106.0
        "streaks": {"current": 0, "last_log_date": None} # NEW in v116.0
    }
    if age <= 19: profile["primary_category"] = "Adolescence/Teen"
    elif 20 <= age <= 39: profile["primary_category"] = "Young Adulthood"
    elif 40 <= age <= 59: profile["primary_category"] = "Middle Adulthood"
    else: profile["primary_category"] = "Senior/Postmenopausal Life"
    return profile

def format_program_for_prompt(program_object):
    """Formats the rich program object from JSON into a markdown string for the AI."""
    if not program_object: return ""
    lines = [f"## {program_object.get('name', 'Program Details')}", f"**URL:** {program_object.get('url', 'N/A')}"]
    details = program_object.get('details', {})
    if 'goals' in details:
        lines.append("\n**Program Goals:**")
        lines.extend([f"- {goal}" for goal in details['goals']])
    if 'benefits' in details:
        lines.append("\n**Key Benefits:**")
        lines.extend([f"- {benefit}" for benefit in details['benefits']])
    if 'sub_programs' in program_object:
        lines.append("\n**Available Plans & Pricing:**")
        for sub in program_object['sub_programs']:
            lines.append(f"- **{sub['name']}**:")
            for plan in sub.get('pricing_plans', []): lines.append(f"  - {plan['plan_title']}: {plan['price']}")
    return "\n".join(lines)

# --- NEW in v120.0: Proactive Logic Tree ---
def generate_proactive_instruction(profile):
    """
    Analyzes the user profile to determine the 'hook' for a proactive greeting.
    Returns a string instruction for the LLM.
    v120.1 Update: Fixed pregnancy check to rely on weeks_gestation > 0.
    """
    now = datetime.now()
    details = profile.get("secondary_details", {})
    health_logs = profile.get("health_logs", [])
    
    # 1. SAFETY/CONTINUITY (Highest Priority)
    # Check for negative logs in the last 24 hours
    one_day_ago = now - timedelta(days=1)
    recent_negative_logs = []
    for log in health_logs:
        try:
            log_dt = dateparser.parse(log['timestamp'])
            # Normalize naive/aware datetimes
            if log_dt and log_dt.tzinfo is None and now.tzinfo: 
                log_dt = log_dt.replace(tzinfo=now.tzinfo)
            if log_dt and now.tzinfo is None and log_dt.tzinfo:
                log_dt = log_dt.replace(tzinfo=None)

            if log_dt and log_dt > one_day_ago:
                val = log.get('value', '').lower()
                cat = log.get('category', '').lower()
                if val in ['high', 'severe', 'poor', 'terrible', 'sad', 'anxious', 'depressed', 'painful']:
                    recent_negative_logs.append(f"{val} {cat}")
        except: continue
        
    if recent_negative_logs:
        return f"The user recently logged: {', '.join(recent_negative_logs[:2])}. Your GOAL is to gently and empathetically check in on how they are feeling now compared to earlier. Do not be alarmist, be supportive."

    # 2. LIFE STAGE CONTEXT (The "Care" Layer)
    # v120.1 FIX: Ensure we check weeks explicitly to avoid 'starting out' assumption for missing data
    if details.get('is_pregnant'):
        weeks = details.get('weeks_gestation', 0)
        if weeks >= 30:
            return f"User is {weeks} weeks pregnant (3rd Trimester). GOAL: Suggest a quick, specific physical relief tip (like a pelvic tilt or breathing) or ask about physical comfort (back pain/swelling)."
        elif weeks > 0:
            return f"User is {weeks} weeks pregnant. GOAL: Ask a warm question about how the pregnancy is going or how they are bonding with the baby."
        else:
            # Fallback if is_pregnant is True but weeks are 0/missing
            return "User is pregnant but exact weeks are currently unknown. GOAL: Gently ask how far along they are so you can provide better support."

    # Check Parenting (New Mom context)
    if details.get('is_parent'):
        # General check for parenting context if specific age calc isn't granular enough
        return "User is a parent. GOAL: Ask how they are balancing their own wellness with parenting duties today. Validate that self-care is hard."

    # Check Teen
    if profile.get('age', 25) <= 19:
        return "User is a teenager. GOAL: Do a casual 'vibe check'. Ask about school, stress, or just energy levels in a non-cringy way."

    # Check Menopause
    if details.get('is_perimenopausal') or details.get('is_menopausal'):
        return "User is navigating perimenopause/menopause. GOAL: Gently ask about sleep quality or energy levels, as these are common pain points."

    # 3. CYCLE PHASE (The "Living UI" Hook)
    period_data = profile.get("period_data", {})
    if period_data.get("tracking_enabled") and period_data.get("cycles"):
        last_start = period_data["cycles"][0].get("start_date")
        if last_start:
            try:
                days_since = (now.date() - datetime.strptime(last_start, "%Y-%m-%d").date()).days + 1
                if 1 <= days_since <= 5:
                    return "User is likely on their period (Day " + str(days_since) + "). GOAL: Be cozy and comforting. Ask if they need any tips for cramps or just want to vent."
                elif 20 <= days_since <= 28:
                    return "User is likely in the Luteal phase (Day " + str(days_since) + "). GOAL: Acknowledge that energy might be lower or emotions higher. Encourage gentleness."
            except: pass

    # 4. TIME OF DAY (Fallback)
    hour = now.hour
    if 5 <= hour < 12:
        return "It is morning. GOAL: Ask a motivating question about their intention for the day."
    elif 12 <= hour < 18:
        return "It is afternoon. GOAL: Ask how their energy levels are holding up."
    else:
        return "It is evening. GOAL: Ask if they are ready to wind down or how the day went."


def format_profile_for_prompt(profile, chatbot_name="Tyra", is_first_greeting_of_day=False, suggested_program_object=None, is_follow_up=False, proactive_context=None, special_context=None, enable_realtime_log_context=False, enable_ovulation_tracker=False, last_discussed_program_context=None, is_summary_request=False, education_tidbit=None, is_proactive_greeting=False):
    if not profile: return f"You are a helpful AI assistant named {chatbot_name}."
    
    lang_code = profile.get("language", "en")
    lang_name = LANG_MAP.get(lang_code, "English")
    language_instruction = f"CRITICAL: You MUST generate your entire response in the user's specified language: {lang_name} ({lang_code}). Do not use any other language."
    
    name = profile.get("name", "the user")
    age = profile.get("age", "Not specified")
    details = profile.get("secondary_details", {})

    # --- MODIFIED in v119.4: Dynamic Persona Switching ---
    selected_persona = profile.get("persona", "bestie")
    base_persona_text = PERSONA_PROMPTS.get(selected_persona, PERSONA_PROMPTS["bestie"])

    persona_instruction = (
        f"--- CORE PERSONA: {chatbot_name} ({selected_persona.upper()} MODE) ---\n"
        f"{base_persona_text}\n"
        "1.  **Your Role:** You are an empathetic wellness companion, not a clinical doctor.\n"
        "2.  **CRITICAL RULE:** Even in professional mode, remain polite."
    )

    # Age-Adaptive Tone Adjustment (FIXED in v119.4: Supports persona instead of overriding)
    if profile.get('age', 30) <= 19:
        if selected_persona == "professional":
            persona_instruction += "\n(Context: User is a Teenager. Maintain your Professional tone, but simplify medical jargon. Ensure they feel respected, not lectured.)"
        else:
            persona_instruction += "\n(Context: User is a Teenager. Adopt a 'Cool Older Sister' vibe. Be relatable, safe, and non-judgmental.)"
    elif profile.get('age', 35) > 50:
        persona_instruction += "\n(Context: User is an older adult. Ensure clarity and respect life experience.)"

    # --- MODIFIED in v120.0: Proactive Greeting Mode Logic ---
    if is_proactive_greeting:
        proactive_instruction = generate_proactive_instruction(profile)
        main_instruction = (
            f"--- PROACTIVE GREETING MODE ---\n"
            f"You are initiating the conversation with {name}. Do NOT wait for a user question.\n"
            f"**Specific Instruction:** {proactive_instruction}\n"
            f"Keep the greeting short (under 2 sentences), engaging, and strictly adherent to your {selected_persona} persona. End with a question."
        )
    else:
        # Standard Reactive Logic (Preserved from v119.3)
        memory_protocol = (
            "--- MEMORY PROTOCOL ---\n"
            "The system will automatically save important user-mentioned future events (like appointments or exams) to your memory. You can occasionally reference these past events to show you remember the user's journey."
        )

        if selected_persona == "professional":
            response_pattern = (
                "When the user expresses a negative feeling or symptom:\n"
                "1.  **Acknowledge Objectively:** (e.g., 'Noted.', 'I have logged that.')\n"
                "2.  **Provide Context/Action:** Briefly explain or confirm the data point.\n"
                "3.  **Neutral Support:** Suggest a medical consultation if severe, but avoid emotional coddling."
            )
        elif selected_persona == "coach":
            response_pattern = (
                "When the user expresses a negative feeling or symptom:\n"
                "1.  **Acknowledge the Challenge:** (e.g., 'That's a hurdle, but we can handle it.')\n"
                "2.  **Action Plan:** Suggest a small, immediate step to improve the situation.\n"
                "3.  **Motivation:** End with encouragement."
            )
        else: # Bestie (Default)
            response_pattern = (
                "When the user expresses a negative feeling or symptom:\n"
                "1.  **Validate their feeling** (e.g., 'I'm so sorry', 'That sucks').\n"
                "2.  **Directly answer/confirm**.\n"
                "3.  **Gently offer emotional support**."
            )
        
        main_instruction = (
            f"Your name is {chatbot_name}. Answer according to your {selected_persona} persona.\n"
            f"{response_pattern}\n"
            f"{memory_protocol}\n"
            "Use the profile context below."
        )

    context_lines = [
        language_instruction,
        "\n" + persona_instruction,
        "\n" + main_instruction,
        "--- USER PROFILE ---",
        f"Name: {name}", f"Age: {age}", f"Life Stage Category: {profile.get('primary_category', 'Not specified')}"
    ]
    
    if details.get('is_trying_to_conceive'): context_lines.append(f"- Is trying to conceive for {details.get('months_trying', 'N/A')} months.")
    if details.get('is_pregnant'): context_lines.append(f"- Is currently pregnant: {details.get('weeks_gestation', 'N/A')} weeks gestation ({details.get('current_trimester', 'N/A')}).")
    if details.get('is_parent'):
        num_children = details.get('num_children', 0)
        ages_str = ", ".join([f"{age.get('years', 0)}y {age.get('months', 0)}m" for age in details.get('calculated_child_ages', [])]) or "not specified"
        context_lines.append(f"- Is a parent of {num_children} child/children. Last child born {details.get('last_child_birth_ago', 'not specified')} ago. Ages: {ages_str}.")
    if details.get('is_perimenopausal'): context_lines.append("- Is experiencing perimenopause symptoms.")
    
    # --- MODIFIED in v120.0: Only add deep context if NOT a proactive greeting ---
    if not is_proactive_greeting:
        # --- NEW in v116.3: Comprehensive UI Context for feature awareness ---
        ui_context = ["\n--- UI CONTEXT (For your awareness of the app's features) ---", "- The user is interacting with you inside a chat widget."]
        streaks = profile.get("streaks", {})
        current_streak = streaks.get("current", 0)
        
        is_authenticated = "email" in profile and profile["email"]
        
        if is_authenticated:
            ui_context.append("- Header Controls:")
            if current_streak > 0:
                ui_context.append(f"  - Streak Counter: A '🔥 {current_streak}' icon shows the user's 'daily streak counter,' representing how many days in a row they have chatted with you.")
            ui_context.append("  - Dashboard Button: A 'Dashboard' button takes the user to a page summarizing their health data.")
            
            # --- MODIFIED in v119.7: Detailed Settings Menu Context for Self-Awareness ---
            ui_context.append("  - Settings Menu (⋮): This is the 'three dots' menu in the top right. It contains the following items:")
            ui_context.append("    1. 'Privacy Policy': Link to the policy.")
            ui_context.append("    2. '🎨 Change Theme': Lets the user manually change the app colors (Themes: Midnight, Coquette, Matcha, Ocean, Sunset).")
            ui_context.append("    3. '🔄 Cycle Sync': A toggle feature. If ON, the app theme automatically changes color based on the user's cycle phase (Pink for Period, Orange for Ovulation). It aligns the app's aesthetic with their biology.")
            ui_context.append("    4. '🎭 Change Icon': Lets the user disguise the app icon as a Calculator or Notes app for privacy (Discreet Mode).")
            ui_context.append("    5. '✨ Change Vibe': Lets the user change YOUR personality (Bestie, Professional, Coach).")
            ui_context.append("    6. '🔥 Burn History': A 'Panic Button' that instantly wipes the chat screen and removes recent logs for privacy.")
            ui_context.append("    7. 'Logout': Logs the user out.")
            # --- End v119.7 ---

            ui_context.append("- Dashboard Widgets: The Dashboard page contains widgets for: Current Cycle, Upcoming Reminders, Medications, Health Goals, Recent Logs, and Charts.")
            ui_context.append("- Chat Controls:")
            ui_context.append("  - File Upload (📎 icon): Allows users to upload documents or images for analysis.")
            ui_context.append("  - Voice Input (🎤 icon): Allows users to speak their messages.")
        
        ui_context.append("\n**INSTRUCTION:** If a user asks a question about a feature of the app (like 'where are my reminders,' 'what is Cycle Sync', 'how to hide the app'), you MUST use the context above to provide a direct, helpful answer that explains what the feature is and exactly where to find it.")
        context_lines.extend(ui_context)
        
        # --- NEW v102.0: Add Key Memories to context ---
        memories = profile.get("key_memories", [])
        if memories:
            context_lines.append("\n--- KEY MEMORIES (User's significant life events) ---")
            for mem in memories[:KEY_MEMORIES_LIMIT]:
                context_lines.append(f"- On {mem['timestamp']}: {mem['memory']}")
            context_lines.append("INSTRUCTION: You can occasionally and naturally reference an older, relevant memory to build rapport and show you remember the user's journey. Do this subtly.")

        synopsis_data = profile.get("behavioral_synopsis", {})
        if synopsis_data and synopsis_data.get('synopsis'):
            context_lines.append("\n--- BEHAVIORAL SYNOPSIS (User's recent focus) ---")
            for point in synopsis_data['synopsis']:
                context_lines.append(f"- {point}")

        if is_summary_request:
            meds = profile.get("medication_log", [])
            if meds:
                context_lines.append("\n--- CURRENT MEDICATIONS/SUPPLEMENTS ---")
                for med in meds:
                    context_lines.append(f"- {med.get('name')} ({med.get('dosage', 'N/A')}), Frequency: {med.get('frequency', 'N/A')}")

            goals = profile.get("goals", [])
            if goals:
                context_lines.append("\n--- USER'S GOALS ---")
                for goal in goals:
                    context_lines.append(f"- Goal: {goal.get('text')}")

            if enable_realtime_log_context:
                health_logs = profile.get("health_logs", [])
                if health_logs:
                    context_lines.append("\n--- RECENT HEALTH LOGS ---")
                    for log in health_logs[:RECENT_LOG_LIMIT]:
                        try:
                            log_date = dateparser.parse(log['timestamp']).strftime('%Y-%m-%d')
                            category = log.get('category', 'log')
                            value = log.get('value', 'entry')
                            context_lines.append(f"- On {log_date}: Logged '{value}' for '{category}'.")
                        except (TypeError, ValueError):
                            continue
            
            period_data = profile.get('period_data')
            if period_data and period_data.get('tracking_enabled'):
                context_lines.append("\n--- PERIOD & FERTILITY SUMMARY ---")
                context_lines.append("- Status: Tracking is enabled.")
                if period_data.get('average_cycle_length'): context_lines.append(f"- Average Cycle Length: {period_data['average_cycle_length']} days.")
                if period_data.get('average_period_length'): context_lines.append(f"- Average Period Length: {period_data['average_period_length']} days.")
                
                if period_data.get('cycles'):
                    last_cycle = period_data['cycles'][0]
                    context_lines.append(f"- Last Logged Period Started: {last_cycle.get('start_date', 'N/A')}.")
                    if enable_ovulation_tracker and last_cycle.get('fertile_start'):
                        context_lines.append(f"- Last Cycle's Estimated Fertile Window: {last_cycle.get('fertile_start')} to {last_cycle.get('fertile_end')}")

                if enable_ovulation_tracker and period_data.get('predicted_next_start_date'):
                     context_lines.append(f"- Predicted Next Period Start: {period_data.get('predicted_next_start_date')}")
                     context_lines.append(f"- Predicted Next Fertile Window: {period_data.get('predicted_fertile_start')} to {period_data.get('predicted_fertile_end')}.")

        reminders = profile.get("proactive_assistance", {}).get("reminders", [])
        if reminders:
            context_lines.append("\n--- USER'S SCHEDULED REMINDERS (FOR YOUR KNOWLEDGE ONLY) ---")
            for r in reminders:
                context_lines.append(f"- Reminder for '{r.get('text')}'" + (f" on {r.get('due_date')}." if r.get('due_date') else "."))
            context_lines.append("IMPORTANT: This list is for your reference. Refer to it ONLY if the user asks a direct question about a direct question about their 'reminders', 'appointments', or 'schedule'. Otherwise, do not mention it.")

        history = profile.get('conversation_history', [])
        if history:
            context_lines.append("\n--- CONVERSATION SUMMARY (Most Recent First) ---")
            summary_map = {"health_symptoms": "Mentioned health symptoms", "mood_log": "Mentioned feelings","fitness_activities": "Mentioned fitness activities", "life_goals": "Mentioned goals","recent_life_events": "Mentioned life events","expressed_needs_or_challenges": "Mentioned needs/challenges"}
            for entry in history[:PROMPT_HISTORY_LIMIT]:
                insights = entry.get('insights', {})
                entry_parts = [f"{summary_map.get(k, 'Mentioned')}: {', '.join(v)}" for k, v in insights.items() if v]
                if entry_parts: context_lines.append(f"- On {entry.get('timestamp', 'an unknown time').split('T')[0]}: " + "; ".join(entry_parts))
        
        # MODIFIED in v115.0: Added handler for "Real Talk" mode
        if special_context:
            context_lines.append("\n--- CRITICAL INSTRUCTION FOR THIS TURN ---")
            
            if special_context.get("type") == "explain_and_offer_program":
                context_lines.append(
                    "The user's question is a direct inquiry about a topic for which you have a relevant program suggestion. Your response MUST follow this two-part structure:\n"
                    "1. **Explain:** First, directly and helpfully answer the user's question (e.g., 'what is postnatal yoga').\n"
                    "2. **Offer:** Immediately after, on a new line, seamlessly transition to an offer. Example: 'Since this is something you're asking about, you might be interested to know that Tribher offers a specialized [Program Name] designed to help with exactly these goals. Would you like to know more about it?'\n"
                    "This is your primary directive for this conversational turn."
                )
            elif special_context.get("type") == "dynamic_confirmation":
                # FIX v119.4: Dynamic Confirmation respects Persona
                log_details = special_context.get("log_details", {})
                log_str = f"{log_details.get('value')} for {log_details.get('category')}"
                
                if selected_persona == "professional":
                    instruction = (
                        f"The user just logged '{log_str}'. Confirm this action concisely and professionally. "
                        "Example: 'I have updated your health log with that information.' "
                        "DO NOT ask follow-up questions unless the value indicates a medical emergency. DO NOT use emojis."
                    )
                elif selected_persona == "coach":
                    instruction = (
                        f"The user just logged '{log_str}'. Confirm this with energy. "
                        "Example: 'Got it! Tracking is the first step to improvement. 💪' "
                        "If it's negative, suggest a quick fix."
                    )
                else: # Bestie
                    instruction = (
                        f"The user just logged '{log_str}'. Confirm this naturally and warmly. "
                        "Example: 'Okay, I've made a note of that.' "
                    )
                    if special_context.get("is_negative"):
                        instruction += " Since this is negative, ask a gentle, caring follow-up question."

                context_lines.append(instruction)
            
            elif special_context.get("type") == "achievement_unlocked":
                badge_names = [badge['name'] for badge in special_context.get("badges", [])]
                badge_text = f"the '{badge_names[0]}'" if len(badge_names) == 1 else f"the following badges: {', '.join(badge_names)}"
                instruction = (
                    f"The user has just unlocked {badge_text} badge! This is an important milestone. "
                    "Your response MUST follow this two-part structure:\n"
                    "1. **Celebrate:** Start with an enthusiastic, celebratory message congratulating them. Example: 'Wow, congratulations!' or 'This is awesome! You've just unlocked...'\n"
                    "2. **Answer:** Immediately after, on a new line, answer their original question as you normally would.\n"
                    "This is your primary directive for this turn."
                )
                context_lines.append(instruction)

            elif special_context.get("type") == "real_talk_mode": # NEW in v115.0
                instruction = (
                    "The user has requested 'Real Talk'. This is your HIGHEST priority. You MUST adopt a more direct, frank, and confidential tone, like a trusted older sister. Start your response with a phrase like 'Of course, let's talk freely.' or 'Okay, real talk.' Then, address their underlying question with extra empathy and directness. Use 'I' statements to share wisdom (e.g., 'I know it can feel like...')."
                )
                context_lines.append(instruction)

            # NEW in v117.0
            elif special_context.get("type") == "offer_weekly_summary":
                instruction = (
                    "The user has been highly engaged this week. Your primary goal is to answer their question, but you MUST conclude your response by offering them a weekly summary. "
                    "End your message with a friendly, encouraging offer like: 'By the way, you've been really consistent this week! Would you like to see a shareable summary of your wellness insights?'"
                )
                context_lines.append(instruction)

        elif proactive_context:
            context_lines.append("\n--- Special Note for Conversation ---")
            context_type = proactive_context.get("type")
            if context_type == "reminder":
                context_lines.append(f"Start your response by GENTLY reminding the user: \"{proactive_context.get('text')}\". Then, on a new line, answer their main question.")
            elif context_type == "goal_check_in":
                goal_text = proactive_context.get('text', 'one of your goals')
                context_lines.append(f"After answering the user's primary question, gently and encouragingly check in on their progress with a question like: 'By the way, how has your goal to \"{goal_text}\" been going lately?'")
            elif context_type == "memory_check_in": # NEW in v115.0
                memory_text = proactive_context.get('text', 'something you mentioned')
                context_lines.append(f"Start your response with a warm, natural check-in about a past event the user mentioned. For example: 'Hey, I was just thinking about you. I remember you mentioned you had '{memory_text}'. How did it go?' Then, on a new line, address their current question.")
            elif context_type == "pregnancy_milestone":
                context_lines.append(f"Start your response with this exciting milestone update: \"{proactive_context.get('text')}\". Then, on a new line, answer their main question.")
            elif context_type == "symptom_correlation":
                context_lines.append(f"The system has found a potential health pattern. After answering the user's question, gently present this insight: \"{proactive_context.get('text')}\" Then, ask if they'd like to discuss it or get some tips.")
            elif context_type == "offer_tracking":
                context_lines.append("After answering the user's question, casually ask if they'd like you to help track their periods.")
            elif context_type == "prompt_for_update":
                context_lines.append("After answering the user's question, politely add a check-in like, 'By the way, I noticed your period might be due soon. If it has started, just let me know.'")

        # NEW in v104.2, MODIFIED in v104.5 for forceful instruction
        if education_tidbit:
            context_lines.append("\n--- EDUCATIONAL INSIGHT (MANDATORY ACTION) ---")
            context_lines.append(
                "The system has provided a relevant educational fact. This is NOT optional. After you have fully answered the user's primary question, you MUST seamlessly weave this fact into your response. "
                "Introduce it naturally. Example: 'By the way, here's something you might find interesting...' or 'Did you know that...?'"
            )
            context_lines.append(f"Educational Tidbit to Share: \"{education_tidbit}\"")

        final_program_context = suggested_program_object or last_discussed_program_context
        if final_program_context:
            context_lines.append("\n--- RELEVANT PROGRAM KNOWLEDGE BASE (IMPORTANT INSTRUCTION) ---")
            if is_follow_up:
                program_knowledge = format_program_for_prompt(final_program_context)
                context_lines.append(f"CRITICAL: The user just said 'yes' to learning more about the '{final_program_context.get('name')}'. IGNORE their 'yes' message and provide a detailed explanation of the program using the knowledge base below. Start enthusiastically.")
                context_lines.append(program_knowledge)
            elif suggested_program_object and not special_context: # Only trigger the generic offer if a special context isn't active
                program_name = suggested_program_object.get('name', 'a relevant program')
                context_lines.append(f"A relevant program was found: '{program_name}'.")
                context_lines.append("CRITICAL INSTRUCTION: First, answer the user's question as your primary goal. Then, as a mandatory final step, you MUST conclude your response with the following two sentences verbatim, without any modification: \"For more specialized guidance, Tribher offers programs designed for this life stage. Would you like to know more about it?\" This action is not optional.")
            elif last_discussed_program_context:
                 context_lines.append(f"The user's question is likely a follow-up about the '{last_discussed_program_context.get('name')}' which was just discussed. Use this context to answer accurately.")
                 context_lines.append(format_program_for_prompt(last_discussed_program_context))

        context_lines.append("\n---\nINSTRUCTION: Now, provide a helpful and direct answer to the user's question.\n\nUSER QUESTION: ")
    
    return "\n".join(context_lines)