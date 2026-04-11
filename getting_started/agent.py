from google.adk.agents import LlmAgent
from google.adk.agents.llm_agent import Agent
import asyncio
from google.adk.runners import InMemoryRunner

root_agent =Agent(
    model='gemini-flash-latest',
    name='root_agent',
    description="Tells the current time in a specified city.",
    instruction="You are a helpful assistant that tells the current time in cities. Use your knowledge to get answer."
)

runner = InMemoryRunner(agent=root_agent, app_name="simple_agent_app")

async def main():
    """Run the agent with a simple prompt using run_debug."""
    try:
        response = await runner.run_debug("Hello! What is current time in london?")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
