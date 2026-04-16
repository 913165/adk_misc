"""
main.py — Travel Agent with VertexAiSessionService.

═══════════════════════════════════════════════════════════════════
CHANGED FROM SQLITE VERSION:
  DatabaseSessionService (local SQLite)
    → VertexAiSessionService (Google Cloud Vertex AI)model

  app_name = "travel_agent_app"
    → app_name = REASONING_ENGINE_ID (full resource name)

  DB_URL, aiosqlite, inspect-db
    → removed (no local DB — everything lives in Vertex AI)

Everything else stays the same: tools, agent, user identification.
═══════════════════════════════════════════════════════════════════

Usage:
    python main.py                    # Asks name, chats
    python main.py --seed             # Insert Alice & Bob sample data
    python main.py --show-profiles    # Show all stored profiles
"""

import asyncio
import argparse
import os
import time
import uuid

from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.events import Event, EventActions
from google.genai.types import Content, Part

import active_context
import session_manager
from my_travel_agent.tools import travel_tools

load_dotenv()

APP_NAME = session_manager.APP_NAME


# ── Agent ────────────────────────────────────────────────────────────────
INSTRUCTION = """
You are TravelBot — a personalized travel planning assistant.

TOOLS (read/write via VertexAiSessionService):
• recall_user_preferences()           — Load ALL stored preferences
• get_user_preference(preference_key) — Look up one preference
• save_user_preference(key, value)    — Save/update one preference
• save_multiple_preferences(...)      — Save several at once
• delete_user_preference(key)         — Remove a preference

FLOW:
1. ALWAYS call recall_user_preferences() FIRST.
2. If prefs exist → greet by name, reference their preferences.
3. If no prefs → welcome new user, ask about dietary needs, travel theme,
   transport mode, budget, accommodation. Save what they share.
4. Use preferences to personalize all recommendations.
5. If user mentions new preferences mid-conversation, save them immediately.
"""

