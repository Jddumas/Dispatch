"""Streamlit chat frontend for the Dispatch AI support agent."""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

_API_URL_ENV = os.environ.get("API_URL")
if _API_URL_ENV:
    API_URL = _API_URL_ENV
else:
    try:
        API_URL = st.secrets.get("API_URL", "http://localhost:8000")
    except StreamlitSecretNotFoundError:
        API_URL = "http://localhost:8000"
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
        "Customer 360° Card": [
            "Customer card for Sarah Chen",
            "Customer summary for Marcus Johnson",
            "Tell me about Emily Torres",
        ],
        "RAG / Knowledge Base": [
            "What is the return policy?",
            "My package is 2 weeks late, what do I do?",
            "Can I return an item after 30 days?",
            "How does the loyalty program work?",
            "Can I stack my loyalty points with a promo code?",
            "What does the warranty cover?",
            "How do I file a warranty claim?",
        ],
        "SQL / Account": [
            "Which gold customers have an open ticket?",
            "What is the refund rate by product category?",
            "Who are the top 5 customers by lifetime spend?",
            "Which customers have an open ticket and a returned order?",
            "What is total revenue by product category?",
            "How many orders were placed last month?",
        ],
        "Tools & Actions": [
            "Create a support ticket for Marcus Johnson about a damaged item",
            "Update ticket 82 status to in progress",
            "Close ticket 82 with note: replacement shipped to customer",
            "Find the customer with email marcus.johnson@example.com",
            "What is the weather in Austin?",
        ],
        "Hybrid (RAG + SQL)": [
            "Is Sarah Chen's last order still eligible for a return?",
            "Does Marcus Johnson's last order qualify for a warranty claim?",
            "What loyalty tier is Sarah Chen and what discount does she get?",
            "Is Emily Torres's order eligible for a return?",
        ],
    }
    _CATEGORY_DESCRIPTIONS = {
        "Customer 360° Card": "Pull a complete profile for any customer — spend, orders, open tickets, refunds, and risk flags.",
        "Knowledge Base": "Ask questions about company policies: returns, warranties, loyalty rewards, and shipping rules.",
        "SQL / Account": "Run aggregate queries across all accounts — revenue, refund rates, top customers, open tickets.",
        "Tools & Actions": "Trigger live tools — create, update, and close support tickets; look up customers; check real-time weather.",
        "Hybrid (RAG + SQL)": "Questions that need both customer data and policy knowledge, like return or warranty eligibility.",
    }
    for category, questions in example_questions.items():
        with st.expander(category, expanded=False):
            if category in _CATEGORY_DESCRIPTIONS:
                st.caption(_CATEGORY_DESCRIPTIONS[category])
            for i, q in enumerate(questions):
                if st.button(q, key=f"example_{category}_{i}", use_container_width=True):
                    st.session_state.pending_prompt = q
                    st.rerun()
    st.markdown("---")

    use_streaming = st.checkbox("Use streaming response", value=True)
    if st.session_state.get("dev_mode"):
        session_id = st.text_input("Session ID", value=st.session_state.get("auto_session_id", ""), key="session_id_input")
    else:
        session_id = st.session_state.get("auto_session_id", "")

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
        "- Hybrid Agent → SQL + RAG → LLM\n"
        "- General Node → LLM"
    )

    st.markdown("---")
    st.checkbox("Developer mode", value=False, key="dev_mode")


if "auto_session_id" not in st.session_state:
    st.session_state.auto_session_id = str(uuid.uuid4())

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
            # Re-attach profile data for customer card messages.
            # Fetch each unique customer ID once, then apply to all matching messages.
            profile_cache: dict[str, list] = {}
            for msg in history:
                if msg["role"] == "assistant":
                    m = re.search(r"Customer 360 for .+? \(ID (\d+)\)", msg["content"])
                    if m:
                        cid = m.group(1)
                        if cid not in profile_cache:
                            try:
                                pr = requests.post(
                                    SYNC_CHAT_ENDPOINT,
                                    json={"message": f"customer card for customer {cid}", "session_id": "__profile_cache__"},
                                    timeout=15,
                                )
                                if pr.status_code == 200:
                                    data = pr.json().get("data") or []
                                    if data and isinstance(data[0], dict) and data[0].get("basic"):
                                        profile_cache[cid] = data
                            except requests.exceptions.RequestException:
                                pass
                        if cid in profile_cache:
                            msg["data"] = profile_cache[cid]
            st.session_state.messages = history
    except requests.exceptions.RequestException:
        pass


_TIER_COLORS: dict[str, tuple[str, str]] = {
    "platinum": ("#ede9fe", "#5b21b6"),
    "gold":     ("#fef9c3", "#854d0e"),
    "silver":   ("#f1f5f9", "#475569"),
    "bronze":   ("#fef3c7", "#92400e"),
}


