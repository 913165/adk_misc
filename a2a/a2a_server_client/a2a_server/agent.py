"""
Remote Greeting Agent - A2A Server Agent

This agent is exposed via the A2A protocol so other agents can
discover and communicate with it over the network.

It provides two tools:
  1. greet_user  - generates a personalized greeting
  2. get_weather - returns a mock weather report for a city

Run this file directly with uvicorn (see below) or via the helper script.
"""

import random
from datetime import datetime

from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

def greet_user(name: str, language: str = "english") -> str:
    """Generate a personalized greeting for the user.

    Args:
        name: The name of the person to greet.
        language: The language for the greeting (english, spanish, french,
                  hindi, japanese). Defaults to english.

    Returns:
        A personalized greeting string.
    """
    greetings = {
        "english": [
            f"Hello, {name}! Welcome aboard!",
            f"Hi there, {name}! Great to see you!",
            f"Hey {name}! How's it going?",
        ],
        "spanish": [
            f"¡Hola, {name}! ¡Bienvenido!",
            f"¡Buenos días, {name}!",
        ],
        "french": [
            f"Bonjour, {name}! Bienvenue!",
            f"Salut, {name}! Comment ça va?",
        ],
        "hindi": [
            f"नमस्ते, {name}! आपका स्वागत है!",
            f"प्रणाम, {name}!",
        ],
        "japanese": [
            f"こんにちは、{name}さん！ようこそ！",
            f"やあ、{name}さん！",
        ],
    }
    lang = language.lower()
    options = greetings.get(lang, greetings["english"])
    return random.choice(options)

def get_weather(city: str) -> str:
    """Return a simulated weather report for the given city.

    Args:
        city: The name of the city to get the weather for.

    Returns:
        A string containing the simulated weather information.
    """
    conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Rainy", "Thunderstorms", "Snowy", "Windy", "Foggy"]
    condition = random.choice(conditions)
    temp_c = random.randint(5, 42)
    humidity = random.randint(30, 95)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    return (
        f"Weather report for {city} ({now}):\n"
        f"  Condition : {condition}\n"
        f"  Temperature: {temp_c}°C / {round(temp_c * 9/5 + 32)}°F\n"
        f"  Humidity  : {humidity}%"
    )

def get_time(timezone: str = "UTC") -> str:
    """Return the current date and time.

    Args:
        timezone: A timezone label (for display only; always returns server time).

    Returns:
        A string with the current date and time.
    """
    now = datetime.now().strftime("%A, %B %d, %Y at %H:%M:%S")
    return f"Current time ({timezone}): {now}"

root_agent = Agent(
    model="gemini-flash-latest",
    name="greeting_agent",
    description=(
        "A friendly greeting agent that can greet users in multiple languages, "
        "provide weather reports for any city, and tell the current time."
    ),
    instruction="""You are a friendly and helpful greeting agent.
    You have three capabilities:
    1. Greet users by name in multiple languages (English, Spanish, French, Hindi, Japanese).
       Always call the greet_user tool when asked to greet someone.
    2. Provide weather information for any city.
       Always call the get_weather tool when asked about weather.
    3. Tell the current date and time.
       Always call the get_time tool when asked about the time or date.

    Be warm, friendly, and conversational in your responses.
    When greeting, feel free to add a short friendly comment after the greeting.
    """,
    tools=[greet_user, get_weather, get_time],
)

# ---------------------------------------------------------------------------
# A2A exposure — wraps the agent into an A2A-compatible Starlette app
# ---------------------------------------------------------------------------

a2a_app = to_a2a(root_agent, port=8001)

# ---------------------------------------------------------------------------
# Direct-run entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    print("Starting A2A Greeting Agent server on http://localhost:8001 ...")
    print("Agent card available at: http://localhost:8001/.well-known/agent-card.json")
    uvicorn.run(a2a_app, host="0.0.0.0", port=8001)



