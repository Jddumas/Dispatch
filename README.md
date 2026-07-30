# 🤖 Otto - Internal Support Assistant

A production-ready multi-agent AI support system built with **LangGraph**, **FastAPI**, **PostgreSQL**, **ChromaDB**, and **Groq**. It validates and classifies each user message with a confidence score, routes it to a specialized agent, and asks a clarifying question when intent is ambiguous — with conversation memory, streaming responses, user feedback, and observability built in.

## Live Demo

- Chat UI: https://otto-support.streamlit.app
- API Base: https://otto-api-qsk6.onrender.com
- API Docs: https://otto-api-qsk6.onrender.com/docs

## Features

- **Confidence-scored routing** — the classifier returns an intent label and a confidence score; low-confidence requests are sent to a clarify node that asks the user a follow-up question before invoking a specialist.
- **Input validation** — empty messages, oversized input, and blocked keywords are rejected before any LLM call.
- **Multi-agent routing** — routes to `sql`, `rag`, `action`, `hybrid`, or `general` agents based on classified intent.
- **RAG-powered knowledge base** — answers policy and product questions from a markdown document collection, with source attribution.
- **Natural language to SQL** — generates safe, read-only PostgreSQL queries and returns concise natural-language summaries with human-readable column labels.
- **Hybrid agent** — handles questions that require both live database data and policy knowledge (e.g., eligibility checks, loyalty tier lookups).
- **Automated action execution** — uses tool calling to fetch weather, send notifications, and create/update/close support tickets.
- **User feedback loop** — 👍/👎 buttons on every assistant reply; thumbs-down opens a text reason box; ratings are stored in PostgreSQL.
- **Conversation memory** — persists multi-turn state with `thread_id` using LangGraph's `SqliteSaver`.
- **Session persistence** — session ID stored in the URL query string so conversations survive page reloads.
- **Streaming responses** — Server-Sent Events endpoint for a typing effect in the UI.
- **FastAPI backend** — `/health`, `/chat`, `/chat/stream`, `/sessions/{id}/history`, `/metrics`, and `/feedback`.
- **Rate limiting, CORS, and request logging** — production middleware configured out of the box.
- **Evaluation suite** — test cases covering intent classification, SQL safety, RAG relevance, and action accuracy.
- **LangSmith tracing** — optional tracing by setting environment variables.
- **Docker support** — `docker-compose.yml` spins up PostgreSQL, ChromaDB, and the FastAPI app.

## Architecture

See the full write-up in [`docs/architecture.md`](docs/architecture.md).

```mermaid
graph TD
    U[User / Streamlit Frontend] -->|HTTP POST /chat or /chat/stream| F[FastAPI Backend]
    F -->|thread_id + SqliteSaver| S[(SQLite Checkpoints)]
    F -->|invoke| V[Validate Node]
    V -->|invalid input| FB[Fallback Node]
    V -->|valid| C[Classify Node]
    C -->|confidence ≥ 0.7| R{Route}
    C -->|confidence < 0.7| CL[Clarify Node]
    R -->|sql| SQL[SQL Agent]
    R -->|rag| RAG[RAG Agent]
    R -->|action| ACT[Action Agent]
    R -->|hybrid| HYB[Hybrid Agent]
    R -->|general| GEN[General Node]
    SQL -->|safe SELECT| PG[(PostgreSQL)]
    RAG -->|retrieve| CH[(ChromaDB)]
    HYB -->|safe SELECT + retrieve| PG & CH
    ACT -->|tool calls| API[Mock APIs]
    SQL & RAG & ACT & HYB & GEN & CL & FB --> FMT[Format Node]
    F -->|POST /feedback| PG
    F -->|traces| LS[LangSmith]
```

## Tech Stack

Python 3.13 | LangGraph | FastAPI | PostgreSQL | ChromaDB | Groq | Streamlit | Docker | LangSmith

## Evaluation Results

Run the suite yourself with:

```bash
python -m eval.run_eval
```

| Metric                       | Score    |
|------------------------------|----------|
| Intent Accuracy              | 100.0%   |
| Answer Relevance             | 96.6%    |
| SQL Generation Accuracy      | 100.0%   |
| RAG Source Grounding         | 100.0%   |
| Action Tool Accuracy         | 100.0%   |
| Error Rate                   | 0.0%     |

## Quick Start

### Prerequisites

