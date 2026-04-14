"""
session_manager.py — Shared DatabaseSessionService + state helpers.

READ  → session_service.get_session()  →  session.state
WRITE → session_service.append_event() with EventActions(state_delta={...})
"""

import os
import time
import uuid

from google.adk.sessions import DatabaseSessionService
from google.adk.events import Event, EventActions

# ── Shared service instance ──────────────────────────────────────────────
DB_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///./travel_agent_data.db")
session_service = DatabaseSessionService(db_url=DB_URL)

APP_NAME = "travel_agent_app"


# ═══════════════════════════════════════════════════════════════════════════
# User identification — how the app knows "who are you" after restart
# ═══════════════════════════════════════════════════════════════════════════

def name_to_user_id(name: str) -> str:
    """Convert a display name to a stable user_id.

    'Alice'       → 'alice'
    'Bob Smith'   → 'bob_smith'
    'user_001'    → 'user_001'

    This is the KEY to persistence: same name → same user_id → same
    preferences from DatabaseSessionService, even after restart.
    """
    return name.strip().lower().replace(" ", "_")


async def find_or_create_session(user_id: str) -> tuple:
    """Find the most recent session for a user, or create a new one.

    Returns:
        (session, session_id, is_new)
    """
    existing = await session_service.list_sessions(
        app_name=APP_NAME, user_id=user_id,
    )

    if existing and existing.sessions:
        session_id = existing.sessions[0].id
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id,
        )
        return session, session_id, False

    # Create new
    session_id = f"session_{user_id}_{int(time.time())}"
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id,
    )
    return session, session_id, True


# ═══════════════════════════════════════════════════════════════════════════
# READ state
# ═══════════════════════════════════════════════════════════════════════════

async def read_user_preferences(session_id: str, user_id: str) -> dict:
    """Read 'user:pref_*' keys → clean dict like {'dietary': 'vegetarian'}."""
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id,
    )
    if not session:
        return {}
    return {
        k.replace("user:pref_", ""): v
        for k, v in session.state.items()
        if k.startswith("user:pref_") and v
    }


async def read_state(session_id: str, user_id: str) -> dict:
    """Read full state dict."""
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id,
    )
    return dict(session.state) if session else {}


# ═══════════════════════════════════════════════════════════════════════════
# WRITE state — via append_event + EventActions(state_delta)
# ═══════════════════════════════════════════════════════════════════════════

async def write_state(session_id: str, state_delta: dict, user_id: str) -> bool:
    """Write key-value pairs into session state via append_event."""
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id,
    )
    if not session:
        return False

    actions = EventActions(state_delta=state_delta)
    event = Event(
        invocation_id=str(uuid.uuid4()),
        author="system",
        actions=actions,
        timestamp=time.time(),
    )
    await session_service.append_event(session=session, event=event)
    return True


async def save_user_preference(session_id: str, key: str, value: str,
                               user_id: str) -> bool:
    """Save one preference with 'user:pref_' prefix (persists across sessions)."""
    return await write_state(session_id, {f"user:pref_{key}": value}, user_id)


async def save_user_preferences_bulk(session_id: str, prefs: dict,
                                     user_id: str) -> bool:
    """Save multiple preferences at once."""
    delta = {f"user:pref_{k}": v for k, v in prefs.items()}
    return await write_state(session_id, delta, user_id)
