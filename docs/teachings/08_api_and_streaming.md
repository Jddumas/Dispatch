# Step 8 — FastAPI Backend + Streaming

**Experiment:** none — built directly in production  
**Production file:** `app/main.py`

## Concept

FastAPI is an async Python web framework. It handles the HTTP layer between the Streamlit frontend and the LangGraph agent: receiving requests, running the graph, and streaming responses back.

The streaming endpoint is especially interesting — the LLM graph runs synchronously (it finishes before returning), but the API gives users a "typing" effect by streaming the completed answer word-by-word over Server-Sent Events.

---

## The API Surface

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Liveness check — returns `{"status": "healthy"}` |
| `/chat` | POST | Run agent, return full answer at once |
| `/chat/stream` | POST | Run agent, stream answer word-by-word as SSE |
| `/sessions/{id}/history` | GET | Retrieve past messages for a session |
| `/metrics` | GET | Aggregate request count, latency, tokens, cost |

---

## Key Patterns

### Request/Response models with Pydantic

```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = "default"

class ChatResponse(BaseModel):
    reply: str
    intent: str
    sources: list[str] = []
    sql_query: str = ""
    data: list[dict[str, Any]] | None = None
```

FastAPI validates every incoming request against `ChatRequest` automatically. If `message` is empty or over 2000 chars, FastAPI returns a 422 before the agent even runs.

### Startup initialization with `lifespan`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # runs once when the server starts
    app.state.metrics = {"total_requests": 0, "total_latency": 0.0, ...}
    indexed = await run_in_threadpool(_check_and_index)  # index ChromaDB if empty
    yield
    # cleanup on shutdown goes here
```

The `lifespan` context manager replaces `@app.on_event("startup")`. It runs ChromaDB initialization once at startup so the first request doesn't have to wait for indexing.

### LRU cache on agent runs

```python
@lru_cache(maxsize=128)
def _cached_agent_run(message: str, session_id: str) -> dict:
    state = run_agent(message, thread_id=session_id)
    return {
        "reply": state["messages"][-1].content,
        "intent": state.get("intent", "general"),
        ...
    }
```

Identical `(message, session_id)` pairs return the cached result instantly. This is a fast-path optimization for the Streamlit UI, which can fire duplicate requests if the user clicks quickly. The trade-off: it won't re-run the agent for literally identical repeat messages in the same session.

### Server-Sent Events (SSE)

SSE is a simple HTTP protocol where the server sends a stream of `event: name\ndata: value\n\n` frames:

```python
def _sse(event: str, data: str) -> bytes:
    data = data.replace("\n", "\\n")   # escape newlines so the frame isn't broken
    return f"event: {event}\ndata: {data}\n\n".encode()

async def _stream_reply(reply, intent, sources, sql_query, data):
    yield _sse("intent", intent)          # send metadata first
    for source in sources:
        yield _sse("source", source)
    if sql_query:
        yield _sse("sql_query", sql_query)
    if data:
        yield _sse("data", json.dumps(data, default=str))

    # simulate token streaming by sending 2 words at a time
    words = reply.split(" ")
    for i in range(0, len(words), 2):
        chunk = " ".join(words[i:i+2])
        yield _sse("message", chunk)
        await asyncio.sleep(0.01)         # 10ms pause = ~100 words/sec

    yield _sse("done", "[DONE]")
```

The Streamlit frontend reads each event type and handles it differently: `intent` updates the sidebar, `source` adds to the sources list, `message` appends tokens to the chat bubble.

### Middleware stack

```python
app.add_middleware(RequestLogMiddleware)  # log every request
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, ...)
```

`RequestLogMiddleware` is a custom middleware that logs method, path, status code, duration, and client IP for every request — basic but essential for debugging production issues.

### Rate limiting with SlowAPI

```python
limiter = Limiter(key_func=get_remote_address)  # rate limit per IP

@app.post("/chat")
@limiter.limit(API_RATE_LIMIT)   # default: "10/minute"
async def chat(request: Request, payload: ChatRequest):
    ...
```

`get_remote_address` keys the rate limit by client IP. The limit is configurable via env var so you can loosen it for development (`API_RATE_LIMIT=100/minute`) without changing code.

### Running the graph in a thread pool

```python
result = await run_in_threadpool(_cached_agent_run, payload.message, payload.session_id)
```

The LangGraph agent runs synchronous blocking code (psycopg2, Ollama HTTP calls). `run_in_threadpool` runs it in a background thread so FastAPI's async event loop isn't blocked. This is the correct pattern for mixing sync and async code in FastAPI.

---

## Interview Q&A

**Q: Why use SSE instead of WebSockets?**
SSE is one-directional (server → client) and works over a plain HTTP connection. WebSockets require a handshake and maintain a persistent two-way connection. For a chat UI where the user sends one message and waits for a streamed reply, SSE is simpler: no connection state, works through proxies, and HTTP/2 supports multiple SSE streams over one TCP connection.

**Q: The streaming endpoint still runs the full agent before streaming — is that really "streaming"?**
Technically it's *simulated* streaming. The underlying LLM runs synchronously and produces the full answer before the endpoint returns. The word-by-word SSE loop creates the *appearance* of streaming. True token streaming would require async graph nodes and the LLM to support it — that's a future improvement. In practice, the perceived UX is nearly identical for responses under ~200 words.

**Q: What does the LRU cache buy you and when would you remove it?**
It makes identical repeat requests instant (no graph round-trip). This matters in the Streamlit UI where duplicate requests can happen. The downside: if the conversation evolves, an identical-looking message in the same session might warrant a different response — the cache would return the stale one. For a production multi-user system you'd want cache invalidation keyed on conversation state, not just (message, session_id).
