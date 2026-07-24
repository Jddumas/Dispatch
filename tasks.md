# Dispatch Tasks

## Current
- [ ] Week 9: Docker + Deployment

## Next
- [ ] Week 10: Streamlit Frontend
- [ ] Week 11: Optimization + Polish

## Backlog
- Week 12: README + Blog + Apply

## Done
- [x] Week 1 Day 1-2: Python Refresher — functions, classes, decorators, type hints
- [x] Week 1 Day 1-2: Async/await with asyncio and httpx
- [x] Week 1 Day 1-2: Pydantic data validation
- [x] Install Ollama locally, pull `llama3.1` and `nomic-embed-text`, clean up `llama3.2`
- [x] Add `experiments/04_basic_call.py` (Ollama basic call)
- [x] Add `experiments/05_streaming.py` (streaming responses)
- [x] Add `experiments/06_function_calling.py` (single tool call)
- [x] Add `experiments/07_agent_with_tools.py` (multi-tool agent loop)
- [x] Update project plan, README, requirements, `.env.example` to use Ollama
- [x] Initialize Git repository and commit Week 1 progress
- [x] Week 2: SQL + Database Setup
  - [x] Start PostgreSQL from EDB binaries locally
  - [x] Create `customers`, `orders`, and `support_tickets` schema
  - [x] Generate and load `data/seed_data.sql` (50+ rows per table)
  - [x] Practice 10 representative queries in `data/practice_queries.sql`
  - [x] Write `app/tools/database.py` with connection, query, and safe execution helpers
- [x] Week 3: RAG Pipeline
  - [x] Install `chromadb` and pull `nomic-embed-text`
  - [x] Create 13 knowledge base documents in `data/documents/`
  - [x] Write `app/tools/retriever.py` with load, chunk, embed, retrieve, and answer helpers
  - [x] Test `experiments/08_rag.py` with 6 grounded Q&A examples
- [x] Week 4: LangGraph Fundamentals
  - [x] Install `langgraph` and `langchain-ollama`
  - [x] Build a state-machine graph that classifies intent and routes to SQL, RAG, action, or general nodes
  - [x] Write `experiments/09_langgraph_basics.py`
  - [x] Test the graph with 5 representative inputs
- [x] Week 5: SQL Agent + Action Agent
  - [x] Write `app/agents/sql_agent.py` with safe, read-only SQL generation and natural-language result formatting
  - [x] Write `app/agents/action_agent.py` and `app/tools/api_client.py` (weather, notification, create support ticket)
  - [x] Write `app/agents/rag_agent.py` and `app/agents/router.py`; wire SQL/RAG/action/general branches into the Week 4 graph
  - [x] Run `experiments/10_week5_graph.py` end-to-end against PostgreSQL
- [x] Week 6: Memory + Error Handling
  - [x] Add SQLite `SqliteSaver` checkpointer and `thread_id`-based conversation memory
  - [x] Add `validate_input` guardrails and `fallback` node
  - [x] Add retries (`with_retry`) and try/except error handling around LLM, DB, RAG, and action calls
  - [x] Add logging throughout the agent modules
  - [x] Test multi-turn SQL/RAG conversations and edge cases in `experiments/11_week6_memory.py`
- [x] Week 7: FastAPI Backend
  - [x] Install `fastapi`, `uvicorn`, `slowapi`, `pydantic-settings`
  - [x] Write `app/main.py` with `/health`, `/chat`, `/chat/stream`, and `/sessions/{session_id}/history`
  - [x] Add CORS, rate limiting, and request/response logging middleware
  - [x] Use pydantic-settings in `app/config.py`
  - [x] Test endpoints with curl/httpx and Swagger at `/docs`
- [x] Week 8: LangSmith Tracing + Evaluation
  - [x] Add LangSmith env vars (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`) to `.env.example` and `app/config.py`
  - [x] Add `experiments/12_langsmith_trace.py` for tracing verification
  - [x] Create `eval/test_cases.json` with 20+ test cases
  - [x] Write `eval/run_eval.py` for intent, SQL, RAG, and action evaluation
  - [x] Run evaluation suite and save results JSON
