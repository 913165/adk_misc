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


def cancel_order(order_id: str, reason: str) -> dict:
    """Cancels a customer order if it hasn't been delivered yet.

    Args:
        order_id: The order ID like "ORD-1001".
        reason: Why the customer wants to cancel.
    """
    non_cancellable = {"Delivered", "Cancelled", "Out for Delivery"}
    orders = {
        "ORD-1001": "Delivered",
        "ORD-1002": "Shipped",
        "ORD-1003": "Processing",
        "ORD-1004": "Shipped",
        "ORD-1005": "Delivered",
        "ORD-1006": "Out for Delivery",
        "ORD-1007": "Processing",
        "ORD-1008": "Cancelled",
        "ORD-1009": "Shipped",
        "ORD-1010": "Delivered",
    }
    status = orders.get(order_id.upper())
    if not status:
        return {"error": f"Order '{order_id}' not found."}
    if status in non_cancellable:
        return {"error": f"Cannot cancel — order is already '{status}'."}
    return {
        "status": "Cancelled",
        "message": f"Order {order_id.upper()} has been cancelled. Reason: {reason}. Refund will be processed in 3-5 business days.",
    }


root_agent = Agent(
    model='gemini-flash-latest',
    name='root_agent',
    description="Tracks and cancels customer orders.",
    instruction=(
        "You are a helpful order support assistant. "
        "Use track_order to look up order details. "
        "Use cancel_order when a customer wants to cancel. "
        "Always check the order status before confirming a cancellation."
    ),
    tools=[track_order, cancel_order],
)
