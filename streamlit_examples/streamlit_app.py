import os
import asyncio
import shutil
import streamlit as st
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters
from google.genai import types

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="University Management Agent",
    page_icon="🎓",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main { background-color: #0d1117; }
    .stChatMessage { background-color: #161b22; border-radius: 10px; }
    .stTextInput > div > div > input { background-color: #161b22; color: #e6edf3; }
    .sidebar-info { font-size: 12px; color: #8b949e; line-height: 1.6; }
    h1 { font-weight: 300 !important; letter-spacing: -1px; }
</style>
""", unsafe_allow_html=True)

# ── Environment setup ─────────────────────────────────────────────────────────

def configure_environment():
    os.environ["GOOGLE_API_KEY"] = os.getenv(
        "GOOGLE_API_KEY", "your-key-here"
    )
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

    DB_FOLDER   = os.path.abspath("mcp-university-project/db")
    DB_FILENAME = "university.db"
    DB_PATH     = os.path.join(DB_FOLDER, DB_FILENAME)

    if not os.path.isdir(DB_FOLDER):
        raise FileNotFoundError(
            f"Database folder not found: {DB_FOLDER}\n"
            f"Make sure 'mcp-university-project/db' exists in: {os.getcwd()}"
        )
    if not os.path.isfile(DB_PATH):
        raise FileNotFoundError(
            f"Database file not found: {DB_PATH}\n"
            f"Run setup_university_db.py first."
        )
    if shutil.which("uv") is None:
        raise FileNotFoundError(
            "'uv' not found on PATH.\n"
            "Install: https://docs.astral.sh/uv/getting-started/installation/"
        )
    return DB_FOLDER, DB_FILENAME


# ── Agent creation ────────────────────────────────────────────────────────────

def create_university_agent(MCP_SERVER_PATH, DB_PATH):
    if not os.path.isdir(MCP_SERVER_PATH):
        raise FileNotFoundError(
            f"MCP server directory not found: {MCP_SERVER_PATH}"
        )

    return Agent(
        name="University_SQLite_Agent",
        model="gemini-flash-latest",
        description=(
            "Intelligent university management agent with direct access to a SQLite database."
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
              - Database path: {DB_PATH}
        """,
    )


# ── Async agent call ──────────────────────────────────────────────────────────

async def call_agent_async(query: str, runner, user_id: str, session_id: str) -> str:
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
        final_response = f"❌ MCP Connection Error: {e}"
    except ExceptionGroup as eg:
        msgs = "\n".join(f"  - {type(x).__name__}: {x}" for x in eg.exceptions)
        final_response = f"❌ MCP Error:\n{msgs}"
    except Exception as e:
        final_response = f"❌ Unexpected Error — {type(e).__name__}: {e}"

    return final_response


def run_agent_query(query: str) -> str:
    """Synchronous wrapper so Streamlit can call the async agent."""
    runner      = st.session_state.runner
    user_id     = st.session_state.user_id
    session_id  = st.session_state.session_id
    return asyncio.run(call_agent_async(query, runner, user_id, session_id))


# ── Session state init ────────────────────────────────────────────────────────

async def _init_runner(agent):
    session_service = InMemorySessionService()
    app_name   = "university_app"
    user_id    = "admin_1"
    session_id = "session_001"
    await session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    runner = Runner(agent=agent, app_name=app_name, session_service=session_service)
    return runner, user_id, session_id


@st.cache_resource(show_spinner="Setting up agent...")
def init_agent():
    """Initialise agent + runner once and cache across reruns."""
    DB_FOLDER, DB_FILENAME = configure_environment()
    DB_PATH        = os.path.join(DB_FOLDER, DB_FILENAME)
    MCP_SERVER_PATH = os.path.abspath("mcp-university-project/sqlite")
    agent  = create_university_agent(MCP_SERVER_PATH, DB_PATH)
    runner, user_id, session_id = asyncio.run(_init_runner(agent))
    return runner, user_id, session_id


# ── Main UI ───────────────────────────────────────────────────────────────────

# Sidebar
with st.sidebar:
    st.markdown("## 🎓 University Agent")
    st.markdown("---")

    st.markdown("**Database Tables**")
    for table in ["students", "professors", "courses", "enrollments", "assignments", "submissions"]:
        st.markdown(f"- `{table}`")

    st.markdown("---")
    st.markdown("**Sample Prompts**")
    sample_prompts = [
        "Show top 10 students by GPA",
        "List all Computer Science courses",
        "Which students have GPA below 2.0?",
        "Show overdue assignments",
        "Which professor teaches most courses?",
        "Give me a full university summary",
    ]
    for prompt in sample_prompts:
        if st.button(prompt, use_container_width=True, key=prompt):
            st.session_state.pending_prompt = prompt

    st.markdown("---")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown('<p class="sidebar-info">Powered by Google ADK + SQLite MCP</p>',
                unsafe_allow_html=True)

# Header
st.markdown("# University Management Agent")
st.markdown("Ask questions about students, professors, courses, assignments and more.")
st.markdown("---")

# Initialise agent (cached)
try:
    if "runner" not in st.session_state:
        runner, user_id, session_id = init_agent()
        st.session_state.runner     = runner
        st.session_state.user_id    = user_id
        st.session_state.session_id = session_id
except FileNotFoundError as e:
    st.error(f"**Setup Error:** {e}")
    st.stop()
except Exception as e:
    st.error(f"**Agent Initialisation Error:** {type(e).__name__}: {e}")
    st.stop()

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render existing chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle sidebar prompt button click
if "pending_prompt" in st.session_state:
    prompt = st.session_state.pop("pending_prompt")
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Querying database..."):
            response = run_agent_query(prompt)
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()

# Chat input
if user_input := st.chat_input("Ask anything about the university..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Querying database..."):
            response = run_agent_query(user_input)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
