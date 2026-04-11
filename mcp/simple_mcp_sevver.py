"""
Google ADK — Custom MCP Server + Agent Example
=================================================
This single file contains BOTH:
  1. A custom MCP server (inventory system with 3 tools)
  2. An ADK agent that connects to it via stdio

The agent spawns THIS SAME FILE as the MCP server process.

Install:
  pip install google-adk python-dotenv mcp fastmcp

Run:
  export GOOGLE_API_KEY="your-key"
  python custom_mcp_agent.py
"""

import sys
import asyncio


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PART 1 — Custom MCP Server (runs when called with --server flag)       ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def run_mcp_server():
    """A simple inventory MCP server built with FastMCP."""
    from fastmcp import FastMCP

    mcp = FastMCP("Inventory Server")

    # ── Fake product database ────────────────────────────────────────────
    PRODUCTS = {
        "SKU-101": {"name": "Wireless Mouse",      "price": 29.99, "stock": 150},
        "SKU-102": {"name": "Mechanical Keyboard",  "price": 79.99, "stock": 45},
        "SKU-103": {"name": "USB-C Monitor Cable",  "price": 14.99, "stock": 300},
        "SKU-104": {"name": "Laptop Stand",         "price": 49.99, "stock": 0},
    }

    ORDERS = []  # in-memory order list

    # ── Tool 1: search products ──────────────────────────────────────────
    @mcp.tool()
    def search_products(query: str) -> list[dict]:
        """Search the product catalog by name (case-insensitive partial match).

        Args:
            query: Search term to match against product names.
        """
        results = []
        for sku, info in PRODUCTS.items():
            if query.lower() in info["name"].lower():
                results.append({"sku": sku, **info})
        if not results:
            return [{"message": f"No products found matching '{query}'."}]
        return results

    # ── Tool 2: check stock ──────────────────────────────────────────────
    @mcp.tool()
    def check_stock(sku: str) -> dict:
        """Check the current stock level for a product by its SKU.

        Args:
            sku: The product SKU like "SKU-101".
        """
        product = PRODUCTS.get(sku.upper())
        if not product:
            return {"error": f"SKU '{sku}' not found. Try: SKU-101, SKU-102, SKU-103, SKU-104."}
        return {
            "sku": sku.upper(),
            "name": product["name"],
            "stock": product["stock"],
            "available": product["stock"] > 0,
        }

    # ── Tool 3: place an order ───────────────────────────────────────────
    @mcp.tool()
    def place_order(sku: str, quantity: int) -> dict:
        """Place an order for a product. Reduces stock if available.

        Args:
            sku: The product SKU to order.
            quantity: How many units to order.
        """
        product = PRODUCTS.get(sku.upper())
        if not product:
            return {"error": f"SKU '{sku}' not found."}
        if product["stock"] < quantity:
            return {"error": f"Not enough stock. Available: {product['stock']}, requested: {quantity}."}

        product["stock"] -= quantity
        order = {
            "order_id": f"ORD-{2001 + len(ORDERS)}",
            "sku": sku.upper(),
            "item": product["name"],
            "quantity": quantity,
            "total": round(product["price"] * quantity, 2),
            "status": "Confirmed",
        }
        ORDERS.append(order)
        return order

    # Start the server over stdio (so ADK can spawn and talk to it)
    mcp.run(transport="stdio")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PART 2 — ADK Agent (connects to our custom MCP server)                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

async def run_agent():
    """An ADK agent that uses the custom MCP inventory server."""
    import os
    from google.adk.agents import LlmAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.tools.mcp_tool import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
    from mcp import StdioServerParameters
    from google.genai import types
    from dotenv import load_dotenv

    load_dotenv()

    # Point to THIS SAME FILE with --server flag as the MCP server
    server_script = os.path.abspath(__file__)

    # ── Define the agent ─────────────────────────────────────────────────
    root_agent = LlmAgent(
        name="inventory_assistant",
        model="gemini-2.5-flash",
        description="An assistant that manages product inventory via MCP.",
        instruction=(
            "You are a helpful inventory assistant for an electronics store.\n"
            "Use your tools to:\n"
            "- Search for products when customers ask about items\n"
            "- Check stock availability\n"
            "- Place orders when requested\n"
            "Always confirm details with the customer before placing orders."
        ),
        tools=[
            McpToolset(
                connection_params=StdioConnectionParams(
                    server_params=StdioServerParameters(
                        command=sys.executable,       # current python interpreter
                        args=[server_script, "--server"],
                    ),
                ),
            )
        ],
    )

    # ── Run the conversation ─────────────────────────────────────────────
    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="app", session_service=session_service)
    await session_service.create_session(app_name="app", user_id="u1", session_id="s1")

    for question in [
        "What keyboards do you have?",
        "Check if SKU-102 is in stock",
        "Place an order for 2 units of SKU-102",
    ]:
        print(f"\n👤 {question}")
        msg = types.Content(role="user", parts=[types.Part(text=question)])
        async for event in runner.run_async(
            user_id="u1", session_id="s1", new_message=msg
        ):
            if event.is_final_response() and event.content and event.content.parts:
                print(f"🤖 {event.content.parts[0].text}")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Entry Point                                                            ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    if "--server" in sys.argv:
        # Launched as MCP server subprocess by the agent
        run_mcp_server()
    else:
        # Launched by the user — run the ADK agent
        asyncio.run(run_agent())
