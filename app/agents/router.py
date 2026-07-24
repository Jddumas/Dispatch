"""Dispatch AI LangGraph router and compiled graph."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from app.agents.action_agent import action_node
from app.agents.rag_agent import rag_node
from app.agents.sql_agent import sql_node
from app.agents.state import AgentState, last_human_message


LLM_MODEL = "llama3.1"
ALLOWED_INTENTS = {"sql", "rag", "action", "general"}


def classify_intent(state: AgentState) -> dict[str, str]:
    """Classify the user's last message into sql, rag, action, or general."""
    user_text = last_human_message(state)
    prompt = (
        "You are an intent classifier for a support assistant. "
        "Classify the user's message into exactly one of these categories:\n"
        "- sql: questions about orders, customers, tickets, or anything stored in the database\n"
        "- rag: questions about company policies, product specs, or troubleshooting\n"
        "- action: requests that require calling a tool such as checking weather, "
        "sending a notification, or creating a support ticket\n"
        "- general: anything else, including greetings or small talk\n\n"
        "Respond with exactly one lowercase word. Do not explain.\n"
        "Allowed responses: sql, rag, action, general\n\n"
        f"User message: {user_text}\n"
        "Intent:"
    )
    llm = ChatOllama(model=LLM_MODEL, temperature=0.0)
    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip().lower()
    first_word = raw.split()[0] if raw.split() else ""
    intent = "".join(c for c in first_word if c.isalpha())
    if intent not in ALLOWED_INTENTS:
        intent = "general"
    return {"intent": intent}


def route(state: AgentState) -> str:
    """Return the name of the next node based on the classified intent."""
    return state.get("intent", "general")


def general_node(state: AgentState) -> dict[str, str]:
    """Answer directly with the LLM."""
    llm = ChatOllama(model=LLM_MODEL, temperature=0.0)
    response = llm.invoke(
        [
            SystemMessage(content="You are a helpful support assistant."),
            *state["messages"],
        ]
    )
    return {"result": response.content}


def format_response(state: AgentState) -> dict:
    """Append the specialist result as an assistant message."""
    return {"messages": [AIMessage(content=state["result"])]}


def build_graph():
    """Build and compile the full multi-agent graph."""
    builder = StateGraph(AgentState)
    builder.add_node("classify", classify_intent)
    builder.add_node("sql_agent", sql_node)
    builder.add_node("rag_agent", rag_node)
    builder.add_node("action_agent", action_node)
    builder.add_node("general", general_node)
    builder.add_node("format", format_response)

    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route,
        {
            "sql": "sql_agent",
            "rag": "rag_agent",
            "action": "action_agent",
            "general": "general",
        },
    )
    builder.add_edge("sql_agent", "format")
    builder.add_edge("rag_agent", "format")
    builder.add_edge("action_agent", "format")
    builder.add_edge("general", "format")
    builder.add_edge("format", END)

    return builder.compile()


def run_agent(question: str) -> AgentState:
    """Run the compiled graph against a single user question."""
    graph = build_graph()
    return graph.invoke({"messages": [HumanMessage(content=question)]})


if __name__ == "__main__":
    questions = [
        "How many customers do we have?",
        "What is the return policy?",
        "What is the weather in London?",
        "Create a support ticket for customer 1 about order 5",
        "Hello!",
    ]
    for question in questions:
        print(f"\nUser: {question}")
        final_state = run_agent(question)
        print(f"Intent: {final_state['intent']}")
        print(f"Assistant: {final_state['messages'][-1].content}")
