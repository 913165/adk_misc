"""
tools.py — Travel Agent tools using ADK DatabaseSessionService directly.

NO ToolContext anywhere. Tools call session_manager for reads and stage writes
in active_context so main.py can flush changes after each runner turn.
"""

from typing import Any, Dict
import active_context
import session_manager


# ═══════════════════════════════════════════════════════════════════════════
# Tool 1 — Recall all preferences
# ═══════════════════════════════════════════════════════════════════════════
async def recall_user_preferences() -> Dict[str, Any]:
    """Load all stored preferences for the current user.

    Call this at the START of every conversation to personalize responses.
    Data comes from ADK DatabaseSessionService (user: prefixed state).
    """
    stored_prefs = await session_manager.read_user_preferences(
        session_id=active_context.session_id,
        user_id=active_context.user_id,
    )
    prefs = active_context.merge_with_pending_preferences(stored_prefs)
    return {
        "user_id": active_context.user_id,
        "user_name": active_context.user_name,
        "preferences": prefs,
        "count": len(prefs),
        "message": (
            f"Found {len(prefs)} preferences for {active_context.user_name}."
            if prefs else
            f"No preferences yet for {active_context.user_name}. Please onboard them!"
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Tool 2 — Save a single preference
# ═══════════════════════════════════════════════════════════════════════════
async def save_user_preference(
    preference_key: str,
    preference_value: str,
) -> Dict[str, Any]:
    """Save a user preference (persists across ALL sessions via DB).

    Args:
        preference_key:   e.g. 'dietary', 'favorite_theme', 'transport_mode'
        preference_value: e.g. 'vegetarian', 'historic', 'walking'
    """
    active_context.stage_preference(preference_key, preference_value)
    return {
        "status": "saved",
        "preference_key": preference_key,
        "preference_value": preference_value,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Tool 3 — Save multiple preferences at once
# ═══════════════════════════════════════════════════════════════════════════
async def save_multiple_preferences(
    dietary: str = "",
    favorite_theme: str = "",
    transport_mode: str = "",
    budget: str = "",
    accommodation: str = "",
) -> Dict[str, Any]:
    """Save several travel preferences in one call.

    Only non-empty values are saved.

    Args:
        dietary:         e.g. 'vegetarian', 'vegan', 'halal', 'none'
        favorite_theme:  e.g. 'historic', 'adventure', 'beach', 'cultural'
        transport_mode:  e.g. 'walking', 'public_transit', 'car', 'cycling'
        budget:          e.g. 'budget', 'mid-range', 'luxury'
        accommodation:   e.g. 'hotel', 'hostel', 'airbnb', 'resort'
    """
    prefs = {}
    if dietary:        prefs["dietary"] = dietary
    if favorite_theme: prefs["favorite_theme"] = favorite_theme
    if transport_mode: prefs["transport_mode"] = transport_mode
    if budget:         prefs["budget"] = budget
    if accommodation:  prefs["accommodation"] = accommodation

    if not prefs:
        return {"status": "no_changes", "message": "No preferences provided."}

    active_context.stage_preferences(prefs)
    return {"status": "saved", "saved": prefs}


# ═══════════════════════════════════════════════════════════════════════════
# Tool 4 — Get a single preference
# ═══════════════════════════════════════════════════════════════════════════
async def get_user_preference(preference_key: str) -> Dict[str, Any]:
    """Look up one specific preference.

    Args:
        preference_key: e.g. 'dietary', 'transport_mode'
    """
    stored_prefs = await session_manager.read_user_preferences(
        session_id=active_context.session_id,
        user_id=active_context.user_id,
    )
    prefs = active_context.merge_with_pending_preferences(stored_prefs)
    value = prefs.get(preference_key)
    if value is None:
        return {"found": False, "preference_key": preference_key}
    return {"found": True, "preference_key": preference_key, "preference_value": value}


# ═══════════════════════════════════════════════════════════════════════════
# Tool 5 — Delete a preference
# ═══════════════════════════════════════════════════════════════════════════
async def delete_user_preference(preference_key: str) -> Dict[str, Any]:
    """Remove a preference (sets value to empty string).

    Args:
        preference_key: The preference to remove.
    """
    active_context.stage_preference(preference_key, "")
    return {"status": "cleared", "preference_key": preference_key}


# ═══════════════════════════════════════════════════════════════════════════
travel_tools = [
    recall_user_preferences,
    save_user_preference,
    save_multiple_preferences,
    get_user_preference,
    delete_user_preference,
]
