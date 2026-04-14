"""
active_context.py — Holds the current session/user context.

Set by main.py at startup (after user identifies themselves).
Read by tools instead of ToolContext.
"""

from typing import Dict

session_id: str = ""
user_id: str = ""
user_name: str = ""
# Preferences captured during a model turn; flushed to DB after runner completes.
pending_preferences: Dict[str, str] = {}


def set_context(sid: str, uid: str, name: str = "") -> None:
    global session_id, user_id, user_name, pending_preferences
    session_id = sid
    user_id = uid
    user_name = name or uid
    pending_preferences = {}


def stage_preference(preference_key: str, preference_value: str) -> None:
    pending_preferences[preference_key] = preference_value


def stage_preferences(prefs: Dict[str, str]) -> None:
    pending_preferences.update(prefs)


def consume_pending_preferences() -> Dict[str, str]:
    global pending_preferences
    out = dict(pending_preferences)
    pending_preferences = {}
    return out


def merge_with_pending_preferences(stored_prefs: Dict[str, str]) -> Dict[str, str]:
    merged = dict(stored_prefs)
    for key, value in pending_preferences.items():
        if value:
            merged[key] = value
        else:
            merged.pop(key, None)
    return merged
