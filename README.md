# Dispatch AI

A production-ready multi-agent AI system built with LangGraph, FastAPI, and PostgreSQL.

## Project Setup

### Virtual Environment

This project uses a Python virtual environment. To activate it:

**Windows:**
```bash
.\venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

Once activated, you'll see `(venv)` in your command prompt.

### Installing Dependencies

```bash
pip install -r requirements.txt
```

## Week 1 Progress

### Day 1-2: Python Refresher

Completed practice exercises:
- ✅ Functions, classes, decorators, type hints
- ✅ Async/await with asyncio and httpx
- ✅ Pydantic data validation

Practice files are in the `experiments/` directory:
- `01_functions_classes_decorators.py`
- `02_async_await.py`
- `03_pydantic_validation.py`

## Tech Stack

- Python 3.13
- LangGraph (agent orchestration)
- FastAPI (backend)
- PostgreSQL (relational data)
- ChromaDB (vector store)
- Docker (containerization)
- Local or cloud deployment (e.g., Railway, Render, or self-hosted)
- Streamlit (frontend)
- LangSmith (tracing and evaluation) — optional
- Ollama (local LLM)

## Project Structure

```
dispatch-ai/
├── README.md
├── .env
├── .gitignore
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── app/
│   ├── main.py
│   ├── agents/
│   │   ├── router.py
│   │   ├── rag_agent.py
│   │   ├── sql_agent.py
│   │   └── action_agent.py
│   ├── tools/
│   │   ├── retriever.py
│   │   ├── database.py
│   │   └── api_client.py
│   ├── config.py
│   └── models.py
├── data/
│   ├── documents/
│   └── seed_data.sql
├── eval/
│   ├── test_cases.json
│   └── run_eval.py
├── frontend/
│   └── streamlit_app.py
└── docs/
    └── architecture.md
```

## Build Plan

This project follows a 12-week build plan. See `project_plan.md` for details.
