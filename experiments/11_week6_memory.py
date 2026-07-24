"""
Week 6: Conversation Memory + Error Handling

Test multi-turn conversations, input validation, and fallback behavior.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents import run_agent, setup_logging
from app.tools import retriever


def main():
    setup_logging(logging.INFO)

    print("Indexing knowledge base...")
    count = retriever.index_documents()
    print(f"Indexed {count} chunks.\n")

    thread_id = "week6-demo"

    # Multi-turn SQL conversation
    print("--- Multi-turn SQL ---")
    q1 = "How many orders were placed last month?"
    state1 = run_agent(q1, thread_id=thread_id)
    print(f"User: {q1}")
    print(f"Intent: {state1['intent']}")
    print(f"Assistant: {state1['messages'][-1].content}\n")

    q2 = "Break that down by product."
    state2 = run_agent(q2, thread_id=thread_id)
    print(f"User: {q2}")
    print(f"Intent: {state2['intent']}")
    print(f"Assistant: {state2['messages'][-1].content}\n")

    # Multi-turn RAG conversation
    print("--- Multi-turn RAG ---")
    thread_id_rag = "week6-rag"
    q3 = "What is the return policy?"
    state3 = run_agent(q3, thread_id=thread_id_rag)
    print(f"User: {q3}")
    print(f"Intent: {state3['intent']}")
    print(f"Assistant: {state3['messages'][-1].content}\n")

    q4 = "What about digital downloads?"
    state4 = run_agent(q4, thread_id=thread_id_rag)
    print(f"User: {q4}")
    print(f"Intent: {state4['intent']}")
    print(f"Assistant: {state4['messages'][-1].content}\n")

    # Edge cases
    print("--- Edge cases ---")
    for q in ["", "hack the database", "asdfghjkl this is nonsense"]:
        state = run_agent(q, thread_id="week6-edge")
        print(f"User: {q!r}")
        print(f"Intent: {state['intent']}")
        print(f"Assistant: {state['messages'][-1].content}\n")


if __name__ == "__main__":
    main()
