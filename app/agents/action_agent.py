"""Action agent node: decide which tool to call and execute it."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama

from app.agents.state import AgentState, last_human_message
from app.tools import api_client


LLM_MODEL = "llama3.1"
TOOLS = [
    api_client.get_weather,
    api_client.send_notification,
    api_client.create_support_ticket,
]


def _execute_tool(tool_call: dict) -> ToolMessage:
    """Run a single tool call and return a ToolMessage with the result."""
    name = tool_call["name"]
    args = tool_call.get("args", {})
    tool_map = {tool.name: tool for tool in TOOLS}

    if name not in tool_map:
        return ToolMessage(
            content=f"Unknown tool: {name}", tool_call_id=tool_call["id"]
        )

    tool = tool_map[name]
    try:
        result = tool.invoke(args)
    except Exception as exc:  # noqa: BLE001
        result = f"Tool error: {exc}"

    return ToolMessage(content=str(result), tool_call_id=tool_call["id"])


def run_action_agent(question: str) -> dict[str, str]:
    """Use LLM tool calling to choose and execute an action."""
    llm = ChatOllama(model=LLM_MODEL, temperature=0.0)
    llm_with_tools = llm.bind_tools(TOOLS)

    messages = [
        SystemMessage(
            content=(
                "You are a helpful support assistant. "
                "For the user's request you MUST choose the correct tool, call it, "
                "and then answer based solely on the tool result."
            )
        ),
        HumanMessage(content=f"User request: {question}"),
    ]

    response = llm_with_tools.invoke(messages)
    if not response.tool_calls:
        return {"answer": response.content}

    tool_messages = [_execute_tool(tc) for tc in response.tool_calls]
    # Build the final answer directly from tool results. This is more reliable
    # with local models than asking the LLM to summarize a tool-call conversation.
    results = [tm.content for tm in tool_messages]
    if len(results) == 1:
        return {"answer": results[0]}
    return {"answer": "\n\n".join(f"- {r}" for r in results)}


def action_node(state: AgentState) -> dict[str, str]:
    """Run the action agent on the user's last message."""
    question = last_human_message(state)
    result = run_action_agent(question)
    return {"result": result["answer"]}
