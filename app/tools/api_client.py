"""Mock external API tools and database-backed action tools for the action agent."""

from __future__ import annotations

import logging

import httpx
from langchain_core.tools import tool

from app.config import OPENWEATHER_API_KEY
from app.tools import database

logger = logging.getLogger(__name__)

_ALLOWED_TICKET_STATUSES = {"open", "in_progress", "resolved", "closed"}


@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location.

    Use this for questions like "What's the weather in Paris?" or "Will it rain in Tokyo?".
    """
    if OPENWEATHER_API_KEY:
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            resp = httpx.get(
                url,
                params={"q": location, "appid": OPENWEATHER_API_KEY, "units": "imperial"},
                timeout=5,
            )
            resp.raise_for_status()
            data = resp.json()
            description = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind = data["wind"]["speed"]
            return (
                f"Weather in {location}: {description}, {temp:.1f}°F, "
                f"humidity {humidity}%, wind {wind} mph."
            )
        except Exception:
            logger.warning("OpenWeatherMap request failed for %s; using mock", location)

    return f"The weather in {location} is sunny with a chance of rain, 22°C."


@tool
def send_notification(recipient: str, message: str) -> str:
    """Send a notification or email to a recipient.

    Use this when the user asks to notify, email, or alert someone.
    This is a mock implementation; it only logs the request.
    """
    logger.info("[MOCK NOTIFICATION to %s] %s", recipient, message)
    return f"Notification sent to {recipient}: {message}"


@tool
def create_support_ticket(
    customer_id: int | str,
    subject: str,
    description: str,
    order_id: int | str | None = None,
) -> str:
    """Create a support ticket in the database.

    Use this when the user asks to open, create, or file a support ticket.
    """
    customer_id = int(customer_id)
    order_id = int(order_id) if order_id is not None else None
    query = """
        INSERT INTO support_tickets (customer_id, order_id, subject, description, status)
        VALUES (%s, %s, %s, %s, 'open')
    """
    rowcount = database.execute_query(
        query, (customer_id, order_id, subject, description), fetch=False
    )
    return f"Created {rowcount} support ticket(s) for customer {customer_id}."


@tool
def lookup_order(order_id: int | str) -> str:
    """Look up details for a specific order by ID: status, product, total, payment method, carrier."""
    order_id = int(order_id)
    rows = database.execute_query_safe(
        """
        SELECT o.id, o.product_name, o.status, o.total, o.created_at,
               p.method AS payment_method, p.status AS payment_status,
               s.carrier, s.status AS shipping_status, s.tracking_number
        FROM orders o
        LEFT JOIN payments p ON p.order_id = o.id
        LEFT JOIN shipping s ON s.order_id = o.id
        WHERE o.id = %s
        """,
        (order_id,),
    )
    if not rows:
        return f"No order found with ID {order_id}."
    r = rows[0]
    parts = [
        f"Order #{r['id']}: {r['product_name']}",
        f"Status: {r['status']}, Total: ${r['total']:.2f}",
        f"Placed: {r['created_at'].strftime('%Y-%m-%d') if r['created_at'] else 'unknown'}",
    ]
    if r.get("payment_method"):
        parts.append(f"Payment: {r['payment_method']} ({r['payment_status']})")
    if r.get("carrier"):
        parts.append(f"Shipping: {r['carrier']} — {r['shipping_status']}, tracking {r['tracking_number']}")
    return "\n".join(parts)


@tool
def get_customer_by_email(email: str) -> str:
    """Find a customer by email address. Returns name, loyalty tier, account status, open ticket count."""
    rows = database.execute_query_safe(
        """
        SELECT c.id, c.name, c.email, c.loyalty_tier, c.account_status,
               COUNT(t.id) FILTER (WHERE t.status = 'open') AS open_tickets
        FROM customers c
        LEFT JOIN support_tickets t ON t.customer_id = c.id
        WHERE LOWER(c.email) = LOWER(%s)
        GROUP BY c.id
        """,
        (email,),
    )
    if not rows:
        return f"No customer found with email {email}."
    r = rows[0]
    return (
        f"Customer #{r['id']}: {r['name']} ({r['email']})\n"
        f"Loyalty tier: {r['loyalty_tier']}, Status: {r['account_status']}\n"
        f"Open tickets: {r['open_tickets']}"
    )


@tool
def update_ticket_status(ticket_id: int | str, new_status: str) -> str:
    """Update the status of a support ticket. Allowed statuses: open, in_progress, resolved, closed."""
    ticket_id = int(ticket_id)
    if new_status not in _ALLOWED_TICKET_STATUSES:
        return (
            f"Invalid status '{new_status}'. Allowed values: "
            + ", ".join(sorted(_ALLOWED_TICKET_STATUSES))
        )
    rowcount = database.execute_query(
        "UPDATE support_tickets SET status = %s WHERE id = %s",
        (new_status, ticket_id),
        fetch=False,
    )
    if not rowcount:
        return f"No ticket found with ID {ticket_id}."
    return f"Ticket #{ticket_id} status updated to '{new_status}'."


@tool
def close_ticket(ticket_id: int | str, resolution_note: str) -> str:
    """Close a support ticket and record a resolution note on the customer's account."""
    ticket_id = int(ticket_id)
    rowcount = database.execute_query(
        "UPDATE support_tickets SET status = 'closed' WHERE id = %s",
        (ticket_id,),
        fetch=False,
    )
    if not rowcount:
        return f"No ticket found with ID {ticket_id}."

    database.execute_query(
        """
        INSERT INTO account_notes (customer_id, note)
        SELECT customer_id, %s FROM support_tickets WHERE id = %s
        """,
        (resolution_note, ticket_id),
        fetch=False,
    )
    return f"Ticket #{ticket_id} closed. Resolution note recorded."
