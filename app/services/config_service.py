"""Helpers for reading per-business configuration and call completion rules."""

import json
from sqlmodel import Session, select
from app.models import BusinessConfig


def get_business_config(session: Session, business_id: int) -> BusinessConfig | None:
    """Fetch the config row for one business, if present."""
    statement = select(BusinessConfig).where(BusinessConfig.business_id == business_id)
    return session.exec(statement).first()


def get_required_fields(config: BusinessConfig | None) -> list[str]:
    """Return fields that must be collected before the call is complete."""
    if not config:
        return ["service_requested", "preferred_time"]

    try:
        return json.loads(config.required_fields_json or "[]")
    except Exception:
        return []


def has_specific_time(value: str | None) -> bool:
    """Treat vague times like 'tomorrow' as incomplete for booking purposes."""
    if not value:
        return False

    v = value.strip().lower()
    vague_only = {
        "today",
        "tomorrow",
        "this afternoon",
        "this morning",
        "tonight",
        "next week",
        "sometime tomorrow",
        "sometime today",
    }

    return v not in vague_only


def is_field_complete(field_name: str, state: dict) -> bool:
    """Apply per-field completion rules against in-memory call state."""
    value = state.get(field_name)

    if field_name == "preferred_time":
        return has_specific_time(value)

    if field_name == "notes":
        if isinstance(value, list):
            return bool(value)
        return bool(value and str(value).strip())

    return bool(value and str(value).strip())


def get_first_missing_required_field(
    config: BusinessConfig | None, state: dict
) -> str | None:
    """Return the next required field still missing, preserving configured order."""
    required_fields = get_required_fields(config)

    for field_name in required_fields:
        if not is_field_complete(field_name, state):
            return field_name

    return None


def get_prompt_for_field(config: BusinessConfig | None, field_name: str) -> str:
    """Map a field name to a configurable ask prompt with safe defaults."""
    default_prompt_map = {
        "caller_name": "Can I get your name, please?",
        "service_requested": "What service are you looking for?",
        "preferred_time": "What specific time were you thinking?",
        "preferred_barber": "Do you have a preferred staff member?",
        "notes": "Can you tell me a little more about what you need?",
    }

    if not config:
        return default_prompt_map.get(field_name) or "Can you tell me a bit more?"

    prompt_map = {
        "caller_name": config.ask_name_prompt,
        "service_requested": config.ask_service_prompt,
        "preferred_time": config.ask_time_prompt,
        "preferred_barber": config.ask_staff_prompt,
        "notes": "Can you tell me a little more about what you need?",
    }

    return prompt_map.get(field_name) or "Can you tell me a bit more?"