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

## Reporting Requirement
After completing each task or group of related tasks, produce a **detailed report** that includes:
1. **What was completed** — specific files changed, commands run, and outcomes.
2. **Verification** — how you confirmed the change works (e.g., script output, lint, test, `git status`).
3. **Current state** — where the project stands against `tasks.md`.
4. **Next steps** — the immediate next 1–3 tasks to do, pulled from `tasks.md`.

Also keep `tasks.md` and the session todo list in sync as work progresses.
