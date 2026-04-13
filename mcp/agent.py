import os
import asyncio
import shutil
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters
from google.genai import types


def configure_environment():
    print("Configuring environment...")
    os.environ["GOOGLE_API_KEY"] = os.getenv(
        "GOOGLE_API_KEY", "your key"
    )
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

    DB_FOLDER = os.path.abspath("mcp-university-project/db")
    DB_FILENAME = "university.db"
    DB_PATH = os.path.join(DB_FOLDER, DB_FILENAME)


    print(f"Database folder : {DB_FOLDER}")
    print(f"Database file   : {DB_FILENAME}")

    # --- Pre-flight checks ---
    if not os.path.isdir(DB_FOLDER):
        raise FileNotFoundError(
            f"Database folder not found: {DB_FOLDER}\n"
            f"  → Make sure the 'mcp-university-project/db' directory exists "
            f"relative to your working directory: {os.getcwd()}"
        )

    if not os.path.isfile(DB_PATH):
        raise FileNotFoundError(
            f"Database file not found: {DB_PATH}\n"
            f"  → Make sure '{DB_FILENAME}' exists inside '{DB_FOLDER}'"
        )

    # Check that 'uv' is installed and on PATH
    uv_path = shutil.which("uv")
    if uv_path is None:
        raise FileNotFoundError(
            "'uv' command not found on PATH.\n"
            "  → Install it: https://docs.astral.sh/uv/getting-started/installation/\n"
            "  → Or use 'pip install uv' / 'curl -LsSf https://astral.sh/uv/install.sh | sh'"
        )
    print(f"'uv' found at   : {uv_path}")

    return DB_FOLDER, DB_FILENAME


def create_university_agent(MCP_SERVER_PATH, DB_PATH):
    print("Creating university agent...")

    # Verify MCP server directory exists
    if not os.path.isdir(MCP_SERVER_PATH):
        raise FileNotFoundError(
            f"MCP server directory not found: {MCP_SERVER_PATH}\n"
            f"  → Make sure the 'sqlite' folder (with pyproject.toml) exists "
            f"relative to your working directory: {os.getcwd()}"
        )

    AGENT_MODEL = "gemini-flash-latest"

    university_agent = Agent(
        name="University_SQLite_Agent",
        model=AGENT_MODEL,
        description=(
            "Intelligent university management agent with direct access to a SQLite database. "
            "Handles queries about students, courses, professors, enrollments, assignments, and submissions."
        ),
        tools=[
            McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command="uv",
                        args=[
                            "--directory", MCP_SERVER_PATH,
                            "run", "mcp-server-sqlite",
                            "--db-path", DB_PATH,
                        ],
                    )
                )
            )
        ],
        instruction=f"""
            You are an intelligent university management agent with direct access
            to a SQLite database via the MCP server.

            The database contains the following tables:
              - students     : id, name, email, phone, date_of_birth, enrollment_date,
                               department, year_of_study, gpa, status
              - professors   : id, name, email, department, designation, phone, joined_on
              - courses      : id, code, title, department, credits, instructor,
                               max_capacity, schedule
              - enrollments  : id, student_id, course_id, enrolled_on, grade
              - assignments  : id, course_id, title, due_date, max_marks
              - submissions  : id, assignment_id, student_id, submitted_on,
                               marks_obtained, feedback

            Your responsibilities:
              - Answer questions about students, professors, courses, and performance
              - Run SQL queries to retrieve or summarise data accurately
              - Identify top performers, at-risk students, or pending submissions
              - Never fabricate data — always query the database for real answers
              - Present results in a clean, readable format
        """,
    )

    print(f"Agent '{university_agent.name}' created using model '{AGENT_MODEL}'.")
    return university_agent


async def setup_runner(university_agent):
    print("Setting up session and runner...")

    session_service = InMemorySessionService()
    APP_NAME   = "university_app"
    USER_ID    = "admin_1"
    SESSION_ID = "session_001"

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )
    print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

    runner = Runner(
        agent=university_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    print(f"Runner created for agent '{runner.agent.name}'.")
    return runner, USER_ID, SESSION_ID


async def call_agent_async(query: str, runner, user_id, session_id):
    print(f"\n>>> Query: {query}")

    content = types.Content(role="user", parts=[types.Part(text=query)])
    final_response = "Agent did not produce a final response."

    try:
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                elif event.actions and event.actions.escalate:
                    final_response = (
                        f"Agent escalated: {event.error_message or 'No specific message.'}"
                    )
                break

    except FileNotFoundError as e:
        final_response = (
            f"[MCP Connection Error] Could not start the MCP server process.\n"
            f"  Detail: {e}\n"
            f"  → Ensure 'uv' is installed and the MCP server path is correct.\n"
            f"  → Ensure 'mcp-server-sqlite' is listed as a dependency in your pyproject.toml."
        )

    except ExceptionGroup as eg:
        # Python 3.11+ TaskGroup wraps errors in ExceptionGroup
        messages = []
        for exc in eg.exceptions:
            messages.append(f"  - {type(exc).__name__}: {exc}")
        detail = "\n".join(messages)
        final_response = (
            f"[MCP Error] One or more errors occurred while running the agent:\n"
            f"{detail}\n\n"
            f"  Common fixes:\n"
            f"  1. Make sure 'uv' is installed and on your PATH.\n"
            f"  2. Make sure the MCP server directory has a valid pyproject.toml with 'mcp-server-sqlite'.\n"
            f"  3. Make sure the database file exists at the configured path."
        )

    except Exception as e:
        final_response = (
            f"[Unexpected Error] {type(e).__name__}: {e}\n"
            f"  → Check your MCP server configuration, network, and Google API key."
        )

    print(f"<<< Response: {final_response}")
    return final_response


async def interact_with_agent(runner, user_id, session_id):
    print("\n" + "=" * 60)
    print("  University Management Agent — ready")
    print("  Type 'exit' to end the session")
    print("=" * 60)

    while True:
        try:
            user_input = input("\n>>> Your question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if not user_input:
            continue

        if user_input.lower() == "exit":
            print("Session ended.")
            break

        await call_agent_async(user_input, runner, user_id, session_id)


async def main_async():
    try:
        DB_FOLDER, DB_FILENAME = configure_environment()
    except FileNotFoundError as e:
        print(f"\n[Setup Error] {e}")
        return

    DB_PATH = os.path.join(DB_FOLDER, DB_FILENAME)
    MCP_SERVER_PATH = os.path.abspath("mcp-university-project/sqlite")

    try:
        university_agent = create_university_agent(MCP_SERVER_PATH, DB_PATH)
    except FileNotFoundError as e:
        print(f"\n[Setup Error] {e}")
        return
    except Exception as e:
        print(f"\n[Agent Creation Error] {type(e).__name__}: {e}")
        return

    try:
        runner, user_id, session_id = await setup_runner(university_agent)
    except Exception as e:
        print(f"\n[Runner Setup Error] {type(e).__name__}: {e}")
        return

    await interact_with_agent(runner, user_id, session_id)


if __name__ == "__main__":
    asyncio.run(main_async())