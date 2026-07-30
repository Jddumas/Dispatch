"""Evaluation suite for the Otto multi-agent support system."""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Make repo root importable when running this script directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents import run_agent, setup_logging
from app.config import LLM_MODEL
from app.tools import database

logger = logging.getLogger(__name__)

CASES_PATH = Path(__file__).parent / "test_cases.json"
RESULTS_DIR = Path(__file__).parent / "results"

TOOL_PATTERNS = {
    "get_weather": ["weather in"],
    "send_notification": ["Notification sent to"],
    "create_support_ticket": ["created", "ticket"],
    "update_ticket_status": ["ticket"],
    "close_ticket": ["closed"],
    "get_customer_by_email": ["@example.com"],
}


def load_cases(path: Path = CASES_PATH) -> list[dict]:
    """Load test cases from JSON."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _contains_all(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return all(kw.lower() in text_lower for kw in keywords)


def _check_tool(expected_tool: str, reply: str) -> bool:
    patterns = TOOL_PATTERNS.get(expected_tool, [])
    reply_lower = reply.lower()
    return all(p.lower() in reply_lower for p in patterns)


def evaluate_case(case: dict) -> dict:
    """Run a single test case through the agent and score it."""
    case_id = case["id"]
    thread_id = f"eval-{case_id}-{int(time.time()*1000)}"
    start = time.perf_counter()

    try:
        state = run_agent(case["input"], thread_id=thread_id)
        latency = time.perf_counter() - start
        reply = state["messages"][-1].content if state.get("messages") else ""
        intent = state.get("intent", "")
        sources = state.get("sources", [])
        sql_query = state.get("sql_query", "")

        # Intent accuracy
        intent_ok = intent == case["expected_intent"]

        # Answer relevance (expected keywords present)
        keyword_ok = _contains_all(reply, case.get("expected_keywords", []))

        # SQL generation accuracy
        query_ok = None
        if case["category"] == "sql":
            expected_query_keywords = case.get("expected_query_keywords", [])
            if sql_query:
                query_ok = all(kw.upper() in sql_query.upper() for kw in expected_query_keywords)
            else:
                query_ok = False

        # RAG faithfulness/source grounding
        sources_ok = None
        if case["category"] == "rag":
            expected_sources = case.get("expected_sources", [])
            if expected_sources:
                sources_ok = bool(set(expected_sources) & set(sources))

        # Action tool correctness (best-effort heuristic based on reply text)
        tool_ok = None
        if case["category"] == "action" and "expected_tool" in case:
            tool_ok = _check_tool(case["expected_tool"], reply)

        logger.info(
            "[%s] intent=%s (ok=%s) latency=%.2fs",
            case_id,
            intent,
            intent_ok,
            latency,
        )

        return {
            "id": case_id,
            "input": case["input"],
            "category": case["category"],
            "expected_intent": case["expected_intent"],
            "predicted_intent": intent,
            "reply": reply,
            "sources": sources,
            "sql_query": sql_query,
            "latency_seconds": round(latency, 3),
            "intent_ok": intent_ok,
            "keyword_ok": keyword_ok,
            "query_ok": query_ok,
            "sources_ok": sources_ok,
            "tool_ok": tool_ok,
            "error": None,
        }
    except Exception as exc:
        latency = time.perf_counter() - start
        logger.exception("[%s] failed", case_id)
        return {
            "id": case_id,
            "input": case["input"],
            "category": case["category"],
            "expected_intent": case["expected_intent"],
            "predicted_intent": None,
            "reply": "",
            "sources": [],
            "sql_query": "",
            "latency_seconds": round(latency, 3),
            "intent_ok": False,
            "keyword_ok": False,
            "query_ok": False if case["category"] == "sql" else None,
            "sources_ok": False if case["category"] == "rag" else None,
            "tool_ok": False if case["category"] == "action" else None,
            "error": str(exc),
        }


def _compute_summary(results: list[dict]) -> dict:
    total = len(results)
    errors = sum(1 for r in results if r["error"])
    intent_ok_count = sum(1 for r in results if r["intent_ok"])
    keyword_ok_count = sum(1 for r in results if r["keyword_ok"])

    sql_results = [r for r in results if r["category"] == "sql"]
    rag_results = [r for r in results if r["category"] == "rag"]
    action_results = [r for r in results if r["category"] == "action"]
    hybrid_results = [r for r in results if r["category"] == "hybrid"]

    def _pct(part: list, key: str) -> float | None:
        valid = [r for r in part if r[key] is not None]
        if not valid:
            return None
        return round(100 * sum(1 for r in valid if r[key]) / len(valid), 1)

    avg_latency = round(
        sum(r["latency_seconds"] for r in results) / total, 3
    ) if total else 0.0

    hybrid_intent_pct = (
        round(100 * sum(1 for r in hybrid_results if r["intent_ok"]) / len(hybrid_results), 1)
        if hybrid_results
        else None
    )
    hybrid_keyword_pct = (
        round(100 * sum(1 for r in hybrid_results if r["keyword_ok"]) / len(hybrid_results), 1)
        if hybrid_results
        else None
    )

    return {
        "total": total,
        "error_rate_percent": round(100 * errors / total, 1) if total else 0.0,
        "intent_accuracy_percent": round(100 * intent_ok_count / total, 1) if total else 0.0,
        "answer_relevance_percent": round(100 * keyword_ok_count / total, 1) if total else 0.0,
        "sql_generation_accuracy_percent": _pct(sql_results, "query_ok"),
        "rag_faithfulness_percent": _pct(rag_results, "sources_ok"),
        "tool_accuracy_percent": _pct(action_results, "tool_ok"),
        "hybrid_intent_accuracy_percent": hybrid_intent_pct,
        "hybrid_answer_relevance_percent": hybrid_keyword_pct,
        "average_latency_seconds": avg_latency,
        "model": LLM_MODEL,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _print_summary(summary: dict) -> None:
    print("\n=== Otto Evaluation Report ===")
    print(f"Model: {summary['model']}")
    print(f"Total test cases: {summary['total']}")
    print(f"Intent accuracy: {summary['intent_accuracy_percent']}%")
    print(f"Answer relevance: {summary['answer_relevance_percent']}%")
    if summary["sql_generation_accuracy_percent"] is not None:
        print(f"SQL generation accuracy: {summary['sql_generation_accuracy_percent']}%")
    if summary["rag_faithfulness_percent"] is not None:
        print(f"RAG source grounding: {summary['rag_faithfulness_percent']}%")
    if summary["tool_accuracy_percent"] is not None:
        print(f"Action tool accuracy: {summary['tool_accuracy_percent']}%")
    if summary.get("hybrid_intent_accuracy_percent") is not None:
        print(f"Hybrid intent accuracy: {summary['hybrid_intent_accuracy_percent']}%")
        print(f"Hybrid answer relevance: {summary['hybrid_answer_relevance_percent']}%")
    print(f"Average latency: {summary['average_latency_seconds']}s")
    print(f"Error rate: {summary['error_rate_percent']}%")
    print("=====================================\n")


def main() -> None:
    setup_logging(logging.INFO)
    cases = load_cases()
    logger.info("Loaded %d test cases", len(cases))

    logger.info("Resetting seed data before evaluation...")
    counts = database.reset_seed_data()
    logger.info("Seed reset: %s", counts)

    try:
        results = [evaluate_case(case) for case in cases]
        summary = _compute_summary(results)
        _print_summary(summary)

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        results_path = RESULTS_DIR / f"eval_{timestamp}.json"
        output = {"summary": summary, "results": results}
        with results_path.open("w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        logger.info("Saved evaluation results to %s", results_path)
    finally:
        logger.info("Resetting seed data after evaluation...")
        try:
            counts = database.reset_seed_data()
            logger.info("Seed reset: %s", counts)
        except Exception:
            logger.exception("Post-eval seed reset failed")


if __name__ == "__main__":
    main()
