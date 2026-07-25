# 🤖 Dispatch AI

A production-ready multi-agent AI support system built with **LangGraph**, **FastAPI**, **PostgreSQL**, **ChromaDB**, and **Ollama**. It routes customer questions to specialized agents for knowledge-base Q&A, safe SQL queries, automated actions, and general conversation — with conversation memory, streaming responses, and observability built in.

> **Note:** This project uses local LLMs via Ollama by default. It also supports Groq and OpenAI for faster cloud deployments, and `fastembed` for CPU embeddings when Ollama is not available.

## Live Demo

- Chat UI: *[Streamlit app URL to be added after deployment]*
- API Base: *[Render URL to be added after deployment]*
- API Docs: `http://localhost:8000/docs` (when running locally)

## Features

- **Multi-agent routing** — an LLM classifier routes each question to the right specialist agent (`sql`, `rag`, `action`, or `general`).
- **RAG-powered knowledge base** — answers policy and product questions from a markdown document collection, with source attribution.
- **Natural language to SQL** — generates safe, read-only PostgreSQL queries and returns concise natural-language summaries.
- **Automated action execution** — uses tool calling to fetch weather, send notifications, and create support tickets.
- **Conversation memory** — persists multi-turn state with `thread_id` using LangGraph's `SqliteSaver`.
- **Streaming responses** — Server-Sent Events endpoint for a typing effect in the UI.
- **FastAPI backend** — `/health`, `/chat`, `/chat/stream`, `/sessions/{id}/history`, and `/metrics`.
- **Rate limiting, CORS, and request logging** — production middleware configured out of the box.
- **Evaluation suite** — 20 test cases covering intent classification, SQL safety, RAG relevance, and action accuracy.
- **LangSmith tracing** — optional tracing by setting environment variables.
- **Docker support** — `docker-compose.yml` spins up PostgreSQL, ChromaDB, Ollama, and the FastAPI app.

## Architecture

See the full architecture write-up in [`docs/architecture.md`](docs/architecture.md).

```mermaid
graph TD
    U[User / Streamlit Frontend] -->|HTTP POST /chat| F[FastAPI Backend]
    F -->|thread_id + SqliteSaver| S[(SQLite Checkpoints)]
    F -->|invoke| R[LangGraph Router]
    R -->|intent: sql| SQL[SQL Agent]
    R -->|intent: rag| RAG[RAG Agent]
    R -->|intent: action| ACT[Action Agent]
    R -->|intent: general| GEN[General Node]
    SQL -->|safe SELECT| PG[(PostgreSQL)]
    RAG -->|retrieve| CH[(ChromaDB + Ollama Embeddings)]
    ACT -->|tool calls| API[Mock APIs]
    GEN -->|LLM| OLL[Ollama]
    SQL -->|LLM| OLL
    RAG -->|LLM| OLL
    ACT -->|LLM| OLL
    F -->|traces| LS[LangSmith]
```

## Tech Stack

Python 3.13 | LangGraph | FastAPI | PostgreSQL | ChromaDB | Ollama | Streamlit | Docker | LangSmith

## Evaluation Results

Run the suite yourself with:

```bash
python -m eval.run_eval
```

Latest run (`llama3.1` on a local CPU):

| Metric                       | Score    |
|------------------------------|----------|
| Intent Accuracy              | 100.0%   |
| Answer Relevance             | 96.6%    |
| SQL Generation Accuracy      | 100.0%   |
| RAG Source Grounding         | 100.0%   |
| Action Tool Accuracy         | 100.0%   |
| Error Rate                   | 0.0%     |
| Average Latency              | ~10.6s   |

## Quick Start

### Prerequisites

- Python 3.13
- [Ollama](https://ollama.com) installed and running
- [PostgreSQL](https://www.postgresql.org) running locally, or Docker

### Local Setup

1. Clone the repo and create a virtual environment:

```bash
git clone <repo-url>
cd dispatch
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

3. Copy environment variables and start Postgres/Ollama:

```bash
# Linux/Mac:
cp .env.example .env
# Windows PowerShell:
Copy-Item .env.example .env

# Make sure Ollama has the required models:
ollama pull llama3.1
ollama pull nomic-embed-text
```

4. Start the FastAPI backend:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

5. Open the interactive docs at `http://127.0.0.1:8000/docs`.

### Streamlit Frontend

In a new terminal:

```bash
# Windows
$env:API_URL="http://127.0.0.1:8000"
python -m streamlit run frontend/streamlit_app.py

# Linux/Mac
API_URL=http://127.0.0.1:8000 python -m streamlit run frontend/streamlit_app.py
```

Then open `http://localhost:8501`.

### Docker

> First startup pulls the Ollama models and may take several minutes.

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

The repository includes a `render.yaml` blueprint for [Render](https://render.com). It uses **Groq** for fast, hosted LLM inference and **FastEmbed** for CPU embeddings so the app runs on Render's free/CPU tier.

### Render (backend)

1. Make sure the repo is pushed to GitHub.
2. Create a Render account and install the [Render CLI](https://render.com/docs/cli).
3. Set the Groq API key in your shell:

```bash
export GROQ_API_KEY=gsk_...
```

4. Deploy:

```bash
render blueprint apply render.yaml
# or click the Render dashboard "New +" -> "Blueprint" and select render.yaml
```

5. After the service is live, copy the service URL (e.g. `https://dispatch-api-xxx.onrender.com`) and add it to the Streamlit Cloud secrets as `API_URL`.

### Streamlit Community Cloud (frontend)

1. Push the repo to GitHub.
2. Go to [Streamlit Community Cloud](https://streamlit.io/cloud) and create a new app.
3. Select `frontend/streamlit_app.py` as the main file.
4. In the app settings/secrets, add:

```toml
API_URL = "https://dispatch-api-xxx.onrender.com"
```

5. Deploy and update the **Live Demo** URLs above.

### Switching LLM providers locally

Set the provider in `.env`:

```bash
# Ollama (default)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1

# Groq
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
LLM_MODEL=llama-3.1-8b-instant
CLASSIFY_MODEL=llama-3.1-8b-instant

# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```

## Example Questions to Try

The Streamlit sidebar includes a categorized bank of one-click example prompts. You can also type these directly into the chat:

- **RAG / Policy:**
  - "What is the return policy?"
  - "What payment methods do you accept?"
  - "How does the loyalty program work?"
  - "What does the account security documentation say about two-factor authentication?"

- **SQL / Account:**
  - "How many orders are there?"
  - "What is total revenue by product category?"
  - "Which customers have an open ticket and a returned order?"
  - "Who are the top 5 customers by spend in the last 90 days?"
  - "What is the average order value?"

- **Action:**
  - "What is the weather in Paris?"
  - "Create a support ticket for customer 2 about order 3"
  - "Send a notification to team@example.com about order 5"

- **General:**
  - "What can you do?"
  - "Hello!"

## Project Structure

```
dispatch/
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
│   ├── config.py            # Centralized pydantic-settings config
│   ├── agents/
│   │   ├── router.py        # LangGraph router + graph compile
│   │   ├── rag_agent.py     # RAG node
│   │   ├── sql_agent.py     # SQL generation + safety
│   │   ├── action_agent.py  # Tool-calling agent
│   │   └── state.py         # AgentState TypedDict
│   └── tools/
│       ├── retriever.py     # ChromaDB + Ollama RAG
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

## Blog Post

Read the build journal: *[blog post URL to be added]*

## License

MIT — feel free to fork and adapt for your own projects.
