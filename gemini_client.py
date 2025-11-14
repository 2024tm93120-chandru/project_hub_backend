# gemini_client.py
import json
from typing import Dict, Any
import os
import re
import time
from dotenv import load_dotenv
load_dotenv()
# google gen ai SDK
from google import genai

_api_key = os.getenv("GENAI_API_KEY")

if not _api_key:
    raise ValueError("GENAI_API_KEY is missing! Add it to .env")

client = genai.Client(api_key=_api_key)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")  # change if your account uses a different label

def _extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    The model will be prompted to return JSON. But sometimes it wraps it in text.
    This helper extracts the first JSON object found.
    """
    try:
        # find first "{" ... "}" block (simple but effective)
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            candidate = m.group(0)
            return json.loads(candidate)
    except Exception:
        pass
    # fallback: attempt to parse direct text
    try:
        return json.loads(text)
    except Exception:
        return {}

def ask_gemini_for_intent(user_text: str, language: str ) -> Dict[str, Any]:
    """
    Sends a prompt to Gemini asking for: intent, entities, reply, action.
    The model is instructed to return VALID JSON only.
    """
    # define allowed intents and an example to make model reliable
    system_instruction = """
You are an assistant for a Project Hub system. You must ONLY return one JSON object
and nothing else. The JSON object must contain these keys: "intent", "entities", "reply", "action".

- intent: one of ["create_requirement","report_bug","raise_query","get_items","language_switch","smalltalk","fallback"]
- entities: a map with extracted named fields (title, description, severity, assigned_to, type, question, language)
- reply: a short natural-language reply only in the user's language (either English or Tamil)
- User language: {language} Always produce the reply in this language.
- action: object with "type" (one of "none","create_requirement","report_bug","raise_query","list_items") and "params" for fulfillment.

Return only JSON. Example:
{"intent":"create_requirement","entities":{"title":"Mobile login","description":"Allow login via mobile number"},"reply":"Requirement created.","action":{"type":"create_requirement","params":{"title":"Mobile login","description":"Allow login via mobile number"}}}
"""
    # instruct model to produce JSON
    prompt = f"""{system_instruction}

User language: {language}
User message: \"\"\"{user_text}\"\"\"

Always write "reply" in the {language} language.
Now produce the JSON response.
"""

    # call gemini / genai SDK
    # we use models.generate_content to get text output
    # the response object has `.text` or `.content` depending on sdk version
    try:
        resp = client.models.generate_content(model=MODEL, contents=prompt)
        # SDK may return different shapes; try common accessors
        text = ""
        if hasattr(resp, "text") and resp.text:
            text = resp.text
        else:
            # try dictionary style
            text = getattr(resp, "content", None) or str(resp)
        # text may be an object with fields; make it str
        if not isinstance(text, str):
            text = str(text)
    except Exception as e:
        # If the API fails, return fallback
        return {
            "intent": "fallback",
            "entities": {},
            "reply": f"Sorry, I couldn't reach the language model: {e}",
            "action": {"type": "none", "params": {}}
        }

    parsed = _extract_json_from_text(text)
    # If parsing failed, create a safe fallback reply
    if not parsed:
        return {
            "intent": "fallback",
            "entities": {},
            "reply": "மன்னிக்கவும், நான் உங்கள் வேண்டுகோளைப் புரிந்து கொள்ளவில்லை. Please rephrase.",
            "action": {"type": "none", "params": {}}
        }
    # Ensure keys exist
    return {
        "intent": parsed.get("intent", "fallback"),
        "entities": parsed.get("entities", {}),
        "reply": parsed.get("reply", ""),
        "action": parsed.get("action", {"type":"none","params":{}})
    }
