# Otto — Learning Journey Overview

This folder documents what was built in Otto, step by step. Each file explains one concept: what it is, how it was prototyped in the `experiments/` folder, and where it lives in the production app.

## The Big Picture

Otto is a multi-agent AI support system. A user asks a question in natural language; a classifier routes it to the right specialist; the specialist answers using a database, a knowledge base, or external tools; the answer streams back to the UI.

```
User (Streamlit)
    ↓ HTTP POST /chat/stream
FastAPI Backend
    ↓
LangGraph Router
    ├─ sql     → SQL Agent     → PostgreSQL
    ├─ rag     → RAG Agent     → ChromaDB (vector search)
    ├─ action  → Action Agent  → External tools (weather, tickets)
    └─ general → LLM           → Direct answer
```

## Learning Path

| Step | Concept | Experiment(s) | Production file(s) | Teaching doc |
|------|---------|---------------|---------------------|--------------|
| 1 | Python foundations | 01, 02, 03 | `app/config.py`, `app/main.py` | [01_python_foundations](01_python_foundations.md) |
| 2 | Basic LLM calls + streaming | 04, 05 | `app/llm.py`, `/chat/stream` | [02_llm_basics](02_llm_basics.md) |
| 3 | Tool calling + agentic loop | 06, 07 | `app/agents/action_agent.py` | [03_tool_calling](03_tool_calling.md) |
| 4 | RAG pipeline | 08 | `app/tools/retriever.py`, `app/agents/rag_agent.py` | [04_rag_pipeline](04_rag_pipeline.md) |
| 5 | LangGraph state machine | 09, 10 | `app/agents/router.py` | [05_langgraph](05_langgraph.md) |
| 6 | SQL agent + safety | — | `app/agents/sql_agent.py` | [06_sql_agent](06_sql_agent.md) |
| 7 | Conversation memory | 11 | `app/agents/router.py` (SqliteSaver) | [07_memory](07_memory.md) |
| 8 | FastAPI + streaming API | — | `app/main.py` | [08_api_and_streaming](08_api_and_streaming.md) |
| 9 | Evaluation + observability | 12 | `eval/run_eval.py`, `eval/test_cases.json` | [09_evaluation](09_evaluation.md) |
| 10 | Docker + deployment | — | `docker-compose.yml`, `render.yaml` | [10_deployment](10_deployment.md) |

## How the pieces fit together

Each experiment proves out an isolated concept. Once it worked, the concept was refactored into the production `app/` module with proper error handling, configuration, logging, and testing. The pattern:

```
experiments/XX_concept.py   ← quick, no error handling, hardcoded values
        ↓
app/agents/ or app/tools/   ← production version: config-driven, logged, tested
```

For interview prep, go to [docs/interview.md](../interview.md).
