"""FastAPI backend for the Dispatch AI support agent."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from app.agents import get_thread_history, run_agent, setup_logging
from app.config import API_RATE_LIMIT, CORS_ORIGINS, TOKEN_COST_PER_1K
from app.tools import database

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize external services and metrics state before accepting requests."""
    app.state.metrics = {
        "total_requests": 0,
        "total_latency": 0.0,
        "total_tokens": 0,
        "intent_counts": {},
        "cost_per_1k_tokens": TOKEN_COST_PER_1K,
    }
    app.state.metrics_lock = asyncio.Lock()

    try:
        from app.tools import retriever

        def _check_and_index() -> int:
            client = retriever._get_client()
            collection = retriever._get_collection(client)
            if collection.count() == 0:
                logger.info("ChromaDB collection is empty; indexing knowledge base...")
                return retriever.index_documents()
            logger.info("ChromaDB collection already has %s chunks; skipping index", collection.count())
            return 0

        indexed = await run_in_threadpool(_check_and_index)
        if indexed:
            logger.info("Indexed %d knowledge-base chunks", indexed)
    except Exception:
        logger.exception("ChromaDB initialization failed")

    yield
    # Shutdown cleanup can be added here.


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Dispatch AI — Support Agent API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, duration, and client IP."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        client = request.client.host if request.client else "-"
        logger.info(
            "%s %s %s - %.3fs - %s",
            request.method,
            request.url.path,
            response.status_code,
            duration,
            client,
        )
        return response


