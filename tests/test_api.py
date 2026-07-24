"""Tests for the FastAPI endpoints."""

from __future__ import annotations


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_chat_endpoint_schema(client, monkeypatch):
    def fake_cached_run(message: str, session_id: str):
        return {
            "reply": "You can return items within 30 days.",
            "intent": "rag",
            "sources": ["Returns"],
            "sql_query": "",
        }

    monkeypatch.setattr("app.main._cached_agent_run", fake_cached_run)
    response = client.post(
        "/chat",
        json={"message": "What is the return policy?", "session_id": "test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reply"]
    assert data["intent"] == "rag"
    assert "Returns" in data["sources"]


def test_chat_stream_endpoint(client, monkeypatch):
    def fake_cached_run(message: str, session_id: str):
        return {
            "reply": "It is sunny.",
            "intent": "action",
            "sources": [],
            "sql_query": "",
        }

    monkeypatch.setattr("app.main._cached_agent_run", fake_cached_run)
    response = client.post(
        "/chat/stream",
        json={"message": "What is the weather?", "session_id": "test"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: intent" in body
    assert "data: action" in body
    assert "It is" in body
    assert "sunny" in body
    assert "event: done" in body


def test_metrics_endpoint(client, monkeypatch):
    def fake_cached_run(message: str, session_id: str):
        return {
            "reply": "Sunny.",
            "intent": "action",
            "sources": [],
            "sql_query": "",
        }

    monkeypatch.setattr("app.main._cached_agent_run", fake_cached_run)
    client.post("/chat", json={"message": "weather", "session_id": "m1"})
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_requests"] == 1
    assert data["intent_counts"]["action"] == 1
    assert data["total_tokens"] > 0


def test_history_endpoint(client, monkeypatch):
    def fake_history(thread_id: str):
        return [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]

    monkeypatch.setattr("app.main.get_thread_history", fake_history)
    response = client.get("/sessions/s1/history")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "s1"
    assert len(data["messages"]) == 2
