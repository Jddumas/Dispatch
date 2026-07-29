# Step 9 — Evaluation + Observability

**Experiment:** `12_langsmith_trace.py`  
**Production files:** `eval/run_eval.py`, `eval/test_cases.json`

## Concept

How do you know your agent is working correctly? You can't just manually test it — it has too many code paths, and LLM outputs are non-deterministic. The answer is an automated eval suite: a set of test cases with known expected outputs that you can run after any change to check for regressions.

Observability (LangSmith tracing) is complementary — it shows you *what happened inside* each agent run, which is essential for debugging when something goes wrong.

---

## The Experiment (`12_langsmith_trace.py`)

The experiment sets up LangSmith tracing and runs the agent:

```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "lsv2_..."
os.environ["LANGCHAIN_PROJECT"] = "otto"

from app.agents import run_agent

questions = [
    "What is the return policy?",
    "How many orders were placed last month?",
    "What is the weather in Paris?",
]

for question in questions:
    state = run_agent(question, thread_id="langsmith-trace-demo")
    print(f"Intent: {state['intent']}")
    print(f"Assistant: {state['messages'][-1].content}")

print("Check the LangSmith dashboard for traces.")
```

Once tracing is on, every LangGraph invocation sends a trace to LangSmith: each node's inputs/outputs, latency, token counts, and the full message history. No code changes needed beyond the env vars.

---

## In Production

### Test cases (`eval/test_cases.json`)

30 test cases across 4 categories:

```json
{
  "id": "sql-01",
  "question": "How many orders are there?",
  "expected_intent": "sql",
  "expected_keywords": ["103"],
  "expected_sql_keywords": ["COUNT", "orders"]
},
{
  "id": "rag-01",
  "question": "What is the return policy?",
  "expected_intent": "rag",
  "expected_keywords": ["30 days", "refund"],
  "expected_sources": ["Returns"]
},
{
  "id": "action-01",
  "question": "What is the weather in Paris?",
  "expected_intent": "action",
  "expected_tool_pattern": "The weather in Paris"
}
```

### Evaluation metrics (`eval/run_eval.py`)

Five metrics per test case:

| Metric | How it's checked |
|--------|-----------------|
| **Intent accuracy** | `predicted_intent == expected_intent` |
| **Answer relevance** | All `expected_keywords` appear in the reply (case-insensitive) |
| **SQL accuracy** | All `expected_sql_keywords` appear in the generated SQL |
| **RAG source grounding** | All `expected_sources` appear in the `sources` list |
| **Tool accuracy** | `expected_tool_pattern` appears in the reply |

```python
def run_eval(test_cases):
    results = []
    for case in test_cases:
        state = run_agent(case["question"], thread_id=f"eval-{case['id']}")
        reply = state["messages"][-1].content
        intent = state.get("intent", "")

        intent_ok = intent == case["expected_intent"]
        keyword_ok = all(kw.lower() in reply.lower() for kw in case.get("expected_keywords", []))
        sources_ok = all(s in state.get("sources", []) for s in case.get("expected_sources", []))

        results.append({
            "id": case["id"],
            "intent_ok": intent_ok,
            "keyword_ok": keyword_ok,
            "sources_ok": sources_ok,
            "latency": ...,
        })

    # aggregate and print summary table
    intent_accuracy = sum(r["intent_ok"] for r in results) / len(results)
    print(f"Intent Accuracy: {intent_accuracy:.1%}")
```

Results are saved to `eval/results/eval_YYYYMMDD_HHMMSS.json` for trend tracking.

### Latest eval results (on `llama3.1` locally)

| Metric | Score |
|--------|-------|
| Intent Accuracy | 100.0% |
| Answer Relevance | 96.6% |
| SQL Generation Accuracy | 100.0% |
| RAG Source Grounding | 100.0% |
| Action Tool Accuracy | 100.0% |
| Error Rate | 0.0% |
| Average Latency | ~10.6s |

### LangSmith in production (`app/config.py`)

```python
if settings.langchain_api_key:
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
if settings.langchain_tracing_v2:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
```

Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY=lsv2_...` in `.env` to enable tracing. Every production request shows up in the LangSmith dashboard with its full node-by-node trace.

---

## Interview Q&A

**Q: Why do you need an eval suite if you can just manually test the chatbot?**
Manual testing is slow, inconsistent, and doesn't scale. An eval suite catches regressions automatically — if you change the SQL agent's prompt and it breaks intent classification for some edge case, the eval catches it before it ships. It also gives you a quantitative baseline: "intent accuracy went from 95% to 100% after I updated the classifier prompt."

**Q: Your keyword matching eval seems simple — what are its limitations?**
It's a heuristic, not a semantic check. It would pass if the answer contains "30 days" but hallucinated everything else around it. A stronger eval would use an LLM as a judge — send the question, expected answer, and actual answer to a model and ask "is this correct?" This is called LLM-as-judge evaluation, and LangSmith supports it natively.

**Q: What does LangSmith actually show you that logs don't?**
Logs show you what happened sequentially. LangSmith shows the full *tree* of an agent run: which nodes ran, what each node received as input, what it returned, how long it took, how many tokens it used, and the full prompt that was sent to the LLM. When a query returns a wrong answer, you can trace exactly which node produced the bad output and what prompt it was given.
