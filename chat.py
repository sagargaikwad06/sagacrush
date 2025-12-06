import os
import json
import uuid
from dotenv import load_dotenv
from openai import OpenAI
import redis
import moderation

load_dotenv()

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Redis setup
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
SESSION_TIMEOUT = 30 * 60  # 30 minutes

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

# Bot identity
BOT_NAME = "SagaCrush AI"
BOT_CREATOR = "Sagar Gaikwad"
BOT_WEBSITE = "www.sagacrush.com"

# Chat modes
MODES = {
    "emotional": "Respond with empathy and focus on feelings.",
    "financial": "Give simple, responsible financial guidance. No legal or investment guarantees.",
    "sarcastic": "Use polite, dry sarcasm while still being helpful.",
    "witty": "Be clever and playful with light humor.",
    "educational": "Explain ideas clearly and help the user learn.",
    "guidance": "Offer thoughtful life guidance like a calm mentor.",
    "mental": "Be gentle and supportive. Encourage healthy thinking. No medical claims.",
    "friendly": "Stay warm, positive, and approachable.",
    "career": "Offer practical career direction and insights.",
    "health": "Share general wellness tips only. No diagnosis.",
    "tech": "Explain technology in simple, clear language.",
    "coding": "Help with programming questions and code examples.",
    "motivation": "Encourage and energize the user with positive tone.",
    "relationship": "Provide calm and balanced relationship advice.",
    "parenting": "Offer supportive, non-judgmental parenting suggestions.",
    "spiritual": "Respond with a gentle, reflective spiritual tone.",
    "general": "Reply normally with a helpful conversational tone.",
}

# ----- Session Helpers -----
def get_session_data(session_id: str):
    data = r.get(session_id)
    if data:
        return json.loads(data)
    return {"messages": [], "facts": {}}

def save_session_data(session_id: str, data: dict):
    r.setex(session_id, SESSION_TIMEOUT, json.dumps(data))

def delete_session(session_id: str):
    r.delete(session_id)

def clear_session_messages(session_id: str):
    data = get_session_data(session_id)
    data["messages"] = []  # preserve facts
    save_session_data(session_id, data)

def new_session():
    session_id = str(uuid.uuid4())
    data = {"messages": [], "facts": {}}
    save_session_data(session_id, data)
    return session_id

# ----- Chat Generation -----
async def generate_reply(message: str, mode: str = "general", session_id: str = None):
    # Moderation check
    safe, warning = moderation.check_message(message)
    if not safe:
        return "🚫 Your message violates content guidelines and cannot be processed.", session_id or "unknown"

    # Create new session if needed
    if not session_id or not r.exists(session_id):
        session_id = new_session()
    session_data = get_session_data(session_id)
    messages = session_data["messages"]
    facts = session_data["facts"]

    # Add system message if session is new
    if not messages:
        system_message = f"""
        You are {BOT_NAME}, a smart and friendly chatbot.
        Developed by {BOT_CREATOR}, official website {BOT_WEBSITE}.
        Your goal is to provide helpful, context-aware, and varied responses.
        Follow the style of the selected mode: {MODES.get(mode, MODES['general'])}
        """
        messages.append({"role": "system", "content": system_message})

    # Include facts as context
    if facts:
        fact_summary = "User facts remembered: " + json.dumps(facts)
        messages.append({"role": "system", "content": fact_summary})

    # Append user message
    messages.append({"role": "user", "content": message})

    # Generate bot reply
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.8,
    )

    bot_message = response.choices[0].message.content

    # Prepend soft warning if exists
    if warning:
        bot_message = f"{warning}\n{bot_message}"

    messages.append({"role": "assistant", "content": bot_message})

    # Optional: update user facts automatically
    fact_request_prompt = """
    Analyze the conversation. If there are new facts about the user (name, preferences, interests) 
    that should be remembered for future chats, output them as JSON. Otherwise, output {}.
    """
    fact_response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages + [{"role": "user", "content": fact_request_prompt}],
        temperature=0.0,
    )

    try:
        new_facts = json.loads(fact_response.choices[0].message.content)
        if isinstance(new_facts, dict):
            facts.update(new_facts)
    except:
        pass

    # Save session
    session_data["messages"] = messages
    session_data["facts"] = facts
    save_session_data(session_id, session_data)

    return bot_message, session_id