def _is_customer_profile(msg: dict) -> bool:
    data = msg.get("data")
    return bool(
        data
        and isinstance(data, list)
        and isinstance(data[0], dict)
        and data[0].get("basic")
    )


def _render_customer_card(profile: dict) -> None:
    basic = profile["basic"]
    order_stats = profile["order_stats"]
    last_order = profile.get("last_order")
    open_tickets = int(profile["open_tickets"].get("open_count") or 0)
    ticket_list = profile.get("open_ticket_list") or []
    refunds = profile["refunds"]
    last_note = profile.get("last_note")
    last_payment = profile.get("last_payment")
    cohort_avg = float(profile.get("cohort_avg_spend") or 0)

    spend = float(order_stats.get("lifetime_spend") or 0)
    order_count = int(order_stats.get("order_count") or 0)
    aov = spend / order_count if order_count else 0.0
    refund_count = int(refunds.get("refund_count") or 0)
    refund_total = float(refunds.get("refund_total") or 0)

    tier = str(basic.get("loyalty_tier", "")).lower()
    bg, fg = _TIER_COLORS.get(tier, ("#f3f4f6", "#374151"))
    status = str(basic.get("account_status", "")).upper()
    status_bg = "#d1fae5" if status == "ACTIVE" else "#fee2e2"
    status_fg = "#065f46" if status == "ACTIVE" else "#991b1b"

    # Tenure
    try:
        created_dt = datetime.fromisoformat(str(basic.get("created_at", ""))[:10]).replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - created_dt).days
        if days >= 365:
            tenure_str = f"{days // 365}y {(days % 365) // 30}m"
        elif days >= 30:
            tenure_str = f"{days // 30}mo"
        else:
            tenure_str = f"{days}d"
    except ValueError:
        tenure_str = ""

    # Preferred contact
    _CONTACT_ICONS = {"email": "✉", "phone": "📞", "chat": "💬"}
    preferred = str(basic.get("preferred_contact", ""))
    contact_str = f"{_CONTACT_ICONS.get(preferred, '')} {preferred}".strip() if preferred else ""

    with st.container(border=True):
        col_name, col_badges = st.columns([2, 1])
        with col_name:
            email = basic.get('email', '')
            region = basic.get('region', '')
            cid = basic.get('id', '')
            caption_parts = [p for p in [email, region, f"#{cid}", tenure_str, contact_str] if p]
            _CARD_TOOLTIP = (
                "Customer 360° Card — a unified view assembled from all data sources: "
                "lifetime spend, order history, open support tickets, refunds, "
                "payment method, account notes, and computed risk flags."
            )
            st.markdown(
                f"**👤 {basic.get('name', 'Unknown')}** &nbsp;"
                f"<span title='{_CARD_TOOLTIP}' style='cursor:help;opacity:0.4;font-size:0.8rem'>ℹ</span>"
                f"&nbsp;<span style='font-size:0.8rem;opacity:0.6'>"
                f"{' · '.join(caption_parts)}</span>",
                unsafe_allow_html=True,
            )
        with col_badges:
            st.markdown(
                f"<div style='text-align:right;white-space:nowrap'>"
                f"<span style='background:{bg};color:{fg};padding:3px 10px;"
                f"border-radius:12px;font-size:0.72rem;font-weight:600'>{tier.upper()}</span>"
                f"&nbsp;"
                f"<span style='background:{status_bg};color:{status_fg};padding:3px 10px;"
                f"border-radius:12px;font-size:0.72rem;font-weight:600'>{status}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"<span style='font-size:0.95rem'>"
            f"<strong>&#36;{spend:,.2f}</strong> lifetime &nbsp;·&nbsp; "
            f"<strong>{order_count}</strong> orders &nbsp;·&nbsp; "
            f"<strong>&#36;{aov:,.2f}</strong> avg order"
            f"</span>",
            unsafe_allow_html=True,
        )

        _STATUS_COLORS = {
            "delivered": ("#d1fae5", "#065f46"),
            "returned":  ("#fee2e2", "#991b1b"),
            "shipped":   ("#dbeafe", "#1e40af"),
            "pending":   ("#fef3c7", "#92400e"),
            "cancelled": ("#f3f4f6", "#374151"),
        }

        detail_lines = []

        if last_order:
            lo_date = str(last_order.get("created_at", ""))[:10]
            lo_total = float(last_order.get("total") or 0)
            lo_status = str(last_order.get("status", "")).title()
            s_bg, s_fg = _STATUS_COLORS.get(lo_status.lower(), ("#f3f4f6", "#374151"))
            status_badge = (
                f"<span style='background:{s_bg};color:{s_fg};"
                f"padding:1px 7px;border-radius:8px;font-size:0.8em;font-weight:600'>"
                f"{lo_status}</span>"
            )
            detail_lines.append(
                f"<b>Last Order:</b> {last_order.get('product_name', '—')} — "
                f"{status_badge} — {lo_date} (${lo_total:,.2f})"
            )

        if open_tickets:
            items = "".join(
                f"<li>{t['subject']} "
                f"<span style='opacity:0.5;font-size:0.85em'>({str(t['created_at'])[:10]})</span></li>"
                for t in ticket_list
            )
            detail_lines.append(
                f"<b>Support:</b> {open_tickets} open ticket(s)"
                f"<ul style='margin:2px 0 0 0;padding-left:1.2em'>{items}</ul>"
            )
        else:
            detail_lines.append("<b>Support:</b> No open tickets")

        refund_str = f"{refund_count} (${refund_total:,.2f})" if refund_count else "None"
        payment_str = (
            str(last_payment.get("method", "")).replace("_", " ").title()
            if last_payment else "—"
        )
        detail_lines.append(f"<b>Refunds:</b> {refund_str} &nbsp;|&nbsp; <b>Payment:</b> {payment_str}")

        if last_note:
            note_date = str(last_note.get("created_at", ""))[:10]
            detail_lines.append(f"<b>Note:</b> {last_note.get('note', '')} <i>({note_date})</i>")

        st.markdown(
            "<hr style='margin:6px 0;border:none;border-top:1px solid rgba(49,51,63,0.2)'>"
            f"<div style='font-size:0.9rem;line-height:2'>"
            + "<br>".join(detail_lines)
            + "</div>",
            unsafe_allow_html=True,
        )

        # Recompute flags from structured data (mirrors _format_customer_profile logic)
        flags: list[tuple[str, str]] = []
        if open_tickets >= 2 and refund_count >= 1:
            flags.append(("warning", "At-risk: multiple open tickets and refund history"))
        elif open_tickets >= 3:
            flags.append(("warning", "At-risk: high volume of open support tickets"))
        if cohort_avg and spend >= cohort_avg * 2:
            flags.append((
                "success",
                f"High-value: spend is {spend / cohort_avg:.1f}x the account average (${cohort_avg:,.0f})",
            ))
        last_order_date_str = str(order_stats.get("last_order_date") or "")
        if last_order_date_str and last_order_date_str != "None":
            try:
                lo_dt = datetime.fromisoformat(last_order_date_str)
                if lo_dt.tzinfo is None:
                    lo_dt = lo_dt.replace(tzinfo=timezone.utc)
                days_since = (datetime.now(timezone.utc) - lo_dt).days
                if days_since > 180 and basic.get("account_status") == "active":
                    flags.append(("info", f"Dormant: no purchase in {days_since} days"))
            except ValueError:
                pass

        if flags:
            st.markdown(
                "<hr style='margin:6px 0;border:none;border-top:1px solid rgba(49,51,63,0.2)'>",
                unsafe_allow_html=True,
            )
            for flag_type, flag_msg in flags:
                if flag_type == "warning":
                    st.warning(flag_msg)
                elif flag_type == "success":
                    st.success(flag_msg)
                else:
                    st.info(flag_msg)


