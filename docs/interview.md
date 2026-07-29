# Otto — Interview Cheat Sheet

A standalone reference for talking about this project in a technical interview. Read the full question and answer aloud before the interview — you want to answer in under 90 seconds without notes.

---

## The Elevator Pitch

> "I built Otto — a multi-agent AI support system. Users ask questions in natural language; a classifier routes them to the right specialist agent; the agent answers using either a PostgreSQL database, a ChromaDB knowledge base, or external tools. The whole thing is orchestrated with LangGraph, served via FastAPI with streaming responses, and runs locally on Ollama or deploys to Render with Groq."

That's 3 sentences. Use it as the opener for any "tell me about your project" question.

---

## Architecture Questions

### "Walk me through the architecture."

Start with the diagram:

```
User (Streamlit)
    ↓ POST /chat/stream  (Server-Sent Events)
FastAPI
    ↓ run_agent(message, thread_id)
LangGraph Router
    ├─ sql     → SQL Agent     → PostgreSQL
    ├─ rag     → RAG Agent     → ChromaDB (vector search)
    ├─ action  → Action Agent  → Tools (weather, tickets)
    └─ general → LLM           → Direct answer
```

Then narrate:
> "The user sends a message to the FastAPI backend. The LangGraph router first validates the input — length, blocked keywords — then runs an LLM classifier to pick one of four intents: sql, rag, action, or general. The specialist agent handles the request and returns a result. FastAPI streams it back as Server-Sent Events so the UI shows a typing effect."

### "Why LangGraph instead of if/else routing?"

> "Three reasons: state management, testability, and extensibility. LangGraph's `SqliteSaver` checkpointer serializes the full conversation state to disk after every turn — multi-turn memory is built in. Each node is a pure function I can test in isolation. And adding a new agent type is just a new node and a new edge — I don't touch the routing logic."

### "What are the four agent types and when does each fire?"

| Intent | Triggers | How it answers |
|--------|----------|----------------|
| `sql` | Questions about orders, customers, tickets, revenue | NL → SQL → PostgreSQL → formatted text |
| `rag` | Policy questions, product specs, troubleshooting | Embed query → ChromaDB retrieval → LLM grounded answer |
| `action` | "weather in X", "create a ticket", "notify someone" | LLM picks a tool, runs it, returns result |
| `general` | Greetings, small talk, anything else | LLM answers directly |

---

## Technical Deep Dives

### "How does RAG work in your system?"

> "RAG has three phases. At startup I index the knowledge base: split 18 markdown documents into 800-character chunks with 100-character overlap, embed each chunk using nomic-embed-text, and store the vectors in ChromaDB. When a question comes in, I embed it with the same model and run a cosine similarity search to get the top 3 chunks. Then I pass those chunks to the LLM as context and tell it to answer *only from the context*. A distance threshold filters out irrelevant matches — if nothing is close enough, it returns 'I don't have information about that' instead of hallucinating."

### "How do you prevent SQL injection?"

> "Three layers. First, after the LLM generates SQL, I strip comments and replace string literals, then check for forbidden keywords like DROP, DELETE, INSERT. Second, I verify the statement starts with SELECT or WITH — nothing else runs. Third, psycopg2 uses parameterized queries for any user-supplied values, so even if something slips through the keyword check, the driver won't execute it as SQL. The layering matters — comments can hide forbidden keywords, so you have to strip them before checking."

### "How does conversation memory work?"

> "LangGraph has a pluggable checkpointer system. I use `SqliteSaver`, which serializes the full graph state — including the complete message history — to a SQLite file after every turn. Each session gets a `thread_id`; when a new message comes in, LangGraph looks up that thread, reloads the state, appends the new message, runs the graph, and saves the updated state. If the server restarts, nothing is lost — it's all in the file."

### "How does streaming work?"

> "The streaming endpoint uses Server-Sent Events — a simple HTTP protocol where the server pushes `event: name\ndata: value\n\n` frames. I first send metadata events: intent, sources, SQL query. Then I split the completed reply into 2-word chunks and send each as a `message` event with a 10ms pause — that's the typing effect. It's simulated streaming because the underlying LLM runs synchronously and finishes before any tokens are sent. True token streaming would require async graph nodes."

---

## Design Decision Questions

### "Why Ollama locally instead of OpenAI?"

> "Ollama is free, private, and doesn't require an API key — perfect for local development and demos. The tradeoff is speed: llama3.1 on CPU takes 8–15 seconds per response. For the cloud deployment I switch to Groq, which runs the same model and returns responses in under 2 seconds. The `get_llm()` factory makes this a one-env-var change."

### "What's the LRU cache for?"

> "It caches agent runs keyed on (message, session_id). If the Streamlit UI fires a duplicate request — which happens when the user clicks quickly — the cached result returns instantly instead of running the full graph again. The trade-off is that an identical message in the same session always returns the cached response, even if the conversation context changed. For this use case that's acceptable."

### "How would you scale this?"

> "A few changes: swap `SqliteSaver` for a Redis checkpointer so multiple API instances can share conversation state. Run uvicorn with multiple workers (currently single-threaded because LangGraph's sync graph blocks the event loop). Use a persistent ChromaDB server instead of the embedded one so the vector index survives deploys. For the LLM, Groq handles horizontal scaling transparently — I'd just need to stay within rate limits."

---

## "What Would You Add Next?"

Point to `new_feature.md` in the repo root. Key items to mention:

1. **Conversation-aware follow-ups** — the SQL and RAG agents see the last 3 user messages, but they don't yet use assistant replies as context. Adding that makes "filter to gold tier" work after "show me top customers."

2. **Real DB-backed action tools** — currently `get_weather` is mocked and `send_notification` just prints. Adding `lookup_order(order_id)`, `get_customer_by_email(email)`, and `update_ticket_status(ticket_id, status)` makes the action agent genuinely useful.

3. **Hybrid intent** — a fifth intent (`hybrid`) that fans out to both SQL and RAG and synthesizes the results. Enables "Is customer 3's last order still in the return window?" — needs order date from the DB and the return policy from the knowledge base.

---

## Numbers to Remember

- **30 test cases**, 5 eval metrics, 100% intent accuracy on `llama3.1`
- **18 knowledge base documents** across 3 categories (policies, products, support)
- **9 database tables**, 50 customers, 103 orders, 80 support tickets
- **4 agent types**, 3 action tools, ~10s average latency (local CPU)
- **Chunking:** 800-char chunks, 100-char overlap, top-3 retrieval
- **Safety:** 15 forbidden SQL keywords + comment stripping + parameterized queries
