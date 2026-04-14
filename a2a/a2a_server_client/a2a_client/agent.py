"""
A2A Client (Root Agent)

This agent acts as the orchestrator / consumer that connects to one or more
remote A2A agents.  It discovers the remote Greeting Agent via its well-known
agent-card URL and delegates greeting, weather, and time queries to it.

It also has a local calculator tool to demonstrate mixing local and remote
capabilities.

Usage:
    # Make sure the remote A2A server is already running on port 8001, then:
    adk web .          # opens the ADK dev UI at http://localhost:8000
    # — or —
    python agent.py    # runs a simple CLI loop (see bottom of file)
"""

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import (
    AGENT_CARD_WELL_KNOWN_PATH,
    RemoteA2aAgent,
)


# ---------------------------------------------------------------------------
# Local tool
# ---------------------------------------------------------------------------

def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the result.

    Args:
        expression: A mathematical expression to evaluate.
                    Supports +, -, *, /, **, (), and common math.

    Returns:
        The result of the evaluation as a string.
    """
    try:
        # Allow only safe math operations
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return f"Error: expression contains unsupported characters. Only numbers and +-**/() are allowed."
        result = eval(expression)  # safe because we validated chars above
        return f"{expression} = {result}"
    except Exception as e:
        return f"Error evaluating '{expression}': {e}"


# ---------------------------------------------------------------------------
# Remote A2A agent proxy — connects to the Greeting Agent server
# ---------------------------------------------------------------------------

REMOTE_AGENT_URL = "http://localhost:8001"

greeting_agent = RemoteA2aAgent(
    name="greeting_agent",
    description=(
        "A remote greeting agent that can greet users in multiple languages, "
        "provide weather reports for any city, and tell the current time. "
        "Delegate to this agent whenever the user wants a greeting, weather, or time info."
    ),
    agent_card=f"{REMOTE_AGENT_URL}/{AGENT_CARD_WELL_KNOWN_PATH}",
)


# ---------------------------------------------------------------------------
# Root (orchestrator) agent
# ---------------------------------------------------------------------------

root_agent = Agent(
    model="gemini-flash-latest",
    name="orchestrator_agent",
    description="Root orchestrator that coordinates local tools and remote A2A agents.",
    instruction="""You are an intelligent orchestrator agent.

    You have access to:
    1. **greeting_agent** (remote, via A2A) — can greet users in multiple
       languages, provide weather reports, and tell the time.
       Delegate greeting / weather / time requests to this agent.

    2. **calculate** (local tool) — evaluates math expressions.
       Use this for any calculation or math question.

    Routing rules:
    - If the user asks to be greeted or says hello → delegate to greeting_agent.
    - If the user asks about weather in a city   → delegate to greeting_agent.
    - If the user asks for the time or date       → delegate to greeting_agent.
    - If the user asks a math question            → use the calculate tool.
    - For anything else, respond helpfully using your own knowledge.
    """,
    tools=[calculate],
    sub_agents=[greeting_agent],
)
