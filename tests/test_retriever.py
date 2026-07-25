"""Tests for the ChromaDB retriever."""

from __future__ import annotations

from app.tools import retriever


class _MockEmbedder:
    """Return deterministic embeddings for tests."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0]] * len(texts)

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]


class _MockChat:
    """Return a deterministic RAG answer for tests."""

    def invoke(self, messages):
        from langchain_core.messages import AIMessage

        return AIMessage(content="You can return items within 30 days.")


def _make_llm_mocks(monkeypatch):
    """Patch the configured embedder and LLM so tests do not require a running server."""
    monkeypatch.setattr(retriever, "get_embedder", lambda: _MockEmbedder())
    monkeypatch.setattr(retriever, "get_llm", lambda **kwargs: _MockChat())


def test_retriever_returns_relevant_answer(tmp_path, monkeypatch):
    """Index a tiny knowledge base and verify the RAG answer contains the expected fact."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "returns.md").write_text(
        "# Returns\n\nYou can return any item within 30 days.\n", encoding="utf-8"
    )

    chroma_dir = tmp_path / "chroma"
    monkeypatch.setattr(retriever, "DOCUMENTS_DIR", docs_dir)
    monkeypatch.setattr(retriever, "CHROMA_DIR", chroma_dir)
    monkeypatch.setattr(retriever, "CHROMA_HOST", "")
    _make_llm_mocks(monkeypatch)

    # Ensure the collection exists so index_documents can delete/re-create it cleanly.
    retriever._get_collection()
    count = retriever.index_documents()
    assert count == 1

    result = retriever.answer("What is the return policy?")
    assert "30 days" in result["answer"].lower()
    assert result["matches"]
    assert result["matches"][0]["metadata"]["title"] == "Returns"
