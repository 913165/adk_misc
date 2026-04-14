"""
main.py — Travel Agent with user identification at startup.

═══════════════════════════════════════════════════════════════════
HOW THE AGENT KNOWS WHO YOU ARE AFTER RESTART:
═══════════════════════════════════════════════════════════════════

1. App starts → asks "What's your name?"
2. Name is converted to a stable user_id:
   "Alice" → "alice",  "Bob Smith" → "bob_smith"
3. DatabaseSessionService looks up existing sessions for that user_id
4. If found → resumes session → preferences are already in state
5. If not found → creates new session → agent will onboard the user

Same name = same user_id = same preferences, even after restart.

Usage:
    python main.py                    # Asks name interactively
    python main.py --seed             # Insert sample data
    python main.py --show-profiles    # Show all stored profiles
    python main.py --inspect-db       # Show raw DB tables
"""

import asyncio
import argparse
import os
import time
import uuid
import sqlite3

from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.events import Event, EventActions
from google.genai.types import Content, Part

import active_context
import session_manager
from travel_agent.tools import travel_tools

load_dotenv()

APP_NAME = session_manager.APP_NAME
DB_URL = session_manager.DB_URL


# ── Agent ────────────────────────────────────────────────────────────────
INSTRUCTION = """
You are TravelBot — a personalized travel planning assistant.

TOOLS (read/write via DatabaseSessionService):
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
    model="gemini-flash-latest",
    instruction=INSTRUCTION,
    tools=travel_tools,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Seed sample data
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_seed():
    """Insert sample profiles matching the diagram."""
    svc = session_manager.session_service

    samples = [
        ("Alice", {"dietary": "vegetarian", "favorite_theme": "historic",
                    "transport_mode": "walking"}),
        ("Bob",   {"dietary": "vegan"}),
    ]

    for name, prefs in samples:
        uid = session_manager.name_to_user_id(name)
        sid = f"seed_{uid}"

        # Create session if needed
        existing = await svc.list_sessions(app_name=APP_NAME, user_id=uid)
        session = None
        if existing and existing.sessions:
            for s in existing.sessions:
                if s.id == sid:
                    session = await svc.get_session(
                        app_name=APP_NAME, user_id=uid, session_id=sid
                    )
                    break
        if session is None:
            session = await svc.create_session(
                app_name=APP_NAME, user_id=uid, session_id=sid
            )

        # Save name as a preference too
        delta = {f"user:pref_{k}": v for k, v in prefs.items()}
        delta["user:pref_display_name"] = name

        actions = EventActions(state_delta=delta)
        event = Event(
            invocation_id=str(uuid.uuid4()),
            author="system", actions=actions, timestamp=time.time(),
        )
        await svc.append_event(session=session, event=event)
        print(f"  ✅ {name} (user_id={uid}): {prefs}")

    print()
    print("  Stored in DatabaseSessionService as user: prefixed state.")
    print("  Now run:  python main.py  →  type 'Alice' or 'Bob' when asked.\n")


# ═══════════════════════════════════════════════════════════════════════════════
# Show all profiles
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_show_profiles():
    svc = session_manager.session_service

    print(f"\n  {'user_id':<12s}  {'preference_key':<20s}  {'preference_value'}")
    print(f"  {'─' * 12}  {'─' * 20}  {'─' * 20}")

    found = False
    # Check common user_ids — in production you'd query the DB directly
    for uid in ["alice", "bob", "user_001", "user_002", "charlie"]:
        existing = await svc.list_sessions(app_name=APP_NAME, user_id=uid)
        if not existing or not existing.sessions:
            continue
        session = await svc.get_session(
            app_name=APP_NAME, user_id=uid, session_id=existing.sessions[0].id,
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
# Inspect raw DB
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_inspect_db():
    db_file = DB_URL.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    if not os.path.exists(db_file):
        print(f"  DB not found: {db_file}")
        return

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"\n  Tables: {tables}\n")

    for table in tables:
        cursor.execute(f"SELECT * FROM {table} LIMIT 10;")
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        print(f"  ── {table} ({len(rows)} rows) ── Columns: {cols}")
        for row in rows:
            display = [str(v)[:70] + "..." if len(str(v)) > 70 else str(v) for v in row]
            print(f"    {display}")
        print()
    conn.close()


def _is_stale_session_error(exc: Exception) -> bool:
    """Detect ADK's optimistic-concurrency stale session error."""
    return "session has been modified in storage since it was loaded" in str(exc).lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Interactive Chat — with user identification at startup
