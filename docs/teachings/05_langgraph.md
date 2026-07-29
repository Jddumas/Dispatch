# Step 5 — LangGraph: State Machines for Agents

**Experiments:** `09_langgraph_basics.py`, `10_week5_graph.py`

## Concept

LangGraph is a way to build AI agents as a graph — nodes do work, edges connect them, and a central `State` object flows through. Instead of a chain of function calls, you define a *directed graph* that can branch, loop, and persist state across turns.

Why not just use if/else? Three reasons:
1. **State management** — the graph automatically tracks the full conversation state and can checkpoint it to a database
2. **Testability** — each node is a pure function you can unit test in isolation
3. **Extensibility** — adding a new agent type means adding a node and an edge, not rewriting routing logic

---

## The Experiment (`09_langgraph_basics.py`)

The experiment builds the same 4-way router that's in production:

```python
from langgraph.graph import StateGraph, START, END, add_messages
from typing_extensions import Annotated, TypedDict

class State(TypedDict):
    messages: Annotated[list, add_messages]  # accumulates all messages
    intent: str                               # set by classifier
    result: str                               # set by specialist node

def classify_intent(state: State) -> dict:
    user_text = state["messages"][-1].content
    # ask LLM to classify into "sql", "rag", "action", or "general"
    return {"intent": intent}

def route(state: State) -> str:
    return state.get("intent", "general")  # returns the name of the next node

builder = StateGraph(State)
builder.add_node("classify", classify_intent)
builder.add_node("sql",     sql_node)
builder.add_node("rag",     rag_node)
builder.add_node("action",  action_node)
builder.add_node("general", general_node)
builder.add_node("format",  format_response)

builder.add_edge(START, "classify")
builder.add_conditional_edges("classify", route,
    {"sql": "sql", "rag": "rag", "action": "action", "general": "general"})
# all specialist nodes → format → END
builder.add_edge("sql", "format")
builder.add_edge("rag", "format")
builder.add_edge("action", "format")
builder.add_edge("general", "format")
builder.add_edge("format", END)

graph = builder.compile()
final_state = graph.invoke({"messages": [HumanMessage(content="How many orders?")]})
```

Every node is a function that receives the current `State` and returns a dict of fields to update. LangGraph merges that dict into the state.

---

## In Production (`app/agents/router.py`)

The production graph adds two things the experiment doesn't have: **input validation** and **conversation memory**.

```
START
  ↓
validate_input      ← new: check length, blocked keywords
  ↓ (valid)
classify_intent
  ↓
route_by_intent     ← conditional: sql / rag / action / general / fallback
  ↓
[specialist node]
  ↓
format_response
  ↓
END
```

**Input validation node:**
```python
def validate_input(state: AgentState) -> dict:
    text = last_human_message(state)
    if not text:
        return {"intent": "fallback", "result": "Please enter a message."}
    if len(text) > MAX_INPUT_LENGTH:
        return {"intent": "fallback", "result": "Message too long."}
    for kw in _BLOCKED_KEYWORDS:
        if kw in text.lower():
            return {"intent": "fallback", "result": "I can't help with that request."}
    return {}  # empty dict = no change, continue to classify
```

**Conversation memory:**
```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string(CHECKPOINT_DB)
graph = builder.compile(checkpointer=checkpointer)

# invoke with a thread_id to persist and restore state
config = {"configurable": {"thread_id": session_id}}
final_state = graph.invoke({"messages": [HumanMessage(content=question)]}, config=config)
```

Every invocation with the same `thread_id` continues from where it left off — the entire `messages` list is reloaded from SQLite.

### `AgentState` (`app/agents/state.py`)

```python
class AgentState(TypedDict):
    messages:   Annotated[list[BaseMessage], add_messages]
    intent:     str
    result:     str
    sources:    list[str]   # RAG source document titles
    sql_query:  str         # generated SQL (shown in UI)
    data:       list[dict] | None  # raw SQL result rows
```

`add_messages` is an *annotated reducer* — instead of replacing `messages`, LangGraph appends new messages to the existing list. This is what enables multi-turn conversations.

---

## What Changed in Production

| Experiment | Production upgrade |
|------------|-------------------|
| No validation | `validate_input` node with length + keyword checks |
| No memory | `SqliteSaver` checkpointer keyed by `thread_id` |
| Simple `State` | `AgentState` adds `sources`, `sql_query`, `data` fields |
| In-memory only | Checkpoints persist to `data/checkpoints.sqlite` |

---

## Interview Q&A

**Q: Why use LangGraph instead of a simple chain of function calls?**
A chain is fine for linear flows, but breaks when you need branching (route to different agents), state persistence (resume a conversation), or loops (retry on failure). LangGraph models these as first-class graph constructs. It also gives you a checkpointer for free — conversation state gets serialized to SQLite without any extra code.

**Q: What's the `add_messages` annotation doing?**
It tells LangGraph how to *merge* updates to the `messages` field. Without it, a node that returns `{"messages": [new_message]}` would *replace* the entire message list. With `add_messages`, it *appends* — so you accumulate the full conversation history automatically.

**Q: How does the conditional edge work?**
`add_conditional_edges("classify", route, mapping)` runs `route(state)` after the `classify` node, takes its return value (a string), and uses the `mapping` dict to look up the next node name. It's just a dictionary lookup — clean, explicit, and easy to extend by adding a new key.
