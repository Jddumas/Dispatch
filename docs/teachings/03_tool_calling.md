# Step 3 — Tool Calling + The Agentic Loop

**Experiments:** `06_function_calling.py`, `07_agent_with_tools.py`

## Concept

Tool calling (also called function calling) is when the model decides to call a function instead of writing a text answer. You give the model a list of available tools with descriptions; it decides which one to call and with what arguments; your code executes the tool and sends the result back; the model uses the result to form its final answer.

The "agentic loop" is just running this multiple times: model → tool call → execute → model → (more tool calls or final answer).

---

## The Experiments

### Single tool (`06_function_calling.py`)

```python
def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    return f"Sunny with a chance of rain, 22 C in {location}."

messages = [
    {"role": "system", "content": "Use tools to answer questions."},
    {"role": "user",   "content": "What is the weather like in Paris?"},
]

response = ollama.chat(model="llama3.1", messages=messages, tools=[get_weather])

tool_calls = response["message"].get("tool_calls")
if tool_calls:
    for tool_call in tool_calls:
        result = get_weather(**tool_call["function"]["arguments"])
        messages.append(response["message"])              # assistant's tool request
        messages.append({"role": "tool", "content": result})  # tool result

    final = ollama.chat(model="llama3.1", messages=messages, tools=[get_weather])
    print(final["message"]["content"])
```

Two LLM calls: first to decide which tool, second to form the answer from the tool result.

### Multi-tool agentic loop (`07_agent_with_tools.py`)

The loop runs up to 3 times — more tools, more turns possible:

```python
TOOLS = [get_weather, lookup_order, search_database]
TOOL_NAMES = {tool.__name__: tool for tool in TOOLS}

def run_agent_turn(messages, user_message):
    messages.append({"role": "user", "content": user_message})

    for _ in range(3):  # max 3 tool-call turns
        response = ollama.chat(model="llama3.1", messages=messages, tools=TOOLS)
        tool_calls = response["message"].get("tool_calls") or []

        if not tool_calls:
            return response["message"]["content"]  # final answer, no more tools needed

        messages.append(response["message"])
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            if tool_name not in TOOL_NAMES:
                result = f"Tool '{tool_name}' is not available."
            else:
                result = TOOL_NAMES[tool_name](**tool_call["function"]["arguments"])
            messages.append({"role": "tool", "tool_name": tool_name, "content": result})

    return "Reached maximum tool-call turns."
```

---

## In Production

### `app/tools/api_client.py` — tool definitions

Production tools use LangChain's `@tool` decorator instead of plain functions. The decorator reads the docstring and type hints to auto-generate a JSON schema the model uses to know how to call the tool:

```python
from langchain_core.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location.
    Use this for questions like 'What's the weather in Paris?'"""
    return f"The weather in {location} is sunny with a chance of rain, 22 C."

@tool
def create_support_ticket(customer_id: int, subject: str, description: str,
                          order_id: int | None = None) -> str:
    """Create a support ticket in the database."""
    rowcount = database.execute_query(
        "INSERT INTO support_tickets (customer_id, order_id, subject, description, status) "
        "VALUES (%s, %s, %s, %s, 'open')",
        (customer_id, order_id, subject, description),
        fetch=False,
    )
    return f"Created {rowcount} support ticket(s) for customer {customer_id}."
```

The docstring is the tool's description — write it clearly because the model reads it to decide when to call the tool.

### `app/agents/action_agent.py` — the loop

```python
TOOLS = [api_client.get_weather, api_client.send_notification, api_client.create_support_ticket]

def run_action_agent(question: str) -> dict:
    llm = get_llm(temperature=0.0, max_tokens=200)
    llm_with_tools = llm.bind_tools(TOOLS).with_retry(stop_after_attempt=3)

    messages = [
        SystemMessage(content="You are a support assistant. Use tools to complete requests."),
        HumanMessage(content=f"User request: {question}"),
    ]

    response = llm_with_tools.invoke(messages)
    if not response.tool_calls:
        return {"answer": response.content}

    tool_messages = [_execute_tool(tc) for tc in response.tool_calls]
    return {"answer": "\n\n".join(tm.content for tm in tool_messages)}
```

`.bind_tools(TOOLS)` sends the tool schemas to the model. `.with_retry()` retries the LLM call (not the tool) on network errors.

---

## What Changed in Production

| Experiment | Production upgrade |
|------------|-------------------|
| Plain Python functions | LangChain `@tool` decorator — auto-generates JSON schema |
| `tool.__name__` registry | `llm.bind_tools(TOOLS)` handles schema registration |
| Manual message assembly | LangChain `ToolMessage` type handles tool result formatting |
| No error handling | `try/except` in `_execute_tool`; `.with_retry()` on the LLM |
| Hardcoded tool list | `TOOLS` list — add a `@tool` function and append it |

---

## Interview Q&A

**Q: How does the model know which tool to call?**
The `@tool` decorator generates a JSON schema from the function's type hints and docstring. This schema is sent to the model alongside the user message. The model reads the schema descriptions to decide which tool fits the request, then returns a structured JSON object with the tool name and arguments — it doesn't execute the tool itself, it just says "call this function with these args."

**Q: What happens if the model calls a tool with wrong arguments?**
LangChain validates the arguments against the schema before calling the function. If the model passes a string where an int is expected, the tool call fails with a `ValidationError`. The `_execute_tool` function catches this and returns an error string back to the model, which can then try again or give a graceful answer.

**Q: Why cap the agentic loop at 3 turns?**
To prevent infinite loops — a model that calls the wrong tool repeatedly would otherwise run forever. Three turns is enough for: pick a tool → get a result → form an answer. If it takes more than that, something is wrong and it's better to fail fast than spin.
