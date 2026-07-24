"""FastAPI backend for the Dispatch AI support agent."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncGenerator

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
from app.config import API_RATE_LIMIT, CORS_ORIGINS


setup_logging()
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Dispatch AI — Support Agent API")
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


class ChatResponse(BaseModel):
    reply: str
    intent: str
    sources: list[str] = []


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
@limiter.limit(API_RATE_LIMIT)
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    """Run the agent for a single message and return the final reply."""
    try:
        state = await run_in_threadpool(run_agent, payload.message, payload.session_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent error for session %s: %s", payload.session_id, exc)
        raise HTTPException(status_code=500, detail="Agent processing failed") from exc

    return ChatResponse(
        reply=state["messages"][-1].content,
        intent=state.get("intent", "general"),
        sources=state.get("sources", []),
    )


def _sse(event: str, data: str) -> bytes:
    """Encode a Server-Sent Event."""
    return f"event: {event}\ndata: {data}\n\n".encode("utf-8")


async def _stream_reply(reply: str, intent: str, sources: list[str]) -> AsyncGenerator[bytes, None]:
    """Stream the final answer as Server-Sent Events.

    Note: the underlying local-LLM graph is synchronous, so this streams the
    already-generated reply word-by-word to improve perceived responsiveness.
    True token-by-token streaming would require async graph nodes and an
    LLM that supports streaming through LangChain.
    """
    yield _sse("intent", intent)
    for source in sources:
        yield _sse("source", source)

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
    try:
        state = await run_in_threadpool(run_agent, payload.message, payload.session_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent streaming error for session %s: %s", payload.session_id, exc)
        raise HTTPException(status_code=500, detail="Agent processing failed") from exc

    reply = state["messages"][-1].content
    intent = state.get("intent", "general")
    sources = state.get("sources", [])

    return StreamingResponse(
        _stream_reply(reply, intent, sources),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/sessions/{session_id}/history")
@limiter.limit("60/minute")
async def history(request: Request, session_id: str) -> JSONResponse:
    """Return the persisted message history for a session."""
    try:
        messages = await run_in_threadpool(get_thread_history, session_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("History error for session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Failed to load history") from exc

    return JSONResponse({"session_id": session_id, "messages": messages})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