agent = LlmAgent(
    name="travel_agent",
    model="gemini-2.5-pro",
    instruction=INSTRUCTION,
    tools=travel_tools,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Seed sample data (via append_event to Vertex AI)
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_seed():
    """Insert sample profiles into VertexAiSessionService."""
    svc = session_manager.session_service

    samples = [
        ("Alice", {"dietary": "vegetarian", "favorite_theme": "historic",
                    "transport_mode": "walking"}),
        ("Bob",   {"dietary": "vegan"}),
    ]

    for name, prefs in samples:
        uid = session_manager.name_to_user_id(name)

        # Find or create session
        existing = await svc.list_sessions(app_name=APP_NAME, user_id=uid)
        session = None
        if existing and existing.sessions:
            session = await svc.get_session(
                app_name=APP_NAME, user_id=uid,
                session_id=existing.sessions[0].id,
            )

        if session is None:
            session = await svc.create_session(
                app_name=APP_NAME, user_id=uid,
            )

        # Write preferences via append_event + state_delta
        delta = {f"user:pref_{k}": v for k, v in prefs.items()}
        delta["user:pref_display_name"] = name

        actions = EventActions(state_delta=delta)
        event = Event(
            invocation_id=str(uuid.uuid4()),
            author="system",
            actions=actions,
            timestamp=time.time(),
        )
        await svc.append_event(session=session, event=event)
        print(f"  ✅ {name} (user_id={uid}): {prefs}")

    print()
    print("  Stored in VertexAiSessionService as user: prefixed state.")
    print("  Now run:  python main.py  →  type 'Alice' or 'Bob' when asked.\n")


# ═══════════════════════════════════════════════════════════════════════════════
# Show all profiles
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_show_profiles():
    """List preferences for known users from Vertex AI."""
    svc = session_manager.session_service

    print(f"\n  {'user_id':<12s}  {'preference_key':<20s}  {'preference_value'}")
    print(f"  {'─' * 12}  {'─' * 20}  {'─' * 20}")

    found = False
    for uid in ["alice", "bob", "charlie", "user_001", "user_002"]:
        existing = await svc.list_sessions(app_name=APP_NAME, user_id=uid)
        if not existing or not existing.sessions:
            continue
        session = await svc.get_session(
            app_name=APP_NAME, user_id=uid,
            session_id=existing.sessions[0].id,
        )
        if not session:
            continue
        for k, v in sorted(session.state.items()):
            if k.startswith("user:pref_") and v:
                clean = k.replace("user:pref_", "")
                print(f"  {uid:<12s}  {clean:<20s}  {v}")
                found = True

    if not found:
        print("  (no profiles found — run --seed first)")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
# Stale session handling
# ═══════════════════════════════════════════════════════════════════════════════

def _is_stale_session_error(exc: Exception) -> bool:
    """Detect ADK's optimistic-concurrency stale session error."""
    return "session has been modified in storage since it was loaded" in str(exc).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Interactive Chat
# ═══════════════════════════════════════════════════════════════════════════════

async def run_interactive():
    """Main chat loop with user identification."""

    print()
    print("=" * 58)
    print("   TravelBot — VertexAiSessionService Edition")
    print(f"   Project:  {session_manager.PROJECT_ID}")
    print(f"   Location: {session_manager.LOCATION}")
    print("=" * 58)
    print()

    # ── STEP 1: Ask "Who are you?" ───────────────────────────────────────
    try:
        name = input("  What's your name? → ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Goodbye!")
        return

    if not name:
        print("  No name provided. Exiting.")
        return

    # ── STEP 2: Convert name → user_id ───────────────────────────────────
    user_id = session_manager.name_to_user_id(name)
    print(f"  (user_id: {user_id})")

    # ── STEP 3: Find or create session in Vertex AI ──────────────────────
    session, session_id, is_new = await session_manager.find_or_create_session(user_id)

    if is_new:
        await session_manager.save_user_preference(session_id, "display_name", name, user_id)
        print(f"\n  🆕 Welcome! New profile created for '{name}'.")
        print("     The agent will ask about your preferences.\n")
    else:
        prefs = await session_manager.read_user_preferences(session_id, user_id)
        pref_count = len([v for v in prefs.values() if v])
        print(f"\n  ✅ Welcome back, {name}! Resumed with {pref_count} stored preferences.")
        if prefs:
            for k, v in sorted(prefs.items()):
                if v and k != "display_name":
                    print(f"     • {k}: {v}")
        print()

    # ── STEP 4: Set active context ───────────────────────────────────────
    active_context.set_context(sid=session_id, uid=user_id, name=name)

    # ── STEP 5: Create Runner ────────────────────────────────────────────
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_manager.session_service,
    )

    print("  Type 'quit' to exit  |  'profile' to show stored prefs")
    print("─" * 58)

    # ── STEP 6: Chat loop ────────────────────────────────────────────────
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("  Goodbye! Your preferences are saved in Vertex AI.")
            break
        if user_input.lower() == "profile":
            prefs = await session_manager.read_user_preferences(session_id, user_id)
            print(f"\n  📋 Profile for {name} ({user_id}):")
            for k, v in sorted(prefs.items()):
                if v and k != "display_name":
                    print(f"    • {k}: {v}")
            if not prefs:
                print("    (no preferences yet)")
            print()
            continue

        user_message = Content(parts=[Part(text=user_input)])

        max_attempts = 3
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            try:
                print("\nTravelBot: ", end="", flush=True)
                async for event in runner.run_async(
                    session_id=session_id,
                    user_id=user_id,
                    new_message=user_message,
                ):
                    if event.is_final_response() and event.content and event.content.parts:
                        print(event.content.parts[0].text)

                # Flush any pending preference writes
                pending = active_context.consume_pending_preferences()
                if pending:
                    flush_attempts = 0
                    while True:
                        flush_attempts += 1
                        try:
                            await session_manager.save_user_preferences_bulk(
                                session_id=session_id,
                                prefs=pending,
                                user_id=user_id,
                            )
                            break
                        except (ValueError, Exception) as flush_exc:
                            if not _is_stale_session_error(flush_exc):
                                raise
                            if flush_attempts >= max_attempts:
                                active_context.stage_preferences(pending)
                                print("  Saved response, but profile sync delayed. Will retry next turn.")
                                break
                            _, session_id, _ = await session_manager.find_or_create_session(user_id)
                            active_context.set_context(sid=session_id, uid=user_id, name=name)
                            await asyncio.sleep(0.15 * flush_attempts)

                break

            except (ValueError, Exception) as exc:
                if not _is_stale_session_error(exc):
                    raise
                print("\n  Session changed while processing. Reloading...")
                if attempt >= max_attempts:
                    print("  Couldn't recover. Please resend your last message.")
                    break
                _, session_id, _ = await session_manager.find_or_create_session(user_id)
                active_context.set_context(sid=session_id, uid=user_id, name=name)
                runner = Runner(
                    agent=agent,
                    app_name=APP_NAME,
                    session_service=session_manager.session_service,
                )
                await asyncio.sleep(0.25 * attempt)


# ═══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

async def main_async(args):
    if args.seed:
        await cmd_seed()
    elif args.show_profiles:
        await cmd_show_profiles()
    else:
        await run_interactive()


def main():
    parser = argparse.ArgumentParser(description="TravelBot — VertexAI Profile Store")
    parser.add_argument("--seed", action="store_true",
                        help="Insert Alice & Bob sample data into Vertex AI")
    parser.add_argument("--show-profiles", action="store_true",
                        help="Show all stored user profiles")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
