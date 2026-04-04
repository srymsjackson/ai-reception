import json
import re
from openai import OpenAI
from app.config import settings

client = OpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """
You are a highly natural, friendly receptionist for a modern barbershop.

You speak casually, like a real human, not robotic.

Your job:
- understand what the caller wants
- ask for missing booking details naturally
- extract clean structured booking data

Important:
- If the caller gives a name, put it in caller_name
- If the caller gives a service, put it in service_requested
- If the caller gives a barber preference, put it in preferred_barber
- If the caller gives a time or day, put it in preferred_time
- If a field is missing, set it to null
- Never invent information
- Never say the appointment is confirmed or booked

Keep assistant_reply:
- short
- conversational
- one question at a time

Return ONLY valid JSON.
No markdown.
No explanation.
No extra text.

JSON schema:
{
  "intent": "booking" | "question" | "callback",
  "assistant_reply": "short conversational response",
  "caller_name": string or null,
  "service_requested": string or null,
  "preferred_barber": string or null,
  "preferred_time": string or null,
  "enough_to_complete": true or false
}
""".strip()


def fallback_response():
    return {
        "intent": "booking",
        "assistant_reply": "Got you — what time were you thinking?",
        "caller_name": None,
        "service_requested": None,
        "preferred_barber": None,
        "preferred_time": None,
        "enough_to_complete": False,
    }


def clean_service(service):
    if not service:
        return None
    s = service.lower().strip()

    if "fade" in s:
        return "fade"
    if "beard" in s:
        return "beard trim"
    if "trim" in s:
        return "trim"
    if "haircut" in s or "hair cut" in s or "cut" in s:
        return "haircut"

    return s


def clean_time(value):
    if not value:
        return None
    return value.replace(".", "").strip().lower()


def clean_barber(value):
    if not value:
        return None
    v = value.strip().lower()
    if "any" in v or "whoever" in v or "doesn't matter" in v:
        return "no preference"
    return value.strip()


def clean_name(value):
    if not value:
        return None
    return value.strip().title()


def fallback_extract_name(text: str):
    patterns = [
        r"my name is ([A-Za-z]+)",
        r"my name's ([A-Za-z]+)",
        r"this is ([A-Za-z]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).title()
    return None


def fallback_extract_barber(text: str):
    lowered = text.lower()
    if (
        "anybody is fine" in lowered
        or "any barber is fine" in lowered
        or "whoever is open" in lowered
        or "no preference" in lowered
    ):
        return "no preference"
    return None


def fallback_extract_service(text: str):
    lowered = text.lower()
    if "fade" in lowered:
        return "fade"
    if "beard" in lowered:
        return "beard trim"
    if "trim" in lowered:
        return "trim"
    if "haircut" in lowered or "hair cut" in lowered or "cut" in lowered:
        return "haircut"
    return None


def fallback_extract_time(text: str):
    match = re.search(
        r"(tomorrow(?:\s+(?:morning|afternoon|evening|night))?)|"
        r"(around\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?))|"
        r"(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?))",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(0).replace(".", "").strip().lower()
    return None


def extract_json(raw_text: str) -> dict | None:
    raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    return None


def analyze_customer_turn(user_text: str) -> dict:
    try:
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
        )

        raw_text = response.output_text.strip()
        print("RAW AI RESPONSE:", raw_text)

        data = extract_json(raw_text)
        if not data:
            print("JSON PARSE FAILED")
            data = fallback_response()
            data["assistant_reply"] = raw_text or data["assistant_reply"]

        data["intent"] = data.get("intent", "booking")
        data["assistant_reply"] = data.get("assistant_reply", "Got you — what time were you thinking?")
        data["caller_name"] = clean_name(data.get("caller_name")) or fallback_extract_name(user_text)
        data["service_requested"] = clean_service(data.get("service_requested")) or fallback_extract_service(user_text)
        data["preferred_barber"] = clean_barber(data.get("preferred_barber")) or fallback_extract_barber(user_text)
        data["preferred_time"] = clean_time(data.get("preferred_time")) or fallback_extract_time(user_text)
        data["enough_to_complete"] = bool(data.get("enough_to_complete", False))

        print("CLEANED DATA:", data)
        return data

    except Exception as e:
        print("OPENAI ERROR:", str(e))
        data = fallback_response()
        data["caller_name"] = fallback_extract_name(user_text)
        data["service_requested"] = fallback_extract_service(user_text)
        data["preferred_barber"] = fallback_extract_barber(user_text)
        data["preferred_time"] = fallback_extract_time(user_text)
        return data