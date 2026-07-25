"""Streamlit chat frontend for the Dispatch AI support agent."""

from __future__ import annotations

import json
import os

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("API_URL", st.secrets.get("API_URL", "http://localhost:8000"))
CHAT_ENDPOINT = f"{API_URL}/chat/stream"
SYNC_CHAT_ENDPOINT = f"{API_URL}/chat"
HISTORY_ENDPOINT = f"{API_URL}/sessions"

st.set_page_config(
    page_title="Dispatch AI",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.title("🤖 Dispatch AI — Support Agent")

with st.sidebar:
    st.header("About")
    st.write(
        "Dispatch AI is a multi-agent support assistant that can answer "
        "policy questions from a knowledge base, query a PostgreSQL database, "
        "and perform actions like weather lookups or ticket creation."
    )
    st.markdown("---")

    st.subheader("Example questions")
    example_questions = {
        "RAG / Policy": [
            "What is the return policy?",
            "How do I reset my password?",
            "What payment methods do you accept?",
            "How does the loyalty program work?",
            "What is the Subscribe & Save discount?",
        ],
        "SQL / Account": [
            "How many orders were placed last month?",
            "What is total revenue by product category?",
            "Which customers have an open ticket and a returned order?",
            "Who are the top 5 customers by spend in the last 90 days?",
            "What is the average order value?",
        ],
        "Action": [
            "What is the weather in Paris?",
            "Create a support ticket for customer 2 about order 3",
            "Send a notification to team@example.com about order 5",
        ],
        "General": [
            "What can you do?",
            "Hello!",
        ],
    }
    for category, questions in example_questions.items():
        with st.expander(category, expanded=False):
            for i, q in enumerate(questions):
                if st.button(q, key=f"example_{category}_{i}", use_container_width=True):
                    st.session_state.pending_prompt = q
                    st.rerun()
    st.markdown("---")

    session_id = st.text_input("Session ID", value="streamlit_user", key="session_id_input")
    use_streaming = st.checkbox("Use streaming response", value=True)

    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.caption(
        "Architecture:\n\n"
        "Streamlit → FastAPI → LangGraph\n\n"
        "LangGraph routes to:\n"
        "- RAG Agent → ChromaDB\n"
        "- SQL Agent → PostgreSQL\n"
        "- Action Agent → Tools / APIs\n"
        "- General Node → LLM"
    )


if "messages" not in st.session_state:
    st.session_state.messages = []


# Load persisted history when the session ID changes.
if "session_id" not in st.session_state or st.session_state.session_id != session_id:
    st.session_state.session_id = session_id
    st.session_state.messages = []
    try:
        resp = requests.get(f"{HISTORY_ENDPOINT}/{session_id}/history", timeout=5)
        if resp.status_code == 200:
            history = resp.json().get("messages", [])
            st.session_state.messages = history
    except requests.exceptions.RequestException:
        pass


def _escape_text(text: str) -> str:
    """Escape markdown characters that Streamlit's st.markdown treats as special.

    Streamlit's markdown renderer interprets $...$ as math and _..._ as italic.
    Escaping them keeps plain-text replies looking like normal black text.
    """
    return text.replace("$", "\\$").replace("_", "\\_")


def _display_message(msg: dict) -> None:
    with st.chat_message(msg["role"]):
        st.write(_escape_text(msg["content"]))
        if msg.get("intent"):
            with st.expander("Details"):
                st.write(f"Intent: `{msg['intent']}`")
                if msg.get("sources"):
                    st.caption("Sources")
                    for source in msg["sources"]:
                        st.markdown(f"- *{source}*")
                if msg.get("sql_query"):
                    st.caption("SQL")
                    st.code(msg["sql_query"], language="sql")
                if msg.get("data"):
                    st.caption("Query results")
                    df = pd.DataFrame(msg["data"])
                    st.dataframe(df, use_container_width=True, hide_index=True)


for message in st.session_state.messages:
    _display_message(message)


def _handle_streaming_response(prompt: str, session_id: str) -> tuple[str, str, list[str], str, list[dict] | None]:
    reply = ""
    intent = "general"
    sources: list[str] = []
    sql_query = ""
    rows: list[dict] | None = None

    with requests.post(
        CHAT_ENDPOINT,
        json={"message": prompt, "session_id": session_id},
        stream=True,
        timeout=120,
    ) as resp:
        resp.raise_for_status()
        placeholder = st.empty()
        current_event: str | None = None
        for line in resp.iter_lines():
            if not line:
                continue
            text = line.decode("utf-8")
            if text.startswith("event:"):
                current_event = text[6:].strip()
            elif text.startswith("data:"):
                # SSE includes one space after the colon; remove it but keep any
                # intentional leading spaces in the payload.
                data = text[5:].removeprefix(" ")
                if current_event == "intent":
                    intent = data
                elif current_event == "source":
                    sources.append(data)
                elif current_event == "sql_query":
                    sql_query = data
                elif current_event == "data":
                    rows = json.loads(data)
                elif current_event == "message":
                    reply += data
                    placeholder.markdown(_escape_text(reply))
                elif current_event == "done":
                    break

    return reply, intent, sources, sql_query, rows


def _handle_sync_response(prompt: str, session_id: str) -> tuple[str, str, list[str], str, list[dict] | None]:
    resp = requests.post(
        SYNC_CHAT_ENDPOINT,
        json={"message": prompt, "session_id": session_id},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    reply = data.get("reply", "")
    intent = data.get("intent", "general")
    sources = data.get("sources", [])
    sql_query = data.get("sql_query", "")
    rows = data.get("data") or None
    st.write(_escape_text(reply))
    return reply, intent, sources, sql_query, rows


prompt = st.chat_input("Ask me anything...")
if not prompt and st.session_state.get("pending_prompt"):
    prompt = st.session_state.pop("pending_prompt")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    reply: str = ""
    intent: str = "general"
    sources: list[str] = []

    sql_query = ""
    rows: list[dict] | None = None
    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                if use_streaming:
                    reply, intent, sources, sql_query, rows = _handle_streaming_response(prompt, session_id)
                else:
                    reply, intent, sources, sql_query, rows = _handle_sync_response(prompt, session_id)
        except requests.exceptions.ConnectionError:
            reply = "Unable to reach the Dispatch AI API. Please make sure the backend is running."
            st.error(reply)
        except requests.exceptions.Timeout:
            reply = "The backend took too long to respond. Please try again."
            st.error(reply)
        except requests.exceptions.HTTPError as exc:
            reply = f"The backend returned an error: {exc.response.status_code}"
            st.error(reply)
        except Exception as exc:  # noqa: BLE001
            reply = f"Unexpected error: {exc}"
            st.error(reply)

        if reply and reply != "Unable to reach the Dispatch AI API. Please make sure the backend is running.":
            with st.expander("Details"):
                st.write(f"Intent: `{intent}`")
                if sources:
                    st.caption("Sources")
                    for source in sources:
                        st.markdown(f"- *{source}*")
                if sql_query:
                    st.caption("SQL")
                    st.code(sql_query, language="sql")
                if rows:
                    st.caption("Query results")
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, hide_index=True)

    st.session_state.messages.append(
        {"role": "assistant", "content": reply, "intent": intent, "sources": sources, "sql_query": sql_query, "data": rows}
    )
