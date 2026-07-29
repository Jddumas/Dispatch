# Building Otto: A Production Multi-Agent System from Scratch

## Introduction

Over the last three months I built **Otto**, a production-oriented customer-support assistant that can answer policy questions, query a PostgreSQL database, and execute simple actions — all powered by local LLMs. The goal was not just to chain a model to an API, but to design a maintainable, observable, multi-agent system that could be deployed on modest hardware without paying per-token fees.

In this post I walk through the architecture, the key engineering decisions, the mistakes I made, and how I evaluated the result.

## What I Built and Why

Customer-support chatbots usually fall into one of two traps: they either give generic answers with no grounding in company data, or they are rigid rule-based systems that cannot handle nuance. I wanted Otto to combine the best of both:

- **Grounded answers** from a knowledge base (RAG).
- **Live data** from a PostgreSQL database (SQL).
- **Actionable tasks** like checking the weather, sending a notification, or opening a support ticket.
- **Memory** so a user can ask follow-up questions naturally.
- **Local execution** to avoid cloud API costs and data-leakage concerns.

The result is a FastAPI backend, a Streamlit frontend, a LangGraph agent graph, and a Docker Compose stack that runs entirely on a laptop or server with Ollama.

## Architecture Decisions

Otto follows a router pattern. When a message arrives, the router node classifies it into one of four intents:

```text
sql     -> SQL Agent
rag     -> RAG Agent
action  -> Action Agent
general -> General Node
```

Each specialist node is a small LangGraph node that receives the full conversation state and returns an updated result. The `format_response` node then appends that result as an assistant message and writes the state to a `SqliteSaver` checkpointer keyed by the user's `session_id`.

I chose LangGraph because it makes the control flow explicit: you see the graph edges, the state schema, and the checkpointed memory in one place. This is much easier to debug than a long chain of `.pipe()` calls.

### Why Local Ollama?

Running `llama3.1` locally has trade-offs:

- **Pros:** no API keys, no network latency to OpenAI, no per-token costs, and data never leaves the machine.
- **Cons:** latency is higher than cloud APIs, and a consumer CPU takes ~5–10 seconds per LLM call.

For a portfolio project and for privacy-sensitive deployments, the pros outweigh the cons. I also added `with_retry` around every LLM call and wrapped tool/database access in try/except blocks so the system stays resilient when Ollama stutters.

## How the Routing Works

The router uses a small prompt that includes the conversation history and the latest user message:

```python
prompt = (
    "You are an intent classifier for a support assistant...\n"
    "Respond with exactly one lowercase word: sql, rag, action, or general."
)
```

I added few-shot examples because small models can be brittle:

```text
- 'How many orders did John place last month?' -> sql
- 'What is your return policy?' -> rag
- 'What's the weather in Berlin?' -> action
- 'Hello!' -> general
```

After classification, the graph uses a conditional edge to dispatch to the appropriate node. The classifier achieved 100% accuracy on a 20-case evaluation suite, although that is partly because the test cases are representative of the training documents and not adversarial.

## RAG Implementation Details

The RAG agent indexes markdown documents into ChromaDB using `nomic-embed-text` embeddings. Each document is split into paragraphs, then further chunked if a paragraph exceeds 800 characters.

```python
collection.add(
    ids=[chunk["id"] for chunk in chunks],
    documents=[chunk["text"] for chunk in chunks],
    embeddings=embeddings,
    metadatas=[chunk["metadata"] for chunk in chunks],
)
```

At query time, the retriever:

1. Embeds the question.
2. Queries ChromaDB with cosine distance.
3. Filters out chunks whose distance is above `RAG_DISTANCE_THRESHOLD`.
4. Sends the remaining context to `llama3.1` with a strict prompt: "Use only the provided context."

The agent also extracts source titles from the retrieved metadata and returns them to the UI, so the user sees which knowledge-base article the answer came from.

## SQL Agent Challenges and Solutions

Allowing an LLM to generate SQL is risky. I added a multi-layer safety net:

