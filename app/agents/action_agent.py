"""Action agent node: decide which tool to call and execute it."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.agents.state import AgentState, last_human_message
from app.config import LLM_MODEL
from app.llm import get_llm
from app.tools import api_client

logger = logging.getLogger(__name__)

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
        logger.warning("Unknown tool requested: %s", name)
        return ToolMessage(
            content=f"Unknown tool: {name}", tool_call_id=tool_call["id"]
        )

    tool = tool_map[name]
    try:
        result = tool.invoke(args)
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        result = f"Tool error: {exc}"

    return ToolMessage(content=str(result), tool_call_id=tool_call["id"])


def run_action_agent(question: str) -> dict[str, str]:
    """Use LLM tool calling to choose and execute an action."""
    try:
        llm = get_llm(model=LLM_MODEL, temperature=0.0, max_tokens=200)
        llm_with_tools = llm.bind_tools(TOOLS).with_retry(
            stop_after_attempt=3, wait_exponential_jitter=True
        )

        messages = [
            SystemMessage(
                content=(
                    "You are a helpful support assistant that can use tools. "
                    "For the user's request you MUST choose the correct tool, call it, "
                    "and then answer based solely on the tool result."
                )
            ),
            HumanMessage(content=f"User request: {question}"),
        ]

        response = llm_with_tools.invoke(messages)
        if not response.tool_calls:
            logger.info("No tool call made; returning direct response")
            return {"answer": response.content or "I'm not sure how to handle that request."}

        logger.info("Action agent calling tool(s): %s", [tc["name"] for tc in response.tool_calls])
        tool_messages = [_execute_tool(tc) for tc in response.tool_calls]
        results = [tm.content for tm in tool_messages]
        if len(results) == 1:
            return {"answer": results[0]}
        return {"answer": "\n\n".join(f"- {r}" for r in results)}
    except Exception:
        logger.exception("Action agent failed")
        return {"answer": "I couldn't complete that action right now. Please try again later."}


def action_node(state: AgentState) -> dict[str, str]:
    """Run the action agent on the latest user message."""
    question = last_human_message(state)
    result = run_action_agent(question)
    return {"result": result["answer"]}
