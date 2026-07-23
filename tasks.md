# Dispatch Tasks

## Current
- [ ] Week 4: LangGraph Fundamentals
  - [ ] Install `langgraph` and sketch the multi-agent graph structure
  - [ ] Build a simple state-machine graph: classify user intent -> route to SQL, RAG, or action node
  - [ ] Write `experiments/09_langgraph_basics.py` to demonstrate the graph

## Next
- [ ] Week 5: SQL Agent + Action Agent
- [ ] Week 6: Memory + Error Handling
- [ ] Week 7: FastAPI Backend

## Backlog
- Week 5: SQL Agent + Action Agent
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
- [x] Week 3: RAG Pipeline
  - [x] Install `chromadb` and pull `nomic-embed-text`
  - [x] Create 13 knowledge base documents in `data/documents/`
  - [x] Write `app/tools/retriever.py` with load, chunk, embed, retrieve, and answer helpers
  - [x] Test `experiments/08_rag.py` with 6 grounded Q&A examples
