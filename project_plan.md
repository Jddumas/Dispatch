
Here is the full plan. Select all, copy, and paste into any text editor. Save as `dispatch-ai-build-plan.md` or `.txt`.

---

```
================================================================================
DISPATCH AI — 12-WEEK BUILD PLAN
Steady Schedule: 10-12 hrs/week
================================================================================


OVERVIEW
--------
Goal: Build and deploy one multi-agent AI system that covers 90% of the
job requirements.

Final Product: "Dispatch" — A deployed AI Support Agent with RAG, SQL, and
API tool capabilities, complete with evaluation, monitoring, a live demo,
and a blog post.

Tech Stack:
- Python 3.11+
- LangGraph (agent orchestration)
- FastAPI (backend)
- PostgreSQL (relational data)
- ChromaDB (vector store)
- Docker (containerization)
- Local or cloud deployment (e.g., Railway, Render, or self-hosted)
- Streamlit (frontend)
- LangSmith (tracing and evaluation) — optional
- Ollama (local LLM)
- GitHub (version control and portfolio)

GitHub Repo Name: dispatch-ai


================================================================================
PRE-WORK (Before Week 1)
================================================================================

Setup Checklist:
[x] Install Python 3.11+ and set up a virtual environment manager (venv or conda)
[ ] Install VS Code with Python extensions
[x] Create a GitHub account (if needed) and set up Git locally
[x] Set up Ollama locally:
    [x] Install Ollama from https://ollama.com
    [x] Pull a chat model (e.g., `ollama pull llama3.2`)
    [x] Verify the server is running at http://localhost:11434
[ ] Create a LangSmith account (https://smith.langchain.com) — free tier (optional, for tracing)
[ ] Install Docker Desktop
[x] Install PostgreSQL locally (or use Docker for it)
[x] Create a new GitHub repository called "dispatch-ai"


Folder Structure:

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


================================================================================
WEEK 1: PYTHON + LLM API FUNDAMENTALS
================================================================================
Hours: 10-12
Goal: Get comfortable calling LLMs from Python and handling responses.


Day 1-2: Python Refresher (3 hrs)
[x] Review/practice: functions, classes, decorators, type hints
[x] Practice async/await with asyncio and httpx
[x] Learn pydantic for data validation (BaseModel, Field, validators)
    Resource: https://docs.pydantic.dev/latest/concepts/models/


Day 3-4: LLM API Basics (4 hrs)
[x] Install the ollama Python client
[x] Write a script that sends a prompt and prints the response
[x] Experiment with parameters: temperature, max_tokens, system prompt
[x] Implement streaming responses (print tokens as they arrive)
[x] Try function calling: define a tool schema and get the model to call it
[x] Save all experiments in a notebooks/ or experiments/ folder

Example code — basic_call.py:

    import ollama

    response = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is RAG in AI?"}
        ]
    )
    print(response["message"]["content"])


Day 5: Function Calling Deep Dive (3 hrs)
[x] Define 2-3 tool schemas (e.g., get_weather, search_database, lookup_order)
[x] Write code that handles the model's tool call and returns results
[x] Implement a loop: user > model > tool call > tool result > model > final answer
[x] Understand this pattern — it is the foundation of all agent behavior


Deliverable:
[x] A working Python script that calls an LLM with tools/function calling
[x] Push to GitHub


================================================================================
WEEK 2: SQL + DATABASE SETUP
================================================================================
Hours: 10-12
Goal: Set up PostgreSQL, load sample data, and write queries.


Day 1-2: SQL Fundamentals (4 hrs)
[ ] Complete SQLBolt lessons 1-12 (https://sqlbolt.com)
[ ] Key concepts to nail:
    - SELECT, WHERE, ORDER BY, LIMIT
    - JOIN (INNER, LEFT, RIGHT)
    - GROUP BY, HAVING, COUNT, SUM, AVG
    - Subqueries
    - CTEs (WITH clauses)


Day 3-4: Set Up Your Project Database (4 hrs)
[x] Start PostgreSQL (locally or via Docker)
[x] Design a simple schema for a fake e-commerce support system:

    -- data/seed_data.sql

    CREATE TABLE customers (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100),
        email VARCHAR(100),
        created_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE orders (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER REFERENCES customers(id),
        product_name VARCHAR(200),
        status VARCHAR(50),
        total DECIMAL(10,2),
        created_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE support_tickets (
        id SERIAL PRIMARY KEY,
        customer_id INTEGER REFERENCES customers(id),
        order_id INTEGER REFERENCES orders(id),
        subject VARCHAR(200),
        description TEXT,
        status VARCHAR(50),
        created_at TIMESTAMP DEFAULT NOW()
    );

    -- Insert 50+ rows of sample data for each table

[x] Write seed data with realistic entries (use a local LLM or a sample data generator to create bulk INSERTs)
[x] Practice 10 queries against your data:
    - Find all open orders for a customer
    - Get total revenue by month
    - List unresolved support tickets with customer and order details


Day 5: Python + Database Connection (3 hrs)
[x] Install psycopg2 or asyncpg
[x] Write app/tools/database.py:
    - Function to connect to the database
    - Function to execute a query and return results
    - Function to execute a query safely (parameterized)
[x] Test it: call from a simple script, print results


Deliverable:
[x] PostgreSQL running with seeded data
[x] Python database utility module working
[x] Push to GitHub


================================================================================
WEEK 3: RAG PIPELINE
================================================================================
Hours: 10-12
Goal: Build a working retrieval-augmented generation pipeline.


Day 1-2: Embeddings + Vector Store (4 hrs)
[x] Understand what embeddings are (text > vector > similarity search)
[x] Install chromadb and the ollama Python client
[x] Write a script to:
    - Take a list of text chunks
    - Generate embeddings using an Ollama embedding model (e.g., nomic-embed-text)
    - Store them in ChromaDB
    - Query with a question and retrieve top-k results


Day 3-4: Document Ingestion (4 hrs)
[x] Create 10-15 markdown or text files in data/documents/ simulating a
    company knowledge base:
    - Return policy
    - Shipping FAQ
    - Product specifications
    - Troubleshooting guides
    - Account management help
[x] Write app/tools/retriever.py:
    - Load documents from the folder
    - Split them into chunks (use langchain_text_splitters or write simple logic)
    - Embed and store in ChromaDB
    - Expose a retrieve(query: str) -> list[str] function


Day 5: RAG Chain (3 hrs)
[x] Combine retrieval + LLM:
    1. User asks a question
    2. Retrieve top 3-5 relevant chunks from ChromaDB
    3. Inject chunks into LLM prompt as context
    4. LLM generates an answer grounded in the documents
[x] Test with 5+ questions and verify answers reference the correct documents
[x] Handle edge case: what happens when no relevant documents are found?

    # Simplified RAG pattern
    context_chunks = retriever.retrieve(user_question)
    context = "\n\n".join(context_chunks)

    prompt = f"""Answer the question based on the context below.
    If the context doesn't contain the answer, say "I don't have that information."

    Context:
    {context}

    Question: {user_question}
    """


Deliverable:
[x] Working RAG pipeline: ingest docs > embed > retrieve > answer
[x] Push to GitHub


================================================================================
WEEK 4: LANGGRAPH FUNDAMENTALS
================================================================================
Hours: 10-12
Goal: Learn LangGraph and convert your components into graph-based agents.


Day 1-2: LangGraph Concepts (4 hrs)
[x] Read LangGraph documentation: https://langchain-ai.github.io/langgraph/
[x] Understand core concepts:
    - State: shared data that flows through the graph
    - Nodes: functions that process and update state
    - Edges: connections between nodes (including conditional edges)
    - Graph: the overall workflow
[x] Build a simple 3-node graph:
    - Node 1: take user input
    - Node 2: call LLM
    - Node 3: format output
[x] Run it and trace the execution


Day 3-4: Build the Router Agent (4 hrs)
[x] Define your agent state:

    from typing import TypedDict, Literal

    class AgentState(TypedDict):
        user_message: str
        intent: str  # "rag", "sql", "action", "unknown"
        context: list[str]
        sql_query: str
        sql_results: str
        api_results: str
        final_answer: str
        messages: list

[x] Write app/agents/router.py:
    - Takes user message
    - Calls LLM to classify intent into: rag, sql, action, or unknown
    - Routes to the correct downstream node

[x] Write a conditional edge function:

    def route_by_intent(state: AgentState) -> str:
        intent = state["intent"]
        if intent == "rag":
            return "rag_agent"
        elif intent == "sql":
            return "sql_agent"
        elif intent == "action":
            return "action_agent"
        else:
            return "fallback"


Day 5: Build the RAG Agent Node (3 hrs)
[x] Write app/agents/rag_agent.py:
    - Receives state
    - Calls your retriever from Week 3
    - Calls LLM with retrieved context
    - Updates state with final_answer
[x] Wire it into the graph: router > rag_agent > end
[x] Test with knowledge base questions


Deliverable:
[x] LangGraph with router + RAG agent working end-to-end
[x] Push to GitHub


================================================================================
WEEK 5: SQL AGENT + ACTION AGENT
================================================================================
Hours: 10-12
Goal: Build remaining agent nodes and complete the multi-agent graph.


Day 1-3: SQL Agent (5 hrs)
[x] Write app/agents/sql_agent.py:
    - Receives user question from state
    - Calls LLM with your database schema to generate a SQL query
    - CRITICAL: validate/sanitize the generated SQL (read-only, no DROP/DELETE)
    - Execute query against PostgreSQL
    - Call LLM again to format results into natural language
    - Update state with final_answer

    SCHEMA_PROMPT = """
    You have access to a PostgreSQL database with these tables:

    customers (id, name, email, created_at)
    orders (id, customer_id, product_name, status, total, created_at)
    support_tickets (id, customer_id, order_id, subject, description, status, created_at)

    Write a SQL query to answer the user's question.
    Return ONLY the SQL query, nothing else.
    Only use SELECT statements.
    """

[x] Test with questions like:
    - "How many orders were placed last month?"
    - "What's the status of order #1234?"
    - "Which customer has the most support tickets?"


Day 4-5: Action Agent (4 hrs)
[x] Write app/tools/api_client.py:
    - Pick 1-2 simple external APIs or mock them:
        - Check shipping status (mock)
        - Send notification/email (mock — just log it)
        - Create a support ticket (write to database)
[x] Write app/agents/action_agent.py:
    - Uses LLM function calling to decide which action to take
    - Executes the action
    - Returns result to state
[x] Wire everything into the full graph:

    START > router > rag_agent > END
                   > sql_agent > END
                   > action_agent > END
                   > fallback > END

[x] Test the full graph with mixed questions


Deliverable:
[x] All 3 agent nodes working within LangGraph
[x] Full routing working correctly
[x] Push to GitHub


================================================================================
WEEK 6: CONVERSATION MEMORY + ERROR HANDLING
================================================================================
Hours: 10-12
Goal: Make the agent production-ready with memory and resilience.


Day 1-2: Conversation Memory (4 hrs)
[x] Add message history to your agent state
[x] Use LangGraph's checkpointer to persist state across turns
[x] Implement a MemorySaver or SQLite-based checkpointer
[x] Test multi-turn conversations:
    - "How many orders were placed last month?" > answer
    - "Break that down by product" > should use context from previous turn


Day 3-4: Error Handling + Fallbacks (4 hrs)
[x] Add try/except around every external call (LLM, database, API)
[x] Implement retries with exponential backoff for LLM calls
[x] Add a fallback node: if any agent fails, return a graceful error message
[x] Handle these scenarios:
    [x] LLM API is down or rate-limited
    [x] SQL query returns an error
    [x] No relevant documents found in RAG
    [x] User intent is unclear
[x] Add logging throughout (use Python's logging module)


Day 5: Input Validation + Safety (3 hrs)
[x] Validate user input (length, content)
[x] SQL injection prevention: ensure generated SQL is read-only
[x] Add guardrails: reject off-topic or inappropriate requests
[x] Test edge cases and document them


Deliverable:
[x] Multi-turn conversation working
[x] Robust error handling throughout
[x] Push to GitHub


================================================================================
WEEK 7: FASTAPI BACKEND
================================================================================
Hours: 10-12
Goal: Wrap your agent in a production API.


Day 1-2: FastAPI Basics (3 hrs)
[x] Install fastapi and uvicorn
[x] Build app/main.py:

    from fastapi import FastAPI
    from pydantic import BaseModel

    app = FastAPI(title="Dispatch AI — Support Agent API")

    class ChatRequest(BaseModel):
        message: str
        session_id: str = "default"

    class ChatResponse(BaseModel):
        reply: str
        intent: str
        sources: list[str] = []

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        result = await run_agent(request.message, request.session_id)
        return ChatResponse(
            reply=result["final_answer"],
            intent=result["intent"],
            sources=result.get("sources", [])
        )

    @app.get("/health")
    async def health():
        return {"status": "healthy"}


Day 3-4: Streaming + Sessions (5 hrs)
[x] Implement streaming endpoint using FastAPI's StreamingResponse
[x] Tokens stream to the client as the LLM generates them
[x] Session management: each session_id gets its own conversation memory
[x] Add a GET /sessions/{session_id}/history endpoint


Day 5: API Hardening (3 hrs)
[x] Add rate limiting (use slowapi)
[x] Add CORS middleware
[x] Add request/response logging middleware
[x] Environment variable management with pydantic-settings
[x] Write a config.py that loads all settings from .env
[x] Test all endpoints with curl or Swagger docs at /docs


Deliverable:
[x] Fully functional API serving your agent
[x] Streaming responses working
[x] Push to GitHub


================================================================================
WEEK 8: LANGSMITH TRACING + EVALUATION
================================================================================
Hours: 10-12
Goal: Add observability and build an evaluation suite.


Day 1-2: LangSmith Integration (4 hrs)
[ ] Set up LangSmith account and get API key
[x] Add environment variables:

    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=your_key
    LANGCHAIN_PROJECT=dispatch-ai

[ ] Run your agent and verify traces appear in LangSmith dashboard
[ ] Explore: see each step, latency per node, token usage, inputs/outputs


Day 3-5: Evaluation Suite (7 hrs)
[x] Create eval/test_cases.json:

    [
      {
        "input": "What is your return policy?",
        "expected_intent": "rag",
        "expected_keywords": ["30 days", "refund", "return"],
        "category": "rag"
      },
      {
        "input": "How many orders were placed this month?",
        "expected_intent": "sql",
        "expected_keywords": ["orders"],
        "category": "sql"
      },
      {
        "input": "Create a support ticket for order 5",
        "expected_intent": "action",
        "category": "action"
      }
    ]

[x] Write eval/run_eval.py:
    - Load test cases
    - Run each through the agent
    - Check:
        - Intent accuracy: did the router pick the right intent?
        - Answer relevance: does the answer contain expected keywords?
        - Faithfulness: is the RAG answer grounded in retrieved docs?
        - Latency: how long did each request take?
        - Error rate: did any requests fail?
    - Output a summary report:

    === Dispatch AI Evaluation Report ===
    Total test cases: 20
    Intent accuracy: 95% (19/20)
    Answer relevance: 85% (17/20)
    Average latency: 2.3s
    Error rate: 0%

[x] Create at least 20 test cases covering all three agent types
[x] Save evaluation results to a JSON file for tracking over time
[ ] Bonus: Use LangSmith's built-in evaluation features if time permits


Deliverable:
[ ] LangSmith tracing active and showing data
[x] Evaluation suite with 20+ test cases
[x] Documented evaluation results
[x] Push to GitHub


================================================================================
WEEK 9: DOCKER + CLOUD DEPLOYMENT
================================================================================
Hours: 10-12
Goal: Containerize and deploy your agent to the cloud.


Day 1-2: Docker (4 hrs)
[x] Write Dockerfile:

    FROM python:3.11-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    COPY . .
    EXPOSE 8000
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

[x] Write docker-compose.yml:

    version: "3.8"
    services:
      app:
        build: .
        ports:
          - "8000:8000"
        env_file:
          - .env
        depends_on:
          - db
          - chromadb

      db:
        image: postgres:15
        environment:
          POSTGRES_DB: support_agent
          POSTGRES_USER: agent
          POSTGRES_PASSWORD: password
        ports:
          - "5432:5432"
        volumes:
          - pgdata:/var/lib/postgresql/data
          - ./data/seed_data.sql:/docker-entrypoint-initdb.d/seed.sql

      chromadb:
        image: chromadb/chroma:latest
        ports:
          - "8001:8000"
        volumes:
          - chromadata:/chroma/chroma

    volumes:
      pgdata:
      chromadata:

[ ] Run docker-compose up and verify everything works together
[ ] Test the API from outside the container


Day 3-5: Deployment (7 hrs) — optional
[ ] Choose a deployment target that fits your setup:
    - Local/self-hosted: run the full Docker stack on your machine (no external APIs required)
    - Cloud: use Railway.app, Render.com, or a self-managed server
[ ] Provision a PostgreSQL database (cloud managed or Docker)
[ ] Configure environment variables for the target platform
[ ] Keep ChromaDB as a container or use a local/self-hosted vector store
[ ] Test the live deployed API endpoint
[ ] Note the URL — this is your live demo link

Alternative Simpler Deployment:
If Docker/cloud is too complex, run the FastAPI backend and Streamlit frontend locally:
[x] Start the backend with `uvicorn app.main:app --reload`
[x] Start the frontend with `streamlit run frontend/streamlit_app.py`
[x] Open the local URLs in your browser


Deliverable:
[ ] Docker setup working locally
[ ] Agent deployed and accessible via a public URL
[x] Push Docker configs to GitHub


================================================================================
WEEK 10: STREAMLIT FRONTEND
================================================================================
Hours: 10-12
Goal: Build a simple chat UI that connects to your deployed API.


Day 1-3: Build the Chat Interface (6 hrs)
[x] Write frontend/streamlit_app.py:

    import streamlit as st
    import requests

    st.set_page_config(page_title="Dispatch AI", page_icon="🤖")
    st.title("🤖 Dispatch AI — Support Agent")

    API_URL = st.secrets.get("API_URL", "http://localhost:8000")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input("Ask me anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = requests.post(
                    f"{API_URL}/chat",
                    json={"message": prompt, "session_id": "streamlit_user"}
                )
                data = response.json()
                reply = data["reply"]
                st.write(reply)

                with st.expander("Details"):
                    st.write(f"**Intent**: {data['intent']}")
                    if data.get("sources"):
                        st.write(f"**Sources**: {', '.join(data['sources'])}")

        st.session_state.messages.append({"role": "assistant", "content": reply})


Day 4-5: Polish + Deploy Frontend (5 hrs)
[x] Add a sidebar with:
    - Project description
    - Example questions users can try
    - Architecture diagram image
[x] Add error handling for API failures
[ ] Deploy to Streamlit Community Cloud (free):
    - Push frontend to GitHub
    - Connect at https://share.streamlit.io
    - Add secrets (API_URL)
    - Get a public link
[x] Test the full flow: Streamlit > FastAPI > Agents > Response


Deliverable:
[x] Working chat UI
[ ] Deployed and accessible publicly
[x] Push to GitHub


================================================================================
WEEK 11: OPTIMIZATION + POLISH
================================================================================
Hours: 10-12
Goal: Optimize performance and finalize the codebase.


Day 1-2: Performance Optimization (4 hrs)
[x] Latency:
    - Add response caching for repeated queries (functools.lru_cache or Redis)
    - Use a small local model (e.g., llama3.2) for routing (fast), and a larger local model (e.g., qwen2.5 or llama3.1) for final answers
    - Measure and log time per node in the graph
[x] Cost tracking:
    - Log token usage per request
    - Add a /metrics endpoint showing:
        - Total requests served
        - Average latency
        - Total tokens consumed
        - Cost estimate


Day 3-4: Code Quality (4 hrs)
[x] Add type hints everywhere
[x] Add docstrings to all functions
[x] Create a clean requirements.txt with pinned versions
[x] Run a linter (ruff or flake8) and fix issues
[x] Write 5-10 unit tests for critical functions:
    - Router intent classification
    - SQL sanitization
    - Retriever returns relevant results
    - API endpoints return correct schemas


Day 5: Architecture Documentation (3 hrs)
[x] Write docs/architecture.md:
    - System overview with diagram
    - Component descriptions
    - Data flow explanation
    - Design decisions and trade-offs
[x] Create an architecture diagram (use draw.io, Excalidraw, or Mermaid):

    User > Streamlit Frontend > FastAPI Backend > Router Agent
    Router Agent > RAG Agent > ChromaDB
    Router Agent > SQL Agent > PostgreSQL
    Router Agent > Action Agent > External APIs
    FastAPI Backend > LangSmith Tracing


Deliverable:
[x] Optimized, clean codebase
[x] Architecture documentation with diagram
[x] Unit tests passing
[x] Push to GitHub


================================================================================
WEEK 12: README, BLOG POST, PORTFOLIO
================================================================================
Hours: 10-12
Goal: Make everything presentable and start applying.


Day 1-2: README (4 hrs)
[x] Write a stellar README.md:

    # 🤖 Dispatch AI

    A production-ready multi-agent AI system built with LangGraph, FastAPI,
    and PostgreSQL. Routes customer queries to specialized agents for
    knowledge base search, database queries, and automated actions.

    ## Live Demo
    - Chat UI: [link to Streamlit app]
    - API Docs: [link to FastAPI /docs]

    ## Architecture
    [Insert architecture diagram]

    ## Features
    - Multi-agent routing with intent classification
    - RAG-powered knowledge base Q&A
    - Natural language to SQL queries
    - Automated action execution
    - Conversation memory across sessions
    - Streaming responses
    - Comprehensive evaluation suite (95% intent accuracy, 2.3s avg latency)
    - Full observability via LangSmith

    ## Tech Stack
    Python | LangGraph | FastAPI | PostgreSQL | ChromaDB | Docker | Ollama | Streamlit

    ## Evaluation Results
    | Metric           | Score |
    |------------------|-------|
    | Intent Accuracy  | 95%   |
    | Answer Relevance | 85%   |
    | Avg Latency      | 2.3s  |
    | Error Rate       | 0%    |

    ## Quick Start
    [Docker setup instructions]

    ## Project Structure
    [Folder tree]

    ## Blog Post
    [Link to your blog post]


Day 3-4: Blog Post (5 hrs)
[ ] Write a blog post (1500-2000 words) on Medium or Dev.to:
    Title: "Building Dispatch AI: A Production Multi-Agent System from Scratch"
    Sections:
        1. What I built and why
        2. Architecture decisions
        3. How the routing works
        4. RAG implementation details
        5. SQL agent challenges and solutions
        6. Evaluation approach and results
        7. Deployment and monitoring
        8. Lessons learned
        9. What I'd do differently
    Include code snippets, architecture diagram, and screenshots
    Include LangSmith trace screenshots


Day 5: Final Checks + Apply (3 hrs)
[ ] Test the live demo end-to-end
[ ] Verify all GitHub links work
[ ] Review README for typos
[ ] Take screenshots of:
    [ ] Streamlit chat interface
    [ ] LangSmith traces
    [ ] Evaluation results
    [ ] API Swagger docs
[ ] Update your LinkedIn:
    - Add project to Featured section
    - Post about what you built
[ ] Start applying to jobs with your portfolio


================================================================================
WEEK 13: DEMO POLISH — RICHER & HARDER QUESTIONS
================================================================================
Hours: 8-10
Goal: Make the demo more impressive by widening the range of questions the
agent can answer and adding a second level of complexity to them. The system
already works end-to-end; this week is about showing it off.


Day 1: Deepen the demo data (2 hrs)
[x] Expand the seed data so richer questions have interesting answers:
    - More customers, orders, and support tickets (varied dates, statuses, totals)
    - Add supporting detail worth querying (e.g., product categories, order
      items/quantities, payments, shipping/refund status, account notes)
[x] Add a handful of matching knowledge base documents so RAG has more to draw on
    (e.g., billing, loyalty/rewards, account security, subscription/plan policies)
[x] Re-seed the database and re-index the knowledge base; sanity-check a few answers


Day 2: Add more example questions (2 hrs)
[x] Curate a larger, categorized bank of example questions across all intents:
    - RAG: returns, warranty, shipping, billing, loyalty, account security
    - SQL: counts, lookups, filters by status/date/customer
    - Action: weather, notifications, create/lookup support tickets
    - General: greetings, capabilities ("what can you do?")
[x] Surface these as clickable example prompts in the Streamlit sidebar,
    grouped by category so the demo is self-guiding


Day 3: Add a second level of complexity (3 hrs)
[x] Level-up SQL questions to multi-step / analytical queries:
    - Aggregations and grouping ("total revenue per product category")
    - Joins across tables ("which customers have an open ticket AND a returned order?")
    - Time windows and ranking ("top 5 customers by spend in the last 90 days")
    - Comparisons ("compare this month's orders vs last month's")
[x] Add multi-turn / follow-up questions that rely on conversation memory
    ("...and how many of those were shipped?")
[~] Add mixed-intent flows that chain RAG + SQL + action in one conversation
[x] Confirm SQL safety guardrails still reject anything non-read-only


Day 4: Polish + verify (2 hrs)
[x] Improve how answers are presented in the UI (tables for query results,
    clearer source citations, tidy intent/details expander)
[x] Add the new complex questions to eval/test_cases.json and re-run the eval suite
[ ] Record a short demo script (the exact sequence of questions to show off)
[x] Update README example questions; screenshots to re-capture after deployment

Deliverables:
[x] Broader, more interesting demo data + knowledge base
[x] Categorized example-question bank shown in the UI
[x] Support for multi-step, analytical, and follow-up questions
[~] Updated eval suite and a repeatable demo script


================================================================================
POST-PLAN: CONTINUED GROWTH
================================================================================

Quick Wins to Add:
[ ] Swap in a different local model (e.g., qwen2.5, phi4) as an alternative LLM (shows multi-LLM experience)
[ ] Try a different agent framework (e.g., smolagents, CrewAI) to show framework flexibility
[ ] Add a second blog post comparing LangGraph vs another agent framework

Ongoing Learning:
[ ] Follow LangChain and LangGraph changelogs
[ ] Read AI agent papers and blog posts weekly
[ ] Join LangChain Discord and AI engineering communities
[ ] Experiment with new models as they release

Interview Prep Topics:
[ ] Explain your architecture decisions and trade-offs
[ ] Discuss how you'd scale to 1000 concurrent users
[ ] Explain your evaluation methodology
[ ] Discuss cost optimization strategies
[ ] Be ready to live-code a simple agent in an interview


================================================================================
WEEKLY PROGRESS TRACKER
================================================================================

Week  | Focus                          | Status
------|--------------------------------|-------
  1   | Python + LLM APIs              | [x]
  2   | SQL + Database Setup           | [x]
  3   | RAG Pipeline                   | [x]
  4   | LangGraph Fundamentals         | [x]
  5   | SQL Agent + Action Agent       | [x]
  6   | Memory + Error Handling        | [x]
  7   | FastAPI Backend                | [x]
  8   | Tracing + Evaluation           | [x] Code done; live tracing/dashboard not verified
  9   | Docker + Deployment            | [~] Configs done; not deployed to a public URL
 10   | Streamlit Frontend             | [~] UI done; not deployed to Streamlit Cloud
 11   | Optimization + Polish          | [x]
 12   | README + Blog + Apply          | [~] README/blog draft done; publish + apply pending
 13   | Demo Polish — Richer Questions | [~] Core + UI polish done; demo script + screenshots remain


================================================================================
KEY REMINDERS
================================================================================

1. Commit daily. Even small progress. Your GitHub graph matters.
2. Don't get stuck. If something takes more than 2 hours, ask an LLM,
   check Stack Overflow, or skip and come back.
3. Working > Perfect. Ship ugly code first, then refine.
4. Document as you go. Don't leave docs for the end.
5. The project IS the learning. You don't need courses. Build and search.

================================================================================
END OF PLAN
================================================================================
```