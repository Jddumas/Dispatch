# Step 10 — Docker + Deployment

**Experiment:** none — built directly  
**Production files:** `docker-compose.yml`, `Dockerfile`, `render.yaml`

## Concept

Deployment means making the app available to others, reliably. Two challenges: (1) the app depends on four services (FastAPI, PostgreSQL, ChromaDB, Ollama) that all need to be running in the right configuration; (2) the production server (Render) doesn't have a GPU or the disk space for Ollama models.

Docker solves (1) locally. The cloud deployment solves (2) by switching to lighter dependencies.

---

## Local: Docker Compose

`docker-compose.yml` defines four services and wires them together:

```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: support_agent
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: password
    volumes:
      - ./data/seed_data.sql:/docker-entrypoint-initdb.d/seed.sql  # auto-seeds on first start

  chromadb:
    image: chromadb/chroma:latest
    ports: ["8001:8000"]

  ollama:
    image: ollama/ollama:latest
    command: >
      sh -c "ollama serve & sleep 5 && ollama pull llama3.1 && ollama pull nomic-embed-text && wait"
    healthcheck:
      test: ["CMD-SHELL", "ollama list | grep -q 'llama3.1'"]
      interval: 15s
      retries: 60  # first startup pulls ~5GB of models

  app:
    build: .
    ports: ["8000:8000"]
    env_file: [.env]
    environment:
      - PGHOST=db                      # override .env for Docker networking
      - OLLAMA_HOST=http://ollama:11434
      - CHROMA_HOST=chromadb
    depends_on:
      db:       {condition: service_healthy}
      chromadb: {condition: service_healthy}
      ollama:   {condition: service_healthy}
```

Key patterns:
- `depends_on` with `service_healthy` ensures the app doesn't start until all dependencies are ready
- Services communicate by service name (e.g., `http://ollama:11434`) — Docker's internal DNS resolves service names
- The app's `.env` has localhost defaults; Docker `environment` overrides them for container-to-container networking
- `seed_data.sql` is mounted as a Docker init script — PostgreSQL runs it automatically on first start

### Dockerfile

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`--no-cache-dir` keeps the image smaller. `0.0.0.0` binds to all interfaces inside the container so Docker can route traffic to it.

---

## Cloud: Render + Streamlit Cloud

Render's free/CPU tier can't run Ollama (no GPU, limited disk). The deployment switches to lighter alternatives:

**`render.yaml`:**
```yaml
services:
  - type: web
    name: dispatch-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: LLM_PROVIDER
        value: groq           # ← Groq instead of Ollama
      - key: LLM_MODEL
        value: llama-3.1-8b-instant
      - key: EMBED_PROVIDER
        value: fastembed      # ← CPU embeddings instead of Ollama
      - key: EMBED_MODEL
        value: BAAI/bge-small-en-v1.5
```

**Provider swap:** `app/llm.py`'s `get_llm()` factory reads `LLM_PROVIDER` from config — changing one env var switches the whole app from Ollama to Groq. No code changes needed.

**Streamlit Cloud** hosts the frontend separately. It needs only one secret:
```toml
# Streamlit Cloud secrets
API_URL = "https://dispatch-api-27sb.onrender.com"
```

The backend and frontend are completely decoupled — Render handles the API, Streamlit Cloud handles the UI.

---

## Local vs. Cloud Config Comparison

| Config | Local | Cloud (Render) |
|--------|-------|----------------|
| LLM | Ollama (`llama3.1`) | Groq (`llama-3.1-8b-instant`) |
| Embeddings | Ollama (`nomic-embed-text`) | FastEmbed (`BAAI/bge-small-en-v1.5`) |
| Vector DB | Local ChromaDB | Local ChromaDB (ephemeral on Render) |
| PostgreSQL | Local (`localhost`) | Render PostgreSQL add-on |
| Cost | Free (local hardware) | Free tier (Groq has free quota) |

---

## Interview Q&A

**Q: Why split frontend and backend across two platforms?**
Render is optimized for Python/Node backends with persistent compute. Streamlit Community Cloud is purpose-built for Streamlit apps — it handles secrets management and hot reloads out of the box. Each platform hosts what it does best. The only coupling is the `API_URL` env var in the frontend.

**Q: What would break if you deployed Ollama to Render?**
Render free tier has ~512MB–1GB RAM and no GPU. `llama3.1` requires ~5GB RAM (4-bit quantized). Even if it fit, inference on CPU would take 30–120 seconds per response, making the app unusable. Groq runs the same model on its own hardware and returns responses in ~0.5–2 seconds via API.

**Q: What's the risk of ChromaDB being "ephemeral" on Render?**
Render's free tier uses an ephemeral filesystem — the disk resets on every deploy. ChromaDB stores its vector index on disk, so after each deploy the index is empty. The `lifespan` startup in `main.py` handles this: it checks if the collection is empty and re-indexes if so. Re-indexing from 18 small markdown files takes a few seconds — acceptable for a portfolio project, but in production you'd use a persistent ChromaDB server or a managed vector database.
