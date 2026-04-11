"""
Google ADK — Simple MCP Connection Example
=============================================
An agent that connects to an MCP server to get tools,
instead of defining tools as local Python functions.

Two patterns shown:
  1. Stdio  → local MCP server (filesystem, sqlite, etc.)
  2. SSE    → remote MCP server over HTTP

Install:
  pip install google-adk python-dotenv mcp
  npm install -g @modelcontextprotocol/server-filesystem   # for the stdio example

Run:
  python simple_agent_mcp.py
"""

import os
import asyncio
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    SseConnectionParams,
)
from mcp import StdioServerParameters
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


# ── Pick the folder the MCP filesystem server can access ─────────────────────
TARGET_FOLDER = os.path.expanduser("~/mcp_demo_files")
os.makedirs(TARGET_FOLDER, exist_ok=True)

# Create a sample file so there's something to read
sample_file = os.path.join(TARGET_FOLDER, "hello.txt")
if not os.path.exists(sample_file):
    with open(sample_file, "w") as f:
        f.write("Hello from MCP! This file was created for the demo.\n")


# ── Pattern 1: Stdio — local MCP server (filesystem) ────────────────────────
#    The agent spawns the MCP server as a child process and talks over stdin/out.

root_agent = LlmAgent(
    name="file_assistant",
    model="gemini-2.5-flash",
    description="An assistant that can read and list files via MCP.",
    instruction=(
        "You are a helpful file assistant. "
        "Use your tools to list directories and read files when the user asks."
    ),
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=[
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        os.path.abspath(TARGET_FOLDER),
                    ],
                ),
            ),
            # Optional: only expose specific tools from the server
            # tool_filter=["read_file", "list_directory"],
        )
    ],
)


# ── Pattern 2 (alternative): SSE — remote MCP server ────────────────────────
#    Uncomment below to connect to an MCP server running over HTTP/SSE instead.
#
# root_agent = LlmAgent(
#     name="remote_assistant",
#     model="gemini-2.5-flash",
#     description="An assistant connected to a remote MCP server.",
#     instruction="You are a helpful assistant. Use your tools to answer questions.",
#     tools=[
#         McpToolset(
#             connection_params=SseConnectionParams(
#                 url="http://localhost:8001/sse",    # your MCP server URL
#                 headers={"Authorization": "Bearer YOUR_TOKEN"},  # optional auth
#             ),
#         )
#     ],
# )


# ── Run it ───────────────────────────────────────────────────────────────────
async def main():
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="app", session_service=session_service)
    await session_service.create_session(app_name="app", user_id="u1", session_id="s1")

    for question in [
        f"List the files in {TARGET_FOLDER}",
        f"Read the file hello.txt",
    ]:
        print(f"\n👤 {question}")
        msg = types.Content(role="user", parts=[types.Part(text=question)])
        async for event in runner.run_async(
            user_id="u1", session_id="s1", new_message=msg
        ):
            if event.is_final_response() and event.content.parts:
                print(f"🤖 {event.content.parts[0].text}")


if __name__ == "__main__":
    asyncio.run(main())
