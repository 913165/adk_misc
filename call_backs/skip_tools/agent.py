from google.adk.agents import LlmAgent
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.genai import types
from typing import Optional


# ── 1. Mock book inventory ──────────────────────────────────────────
BOOK_INVENTORY = {
    "clean code": {
        "title"      : "Clean Code",
        "author"     : "Robert C. Martin",
        "price"      : 599,
        "stock"      : 0,          # ← OUT OF STOCK
        "available"  : False,
        "category"   : "Software Engineering"
    },
    "the pragmatic programmer": {
        "title"      : "The Pragmatic Programmer",
        "author"     : "Andrew Hunt & David Thomas",
        "price"      : 699,
        "stock"      : 15,
        "available"  : True,
        "category"   : "Software Engineering"
    },
    "design patterns": {
        "title"      : "Design Patterns",
        "author"     : "Gang of Four",
        "price"      : 799,
        "stock"      : 8,
        "available"  : True,
        "category"   : "Software Engineering"
    },
    "atomic habits": {
        "title"      : "Atomic Habits",
        "author"     : "James Clear",
        "price"      : 499,
        "stock"      : 0,          # ← OUT OF STOCK
        "available"  : False,
        "category"   : "Self Help"
    },
    "python crash course": {
        "title"      : "Python Crash Course",
        "author"     : "Eric Matthes",
        "price"      : 549,
        "stock"      : 22,
        "available"  : True,
        "category"   : "Programming"
    },
}


# ── 2. Define the real order tool ───────────────────────────────────
def place_book_order(book_name: str, quantity: int = 1) -> dict:
    """
    Places an order for a book.
    In a real app this would hit an order management API,
    deduct stock, generate an order ID, and send a confirmation.

    Args:
        book_name : Name of the book to order
        quantity  : Number of copies to order (default 1)

    Returns:
        dict with order confirmation details
    """
    print(f"[Tool] place_book_order() ACTUALLY CALLED")
    print(f"[Tool] Book: '{book_name}', Quantity: {quantity}")
    print(f"[Tool] Processing order... hitting order management API...")

    # Simulate real order placement
    import uuid
    return {
        "order_id"   : str(uuid.uuid4())[:8].upper(),
        "book_name"  : book_name,
        "quantity"   : quantity,
        "status"     : "CONFIRMED",
        "message"    : f"Order placed successfully for {quantity} copy/copies of '{book_name}'.",
        "source"     : "REAL ORDER API"
    }


# ── 3. Define the before_tool callback ─────────────────────────────
def check_availability_before_order(
    tool: BaseTool,
    tool_args: dict,
    tool_context: ToolContext
) -> Optional[dict]:
    """
    A before_tool callback that intercepts place_book_order.
    Before the order is placed, it checks the book inventory:

    - If the book is OUT OF STOCK  → skip the tool, return blocked message
    - If the book is NOT FOUND     → skip the tool, return not found message
    - If the book is IN STOCK      → allow the real tool to execute

    Args:
        tool         : The tool about to be executed
        tool_args    : Arguments the LLM passed to the tool
        tool_context : Context with session state and agent info

    Returns:
        dict  → tool execution SKIPPED (out of stock or not found)
        None  → tool executes normally (book is available)
    """

    print(f"\n[before_tool] Tool requested : '{tool.name}'")
    print(f"[before_tool] Tool args      : {tool_args}")

    # ── Only intercept place_book_order ────────────────────────────
    if tool.name != "place_book_order":
        print(f"[before_tool] Not our tool — passing through.")
        return None

    # ── Get book name from tool args ───────────────────────────────
    book_name = tool_args.get("book_name", "").lower().strip()
    quantity  = tool_args.get("quantity", 1)

    print(f"[before_tool] Checking inventory for: '{book_name}'")

    # ── Check if book exists in inventory ──────────────────────────
    if book_name not in BOOK_INVENTORY:
        print(f"[before_tool] ❌ NOT FOUND — '{book_name}' not in inventory.")
        return {
            "order_id"  : None,
            "book_name" : book_name,
            "quantity"  : quantity,
            "status"    : "NOT_FOUND",
            "message"   : (
                f"Sorry, '{book_name}' was not found in our catalog. "
                f"Please check the book name and try again."
            ),
            "source"    : "INVENTORY CHECK"
        }

    book = BOOK_INVENTORY[book_name]

    # ── Check if book is out of stock ──────────────────────────────
    if not book["available"] or book["stock"] == 0:
        print(f"[before_tool] 🚫 OUT OF STOCK — skipping order for '{book_name}'.")
        return {
            "order_id"  : None,
            "book_name" : book["title"],
            "author"    : book["author"],
            "quantity"  : quantity,
            "status"    : "OUT_OF_STOCK",
            "message"   : (
                f"Sorry, '{book['title']}' by {book['author']} "
                f"is currently out of stock. "
                f"Please try again later or choose a different book."
            ),
            "source"    : "INVENTORY CHECK"
        }

    # ── Book is available — allow real tool to run ─────────────────
    print(f"[before_tool] ✅ IN STOCK — '{book['title']}' "
          f"has {book['stock']} copies. Proceeding with order.")
    return None  # ← real tool executes


# ── 4. root_agent ───────────────────────────────────────────────────
root_agent = LlmAgent(
    name="BookOrderAgent",
    model="gemini-3.1-pro-preview",
    instruction=(
        "You are a helpful bookstore assistant. "
        "You help customers order books. "
        "Use the place_book_order tool when a customer wants to order a book. "
        "Always share the order status and any relevant details with the customer."
    ),
    tools=[place_book_order],
    before_tool_callback=check_availability_before_order
)