# Step 2 — LLM Basics + Streaming

**Experiments:** `04_basic_call.py`, `05_streaming.py`

## Concept

An LLM is just an API. You send a list of messages (system + user turns), and it returns a response. The two most important parameters are `temperature` (0 = deterministic, 1 = creative) and `max_tokens` (caps response length and cost).

Streaming means the model sends tokens back *as it generates them* rather than waiting until it's done. The user sees words appearing in real time — the same effect as ChatGPT's typing animation.

---

## The Experiments

### Basic call (`04_basic_call.py`)

```python
import ollama

response = ollama.chat(
    model="llama3.1",
    messages=[
        {"role": "system", "content": "You are a knowledgeable AI assistant."},
        {"role": "user",   "content": "What does RAG stand for?"},
    ],
    options={"temperature": 0.3, "num_predict": 300},
)
print(response["message"]["content"])
```

That's the whole thing. The response is a dict; the text is at `response["message"]["content"]`.

### Streaming (`05_streaming.py`)

The only change from a basic call is `stream=True`. The response becomes an iterator; each item is a chunk with partial content:

```python
stream = ollama.chat(
    model="llama3.1",
    messages=[...],
    stream=True,         # ← the only difference
)

print("Assistant: ", end="", flush=True)
for chunk in stream:
    content = chunk["message"]["content"]
    print(content, end="", flush=True)   # print each token immediately
print()
```

`flush=True` forces the terminal to display immediately instead of buffering.

---

## In Production

### Basic call → `app/llm.py`

The experiment calls `ollama.chat()` directly. Production wraps this in a factory function that swaps providers based on config:

```python
def get_llm(model=None, temperature=0.0, max_tokens=None) -> BaseChatModel:
    if LLM_PROVIDER == "groq":
        return ChatGroq(model=model_name, api_key=GROQ_API_KEY, ...)
    if LLM_PROVIDER == "openai":
        return ChatOpenAI(model=model_name, api_key=OPENAI_API_KEY, ...)
    return ChatOllama(model=model_name, base_url=OLLAMA_HOST, ...)  # default
```

Every agent calls `get_llm()` — they never hardcode a provider. To switch from Ollama to Groq, change one env var.

### Streaming → `app/main.py` `/chat/stream` endpoint

The experiment iterates tokens in a terminal. Production sends them over HTTP as Server-Sent Events (SSE):

```python
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        # first send metadata
        yield f"data: {json.dumps({'intent': state['intent']})}\n\n"
        # then stream the reply word-by-word
        words = state["result"].split()
        for i in range(0, len(words), 2):
            chunk = " ".join(words[i:i+2])
            yield f"data: {json.dumps({'token': chunk})}\n\n"
            await asyncio.sleep(0.01)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

The Streamlit frontend reads these SSE events and appends tokens to the chat bubble in real time.

---

## What Changed in Production

| Experiment | Production upgrade |
|------------|-------------------|
| `ollama.chat()` directly | `get_llm()` factory — provider-agnostic |
| Streams to terminal | Streams over HTTP as SSE events |
| Single hardcoded model | Configurable via `LLM_MODEL` env var |
| No token tracking | Production counts tokens (`len(text) / 4`) and logs cost estimate |

---

## Interview Q&A

**Q: What's the difference between temperature 0 and temperature 1?**
Temperature 0 makes the model always pick the most likely next token — the output is deterministic and consistent. Temperature 1 introduces randomness; the model samples from the probability distribution, producing more varied responses. The SQL agent uses temperature 0 because you always want the same query for the same question. The RAG agent uses 0.3 for slightly more natural-sounding answers.

**Q: Why SSE instead of WebSockets for streaming?**
SSE is one-directional (server → client) and works over a regular HTTP connection — no handshake, no state, works through proxies and load balancers. WebSockets are bidirectional and better for real-time two-way communication (like a game or collaborative editor). For a chat app where the user sends one message and the server streams back a response, SSE is simpler and sufficient.

**Q: What does `max_tokens` do and why does it matter in production?**
It caps how many tokens the model generates per response. Without a limit, a model can ramble for thousands of tokens — slow and expensive. Classification uses 20 tokens (just needs one word), SQL generation uses 400 (enough for a complex query), answers use 400 (a paragraph or two). Setting these tight reduces latency and cost.
