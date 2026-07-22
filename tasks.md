# Dispatch Tasks

## Current
- [ ] Week 3: RAG Pipeline
  - [ ] Install `chromadb` and an Ollama embedding model (e.g., `nomic-embed-text`)
  - [ ] Create 10-15 markdown/text files in `data/documents/` simulating a company knowledge base
  - [ ] Write `app/tools/retriever.py` to load, chunk, embed, and retrieve documents
  - [ ] Combine retrieval with `llama3.1` to answer questions grounded in the documents

## Next
- [ ] Index sample documents and test 5+ RAG questions
- [ ] Week 4: LangGraph Fundamentals
- [ ] Week 5: SQL Agent + Action Agent

## Backlog
- Week 4: LangGraph Fundamentals
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
- [x] Install Ollama locally, pull `llama3.1`, and clean up `llama3.2` / installer
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
