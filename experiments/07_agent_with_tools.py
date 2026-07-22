"""
Week 1, Day 5: Function Calling Deep Dive

A small agent loop that lets a local Ollama model decide when to call one of
several tools, executes the tool, feeds the result back to the model, and
continues until a final answer is produced.
"""

import json
from typing import Callable

import ollama


def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"Sunny with a chance of rain, 22 C in {location}."


def lookup_order(order_id: str) -> str:
    """Look up the status of an order by its order ID."""
    mock_orders = {
        "12345": "Order 12345: shipped, arriving tomorrow.",
        "67890": "Order 67890: processing, expected to ship in 2 days.",
    }
    return mock_orders.get(order_id, f"Order {order_id}: not found.")


def search_database(query: str) -> str:
    """Search the support knowledge base for the given query."""
    mock_results = {
        "return policy": "Returns accepted within 30 days with original receipt.",
        "shipping": "Standard shipping is 3-5 business days; express is 1-2 days.",
    }
    return mock_results.get(
        query.lower(),
        f"No exact match for '{query}'. Try 'return policy' or 'shipping'.",
    )


# Registry of available tools
TOOLS: list[Callable[..., str]] = [get_weather, lookup_order, search_database]
TOOL_NAMES = {tool.__name__: tool for tool in TOOLS}


def run_agent_turn(messages: list[dict], user_message: str) -> str:
    """Run the user > model > tool > result > model loop for one user turn."""
    messages.append({"role": "user", "content": user_message})

    for _ in range(3):
        response = ollama.chat(
            model="llama3.1",
            messages=messages,
            tools=TOOLS,
        )

        assistant_message = response["message"]
        tool_calls = assistant_message.get("tool_calls") or []

        if not tool_calls:
            # No tools requested -> we have a final answer
            messages.append(assistant_message)
            return assistant_message["content"]

        # Execute each tool call and build the tool-result messages
        messages.append(assistant_message)
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            arguments = tool_call["function"]["arguments"]
            print(f"  [tool call] {tool_name}({json.dumps(arguments)})")

            if tool_name not in TOOL_NAMES:
                result = f"Tool '{tool_name}' is not available."
            else:
                try:
                    result = TOOL_NAMES[tool_name](**arguments)
                except Exception as exc:
                    result = f"Error calling {tool_name}: {exc}"

            print(f"  [tool result] {result}")
            messages.append(
                {
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": result,
                }
            )

    return "Reached the maximum number of tool-call turns."


def main() -> None:
    system_prompt = (
        "You are a helpful support agent. You have access to the following tools:\n"
        "- get_weather(location): current weather for a city\n"
        "- lookup_order(order_id): status of an order\n"
        "- search_database(query): search the support knowledge base\n"
        "If a user's question can be answered with one of these tools, call it. "
        "Otherwise, answer directly."
    )

    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    sample_questions = [
        "What is the weather like in Paris?",
        "What is the status of order 12345?",
        "What is the return policy?",
        "Who wrote Romeo and Juliet?",
    ]

    for question in sample_questions:
        print(f"\nUser: {question}")
        answer = run_agent_turn(messages, question)
        print(f"Assistant: {answer}")


if __name__ == "__main__":
    main()