# ═══════════════════════════════════════════════════════════════════════════════

async def run_interactive():
    """Main chat loop with user identification."""

    # ─────────────────────────────────────────────────────────────────────
    # STEP 1: Ask "Who are you?"
    # ─────────────────────────────────────────────────────────────────────
    print()
    print("=" * 58)
    print("   TravelBot — Personalized Travel Assistant")
    print("=" * 58)
    print()

    try:
        name = input("  What's your name? → ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Goodbye!")
        return

    if not name:
        print("  No name provided. Exiting.")
        return

    # ─────────────────────────────────────────────────────────────────────
    # STEP 2: Convert name → user_id
    #   "Alice"      → "alice"
    #   "Bob Smith"  → "bob_smith"
    #   Same name always → same user_id → same stored preferences
    # ─────────────────────────────────────────────────────────────────────
    user_id = session_manager.name_to_user_id(name)
    print(f"  (user_id: {user_id})")

    # ─────────────────────────────────────────────────────────────────────
    # STEP 3: Find existing session or create new one
    # ─────────────────────────────────────────────────────────────────────
    session, session_id, is_new = await session_manager.find_or_create_session(user_id)

    if is_new:
        # Store the display name as a preference
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

    # ─────────────────────────────────────────────────────────────────────
    # STEP 4: Set active context (tools read from here)
    # ─────────────────────────────────────────────────────────────────────
    active_context.set_context(sid=session_id, uid=user_id, name=name)

    # ─────────────────────────────────────────────────────────────────────
    # STEP 5: Create Runner with same DatabaseSessionService
    # ─────────────────────────────────────────────────────────────────────
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_manager.session_service,
    )

    print("  Type 'quit' to exit  |  'profile' to show stored prefs")
    print("─" * 58)

    # ─────────────────────────────────────────────────────────────────────
    # STEP 6: Chat loop
    # ─────────────────────────────────────────────────────────────────────
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("  Goodbye! Your preferences are saved in the database.")
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

                # Persist any tool-staged preference updates after the turn ends.
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
                        except ValueError as flush_exc:
                            if not _is_stale_session_error(flush_exc):
                                raise
                            if flush_attempts >= max_attempts:
                                active_context.stage_preferences(pending)
                                print("  Saved response, but profile sync is delayed. It will retry next turn.")
                                break

                            _, session_id, _ = await session_manager.find_or_create_session(user_id)
                            active_context.set_context(sid=session_id, uid=user_id, name=name)
                            await asyncio.sleep(0.15 * flush_attempts)

                break
            except ValueError as exc:
                if not _is_stale_session_error(exc):
                    raise

                print("\n  Session changed while processing. Reloading and retrying...")

                if attempt >= max_attempts:
                    print("  Couldn't recover session state. Please resend your last message.")
                    break

                # Reload the latest session snapshot and rebuild runner context.
                _, session_id, _ = await session_manager.find_or_create_session(user_id)
                active_context.set_context(sid=session_id, uid=user_id, name=name)
                runner = Runner(
                    agent=agent,
                    app_name=APP_NAME,
                    session_service=session_manager.session_service,
                )
                await asyncio.sleep(0.25 * attempt)


async def main_async(args: argparse.Namespace) -> None:
    """Dispatch CLI commands."""
    if args.seed:
        await cmd_seed()
    elif args.show_profiles:
        await cmd_show_profiles()
    elif args.inspect_db:
        cmd_inspect_db()
    else:
        await run_interactive()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TravelBot profile-store demo")
    parser.add_argument("--seed", action="store_true", help="Insert sample profile data")
    parser.add_argument("--show-profiles", action="store_true", help="Show stored profiles")
    parser.add_argument("--inspect-db", action="store_true", help="Inspect raw DB tables")
    return parser.parse_args()


def main() -> None:
    asyncio.run(main_async(parse_args()))


if __name__ == "__main__":
    main()

