"""
tools.py — Travel Agent tools using ADK session service directly.

NO ToolContext anywhere. Works with both DatabaseSessionService
and VertexAiSessionService — tools don't care which backend is used.
"""

from typing import Any, Dict
import active_context
import session_manager


async def recall_user_preferences() -> Dict[str, Any]:
    """Load all stored preferences for the current user.

    Call this at the START of every conversation to personalize responses.
    """
    prefs = await session_manager.read_user_preferences(
        session_id=active_context.session_id,
        user_id=active_context.user_id,
    )
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


async def save_user_preference(
    preference_key: str,
    preference_value: str,
) -> Dict[str, Any]:
    """Save a user preference (persists across ALL sessions).

    Args:
        preference_key:   e.g. 'dietary', 'favorite_theme', 'transport_mode'
        preference_value: e.g. 'vegetarian', 'historic', 'walking'
    """
    success = await session_manager.save_user_preference(
        session_id=active_context.session_id,
        key=preference_key,
        value=preference_value,
        user_id=active_context.user_id,
    )
    return {
        "status": "saved" if success else "error",
        "preference_key": preference_key,
        "preference_value": preference_value,
    }


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

    success = await session_manager.save_user_preferences_bulk(
        session_id=active_context.session_id,
        prefs=prefs,
        user_id=active_context.user_id,
    )
    return {"status": "saved" if success else "error", "saved": prefs}


async def get_user_preference(preference_key: str) -> Dict[str, Any]:
    """Look up one specific preference.

    Args:
        preference_key: e.g. 'dietary', 'transport_mode'
    """
    prefs = await session_manager.read_user_preferences(
        session_id=active_context.session_id,
        user_id=active_context.user_id,
    )
    value = prefs.get(preference_key)
    if value is None:
        return {"found": False, "preference_key": preference_key}
    return {"found": True, "preference_key": preference_key, "preference_value": value}


async def delete_user_preference(preference_key: str) -> Dict[str, Any]:
    """Remove a preference (sets value to empty string).

    Args:
        preference_key: The preference to remove.
    """
    success = await session_manager.save_user_preference(
        session_id=active_context.session_id,
        key=preference_key,
        value="",
        user_id=active_context.user_id,
    )
    return {"status": "cleared" if success else "error", "preference_key": preference_key}


travel_tools = [
    recall_user_preferences,
    save_user_preference,
    save_multiple_preferences,
    get_user_preference,
    delete_user_preference,
]
