# user_profiler.py (v108.0 - Chat History Persistence)
from datetime import datetime, timedelta

PROMPT_HISTORY_LIMIT = 5
RECENT_LOG_LIMIT = 7
KEY_MEMORIES_LIMIT = 5 # NEW in v102.0

# BUG FIX v92.0: Add Arabic to the language map
LANG_MAP = {
    "en": "English", "hi": "Hindi", "bn": "Bengali", "te": "Telugu", "mr": "Marathi",
    "ta": "Tamil", "gu": "Gujarati", "ur": "Urdu", "kn": "Kannada",
    "or": "Odia", "ml": "Malayalam", "pa": "Punjabi", "ar": "Arabic"
}

# MODIFIED in v107.6: Added dob_source field
def create_user_profile(name, email, phone, age, details, lang_code='en'):
    # Calculate an approximate date of birth from the provided age
    # This makes the profile dynamic over time
    dob = datetime.now() - timedelta(days=age * 365.25)

    profile = {
        "name": name, "email": email, "phone": phone, 
        "dob": dob.date().isoformat(), # Store DOB instead of static age
        "dob_source": "tool_provided", # NEW in v107.6
        "age": age, # Store initial age for immediate use
        "language": lang_code,
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
            "last_summary_date": None # NEW in v105.1
        },
        "behavioral_synopsis": {},
        "health_logs": [],
        "medication_log": [],
        "goals": [],
        "interaction_log": [],
        "key_memories": [], # NEW in v102.0
        "shown_education_tidbits": [], # NEW in v104.2
        "achievements": { "unlocked_badges": {} }, # NEW in v105.0
        "shown_video_ids": [] # NEW in v106.0
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


