# Dispatch Tasks

## Current
- [ ] Week 5: SQL Agent + Action Agent
  - [ ] Design a robust SQL node that converts natural language to safe, parameterized SQL
  - [ ] Add tool definitions and a ToolNode for real actions (e.g., get_weather, update_order_status)
  - [ ] Integrate the SQL and action branches into the Week 4 graph

## Next
- [ ] Week 6: Memory + Error Handling
- [ ] Week 7: FastAPI Backend
- [ ] Week 8: LangSmith Tracing + Evaluation

## Backlog
- Week 6: Memory + Error Handling
- Week 7: FastAPI Backend
- Week 8: LangSmith Tracing + Evaluation
- Week 9: Docker + Deployment
- Week 10: Streamlit Frontend
- Week 11: Optimization + Polish
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
