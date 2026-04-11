"""
=============================================================
 Simple A2A Server Demo — Google ADK + a2a-sdk
=============================================================
 Architecture (bottom → top):
   1. Agent      – a Gemini-powered LLM agent (google-adk)
   2. Runner     – ties the agent to a session store
   3. Executor   – wraps the runner in the A2A protocol
   4. Handler    – handles A2A JSON-RPC requests
   5. App        – Starlette web app served by uvicorn
=============================================================
"""

import uvicorn
from dotenv import load_dotenv

# ── Load API key and other env vars from .env ──────────────
load_dotenv()

# ── 1. Define the Agent ────────────────────────────────────
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

greeting_agent = Agent(
    name="greeting_agent",
    model="gemini-2.0-flash",          # swap for any Gemini model
    instruction=(
        "You are a friendly assistant called DemoBot. "
        "Greet the user warmly and answer any questions they have. "
        "Keep your replies short and encouraging."
    ),
)

# ── 2. Create the Runner ───────────────────────────────────
runner = Runner(
    app_name="a2a_demo",
    agent=greeting_agent,
    session_service=InMemorySessionService(),
)

# ── 3. Wrap with the A2A Executor ──────────────────────────
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor

executor = A2aAgentExecutor(runner=runner)

# ── 4. Build the A2A Request Handler ──────────────────────
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

handler = DefaultRequestHandler(
    agent_executor=executor,
    task_store=InMemoryTaskStore(),
)

# ── 5. Describe the Agent (Agent Card) ────────────────────
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
)

agent_card = AgentCard(
    name="DemoBot",
    description="A simple greeting agent — A2A demo for students.",
    url="http://localhost:8000/",
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=False),
    skills=[
        AgentSkill(
            id="greet",
            name="Greeting",
            description="Greets the user and answers general questions.",
            tags=["greeting", "general"],
        )
    ],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
)

# ── 6. Create the Starlette App ────────────────────────────
from a2a.server.apps import A2AStarletteApplication

a2a_app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=handler,
)

app = a2a_app.build()  # returns a Starlette application

# ── Entry point ────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀  A2A Demo Server starting on http://localhost:8000")
    print("📄  Agent card: http://localhost:8000/.well-known/agent.json")
    uvicorn.run("a2a_server:app", host="0.0.0.0", port=8000, reload=False)
