import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def check_message(message: str):
    """
    Soft moderation: blocks high-risk messages, warns low-risk.
    Returns tuple: (safe_to_process: bool, soft_warning: str)
    """
    try:
        response = client.moderations.create(
            model="omni-moderation-latest",
            input=message
        )
        result = response.results[0]
        flagged = result.flagged
        categories = result.categories

        # Block high-risk categories
        block_categories = ["violence", "self_harm", "harassment", "hateful"]
        if flagged and any(categories.get(cat, False) for cat in block_categories):
            return False, ""

        # Soft warning for low-risk categories
        warn_categories = ["sexual", "political"]
        soft_flags = [cat for cat in warn_categories if categories.get(cat, False)]
        if soft_flags:
            warning = "⚠️ Your message may contain sensitive content. I will respond carefully."
            return True, warning

        return True, ""
    except Exception as e:
        print("Moderation error:", e)
        return True, ""

