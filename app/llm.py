"""Provider-agnostic LLM and embedding factory."""

from __future__ import annotations

import httpx
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import (
    EMBED_MODEL,
    EMBED_PROVIDER,
    GROQ_API_KEY,
    GROQ_VERIFY_SSL,
    LLM_MODEL,
    LLM_PROVIDER,
    OLLAMA_HOST,
    OPENAI_API_KEY,
)


def get_llm(
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> BaseChatModel:
    """Return a chat model based on the configured LLM_PROVIDER."""
    model_name = model or LLM_MODEL

    if LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq

        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        http_client = httpx.Client(verify=GROQ_VERIFY_SSL)
        return ChatGroq(
            model=model_name,
            api_key=GROQ_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens,
            http_client=http_client,
        )

    if LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI

        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return ChatOpenAI(
            model=model_name,
            api_key=OPENAI_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # Default to Ollama.
    from langchain_ollama import ChatOllama

    kwargs: dict[str, object] = {
        "model": model_name,
        "temperature": temperature,
        "base_url": OLLAMA_HOST,
    }
    if max_tokens is not None:
        kwargs["num_predict"] = max_tokens
    return ChatOllama(**kwargs)


def get_embedder() -> Embeddings:
    """Return an embeddings model based on the configured EMBED_PROVIDER."""
    if EMBED_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings

        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when EMBED_PROVIDER=openai")
        return OpenAIEmbeddings(
            model=EMBED_MODEL or "text-embedding-3-small",
            api_key=OPENAI_API_KEY,
        )

    if EMBED_PROVIDER == "fastembed":
        from langchain_community.embeddings import FastEmbedEmbeddings

        return FastEmbedEmbeddings(model_name=EMBED_MODEL or "BAAI/bge-small-en-v1.5")

    # Default to Ollama.
    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(model=EMBED_MODEL or "nomic-embed-text", base_url=OLLAMA_HOST)
