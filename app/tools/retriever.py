"""Document retriever backed by ChromaDB + a configurable embeddings provider."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import chromadb
from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_embedder, get_llm

logger = logging.getLogger(__name__)

DOCUMENTS_DIR = Path(__file__).resolve().parents[2] / "data" / "documents"
CHROMA_DIR = Path(__file__).resolve().parents[2] / "data" / "chroma"

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

# Optional ChromaDB server connection (used in Docker); falls back to local persistent storage.
CHROMA_HOST = os.getenv("CHROMA_HOST")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

# Cosine distance threshold: chunks above this are considered irrelevant.
RAG_DISTANCE_THRESHOLD = float(os.getenv("RAG_DISTANCE_THRESHOLD", "0.65"))


def _get_client() -> chromadb.ClientAPI:
    """Return a ChromaDB client: HttpClient when CHROMA_HOST is set, else PersistentClient."""
    if CHROMA_HOST:
        return chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _get_collection(client: chromadb.ClientAPI | None = None):
    if client is None:
        client = _get_client()
    return client.get_or_create_collection(name="support_kb")


def _embed(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using the configured embedder."""
    return get_embedder().embed_documents(texts)


def _load_markdown_documents(directory: Path = DOCUMENTS_DIR) -> list[dict[str, str]]:
    """Load all markdown files from the knowledge base directory."""
    documents = []
    for file_path in sorted(directory.glob("*.md")):
        text = file_path.read_text(encoding="utf-8")
        documents.append(
            {
                "source": str(file_path.relative_to(directory)),
                "title": file_path.stem.replace("-", " ").title(),
                "text": text,
            }
        )
    return documents


def _split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into chunks by paragraphs, then by size if needed."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    buffer = ""
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 2 <= chunk_size:
            buffer = buffer + "\n\n" + paragraph if buffer else paragraph
        else:
            if buffer:
                chunks.append(buffer)
            buffer = paragraph
            # If a single paragraph is too long, split it by length.
            while len(buffer) > chunk_size:
                split_point = buffer.rfind(" ", 0, chunk_size)
                if split_point == -1:
                    split_point = chunk_size
                chunks.append(buffer[:split_point])
                buffer = buffer[max(0, split_point - overlap) :]
    if buffer:
        chunks.append(buffer)

    return chunks


def _chunk_documents(documents: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Split documents into chunks and attach source metadata."""
    chunks = []
    for doc in documents:
        for idx, text_chunk in enumerate(_split_text(doc["text"])):
            chunks.append(
                {
                    "id": f"{Path(doc['source']).stem}-{idx}",
                    "text": text_chunk,
                    "metadata": {
                        "source": doc["source"],
                        "title": doc["title"],
                    },
                }
            )
    return chunks


def index_documents() -> int:
    """Load, chunk, embed, and store all knowledge base documents."""
    client = _get_client()
    collection = _get_collection(client)

    # Clear existing entries so re-runs stay consistent.
    try:
        client.delete_collection(name="support_kb")
    except Exception:  # noqa: BLE001
        logger.debug("Could not delete collection; it may not exist")
    collection = client.create_collection(
        name="support_kb",
        metadata={"hnsw:space": "cosine"},
    )

    documents = _load_markdown_documents(DOCUMENTS_DIR)
    chunks = _chunk_documents(documents)

    if not chunks:
        return 0

    embeddings = _embed([chunk["text"] for chunk in chunks])

    collection.add(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["text"] for chunk in chunks],
        embeddings=embeddings,
        metadatas=[chunk["metadata"] for chunk in chunks],
    )
    return len(chunks)


def retrieve(query: str, k: int = 3) -> list[dict[str, Any]]:
    """Retrieve the top-k chunks most relevant to the query."""
    collection = _get_collection()
    query_embedding = _embed([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    matches = []
    for i in range(len(results["ids"][0])):
        matches.append(
            {
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            }
        )
    return matches


def answer(query: str, k: int = 3, conversation_history: str = "") -> dict[str, Any]:
    """Answer a question using retrieved context and the configured LLM."""
    matches = retrieve(query, k=k)
    relevant = [m for m in matches if m["distance"] <= RAG_DISTANCE_THRESHOLD]

    if not relevant:
        return {
            "query": query,
            "answer": "I don't have any relevant information about that.",
            "matches": matches,
        }

    context = "\n\n---\n\n".join(match["text"] for match in relevant)

    history_block = (
        f"Conversation history (for context only):\n{conversation_history}\n\n"
        if conversation_history
        else ""
    )

    messages = [
        SystemMessage(
            content=(
                "You are a helpful support assistant. Use only the provided context to answer "
                "the user's question. If the context does not contain the answer, say so. "
                "Cite the source titles when possible. Answer in plain text sentences and "
                "paragraphs; do not use markdown formatting, bold markers, or numbered lists."
            )
        ),
        HumanMessage(
            content=f"Context:\n{context}\n\n{history_block}Question: {query}\n\nAnswer:"
        ),
    ]

    response = get_llm(temperature=0.3, max_tokens=400).invoke(messages)

    return {
        "query": query,
        "answer": response.content,
        "matches": relevant,
    }


if __name__ == "__main__":
    count = index_documents()
    print(f"Indexed {count} chunks from {DOCUMENTS_DIR}")

    test_query = "How long do I have to return an item?"
    result = answer(test_query)
    print(f"\nQuestion: {result['query']}")
    print(f"Answer: {result['answer']}")
    print("\nSources:")
    for match in result["matches"]:
        print(f"  - {match['metadata']['title']} ({match['metadata']['source']})")