def format_profile_for_prompt(profile, chatbot_name="Tyra", is_first_greeting_of_day=False, suggested_program_object=None, is_follow_up=False, proactive_context=None, special_context=None, enable_realtime_log_context=False, enable_ovulation_tracker=False, last_discussed_program_context=None, is_summary_request=False, education_tidbit=None):
    if not profile: return f"You are a helpful AI assistant named {chatbot_name}."
    
    lang_code = profile.get("language", "en")
    lang_name = LANG_MAP.get(lang_code, "English")
    language_instruction = f"CRITICAL: You MUST generate your entire response in the user's specified language: {lang_name} ({lang_code}). Do not use any other language."
    
    name = profile.get("name", "the user")
    age = profile.get("age", "Not specified")
    details = profile.get("secondary_details", {})

    # --- NEW v101.8: Explicit Persona Definition ---
    # --- MODIFIED v104.0: Age-Adaptive Persona ---
    persona_instruction = (
        f"--- CORE PERSONA: {chatbot_name} ---\n"
        "1.  **Your Role:** You are an empathetic wellness companion, not a clinical doctor.\n"
        "2.  **Your Traits:** You are calm, knowledgeable, encouraging, and completely non-judgmental.\n"
        "3.  **Your Tone:** Your base tone is warm and supportive. Avoid being overly bubbly or using excessive emojis.\n"
        "4.  **CRITICAL RULE:** Always validate the user's feelings, especially when they express distress. Never be dismissive."
    )

    # Age-Adaptive Tone Adjustment
    if profile.get('age', 30) <= 19:
        persona_instruction += (
            "\n5.  **Teen Persona:** The user is a teenager. Adjust your tone to be more encouraging, friendly, and relatable, like a cool older sister or a mentor. "
            "You can use emojis where appropriate (e.g., ✨, 😊, 👍) to keep the tone light and engaging, but don't overdo it. "
            "Avoid overly clinical or formal language."
        )
    else:
         persona_instruction += (
            "\n5.  **Adult Persona:** The user is an adult. Maintain your standard supportive, knowledgeable, and compassionate tone. "
            "Clarity and empathy are key."
        )

    # --- NEW v102.0: Memory Protocol Instruction ---
    memory_protocol = (
        "--- MEMORY PROTOCOL ---\n"
        "If the user mentions a significant, forward-looking life event (e.g., an upcoming exam, a new job, a vacation, a doctor's appointment), you MUST embed a special tag in your response for the system to save it. The tag format is `[SUGGEST_MEMORY: Text of the memory]`. The system will remove this tag before showing the user your message.\n"
        "Example User Message: 'I'm so stressed, I have a huge final exam next Friday.'\n"
        "Example AI Response: That sounds very stressful. Make sure to take breaks! [SUGGEST_MEMORY: User has a final exam next Friday]\n"
        "DO NOT use this for simple health logs like 'I have a headache'."
    )
    
    # --- MODIFIED v101.8: Main instruction now includes the empathetic response pattern ---
    if is_first_greeting_of_day:
        main_instruction = f"Your name is {chatbot_name}. Start with a warm, personalized greeting for {name}. Then, on a new line, answer their question directly. When stating dates, use the full date (e.g., 'June 30, 2025') and avoid relative terms like 'today' or 'tomorrow'."
    else:
        main_instruction = (
            f"Your name is {chatbot_name}. Your primary goal is to answer the user's question directly and accurately. "
            "When the user expresses a negative feeling or symptom (e.g., stress, sadness, pain), your response structure MUST be:\n"
            "1.  **Validate their feeling** (e.g., 'That sounds really tough,' or 'I'm sorry you're dealing with that.').\n"
            "2.  **Directly answer their question or confirm the action** (e.g., 'I've logged that for you.').\n"
            "3.  **Gently offer support** (e.g., 'If you'd like to talk more about it, I'm here to listen.').\n\n"
            "Use the provided user profile context below to make your response more personal and relevant."
        )

    context_lines = [
        language_instruction,
        "\n" + persona_instruction,
        "\n" + memory_protocol,
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
        context_lines.append("IMPORTANT: This list is for your reference. Refer to it ONLY if the user asks a direct question about their 'reminders', 'appointments', or 'schedule'. Otherwise, do not mention it.")

    history = profile.get('conversation_history', [])
    if history:
        context_lines.append("\n--- CONVERSATION SUMMARY (Most Recent First) ---")
        summary_map = {"health_symptoms": "Mentioned health symptoms", "mood_log": "Mentioned feelings","fitness_activities": "Mentioned fitness activities", "life_goals": "Mentioned goals","recent_life_events": "Mentioned life events","expressed_needs_or_challenges": "Mentioned needs/challenges"}
        for entry in history[:PROMPT_HISTORY_LIMIT]:
            insights = entry.get('insights', {})
            entry_parts = [f"{summary_map.get(k, 'Mentioned')}: {', '.join(v)}" for k, v in insights.items() if v]
            if entry_parts: context_lines.append(f"- On {entry.get('timestamp', 'an unknown time').split('T')[0]}: " + "; ".join(entry_parts))
    
    # --- MODIFIED v104.1: Added handler for dynamic_confirmation
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
            log_details = special_context.get("log_details", {})
            log_value = log_details.get("value", "an event")
            log_category = log_details.get("category", "health")
            
            instruction = (
                f"The user just used a 'Quick Log' button to record '{log_value}' for their '{log_category}'. "
                f"Your entire response MUST be a simple, natural, non-robotic confirmation of this action. Do not ask a question unless specified below."
            )
            
            if special_context.get("is_negative"):
                instruction += (
                    " Since this is a negative log, you MUST ALSO ask a gentle, caring, open-ended follow-up question after the confirmation. "
                    "Example: 'Got it, I've noted that you had poor sleep. Is there anything on your mind you'd like to talk about?'"
                )
            else:
                 instruction += " Example: 'Okay, I've made a note of your good sleep!'"
            
            context_lines.append(instruction)
        
        # NEW in v105.0
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


    elif proactive_context:
        context_lines.append("\n--- Special Note for Conversation ---")
        context_type = proactive_context.get("type")
        if context_type == "reminder":
            context_lines.append(f"Start your response by GENTLY reminding the user: \"{proactive_context.get('text')}\". Then, on a new line, answer their main question.")
        elif context_type == "goal_check_in":
            goal_text = proactive_context.get('text', 'one of your goals')
            context_lines.append(f"After answering the user's primary question, gently and encouragingly check in on their progress with a question like: 'By the way, how has your goal to \"{goal_text}\" been going lately?'")
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

    context_lines.append("\n---\nINSTRUCTION: Now, provide a helpful and direct answer to the user's question. Use the context above to personalize your response where it is relevant.\n\nUSER QUESTION: ")
    return "\n".join(context_lines)