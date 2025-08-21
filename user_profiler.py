# user_profiler.py (v102.0 - Conversational Memory)
from datetime import datetime
import dateparser

PROMPT_HISTORY_LIMIT = 5
RECENT_LOG_LIMIT = 7
KEY_MEMORIES_LIMIT = 5 # NEW in v102.0

# BUG FIX v92.0: Add Arabic to the language map
LANG_MAP = {
    "en": "English", "hi": "Hindi", "bn": "Bengali", "te": "Telugu", "mr": "Marathi",
    "ta": "Tamil", "gu": "Gujarati", "ur": "Urdu", "kn": "Kannada",
    "or": "Odia", "ml": "Malayalam", "pa": "Punjabi", "ar": "Arabic"
}

def create_user_profile(name, email, phone, age, details, lang_code='en'):
    profile = {
        "name": name, "email": email, "phone": phone, "age": age,
        "language": lang_code,
        "primary_category": None, "secondary_details": details,
        "conversation_history": [],
        "last_seen_timestamp": None,
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
            "pending_program_offer": None
        },
        "behavioral_synopsis": {},
        "health_logs": [],
        "medication_log": [],
        "goals": [],
        "interaction_log": [],
        "key_memories": [] # NEW in v102.0
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


def format_profile_for_prompt(profile, chatbot_name="Tyra", is_first_greeting_of_day=False, suggested_program_object=None, is_follow_up=False, proactive_context=None, special_context=None, enable_realtime_log_context=False, enable_ovulation_tracker=False, last_discussed_program_context=None, is_summary_request=False):
    if not profile: return f"You are a helpful AI assistant named {chatbot_name}."
    
    lang_code = profile.get("language", "en")
    lang_name = LANG_MAP.get(lang_code, "English")
    language_instruction = f"CRITICAL: You MUST generate your entire response in the user's specified language: {lang_name} ({lang_code}). Do not use any other language."
    
    name = profile.get("name", "the user")
    age = profile.get("age", "Not specified")
    details = profile.get("secondary_details", {})

    # --- NEW v101.8: Explicit Persona Definition ---
    persona_instruction = (
        f"--- CORE PERSONA: {chatbot_name} ---\n"
        "1.  **Your Role:** You are an empathetic wellness companion, not a clinical doctor.\n"
        "2.  **Your Traits:** You are calm, knowledgeable, encouraging, and completely non-judgmental.\n"
        "3.  **Your Tone:** Your tone is warm and supportive. Avoid being overly bubbly or using excessive emojis.\n"
        "4.  **CRITICAL RULE:** Always validate the user's feelings, especially when they express distress. Never be dismissive."
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
    
    if special_context and special_context.get("type") == "explain_and_offer_program":
        context_lines.append("\n--- CRITICAL INSTRUCTION FOR THIS TURN ---")
        context_lines.append(
            "The user's question is a direct inquiry about a topic for which you have a relevant program suggestion. Your response MUST follow this two-part structure:\n"
            "1. **Explain:** First, directly and helpfully answer the user's question (e.g., 'what is postnatal yoga').\n"
            "2. **Offer:** Immediately after, on a new line, seamlessly transition to an offer. Example: 'Since this is something you're asking about, you might be interested to know that Tribher offers a specialized [Program Name] designed to help with exactly these goals. Would you like to know more about it?'\n"
            "This is your primary directive for this conversational turn."
        )
    elif special_context and special_context.get("type") == "empathetic_follow_up":
        context_lines.append("\n--- CRITICAL INSTRUCTION FOR THIS TURN ---")
        confirmation = special_context.get("confirmation_message", "Okay, I've noted that.")
        context_lines.append(
            "The user just logged a negative health event. Your response MUST follow this two-part structure:\n"
            f"1. **Acknowledge:** Start by stating this confirmation message verbatim: \"{confirmation}\"\n"
            "2. **Follow-up:** Immediately after, on a new line, ask a gentle, caring, and open-ended follow-up question. Examples: 'I'm sorry to hear that. Is there anything on your mind you'd like to talk about?' or 'That sounds tough. If you'd like to vent or explore what might be causing it, I'm here to listen.'\n"
            "Do not add any other text. The user's message below is the log itself, so your entire response is just the acknowledgement and the follow-up question."
        )
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