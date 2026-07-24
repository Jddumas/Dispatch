"""Mock external API tools and database-backed action tools for the action agent."""

from __future__ import annotations

from langchain_core.tools import tool

from app.tools import database


@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location.

    Use this for questions like "What's the weather in Paris?" or "Will it rain in Tokyo?".
    """
    return f"The weather in {location} is sunny with a chance of rain, 22 C."


@tool
def send_notification(recipient: str, message: str) -> str:
    """Send a notification or email to a recipient.

    Use this when the user asks to notify, email, or alert someone.
    This is a mock implementation; it only logs the request.
    """
    print(f"[MOCK NOTIFICATION to {recipient}] {message}")
    return f"Notification sent to {recipient}: {message}"


@tool
def create_support_ticket(
    customer_id: int,
    subject: str,
    description: str,
    order_id: int | None = None,
) -> str:
    """Create a support ticket in the database.

    Use this when the user asks to open, create, or file a support ticket.
    """
    query = """
        INSERT INTO support_tickets (customer_id, order_id, subject, description, status)
        VALUES (%s, %s, %s, %s, 'open')
    """
    rowcount = database.execute_query(
        query, (customer_id, order_id, subject, description), fetch=False
    )
    return f"Created {rowcount} support ticket(s) for customer {customer_id}."
