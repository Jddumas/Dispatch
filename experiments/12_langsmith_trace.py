"""
Week 8: Verify LangSmith tracing is active.

Set these in your .env file (or environment) before running:

    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=lsv2_...
    LANGCHAIN_PROJECT=otto

Then run this script and check the LangSmith dashboard for the project.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    api_key = os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGCHAIN_PROJECT", "otto")

    if not api_key:
        print("LANGCHAIN_API_KEY is not set. Add it to .env and rerun.")
        print("Example .env entries:")
        print("  LANGCHAIN_TRACING_V2=true")
        print("  LANGCHAIN_API_KEY=lsv2_...")
        print("  LANGCHAIN_PROJECT=otto")
        return

    # Enable tracing for this run (idempotent if already set in .env).
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ.setdefault("LANGCHAIN_PROJECT", project)

    from app.agents import run_agent, setup_logging

    setup_logging()

    questions = [
        "What is the return policy?",
        "How many orders were placed last month?",
        "What is the weather in Paris?",
    ]

    for question in questions:
        print(f"\nUser: {question}")
        state = run_agent(question, thread_id="langsmith-trace-demo")
        print(f"Intent: {state['intent']}")
        print(f"Assistant: {state['messages'][-1].content}")

    print(f"\nCheck the LangSmith project '{project}' for traces.")


if __name__ == "__main__":
    main()
