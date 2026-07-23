"""
Week 4: LangGraph Fundamentals

A simple state-machine graph that classifies a user's question and routes it to
one of four specialist nodes:
- sql     -> run a safe, parameterized query against PostgreSQL
- rag     -> answer from the ChromaDB knowledge base
- action  -> call a mock tool (get_weather)
- general -> answer directly with the LLM
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph, add_messages
from typing_extensions import Annotated, TypedDict

from app.tools import database, retriever


class State(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str
    result: str


llm = ChatOllama(model="llama3.1", temperature=0.0)
ALLOWED_INTENTS = {"sql", "rag", "action", "general"}


def _last_human_message(state: State) -> str:
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def classify_intent(state: State) -> dict:
    """Classify the user's last message into sql, rag, action, or general."""
    user_text = _last_human_message(state)
    prompt = (
        "You are an intent classifier for a support assistant. "
        "Classify the user's message into exactly one of these categories:\n"
        "- sql: questions about orders, customers, tickets, or anything stored in the database\n"
        "- rag: questions about company policies, product specs, or troubleshooting\n"
        "- action: requests that require calling a tool such as checking the weather\n"
        "- general: anything else, including greetings or small talk\n\n"
        "Respond with exactly one lowercase word. Do not explain.\n"
        "Allowed responses: sql, rag, action, general\n\n"
        f"User message: {user_text}\n"
        "Intent:"
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip().lower()
    # Take the first word and strip any trailing punctuation.
    first_word = raw.split()[0] if raw.split() else ""
    intent = "".join(c for c in first_word if c.isalpha())
    if intent not in ALLOWED_INTENTS:
        intent = "general"
    return {"intent": intent}


def route(state: State) -> str:
    """Return the name of the next node based on the classified intent."""
    return state.get("intent", "general")


def sql_node(state: State) -> dict:
    """Handle a small set of safe SQL questions."""
    text = _last_human_message(state).lower()

    if "how many customers" in text or "number of customers" in text:
        rows = database.execute_query_safe("SELECT COUNT(*) AS count FROM customers")
        result = f"There are {rows[0]['count']} customers."
    elif "how many orders" in text or "number of orders" in text:
        rows = database.execute_query_safe("SELECT COUNT(*) AS count FROM orders")
        result = f"There are {rows[0]['count']} orders."
    elif "how many tickets" in text or "number of tickets" in text:
        rows = database.execute_query_safe("SELECT COUNT(*) AS count FROM support_tickets")
        result = f"There are {rows[0]['count']} support tickets."
    else:
        match = re.search(r"status of order\s+(\d+)", text)
        if match:
            order_id = int(match.group(1))
            rows = database.execute_query_safe(
                "SELECT status FROM orders WHERE id = %s", (order_id,)
            )
            if rows:
                result = f"Order {order_id} status: {rows[0]['status']}."
            else:
                result = f"Order {order_id} was not found."
        else:
            result = (
                "I can answer count queries (customers, orders, tickets) "
                "or the status of a specific order."
            )

    return {"result": result}


def rag_node(state: State) -> dict:
    """Answer from the knowledge base via the retriever module."""
    query = _last_human_message(state)
    answer = retriever.answer(query, k=3)
    return {"result": answer["answer"]}


def get_weather(location: str) -> str:
    """Mock weather tool."""
    return f"Sunny with a chance of rain, 22 C in {location}."


def action_node(state: State) -> dict:
    """Run a simple tool based on the user's request."""
    text = _last_human_message(state)
    match = re.search(r"weather (?:in|for)?\s*([a-zA-Z\s]+)", text, re.IGNORECASE)
    location = match.group(1).strip() if match else "Paris"
    result = get_weather(location)
    return {"result": result}


def general_node(state: State) -> dict:
    """Answer directly with the LLM."""
    response = llm.invoke(
        [
            SystemMessage(content="You are a helpful support assistant."),
            *state["messages"],
        ]
    )
    return {"result": response.content}


def format_response(state: State) -> dict:
    """Append the specialist result as an assistant message."""
    return {"messages": [AIMessage(content=state["result"])]}


def build_graph():
    builder = StateGraph(State)
    builder.add_node("classify", classify_intent)
    builder.add_node("sql", sql_node)
    builder.add_node("rag", rag_node)
    builder.add_node("action", action_node)
    builder.add_node("general", general_node)
    builder.add_node("format", format_response)

    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route,
        {"sql": "sql", "rag": "rag", "action": "action", "general": "general"},
    )
    builder.add_edge("sql", "format")
    builder.add_edge("rag", "format")
    builder.add_edge("action", "format")
    builder.add_edge("general", "format")
    builder.add_edge("format", END)

    return builder.compile()


def main() -> None:
    graph = build_graph()

    sample_questions = [
        "How many orders do we have?",
        "What is the return policy?",
        "What is the weather in London?",
        "Hello, who are you?",
        "What is the status of order 12345?",
    ]

    for question in sample_questions:
        print(f"\nUser: {question}")
        final_state = graph.invoke({"messages": [HumanMessage(content=question)]})
        answer = final_state["messages"][-1].content
        detected_intent = final_state.get("intent", "unknown")
        print(f"[intent={detected_intent}] Assistant: {answer}")


if __name__ == "__main__":
    main()
