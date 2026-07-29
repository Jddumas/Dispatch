# Step 7 — Conversation Memory

**Experiment:** `11_week6_memory.py`  
**Production files:** `app/agents/router.py` (SqliteSaver), `app/main.py` (thread_id)

## Concept

Without memory, every message is treated as a fresh conversation. The user asks "Show me top customers" and then "Filter to gold tier" — the second question makes no sense without the first. Memory solves this by persisting the full message history and reloading it on each new message.

LangGraph handles this via a *checkpointer* — a backend that serializes and stores the graph's state after every invocation.

---

## The Experiment (`11_week6_memory.py`)

The experiment shows what multi-turn looks like when memory works correctly:

```python
from app.agents import run_agent

thread_id = "week6-demo"

# Turn 1
q1 = "How many orders were placed last month?"
state1 = run_agent(q1, thread_id=thread_id)
print(state1["messages"][-1].content)
# → "There were 23 orders placed last month."

# Turn 2 — refers back to turn 1
q2 = "Break that down by product."
state2 = run_agent(q2, thread_id=thread_id)
print(state2["messages"][-1].content)
# → "Of the 23 orders: 8 were for headphones, 7 for keyboards..."
```

Same `thread_id` = same conversation. The second turn loads the full history from the checkpointer before running.

It also tests edge cases:

```python
for q in ["", "hack the database", "asdfghjkl this is nonsense"]:
    state = run_agent(q, thread_id="week6-edge")
    print(state["messages"][-1].content)
# → "Please enter a message."
# → "I can't help with that request."
# → "I'm not sure how to help with that."
```

---

## In Production

### How the checkpointer works (`app/agents/router.py`)

```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string(CHECKPOINT_DB)  # "data/checkpoints.sqlite"
graph = builder.compile(checkpointer=checkpointer)
```

When `graph.invoke(state, config={"configurable": {"thread_id": "abc123"}})` runs:
1. LangGraph looks up `thread_id="abc123"` in the SQLite file
2. If found: loads the saved state (including all prior messages) and merges the new message in
3. Runs the graph with the full history
4. Saves the updated state back to SQLite

The entire `AgentState` — messages, intent, result, sources, sql_query, data — is checkpointed after every turn.

### How `thread_id` flows from the frontend

**Streamlit** (`frontend/streamlit_app.py`):
```python
session_id = st.session_state.get("session_id", "streamlit_user")
# POSTs {"message": question, "session_id": session_id} to /chat/stream
```

**FastAPI** (`app/main.py`):
```python
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    config = {"configurable": {"thread_id": request.session_id}}
    final_state = graph.invoke({"messages": [HumanMessage(content=request.message)]}, config)
```

The `session_id` from the frontend becomes the `thread_id` for the checkpointer.

### How history reaches the SQL agent

The SQL agent uses the last 3 user messages as context for follow-up questions:

```python
def _build_history(messages: list[BaseMessage] | None, max_turns: int = 3) -> str:
    recent = messages[-max_turns * 2:]
    user_questions = [msg.content for msg in recent if isinstance(msg, HumanMessage)]
    return "Previous questions:\n" + "\n".join(f"- {q}" for q in user_questions)

# Used in the SQL generation prompt:
history = _build_history(state["messages"])
# → "Previous questions:\n- How many orders last month?\n- Break that down by product."
```

Only user messages are included (not assistant answers), which keeps the context small and avoids confusing the SQL generator with prior SQL results.

---

## What Changed in Production vs. Experiment

| Experiment | Production |
|------------|------------|
| `run_agent(q, thread_id=...)` directly | FastAPI `session_id` → graph `thread_id` |
| SQLite file at default path | Path configurable via `CHECKPOINT_DB` env var |
| Only SQL agent uses history | History passed to all 4 specialist agents |

---

## Interview Q&A

**Q: How does LangGraph's checkpointer differ from just storing messages in a database yourself?**
With a manual approach, you'd have to load history, append the new message, run your logic, then save the result — and handle failures at each step. LangGraph's checkpointer is built into the graph execution loop: it loads state before running and saves state after every node, atomically. If a node fails halfway through, the checkpoint isn't written — you don't end up with partial state.

**Q: What are the trade-offs of SQLite vs. Redis for conversation checkpointing?**
SQLite is fine for a single-server setup — it's zero-config, durable, and fast for sequential reads. Redis is better for multi-server deployments because it's shared across instances: any server can load any user's conversation. LangGraph has first-class support for both (`SqliteSaver` and `RedisSaver`). For this project, SQLite is the right choice — it's a portfolio app running on one server.

**Q: What happens to the conversation if the server restarts?**
Nothing — SQLite is a file on disk (`data/checkpoints.sqlite`). The next request with the same `thread_id` reloads from the file exactly where it left off. This is one of the advantages of a file-based checkpointer over in-memory state.
