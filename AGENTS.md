# Dispatch AI — Agent Rules

## Project Context

- This is the **Dispatch AI** multi-agent support system.
- Stack: Python 3.13, LangGraph, FastAPI, PostgreSQL, ChromaDB, Docker, Streamlit, Ollama (local LLM).
- Active Python environment: `venv`. Because each shell session is fresh, use `.\venv\Scripts\python.exe` and `.\venv\Scripts\python.exe -m pip` directly instead of relying on activation persisting.
- Ollama is installed locally and the project uses `llama3.1` (generation) and `nomic-embed-text` (embeddings).
- PostgreSQL 15 can run from the local `pgsql/` binary tree or from the Docker Compose stack.
- Conversation state is persisted in `data/checkpoints.sqlite` using LangGraph's `SqliteSaver`. Use a consistent `thread_id` / `session_id` for multi-turn conversations.

## Common Commands

### Backend
```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend
```powershell
$env:API_URL='http://127.0.0.1:8000'
.\venv\Scripts\python.exe -m streamlit run frontend/streamlit_app.py
```

### Docker (full stack)
```powershell
docker compose up --build -d
```

### Evaluation
```powershell
.\venv\Scripts\python.exe -m eval.run_eval
```

### Linting and Tests
```powershell
.\venv\Scripts\python.exe -m ruff check app frontend eval tests
.\venv\Scripts\python.exe -m pytest tests -v
```

### LangSmith Tracing
Set in `.env`:
```text
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=dispatch-ai
```
Then run `experiments/12_langsmith_trace.py` to verify traces appear.

## Key Project Files

- `app/main.py` — FastAPI backend with `/health`, `/chat`, `/chat/stream`, `/sessions/{id}/history`, and `/metrics`.
- `app/agents/router.py` — LangGraph router, `run_agent()`, and `get_thread_history()`.
- `app/agents/sql_agent.py` — Safe SQL generation and execution.
- `app/agents/rag_agent.py` — RAG answer synthesis with source extraction.
- `app/agents/action_agent.py` — Tool-calling agent.
- `app/tools/retriever.py` — ChromaDB + Ollama embeddings for RAG.
- `frontend/streamlit_app.py` — Chat UI.
- `eval/run_eval.py` and `eval/test_cases.json` — Evaluation suite.
- `tests/` — pytest unit tests.
- `docs/architecture.md` — System architecture.
- `docs/blog_post.md` — Build journal / blog draft.
- `README.md` — Public-facing project overview and quick start.

## Reporting Requirement

After completing each task or group of related tasks, produce a **detailed report** that includes:
1. **What was completed** — specific files changed, commands run, and outcomes.
2. **Verification** — how you confirmed the change works (e.g., script output, lint, test, `git status`).
3. **Current state** — where the project stands against `tasks.md`.
4. **Next steps** — the immediate next 1–3 tasks to do, pulled from `tasks.md`.

Also keep `tasks.md` and the session todo list in sync as work progresses.
