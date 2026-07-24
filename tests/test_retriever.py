"""Tests for the ChromaDB retriever."""

from __future__ import annotations

from types import SimpleNamespace

from app.tools import retriever


def _make_ollama_mocks(monkeypatch):
    """Patch Ollama embed/chat calls so retriever tests do not require a running server."""

    def mock_embed(*, model, input):
        return SimpleNamespace(embeddings=[[1.0, 0.0, 0.0]] * len(input))

    def mock_chat(*, model, messages, options=None):
        return {"message": {"content": "You can return items within 30 days."}}

    monkeypatch.setattr(retriever.ollama, "embed", mock_embed)
    monkeypatch.setattr(retriever.ollama, "chat", mock_chat)


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
    _make_ollama_mocks(monkeypatch)

    # Ensure the collection exists so index_documents can delete/re-create it cleanly.
    retriever._get_collection()
    count = retriever.index_documents()
    assert count == 1

    result = retriever.answer("What is the return policy?")
    assert "30 days" in result["answer"].lower()
    assert result["matches"]
    assert result["matches"][0]["metadata"]["title"] == "Returns"
