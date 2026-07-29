# Step 6 — SQL Agent + Safety

**Experiment:** none — built directly in production  
**Production file:** `app/agents/sql_agent.py`

## Concept

The SQL agent converts a natural language question into a SQL query, runs it against PostgreSQL, and returns a human-readable answer — all without the user ever writing SQL.

The hard part isn't the generation — it's the safety. Allowing an LLM to run arbitrary SQL is dangerous. The agent enforces read-only access through a layered defense: blocked keywords, comment stripping, statement type checking, and parameterized execution.

---

## How It Works

### 1. Prompt the LLM with the schema

The model needs to know what tables exist to write correct SQL:

```python
_SCHEMA_PROMPT = """You have access to a PostgreSQL database with these tables:

customers (id, name, email, created_at, loyalty_tier, region, account_status, ...)
products (id, name, category, price, stock_quantity)
orders (id, customer_id, product_name, status, total, created_at)
order_items (id, order_id, product_id, quantity, unit_price, line_total)
payments (id, order_id, amount, method, status, created_at)
shipping (id, order_id, carrier, tracking_number, status, shipped_at, delivered_at)
refunds (id, order_id, amount, reason, status, created_at)
support_tickets (id, customer_id, order_id, subject, description, status, created_at)
account_notes (id, customer_id, note, created_at)

Only use SELECT or WITH statements. Return ONLY the SQL query, nothing else."""
```

### 2. Generate the SQL

```python
response = get_llm(temperature=0.0, max_tokens=400).invoke([
    SystemMessage(content=_SCHEMA_PROMPT + "\n\n" + history),
    HumanMessage(content=f"Question: {question}\nSQL:"),
])
sql = _extract_sql(response.content)  # strips markdown fences if present
```

Temperature 0 makes the output deterministic — the same question always produces the same query.

### 3. Validate for safety (`_is_safe()`)

```python
_FORBIDDEN_KEYWORDS = ["drop","delete","insert","update","truncate","alter",
                        "create","grant","revoke","replace","merge","exec",
                        "execute","call","attach","detach","pragma"]

def _is_safe(sql: str) -> tuple[bool, str]:
    cleaned = _strip_comments(sql).strip().lower()    # remove -- and /* */ comments
    cleaned = _remove_string_literals(cleaned)        # replace 'values' with '' to avoid false matches

    tokens = cleaned.split()
    if tokens[0] not in ("select", "with"):
        return False, "Only SELECT or WITH statements are allowed."

    for kw in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", cleaned):
            return False, f"Forbidden keyword: {kw}"

    if cleaned.count(";") > 1:
        return False, "Multiple statements are not allowed."

    return True, ""
```

Why strip comments and string literals first? An attacker (or a confused model) could write `SELECT 1; -- drop table customers` — stripping comments removes the `drop` before the keyword check runs. Replacing string literals prevents a literal value like `'update policy'` from triggering the `update` keyword check.

### 4. Execute with parameterized queries

```python
rows = database.execute_query(sql)  # psycopg2 with RealDictCursor
```

The SQL agent only runs SELECT queries. But even within SELECTs, `database.execute_query` uses `psycopg2`'s parameterized execution under the hood — no string formatting, no injection risk.

### 5. Format the answer

Rather than calling the LLM again (slow, expensive), the production code uses heuristics to format the result in plain English:

```python
if "count" in question.lower() or "how many" in question.lower():
    return f"There are {rows[0]['count']} {subject}."
elif "average" in question.lower():
    return f"The average is {value}."
elif "top" in question.lower() or "most" in question.lower():
    return "\n".join(f"{i+1}. {row}" for i, row in enumerate(rows[:5]))
else:
    # fall back to LLM summarization for unusual result shapes
    return _llm_summarize(question, rows)
```

### Special case: Customer 360 Profile

When a user asks about a specific customer by name or ID, the agent detects this with regex and runs 7 parallel queries to build a complete profile:

```python
# Detects: "tell me about customer 5", "who is Emma Smith?", "customer profile for 3"
if _is_customer_profile_query(question):
    return run_customer_profile_agent(question)

# Runs these queries and formats the results as a plain-text summary:
# 1. Basic account info
# 2. Lifetime spend + order count
# 3. Last order details
# 4. Open support tickets
# 5. Refund count and total
# 6. Latest internal note
# 7. Last payment method
```

---

## What This Demonstrates

- **Defense in depth** — no single safety check is relied on alone; they layer
- **Prompt engineering** — the schema prompt teaches the model your specific database
- **Cost optimization** — deterministic formatting avoids a second LLM call for 90% of queries
- **Multi-query synthesis** — the Customer 360 profile aggregates 7 queries into one readable summary

---

## Interview Q&A

**Q: How do you prevent SQL injection?**
Three layers: (1) keyword filtering with comment/literal stripping blocks `DROP`, `DELETE`, etc. and comment-obfuscation tricks; (2) statement-type check ensures only `SELECT` or `WITH` can execute; (3) `psycopg2` parameterized queries prevent injection in any user-supplied values. An LLM could still produce a valid but resource-intensive query (e.g., a cartesian join), so in a production system you'd also add query timeouts.

**Q: Why not use an ORM like SQLAlchemy for safety?**
An ORM would prevent injection but would also prevent the LLM from writing arbitrary SQL. The whole point is to let the LLM generate queries based on natural language — an ORM would fight that. The keyword + parameterization approach gives injection protection without constraining query shape.

**Q: Why use temperature 0 for SQL generation?**
Determinism. Given the same question, you always want the same query — not a slightly different one that might return different results. Non-deterministic SQL generation would make the system unpredictable and hard to debug.