1. **Prompt instructions** — the model is told to produce only `SELECT` statements and no trailing semicolon.
2. **Keyword filtering** — a regex strips comments and string literals, then checks for forbidden words like `DELETE`, `DROP`, `INSERT`, `UPDATE`, etc.
3. **Statement count check** — rejects any query containing more than one statement.
4. **Read-only database user** — in production the application user should have only `SELECT` privileges.

```python
def _is_safe(sql: str) -> tuple[bool, str]:
    cleaned = _strip_comments(sql).strip().lower()
    tokens = cleaned.split()
    if not tokens or tokens[0] != "select":
        return False, "Only SELECT statements are allowed."
    # ... additional checks
```

The SQL agent also formats the raw rows into a concise natural-language answer using a second LLM call. This keeps the UI friendly while still exposing the generated query for debugging.

## Action Agent and Tool Calling

The action agent uses `ChatOllama.bind_tools(...)` with three mock tools:

- `get_weather(location: str)`
- `send_notification(recipient: str, message: str)`
- `create_support_ticket(customer_id: int, order_id: int, subject: str)`

The LLM returns a tool call JSON, which the agent executes and returns as a `ToolMessage`. A subtle but important fix: you must call `bind_tools()` **before** `.with_retry()`. Reversing the order silently breaks tool binding.

## Evaluation Approach and Results

I created 20 test cases covering all four intent types:

- 5 SQL questions about orders, customers, and tickets.
- 7 RAG questions about returns, shipping, warranty, and contact policies.
- 5 action questions about weather, notifications, and ticket creation.
- 3 general greetings and identity questions.

`eval/run_eval.py` runs each case through the agent and checks:

- intent accuracy,
- keyword relevance in the final answer,
- SQL generation accuracy,
- RAG source grounding,
- action tool correctness,
- latency and error rate.

Latest results against `llama3.1` on a local CPU:

| Metric | Score |
|--------|-------|
| Intent Accuracy | 100% |
| Answer Relevance | 90% |
| SQL Generation Accuracy | 100% |
| RAG Source Grounding | 100% |
| Action Tool Accuracy | 100% |
| Error Rate | 0% |
| Avg Latency | ~9.9s |

The 90% answer-relevance score came from a couple of keyword mismatches — the answers were correct, but the exact expected phrase was not present. This is a good reminder that keyword-based evaluation is imperfect and that a semantic similarity scorer would be a useful next addition.

## Deployment and Monitoring

The Docker Compose stack includes PostgreSQL, ChromaDB, Ollama, and the FastAPI app. On first start, the Ollama container pulls the required models, so the initial launch is slow but self-contained.

The FastAPI app exposes a `/metrics` endpoint and logs every request with method, path, status, latency, and client IP. Optional LangSmith tracing is controlled by environment variables:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=otto
```

## Lessons Learned

1. **Small models need structure.** Few-shot examples, strict response formats, and small max token windows dramatically improved reliability.
2. **Safety cannot be prompt-only.** Keyword and regex checks after generation catch mistakes that prompts do not.
3. **Local LLMs are slower but liberating.** Once the retry/error-handling infrastructure is in place, the development loop is fast and free.
4. **Evaluation is a feature, not an afterthought.** Building `eval/run_eval.py` early forced me to think about what "good" means for each agent type.
5. **Caching is a cheap win.** A simple `lru_cache` on the agent runner dropped repeated-query latency to near zero.

## What I Would Do Differently

- Use a smaller/faster model for intent classification to reduce the per-request latency.
- Add a semantic answer-relevance scorer instead of relying only on keyword matching.
- Implement a real read-only Postgres user and query whitelisting in production.
- Swap `SqliteSaver` for a shared checkpointer store if horizontal scaling becomes a requirement.
- Add end-to-end Playwright or pytest-bdd tests for the Streamlit UI.

## Conclusion

Otto is not a toy. It has routing, memory, safety, observability, tests, linting, Docker, and an evaluation suite. More importantly, it is a reproducible, local-first blueprint for building agentic systems that can be extended to real support domains, internal tooling, or any scenario where grounded, multi-step reasoning is needed.

The full code is on GitHub. I am excited to apply these patterns to production use cases and to keep iterating as local models get faster and smaller.
