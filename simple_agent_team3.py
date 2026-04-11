"""
Google ADK — Simple Agent Team Example
========================================
E-commerce customer support team:
  - order_agent   → tracks order status
  - returns_agent → handles return/refund requests

Install:  pip install google-adk python-dotenv
Run:      python simple_agent_team.py
"""

import asyncio
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from dotenv import load_dotenv
load_dotenv()


# ── Tool 1: look up order status ─────────────────────────────────────────────
def track_order(order_id: str) -> dict:
    """Looks up the current status of a customer order.

    Args:
        order_id: The order ID like "ORD-1001".
    """
    orders = {
        "ORD-1001": {"status": "Shipped", "item": "Wireless Headphones", "delivery": "April 14, 2026"},
        "ORD-1002": {"status": "Processing", "item": "USB-C Hub", "delivery": "April 18, 2026"},
        "ORD-1003": {"status": "Delivered", "item": "Laptop Stand", "delivery": "April 9, 2026"},
    }
    result = orders.get(order_id.upper())
    if result:
        return result
    return {"error": f"Order '{order_id}' not found. Try: ORD-1001, ORD-1002, ORD-1003."}


# ── Tool 2: initiate a return ────────────────────────────────────────────────
def initiate_return(order_id: str, reason: str) -> dict:
    """Initiates a return request for a delivered order.

    Args:
        order_id: The order ID to return.
        reason: Why the customer wants to return it.
    """
    delivered = ["ORD-1003"]
    if order_id.upper() in delivered:
        return {
            "return_id": "RET-5001",
            "status": "Return approved",
            "refund_estimate": "3-5 business days",
            "pickup_date": "April 15, 2026",
        }
    return {"error": f"Order '{order_id}' is not eligible for return. Only delivered orders can be returned."}


# ── Sub-agent 1: order tracking ──────────────────────────────────────────────
order_agent = Agent(
    name="order_agent",
    model="gemini-2.5-flash",
    description="Tracks order status when customers ask where their order is.",
    instruction="Use the track_order tool to look up order details. Share status, item, and delivery date.",
    tools=[track_order],
)

# ── Sub-agent 2: returns and refunds ─────────────────────────────────────────
returns_agent = Agent(
    name="returns_agent",
    model="gemini-2.5-flash",
    description="Handles return and refund requests from customers.",
    instruction="Use the initiate_return tool to process returns. Confirm the return ID and refund timeline.",
    tools=[initiate_return],
)

# ── Root agent: customer support coordinator ─────────────────────────────────
root_agent = Agent(
    name="support_coordinator",
    model="gemini-2.5-flash",
    description="Routes customer queries to the right support agent.",
    instruction=(
        "You are a customer support coordinator. Route requests:\n"
        "- Order status or tracking → order_agent\n"
        "- Returns or refunds → returns_agent"
    ),
    sub_agents=[order_agent, returns_agent],
)


# ── Run it ───────────────────────────────────────────────────────────────────
async def main():
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="app", session_service=session_service)
    await session_service.create_session(app_name="app", user_id="u1", session_id="s1")

    for question in [
        "Where is my order ORD-1001?",
        "I want to return order ORD-1003, the stand is wobbly",
    ]:
        print(f"\n👤 {question}")
        msg = types.Content(role="user", parts=[types.Part(text=question)])
        async for event in runner.run_async(user_id="u1", session_id="s1", new_message=msg):
            if event.is_final_response() and event.content.parts:
                print(f"🤖 {event.content.parts[0].text}")

if __name__ == "__main__":
    asyncio.run(main())