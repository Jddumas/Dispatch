"""
Week 1, Day 3-4: Function calling with a local Ollama model.

The assistant defines a `get_weather` tool. When asked about the weather,
the model should call the tool; we run it and return the result so the
model can produce a final answer.
"""

import json
import ollama


def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"Sunny with a chance of rain, 22 C in {location}."


def main() -> None:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant. Use the available "
                "tools to answer the user's questions."
            ),
        },
        {"role": "user", "content": "What is the weather like in Paris?"},
    ]

    response = ollama.chat(
        model="llama3.1",
        messages=messages,
        tools=[get_weather],
    )

    tool_calls = response["message"].get("tool_calls")
    if tool_calls:
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            arguments = tool_call["function"]["arguments"]
            print(f"Tool call requested: {tool_name}({json.dumps(arguments)})")

            if tool_name == "get_weather":
                result = get_weather(**arguments)
                print(f"Tool result: {result}")

                # Add the assistant's tool call and the tool result to the conversation
                messages.append(response["message"])
                messages.append(
                    {"role": "tool", "tool_name": tool_name, "content": result}
                )

        final = ollama.chat(
            model="llama3.1",
            messages=messages,
            tools=[get_weather],
        )
        print(f"Final answer: {final['message']['content']}")
    else:
        print("No tool call was returned.")
        print(response["message"]["content"])


if __name__ == "__main__":
    main()
