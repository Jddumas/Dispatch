"""
Week 5: SQL Agent + Action Agent

Run the full multi-agent graph with all four branches and mixed questions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import HumanMessage

from app.agents import build_graph
from app.tools import retriever


def main() -> None:
    print("Indexing knowledge base...")
    count = retriever.index_documents()
    print(f"Indexed {count} chunks.\n")

    questions = [
        "How many orders were placed last month?",
        "Which customer has the most support tickets?",
        "What is the return policy?",
        "What is the weather in Paris?",
        "Send a notification to john@example.com saying your order has shipped",
        "Create a support ticket for customer 1 about order 5, subject 'Missing item'",
        "Hello!",
    ]

    graph = build_graph()
    for question in questions:
        print(f"\nUser: {question}")
        final_state = graph.invoke({"messages": [HumanMessage(content=question)]})
        print(f"Intent: {final_state['intent']}")
        print(f"Assistant: {final_state['messages'][-1].content}")


if __name__ == "__main__":
    main()
