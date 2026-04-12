from google.adk.agents.llm_agent import Agent

def track_order(order_id: str) -> dict:
    """Looks up the current status of a customer order.

    Args:
        order_id: The order ID like "ORD-1001".
    """
    orders = {
        "ORD-1001": {"item": "Wireless Headphones", "status": "Delivered", "date": "April 8, 2026"},
        "ORD-1002": {"item": "USB-C Hub", "status": "Shipped", "date": "April 14, 2026"},
        "ORD-1003": {"item": "Laptop Stand", "status": "Processing", "date": "April 18, 2026"},
        "ORD-1004": {"item": "Mechanical Keyboard", "status": "Shipped", "date": "April 13, 2026"},
        "ORD-1005": {"item": "Webcam HD Pro", "status": "Delivered", "date": "April 6, 2026"},
        "ORD-1006": {"item": "Monitor Arm", "status": "Out for Delivery", "date": "April 12, 2026"},
        "ORD-1007": {"item": "Noise Cancelling Earbuds", "status": "Processing", "date": "April 20, 2026"},
        "ORD-1008": {"item": "Phone Charger 65W", "status": "Cancelled", "date": "April 9, 2026"},
        "ORD-1009": {"item": "Desk Mat XXL", "status": "Shipped", "date": "April 15, 2026"},
        "ORD-1010": {"item": "LED Desk Lamp", "status": "Delivered", "date": "April 5, 2026"},
    }
    result = orders.get(order_id.upper())
    if result:
        return result
    return {"error": f"Order '{order_id}' not found. Valid IDs: ORD-1001 to ORD-1010."}


root_agent = Agent(
    model='gemini-flash-latest',
    name='root_agent',
    description="Tracks customer order status.",
    instruction="You are a helpful order tracking assistant. Use the track_order tool to look up order details. Share the item name, status, and expected date clearly.",
    tools=[track_order],
)
