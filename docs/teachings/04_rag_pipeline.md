# Step 4 — RAG Pipeline

**Experiment:** `08_rag.py`

## Concept

RAG — Retrieval-Augmented Generation — solves the problem of an LLM not knowing your specific documents. Instead of fine-tuning the model, you:

1. **Index** — split your documents into chunks and convert each chunk into a vector (a list of numbers that captures meaning)
2. **Retrieve** — when a question comes in, convert it to a vector too, then find the chunks whose vectors are most similar
3. **Generate** — pass the retrieved chunks to the LLM as context, and ask it to answer *using only that context*

The LLM doesn't "know" your documents — it reads them fresh each time. This keeps answers grounded in your actual content and avoids hallucination.

---

## The Experiment (`08_rag.py`)

The experiment imports the production retriever directly — it's the proof that the module works:

```python
from app.tools import retriever

# Step 1: index all markdown files in data/documents/
count = retriever.index_documents()
print(f"Indexed {count} chunks.")

# Step 2 + 3: retrieve relevant chunks and generate an answer
result = retriever.answer("How long do I have to return an item?", k=3)
print(result["answer"])
# → "You have 30 days from the delivery date to return any item..."

for match in result["matches"]:
    print(f"  source: {match['metadata']['title']}")
# → source: Returns
# → source: Refunds
```

---

## In Production (`app/tools/retriever.py`)

### Indexing: `index_documents()`

```python
def index_documents() -> int:
    documents = _load_markdown_documents(DOCUMENTS_DIR)  # reads all .md files
    chunks = _chunk_documents(documents)                  # splits into 800-char pieces
    embeddings = _embed([chunk["text"] for chunk in chunks])  # convert to vectors
    collection.add(ids=..., documents=..., embeddings=embeddings, metadatas=...)
    return len(chunks)
```

**Chunking strategy:** Documents are split at paragraph boundaries up to 800 characters, with 100-character overlap between chunks. Overlap ensures a sentence that straddles a boundary isn't split in half.

### Retrieval: `retrieve(query, k=3)`

```python
def retrieve(query: str, k: int = 3) -> list[dict]:
    query_embedding = _embed([query])[0]      # same embedding model as indexing
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    # distances are cosine distances; lower = more similar
    return matches
```

### Generating: `answer(query, k=3)`

```python
def answer(query: str, k: int = 3) -> dict:
    matches = retrieve(query, k=k)
    relevant = [m for m in matches if m["distance"] <= RAG_DISTANCE_THRESHOLD]

    if not relevant:
        return {"answer": "I don't have any relevant information about that."}

    context = "\n\n---\n\n".join(match["text"] for match in relevant)

    messages = [
        SystemMessage(content=(
            "Use only the provided context to answer. "
            "Cite source titles when possible. Answer in plain text."
        )),
        HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"),
    ]
    response = get_llm(temperature=0.3, max_tokens=400).invoke(messages)
    return {"answer": response.content, "matches": relevant}
```

The `RAG_DISTANCE_THRESHOLD` (default 1.0) filters out chunks that are too dissimilar — if nothing is close enough, the system says "I don't know" instead of hallucinating.

### Knowledge base

18 markdown files in `data/documents/`:
- **Policies:** returns, refunds, shipping, warranty, billing, cancellation, loyalty program, subscriptions
- **Products:** 27" monitor, mechanical keyboard, noise-canceling headphones, wireless mouse
- **Support:** contact info, troubleshooting, account security, password reset, order tracking

---

## What Changed vs. a Naive Approach

| Naive approach | Dispatch RAG |
|---------------|--------------|
| Stuff all documents into the prompt | Retrieve only the top-3 relevant chunks |
| No filtering | Distance threshold filters irrelevant results |
| Model can invent answers | System prompt enforces "use only the context" |
| Hardcoded embeddings | Configurable: Ollama (local), OpenAI, or FastEmbed |

---

## Interview Q&A

**Q: How does RAG differ from fine-tuning?**
Fine-tuning bakes knowledge into the model weights permanently — expensive, slow, and hard to update. RAG keeps knowledge outside the model in a searchable index — cheap to update (just re-index the changed docs), and the model can cite its sources. Fine-tuning is better for teaching the model a new *style* or *task*; RAG is better for keeping factual knowledge up to date.

**Q: What's a vector embedding and why does similarity search work?**
An embedding model converts text into a list of ~768 or 1536 numbers. Similar-meaning sentences end up with similar numbers — "return policy" and "send an item back" will be close in this space, even though they share no words. Cosine similarity measures the angle between two vectors; smaller angle = more similar meaning. This is why you can search by meaning, not just keywords.

**Q: What is the distance threshold for and what happens if it's too low or too high?**
It filters out chunks that are too far from the query. Too low (e.g., 0.3) and even relevant documents get rejected — the system says "I don't know" when it actually could answer. Too high (e.g., 2.0) and unrelated chunks get included — the LLM hallucinates by mixing irrelevant context into its answer. The default of 1.0 is a reasonable middle ground for cosine distance.