def _escape_text(text: str) -> str:
    """Escape markdown characters that Streamlit's st.markdown treats as special.

    Streamlit's markdown renderer interprets $...$ as math and _..._ as italic.
    Escaping them keeps plain-text replies looking like normal black text.
    """
    return text.replace("$", "\\$").replace("_", "\\_")



def _display_message(msg: dict, idx: int) -> None:
    with st.chat_message(msg["role"]):
        if _is_customer_profile(msg):
            _render_customer_card(msg["data"][0])
        else:
            st.write(_escape_text(msg["content"]))
        if msg.get("intent") and st.session_state.get("dev_mode"):
            with st.expander("Details"):
                st.write(f"Intent: `{msg['intent']}`")
                if msg.get("sources"):
                    st.caption("Sources")
                    for source in msg["sources"]:
                        st.markdown(f"- *{source}*")
                if msg.get("sql_query"):
                    st.caption("SQL")
                    st.code(msg["sql_query"], language="sql")
                if msg.get("data") and not _is_customer_profile(msg):
                    st.caption("Query results")
                    df = pd.DataFrame(msg["data"])
                    st.dataframe(df, use_container_width=True, hide_index=True)


for idx, message in enumerate(st.session_state.messages):
    _display_message(message, idx)


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
                # intentional leading spaces in the payload. Restore escaped newlines.
                data = text[5:].removeprefix(" ").replace("\\n", "\n")
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
                _is_profile = bool(rows and isinstance(rows[0], dict) and rows[0].get("basic"))
                if rows and not _is_profile:
                    st.caption("Query results")
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, hide_index=True)

    st.session_state.messages.append(
        {"role": "assistant", "content": reply, "intent": intent, "sources": sources, "sql_query": sql_query, "data": rows, "question": prompt}
    )
    st.rerun()
