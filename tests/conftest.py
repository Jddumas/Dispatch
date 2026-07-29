"""Shared pytest configuration for the Otto test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.tools import retriever


class _DummyAsyncLock:
    """Non-blocking stand-in for asyncio.Lock so sync TestClient can drive the app."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None


class _FakeCollection:
    """Collection stand-in used during app startup in tests."""

    def count(self) -> int:
        return 0


@pytest.fixture
def client(monkeypatch):
    """Yield a TestClient with the app lifespan mocked for fast, isolated tests."""
    monkeypatch.setattr(retriever, "_get_client", lambda: None)
    monkeypatch.setattr(
        retriever,
        "_get_collection",
        lambda client=None: _FakeCollection(),
    )
    monkeypatch.setattr(retriever, "index_documents", lambda: 0)

    app.state.metrics = {
        "total_requests": 0,
        "total_latency": 0.0,
        "total_tokens": 0,
        "intent_counts": {},
        "cost_per_1k_tokens": 0.0,
    }
    app.state.metrics_lock = _DummyAsyncLock()

    with TestClient(app) as test_client:
        yield test_client
