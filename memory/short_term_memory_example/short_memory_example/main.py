import asyncio

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, Session
from google.genai import types
import  google.adk.memory

try:
    from . import agent as agent_module
except ImportError:
    import agent as agent_module

assistant_agent = agent_module.root_agent

########################################################
# helper method
########################################################

async def run_agent_query(
    agent: Agent,
    query: str,
    session: Session,
    user_id: str,
    session_service: InMemorySessionService,
):
    print(f"\n... running query in session: {session.id}")
    print(f"... user: {query}")

    runner = Runner(
        agent=agent,
        app_name=agent.name,
        session_service=session_service
    )

    final_response = ""

    async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=types.Content(
                parts=[types.Part(text=query)],
                role="user"
            ),
    ):
        if event.is_final_response():
            final_response = event.content.parts[0].text

    print("... agent:", final_response)
    print("------------------------------------------")
    return final_response

########################################################
# SCENARIO 1
# memory remembers
########################################################

async def scenario_memory_remembers(session_service, user_id):
    print("\n==============================")
    print("SCENARIO 1 ... MEMORY REMEMBERS")
    print("==============================")

    session = await session_service.create_session(
        app_name=assistant_agent.name,
        user_id=user_id,
    )

    query1 = "I want to order pizza. I like spicy food."
    query2 = "Which pizza should I order?"

    await run_agent_query(
        assistant_agent,
        query1,
        session,
        user_id,
        session_service
    )

    print("\n... asking followup question ...")
    await run_agent_query(
        assistant_agent,
        query2,
        session,
        user_id,
        session_service
    )

########################################################
# SCENARIO 2
# memory lost
########################################################

async def scenario_memory_lost(session_service, user_id):

    print("\n==============================")
    print("SCENARIO 2 ... MEMORY LOST")
    print("==============================")

    session1 = await session_service.create_session(
        app_name=assistant_agent.name,
        user_id=user_id,
    )

    query1 = "I want to order pizza. I like spicy food."

    await run_agent_query(
        assistant_agent,
        query1,
        session1,
        user_id,
        session_service
    )

    print("\n... creating new session (memory lost) ...")

    session2 = await session_service.create_session(
        app_name=assistant_agent.name,
        user_id=user_id,
    )

    query2 = "Which pizza should I order?"

    await run_agent_query(
        assistant_agent,
        query2,
        session2,
        user_id,
        session_service
    )


async def main():
    session_service = InMemorySessionService()
    user_id = "student_demo_user"
    await scenario_memory_remembers(session_service, user_id)
    await scenario_memory_lost(session_service, user_id)
    ########################################################


if __name__ == "__main__":
    asyncio.run(main())