app.add_middleware(RequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = "default"


class FeedbackRequest(BaseModel):
    session_id: str
    question: str
    reply: str
    intent: str = ""
    rating: str = Field(..., pattern="^(up|down)$")
    reason: str = ""


class ChatResponse(BaseModel):
    reply: str
    intent: str
    sources: list[str] = []
    sql_query: str = ""
    data: list[dict[str, Any]] | None = None


@lru_cache(maxsize=128)
def _cached_agent_run(message: str, session_id: str) -> dict[str, Any]:
    """Cacheable agent runner keyed by message and session ID.

    The return value is plain serializable data so it is safe to return
    from the cache repeatedly without mutating LangChain message objects.
    """
    state = run_agent(message, thread_id=session_id)
    return {
        "reply": state["messages"][-1].content,
        "intent": state.get("intent", "general"),
        "sources": state.get("sources", []),
        "sql_query": state.get("sql_query", ""),
        "data": state.get("data") or [],
    }


def _estimate_tokens(prompt: str, reply: str) -> int:
    """Rough token estimate for English text (average ~4 characters per token)."""
    return max(1, (len(prompt) + len(reply)) // 4)


async def _update_metrics(
    request: Request,
    intent: str,
    prompt: str,
    reply: str,
    latency: float,
) -> None:
    """Update aggregate counters for the /metrics endpoint."""
    metrics = request.app.state.metrics
    async with request.app.state.metrics_lock:
        metrics["total_requests"] += 1
        metrics["total_latency"] += latency
        metrics["intent_counts"][intent] = metrics["intent_counts"].get(intent, 0) + 1
        metrics["total_tokens"] += _estimate_tokens(prompt, reply)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/metrics")
@limiter.limit("60/minute")
async def metrics(request: Request) -> dict[str, Any]:
    """Return aggregate request, latency, token, cost, and feedback metrics."""
    m = request.app.state.metrics
    async with request.app.state.metrics_lock:
        total = m["total_requests"]
        avg_latency = m["total_latency"] / total if total else 0.0
        cost = (m["total_tokens"] / 1000) * m["cost_per_1k_tokens"]

    try:
        rows = await run_in_threadpool(
            database.execute_query_safe,
            "SELECT rating, COUNT(*) AS cnt FROM feedback GROUP BY rating",
        )
        counts = {r["rating"]: int(r["cnt"]) for r in rows}
        total_feedback = sum(counts.values())
        thumbs_up_rate = (
            round(100 * counts.get("up", 0) / total_feedback, 1) if total_feedback else None
        )
    except Exception:
        logger.warning("Could not fetch feedback stats")
        total_feedback = 0
        thumbs_up_rate = None

    return {
        "total_requests": total,
        "average_latency_seconds": round(avg_latency, 3),
        "total_tokens": m["total_tokens"],
        "cost_estimate_usd": round(cost, 6),
        "intent_counts": dict(m["intent_counts"]),
        "feedback_total": total_feedback,
        "thumbs_up_rate_percent": thumbs_up_rate,
    }


@app.post("/feedback", status_code=204)
@limiter.limit("60/minute")
async def submit_feedback(request: Request, payload: FeedbackRequest) -> None:
    """Record a thumbs-up or thumbs-down rating for an assistant reply."""
    try:
        await run_in_threadpool(
            database.execute_query,
            "INSERT INTO feedback (session_id, question, reply, intent, rating, reason) VALUES (%s, %s, %s, %s, %s, %s)",
            (payload.session_id, payload.question, payload.reply, payload.intent, payload.rating, payload.reason or None),
            fetch=False,
        )
    except Exception as exc:
        logger.exception("Failed to store feedback")
        raise HTTPException(status_code=500, detail="Failed to store feedback") from exc


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(API_RATE_LIMIT)
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    """Run the agent for a single message and return the final reply."""
    start = time.perf_counter()
    try:
        result = await run_in_threadpool(_cached_agent_run, payload.message, payload.session_id)
    except Exception as exc:
        logger.exception("Agent error for session %s", payload.session_id)
        raise HTTPException(status_code=500, detail="Agent processing failed") from exc

    latency = time.perf_counter() - start
    await _update_metrics(request, result["intent"], payload.message, result["reply"], latency)
    return ChatResponse(
        reply=result["reply"],
        intent=result["intent"],
        sources=result["sources"],
        sql_query=result.get("sql_query", ""),
        data=result.get("data") or [],
    )


def _sse(event: str, data: str) -> bytes:
    """Encode a Server-Sent Event.

    Newlines inside the data payload are escaped so the SSE framing stays intact.
    """
    data = data.replace("\n", "\\n")
    return f"event: {event}\ndata: {data}\n\n".encode()


async def _stream_reply(
    reply: str,
    intent: str,
    sources: list[str],
    sql_query: str = "",
    data: list[dict[str, Any]] | None = None,
) -> AsyncGenerator[bytes, None]:
    """Stream the final answer as Server-Sent Events.

    Note: the underlying local-LLM graph is synchronous, so this streams the
    already-generated reply word-by-word to improve perceived responsiveness.
    True token-by-token streaming would require async graph nodes and an
    LLM that supports streaming through LangChain.
    """
    yield _sse("intent", intent)
    for source in sources:
        yield _sse("source", source)
    if sql_query:
        yield _sse("sql_query", sql_query)
    if data:
        yield _sse("data", json.dumps(data, default=str))

    # Stream the reply in small chunks for a natural typing effect.
    words = reply.split(" ")
    for i in range(0, len(words), 2):
        chunk = " ".join(words[i : i + 2])
        if i > 0:
            chunk = " " + chunk
        yield _sse("message", chunk)
        await asyncio.sleep(0.01)

    yield _sse("done", "[DONE]")


@app.post("/chat/stream")
@limiter.limit(API_RATE_LIMIT)
async def chat_stream(request: Request, payload: ChatRequest) -> StreamingResponse:
    """Run the agent and stream the final reply as Server-Sent Events."""
    start = time.perf_counter()
    try:
        result = await run_in_threadpool(_cached_agent_run, payload.message, payload.session_id)
    except Exception as exc:
        logger.exception("Agent streaming error for session %s", payload.session_id)
        raise HTTPException(status_code=500, detail="Agent processing failed") from exc

    latency = time.perf_counter() - start
    await _update_metrics(request, result["intent"], payload.message, result["reply"], latency)

    return StreamingResponse(
        _stream_reply(
            result["reply"],
            result["intent"],
            result["sources"],
            sql_query=result.get("sql_query", ""),
            data=result.get("data") or [],
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/sessions/{session_id}/history")
@limiter.limit("60/minute")
async def history(request: Request, session_id: str) -> JSONResponse:
    """Return the persisted message history for a session."""
    try:
        messages = await run_in_threadpool(get_thread_history, session_id)
    except Exception as exc:
        logger.exception("History error for session %s", session_id)
        raise HTTPException(status_code=500, detail="Failed to load history") from exc

    return JSONResponse({"session_id": session_id, "messages": messages})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