- Python 3.13
- [PostgreSQL](https://www.postgresql.org) running locally, or Docker
- A [Groq API key](https://console.groq.com) (free tier available)

### Local Setup

1. Clone the repo and create a virtual environment:

```bash
git clone <repo-url>
cd otto
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy and configure environment variables:

```bash
# Linux/Mac:
cp .env.example .env
# Windows PowerShell:
Copy-Item .env.example .env
```

Edit `.env` and set at minimum:

```bash
GROQ_API_KEY=gsk_...
DATABASE_URL=postgresql://user:password@localhost:5432/otto
```

4. Start the FastAPI backend:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

5. Open the interactive docs at `http://127.0.0.1:8000/docs`.

### Streamlit Frontend

In a new terminal:

```bash
# Linux/Mac
API_URL=http://127.0.0.1:8000 python -m streamlit run frontend/streamlit_app.py

# Windows
$env:API_URL="http://127.0.0.1:8000"
python -m streamlit run frontend/streamlit_app.py
```

Then open `http://localhost:8501`.

### Docker

```bash
docker compose up --build -d
```

The API will be available at `http://localhost:8000` and ChromaDB at `http://localhost:8001`.

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Linting
ruff check app frontend eval tests

# Unit tests
pytest tests -v
```

## Deployment

The repository includes a `render.yaml` blueprint for [Render](https://render.com). It uses **Groq** for fast hosted LLM inference and **FastEmbed** for CPU embeddings so the app runs on Render's free/CPU tier.

### Render (backend)

1. Push the repo to GitHub.
2. Set the Groq API key in your shell: `export GROQ_API_KEY=gsk_...`
3. Deploy via the Render dashboard: New → Blueprint → select `render.yaml`.
4. After the service is live, copy the service URL and add it to Streamlit Cloud secrets as `API_URL`.

### Streamlit Community Cloud (frontend)

1. Push the repo to GitHub.
2. Go to [Streamlit Community Cloud](https://streamlit.io/cloud) and create a new app.
3. Select `frontend/streamlit_app.py` as the main file.
4. In app settings/secrets, add:

```toml
API_URL = "https://your-render-service.onrender.com"
```

### Switching LLM providers

Set the provider in `.env`:

```bash
# Groq (default)
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
LLM_MODEL=llama-3.3-70b-versatile
CLASSIFY_MODEL=llama-3.1-8b-instant

# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Ollama (local)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
```

## Example Questions to Try

The Streamlit sidebar includes a categorized bank of one-click example prompts.

- **Customer 360:**
  - "Tell me about Sarah Chen"
  - "Give me the customer card for Emily Torres"
  - "What loyalty tier is Marcus Johnson and what discount does he get?"
  - "Is customer 5 eligible for a warranty claim on their last order?"

- **SQL / Analytics:**
  - "How many orders are there?"
  - "What is total revenue by product category?"
  - "Which customers have an open ticket and a returned order?"
  - "Who are the top 5 customers by spend in the last 90 days?"

- **RAG / Policy:**
  - "What is the return policy?"
  - "What payment methods do you accept?"
  - "How does the loyalty program work?"

- **Action:**
  - "What is the weather in Paris?"
  - "Create a support ticket for customer 2 about order 3"
  - "Close ticket 12 with note: replacement shipped"

- **General:**
  - "What can you do?"
  - "Hello!"

## Project Structure

```
otto/
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── docker-compose.yml
├── Dockerfile
├── .dockerignore
├── app/
│   ├── main.py              # FastAPI app + endpoints
│   ├── config.py            # Centralized config (pydantic-settings)
│   ├── agents/
│   │   ├── router.py        # LangGraph graph: validate → classify → route → format
│   │   ├── rag_agent.py     # RAG node
│   │   ├── sql_agent.py     # SQL generation + safety
│   │   ├── action_agent.py  # Tool-calling agent
│   │   ├── hybrid_agent.py  # SQL + RAG combined agent
│   │   └── state.py         # AgentState TypedDict
│   └── tools/
│       ├── retriever.py     # ChromaDB RAG retrieval
│       ├── database.py      # PostgreSQL helpers
│       └── api_client.py    # Mock action tools
├── data/
│   ├── documents/           # Markdown knowledge base
│   ├── seed_data.sql        # Postgres seed data
│   └── checkpoints.sqlite   # LangGraph conversation memory
├── eval/
│   ├── test_cases.json      # Evaluation cases
│   └── run_eval.py          # Evaluation runner
├── experiments/             # Week-by-week learning scripts
├── frontend/
│   └── streamlit_app.py     # Chat UI
├── tests/                   # pytest suite
├── docs/
│   └── architecture.md      # System design docs
└── AGENTS.md                # Agent rules and dev notes
```

## Running the Test Suite

Otto ships with two complementary test layers:

### 1. Unit tests (`pytest`)

Fast, mocked, no external services. Run in under a second — safe for CI.

```bash
python -m pytest tests/ -v
```

Covers: API endpoints, retriever chunking, router intent classification, SQL safety guards, and answer formatting.

### 2. End-to-end evaluation (`eval/run_eval.py`)

Runs every case in `eval/test_cases.json` through the real agent — real Groq calls, real ChromaDB retrieval, real PostgreSQL queries. Takes 1–2 minutes and consumes API credits.

```bash
python -m eval.run_eval
```

The runner **resets the database from `data/seed_data.sql` before and after** the run, so destructive test cases (creating tickets, updating/closing ticket 82, etc.) always start from and return to a clean state. Results are saved to `eval/results/eval_<timestamp>.json` and a summary is printed to stdout.

Every example question in the Streamlit sidebar has a matching case in `test_cases.json` across five categories: Customer 360°, RAG, SQL, Actions, and Hybrid.

### Resetting the demo manually

The `POST /admin/reset-db` endpoint (rate-limited 5/min) re-seeds Postgres on demand. The Streamlit UI calls it automatically on every fresh page load, and the sidebar's **Reset demo** button triggers it mid-session.

```bash
curl -X POST http://localhost:8000/admin/reset-db
```

## License

MIT — feel free to fork and adapt for your own projects.
