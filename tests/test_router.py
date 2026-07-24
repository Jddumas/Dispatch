"""Tests for the LangGraph router."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.router import classify_intent


@pytest.fixture
def empty_state():
    return {
        "messages": [HumanMessage(content="placeholder")],
        "intent": "",
        "result": "",
        "sources": [],
        "sql_query": "",
    }


def _make_llm_mock(intent: str):
    """Return a mock ChatOllama that responds with the given intent string."""
    mock_llm = type("ChatOllama", (), {})()
    mock_llm.with_retry = lambda **kwargs: mock_llm
    mock_llm.invoke = lambda messages: AIMessage(content=intent)
    return mock_llm


def test_classify_intent_routing(empty_state):
    empty_state["messages"] = [HumanMessage(content="What is the return policy?")]
    with patch("app.agents.router.ChatOllama") as mock_chat:
        mock_chat.return_value = _make_llm_mock("rag")
        result = classify_intent(empty_state)
    assert result["intent"] == "rag"


def test_classify_intent_sql(empty_state):
    empty_state["messages"] = [HumanMessage(content="How many orders last month?")]
    with patch("app.agents.router.ChatOllama") as mock_chat:
        mock_chat.return_value = _make_llm_mock("sql")
        result = classify_intent(empty_state)
    assert result["intent"] == "sql"


def test_classify_intent_action(empty_state):
    empty_state["messages"] = [HumanMessage(content="What is the weather in Paris?")]
    with patch("app.agents.router.ChatOllama") as mock_chat:
        mock_chat.return_value = _make_llm_mock("action")
        result = classify_intent(empty_state)
    assert result["intent"] == "action"


def test_classify_intent_defaults_to_general_for_invalid(empty_state):
    empty_state["messages"] = [HumanMessage(content="Something weird")]
    with patch("app.agents.router.ChatOllama") as mock_chat:
        mock_chat.return_value = _make_llm_mock("not-an-intent")
        result = classify_intent(empty_state)
    assert result["intent"] == "general"
