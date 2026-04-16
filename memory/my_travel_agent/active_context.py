"""
active_context.py — Holds the current session/user context.

Set by main.py at startup (after user identifies themselves).
Read by tools instead of ToolContext.
"""

session_id: str = ""
user_id: str = ""
user_name: str = ""

_pending_preferences: dict = {}


def set_context(sid: str, uid: str, name: str = "") -> None:
    global session_id, user_id, user_name
    session_id = sid
    user_id = uid
    user_name = name or uid


def stage_preferences(prefs: dict) -> None:
    """Stage preferences for deferred write."""
    global _pending_preferences
    _pending_preferences.update(prefs)


def consume_pending_preferences() -> dict:
    """Return and clear any staged preferences."""
    global _pending_preferences
    result = dict(_pending_preferences)
    _pending_preferences = {}
    return result
