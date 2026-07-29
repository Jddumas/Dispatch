# Dispatch AI — Agent Rules

## Project Context

- **Dispatch AI** is a multi-agent customer support assistant.
- Stack: Python 3.13, LangGraph, FastAPI, PostgreSQL, ChromaDB, Streamlit, Groq API.
- LLM: `llama-3.3-70b-versatile` (main), `llama-3.1-8b-instant` (classifier) via Groq.
- Embeddings: `nomic-embed-text` via Ollama (local).
- Virtual environment: `venv/`. Activate with `source venv/bin/activate`.
- Backend runs on port **8002** (port 8000 is taken by another project).
- Conversation state persists in `data/checkpoints.sqlite` via LangGraph `SqliteSaver`.

## Common Commands

### Backend
```bash
source venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

### Frontend
```bash
API_URL=http://localhost:8002 venv/bin/python -m streamlit run frontend/streamlit_app.py --server.port 8501 --server.headless true
```

### Docker (full stack)
```bash
docker compose up --build -d
```

### Tests and Linting
```bash
source venv/bin/activate
python -m ruff check app frontend eval tests
python -m pytest tests -v
```

### Evaluation
```bash
source venv/bin/activate
python -m eval.run_eval
```

## Key Files

- `app/main.py` — FastAPI backend: `/health`, `/chat`, `/chat/stream`, `/sessions/{id}/history`
- `app/agents/router.py` — LangGraph graph, intent classifier, `run_agent()`
- `app/agents/sql_agent.py` — SQL generation, execution, Customer 360 profile builder
- `app/agents/rag_agent.py` — RAG answer synthesis via ChromaDB
- `app/agents/action_agent.py` — Tool-calling agent (weather, tickets, orders)
- `app/agents/hybrid_agent.py` — SQL + RAG fan-out with LLM synthesis
- `app/tools/api_client.py` — Action tools (lookup_order, close_ticket, etc.)
- `app/tools/retriever.py` — ChromaDB retrieval with Ollama embeddings
- `frontend/streamlit_app.py` — Streamlit chat UI with Customer 360 card rendering
- `data/documents/` — 25 markdown files that make up the RAG knowledge base
- `eval/` — Evaluation suite (`run_eval.py`, `test_cases.json`)
- `tests/` — pytest unit tests
- `docs/` — Architecture, blog post, interview notes, teaching materials
