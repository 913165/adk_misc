from dotenv import load_dotenv
from google.adk.agents import Agent

load_dotenv()

root_agent = Agent(
    name="simple_memory_agent",
    model="gemini-3.1-flash-lite-preview",
    description="Simple assistant that remembers user preference during session.",
    instruction=(
        "You are a helpful assistant.\n"
        "Remember user preferences shared earlier in the conversation.\n"
        "Use that information to give better answers.\n"
        "If no previous context exists, give general answer."
    ),
)

print("Agent ready")