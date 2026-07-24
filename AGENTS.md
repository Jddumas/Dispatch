# Dispatch AI — Agent Rules

## Project Context
- This is the **Dispatch AI** multi-agent support system.
- Stack: Python 3.13, LangGraph, FastAPI, PostgreSQL, ChromaDB, Docker, Streamlit, Ollama (local LLM).
- Active Python environment: `venv` (`.\venv\Scripts\activate` on Windows). Because each shell session is fresh, use `.\venv\Scripts\python.exe` and `.\venv\Scripts\python.exe -m pip` directly instead of relying on activation persisting.
- Ollama is installed locally at `C:\Users\Jacob_Dumas\AppData\Local\Programs\Ollama` and `llama3.2` is pulled.
- PostgreSQL 15 is running from a local `pgsql/` binary tree (extracted from the EDB Windows binaries zip). Start/stop commands:
  - Start: `.\pgsql\pgsql\bin\pg_ctl.exe -D "$PWD\pgsql\data" -l "$PWD\pgsql\logfile" start`
  - Stop: `.\pgsql\pgsql\bin\pg_ctl.exe -D "$PWD\pgsql\data" stop`
  - The `support_agent` database, `agent` user, and seeded tables are already created.
- Conversation state is persisted in `data/checkpoints.sqlite` using LangGraph's `SqliteSaver`. Use a consistent `thread_id` for multi-turn conversations; see `experiments/11_week6_memory.py`.
- FastAPI backend lives in `app/main.py`. Start it with `.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` and test with curl/httpx against `/health`, `/chat`, `/chat/stream`, and `/sessions/{session_id}/history`.
- LangSmith tracing is configured through `.env`: set `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_API_KEY`, and `LANGCHAIN_PROJECT`. Run `experiments/12_langsmith_trace.py` to verify.
- Evaluation suite lives in `eval/`: edit `eval/test_cases.json` and run `.\venv\Scripts\python.exe eval/run_eval.py`. Results are saved to `eval/results/`.
- Docker support is in `Dockerfile` and `docker-compose.yml`. Run `docker compose up --build -d` to start the full stack (PostgreSQL, ChromaDB, Ollama, and the FastAPI app). The first startup pulls `llama3.1` and `nomic-embed-text` into the Ollama container and can take several minutes. The app auto-indexes the knowledge base into ChromaDB on startup if the collection is empty.

## Reporting Requirement
After completing each task or group of related tasks, produce a **detailed report** that includes:
1. **What was completed** — specific files changed, commands run, and outcomes.
2. **Verification** — how you confirmed the change works (e.g., script output, lint, test, `git status`).
3. **Current state** — where the project stands against `tasks.md`.
4. **Next steps** — the immediate next 1–3 tasks to do, pulled from `tasks.md`.

Also keep `tasks.md` and the session todo list in sync as work progresses.
