# Step 1 — Python Foundations

**Experiments:** `01_functions_classes_decorators.py`, `02_async_await.py`, `03_pydantic_validation.py`

## Concept

Before touching any AI code, three Python patterns show up constantly in production AI systems:

- **Decorators** — wrap functions to add retry logic, timing, or logging without changing the function itself
- **Async/await** — run multiple I/O operations concurrently instead of waiting for each one to finish
- **Pydantic** — declare the shape of data as a class; Pydantic validates it automatically at runtime

These three are the plumbing behind every production LLM app.

---

## The Experiments

### Decorators (`01_functions_classes_decorators.py`)

The key pattern is the parameterized retry decorator — a function that returns a decorator, which returns a wrapper:

```python
def retry_decorator(max_retries: int = 3, delay: float = 1.0):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

@retry_decorator(max_retries=3, delay=0.5)
def unreliable_function(success_rate: float = 0.5) -> str:
    if random.random() < success_rate:
        return "Success!"
    raise ValueError("Random failure occurred")
```

### Async/Await (`02_async_await.py`)

The core idea is that `asyncio.gather()` runs tasks *concurrently* — it starts all of them and waits for all to finish, instead of running one-by-one:

```python
async def fetch_data(url: str, delay: float) -> dict:
    await asyncio.sleep(delay)  # non-blocking wait (simulates a network call)
    return {"url": url, "data": f"Data from {url}"}

async def fetch_multiple_urls():
    tasks = [fetch_data(url, delay) for url, delay in urls]
    results = await asyncio.gather(*tasks)  # all run at the same time
    return results
```

### Pydantic (`03_pydantic_validation.py`)

Define a model once; get validation, serialization, and documentation for free:

```python
class Customer(BaseModel):
    name: str
    email: str
    age: int = Field(default=0, ge=0, le=120)

    @field_validator('email')
    @classmethod
    def email_must_contain_at(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Email must contain @')
        return v.lower()
```

If you pass `email="not-an-email"`, Pydantic raises a `ValidationError` before your code ever runs.

---

## In Production

### Retry logic → `app/agents/action_agent.py:50`
```python
llm_with_tools = llm.bind_tools(TOOLS).with_retry(
    stop_after_attempt=3, wait_exponential_jitter=True
)
```
LangChain's `.with_retry()` is the same decorator pattern — wrap the LLM call, retry on failure, back off between attempts.

### Async → `app/main.py`
Every FastAPI endpoint is `async def`. The streaming endpoint uses an `async for` loop to yield SSE events as tokens arrive. FastAPI + uvicorn handle the event loop; you write `await` and it just works.

### Pydantic → `app/main.py` + `app/config.py`
```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default")

class _Settings(BaseSettings):
    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
```
`BaseSettings` (from `pydantic-settings`) automatically reads env vars by their alias. `ChatRequest` validates every incoming API request before the graph runs.

---

## What Changed in Production

| Experiment | Production upgrade |
|------------|-------------------|
| Manual `time.sleep` retry | LangChain `.with_retry()` with exponential jitter |
| Hardcoded config values | `pydantic-settings` reads from `.env` or environment |
| `asyncio.run(main())` | FastAPI manages the event loop; endpoints are just `async def` |

---

## Interview Q&A

**Q: Why use Pydantic for configuration instead of just reading `os.getenv()`?**
You get type coercion (string `"true"` → bool `True`), default values, validation, and a single place to see all config. If a required env var is missing you get a clear error at startup, not a confusing `None` deep in a function.

**Q: What's the difference between `asyncio.gather` and running tasks sequentially?**
`gather` starts all coroutines at the same time and waits for all to complete. If you have 3 tasks that each take 1 second, `gather` takes ~1 second total; sequential takes ~3 seconds. This matters for the Customer 360 profile feature, which runs 7 DB queries — they run as sequential queries, but the concept is the same.

**Q: When would a retry decorator make things worse?**
When the failure isn't transient — e.g., retrying a bad request (400) will fail every time and just add delay. Production retry logic checks the exception type and only retries on network/timeout errors, not on client errors.
