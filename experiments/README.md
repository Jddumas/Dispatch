# Experiments

Each script in this folder is a standalone proof-of-concept that was built before its concept was integrated into the production app. Run any of them with the venv active from the project root.

| File | Concept | Teaching doc | Production home |
|------|---------|--------------|-----------------|
| `01_functions_classes_decorators.py` | Python foundations — type hints, classes, decorators | [01_python_foundations](../docs/teachings/01_python_foundations.md) | `app/agents/*.py` (retry logic, type hints throughout) |
| `02_async_await.py` | Async/await, `asyncio.gather`, rate limiting | [01_python_foundations](../docs/teachings/01_python_foundations.md) | `app/main.py` (async FastAPI endpoints) |
| `03_pydantic_validation.py` | Pydantic models, field validators, config | [01_python_foundations](../docs/teachings/01_python_foundations.md) | `app/main.py` (`ChatRequest`, `ChatResponse`), `app/config.py` |
| `04_basic_call.py` | First LLM call with Ollama | [02_llm_basics](../docs/teachings/02_llm_basics.md) | `app/llm.py` (`get_llm()`) |
| `05_streaming.py` | Streaming LLM responses token-by-token | [02_llm_basics](../docs/teachings/02_llm_basics.md) | `app/main.py` (`/chat/stream` endpoint) |
| `06_function_calling.py` | Single tool call — model decides when to call it | [03_tool_calling](../docs/teachings/03_tool_calling.md) | `app/agents/action_agent.py` (`run_action_agent`) |
| `07_agent_with_tools.py` | Multi-tool agentic loop | [03_tool_calling](../docs/teachings/03_tool_calling.md) | `app/agents/action_agent.py` (`_execute_tool`, `TOOLS`) |
| `08_rag.py` | Full RAG pipeline — index, retrieve, answer | [04_rag_pipeline](../docs/teachings/04_rag_pipeline.md) | `app/tools/retriever.py`, `app/agents/rag_agent.py` |
| `09_langgraph_basics.py` | LangGraph state machine with 4-way routing | [05_langgraph](../docs/teachings/05_langgraph.md) | `app/agents/router.py` |
| `10_week5_graph.py` | Full integrated graph — all 4 agents | [05_langgraph](../docs/teachings/05_langgraph.md) | `app/agents/router.py` |
| `11_week6_memory.py` | Multi-turn conversation memory via `thread_id` | [07_memory](../docs/teachings/07_memory.md) | `app/agents/router.py` (`SqliteSaver`), `app/main.py` |
| `12_langsmith_trace.py` | LangSmith observability and tracing | [09_evaluation](../docs/teachings/09_evaluation.md) | `app/config.py` (tracing env vars) |

## Running an experiment

```bash
source venv/bin/activate
python experiments/04_basic_call.py
```

Experiments that import from `app/` (08 onward) require PostgreSQL and Ollama to be running.
